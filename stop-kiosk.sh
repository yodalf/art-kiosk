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

# Kill any process using port 5000
if command -v fuser &> /dev/null; then
    fuser -k 5000/tcp 2>/dev/null
elif command -v lsof &> /dev/null; then
    lsof -ti:5000 | xargs kill -9 2>/dev/null
fi

echo "Kiosk stopped."
