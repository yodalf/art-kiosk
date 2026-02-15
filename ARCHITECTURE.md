# Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Backend Components](#backend-components)
4. [Frontend Components](#frontend-components)
5. [Data Model](#data-model)
6. [API Reference](#api-reference)
7. [WebSocket Events](#websocket-events)
8. [Key Algorithms](#key-algorithms)
9. [Service Architecture](#service-architecture)
10. [External Dependencies](#external-dependencies)
11. [File Structure](#file-structure)
12. [Design Patterns](#design-patterns)
13. [Security Considerations](#security-considerations)

---

## System Overview

The Kiosk Image Display System is a Flask-based web application designed for displaying images and videos on a Raspberry Pi with a 2560x2880 portrait monitor. It provides:

- **Slideshow display** with configurable intervals and smooth dissolve transitions
- **Theme/Atmosphere organization** for categorizing images
- **Day scheduling** to automatically switch content based on time of day
- **Remote control** via web interface (no keyboard needed on display)
- **Video playback** with YouTube integration
- **Image cropping** for custom framing on the display

### Target Environment

- **Hardware**: Raspberry Pi 4 (or compatible)
- **Display**: 2560x2880 portrait monitor
- **OS**: Raspberry Pi OS (X11 mode)
- **Browser**: Firefox in kiosk mode
- **Network**: Local network access for management

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Management Devices                           │
│                    (Phone, Tablet, Computer)                        │
│                              │                                       │
│                    HTTP/WebSocket (Port 80)                         │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────────┐
│                       Raspberry Pi                                   │
│  ┌───────────────────────────┼───────────────────────────────────┐  │
│  │                    Flask Server (app.py)                       │  │
│  │                         Port 80                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │   REST API  │  │  WebSocket  │  │   Static Files      │   │  │
│  │  │  Endpoints  │  │   Events    │  │  (images, CSS, JS)  │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
│  │           │              │                    │                │  │
│  │           └──────────────┼────────────────────┘                │  │
│  │                          │                                     │  │
│  │              ┌───────────┴───────────┐                        │  │
│  │              │    settings.json      │                        │  │
│  │              │   (Persistent State)  │                        │  │
│  │              └───────────────────────┘                        │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                               │                                       │
│  ┌────────────────────────────┼───────────────────────────────────┐  │
│  │                     Firefox Kiosk                               │  │
│  │                    (kiosk.html at /view)                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │  Slideshow  │  │   Smart     │  │   WebSocket         │   │  │
│  │  │   Engine    │  │   Reload    │  │   Listener          │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                               │                                       │
│                        ┌──────┴──────┐                               │
│                        │  mpv Player │                               │
│                        │  (Videos)   │                               │
│                        └─────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
                               │
                        ┌──────┴──────┐
                        │   Display   │
                        │ 2560x2880   │
                        └─────────────┘
```

### Communication Flow

1. **Management Interface** → Flask API → Settings/Commands
2. **Flask Server** → WebSocket → All connected clients
3. **Kiosk Display** polls API every 2 seconds for changes
4. **Remote commands** sent via WebSocket for instant execution

---

## Backend Components

### Flask Server (app.py)

The main application server handles all HTTP requests and WebSocket connections.

**Core Responsibilities:**
- Serve HTML pages and static files
- Provide REST API for all operations
- Manage WebSocket real-time communication
- Control video playback via mpv
- Persist settings to JSON file

**Key Modules:**

| Component | Purpose |
|-----------|---------|
| Flask | Web framework and routing |
| Flask-SocketIO | WebSocket support |
| JSON Storage | Persistent settings |
| subprocess | mpv video control |
| threading | Timers for video transitions |

### Global State Variables

```python
# Remote control (polling fallback)
current_command = None          # Pending command for kiosk
command_timestamp = 0           # Command expiration tracking

# Current display state
current_kiosk_image = None      # Currently displayed image
current_video_id = None         # Currently playing video

# Video playback
mpv_process = None              # Active mpv subprocess
video_transition_timer = None   # Auto-transition timer
video_next_item = None          # Next item after video ends
video_is_last_item = False      # Flag for end of playlist

# Debug logging
debug_messages = deque(maxlen=500)  # Recent log messages

# Test mode (automated testing)
test_mode = {
    'enabled': False,
    'mock_time': None           # Override system time
}
```

---

## Frontend Components

### Templates Overview

| Template | Route | Purpose |
|----------|-------|---------|
| **kiosk.html** | `/view` | Main slideshow display (2560x2880) |
| **manage.html** | `/` | Full management interface |
| **remote.html** | `/remote` | Simplified remote control |
| **upload.html** | `/upload` | Drag-and-drop image upload |
| **search.html** | `/search` | Museum art search |
| **extra-images.html** | `/extra-images` | Staging area for imports |
| **debug.html** | `/debug` | Real-time log viewer |
| **loading.html** | `/loading` | Shown during video startup |
| **backup.html** | `/backup` | Backup management |

### kiosk.html - Slideshow Display

The main display runs on the Raspberry Pi's connected monitor.

**Key Features:**
- Fullscreen slideshow with configurable interval
- Smooth dissolve transitions (0.8s opacity fade)
- Image cropping support
- Video playback integration
- Smart reload (detects changes without disruption)
- Day scheduling support
- Remote command execution

**Key Data Structures:**
```javascript
images[]              // Current enabled images list
currentIndex          // Current slide position
interval              // Slideshow interval (ms)
checkInterval         // Smart reload interval (2000ms)
previousImageVector   // For change detection
previousShuffleId     // Detects theme/atmosphere changes
previousTimePeriod    // Detects day scheduling changes
imageCrops            // Per-image crop data
isPaused              // Slideshow pause state
isPlayingVideo        // Video playback flag
```

### manage.html - Management Interface

The comprehensive admin interface for all settings.

**Features:**
- Image management (upload, enable/disable, delete)
- Image cropping with Cropper.js
- Theme and atmosphere configuration
- Day scheduling (12 time periods)
- Remote control buttons
- Debug console
- Current images grid (filtered by active theme/atmosphere)

---

## Data Model

### settings.json Structure

```json
{
  // === Core Settings ===
  "interval": 3600,              // Slideshow interval in seconds
  "check_interval": 2,           // Smart reload check (always 2s)
  "dissolve_enabled": true,      // Transition animation (always true)
  "shuffle_id": 0.123456,        // Random seed for image ordering

  // === Image State ===
  "enabled_images": {
    "uuid1.jpg": true,
    "uuid2.png": false
  },
  "image_crops": {
    "uuid1.jpg": {
      "x": 100, "y": 200,
      "width": 1280, "height": 1440
    }
  },

  // === Theme System ===
  "themes": {
    "All Images": {              // Permanent default
      "name": "All Images",
      "created": 1234567890,
      "interval": 3600
    },
    "Nature": {
      "name": "Nature",
      "created": 1234567891,
      "interval": 1800
    }
  },
  "image_themes": {              // Image → Themes mapping
    "uuid1.jpg": ["Nature", "Landscapes"],
    "uuid2.png": ["Portraits"]
  },
  "active_theme": "All Images",

  // === Atmosphere System ===
  "atmospheres": {
    "All Images": {              // Permanent default
      "name": "All Images",
      "created": 1234567890,
      "interval": 3600
    },
    "Morning": {
      "name": "Morning",
      "created": 1234567891,
      "interval": 1800
    }
  },
  "atmosphere_themes": {         // Atmosphere → Themes mapping
    "All Images": [],            // Empty = all themes
    "Morning": ["Nature", "Landscapes"]
  },
  "active_atmosphere": null,     // null = use theme instead

  // === Day Scheduling ===
  "day_scheduling_enabled": false,
  "day_times": {
    "1": { "start_hour": 6,  "atmospheres": ["Morning"] },
    "2": { "start_hour": 8,  "atmospheres": [] },
    "3": { "start_hour": 10, "atmospheres": [] },
    "4": { "start_hour": 12, "atmospheres": [] },
    "5": { "start_hour": 14, "atmospheres": [] },
    "6": { "start_hour": 16, "atmospheres": [] },
    "7": { "start_hour": 18, "atmospheres": [] },  // Mirrors 1
    "8": { "start_hour": 20, "atmospheres": [] },  // Mirrors 2
    "9": { "start_hour": 22, "atmospheres": [] },  // Mirrors 3
    "10": { "start_hour": 0, "atmospheres": [] },  // Mirrors 4
    "11": { "start_hour": 2, "atmospheres": [] },  // Mirrors 5
    "12": { "start_hour": 4, "atmospheres": [] }   // Mirrors 6
  },

  // === Video Support ===
  "video_urls": [
    { "id": "video_123", "url": "https://youtube.com/..." }
  ],
  "video_themes": {
    "video_123": ["Nature", "Documentary"]
  },
  "enabled_videos": {
    "video_123": true
  }
}
```

### Hierarchy Relationships

```
Atmosphere
    └── contains Themes[]
            └── contains Images[]
                    └── has Crops (optional)

Day Schedule
    └── Time Period (1-12)
            └── contains Atmospheres[]
```

### Interval Precedence

The slideshow interval is determined by this priority order:

1. **Day Scheduling** → First atmosphere's interval in current time period
2. **Active Atmosphere** → Atmosphere's interval
3. **Active Theme** → Theme's interval
4. **Default** → settings.interval

---

## API Reference

### Image Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/images` | List all images |
| GET | `/api/images?enabled_only=true` | List enabled images (filtered by theme/atmosphere) |
| POST | `/api/images` | Upload new image (multipart/form-data) |
| DELETE | `/api/images/<filename>` | Delete image |
| POST | `/api/images/<filename>/toggle` | Toggle enabled state |
| POST | `/api/images/<filename>/themes` | Update theme assignments |

**Image Filtering Logic:**
```
if day_scheduling_enabled:
    filter by current time period's atmospheres
else if active_atmosphere:
    filter by atmosphere's themes
else if active_theme:
    filter by theme
else:
    show all enabled images
```

### Theme Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/themes` | List all themes |
| POST | `/api/themes` | Create new theme |
| DELETE | `/api/themes/<name>` | Delete theme (not "All Images") |
| POST | `/api/themes/<name>/interval` | Update theme interval |
| POST | `/api/themes/active` | Set active theme |

### Atmosphere Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/atmospheres` | List all atmospheres |
| POST | `/api/atmospheres` | Create new atmosphere |
| DELETE | `/api/atmospheres/<name>` | Delete atmosphere (not "All Images") |
| POST | `/api/atmospheres/<name>/interval` | Update atmosphere interval |
| POST | `/api/atmospheres/<name>/themes` | Assign themes to atmosphere |
| POST | `/api/atmospheres/active` | Set active atmosphere |

### Day Scheduling

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/day/status` | Get status and current time period |
| POST | `/api/day/enable` | Enable day scheduling |
| POST | `/api/day/disable` | Disable day scheduling |
| POST | `/api/day/times/<id>/atmospheres` | Assign atmospheres to time period |

### Remote Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/control/send` | Send command to kiosk |
| GET | `/api/control/poll` | Poll for commands (500ms) |

**Available Commands:**
- `next` - Next image
- `prev` - Previous image
- `pause` - Pause slideshow
- `play` - Resume slideshow
- `reload` - Reload display
- `jump` - Jump to specific image (include `image_name`)

### Video Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/videos` | List all videos |
| POST | `/api/videos` | Add video URL |
| DELETE | `/api/videos/<id>` | Delete video |
| POST | `/api/videos/<id>/toggle` | Toggle enabled state |
| POST | `/api/videos/<id>/themes` | Assign themes |
| POST | `/api/videos/execute-mpv` | Start video playback |
| POST | `/api/videos/stop-mpv` | Stop video playback |

### Settings & Debug

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get all settings |
| POST | `/api/settings` | Update settings |
| POST | `/api/debug/log` | Submit debug message |
| GET | `/api/debug/messages` | Get recent messages (max 500) |
| POST | `/api/debug/clear` | Clear debug messages |

### Backup & Restore

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/backups` | List all backups |
| POST | `/api/backups` | Create new backup |
| POST | `/api/backups/<name>/restore` | Restore from backup |
| DELETE | `/api/backups/<name>` | Delete backup |

### Test Mode (Automated Testing)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/test/enable` | Enable test mode |
| POST | `/api/test/disable` | Disable test mode |
| POST | `/api/test/time` | Set mock time |
| POST | `/api/test/intervals` | Override intervals |
| GET | `/api/test/status` | Get test mode status |

---

## WebSocket Events

### Server → Client Events

| Event | Payload | Purpose |
|-------|---------|---------|
| `settings_update` | `{...settings}` | Settings changed |
| `image_list_changed` | `{}` | Images added/removed |
| `remote_command` | `{command, image_name?}` | Execute command on kiosk |
| `show_loading` | `{}` | Navigate to loading page |
| `show_kiosk` | `{start_image?}` | Navigate back to kiosk |
| `debug_message` | `{timestamp, level, message}` | Debug log entry |
| `thumbnail_generated` | `{video_id}` | Video thumbnail ready |
| `search_progress` | `{message}` | Art search status |
| `search_complete` | `{results[], total}` | Art search finished |

### Client → Server Events

| Event | Payload | Purpose |
|-------|---------|---------|
| `send_command` | `{command, image_name?}` | Send remote command |
| `log_debug` | `{message, level}` | Send debug message |
| `start_art_search` | `{query, options}` | Start museum search |

---

## Key Algorithms

### Smart Reload Algorithm

The kiosk display uses an intelligent reload system to detect changes without disrupting playback.

```
Every 2 seconds (checkForImageChanges):
  1. Fetch /api/images?enabled_only=true → V (current vector)
  2. Fetch /api/settings → interval, shuffle_id, crops
  3. Fetch /api/day/status → current_time_period

  4. Compare with previous values:
     - If V ≠ VP (image list changed) → reload
     - If shuffle_id changed → reload from index 0
     - If interval changed → update timer
     - If crops changed → refresh display
     - If time_period changed → reload for new atmosphere

  5. Save current values as previous
  6. Only reload if something actually changed
```

**Vector Comparison:**
- Creates sorted array of enabled image names
- Compares array length and individual elements
- Detects additions, removals, and reordering

### Day Scheduling Time Period Transitions

When day scheduling is enabled, the kiosk monitors for time period changes:

```
Every 60 seconds (checkHourBoundary):
  currentHour = getHours(mockTime || Date.now())

  if currentHour != lastCheckHour:
    lastCheckHour = currentHour
    await checkForImageChanges()  // Reloads for new period
```

This ensures that when crossing a time period boundary (e.g., 8:00 AM), the kiosk:
1. Detects the hour change
2. Calls checkForImageChanges() which fetches the new image list
3. Reloads the slideshow with images from the new time period's atmosphere(s)

**Time Period Calculation:**
```
Time Periods (12 independent 2-hour blocks):
  Period 1:  6 AM -  8 AM     Period 7:  6 PM -  8 PM
  Period 2:  8 AM - 10 AM     Period 8:  8 PM - 10 PM
  Period 3: 10 AM - 12 PM     Period 9: 10 PM - 12 AM
  Period 4: 12 PM -  2 PM     Period 10: 12 AM -  2 AM
  Period 5:  2 PM -  4 PM     Period 11:  2 AM -  4 AM
  Period 6:  4 PM -  6 PM     Period 12:  4 AM -  6 AM
```

### Video Auto-Transition

```
On video start:
  1. Navigate Firefox to /loading
  2. Launch mpv with video URL
  3. Start timer for interval seconds
  4. Track next_item = images[(video_index + 1) % length]

On timer fire:
  1. Kill mpv process
  2. If video was last item → regenerate shuffle_id
  3. Clear video state
  4. Emit show_kiosk with start_image
  5. Slideshow resumes from next item
```

### Image Cropping Algorithm

```
applyCrop(img, container, cropData):
  1. Calculate scale: container_height / crop_height
  2. Set image size: crop_width × scale, crop_height × scale
  3. Position image: -crop_x × scale, -crop_y × scale
  4. Container has overflow: hidden
  5. Result: Selected region fills entire display
```

### Atomic Settings Write

To prevent corruption from concurrent access:

```python
def save_settings(settings):
    # Write to temp file first
    temp_file = settings_path + '.tmp'
    with open(temp_file, 'w') as f:
        json.dump(settings, f, indent=2)

    # Atomic rename (single OS operation)
    os.rename(temp_file, settings_path)

    # Notify all clients
    socketio.emit('settings_update', settings)
```

---

## Service Architecture

### Systemd Services

The system uses two systemd services managed by a composite target:

```
kiosk.target (composite)
    │
    ├── kiosk-display.service (Flask Backend)
    │       │
    │       ├── ExecStartPre: Kill port 80, kill mpv
    │       ├── ExecStart: python app.py
    │       ├── ExecStopPost: Kill port 80, kill mpv
    │       └── Capability: CAP_NET_BIND_SERVICE (port 80)
    │
    └── kiosk-firefox.service (Display Client)
            │
            ├── BindsTo: kiosk-display.service
            ├── ExecStartPre: Wait for server, disable screen blank
            ├── ExecStart: start-firefox-kiosk.sh
            └── ExecStopPost: Force kill Firefox
```

### Service Dependencies

```
kiosk-firefox.service
    ├── Requires: kiosk-display.service
    ├── After: kiosk-display.service, graphical.target
    └── BindsTo: kiosk-display.service
```

**BindsTo Relationship:**
- Firefox cannot run without the display service
- If display service stops, Firefox automatically stops
- Restart of display service triggers Firefox restart

### Service Commands

```bash
# Start everything
sudo systemctl start kiosk.target

# Stop everything
sudo systemctl stop kiosk.target

# Restart services
sudo systemctl restart kiosk-display.service
sudo systemctl restart kiosk-firefox.service

# View logs
sudo journalctl -u kiosk-display -f
sudo journalctl -u kiosk-firefox -f

# Check status
sudo systemctl status kiosk-display.service
sudo systemctl status kiosk-firefox.service
```

---

## External Dependencies

### Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.0 | Web framework |
| flask-socketio | 5.3.6 | WebSocket support |
| python-socketio | 5.11.1 | Socket.IO server |
| Werkzeug | 3.0.1 | WSGI utilities |
| requests | 2.31.0 | HTTP client |
| Pillow | >=10.0.0 | Image processing |

### Frontend Libraries (CDN)

| Library | Version | Purpose |
|---------|---------|---------|
| Socket.IO | 4.7.2 | WebSocket client |
| Cropper.js | 1.6.1 | Image cropping UI |

### System Tools

| Tool | Purpose |
|------|---------|
| mpv | Video playback engine |
| yt-dlp | YouTube video download |
| scrot | Screenshot capture (thumbnails) |
| curl | HTTP client (health checks) |
| xdotool | Window management |
| unclutter | Hide mouse cursor |

### External APIs (Optional)

Museum search integrates with these APIs (configured in `sources_config.json`):
- Cleveland Museum of Art API
- Rijksmuseum API
- Wikimedia Commons API
- Europeana API
- Harvard Art Museums API

---

## File Structure

```
kiosk_images/
├── app.py                      # Flask backend (main application)
├── painting_searcher.py        # Museum API search client
│
├── templates/                  # HTML templates
│   ├── kiosk.html             # Main slideshow display
│   ├── manage.html            # Management interface
│   ├── remote.html            # Simple remote control
│   ├── upload.html            # Image upload
│   ├── search.html            # Art search
│   ├── extra-images.html      # Extra images staging
│   ├── debug.html             # Debug console
│   ├── loading.html           # Video loading screen
│   └── backup.html            # Backup management
│
├── images/                    # Main image storage (gitignored)
├── EXTRA_IMAGES/              # Staging folder for imports
├── thumbnails/                # Video thumbnail cache
├── backups/                   # Backup archives
│
├── settings.json              # Runtime settings (gitignored)
├── api_keys.json              # API keys (gitignored)
├── sources_config.json        # Museum API configuration
│
├── venv/                      # Python virtual environment
├── requirements.txt           # Python dependencies
│
├── kiosk-display.service      # Flask systemd service
├── kiosk-firefox.service      # Firefox systemd service
├── kiosk.target               # Composite systemd target
├── install-autostart.sh       # Service installation script
│
├── start-kiosk.sh             # Development start script
├── start-firefox-kiosk.sh     # Firefox launcher
├── stop-kiosk.sh              # Stop script
│
├── kiosk-tests/               # Test suite
│   ├── tests/
│   │   ├── unit/             # Unit tests
│   │   ├── integration/      # Integration tests
│   │   └── e2e/              # End-to-end tests
│   ├── conftest.py           # Test fixtures
│   └── requirements.txt      # Test dependencies
│
├── README.md                  # User documentation
├── ARCHITECTURE.md            # This file
├── REQUIREMENTS.md            # Feature requirements
├── CLAUDE.md                  # Developer instructions
├── TEST.md                    # Test documentation
└── TEST_MODE.md               # Test mode documentation
```

---

## Design Patterns

### Hybrid Communication (Polling + WebSocket)

The system uses both approaches for reliability:

- **WebSocket**: Immediate updates for settings, commands, real-time events
- **Polling**: Kiosk polls `/api/control/poll` every 500ms as fallback

Commands auto-expire after 5 seconds to prevent stale execution.

### Immutable Core Entities

Certain entities cannot be deleted:

- **"All Images" theme** - Always exists as default
- **"All Images" atmosphere** - Always exists as default
- **"Extras" theme** - Auto-created for imported images

### UUID-Based Filenames

All uploaded images receive UUID filenames:

```
Original: vacation_photo.jpg
Stored as: ab4ab3c1-5c16-48ed-86ab-cd769182ea97.jpg
```

**Benefits:**
- Prevents naming conflicts
- Eliminates special character issues
- Allows deterministic testing

### Atomic File Operations

Settings are written atomically:

1. Write to temporary file
2. Atomic rename to final location
3. Emit WebSocket update

This prevents corruption if process crashes during write.

### 12-Period Day Scheduling

All 12 time periods are independently configurable, each with its own atmosphere assignments, covering the full 24-hour day.

---

## Security Considerations

### Network Security

- **No authentication** - Designed for trusted local network only
- **Do not expose to internet** without adding authentication
- Consider using reverse proxy (nginx) for production

### Port 80 Binding

The Flask server binds to port 80 without root:

```bash
# Capability set on Python binary
sudo setcap 'cap_net_bind_service=+ep' /path/to/python
```

### File Upload Validation

- **Max file size**: 50MB enforced server-side
- **Allowed extensions**: png, jpg, jpeg, gif, webp, bmp
- **UUID filenames**: Prevents path traversal attacks

### Input Sanitization

- Theme/atmosphere names sanitized before storage
- File paths validated before operations
- JSON parsing with error handling

---

## Deployment Workflow

From development machine to Raspberry Pi:

```bash
# 1. Stop services
ssh user@pi "sudo systemctl stop kiosk-display.service"

# 2. Sync code (excludes runtime data)
rsync -avz --exclude 'venv/' --exclude 'images/' \
  --exclude 'settings.json' --exclude '.git/' \
  ./ user@pi:~/kiosk_images/

# 3. Start services
ssh user@pi "sudo systemctl start kiosk.target"

# 4. Verify both services running
ssh user@pi "sudo systemctl status kiosk-display.service"
ssh user@pi "sudo systemctl status kiosk-firefox.service"
```

See `CLAUDE.md` for complete deployment instructions with credentials.
