# Kiosk Image Display System

A web-based digital art display system for Raspberry Pi, optimized for a 2560x2880 portrait monitor. Display images and videos in a beautiful slideshow with remote control from any device on your network.

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Web Interfaces](#web-interfaces)
- [Core Concepts](#core-concepts)
- [Configuration Guide](#configuration-guide)
- [Remote Control](#remote-control)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)

---

## Quick Start

```bash
# 1. Copy to Raspberry Pi
scp -r kiosk_images pi@raspberrypi.local:~/

# 2. SSH into Pi and set up
ssh pi@raspberrypi.local
cd ~/kiosk_images
sudo apt install python3-venv python3-full -y
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install auto-start services
sudo ./install-autostart.sh

# 4. Access from any device on your network
# Management: http://raspberrypi.local/
# Display:    http://raspberrypi.local/view
```

---

## Features

### Display Features
| Feature | Description |
|---------|-------------|
| **Portrait Display** | Optimized for 2560x2880 portrait monitors |
| **Smooth Transitions** | 0.8s dissolve fade between images |
| **Image Cropping** | Select specific regions to display |
| **Video Support** | Play YouTube videos in the slideshow |
| **Smart Reload** | Detects changes without interrupting playback |
| **Hidden Cursor** | Clean display without mouse pointer |

### Organization Features
| Feature | Description |
|---------|-------------|
| **Themes** | Organize images into categories |
| **Atmospheres** | Group themes together for moods |
| **Day Scheduling** | Auto-switch atmospheres by time of day |
| **Randomization** | Images shuffle with each theme switch |

### Management Features
| Feature | Description |
|---------|-------------|
| **Web Interface** | Manage everything from your phone/tablet |
| **Remote Control** | Next/prev/pause without touching the kiosk |
| **Click-to-Jump** | Tap any thumbnail to display it |
| **Auto-Preview** | New uploads instantly show on display |
| **Backup/Restore** | Save and restore complete configurations |
| **Debug Console** | Real-time logs for troubleshooting |

### Integration Features
| Feature | Description |
|---------|-------------|
| **Museum Search** | Find art from major museum collections |
| **YouTube Videos** | Add videos by URL |
| **WebSocket** | Real-time communication |
| **REST API** | Full programmatic control |

---

## Requirements

### Hardware
- Raspberry Pi 4 (recommended) or compatible
- Monitor: 2560x2880 portrait orientation
- Network connection (WiFi or Ethernet)

### Software
- Raspberry Pi OS (X11 mode - not Wayland)
- Python 3.7+
- Firefox browser

### System Packages
```bash
# Required
sudo apt install python3-venv python3-full firefox-esr unclutter curl -y

# For video support
sudo apt install mpv -y
pip install yt-dlp
```

### Python Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.0 | Web framework |
| flask-socketio | 5.3.6 | Real-time WebSocket |
| Werkzeug | 3.0.1 | WSGI utilities |
| requests | 2.31.0 | HTTP client |
| Pillow | >=10.0.0 | Image processing |

> **Important**: This system requires X11. If using Raspberry Pi OS with Wayland:
> ```bash
> sudo raspi-config
> # Navigate to: Advanced Options > Wayland > Select "X11"
> sudo reboot
> ```

---

## Installation

### Step 1: Copy Files to Raspberry Pi

```bash
# From your computer
scp -r kiosk_images pi@<raspberry-pi-ip>:~/
```

### Step 2: Set Up Python Environment

```bash
# On the Raspberry Pi
cd ~/kiosk_images

# Install system dependencies
sudo apt install python3-venv python3-full -y

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Install Auto-Start Services (Recommended)

```bash
sudo ./install-autostart.sh
```

This creates two systemd services:

| Service | Purpose |
|---------|---------|
| **kiosk-display.service** | Flask server on port 80 |
| **kiosk-firefox.service** | Firefox in kiosk mode |

### Step 4: Verify Installation

```bash
# Check services are running
sudo systemctl status kiosk-display.service
sudo systemctl status kiosk-firefox.service

# View logs if needed
sudo journalctl -u kiosk-display -f
```

### Manual Start (Development)

```bash
# Start server manually
cd ~/kiosk_images
source venv/bin/activate
python app.py

# In another terminal, start Firefox
firefox --kiosk http://localhost/view
```

---

## Web Interfaces

Access from any device on your network:

| Interface | URL | Purpose |
|-----------|-----|---------|
| **Management** | `http://<pi-ip>/` | Main control panel |
| **Kiosk Display** | `http://<pi-ip>/view` | Slideshow display |
| **Upload** | `http://<pi-ip>/upload` | Image upload |
| **Search Art** | `http://<pi-ip>/search` | Museum search |
| **Extra Images** | `http://<pi-ip>/extra-images` | Staging area |
| **Debug** | `http://<pi-ip>/debug` | Log viewer |
| **Backup** | `http://<pi-ip>/backup` | Backup management |
| **Remote** | `http://<pi-ip>/remote` | Simple remote |

### Management Interface (/)

The main control panel provides:

- **Image Management** - Enable/disable, crop, assign themes
- **Theme Configuration** - Create and manage themes
- **Atmosphere Setup** - Group themes into atmospheres
- **Day Scheduling** - Configure automatic time-based switching
- **Remote Control** - Next, prev, pause, play buttons
- **Current Images** - View active slideshow order
- **Debug Console** - Real-time log messages

### Kiosk Display (/view)

The slideshow display supports:

| Key | Action |
|-----|--------|
| `Space` / `→` | Next image |
| `←` | Previous image |
| `F` | Toggle fill/fit mode |
| `R` | Reload display |

---

## Core Concepts

### Organization Hierarchy

```
Day Schedule
    └── Time Period (1-12)
            └── Atmosphere(s)
                    └── Theme(s)
                            └── Image(s)
```

### Images

- **UUID Filenames**: All images get unique names (e.g., `ab4ab3c1-5c16.jpg`)
- **Enable/Disable**: Control which images appear in slideshow
- **Cropping**: Select specific regions to display
- **Multiple Themes**: Images can belong to many themes

### Themes

Organize images into categories:

```
Theme: "Nature"
├── forest.jpg
├── mountains.jpg
└── ocean.jpg

Theme: "Portraits"
├── portrait1.jpg
└── portrait2.jpg
```

- **"All Images"** theme always exists (cannot be deleted)
- Each theme has its own slideshow interval
- Images can belong to multiple themes
- Switching themes reshuffles the display order

### Atmospheres

Group multiple themes together for moods:

```
Atmosphere: "Morning"
├── Theme: "Nature"
└── Theme: "Calm"

Atmosphere: "Evening"
├── Theme: "Portraits"
└── Theme: "Dark Art"
```

- **"All Images"** atmosphere always exists
- Atmosphere interval overrides theme intervals
- Combines all images from all included themes
- Perfect for day scheduling

### Day Scheduling

Automatically switch atmospheres throughout the day:

```
Time Periods (2-hour blocks, 12-hour mirroring):

Period 1:  6 AM -  8 AM  ←→  Period 7:  6 PM -  8 PM
Period 2:  8 AM - 10 AM  ←→  Period 8:  8 PM - 10 PM
Period 3: 10 AM - 12 PM  ←→  Period 9: 10 PM - 12 AM
Period 4: 12 PM -  2 PM  ←→  Period 10: 12 AM -  2 AM
Period 5:  2 PM -  4 PM  ←→  Period 11:  2 AM -  4 AM
Period 6:  4 PM -  6 PM  ←→  Period 12:  4 AM -  6 AM
```

- Configure 6 periods; the other 6 mirror automatically
- Assign different atmospheres to each period
- System automatically switches when time period changes
- Green border highlights current period in UI

### Interval Precedence

The slideshow interval is determined by priority:

1. **Day Scheduling** → First atmosphere's interval
2. **Active Atmosphere** → Atmosphere's interval
3. **Active Theme** → Theme's interval
4. **Default** → Global interval setting

---

## Configuration Guide

### Image Cropping

1. Click **Crop** on any image card
2. Drag corners to resize selection
3. Toggle **Aspect Lock** for display ratio (2560/2880)
4. Click **Save Crop** to apply

Crop behavior:
- Locked aspect ratio maintains display proportions
- Unlocked allows free-form selection
- Cropped region fills entire screen (no black bars)
- Changes apply within 2 seconds

### Video Support

1. Enter YouTube URL in "Add Video" section
2. Click **Add Video**
3. Thumbnails generate automatically on first play
4. Videos appear in slideshow with images
5. Auto-transition after interval expires

Video controls:
- Play/Stop from management interface
- Assign to themes like images
- mpv handles fullscreen playback

### Backup and Restore

Backups include:
- All images and videos
- Theme and atmosphere configurations
- Day scheduling settings
- Image crops and enabled states
- Complete settings.json

```bash
# Backups stored in
~/kiosk_images/backups/
```

### Smart Reload System

The kiosk checks for changes every 2 seconds:

1. Fetches current enabled images
2. Compares with previous list
3. Checks interval, crops, shuffle_id
4. Only reloads if something changed

This means:
- Smooth playback when nothing changes
- Automatic updates when you modify settings
- No manual refresh needed
- Changes apply within 2 seconds

---

## Remote Control

### Web-Based Controls

Available from the management interface:

| Button | Action |
|--------|--------|
| **◀ Prev** | Previous image (instant) |
| **▶ Next** | Next image (instant) |
| **⏸ Pause** | Pause slideshow |
| **▶ Play** | Resume slideshow |
| **↻ Reload** | Refresh display |

### Click-to-Jump

Click any thumbnail in "Current Images" to immediately display it on the kiosk.

### WebSocket Communication

Commands execute instantly via WebSocket:
- 0ms latency for manual controls
- Real-time settings synchronization
- Live debug log streaming

---

## API Reference

### Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/images` | List all images |
| GET | `/api/images?enabled_only=true` | List enabled (filtered) |
| POST | `/api/images` | Upload image |
| DELETE | `/api/images/<name>` | Delete image |
| POST | `/api/images/<name>/toggle` | Toggle enabled |
| POST | `/api/images/<name>/themes` | Update themes |

### Themes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/themes` | List all themes |
| POST | `/api/themes` | Create theme |
| DELETE | `/api/themes/<name>` | Delete theme |
| POST | `/api/themes/active` | Set active theme |
| POST | `/api/themes/<name>/interval` | Update interval |

### Atmospheres

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/atmospheres` | List all atmospheres |
| POST | `/api/atmospheres` | Create atmosphere |
| DELETE | `/api/atmospheres/<name>` | Delete atmosphere |
| POST | `/api/atmospheres/active` | Set active |
| POST | `/api/atmospheres/<name>/themes` | Assign themes |
| POST | `/api/atmospheres/<name>/interval` | Update interval |

### Day Scheduling

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/day/status` | Get status |
| POST | `/api/day/enable` | Enable scheduling |
| POST | `/api/day/disable` | Disable scheduling |
| POST | `/api/day/times/<id>/atmospheres` | Set period atmospheres |

### Remote Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/control/send` | Send command |
| GET | `/api/control/poll` | Poll for commands |

Commands: `next`, `prev`, `pause`, `play`, `reload`, `jump`

### Videos

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/videos` | List videos |
| POST | `/api/videos` | Add video URL |
| DELETE | `/api/videos/<id>` | Delete video |
| POST | `/api/videos/<id>/toggle` | Toggle enabled |
| POST | `/api/videos/execute-mpv` | Start playback |
| POST | `/api/videos/stop-mpv` | Stop playback |

### WebSocket Events

| Event | Direction | Purpose |
|-------|-----------|---------|
| `remote_command` | Server → Client | Execute command |
| `settings_update` | Server → Client | Settings changed |
| `image_list_changed` | Server → Client | Images modified |
| `debug_message` | Server → Client | Log entry |
| `send_command` | Client → Server | Send command |
| `log_debug` | Client → Server | Submit log |

---

## Testing

The project includes 119 automated tests.

### Running Tests

```bash
cd kiosk-tests

# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run by category
pytest tests/unit/           # 14 unit tests
pytest tests/integration/    # 55 integration tests
pytest tests/e2e/            # 50 end-to-end tests

# Verbose output
pytest -v
```

### Test Coverage

| Category | Count | Coverage |
|----------|-------|----------|
| Unit | 14 | API endpoints, cleanup safety |
| Integration | 55 | Themes, atmospheres, day scheduling, videos |
| E2E | 50 | Browser automation, WebSocket, display |
| **Total** | **119** | **100% pass rate** |

### Test Configuration

Tests connect to the device specified in `kiosk-tests/device.txt`:

```
hostname=raspberrypi.local
username=<your-username>
password=<your-password>
```

> **Note**: `device.txt` is gitignored and should never be committed.

---

## Troubleshooting

### Images Not Displaying

1. Verify images are enabled (checkbox checked)
2. Check Flask server is running: `sudo systemctl status kiosk-display`
3. Open browser console (F12) for errors
4. Check API response: `curl http://localhost/api/images?enabled_only=true`

### Server Not Accessible

1. Check service status: `sudo systemctl status kiosk-display`
2. Verify port 80 is open: `sudo ss -tlnp | grep :80`
3. Check firewall settings
4. Try `http://localhost` on the Pi itself

### Firefox Not Starting

1. Check service: `sudo systemctl status kiosk-firefox`
2. View logs: `sudo journalctl -u kiosk-firefox -f`
3. Manual cleanup:
   ```bash
   sudo systemctl stop kiosk-firefox
   rm -rf ~/.mozilla/firefox
   sudo systemctl start kiosk-firefox
   ```
4. Verify X11: `echo $WAYLAND_DISPLAY` should be empty

### Auto-Start Not Working

1. Check both services:
   ```bash
   sudo systemctl status kiosk-display.service
   sudo systemctl status kiosk-firefox.service
   ```
2. Verify X11 mode (not Wayland):
   ```bash
   sudo raspi-config
   # Advanced Options > Wayland > X11
   ```
3. Check script permissions:
   ```bash
   ls -la ~/kiosk_images/start-firefox-kiosk.sh
   chmod +x ~/kiosk_images/start-firefox-kiosk.sh
   ```

### Day Scheduling Not Switching

1. Verify day scheduling is enabled in UI
2. Check current time period: `curl http://localhost/api/day/status`
3. Verify atmospheres are assigned to time periods
4. Wait up to 60 seconds for hour boundary detection

### Theme/Atmosphere Not Filtering

1. Check theme/atmosphere is activated (highlighted in UI)
2. Verify images have themes assigned
3. Check API: `curl http://localhost/api/images?enabled_only=true`
4. Review `settings.json` for correct mappings

---

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file - user guide |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Feature requirements |
| [TEST.md](TEST.md) | Test documentation |
| [TEST_MODE.md](TEST_MODE.md) | Test mode API |
| [QUICKSTART.md](QUICKSTART.md) | Quick start guide |
| [CLAUDE.md](CLAUDE.md) | Developer instructions |

---

## File Structure

```
kiosk_images/
├── app.py                      # Flask backend
├── painting_searcher.py        # Museum API client
├── requirements.txt            # Python dependencies
│
├── templates/                  # HTML templates
│   ├── kiosk.html             # Slideshow display
│   ├── manage.html            # Management interface
│   ├── upload.html            # Image upload
│   ├── search.html            # Art search
│   ├── extra-images.html      # Extra images
│   ├── debug.html             # Debug console
│   ├── backup.html            # Backup management
│   ├── remote.html            # Simple remote
│   └── loading.html           # Video loading
│
├── images/                    # Image storage (gitignored)
├── EXTRA_IMAGES/              # Staging folder
├── thumbnails/                # Video thumbnails
├── backups/                   # Backup archives
├── settings.json              # Configuration (gitignored)
│
├── kiosk-display.service      # Flask systemd service
├── kiosk-firefox.service      # Firefox systemd service
├── kiosk.target               # Composite service
├── install-autostart.sh       # Service installer
├── start-kiosk.sh             # Development start
├── start-firefox-kiosk.sh     # Firefox launcher
├── stop-kiosk.sh              # Stop script
│
├── kiosk-tests/               # Test suite
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   └── conftest.py
│
└── venv/                      # Python environment (gitignored)
```

---

## Performance Tips

- Use **WebP** format for smaller file sizes
- Pre-resize large images before uploading
- Set longer intervals on slower Pi models
- The system checks for changes every 2 seconds automatically

---

## Security Considerations

- **Local Network Only** - No authentication included
- **Do Not Expose to Internet** without adding authentication
- **Port 80 Binding** - Uses Linux capabilities (no root needed)
- **File Validation** - 50MB max, allowed extensions only
- Consider using nginx reverse proxy for production

---

## Supported Formats

### Images
- PNG, JPG/JPEG, GIF, WebP, BMP

### Videos
- YouTube URLs (via yt-dlp)
- Played with mpv in fullscreen

---

## License

This project is provided as-is for personal and educational use.
