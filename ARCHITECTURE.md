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
- Image crop data storage and retrieval
- Settings persistence (JSON file storage)
- Theme and atmosphere management
- Remote control command queue
- Debug logging
- Image filtering by enabled state, active theme, and active atmosphere
- Randomization with consistent seeding via shuffle_id
- Auto-preview newly uploaded images on kiosk display

**Technology Stack**:
- Python 3.7+
- Flask 3.0.0
- Werkzeug 3.0.1
- Cropper.js 1.6.1 (JavaScript image cropping library)

### 2. Frontend - Display (kiosk.html)

**Role**: Fullscreen slideshow display optimized for the kiosk monitor.

**Key Features**:
- Automatic slideshow with configurable interval
- Image cropping with automatic scaling to fill display
- Dissolve transitions (always enabled)
- Smart reload algorithm with shuffle_id detection
- Randomized image ordering that changes with theme/atmosphere switches
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
│  │  - Check shuffle_id (order changes)        │         │
│  │  - Reload if changed (reset to index 0)   │         │
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

**Design**: Professional dark theme with black background (#000000), dark containers (#1a1a1a), white text, and color-coded badges (purple for atmospheres, blue for themes).

**Sections**:
1. **Remote Control** - Control buttons with LED indicators
2. **Atmospheres** - Create, delete, select active atmosphere, assign themes to atmospheres (purple badges)
3. **Themes** - Create, delete, select active theme (includes permanent "All Images" theme, blue badges)
4. **Upload Images** - Drag-and-drop upload area
5. **Current Images** - Grid of thumbnails with controls (filtered by active atmosphere or theme, randomized order)
6. **Debug Console** - Live logs from kiosk display (toggle with DEBUG button)

**Interactive Features**:
- Click image thumbnail to jump to that image
- Crop images using Cropper.js modal interface
- Enable/disable images with checkboxes
- Assign images to themes via dropdown
- Assign themes to atmospheres via modal
- Remove images from themes by clicking theme tags
- LED indicators show play/pause state
- Cropped thumbnails preview actual kiosk display
- Mutual exclusivity: selecting atmosphere deselects theme, and vice versa
- Auto-preview: newly uploaded images automatically display on kiosk

## Data Model

### Settings (settings.json)

```json
{
  "interval": 3600,
  "check_interval": 2,
  "enabled_images": {
    "photo1.jpg": true,
    "photo2.jpg": false
  },
  "dissolve_enabled": true,
  "themes": {
    "All Images": {
      "name": "All Images",
      "created": 1699752000,
      "interval": 3600
    },
    "Nature": {
      "name": "Nature",
      "created": 1699752100,
      "interval": 3600
    },
    "Urban": {
      "name": "Urban",
      "created": 1699752200,
      "interval": 1800
    }
  },
  "image_themes": {
    "photo1.jpg": ["Nature"],
    "photo2.jpg": ["Nature", "Urban"],
    "photo3.jpg": ["Urban"]
  },
  "active_theme": "All Images",
  "atmospheres": {
    "Evening": {
      "name": "Evening",
      "created": 1699752300,
      "interval": 1800
    },
    "Morning": {
      "name": "Morning",
      "created": 1699752400,
      "interval": 3600
    }
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

**Fields**:
- `interval` (I): Current slideshow transition interval in seconds (synced with active theme/atmosphere interval)
- `check_interval` (C): How often to check for changes (always 2)
- `enabled_images`: Per-image enabled/disabled state
- `dissolve_enabled`: Enable smooth fade transitions (always true)
- `themes`: Dictionary of theme definitions, each theme has its own `interval` in seconds (default: 3600 = 60 minutes)
  - **"All Images"**: Permanent theme that cannot be deleted, shows all enabled images regardless of theme assignments
- `image_themes`: Image-to-theme mappings (many-to-many)
- `active_theme`: Currently selected theme (always set, defaults to "All Images"). Active theme's interval is used for slideshow when no atmosphere is active.
- `atmospheres`: Dictionary of atmosphere definitions, each with its own `interval` in seconds
- `atmosphere_themes`: Atmosphere-to-theme mappings (one-to-many, atmospheres contain themes)
- `active_atmosphere`: Currently selected atmosphere (null if none active). Takes priority over active_theme for filtering and interval.
- `shuffle_id`: Random seed for consistent image ordering. Regenerates on theme/atmosphere change to create new random order.
- `image_crops`: Per-image crop data containing x, y, width, height coordinates in original image space, plus original imageWidth and imageHeight for scaling calculations

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
- `GET /api/images?enabled_only=true` - List images (filtered by enabled, active atmosphere, and active theme, randomized by shuffle_id)
- `POST /api/images` - Upload image (multipart/form-data, auto-assigns to active theme and sends jump command for preview)
- `DELETE /api/images/<filename>` - Delete image
- `POST /api/images/<filename>/toggle` - Toggle enabled state
- `POST /api/images/<filename>/themes` - Update theme assignments

### Settings
- `GET /api/settings` - Get all settings
- `POST /api/settings` - Update settings (complete object)

### Themes
- `GET /api/themes` - List themes and active theme
- `POST /api/themes` - Create theme (default interval: 3600 seconds = 60 minutes)
- `DELETE /api/themes/<name>` - Delete theme (cannot delete "All Images")
- `POST /api/themes/<name>/interval` - Update theme interval
- `POST /api/themes/active` - Set active theme (clears active_atmosphere, updates global interval, regenerates shuffle_id)

### Atmospheres
- `GET /api/atmospheres` - List all atmospheres
- `POST /api/atmospheres` - Create atmosphere (`{"name": "Atmosphere Name"}`, default interval: 3600 seconds)
- `DELETE /api/atmospheres/<name>` - Delete atmosphere
- `POST /api/atmospheres/<name>/interval` - Update atmosphere interval (seconds)
- `POST /api/atmospheres/active` - Set active atmosphere (`{"atmosphere_name": "Name"}` or null, clears active_theme, regenerates shuffle_id)
- `POST /api/atmospheres/<name>/themes` - Update themes in atmosphere (`{"themes": ["Theme1", "Theme2"]}`)

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
2. Fetch current settings (interval, dissolve, crops, shuffle_id)
3. Compare V with VP (previous vector)
4. Compare interval with previous interval
5. Compare crop data with previous crop data
6. Compare shuffle_id with previous shuffle_id
7. If anything changed:
   - Log change
   - Reload slideshow
   - If shuffle_id changed: start from index 0 (new order)
   - Update VP = V, previous shuffle_id
8. Else:
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

### 3. Hierarchical Filtering (Atmospheres & Themes)

**Purpose**: Display images based on active atmosphere or theme with priority hierarchy.

**Hierarchy**: Atmospheres → Themes → Images

**Logic**:
```python
def list_images(enabled_only=False):
    # Determine filtering strategy
    allowed_themes = None
    if enabled_only:
        if active_atmosphere:
            # Priority 1: Atmosphere active - get all themes in that atmosphere
            allowed_themes = set(atmosphere_themes.get(active_atmosphere, []))
        elif active_theme and active_theme != 'All Images':
            # Priority 2: Only theme active - use that single theme
            allowed_themes = {active_theme}
        # Priority 3: "All Images" or no selection - no filtering

    for image in all_images:
        # Skip disabled images if filtering
        if enabled_only and not image.enabled:
            continue

        # Apply theme filtering if we have allowed_themes
        if allowed_themes is not None:
            image_themes_set = set(image.themes)
            if not image_themes_set.intersection(allowed_themes):
                continue  # Image not in any allowed theme

        yield image

    # Randomize with consistent seed
    random.seed(shuffle_id)
    random.shuffle(images)
    random.seed()  # Reset to random for other operations
```

**Key Points**:
- **Atmosphere takes priority**: If atmosphere is active, theme selection is ignored for filtering
- **"All Images" theme**: Shows all enabled images (no theme filtering)
- **Other themes**: Only show images assigned to that theme
- **Atmospheres**: Show all images from all themes in that atmosphere
- **Mutual exclusivity**: Setting atmosphere clears theme (and vice versa) for clean UX
- **Randomization**: Images shuffled with consistent seed (shuffle_id) for same order across kiosk and management
- **shuffle_id regeneration**: New random order on every theme/atmosphere change

### 4. Crop Scaling Algorithm

**Purpose**: Scale cropped image regions to fill the entire kiosk display (2560x2880).

**Implementation**:
```javascript
// Given: crop region (x, y, width, height) in original image coordinates
// Goal: Display only the crop region, scaled to fill the viewport

1. Calculate scale to make crop fill viewport (cover behavior):
   scaleX = viewportWidth / cropWidth
   scaleY = viewportHeight / cropHeight
   scale = Math.max(scaleX, scaleY)  // Ensures crop fills entire screen

2. Calculate scaled image dimensions:
   scaledImageWidth = originalImageWidth * scale
   scaledImageHeight = originalImageHeight * scale

3. Calculate position to show crop region:
   offsetX = -(cropX * scale)  // Shift image left to show crop
   offsetY = -(cropY * scale)  // Shift image up to show crop

4. Center any overflow:
   centerX = (viewportWidth - (cropWidth * scale)) / 2
   centerY = (viewportHeight - (cropHeight * scale)) / 2

5. Apply to image element:
   img.style.width = scaledImageWidth + 'px'
   img.style.height = scaledImageHeight + 'px'
   img.style.left = (offsetX + centerX) + 'px'
   img.style.top = (offsetY + centerY) + 'px'
   img.style.objectFit = 'fill'  // Critical: allows scaling
```

**Key Points**:
- Uses `Math.max(scaleX, scaleY)` to ensure crop region fills entire screen
- `object-fit: fill` is essential - `none` would prevent scaling
- Black bars appear on only one dimension (top/bottom OR left/right)
- Container uses `overflow: hidden` to clip to viewport
- Same algorithm used for both kiosk display and management thumbnails (different viewport sizes)

### 5. Image Randomization with Shuffle ID

**Purpose**: Provide randomized image order that stays consistent between kiosk and management, but changes with each theme/atmosphere switch.

**Implementation**:
```python
# In settings.json
shuffle_id = random.random()  # Value like 0.123456789

# When listing images:
random.seed(shuffle_id)
random.shuffle(images)
random.seed()  # Reset to unpredictable random

# When changing theme/atmosphere:
settings['shuffle_id'] = random.random()  # New random order
save_settings(settings)
```

**Key Points**:
- **Consistent order**: Same shuffle_id produces identical order on kiosk and management
- **Truly random**: Each theme/atmosphere switch generates new shuffle_id
- **No duplicates**: Uses Python's random.shuffle (Fisher-Yates algorithm)
- **All images included**: Every enabled image appears exactly once
- **Kiosk detection**: Tracks previousShuffleId to detect order changes and restart from index 0

### 6. Auto-Preview on Upload

**Purpose**: Immediately display newly uploaded images on the kiosk for review.

**Implementation**:
```python
# In upload endpoint:
def upload_image():
    # Save image to disk
    save_file(filename)

    # Auto-assign to active theme (if not "All Images")
    if active_theme and active_theme != 'All Images':
        image_themes[filename] = [active_theme]
        save_settings(settings)

    # Send jump command to kiosk
    current_command = {
        'command': 'jump',
        'image_name': filename
    }
    command_timestamp = time.time()

    return success_response
```

**Jump Command with Reload Fallback**:
```javascript
// In kiosk.html executeCommand():
case 'jump':
    const imageIndex = images.findIndex(img => img.name === imageName);
    if (imageIndex !== -1) {
        // Image found - jump to it
        showSlide(imageIndex);
        if (!isPaused) startSlideshow();
    } else {
        // Image not in current list - reload to include it
        await loadImages(0, imageName);
    }
```

**Key Points**:
- **Theme assignment**: New image added to active theme automatically
- **Immediate display**: Jump command executes within 500ms via polling
- **Reload fallback**: If image not in current list, triggers full reload
- **Prevents duplicates**: loadImages() clears existing slides before rebuilding

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
- Current image name (for reload positioning)
- Play/pause state
- Fill mode (cover/contain)
- Dissolve enabled

**Ephemeral**:
- Image vector (V, VP)
- Previous shuffle_id (for change detection)
- Slideshow timer
- Poll intervals

### Client-Side State (manage.html)

**Persistent** (via API):
- None (all state on server)

**Ephemeral**:
- Available themes (loaded on page load)
- Available atmospheres (loaded on page load)
- Active theme (loaded on page load)
- Active atmosphere (loaded on page load)
- LED states (play/pause indicators)
- Debug console enabled/disabled

### Server-Side State

**Persistent** (settings.json):
- Interval, check_interval
- Enabled images
- Dissolve enabled
- Themes, image_themes, active_theme
- Atmospheres, atmosphere_themes, active_atmosphere
- shuffle_id (for consistent randomization)
- Image crops

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

### Adding New Theme/Atmosphere Features
- Theme descriptions and metadata
- Theme colors/styling
- Scheduled theme/atmosphere switching (time-based)
- Random theme/atmosphere selection
- Atmosphere-specific intervals (already implemented)
- Theme-specific intervals (already implemented)
- Nested atmospheres (atmosphere hierarchies)

## Testing Recommendations

### Manual Testing
1. **Image Management**: Upload, enable/disable, delete, crop
2. **Themes**: Create, assign, delete, switch active, verify "All Images" can't be deleted
3. **Atmospheres**: Create, assign themes, delete, switch active
4. **Hierarchy**: Verify atmosphere takes priority over theme
5. **Mutual Exclusivity**: Verify selecting atmosphere clears theme and vice versa
6. **Randomization**: Switch themes/atmospheres, verify order changes and matches between kiosk and management
7. **Auto-Preview**: Upload image, verify kiosk immediately jumps to it
8. **Remote Control**: All buttons, LED states, pause behavior
9. **Smart Reload**: Change images, interval, dissolve, shuffle_id - verify reload
10. **Click-to-Jump**: Click thumbnails, verify immediate switch
11. **Autostart**: Reboot, verify services start correctly

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

### Theme/Atmosphere Filtering Not Working
1. Verify active theme or atmosphere is set
2. Check images have themes assigned
3. If using atmospheres, verify themes are assigned to the atmosphere
4. Look at API response: `/api/images?enabled_only=true`
5. Check settings.json for correct theme/atmosphere mappings
6. Verify mutual exclusivity: only one of active_theme or active_atmosphere should be set

### Randomization Not Working
1. Check shuffle_id exists in settings.json
2. Verify shuffle_id changes when switching themes/atmospheres
3. Ensure both kiosk and management fetch with `enabled_only=true`
4. Check that kiosk detects shuffle_id changes in checkForImageChanges()
5. Verify kiosk restarts from index 0 when shuffle_id changes

### Auto-Preview Not Working
1. Verify jump command is sent on upload (check server logs)
2. Check that uploaded image is assigned to active theme
3. Verify kiosk polling is active (500ms interval)
4. Check that loadImages() clears existing slides before rebuilding
5. Look for errors in kiosk console (F12)

## Future Enhancements

### Recently Implemented Features
- [x] Hierarchical organization (Atmospheres → Themes → Images)
- [x] Image randomization with consistent ordering
- [x] Dark theme UI
- [x] Auto-preview uploaded images on kiosk
- [x] Image cropping with crop region preview
- [x] Per-theme intervals
- [x] Per-atmosphere intervals
- [x] Remote control via polling

### Potential Features
- [ ] Video support (MP4, WebM)
- [ ] Audio narration per image
- [ ] Scheduled theme/atmosphere switching (time-based, e.g., "Evening" atmosphere activates at 6 PM)
- [ ] Image transitions (slide, fade, zoom, ken burns effect)
- [ ] Multi-monitor support
- [ ] EXIF data display (camera, date, location)
- [ ] Image ratings/favorites
- [ ] Playlists (ordered sequences with manual ordering)
- [ ] Weather/clock overlays
- [ ] REST API for external control (Home Assistant, IFTTT, etc.)
- [ ] Nested atmospheres (atmosphere hierarchies)
- [ ] Theme/atmosphere descriptions and metadata
- [ ] Image search and filtering

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
