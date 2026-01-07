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
- kiosk-display.service kills mpv/ffplay processes on stop (via ExecStopPost)
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

Art Kiosk is a web-based image and video display system for Raspberry Pi with a 2560x2880 portrait monitor. It provides:
- Flask backend with WebSocket support (port 80) for image management and real-time updates
- Nine HTML frontends for different functions (kiosk display, management, upload, backup, etc.)
- Three-tier organization: Images/Videos → Themes → Atmospheres
- Day scheduling with 12 time periods for automatic atmosphere switching
- Remote control via WebSocket for keyboard-less operation
- Smart reload algorithm that checks every 2 seconds for changes
- Video playback with YouTube integration (via yt-dlp and ffplay)
- Image cropping for custom framing
- Backup/restore functionality
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

### Running Tests

```bash
# Navigate to test directory
cd kiosk-tests

# Setup (first time only)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Run all tests
pytest

# Run by category
pytest -m unit          # Fast unit tests
pytest -m integration   # API/server tests
pytest -m e2e           # Browser automation tests

# Run with visible browser
pytest --headed
```

## Architecture

### Core Components

1. **Backend (app.py)**
   - Flask server with Flask-SocketIO on port 80
   - JSON file storage (settings.json) for persistence with atomic writes
   - WebSocket for real-time updates to all connected clients
   - Remote command queue with 5s expiration (legacy polling)
   - Debug message queue (deque, maxlen=500)
   - Video playback via ffplay subprocess
   - Test mode API for automated testing

2. **Frontend - Kiosk Display (templates/kiosk.html)**
   - Fullscreen slideshow with configurable interval
   - Smart reload: checks every 2 seconds for changes via vector comparison
   - WebSocket listener for instant remote commands
   - Opacity-based dissolve transitions (0.8s)
   - Keyboard controls and click-to-jump support
   - Hour boundary detection for day scheduling

3. **Frontend - Management (templates/manage.html)**
   - Main dashboard with navigation to all pages
   - Theme and atmosphere management
   - Day scheduling configuration (12 time periods)
   - Remote control with LED indicators
   - Current images filtered by active theme/atmosphere

4. **Frontend - Upload (templates/upload.html)**
   - Image upload with drag-and-drop (50MB limit)
   - Image grid with enable/disable toggles
   - Theme assignment per image
   - Image cropping with aspect ratio lock
   - Image deletion

5. **Frontend - Backup (templates/backup.html)**
   - Create and restore backups (ZIP format)
   - Includes settings.json and all images
   - Download and delete backups

6. **Additional Frontends**
   - `remote.html` - Simplified remote control interface
   - `debug.html` - Debug console for viewing logs
   - `search.html` - Art search (external sources)
   - `extra-images.html` - Extra images management
   - `loading.html` - Loading screen during video startup

### Organization Hierarchy

```
Images/Videos
    └── Themes (e.g., "Nature", "Urban", "Art")
        └── Atmospheres (e.g., "Morning", "Evening")
            └── Day Scheduling (12 time periods)
```

- **Images/Videos**: Individual media items
- **Themes**: Logical groupings of images (many-to-many relationship)
- **Atmospheres**: Collections of themes for mood/ambiance
- **Day Scheduling**: Time-based automatic atmosphere switching

### Key Algorithms

**Smart Reload (kiosk.html)**
- Every 2 seconds: fetch enabled images → vector V
- Compare V with previous vector VP
- Check if interval changed (theme switching changes interval)
- Only reload if something changed
- Prevents unnecessary disruption during playback

**Theme/Atmosphere Filtering (app.py)**
- **"All Images" theme**: Permanent default, shows all enabled images
- **Specific theme**: Shows only images assigned to that theme
- **Atmosphere active**: Shows images from all themes in that atmosphere
- **Day scheduling**: Overrides atmosphere based on current time period

**Day Scheduling**
- 12 time periods of 2 hours each (24-hour coverage)
- Times 7-12 mirror times 1-6 (PM mirrors AM)
- Each period can have multiple atmospheres assigned
- Empty period defaults to "All Images" atmosphere

**Shuffle Consistency**
- `shuffle_id` in settings provides deterministic random order
- Same order across all clients viewing same theme/atmosphere
- Regenerated when atmosphere/theme changes or manual reshuffle

### Data Model (settings.json)

```json
{
  "interval": 3600,
  "check_interval": 2,
  "enabled_images": {"photo.jpg": true},
  "dissolve_enabled": true,
  "themes": {
    "All Images": {"name": "All Images", "created": 1234567890, "interval": 3600},
    "Nature": {"name": "Nature", "created": 1234567891, "interval": 3600}
  },
  "image_themes": {"photo.jpg": ["Nature", "Urban"]},
  "active_theme": "All Images",
  "atmospheres": {
    "All Images": {"name": "All Images", "created": 1234567890, "interval": 3600}
  },
  "atmosphere_themes": {"All Images": []},
  "active_atmosphere": null,
  "day_scheduling_enabled": false,
  "day_times": {
    "1": {"start_hour": 6, "atmospheres": []},
    "2": {"start_hour": 8, "atmospheres": []},
    ...
    "12": {"start_hour": 4, "atmospheres": []}
  },
  "shuffle_id": 0.123456,
  "image_crops": {"photo.jpg": {"x": 0, "y": 0, "width": 100, "height": 100}},
  "video_urls": [{"url": "https://youtube.com/...", "id": "abc123"}],
  "video_themes": {"abc123": ["Nature"]},
  "enabled_videos": {"abc123": true}
}
```

### Important API Endpoints

**Pages**
- `GET /` - Management interface
- `GET /view` - Kiosk display
- `GET /upload` - Image upload page
- `GET /backup` - Backup management
- `GET /remote` - Simplified remote control
- `GET /debug` - Debug console

**Images API**
- `GET /api/images?enabled_only=true` - List images (filtered)
- `POST /api/images` - Upload image
- `DELETE /api/images/<filename>` - Delete image
- `POST /api/images/<filename>/toggle` - Toggle enabled
- `POST /api/images/<filename>/themes` - Update theme assignments

**Themes API**
- `GET /api/themes` - List themes
- `POST /api/themes` - Create theme
- `DELETE /api/themes/<name>` - Delete theme
- `POST /api/themes/<name>/interval` - Update interval
- `POST /api/themes/active` - Set active theme

**Atmospheres API**
- `GET /api/atmospheres` - List atmospheres
- `POST /api/atmospheres` - Create atmosphere
- `DELETE /api/atmospheres/<name>` - Delete atmosphere
- `POST /api/atmospheres/active` - Set active atmosphere
- `POST /api/atmospheres/<name>/themes` - Update themes in atmosphere

**Day Scheduling API**
- `GET /api/day/status` - Get scheduling status
- `POST /api/day/toggle` - Toggle scheduling
- `POST /api/day/times/<id>/atmospheres` - Set atmospheres for time period

**Video API**
- `GET /api/videos` - List videos
- `POST /api/videos` - Add video URL
- `DELETE /api/videos/<id>` - Delete video
- `POST /api/videos/<id>/play` - Play video via ffplay

**Backup API**
- `GET /api/backups` - List backups
- `POST /api/backup` - Create backup
- `POST /api/backup/restore/<name>` - Restore backup
- `DELETE /api/backup/<name>` - Delete backup

**Control API**
- `POST /api/control/send` - Send command (next/prev/pause/play/reload/jump)
- `GET /api/control/poll` - Poll for commands (legacy)

**Test Mode API** (for automated testing)
- `POST /api/test/enable` - Enable test mode
- `POST /api/test/disable` - Disable test mode
- `POST /api/test/time` - Set mock time
- `POST /api/test/intervals` - Set fast intervals
- `POST /api/test/trigger-hour-boundary` - Trigger hour check

### WebSocket Events

**Server → Client**
- `settings_update` - Full settings object when changed
- `remote_command` - Command to execute (next, prev, pause, play, reload, jump)
- `image_list_changed` - Notification to refresh image list
- `thumbnail_generated` - Video thumbnail ready
- `art_search_result` / `art_search_complete` - Art search progress

**Client → Server**
- `send_command` - Send remote command
- `log_debug` - Log debug message
- `start_art_search` - Begin art search

### State Synchronization

**Real-time via WebSocket:**
- Settings changes broadcast to all clients instantly
- Remote commands execute immediately
- No polling needed for most operations

**Smart reload (2-second polling):**
- Backup check for image list changes
- Vector comparison prevents unnecessary reloads
- Handles cases where WebSocket connection drops

## File Structure

```
art-kiosk/
├── app.py                    # Main Flask application (~3000 lines)
├── painting_searcher.py      # Art search functionality
├── requirements.txt          # Python dependencies
├── settings.json             # Runtime settings (gitignored)
├── device.txt                # Pi credentials (gitignored)
├── templates/
│   ├── kiosk.html           # Kiosk display (~1400 lines)
│   ├── manage.html          # Management dashboard (~3100 lines)
│   ├── upload.html          # Image upload (~950 lines)
│   ├── backup.html          # Backup management (~430 lines)
│   ├── remote.html          # Remote control (~280 lines)
│   ├── debug.html           # Debug console (~390 lines)
│   ├── search.html          # Art search (~800 lines)
│   ├── extra-images.html    # Extra images (~1260 lines)
│   └── loading.html         # Video loading screen (~50 lines)
├── images/                   # User images (gitignored)
├── thumbnails/               # Video thumbnails (gitignored)
├── EXTRA_IMAGES/             # Downloaded art (gitignored)
├── backups/                  # Backup ZIP files
├── kiosk-display.service     # Systemd service for Flask
├── kiosk-firefox.service     # Systemd service for browser
├── kiosk.target              # Systemd target for both services
├── install-autostart.sh      # Service installation script
├── start-kiosk.sh            # Start script with cleanup
├── stop-kiosk.sh             # Stop script
└── kiosk-tests/              # Test suite (23 test files)
    ├── requirements.txt      # Test dependencies (Playwright)
    ├── conftest.py           # Pytest fixtures
    ├── pytest.ini            # Pytest configuration
    └── tests/
        ├── unit/             # Fast API tests
        ├── integration/      # Server interaction tests
        └── e2e/              # Browser automation tests
```

## Key Implementation Details

**Port 80 Binding:**
- Uses Linux capability `CAP_NET_BIND_SERVICE` instead of running as root
- Capability must be set on actual Python binary (not symlink)
- Install script uses `readlink -f` to resolve venv symlinks

**Video Playback:**
- Uses ffplay (from ffmpeg) for video display
- yt-dlp fetches best 30fps format from YouTube
- Video plays fullscreen with crop/scale to fit 2560x2880
- Thumbnail generated by capturing frame after 20 seconds

**Atomic Settings Writes:**
- Uses tempfile + os.replace for atomic updates
- Prevents race conditions during concurrent reads/writes
- WebSocket broadcast after every save

**CSS Transitions:**
- Dissolve uses `opacity` transitions, not `display: none`
- `pointer-events: none` prevents click-through on hidden slides
- `.no-transition` class bypasses animation when needed

**Image Scaling:**
- CSS `object-fit: cover` fills 2560x2880 screen
- Custom crop data overrides default scaling
- Crops stored as percentage values

**Cursor Hiding:**
- CSS `cursor: none` in kiosk display
- `unclutter -idle 0.1 -root` started by systemd service

**Test Mode:**
- Allows mocking time for day scheduling tests
- Can override slideshow/check intervals for fast testing
- Enabled via API, disabled automatically on errors

## Common Patterns

**When modifying slideshow behavior:**
- Update JavaScript in kiosk.html
- May need to update manage.html for UI consistency
- Test with pytest -m e2e for browser tests
- Verify WebSocket events still work

**When adding new settings:**
- Add to defaults dict in `get_settings()` in app.py
- Add migration check for existing settings.json
- Update any templates that need the setting
- Add API endpoint if needed

**When adding remote commands:**
- Add handler in `send_command` WebSocket event in app.py
- Add case to command handler in kiosk.html
- Add button in manage.html or remote.html if needed
- Update LED handling if state-changing

**When adding new features:**
- Create API endpoints in app.py
- Add WebSocket events for real-time updates
- Create or update templates as needed
- Add tests in kiosk-tests/

**When debugging:**
- Use `/debug` page to view server logs
- Use browser dev tools for client-side issues
- Check `journalctl -u kiosk-display -f` for service logs
- Enable test mode API for timing-related issues
