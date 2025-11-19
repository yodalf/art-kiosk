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
systemctl stop kiosk.target 2>/dev/null || true
systemctl stop kiosk-firefox.service 2>/dev/null || true
systemctl stop kiosk-display.service 2>/dev/null || true

# Copy service files
echo ""
echo "Installing service files..."
cp "$SCRIPT_DIR/kiosk.target" /etc/systemd/system/
cp "$SCRIPT_DIR/kiosk-display.service" /etc/systemd/system/
cp "$SCRIPT_DIR/kiosk-firefox.service" /etc/systemd/system/

# Update WorkingDirectory and User in service files to actual values
sed -i "s|/home/realo/kiosk_images|$SCRIPT_DIR|g" /etc/systemd/system/kiosk-display.service
sed -i "s|/home/realo/kiosk_images|$SCRIPT_DIR|g" /etc/systemd/system/kiosk-firefox.service
sed -i "s|/home/realo|$REAL_HOME|g" /etc/systemd/system/kiosk-firefox.service
sed -i "s|User=realo|User=$REAL_USER|g" /etc/systemd/system/kiosk-display.service
sed -i "s|User=realo|User=$REAL_USER|g" /etc/systemd/system/kiosk-firefox.service
sed -i "s|-u realo|-u $REAL_USER|g" /etc/systemd/system/kiosk-firefox.service

# Make startup scripts executable
chmod +x "$SCRIPT_DIR/start-firefox-kiosk.sh"

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

# Enable target and services
echo ""
echo "Enabling kiosk.target and services..."
systemctl enable kiosk.target
systemctl enable kiosk-display.service
systemctl enable kiosk-firefox.service

# Start kiosk.target (starts both services)
echo ""
echo "Starting kiosk.target..."
systemctl start kiosk.target

# Check status
echo ""
echo "Service Status:"
echo "==============="
systemctl status kiosk.target --no-pager -l || true
echo ""
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
echo "  sudo systemctl status kiosk.target            # Check kiosk system status"
echo "  sudo systemctl start kiosk.target             # Start entire kiosk system"
echo "  sudo systemctl stop kiosk.target              # Stop entire kiosk system"
echo "  sudo systemctl restart kiosk.target           # Restart entire kiosk system"
echo ""
echo "  sudo systemctl status kiosk-display.service   # Check Flask server status"
echo "  sudo systemctl status kiosk-firefox.service   # Check Firefox status"
echo "  sudo journalctl -u kiosk-display -f           # View Flask server logs"
echo "  sudo journalctl -u kiosk-firefox -f           # View Firefox logs"
echo ""
