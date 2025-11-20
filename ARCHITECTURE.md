# Architecture Documentation

## System Overview

The Kiosk Image Display System is a Flask-based web application designed for displaying images and videos on a Raspberry Pi with a 2560x2880 portrait monitor.

## Components

### Backend (app.py)

- **Flask server** on port 80
- **Flask-SocketIO** for real-time WebSocket communication
- **JSON file storage** (settings.json) for persistence
- **In-memory state** for current video, commands, and debug messages

### Frontend Templates

- **kiosk.html** - Main slideshow display with dissolve transitions
- **manage.html** - Unified management interface
- **loading.html** - Loading screen during video playback
- **backup.html** - Backup and restore interface

### External Dependencies

- **mpv** - Video playback
- **yt-dlp** - YouTube video download
- **xdotool** - Window management for video playback

## Data Flow

### Image/Video Display Flow

1. User enables images/videos in manage.html
2. Kiosk polls `/api/images?enabled_only=true` every 2 seconds
3. Changes detected via vector comparison (V vs VP)
4. Slideshow reloads with new items maintaining position

### Video Playback Flow

1. User clicks Play or video appears in slideshow
2. `execute_mpv` endpoint called
3. Firefox navigates to `/loading`
4. mpv starts in fullscreen
5. Server-side timer tracks interval
6. Timer fires → mpv stops → Firefox returns to `/view?image=next_item`
7. Kiosk continues to next item in list

### Backup/Restore Flow

1. Backup creates timestamped folder with:
   - images/ directory copy
   - thumbnails/ directory copy
   - video_urls.json
   - settings.json
2. Restore copies all files back and emits WebSocket events
3. Kiosk reloads with restored state

## Key Algorithms

### Smart Reload

```
Every 2 seconds:
  V = current enabled images vector
  if V != VP or interval changed or crops changed or shuffle_id changed:
    reload slideshow
  VP = V
```

### Video Auto-Transition

```
On video start:
  next_item = images[(video_index + 1) % len(images)]
  start_timer(interval)

On timer fire:
  kill mpv
  emit show_kiosk with next_item
```

### Theme/Atmosphere Filtering

- **"All Images"**: Shows all enabled items
- **Theme active**: Filter to items in that theme
- **Atmosphere active**: Combine all themes in atmosphere
- **Day Scheduling**: Use current time period's atmospheres

## API Architecture

### RESTful Endpoints

- `/api/images` - Image CRUD operations
- `/api/videos` - Video CRUD operations
- `/api/themes` - Theme management
- `/api/atmospheres` - Atmosphere management
- `/api/backup` - Backup/restore operations
- `/api/control/send` - Remote control commands

### WebSocket Events

- `remote_command` - Kiosk control commands
- `settings_update` - Settings changed
- `image_list_changed` - Images added/removed
- `show_kiosk` - Navigate to kiosk view
- `show_loading` - Navigate to loading page

## State Management

### Persistent State (settings.json)

- enabled_images, enabled_videos
- themes, atmospheres, image_themes, video_themes
- active_theme, active_atmosphere
- day_scheduling_enabled, day_times
- image_crops, shuffle_id, interval

### In-Memory State

- current_kiosk_image - Last reported image
- current_video_id - Playing video
- video_transition_timer - Auto-transition timer
- video_next_item - Next item after video
- debug_messages - Debug log queue

## Systemd Services

### kiosk-display.service

- Starts Flask server
- Binds to port 80 via Linux capabilities
- Kills mpv on stop

### kiosk-firefox.service

- Starts Firefox in kiosk mode
- Waits for server to be ready
- Manages Firefox profile cleanup

## Security Considerations

- No authentication (designed for local network)
- Port 80 binding via capabilities (no root)
- Input validation on file uploads
- Maximum file size limits
