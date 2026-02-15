#!/bin/bash
# Stop Kiosk Display Script
# This script stops all kiosk-related processes

echo "Stopping kiosk display..."

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

echo "Kiosk stopped."
