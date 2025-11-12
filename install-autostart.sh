#!/bin/bash
# Install systemd services for kiosk autostart

set -e

echo "Installing Kiosk Autostart Services..."
echo "======================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the actual user who called sudo
REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo ~$REAL_USER)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing for user: $REAL_USER"
echo "Home directory: $REAL_HOME"
echo "Kiosk directory: $SCRIPT_DIR"

# Stop services if they're running
echo ""
echo "Stopping existing services (if any)..."
systemctl stop kiosk-firefox.service 2>/dev/null || true
systemctl stop kiosk-display.service 2>/dev/null || true

# Copy service files
echo ""
echo "Installing service files..."
cp "$SCRIPT_DIR/kiosk-display.service" /etc/systemd/system/
cp "$SCRIPT_DIR/kiosk-firefox.service" /etc/systemd/system/

# Update WorkingDirectory and User in service files to actual values
sed -i "s|/home/pi/kiosk_images|$SCRIPT_DIR|g" /etc/systemd/system/kiosk-display.service
sed -i "s|/home/pi|$REAL_HOME|g" /etc/systemd/system/kiosk-firefox.service
sed -i "s|User=pi|User=$REAL_USER|g" /etc/systemd/system/kiosk-display.service
sed -i "s|User=pi|User=$REAL_USER|g" /etc/systemd/system/kiosk-firefox.service

# Reload systemd
echo ""
echo "Reloading systemd..."
systemctl daemon-reload

# Grant Python the capability to bind to port 80
echo ""
echo "Granting Python capability to bind to port 80..."
# Find the actual Python binary (not symlink)
PYTHON_BIN=$(readlink -f "$SCRIPT_DIR/venv/bin/python3")
setcap 'cap_net_bind_service=+ep' "$PYTHON_BIN"

# Enable services
echo ""
echo "Enabling services..."
systemctl enable kiosk-display.service
systemctl enable kiosk-firefox.service

# Start services
echo ""
echo "Starting services..."
systemctl start kiosk-display.service
sleep 2
systemctl start kiosk-firefox.service

# Check status
echo ""
echo "Service Status:"
echo "==============="
systemctl status kiosk-display.service --no-pager -l || true
echo ""
systemctl status kiosk-firefox.service --no-pager -l || true

echo ""
echo "============================================"
echo "Installation complete!"
echo "============================================"
echo ""
echo "The kiosk will now start automatically on boot."
echo ""
echo "Useful commands:"
echo "  sudo systemctl status kiosk-display.service   # Check Flask server status"
echo "  sudo systemctl status kiosk-firefox.service   # Check Firefox status"
echo "  sudo systemctl restart kiosk-display.service  # Restart Flask server"
echo "  sudo systemctl restart kiosk-firefox.service  # Restart Firefox"
echo "  sudo systemctl stop kiosk-firefox.service     # Stop Firefox"
echo "  sudo systemctl stop kiosk-display.service     # Stop Flask server"
echo "  sudo journalctl -u kiosk-display -f           # View Flask server logs"
echo "  sudo journalctl -u kiosk-firefox -f           # View Firefox logs"
echo ""
