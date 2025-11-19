# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git & GitHub Workflow

**IMPORTANT**: Never push to GitHub without explicit permission from the user.

- Always commit changes locally when making updates
- Wait for explicit "push" or "push to github" instruction before running `git push`
- This applies to all future sessions and conversations

## Deployment to Raspberry Pi

**CRITICAL**: When deploying file changes to the Raspberry Pi kiosk, ALWAYS follow this exact 4-step process:

**Device Credentials**: ALWAYS read from `device.txt` file (gitignored) before deploying. This file contains the hostname, username, and password needed for SSH/rsync commands.

```bash
# STEP 1: Stop all kiosk services (stops display, which auto-stops firefox)
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no <username>@<hostname> "sudo systemctl stop kiosk-display.service"

# STEP 2: Sync all code files using rsync (excludes venv, images, settings.json, .git)
sshpass -p '<password>' rsync -avz --exclude 'venv/' --exclude 'images/' --exclude '*.pyc' --exclude '__pycache__/' --exclude '.git/' --exclude 'settings.json' -e "ssh -o StrictHostKeyChecking=no" ./ <username>@<hostname>:~/kiosk_images/

# STEP 3: Start kiosk.target (starts both display and firefox services)
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no <username>@<hostname> "sudo systemctl start kiosk.target"

# STEP 4: VALIDATE all services are running (REQUIRED - do not skip!)
# Check kiosk-display service
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no <username>@<hostname> "sudo systemctl status kiosk-display.service --no-pager"

# Check kiosk-firefox service - if it failed, restart it
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no <username>@<hostname> "sudo systemctl status kiosk-firefox.service --no-pager"

# If Firefox service failed, restart it:
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no <username>@<hostname> "sudo systemctl restart kiosk-firefox.service && sleep 2 && sudo systemctl status kiosk-firefox.service --no-pager"
```

**Why this matters**:
- Stopping kiosk-display.service automatically stops kiosk-firefox.service (via BindsTo)
- kiosk-display.service kills mpv processes on stop (via ExecStopPost)
- Updating files while services are running can cause race conditions and file corruption
- Starting kiosk.target starts both services in the correct order
- Firefox service sometimes fails to restart automatically - you MUST validate and manually restart if needed
- NEVER skip stopping the service before copying files
- NEVER skip validation - always check that both services are active (running)

**Important**:
- The `device.txt` file is gitignored and should never be committed to version control
- Always use rsync with the exact excludes shown above to sync the entire project
- DO NOT use individual scp commands - always sync the whole directory with rsync
- The order is CRITICAL: Stop → Sync → Start → Validate
- Both kiosk-display AND kiosk-firefox must be "active (running)" for deployment to be successful

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
   - Per-theme interval configuration
   - Remote control buttons with LED indicators
   - Debug console (toggle with DEBUG button, polls every 1s)
   - Click thumbnails to jump kiosk display to that image
   - Current Images filtered by active theme

### Key Algorithms

**Smart Reload (kiosk.html)**
- Every 2 seconds: fetch enabled images → vector V
- Compare V with previous vector VP
- Check if interval changed (theme switching changes interval)
- Only reload if something changed
- Prevents unnecessary disruption during playback

**Theme Filtering (app.py)**
- **"All Images" theme**: Permanent default theme, shows all enabled images regardless of theme assignments
- **Other themes**: When `enabled_only=true` and active theme is set, only return images assigned to that theme
- Images not assigned to any theme are only shown in "All Images" theme
- "All Images" theme cannot be deleted

**Remote Control Polling**
- Management sends command to server via POST
- Server stores single command with timestamp
- Kiosk polls GET endpoint every 500ms
- Command auto-expires after 5 seconds
- Cleared after being retrieved once

### Data Model (settings.json)

```json
{
  "interval": 3600,             // Slideshow interval (I) in seconds (synced with active theme)
  "check_interval": 2,          // Always 2 (C)
  "enabled_images": {           // Per-image enabled state
    "photo.jpg": true
  },
  "dissolve_enabled": true,     // Fade transitions (always true)
  "themes": {                   // Theme definitions with per-theme intervals
    "All Images": {"name": "All Images", "created": 1234567890, "interval": 3600},  // Permanent, cannot be deleted
    "Nature": {"name": "Nature", "created": 1234567891, "interval": 3600}
  },
  "image_themes": {             // Many-to-many image→themes
    "photo.jpg": ["Nature", "Urban"]
  },
  "active_theme": "All Images"  // Currently active theme (defaults to "All Images")
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
- `POST /api/themes/active` - Set active theme (updates interval to theme's interval)
- `POST /api/themes/<name>/interval` - Update theme interval (seconds)
- `DELETE /api/themes/<name>` - Delete theme (cannot delete "All Images")
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
