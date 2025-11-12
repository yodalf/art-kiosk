# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git & GitHub Workflow

**IMPORTANT**: Never push to GitHub without explicit permission from the user.

- Always commit changes locally when making updates
- Wait for explicit "push" or "push to github" instruction before running `git push`
- This applies to all future sessions and conversations

## Project Overview

Art Kiosk is a web-based image display system for Raspberry Pi with a 2560x2880 portrait monitor. It provides:
- Flask backend (port 80) for image management and settings
- Two HTML frontends: `/view` (kiosk display) and `/` (management interface)
- Theme system allowing images to belong to multiple themes
- Remote control via polling (500ms) for keyboard-less operation
- Smart reload algorithm that checks every 2 seconds (C interval) for changes
- Dissolve transitions between images
- Systemd services for autostart

## Development Commands

### Running the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run Flask server (port 80, requires sudo or CAP_NET_BIND_SERVICE)
sudo ./venv/bin/python app.py

# Or use the start script (includes cleanup)
./start-kiosk.sh
```

### Installing System Services

```bash
# Install and enable autostart services
sudo ./install-autostart.sh

# Check service status
sudo systemctl status kiosk-display.service
sudo systemctl status kiosk-firefox.service

# View logs
sudo journalctl -u kiosk-display -f
sudo journalctl -u kiosk-firefox -f

# Restart services
sudo systemctl restart kiosk-display.service
sudo systemctl restart kiosk-firefox.service
```

### Virtual Environment Setup

```bash
# Create venv (if not exists)
python3 -m venv venv

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Grant port 80 binding capability
PYTHON_BIN=$(readlink -f venv/bin/python3)
sudo setcap 'cap_net_bind_service=+ep' "$PYTHON_BIN"
```

## Architecture

### Core Components

1. **Backend (app.py)**
   - Flask server on port 80
   - JSON file storage (settings.json) for persistence
   - Remote command queue (single command with 5s expiration)
   - Debug message queue (deque, maxlen=100)
   - Theme filtering in `/api/images?enabled_only=true`

2. **Frontend - Display (templates/kiosk.html)**
   - Fullscreen slideshow with configurable interval (I)
   - Smart reload: checks every C=2 seconds for changes
   - Vector comparison (V vs VP) to detect enabled image changes
   - Opacity-based dissolve transitions (0.8s)
   - Polls for remote commands every 500ms
   - Keyboard controls and click-to-jump support

3. **Frontend - Management (templates/manage.html)**
   - Image upload (drag-and-drop, 50MB limit)
   - Enable/disable individual images
   - Theme creation and assignment (many-to-many)
   - Remote control buttons with LED indicators
   - Debug console (optional, polls every 1s)
   - Click thumbnails to jump kiosk display to that image

### Key Algorithms

**Smart Reload (kiosk.html)**
- Every 2 seconds: fetch enabled images → vector V
- Compare V with previous vector VP
- Check if interval or dissolve settings changed
- Only reload if something changed
- Prevents unnecessary disruption during playback

**Theme Filtering (app.py)**
- When `enabled_only=true` and `active_theme` is set:
  - Only return images assigned to active theme
  - Images not in any theme are excluded when theme is active
  - `active_theme=null` shows all enabled images

**Remote Control Polling**
- Management sends command to server via POST
- Server stores single command with timestamp
- Kiosk polls GET endpoint every 500ms
- Command auto-expires after 5 seconds
- Cleared after being retrieved once

### Data Model (settings.json)

```json
{
  "interval": 10,              // Slideshow interval (I) in seconds
  "check_interval": 2,          // Always 2 (C)
  "enabled_images": {           // Per-image enabled state
    "photo.jpg": true
  },
  "dissolve_enabled": true,     // Fade transitions
  "themes": {                   // Theme definitions
    "Nature": {"name": "Nature", "created": 1234567890}
  },
  "image_themes": {             // Many-to-many image→themes
    "photo.jpg": ["Nature", "Urban"]
  },
  "active_theme": "Nature"      // Currently active theme (null = all)
}
```

### Important API Endpoints

- `GET /` - Management interface
- `GET /view` - Kiosk display
- `GET /api/images?enabled_only=true` - List images (filtered by theme)
- `POST /api/images/<filename>/toggle` - Toggle enabled state
- `POST /api/images/<filename>/themes` - Update theme assignments
- `POST /api/control/send` - Send command (next/prev/pause/play/reload/jump)
- `GET /api/control/poll` - Poll for commands (kiosk)
- `POST /api/themes/active` - Set active theme
- `POST /api/debug/log` - Log from kiosk
- `GET /api/debug/messages` - Get debug logs

### State Synchronization

**Settings changes apply immediately:**
- Management updates settings.json via API
- Kiosk checks every 2 seconds via smart reload
- Remote commands execute within 500ms via polling
- No WebSockets needed for simplicity

**Pause behavior:**
- Navigation (next/prev) respects pause state
- Reload command always resumes playback
- LED indicators show play/pause state in management UI

## File Structure Notes

- `images/` - User-uploaded images (gitignored)
- `settings.json` - Runtime settings (gitignored)
- `venv/` - Python virtual environment (gitignored)
- `templates/kiosk.html` - 2000+ lines of JavaScript for display logic
- `templates/manage.html` - 1800+ lines with comprehensive management UI
- `*.service` - Systemd unit files for autostart
- `install-autostart.sh` - Dynamic path/user detection for installation

## Key Implementation Details

**Port 80 Binding:**
- Uses Linux capability `CAP_NET_BIND_SERVICE` instead of running as root
- Capability must be set on actual Python binary (not symlink)
- Install script uses `readlink -f` to resolve venv symlinks

**CSS Transitions:**
- Dissolve uses `opacity` transitions, not `display: none`
- `pointer-events: none` prevents click-through on hidden slides
- `.no-transition` class bypasses animation when needed

**Image Scaling:**
- CSS `object-fit: cover` fills 2560x2880 screen
- Slight aspect ratio variation permitted for maximum screen usage

**Cursor Hiding:**
- CSS `cursor: none` in kiosk display
- `unclutter -idle 0.1 -root` started by systemd service

**Username Detection:**
- Install script uses `$SUDO_USER` or `$USER`
- Dynamically replaces paths and user in service files
- Supports any username (not hardcoded to 'pi' or 'realo')

## Common Patterns

**When modifying slideshow behavior:**
- Update both JavaScript in kiosk.html and manage.html
- Test smart reload by checking debug console
- Verify vector comparison still works correctly

**When adding new settings:**
- Add to defaults in `get_settings()` in app.py
- Update `settings.json` documentation in ARCHITECTURE.md
- Add UI controls in manage.html
- Add checks in `checkForImageChanges()` in kiosk.html if needed

**When adding remote commands:**
- Add to valid commands list in app.py `/api/control/send`
- Add case to `executeCommand()` in kiosk.html
- Add button in manage.html remote control section
- Update LED handling if state-changing command
