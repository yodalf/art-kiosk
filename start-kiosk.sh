#!/bin/bash
# Kiosk Display Startup Script
# This script starts the Flask server and launches Firefox in kiosk mode

# Set X11 display (needed for GUI applications)
export DISPLAY=:0

# Change to the script directory
cd "$(dirname "$0")"

# Kill any existing Firefox instances
pkill -f "firefox.*kiosk" 2>/dev/null
pkill firefox 2>/dev/null

# Kill any existing unclutter processes
pkill unclutter 2>/dev/null

# Kill any existing Flask server processes for this kiosk
pkill -f "python.*app.py" 2>/dev/null

# Kill any process using port 80
if command -v fuser &> /dev/null; then
    sudo fuser -k 80/tcp 2>/dev/null
elif command -v lsof &> /dev/null; then
    sudo lsof -ti:80 | xargs kill -9 2>/dev/null
fi

# Wait for processes to clean up
sleep 2

# Start the Flask server in the background using venv (silently, requires sudo for port 80)
sudo ./venv/bin/python app.py > /dev/null 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 5

# Disable screen blanking (silently)
xset s off 2>/dev/null
xset -dpms 2>/dev/null
xset s noblank 2>/dev/null

# Hide cursor (silently)
if command -v unclutter &> /dev/null; then
    unclutter -idle 0.1 > /dev/null 2>&1 &
fi

# Start Firefox in kiosk mode (silently)
firefox --kiosk http://localhost/view > /dev/null 2>&1

# When Firefox closes, kill the server
kill $SERVER_PID 2>/dev/null
