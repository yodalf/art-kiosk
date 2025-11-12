# Quick Start Guide - Raspberry Pi

Follow these steps to get your kiosk display running on Raspberry Pi OS.

## Step 1: Install Required System Packages

```bash
sudo apt update
sudo apt install python3-venv python3-full firefox-esr unclutter -y
```

Note: `unclutter` automatically hides the mouse cursor when idle (in addition to CSS cursor hiding in the browser).

## Step 2: Set Up the Application

```bash
cd ~/kiosk_images

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## Step 3: Test the Server

```bash
# Make sure you're in the kiosk_images directory with venv activated
source venv/bin/activate
python app.py
```

You should see:
```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:80
 * Running on http://192.168.x.x:80
```

Keep this terminal open and continue to Step 4 in a new terminal or browser.

## Step 4: Upload Some Images

1. Find your Pi's IP address (shown in the output above, e.g., 192.168.1.100)
2. On any device on your network, open a web browser
3. Go to: `http://<your-pi-ip>/`
4. Drag and drop some images or click "Choose Files"
5. **Enable/disable images** using the "Show" checkbox on each image card (enabled by default)
6. Adjust the slideshow interval if desired (default: 10 minutes)

## Step 5: Test the Kiosk Display

In a new terminal on your Raspberry Pi:

```bash
firefox --kiosk http://localhost/view
```

You should see your images in fullscreen slideshow mode!

Press `ESC` or `F11` to exit fullscreen.

## Convenience Scripts

The kiosk includes helper scripts for easy management:

### Start the kiosk (server + Firefox):

```bash
cd ~/kiosk_images
./start-kiosk.sh
```

This script will:
- Kill any previous kiosk instances (server and browser)
- Start the Flask server
- Launch Firefox in fullscreen kiosk mode
- Clean up when you exit

### Stop the kiosk:

```bash
cd ~/kiosk_images
./stop-kiosk.sh
```

This will stop all kiosk-related processes.

## Step 6 (Optional): Auto-Start on Boot

To make the kiosk start automatically when the Pi boots, run the automated installer:

```bash
cd ~/kiosk_images
sudo ./install-autostart.sh
```

This will:
- Install systemd services for both Flask server and Firefox
- Enable them to start at boot
- Start them immediately

### Enable auto-login (optional):

For a fully automated kiosk, enable auto-login to the desktop:

```bash
sudo raspi-config
```

Navigate to: `System Options` → `Boot / Auto Login` → `Desktop Autologin`

### Reboot to test:

```bash
sudo reboot
```

After reboot, the kiosk should start automatically!

### Check if services are running:

```bash
sudo systemctl status kiosk-display.service
sudo systemctl status kiosk-firefox.service
```

## Keyboard Controls (During Slideshow)

- `Space` or `→` : Next image
- `←` : Previous image
- `F` : Toggle fill mode (contain vs cover)
- `R` : Reload images
- `F11` or `ESC` : Exit fullscreen

## Remote Control (No Keyboard Needed!)

Since this is a remote display, you can control the kiosk from any device on your network:

1. Open the management page: `http://<pi-ip>/`
2. Use the **Remote Control** section (orange box at the top)
3. Click buttons to control the kiosk:
   - **Previous/Next** - Navigate images
   - **Pause/Play** - Control slideshow
   - **Reload** - Refresh the display
4. Or click on any image thumbnail to jump directly to that image

Commands execute almost instantly (500ms polling).

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"

Make sure you activated the virtual environment:

```bash
cd ~/kiosk_images
source venv/bin/activate
pip install -r requirements.txt
```

### Server won't start

Check if port 80 is already in use:

```bash
sudo netstat -tlnp | grep 80
```

### Can't access from other devices

1. Check your Pi's IP address: `hostname -I`
2. Make sure your firewall allows port 80
3. Try accessing from the Pi itself first: `http://localhost`

### Images not displaying

1. Check that you uploaded images via the management interface at `/`
2. Press `R` to reload the page
3. Check browser console (F12) for errors

### Service not starting on boot

```bash
# Check service status
sudo systemctl status kiosk-display.service

# View logs
sudo journalctl -u kiosk-display.service -f

# Restart service
sudo systemctl restart kiosk-display.service
```

## Managing Your Kiosk

### Quick Commands

- **Start kiosk**: `./start-kiosk.sh` (cleans up previous instances automatically)
- **Stop kiosk**: `./stop-kiosk.sh`
- **Upload images**: `http://<pi-ip>/`
- **View kiosk**: `http://<pi-ip>/view`

### Systemd Service Commands (if installed)

- **Check server status**: `sudo systemctl status kiosk-display`
- **View server logs**: `sudo journalctl -u kiosk-display -f`
- **Restart server**: `sudo systemctl restart kiosk-display`
- **Stop server**: `sudo systemctl stop kiosk-display`

## Next Steps

- Customize the slideshow interval in the management interface
- Upload your images (supported formats: PNG, JPG, GIF, WebP, BMP)
- Set up auto-start for a fully automated kiosk
- Consider using a wireless keyboard to control the slideshow remotely

Enjoy your kiosk display!
