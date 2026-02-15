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
- Flask backend with Flask-SocketIO (port 80) for image/video management
- 9 HTML frontend templates for display, management, upload, search, backup, debug, remote control
- Theme and atmosphere organization system with many-to-many image assignments
- Day scheduling with 12 two-hour periods (6 configurable + 6 auto-mirrored)
- Image cropping with non-uniform scaling for full-screen coverage
- Video playback via mpv with YouTube integration (yt-dlp)
- Hybrid communication: WebSocket primary, polling fallback
- Smart reload algorithm that checks every 2 seconds for changes
- 0.8s dissolve transitions between images
- Backup and restore system for settings and media
- Museum art search integration (8+ APIs)
- Test mode with mock time for deterministic testing
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
cd kiosk-tests
pip install -r requirements.txt
playwright install chromium
pytest                          # All tests
pytest tests/unit/              # Unit tests (14)
pytest tests/integration/       # Integration tests (55)
pytest tests/e2e/               # E2E tests (50)
pytest -v                       # Verbose output
pytest --headed                 # Run with visible browser
```

Tests connect to device specified in `kiosk-tests/device.txt` (gitignored).

## Architecture

### Core Components

1. **Backend (app.py ~3200 lines)**
   - Flask server on port 80 with Flask-SocketIO for WebSocket
   - JSON file storage (settings.json) for persistence
   - REST API (80+ endpoints) for all operations
   - WebSocket events for real-time updates to all clients
   - Remote command queue (single command with 5s expiration) as polling fallback
   - Video playback control via mpv subprocess
   - Video auto-transition timer (threading.Timer)
   - Debug message queue (deque, maxlen=500)
   - Test mode with mock time support
   - Atomic settings writes (temp file + rename)

2. **Museum Search (painting_searcher.py ~1500 lines)**
   - Integrates with 8+ museum/art APIs
   - Searches for portrait paintings matching display aspect ratio
   - Configurable via `sources_config.json` and `api_keys.json`

3. **Frontend Templates (9 files)**

   | Template | Route | Lines | Purpose |
   |----------|-------|-------|---------|
   | kiosk.html | `/view` | ~1400 | Fullscreen slideshow display |
   | manage.html | `/` | ~3100 | Main management interface |
   | upload.html | `/upload` | ~950 | Drag-and-drop image upload |
   | extra-images.html | `/extra-images` | ~1260 | Staging area for imports |
   | search.html | `/search` | ~800 | Museum art search |
   | backup.html | `/backup` | ~430 | Backup management |
   | debug.html | `/debug` | ~390 | Real-time log viewer |
   | remote.html | `/remote` | ~280 | Simple remote control |
   | loading.html | `/loading` | ~50 | Video loading screen |

4. **Frontend - Display (kiosk.html)**
   - Fullscreen slideshow with configurable interval
   - Smart reload: checks every 2 seconds for changes
   - Vector comparison (V vs VP) to detect enabled image changes
   - Opacity-based dissolve transitions (0.8s)
   - Image cropping with non-uniform scaling (fills screen, no black bars)
   - Day scheduling integration with 60-second hour boundary checks
   - Video playback support with auto-transition
   - WebSocket listener for remote commands and settings updates
   - Keyboard controls: Space/Right (next), Left (prev), F (fill/fit), R (reload)
   - Test mode support with mock time

5. **Frontend - Management (manage.html)**
   - Image upload (drag-and-drop, 50MB limit)
   - Enable/disable individual images
   - Image cropping with Cropper.js (locked/unlocked aspect ratio)
   - Theme creation and assignment (many-to-many)
   - Atmosphere creation and theme grouping
   - Day scheduling configuration (12 periods with AM/PM cycle labels)
   - Per-theme and per-atmosphere interval configuration
   - Video management (YouTube URLs, enable/disable, themes)
   - Remote control buttons with LED indicators
   - Debug console (toggle with DEBUG button)
   - Click thumbnails to jump kiosk display to that image
   - Current Images grid filtered by active theme/atmosphere

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
- Check if interval, shuffle_id, or crops changed
- Check if time period changed (day scheduling)
- Only reload if something changed
- Prevents unnecessary disruption during playback

**Image Filtering (app.py)**
- **Day scheduling enabled**: Filter by current time period's atmospheres' themes
- **Active atmosphere set**: Filter by atmosphere's themes
- **Active theme set**: Filter by theme
- **"All Images" theme/atmosphere**: Shows all images (including disabled in management view)
- Images not assigned to any theme only shown in "All Images"
- "All Images" theme and atmosphere cannot be deleted

**Day Scheduling (kiosk.html)**
- Every 60 seconds: check if hour boundary crossed
- 12 two-hour periods with automatic mirroring (periods 7-12 mirror 1-6)
- On boundary crossing: triggers `checkForImageChanges()` which reloads for new atmosphere
- Empty period defaults to "All Images" atmosphere

**Video Auto-Transition**
- Navigate Firefox to `/loading` page
- Launch mpv fullscreen with best 30fps format (via yt-dlp)
- Start timer for interval seconds
- On timer fire: kill mpv, regenerate shuffle_id if last item, emit `show_kiosk`

**Image Cropping**
- Crops stored in original image dimensions in `image_crops`
- Display uses non-uniform scaling: crop region fills entire 2560x2880 screen
- No black bars - selected region stretches to fill
- Same algorithm used for thumbnail generation

**Remote Control (Hybrid)**
- Primary: WebSocket `send_command` event for instant execution
- Fallback: POST to `/api/control/send`, kiosk polls GET `/api/control/poll` every 500ms
- Commands auto-expire after 5 seconds, cleared after retrieval

**Shuffle Consistency**
- `shuffle_id` in settings provides deterministic random order
- Same order across all clients viewing same theme/atmosphere
- Regenerated when atmosphere/theme changes or manual reshuffle

### Data Model (settings.json)

```json
{
  "interval": 3600,                    // Slideshow interval (seconds, synced with active theme)
  "check_interval": 2,                 // Smart reload check (always 2s)
  "dissolve_enabled": true,            // Fade transitions (always true)
  "shuffle_id": 0.123456,              // Random seed for image ordering

  "enabled_images": {                  // Per-image enabled state
    "uuid1.jpg": true
  },
  "image_crops": {                     // Per-image crop data (original dimensions)
    "uuid1.jpg": {"x": 100, "y": 200, "width": 1280, "height": 1440}
  },

  "themes": {                          // Theme definitions with per-theme intervals
    "All Images": {"name": "All Images", "created": 1234567890, "interval": 3600},
    "Nature": {"name": "Nature", "created": 1234567891, "interval": 1800}
  },
  "image_themes": {                    // Many-to-many image→themes
    "uuid1.jpg": ["Nature", "Landscapes"]
  },
  "active_theme": "All Images",

  "atmospheres": {                     // Atmosphere definitions
    "All Images": {"name": "All Images", "created": 1234567890, "interval": 3600},
    "Morning": {"name": "Morning", "created": 1234567891, "interval": 1800}
  },
  "atmosphere_themes": {               // Atmosphere→themes mapping
    "All Images": [],
    "Morning": ["Nature", "Landscapes"]
  },
  "active_atmosphere": null,           // null = use theme instead

  "day_scheduling_enabled": false,
  "day_times": {                       // 12 two-hour periods (7-12 mirror 1-6)
    "1": {"start_hour": 6, "atmospheres": ["Morning"]},
    "2": {"start_hour": 8, "atmospheres": []},
    "7": {"start_hour": 18, "atmospheres": []}
  },

  "video_urls": [                      // YouTube videos
    {"id": "video_123", "url": "https://youtube.com/..."}
  ],
  "video_themes": {"video_123": ["Nature"]},
  "enabled_videos": {"video_123": true}
}
```

**Interval Precedence** (highest to lowest):
1. Day Scheduling → First atmosphere's interval in current time period
2. Active Atmosphere → Atmosphere's interval
3. Active Theme → Theme's interval
4. Default → settings.interval

### Important API Endpoints

**Pages:**
- `GET /` - Management interface
- `GET /view` - Kiosk display
- `GET /upload` - Image upload
- `GET /search` - Museum art search
- `GET /extra-images` - Extra images staging
- `GET /backup` - Backup management
- `GET /debug` - Debug console
- `GET /remote` - Simple remote control
- `GET /loading` - Video loading screen

**Images:**
- `GET /api/images?enabled_only=true` - List images (filtered by theme/atmosphere/day)
- `POST /api/images` - Upload image (multipart/form-data)
- `DELETE /api/images/<filename>` - Delete image
- `POST /api/images/<filename>/toggle` - Toggle enabled state
- `POST /api/images/<filename>/themes` - Update theme assignments

**Themes:**
- `GET /api/themes` - List all themes
- `POST /api/themes` - Create theme
- `DELETE /api/themes/<name>` - Delete theme (cannot delete "All Images")
- `POST /api/themes/active` - Set active theme
- `POST /api/themes/<name>/interval` - Update theme interval

**Atmospheres:**
- `GET /api/atmospheres` - List all atmospheres
- `POST /api/atmospheres` - Create atmosphere
- `DELETE /api/atmospheres/<name>` - Delete atmosphere (cannot delete "All Images")
- `POST /api/atmospheres/active` - Set active atmosphere
- `POST /api/atmospheres/<name>/themes` - Assign themes
- `POST /api/atmospheres/<name>/interval` - Update interval

**Day Scheduling:**
- `GET /api/day/status` - Get status and current time period
- `POST /api/day/enable` - Enable day scheduling
- `POST /api/day/disable` - Disable day scheduling
- `POST /api/day/times/<id>/atmospheres` - Set period atmospheres

**Videos:**
- `GET /api/videos` - List videos
- `POST /api/videos` - Add video URL
- `DELETE /api/videos/<id>` - Delete video
- `POST /api/videos/<id>/toggle` - Toggle enabled
- `POST /api/videos/<id>/themes` - Assign themes
- `POST /api/videos/execute-mpv` - Start video playback
- `POST /api/videos/stop-mpv` - Stop video playback

**Remote Control:**
- `POST /api/control/send` - Send command (next/prev/pause/play/reload/jump)
- `GET /api/control/poll` - Poll for commands (kiosk fallback)

**Settings & Debug:**
- `GET /api/settings` - Get all settings
- `POST /api/settings` - Update settings
- `POST /api/debug/log` - Submit debug message
- `GET /api/debug/messages` - Get recent messages (max 500)
- `POST /api/debug/clear` - Clear debug messages

**Backup:**
- `GET /api/backups` - List all backups
- `POST /api/backups` - Create new backup
- `POST /api/backups/<name>/restore` - Restore from backup
- `DELETE /api/backups/<name>` - Delete backup

**Test Mode:**
- `POST /api/test/enable` - Enable test mode
- `POST /api/test/disable` - Disable test mode
- `POST /api/test/time` - Set mock time
- `POST /api/test/intervals` - Override intervals
- `GET /api/test/status` - Get test mode status
- `POST /api/test/trigger-hour-boundary` - Trigger hour check

### WebSocket Events

**Server → Client:**
- `settings_update` - Settings changed
- `image_list_changed` - Images added/removed
- `remote_command` - Execute command on kiosk
- `show_loading` - Navigate to loading page (video start)
- `show_kiosk` - Navigate back to kiosk (video end)
- `debug_message` - Debug log entry
- `thumbnail_generated` - Video thumbnail ready
- `search_progress` / `search_complete` - Art search status

**Client → Server:**
- `send_command` - Send remote command
- `log_debug` - Send debug message
- `start_art_search` - Start museum search

### State Synchronization

**Real-time via WebSocket:**
- Settings changes broadcast to all clients instantly
- Remote commands execute immediately
- No polling needed for most operations

**Smart reload (2-second polling fallback):**
- Backup check for image list changes
- Vector comparison prevents unnecessary reloads
- Handles cases where WebSocket connection drops

## File Structure

```
kiosk_images/
├── app.py                      # Flask backend (main application, ~3200 lines)
├── painting_searcher.py        # Museum API search client (~1500 lines)
├── requirements.txt            # Python dependencies
│
├── templates/                  # HTML templates (9 files)
│   ├── kiosk.html             # Slideshow display
│   ├── manage.html            # Management interface
│   ├── upload.html            # Image upload
│   ├── search.html            # Art search
│   ├── extra-images.html      # Extra images staging
│   ├── debug.html             # Debug console
│   ├── backup.html            # Backup management
│   ├── remote.html            # Simple remote control
│   └── loading.html           # Video loading screen
│
├── images/                    # Image storage (gitignored)
├── EXTRA_IMAGES/              # Staging folder for imports
├── thumbnails/                # Video thumbnail cache
├── backups/                   # Backup archives
│
├── settings.json              # Runtime configuration (gitignored)
├── sources_config.json        # Museum API source configuration
├── api_keys.json              # API keys for museum services (gitignored)
├── device.txt                 # Raspberry Pi credentials (gitignored)
│
├── kiosk-display.service      # Flask systemd service
├── kiosk-firefox.service      # Firefox systemd service
├── kiosk.target               # Composite systemd target
├── install-autostart.sh       # Service installation script
├── start-kiosk.sh             # Development start script
├── start-firefox-kiosk.sh     # Firefox launcher
├── stop-kiosk.sh              # Stop script
│
├── kiosk-tests/               # Test suite (119 tests)
│   ├── tests/
│   │   ├── unit/             # 14 unit tests
│   │   ├── integration/      # 55 integration tests
│   │   └── e2e/              # 50 E2E tests
│   ├── conftest.py           # Test fixtures
│   ├── pytest.ini            # Test configuration
│   ├── requirements.txt      # Test dependencies
│   ├── docs/                 # Generated PDF guides
│   └── doc_screenshots/      # UI screenshots
│
├── README.md                  # User documentation
├── ARCHITECTURE.md            # Technical architecture
├── REQUIREMENTS.md            # Feature requirements (147 testable items)
├── CLAUDE.md                  # This file - developer instructions
├── TEST.md                    # Test documentation
├── TEST_MODE.md               # Test mode API documentation
├── QUICKSTART.md              # Quick start guide for Raspberry Pi
│
└── venv/                      # Python environment (gitignored)
```

## Key Implementation Details

**Port 80 Binding:**
- Uses Linux capability `CAP_NET_BIND_SERVICE` instead of running as root
- Capability must be set on actual Python binary (not symlink)
- Install script uses `readlink -f` to resolve venv symlinks
- Systemd uses `AmbientCapabilities=CAP_NET_BIND_SERVICE`

**CSS Transitions:**
- Dissolve uses `opacity` transitions, not `display: none`
- `pointer-events: none` prevents click-through on hidden slides
- `.no-transition` class bypasses animation when needed

**Image Scaling:**
- Default: CSS `object-fit: cover` fills 2560x2880 screen
- With crop: non-uniform scaling stretches crop region to fill screen
- Fill/Fit toggle: `object-fit: cover` vs `object-fit: contain`
- URL parameter `?fit=true` starts in fit mode

**Video Playback:**
- mpv for fullscreen playback
- yt-dlp for YouTube URL resolution with best 30fps format selection
- Thumbnail generation after 20s playback (brightness check to avoid black frames)
- Auto-transition after interval expires
- Display set to 30Hz via xrandr in systemd service for smooth playback

**Cursor Hiding:**
- CSS `cursor: none` in kiosk display
- `unclutter -idle 0.1 -root` started by systemd service

**Username Detection:**
- Install script uses `$SUDO_USER` or `$USER`
- Dynamically replaces paths and user in service files
- Supports any username (not hardcoded to 'pi' or 'realo')

**Test Mode:**
- Allows mocking time for day scheduling tests
- Can override slideshow/check intervals for fast testing
- Enabled via API, disabled automatically on errors

**Atomic Settings Writes:**
- Write to temp file, then atomic rename
- Prevents corruption from crashes or concurrent access
- WebSocket `settings_update` emitted after every save

**UUID Filenames:**
- All uploaded images renamed to UUID (e.g., `ab4ab3c1-5c16.jpg`)
- Prevents naming conflicts, eliminates special character issues
- Allows deterministic testing

## Common Patterns

**When modifying slideshow behavior:**
- Update JavaScript in kiosk.html (display logic)
- Update manage.html if UI controls needed
- Test smart reload by checking debug console
- Verify vector comparison still works correctly

**When adding new settings:**
- Add to defaults in `get_settings()` in app.py
- Update `settings.json` documentation in ARCHITECTURE.md
- Add UI controls in manage.html
- Add checks in `checkForImageChanges()` in kiosk.html if needed
- Emit `settings_update` WebSocket event after saving

**When adding remote commands:**
- Add to valid commands list in app.py `/api/control/send`
- Add case to `executeCommand()` in kiosk.html
- Add WebSocket handler in app.py for `send_command` event
- Add button in manage.html remote control section
- Update LED handling if state-changing command

**When adding new API endpoints:**
- Add route in app.py
- Emit appropriate WebSocket events for state changes
- Update API reference in ARCHITECTURE.md
- Add integration tests in `kiosk-tests/tests/integration/`

**When modifying themes/atmospheres:**
- Theme and atmosphere filtering logic is in app.py `get_enabled_images()`
- UI for both is in manage.html
- "All Images" theme and atmosphere are immutable defaults
- Switching themes/atmospheres regenerates `shuffle_id`

**When modifying day scheduling:**
- Period calculation is in both app.py and kiosk.html
- Periods 7-12 mirror 1-6 automatically
- Hour boundary check runs every 60 seconds in kiosk.html
- UI shows AM cycle (6am-6pm) and PM cycle (6pm-6am) labels
- Green border highlights current period

**When debugging:**
- Use `/debug` page to view server logs
- Use browser dev tools for client-side issues
- Check `journalctl -u kiosk-display -f` for service logs
- Enable test mode API for timing-related issues
