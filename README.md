# Kiosk Image Display System

A web-based kiosk system for displaying images in slideshow mode, optimized for Raspberry Pi with a 2560x2880 portrait monitor.

## Features

- Web-based image upload and management
- **Image cropping** - Crop images to select specific regions that fill the entire kiosk display
- **Enable/disable individual images** - Control which images appear in the slideshow with checkboxes
- **Themes** - Organize images into multiple themes with per-theme intervals; images can belong to multiple themes
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

- Raspberry Pi running Raspberry Pi OS
- Python 3.7 or higher
- Firefox browser
- unclutter (optional, for hiding mouse cursor system-wide)
- Monitor: 2560x2880 (portrait orientation)

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
   - Configure slideshow interval
   - Remote control the kiosk display
   - Delete images
   - View current images (shows cropped thumbnails)

2. **Kiosk Display**: `http://<raspberry-pi-ip>/view`
   - Main slideshow display
   - Optimized for fullscreen viewing
   - Only shows enabled images

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
- **kiosk-firefox.service** - Firefox in kiosk mode (starts after server is ready)

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

- **interval** (I): Current slideshow interval in seconds (synced with active theme's interval)
- **check_interval** (C): Time in seconds between checks for changes (default: 2)
- **dissolve_enabled**: Smooth dissolve transition between images (always true)
- **themes**: Dictionary of defined themes, each with its own interval in seconds
  - **"All Images"**: Permanent default theme (cannot be deleted), shows all enabled images
- **image_themes**: Mapping of image names to their theme lists
- **active_theme**: Currently active theme (defaults to "All Images")
- **image_crops**: Mapping of image names to crop regions (x, y, width, height in original image coordinates)

### Themes

Organize your images into themes for different occasions or categories:

1. **Default theme** - "All Images" is a permanent theme that shows all enabled images (cannot be deleted)
2. **Create themes** - Enter a theme name and click "Create Theme" (default interval: 60 minutes)
3. **Set theme interval** - Each theme has its own slideshow interval. Edit it in the theme's settings and click "Save"
4. **Assign images** - Use the dropdown on each image card to add it to themes
5. **Multiple themes** - Images can belong to multiple themes
6. **Remove from theme** - Click the "✕" on a theme tag to remove the image from that theme
7. **Select active theme** - Use the "Active Theme" dropdown to choose which theme to display

When a theme is active:
- **"All Images" theme**: Shows all enabled images regardless of theme assignments
- **Other themes**: Only enabled images belonging to that theme will appear in the slideshow
- The slideshow uses the active theme's interval setting

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

### Smart Reload Algorithm

The kiosk uses an intelligent reload system:

1. Every **C seconds** (check_interval = 2), the kiosk checks:
   - The list of enabled images (vector **V**)
   - The slideshow interval setting
   - Image crop data
2. It compares the current vector **V** with the previous vector **VP**
3. It compares the current interval with the previous interval
4. It compares the current crop data with the previous crop data
5. If anything changed, the slideshow reloads from the beginning with the new settings
6. If nothing changed, the slideshow continues uninterrupted

This means:
- No unnecessary reloads when nothing changes
- Smooth playback continues as long as settings are stable
- Automatic updates when you enable/disable images in the management interface
- Automatic updates when you change the slideshow interval
- Automatic updates when you crop or modify image crops
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
- **Previous** - Go to previous image
- **Next** - Go to next image
- **Pause** - Pause the slideshow
- **Play** - Resume the slideshow
- **Reload** - Refresh the kiosk display
- **Click on any image** - Jump directly to that image in the slideshow

The kiosk polls for commands every 500ms, so commands execute almost instantly. Clicking on any image thumbnail in the "Current Images" section will immediately switch the kiosk display to that image.

## API Endpoints

**Images:**
- `GET /api/images` - List all images (use `?enabled_only=true` to filter)
- `POST /api/images` - Upload a new image
- `POST /api/images/<filename>/toggle` - Toggle enabled state of an image
- `DELETE /api/images/<filename>` - Delete an image

**Settings:**
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings

**Remote Control:**
- `POST /api/control/send` - Send command to kiosk (commands: next, prev, pause, play, reload, jump)
  - For jump command, include `image_name` parameter: `{"command": "jump", "image_name": "photo.jpg"}`
- `GET /api/control/poll` - Poll for commands (used by kiosk display)

**Themes:**
- `GET /api/themes` - List all themes and active theme
- `POST /api/themes` - Create a new theme (`{"name": "Theme Name"}`)
- `DELETE /api/themes/<theme_name>` - Delete a theme
- `POST /api/themes/active` - Set active theme (`{"theme_name": "Theme Name"}` or `{"theme_name": null}`)
- `POST /api/images/<filename>/themes` - Update image themes (`{"themes": ["Theme1", "Theme2"]}`)

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
├── app.py                   # Flask server
├── requirements.txt         # Python dependencies
├── settings.json           # Configuration (auto-generated)
├── images/                 # Uploaded images (auto-generated)
├── venv/                   # Python virtual environment
├── start-kiosk.sh          # Start script (cleans up + starts)
├── stop-kiosk.sh           # Stop script
├── kiosk-display.service   # Systemd service file
├── QUICKSTART.md           # Quick start guide
└── templates/
    ├── kiosk.html          # Main kiosk display
    └── manage.html         # Management interface
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
2. Verify the Flask server is running
3. Check browser console for errors (F12)

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
3. Verify autostart configuration in `/etc/xdg/lxsession/LXDE-pi/autostart`

## Performance Tips

- Use optimized image formats (WebP for smaller file sizes)
- Pre-resize large images before uploading for better performance
- Set appropriate slideshow intervals (longer for slower Pi models)
- The page automatically reloads every 5 minutes to check for new images

## Security Considerations

- This server is designed for local network use
- No authentication is included by default
- Do not expose directly to the internet without adding authentication
- Consider using a reverse proxy (nginx) for production deployments

## License

This project is provided as-is for personal and educational use.
