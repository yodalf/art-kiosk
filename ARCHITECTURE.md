# Architecture Documentation

## Overview

The Art Kiosk is a web-based image display system designed for Raspberry Pi with a portrait monitor (2560x2880). It consists of a Flask backend server, two HTML frontends (management and display), and system integration components for autostart.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Raspberry Pi                           │
│                                                             │
│  ┌──────────────┐         ┌─────────────────┐               │
│  │   Flask      │◄────────┤  Firefox        │               │
│  │   Server     │         │  (Kiosk Mode)   │               │
│  │  (Port 80)   │         │  /view          │               │
│  │              │         └─────────────────┘               │
│  │   app.py     │                                           │
│  │              │         ┌─────────────────┐               │
│  │   REST API   │◄────────┤  Management     │               │
│  │              │         │  Interface      │               │
│  │   Settings   │         │  (Any Browser)  │               │
│  │   Storage    │         │  /              │               │
│  └──────────────┘         └─────────────────┘               │
│         ▲                                                   │
│         │                                                   │
│  ┌──────┴─────────┐                                         │
│  │  settings.json  │                                        │
│  │  images/        │                                        │
│  └────────────────┘                                         │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Backend (app.py)

**Role**: Flask web server providing REST API and serving HTML templates.

**Key Responsibilities**:
- Image management (upload, delete, list)
- Settings persistence (JSON file storage)
- Theme management
- Remote control command queue
- Debug logging
- Image filtering by enabled state and active theme

**Technology Stack**:
- Python 3.7+
- Flask 3.0.0
- Werkzeug 3.0.1

### 2. Frontend - Display (kiosk.html)

**Role**: Fullscreen slideshow display optimized for the kiosk monitor.

**Key Features**:
- Automatic slideshow with configurable interval
- Dissolve transitions (optional)
- Smart reload algorithm
- Remote control command polling
- Keyboard controls
- Debug logging to server

**Update Mechanism**:
```
┌─────────────────────────────────────────────────────────┐
│  Kiosk Display (kiosk.html)                             │
│                                                         │
│  ┌────────────────────────────────────────────┐         │
│  │  Poll Loop (every 500ms)                   │         │
│  │  - Check for remote commands               │         │
│  │  - Execute: next, prev, pause, play, jump  │         │
│  └────────────────────────────────────────────┘         │
│                                                         │
│  ┌────────────────────────────────────────────┐         │
│  │  Check Loop (every 2 seconds - C interval) │         │
│  │  - Fetch enabled images (V)                │         │
│  │  - Compare with previous vector (VP)       │         │
│  │  - Check interval setting                  │         │
│  │  - Check dissolve setting                  │         │
│  │  - Reload if changed                       │         │
│  └────────────────────────────────────────────┘         │
│                                                         │
│  ┌────────────────────────────────────────────┐         │
│  │  Slideshow Timer (every I seconds)         │         │
│  │  - Advance to next image                   │         │
│  │  - Can be paused/resumed                   │         │
│  └────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

### 3. Frontend - Management (manage.html)

**Role**: Web interface for configuring and controlling the kiosk.

**Sections**:
1. **Stats** - Total images and size
2. **Remote Control** - Control buttons with LED indicators
3. **Settings** - Interval, dissolve transition
4. **Themes** - Create, delete, select active theme
5. **Current Images** - Grid of thumbnails with controls
6. **Upload Images** - Drag-and-drop upload area
7. **Debug Console** - Live logs from kiosk display

**Interactive Features**:
- Click image thumbnail to jump to that image
- Enable/disable images with checkboxes
- Assign images to themes via dropdown
- Remove images from themes by clicking theme tags
- LED indicators show play/pause state

## Data Model

### Settings (settings.json)

```json
{
  "interval": 10,
  "check_interval": 2,
  "enabled_images": {
    "photo1.jpg": true,
    "photo2.jpg": false
  },
  "dissolve_enabled": true,
  "themes": {
    "Nature": {
      "name": "Nature",
      "created": 1699752000
    },
    "Urban": {
      "name": "Urban",
      "created": 1699752100
    }
  },
  "image_themes": {
    "photo1.jpg": ["Nature"],
    "photo2.jpg": ["Nature", "Urban"],
    "photo3.jpg": ["Urban"]
  },
  "active_theme": "Nature"
}
```

**Fields**:
- `interval` (I): Slideshow transition interval (stored in seconds, displayed in minutes in UI)
- `check_interval` (C): How often to check for changes (always 2)
- `enabled_images`: Per-image enabled/disabled state
- `dissolve_enabled`: Enable smooth fade transitions
- `themes`: Dictionary of theme definitions
- `image_themes`: Image-to-theme mappings (many-to-many)
- `active_theme`: Currently selected theme (null = all images)

### Image Model

**Storage**: Filesystem (`images/` directory)

**Metadata** (computed):
```json
{
  "name": "photo.jpg",
  "url": "/images/photo.jpg",
  "size": 1024768,
  "enabled": true,
  "themes": ["Nature", "Art"]
}
```

## API Endpoints

### Images
- `GET /api/images?enabled_only=true` - List images (filtered by enabled and active theme)
- `POST /api/images` - Upload image (multipart/form-data)
- `DELETE /api/images/<filename>` - Delete image
- `POST /api/images/<filename>/toggle` - Toggle enabled state
- `POST /api/images/<filename>/themes` - Update theme assignments

### Settings
- `GET /api/settings` - Get all settings
- `POST /api/settings` - Update settings (complete object)

### Themes
- `GET /api/themes` - List themes and active theme
- `POST /api/themes` - Create theme
- `DELETE /api/themes/<name>` - Delete theme
- `POST /api/themes/active` - Set active theme

### Remote Control
- `POST /api/control/send` - Send command to kiosk
  - Commands: `next`, `prev`, `pause`, `play`, `reload`, `jump`
  - Jump requires: `{"command": "jump", "image_name": "photo.jpg"}`
- `GET /api/control/poll` - Poll for commands (called by kiosk)

### Debug
- `POST /api/debug/log` - Log message from kiosk
- `GET /api/debug/messages` - Get recent log messages (last 100)
- `POST /api/debug/clear` - Clear debug log

## Key Algorithms

### 1. Smart Reload Algorithm

**Purpose**: Minimize unnecessary reloads while keeping display in sync.

**Implementation**:
```javascript
// Every C seconds (2 seconds):
1. Fetch current enabled images → V (new vector)
2. Fetch current settings (interval, dissolve)
3. Compare V with VP (previous vector)
4. Compare interval with previous interval
5. If anything changed:
   - Log change
   - Reload slideshow
   - Update VP = V
6. Else:
   - Continue playing
```

**Benefits**:
- No polling overhead on slideshow timing
- Immediate updates (within 2 seconds)
- Smooth playback when stable
- Debug logs show what changed

### 2. Remote Control Polling

**Purpose**: Allow management interface to control kiosk without WebSockets.

**Implementation**:
```
Management Interface                Kiosk Display
       │                                  │
       ├──POST /api/control/send──────────┤
       │   {"command": "pause"}           │
       │                                  │
       │                            ┌─────▼────┐
       │                            │ Poll loop│
       │                            │ (500ms)  │
       │                            └─────┬────┘
       │                                  │
       │◄─────GET /api/control/poll───────┤
       │    {"command": "pause"}          │
       │                                  │
       │                            Execute pause
```

**Command Queue**:
- Server stores one command at a time
- Command expires after 5 seconds
- Cleared after being retrieved once
- Kiosk polls every 500ms

### 3. Theme Filtering

**Purpose**: Display only images belonging to the active theme.

**Logic**:
```python
def list_images(enabled_only=False):
    for image in all_images:
        # Skip disabled images if filtering
        if enabled_only and not image.enabled:
            continue
        
        # Skip images not in active theme if filtering
        if enabled_only and active_theme:
            if active_theme not in image.themes:
                continue
        
        yield image
```

**Key Points**:
- Theme filtering only applies when `enabled_only=true`
- Images without themes are excluded when a theme is active
- `active_theme=null` shows all enabled images
- Images can belong to multiple themes

## File Structure

```
kiosk_images/
├── app.py                      # Flask server
├── requirements.txt            # Python dependencies
├── settings.json              # Runtime settings (auto-generated)
├── images/                    # Uploaded images (auto-generated)
│
├── templates/
│   ├── kiosk.html            # Display interface
│   └── manage.html           # Management interface
│
├── start-kiosk.sh            # Start script (cleanup + server + browser)
├── stop-kiosk.sh             # Stop script
├── install-autostart.sh      # Systemd installer
│
├── kiosk-display.service     # Systemd service for Flask
├── kiosk-firefox.service     # Systemd service for Firefox
│
├── README.md                 # User documentation
├── QUICKSTART.md            # Quick start guide
├── ARCHITECTURE.md          # This file
├── LICENSE                  # GPLv3 license
└── .gitignore              # Git ignore rules
```

## System Integration

### Autostart with Systemd

Two services work together:

**kiosk-display.service** (Flask server):
- Starts after network
- Runs as user with virtual environment
- Binds to port 80 (requires `CAP_NET_BIND_SERVICE` capability)
- Auto-restarts on failure

**kiosk-firefox.service** (Display):
- Starts after `kiosk-display.service` and `graphical.target`
- Waits 5 seconds for server to be ready
- Disables screen blanking via `xset`
- Launches Firefox in kiosk mode pointing to `/view`
- Starts `unclutter` to hide cursor
- Auto-restarts on failure

### Startup Sequence

```
Boot
  ↓
Network Ready
  ↓
kiosk-display.service starts
  ↓
Flask server running on port 80
  ↓
Desktop Environment Ready
  ↓
kiosk-firefox.service starts
  ↓
Wait 5 seconds
  ↓
Disable screen blanking
  ↓
Start unclutter (hide cursor)
  ↓
Launch Firefox → http://localhost/view
  ↓
Kiosk display showing
```

## State Management

### Client-Side State (kiosk.html)

**Persistent**:
- Current image index
- Play/pause state
- Fill mode (cover/contain)
- Dissolve enabled

**Ephemeral**:
- Image vector (V, VP)
- Slideshow timer
- Poll intervals

### Client-Side State (manage.html)

**Persistent** (via API):
- None (all state on server)

**Ephemeral**:
- Available themes (loaded on page load)
- Active theme (loaded on page load)
- LED states (play/pause indicators)
- Debug console enabled/disabled

### Server-Side State

**Persistent** (settings.json):
- Interval, check_interval
- Enabled images
- Dissolve enabled
- Themes, image_themes, active_theme

**Ephemeral** (in-memory):
- Current remote control command
- Command timestamp
- Debug message queue (last 100)

## Performance Considerations

### Image Loading
- Images served directly by Flask from filesystem
- No processing or resizing on server
- Browser handles all scaling via CSS
- Consider pre-resizing large images for better performance

### Polling Overhead
- Remote control polling: 500ms (minimal overhead)
- Settings check: 2 seconds (minimal API calls)
- Debug console: 1 second when enabled

### Memory Usage
- Flask server: ~50-100MB
- Firefox (kiosk): ~200-500MB depending on image count
- Debug message queue: Limited to last 100 messages

## Security Considerations

### Current Design
- **No authentication** - Designed for local network use only
- **Port 80** - Requires elevated privileges
- **File uploads** - Validated by extension only
- **Direct file serving** - No path traversal protection needed (Flask handles this)

### Recommendations for Production
1. Add authentication (Basic Auth or OAuth)
2. Use reverse proxy (nginx) with SSL
3. Add rate limiting
4. Implement file upload size limits (currently 50MB)
5. Add CSRF protection for state-changing operations
6. Consider running behind firewall

## Extension Points

### Adding New Remote Commands
1. Add command to `send_command()` validation in `app.py`
2. Add case to `executeCommand()` in `kiosk.html`
3. Add button/control in `manage.html`
4. Update LED handling if needed

### Adding New Settings
1. Add to `defaults` in `get_settings()` in `app.py`
2. Add to `settings.json` schema documentation
3. Add UI control in `manage.html`
4. Add loading in `loadSettings()` in `manage.html`
5. Add saving in `saveSettings()` in `manage.html`
6. Add checking in `checkForImageChanges()` in `kiosk.html` if needed

### Adding New Themes Features
- Theme descriptions
- Theme colors/styling
- Scheduled theme switching
- Random theme selection
- Theme-specific intervals

## Testing Recommendations

### Manual Testing
1. **Image Management**: Upload, enable/disable, delete
2. **Themes**: Create, assign, delete, switch active
3. **Remote Control**: All buttons, LED states, pause behavior
4. **Smart Reload**: Change images, interval, dissolve - verify reload
5. **Click-to-Jump**: Click thumbnails, verify immediate switch
6. **Autostart**: Reboot, verify services start correctly

### Browser Compatibility
- Primary: Firefox (kiosk mode)
- Management: Any modern browser (Chrome, Firefox, Safari, Edge)

### Network Testing
- Access management from different devices
- Verify remote control works across network
- Test with multiple concurrent management sessions

## Troubleshooting Guide

### Display Not Updating
1. Check debug console - look for "Enabled images changed"
2. Verify settings.json is writable
3. Check browser console (F12) for errors
4. Verify Flask server is running: `sudo systemctl status kiosk-display`

### Remote Control Not Working
1. Check command polling in browser console
2. Verify `/api/control/poll` returns commands
3. Check 500ms poll interval is running
4. Verify LED states update in management interface

### Autostart Issues
1. Check service status: `sudo systemctl status kiosk-firefox`
2. View logs: `sudo journalctl -u kiosk-firefox -f`
3. Verify DISPLAY=:0 and XAUTHORITY set correctly
4. Check user permissions

### Theme Filtering Not Working
1. Verify active theme is set
2. Check images have themes assigned
3. Look at API response: `/api/images?enabled_only=true`
4. Check settings.json for correct theme mappings

## Future Enhancements

### Potential Features
- [ ] Video support (MP4, WebM)
- [ ] Audio narration per image
- [ ] Scheduled theme switching (time-based)
- [ ] Image transitions (slide, fade, zoom)
- [ ] Multi-monitor support
- [ ] EXIF data display
- [ ] Image ratings/favorites
- [ ] Playlists (ordered sequences)
- [ ] Weather/clock overlays
- [ ] REST API for external control (Home Assistant, etc.)

### Architecture Improvements
- [ ] WebSocket instead of polling (real-time updates)
- [ ] Database (SQLite) instead of JSON
- [ ] Image thumbnails (performance)
- [ ] CDN for static assets
- [ ] Progressive web app (offline support)
- [ ] Docker containerization
- [ ] Multi-user support with authentication

## License

This project is licensed under the GNU General Public License v3.0.
