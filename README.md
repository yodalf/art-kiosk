# Kiosk Image Display System

A web-based kiosk system for displaying images in slideshow mode, optimized for Raspberry Pi with a 2560x2880 portrait monitor.

## Features

- Web-based image upload and management
- **Dark theme interface** - Professional black background across all pages
- **Atmospheres** - Hierarchical organization layer above themes for complex content management
- **Themes** - Organize images into multiple themes with per-theme intervals; images can belong to multiple themes
- **Randomized ordering** - Images display in random order that changes with each theme/atmosphere switch
- **Image cropping** - Crop images to select specific regions that fill the entire kiosk display
- **Enable/disable individual images** - Control which images appear in the slideshow with checkboxes
- **Auto-preview uploads** - Newly uploaded images automatically display on the kiosk for immediate review
- **Remote control** - Control the kiosk from any device on your network
- **Click-to-jump** - Click any image thumbnail to immediately display it on the kiosk
- **Smooth dissolve transitions** - Optional fade effect between images
- Automatic slideshow with configurable intervals
- Real-time image scaling optimized for 2560x2880 portrait displays
- Firefox fullscreen/kiosk mode support
- Hidden mouse cursor for clean display
- Responsive image scaling with aspect ratio preservation
- Drag-and-drop upload interface
- RESTful API for image management

## Requirements

- Raspberry Pi running Raspberry Pi OS (X11 mode recommended)
- Python 3.7 or higher
- Firefox browser
- unclutter (for hiding mouse cursor in X11 mode)
- curl (for server readiness checks)
- Monitor: 2560x2880 (portrait orientation)

### Python Dependencies
- Flask 3.0.0
- Werkzeug 3.0.1
- flask-socketio 5.3.6
- python-socketio 5.11.1

**Important**: This system is designed for X11. If using Raspberry Pi OS with Wayland (newer versions), switch to X11 mode:
```bash
sudo raspi-config
# Navigate to: Advanced Options > Wayland > Select "X11"
# Then reboot
```

## Installation

### 1. Copy files to your Raspberry Pi

```bash
# On your computer, copy files to the Pi
scp -r kiosk_images pi@<raspberry-pi-ip>:~/
```

### 2. Set up Python virtual environment

On your Raspberry Pi:

```bash
cd ~/kiosk_images

# Install python3-venv if not already installed
sudo apt install python3-venv python3-full -y

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Make scripts executable

```bash
chmod +x app.py start-kiosk.sh
```

## Usage

### Starting the Server

Run the Flask server:

```bash
cd ~/kiosk_images
source venv/bin/activate  # Activate virtual environment
python app.py
```

Or use the start script (which handles the venv automatically):

```bash
./start-kiosk.sh
```

The server will start on `http://0.0.0.0:80` (accessible from any device on your network).

### Accessing the Interfaces

1. **Management Interface**: `http://<raspberry-pi-ip>/`
   - Upload images
   - **Crop images** - Click the "Crop" button to select a region that will fill the entire kiosk display
   - **Enable/disable images** - Use the "Show" checkbox on each image card
   - **Create and manage Atmospheres** - Organize themes into atmospheres
   - **Create and manage Themes** - Organize images into themes
   - Configure slideshow intervals per theme/atmosphere
   - Remote control the kiosk display
   - Delete images
   - View current images (shows cropped thumbnails in randomized order)

2. **Kiosk Display**: `http://<raspberry-pi-ip>/view`
   - Main slideshow display
   - Optimized for fullscreen viewing
   - Only shows enabled images in random order

3. **Upload Page**: `http://<raspberry-pi-ip>/upload`
   - Dedicated upload interface
   - Drag-and-drop support
   - Newly uploaded images automatically switch the kiosk display for preview

### Firefox Kiosk Mode

To run Firefox in fullscreen kiosk mode on your Raspberry Pi:

#### Option 1: Command Line

```bash
firefox --kiosk http://localhost/view
```

#### Option 2: Using a Startup Script

Create a startup script at `/home/pi/start-kiosk.sh`:

```bash
#!/bin/bash

# Wait for the server to start
sleep 5

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Start Firefox in kiosk mode
firefox --kiosk http://localhost/view
```

Make it executable:

```bash
chmod +x /home/pi/start-kiosk.sh
```

#### Option 3: Auto-start on Boot (Recommended)

Use the automated installation script to set up both the Flask server and Firefox to start automatically at boot:

```bash
cd ~/kiosk_images
sudo ./install-autostart.sh
```

This installs two systemd services:
- **kiosk-display.service** - Flask server (starts first)
  - Automatically kills any process using port 80 before starting
  - Binds to port 80 using Linux capabilities (no root required)
- **kiosk-firefox.service** - Firefox in kiosk mode (starts after server is ready)
  - Uses **start-firefox-kiosk.sh** for automatic Firefox profile management
  - Automatically cleans up old Firefox processes and profiles to prevent corruption
  - Creates fresh Firefox profile on each start with kiosk-optimized settings
  - Waits for server to respond before launching Firefox
  - Disables screen blanking and hides cursor

**Manual Installation** (if you prefer to install manually):

1. Copy both service files:

```bash
cd ~/kiosk_images
sudo cp kiosk-display.service /etc/systemd/system/
sudo cp kiosk-firefox.service /etc/systemd/system/
sudo systemctl daemon-reload
```

2. Enable and start services:

```bash
sudo systemctl enable kiosk-display.service
sudo systemctl enable kiosk-firefox.service
sudo systemctl start kiosk-display.service
sudo systemctl start kiosk-firefox.service
```

3. Check status:

```bash
sudo systemctl status kiosk-display.service
sudo systemctl status kiosk-firefox.service
```

**Useful Commands:**

```bash
# View logs
sudo journalctl -u kiosk-display -f
sudo journalctl -u kiosk-firefox -f

# Restart services
sudo systemctl restart kiosk-display.service
sudo systemctl restart kiosk-firefox.service

# Stop services
sudo systemctl stop kiosk-firefox.service
sudo systemctl stop kiosk-display.service

# Disable autostart
sudo systemctl disable kiosk-firefox.service
sudo systemctl disable kiosk-display.service
```

## Configuration

### Slideshow Settings

Configure settings through the management interface at `/`, or edit `settings.json` directly:

```json
{
  "interval": 3600,
  "check_interval": 2,
  "enabled_images": {},
  "dissolve_enabled": true,
  "themes": {
    "All Images": {"name": "All Images", "created": 1234567890, "interval": 3600},
    "Nature": {"name": "Nature", "created": 1234567891, "interval": 3600},
    "Urban": {"name": "Urban", "created": 1234567892, "interval": 1800}
  },
  "image_themes": {
    "photo1.jpg": ["Nature"],
    "photo2.jpg": ["Nature", "Urban"],
    "photo3.jpg": ["Urban"]
  },
  "active_theme": "All Images",
  "atmospheres": {
    "Evening": {"name": "Evening", "created": 1234567893, "interval": 1800},
    "Morning": {"name": "Morning", "created": 1234567894, "interval": 3600}
  },
  "atmosphere_themes": {
    "Evening": ["Nature", "Urban"],
    "Morning": ["Nature"]
  },
  "active_atmosphere": null,
  "shuffle_id": 0.123456789,
  "image_crops": {
    "photo1.jpg": {
      "x": 0,
      "y": 0,
      "width": 1690,
      "height": 1885,
      "imageWidth": 1690,
      "imageHeight": 3000
    }
  }
}
```

- **interval** (I): Current slideshow interval in seconds (synced with active theme/atmosphere interval)
- **check_interval** (C): Time in seconds between checks for changes (default: 2)
- **dissolve_enabled**: Smooth dissolve transition between images (always true)
- **themes**: Dictionary of defined themes, each with its own interval in seconds
  - **"All Images"**: Permanent default theme (cannot be deleted), shows all enabled images
- **image_themes**: Mapping of image names to their theme lists
- **active_theme**: Currently active theme (defaults to "All Images")
- **atmospheres**: Dictionary of defined atmospheres, each with its own interval
- **atmosphere_themes**: Mapping of atmosphere names to theme lists
- **active_atmosphere**: Currently active atmosphere (null if none active)
- **shuffle_id**: Random seed for image ordering (regenerates on theme/atmosphere change)
- **image_crops**: Mapping of image names to crop regions (x, y, width, height in original image coordinates)

### Atmospheres

Atmospheres provide a hierarchical organization layer above themes (Atmospheres → Themes → Images):

1. **Create atmospheres** - Click "New Atmosphere", enter name, press Enter
2. **Assign themes** - Click the "Themes" button on an atmosphere badge to select which themes belong to it
3. **Set interval** - Click the interval display to edit the slideshow duration for that atmosphere
4. **Activate atmosphere** - Click the atmosphere name to activate it and display all images from all its themes
5. **Mutual exclusivity** - Activating an atmosphere deselects any active theme, and vice versa
6. **Random ordering** - Each atmosphere displays images in a random order that changes every time you switch

When an atmosphere is active:
- All images from all themes in that atmosphere are shown
- The atmosphere's interval setting is used for the slideshow
- Images display in randomized order

### Themes

Organize your images into themes for different occasions or categories:

1. **Default theme** - "All Images" is a permanent theme that shows all enabled images (cannot be deleted)
2. **Create themes** - Enter a theme name and click "New Theme" (default interval: 60 minutes)
3. **Set theme interval** - Each theme has its own slideshow interval. Click to edit it
4. **Assign images** - Use the dropdown on each image card to add it to themes
5. **Multiple themes** - Images can belong to multiple themes
6. **Remove from theme** - Click the "✕" on a theme tag to remove the image from that theme
7. **Select active theme** - Click a theme name to activate it
8. **Random ordering** - Each theme displays images in a random order that changes every time you switch

When a theme is active:
- **"All Images" theme**: Shows all enabled images regardless of theme assignments
- **Other themes**: Only enabled images belonging to that theme will appear in the slideshow
- The slideshow uses the active theme's interval setting
- Images display in randomized order

### Image Randomization

Images are displayed in random order, with the following behavior:

- **Order changes** - Switching to a different theme or atmosphere generates a new random order
- **Order persists** - The same theme/atmosphere always shows the same random order (within a session)
- **Kiosk syncs automatically** - The kiosk display matches the order shown in Current Images
- **All images included** - Every enabled image appears exactly once (no duplicates, no missing images)

### Image Cropping

Crop images to display specific regions on the kiosk:

1. **Open crop editor** - Click the "Crop" button on any image card
2. **Select region** - Use the interactive cropper to select the desired area
   - Drag corners to resize the crop region
   - Drag inside the box to move it
   - Free aspect ratio - crop any shape
3. **Save crop** - Click "Save Crop" to apply (or "Clear Crop" to remove)
4. **Automatic scaling** - The cropped region automatically scales to fill the entire 2560x2880 display
5. **Preview** - The management interface shows cropped thumbnails matching what appears on the kiosk

Crop behavior:
- The selected region is scaled to fill the screen completely (cover mode)
- Black bars appear on only one dimension (either top/bottom OR left/right, never both)
- Changes apply automatically within 2 seconds via the smart reload system
- Crops are stored per-image and persist across restarts

### Auto-Preview on Upload

When you upload a new image via the upload page:

1. The image is automatically assigned to the currently active theme (if not "All Images")
2. A "jump" command is sent to the kiosk display
3. The kiosk switches to the newly uploaded image within 500ms
4. This allows immediate review of uploads

### Smart Reload Algorithm

The kiosk uses an intelligent reload system:

1. Every **C seconds** (check_interval = 2), the kiosk checks:
   - The list of enabled images (vector **V**)
   - The slideshow interval setting
   - Image crop data
   - The shuffle_id (detects theme/atmosphere changes)
2. It compares the current vector **V** with the previous vector **VP**
3. It compares the current interval with the previous interval
4. It compares the current crop data with the previous crop data
5. It compares the current shuffle_id with the previous shuffle_id
6. If anything changed, the slideshow reloads with the new settings
7. If nothing changed, the slideshow continues uninterrupted

This means:
- No unnecessary reloads when nothing changes
- Smooth playback continues as long as settings are stable
- Automatic updates when you enable/disable images in the management interface
- Automatic updates when you change the slideshow interval
- Automatic updates when you crop or modify image crops
- Automatic updates when you switch themes or atmospheres (with new random order)
- Changes apply within 2 seconds

### Image Scaling

The kiosk display supports two scaling modes:

1. **Contain Mode** (default): Images fit within the viewport while maintaining aspect ratio
2. **Cover Mode**: Images fill the entire screen, potentially cropping edges

Toggle between modes by pressing `F` while viewing the kiosk display.

## Keyboard Controls (Kiosk Display)

- `Space` or `Right Arrow`: Next image
- `Left Arrow`: Previous image
- `F`: Toggle between contain/cover scaling modes
- `R`: Reload page and refresh image list

## Remote Control (Web-Based)

Since the kiosk is a remote display without a keyboard, you can control it from any device on your network via the management interface at `/`.

**Available Controls:**
- **Previous** - Go to previous image (instant transition)
- **Next** - Go to next image (instant transition)
- **Pause** - Pause the slideshow
- **Play** - Resume the slideshow
- **Reload** - Refresh the kiosk display
- **Click on any image** - Jump directly to that image in the slideshow (instant transition)

**Real-Time Communication**: The system uses WebSockets for instant communication between the management interface and kiosk display. Commands execute immediately with 0ms latency. Automatic slideshow transitions still use smooth dissolve effects, while manual controls (next/prev/jump) use instant transitions.

## API Endpoints

**Images:**
- `GET /api/images` - List all images (use `?enabled_only=true` to filter)
- `POST /api/images` - Upload a new image
- `POST /api/images/<filename>/toggle` - Toggle enabled state of an image
- `DELETE /api/images/<filename>` - Delete an image
- `POST /api/images/<filename>/themes` - Update image themes

**Settings:**
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings

**Remote Control:**
- `POST /api/control/send` - Send command to kiosk (commands: next, prev, pause, play, reload, jump)
  - For jump command, include `image_name` parameter: `{"command": "jump", "image_name": "photo.jpg"}`
- `GET /api/control/poll` - Poll for commands (legacy, replaced by WebSockets)

**WebSocket Events:**
- `connect` - Client connected to server
- `disconnect` - Client disconnected from server
- `send_command` - Send remote command (emitted by client)
- `remote_command` - Receive remote command (broadcasted to all clients)
- `log_debug` - Send debug message from kiosk (emitted by client)
- `debug_message` - Receive debug message (broadcasted to all clients)
- `settings_update` - Settings changed (broadcasted to all clients)
- `image_list_changed` - Image list changed (broadcasted to all clients)

**Themes:**
- `GET /api/themes` - List all themes and active theme
- `POST /api/themes` - Create a new theme (`{"name": "Theme Name"}`)
- `DELETE /api/themes/<theme_name>` - Delete a theme
- `POST /api/themes/active` - Set active theme (`{"theme_name": "Theme Name"}`)
- `POST /api/themes/<theme_name>/interval` - Update theme interval (seconds)

**Atmospheres:**
- `GET /api/atmospheres` - List all atmospheres
- `POST /api/atmospheres` - Create a new atmosphere (`{"name": "Atmosphere Name"}`)
- `DELETE /api/atmospheres/<atmosphere_name>` - Delete an atmosphere
- `POST /api/atmospheres/active` - Set active atmosphere (`{"atmosphere_name": "Atmosphere Name"}` or null)
- `POST /api/atmospheres/<atmosphere_name>/interval` - Update atmosphere interval (seconds)
- `POST /api/atmospheres/<atmosphere_name>/themes` - Update themes in atmosphere (`{"themes": ["Theme1", "Theme2"]}`)

## Convenience Scripts

- **start-kiosk.sh** - Start the kiosk (cleans up previous instances, starts server, launches Firefox)
- **stop-kiosk.sh** - Stop all kiosk processes

Usage:
```bash
./start-kiosk.sh   # Start everything
./stop-kiosk.sh    # Stop everything
```

## File Structure

```
kiosk_images/
├── app.py                     # Flask server
├── requirements.txt           # Python dependencies
├── settings.json              # Configuration (auto-generated)
├── images/                    # Uploaded images (auto-generated)
├── venv/                      # Python virtual environment
├── start-kiosk.sh             # Start script (cleans up + starts)
├── start-firefox-kiosk.sh     # Firefox startup with profile management
├── stop-kiosk.sh              # Stop script
├── kiosk-display.service      # Systemd service file for Flask
├── kiosk-firefox.service      # Systemd service file for Firefox
├── install-autostart.sh       # Systemd installer
├── README.md                  # This file
├── ARCHITECTURE.md            # Architecture documentation
├── QUICKSTART.md              # Quick start guide
└── templates/
    ├── kiosk.html             # Main kiosk display
    ├── manage.html            # Management interface
    └── upload.html            # Upload interface
```

## Supported Image Formats

- PNG
- JPG/JPEG
- GIF
- WebP
- BMP

## Troubleshooting

### Images not displaying

1. Check that images are uploaded via the management interface
2. Verify images are enabled (checkbox is checked)
3. Verify the Flask server is running
4. Check browser console for errors (F12)

### Scaling issues

- Press `F` to toggle between contain and cover modes
- Images are automatically scaled to fit 2560x2880 resolution
- Aspect ratio is preserved in contain mode, may be altered in cover mode

### Server not accessible

1. Check that the Flask server is running: `sudo systemctl status kiosk-display`
2. Verify firewall settings allow port 80
3. Use `http://localhost` on the Pi itself, or `http://<pi-ip>` from other devices

### Auto-start not working

1. Check systemd service status: `sudo systemctl status kiosk-display`
2. View logs: `sudo journalctl -u kiosk-display -f`
3. View Firefox logs: `sudo journalctl -u kiosk-firefox -f`
4. Verify X11 mode (not Wayland): `echo $WAYLAND_DISPLAY` should be empty when logged in locally
5. Check that start-firefox-kiosk.sh is executable: `ls -la ~/kiosk_images/start-firefox-kiosk.sh`

### Firefox not displaying or profile errors

1. **Automatic fix**: The service now automatically cleans Firefox profiles on each start
2. **Manual cleanup** (if needed):
   ```bash
   sudo systemctl stop kiosk-firefox
   rm -rf ~/.mozilla/firefox
   sudo systemctl start kiosk-firefox
   ```
3. Check Firefox logs: `sudo journalctl -u kiosk-firefox -f`
4. Verify X11 is running: `ps aux | grep -E 'X|xinit'`
5. Test manually: `DISPLAY=:0 firefox --kiosk http://localhost/view`

### Wayland compatibility issues

If you see errors like "Failed connect to PipeWire" or Firefox doesn't display:

1. **Switch to X11 mode** (recommended):
   ```bash
   sudo raspi-config
   # Navigate to: Advanced Options > Wayland > Select "X11"
   sudo reboot
   ```

2. **Or modify for Wayland**: Edit `kiosk-firefox.service` to use Wayland environment variables (see ARCHITECTURE.md for details)

### Themes/Atmospheres not filtering

1. Verify the theme or atmosphere is activated (badge shows as active)
2. Check images have themes assigned
3. Look at API response: `/api/images?enabled_only=true`
4. Check settings.json for correct theme/atmosphere mappings

## Performance Tips

- Use optimized image formats (WebP for smaller file sizes)
- Pre-resize large images before uploading for better performance
- Set appropriate slideshow intervals (longer for slower Pi models)
- The page automatically checks for changes every 2 seconds

## Security Considerations

- This server is designed for local network use
- No authentication is included by default
- Do not expose directly to the internet without adding authentication
- Consider using a reverse proxy (nginx) for production deployments

## License

This project is provided as-is for personal and educational use.
