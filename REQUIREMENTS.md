# Requirements Specification

Testable requirements for the Art Kiosk system, organized by functional area with test traceability.

## Table of Contents

- [System Overview](#system-overview)
- [Requirements Summary](#requirements-summary)
- [1. Image Management](#1-image-management)
- [2. Theme Management](#2-theme-management)
- [3. Atmosphere Management](#3-atmosphere-management)
- [4. Day Scheduling](#4-day-scheduling)
- [5. Image Cropping](#5-image-cropping)
- [6. Remote Control](#6-remote-control)
- [7. Smart Reload System](#7-smart-reload-system)
- [8. Video Playback](#8-video-playback)
- [9. Slideshow Display](#9-slideshow-display)
- [10. Settings Persistence](#10-settings-persistence)
- [11. WebSocket Communication](#11-websocket-communication)
- [12. Debug Console](#12-debug-console)
- [13. Performance](#13-performance)
- [14. Security](#14-security)
- [Test Data Requirements](#test-data-requirements)
- [Test Environment](#test-environment)

---

## System Overview

| Property | Value |
|----------|-------|
| Display Resolution | 2560x2880 (portrait) |
| Server | Flask on port 80 |
| Frontend | HTML/JavaScript + Socket.IO |
| Storage | JSON file (settings.json) |
| Image Formats | PNG, JPG, JPEG, GIF, WebP, BMP |
| Video Support | YouTube via mpv + yt-dlp |

---

## Requirements Summary

| Category | Count | Coverage |
|----------|-------|----------|
| Image Management | 16 | Upload, listing, toggle, delete |
| Theme Management | 14 | Creation, assignment, selection |
| Atmosphere Management | 9 | Creation, mapping, selection |
| Day Scheduling | 17 | Toggle, periods, transitions |
| Image Cropping | 15 | Storage, tool, display |
| Remote Control | 10 | WebSocket commands, jump |
| Smart Reload | 11 | Change detection, vectors |
| Video Playback | 16 | Management, playback, transitions |
| Slideshow Display | 12 | Transitions, modes, controls |
| Settings Persistence | 6 | Format, updates |
| WebSocket | 6 | Connection, broadcasting |
| Debug Console | 7 | Logging, actions |
| Performance | 5 | Response times, resources |
| Security | 3 | File validation |
| **Total** | **147** | |

---

## 1. Image Management

### 1.1 Image Upload

| ID | Requirement | Test |
|----|-------------|------|
| REQ-IMG-001 | System SHALL accept image uploads via POST /api/images | Upload valid image, verify UUID filename |
| REQ-IMG-002 | System SHALL reject uploads exceeding 50MB | Upload 51MB file, expect error |
| REQ-IMG-003 | System SHALL reject unsupported file formats | Upload .txt file, expect error |
| REQ-IMG-004 | Uploaded images SHALL be assigned UUID filenames | Verify format: `[uuid].ext` |
| REQ-IMG-005 | New uploads SHALL auto-assign to active theme | Active theme "Nature", upload, verify assigned |
| REQ-IMG-006 | System SHALL send jump command after upload | Verify WebSocket jump command sent |

### 1.2 Image Listing

| ID | Requirement | Test |
|----|-------------|------|
| REQ-IMG-007 | GET /api/images SHALL return all images with metadata | Verify array of image objects |
| REQ-IMG-008 | enabled_only=true SHALL filter disabled images | 5 images (3 enabled), verify 3 returned |
| REQ-IMG-009 | Images SHALL be randomized using shuffle_id | Same shuffle_id → identical order |
| REQ-IMG-010 | Theme/atmosphere change SHALL regenerate shuffle_id | Switch theme, verify new shuffle_id |

### 1.3 Image Enable/Disable

| ID | Requirement | Test |
|----|-------------|------|
| REQ-IMG-011 | POST toggle SHALL toggle enabled state | enabled=true → toggle → false |
| REQ-IMG-012 | Disabled images SHALL NOT appear in kiosk | Disable, verify not in enabled_only |
| REQ-IMG-013 | Toggle SHALL persist in settings.json | Toggle, verify settings updated |

### 1.4 Image Deletion

| ID | Requirement | Test |
|----|-------------|------|
| REQ-IMG-014 | DELETE SHALL remove image file | Delete, verify file removed |
| REQ-IMG-015 | Deletion SHALL remove from all themes | In 2 themes, delete, verify removed |
| REQ-IMG-016 | Deletion SHALL remove crop data | Has crop, delete, verify removed |

---

## 2. Theme Management

### 2.1 Theme Creation

| ID | Requirement | Test |
|----|-------------|------|
| REQ-THEME-001 | POST /api/themes SHALL create new theme | Create, verify in settings |
| REQ-THEME-002 | New themes SHALL have 3600s default interval | Create, verify interval=3600 |
| REQ-THEME-003 | Theme names SHALL be unique | Create duplicate, expect error |
| REQ-THEME-004 | "All Images" SHALL NOT be deletable | DELETE All Images, expect 400 |

### 2.2 Theme Assignment

| ID | Requirement | Test |
|----|-------------|------|
| REQ-THEME-005 | POST themes SHALL update image themes | Assign ["Nature", "Urban"], verify |
| REQ-THEME-006 | Images SHALL support multiple themes | Assign to 3 themes, verify all 3 |
| REQ-THEME-007 | Removing from theme SHALL update settings | Remove, verify settings updated |

### 2.3 Theme Selection

| ID | Requirement | Test |
|----|-------------|------|
| REQ-THEME-008 | POST /api/themes/active SHALL set active theme | Set, verify active_theme |
| REQ-THEME-009 | Activating theme SHALL clear atmosphere | Atmosphere active, activate theme, verify null |
| REQ-THEME-010 | Activating theme SHALL regenerate shuffle_id | Record, activate, verify changed |
| REQ-THEME-011 | "All Images" SHALL show all enabled images | Verify all enabled returned |
| REQ-THEME-012 | Other themes SHALL filter to assigned only | "Nature" has 3, verify only 3 |

### 2.4 Theme Interval

| ID | Requirement | Test |
|----|-------------|------|
| REQ-THEME-013 | POST interval SHALL update theme interval | Update to 1800, verify |
| REQ-THEME-014 | Active theme interval SHALL set slideshow interval | Active interval=1800, verify global |

---

## 3. Atmosphere Management

### 3.1 Atmosphere Creation

| ID | Requirement | Test |
|----|-------------|------|
| REQ-ATM-001 | POST /api/atmospheres SHALL create atmosphere | Create, verify in settings |
| REQ-ATM-002 | New atmospheres SHALL have 3600s default interval | Create, verify interval=3600 |
| REQ-ATM-003 | "All Images" SHALL NOT be deletable | DELETE All Images, expect 400 |

### 3.2 Atmosphere-Theme Mapping

| ID | Requirement | Test |
|----|-------------|------|
| REQ-ATM-004 | POST themes SHALL assign themes to atmosphere | Assign, verify atmosphere_themes |
| REQ-ATM-005 | Atmosphere SHALL show images from all themes | 3+2 images in themes, verify 5 |

### 3.3 Atmosphere Selection

| ID | Requirement | Test |
|----|-------------|------|
| REQ-ATM-006 | POST active SHALL set active atmosphere | Set, verify active_atmosphere |
| REQ-ATM-007 | Activating atmosphere SHALL clear theme | Theme active, activate atm, verify |
| REQ-ATM-008 | Activating atmosphere SHALL regenerate shuffle_id | Record, activate, verify changed |
| REQ-ATM-009 | Atmosphere interval SHALL override theme interval | Atm=1800, theme=3600, verify 1800 |

---

## 4. Day Scheduling

### 4.1 Day Scheduling Toggle

| ID | Requirement | Test |
|----|-------------|------|
| REQ-DAY-001 | POST toggle SHALL enable/disable day scheduling | Enable, verify setting=true |
| REQ-DAY-002 | Enabling SHALL disable manual atmosphere selection | Verify badges disabled in UI |
| REQ-DAY-003 | Disabling SHALL revert to "All Images" | Disable, verify active_atmosphere |

### 4.2 Time Period Configuration

| ID | Requirement | Test |
|----|-------------|------|
| REQ-DAY-004 | System SHALL support 12 time periods (6 × 2-hour + 6 mirrors) | Verify current_time_period |
| REQ-DAY-005 | POST atmospheres SHALL assign to time period | Assign, verify day_times |
| REQ-DAY-006 | Changes SHALL mirror to corresponding period | Update Time 1, verify Time 7 |
| REQ-DAY-007 | Changing atmospheres SHALL regenerate shuffle_id | Update, verify changed |

**Time Period Definitions:**

| Period | Hours | Mirrors |
|--------|-------|---------|
| 1 | 6 AM - 8 AM | 7 (6 PM - 8 PM) |
| 2 | 8 AM - 10 AM | 8 (8 PM - 10 PM) |
| 3 | 10 AM - 12 PM | 9 (10 PM - 12 AM) |
| 4 | 12 PM - 2 PM | 10 (12 AM - 2 AM) |
| 5 | 2 PM - 4 PM | 11 (2 AM - 4 AM) |
| 6 | 4 PM - 6 PM | 12 (4 AM - 6 AM) |

### 4.3 Hour Boundary Transitions

| ID | Requirement | Test |
|----|-------------|------|
| REQ-DAY-008 | System SHALL check hour boundaries every 60 seconds | Verify checkHourBoundary() interval |
| REQ-DAY-009 | Crossing boundary SHALL reload images for new period | Mock 7:59→8:00, verify checkForImageChanges() |
| REQ-DAY-010 | Transitions SHALL override cadence settings | Cadence=3600s, boundary at 8:00, verify transition |
| REQ-DAY-011 | Checking SHALL start when day scheduling enabled | Enable, verify timer started |
| REQ-DAY-012 | Checking SHALL stop when disabled | Disable, verify timer cleared |

### 4.4 UI Display

| ID | Requirement | Test |
|----|-------------|------|
| REQ-DAY-013 | Heading SHALL show actual atmosphere | Verify "Current Images - Atmosphere: X" |
| REQ-DAY-014 | Multiple atmospheres SHALL be comma-separated | ["A", "B"], verify "A, B" |
| REQ-DAY-015 | Empty period SHALL show "All Images" | No atmospheres, verify heading |
| REQ-DAY-016 | Green border SHALL highlight current period | Verify CSS on current period |
| REQ-DAY-017 | Labels SHALL show AM/PM cycle dynamically | Mock 10:00 → AM labels |

---

## 5. Image Cropping

### 5.1 Crop Data Storage

| ID | Requirement | Test |
|----|-------------|------|
| REQ-CROP-001 | Crop data SHALL be stored in image_crops | Save, verify format in settings |
| REQ-CROP-002 | Coordinates SHALL be in original image dimensions | 2000×2000, crop 500×500, verify |

**Crop Data Format:**
```json
{
  "x": 107, "y": 103,
  "width": 1790, "height": 1793,
  "imageWidth": 2000, "imageHeight": 2000
}
```

### 5.2 Crop Tool

| ID | Requirement | Test |
|----|-------------|------|
| REQ-CROP-003 | Tool SHALL initialize with display aspect (0.889) | Open, verify 2560/2880 ratio |
| REQ-CROP-004 | Tool SHALL load existing crop if present | Has crop, verify loaded |
| REQ-CROP-005 | Aspect lock SHALL default to checked | Open, verify checkbox |
| REQ-CROP-006 | Locked SHALL maintain 2560/2880 ratio | Lock, resize, verify ratio |
| REQ-CROP-007 | Unlocked SHALL allow free-form | Unlock, verify variable ratio |
| REQ-CROP-008 | Clear SHALL reset without saving | Clear, verify settings unchanged |
| REQ-CROP-009 | Save SHALL persist crop data | Save, verify settings updated |

### 5.3 Crop Display

| ID | Requirement | Test |
|----|-------------|------|
| REQ-CROP-010 | Crop SHALL use non-uniform scaling (no black bars) | Verify scaleX ≠ scaleY |
| REQ-CROP-011 | Entire crop zone SHALL be visible | Verify no clipping |
| REQ-CROP-012 | Position: offsetX = -cropX × scaleX | Crop at (100,200), verify |
| REQ-CROP-013 | Thumbnails SHALL use same algorithm | Compare to kiosk display |

### 5.4 Crop Updates

| ID | Requirement | Test |
|----|-------------|------|
| REQ-CROP-014 | Changes SHALL update kiosk within 2 seconds | Save, verify reload |
| REQ-CROP-015 | Extra image crops SHALL update immediately | Crop extra, verify WebSocket |

---

## 6. Remote Control

### 6.1 WebSocket Commands

| ID | Requirement | Test |
|----|-------------|------|
| REQ-REMOTE-001 | send_command SHALL send to kiosk | Emit, verify broadcast |
| REQ-REMOTE-002 | next SHALL advance slide | index=2, next → index=3 |
| REQ-REMOTE-003 | prev SHALL go back | index=2, prev → index=1 |
| REQ-REMOTE-004 | pause SHALL stop slideshow | Verify timer cleared |
| REQ-REMOTE-005 | play SHALL resume slideshow | Verify timer restarted |
| REQ-REMOTE-006 | reload SHALL refresh display | Verify loadImages() called |
| REQ-REMOTE-007 | jump SHALL navigate to image | jump photo.jpg, verify index |
| REQ-REMOTE-008 | jump_extra SHALL show overlay | Verify overlay created |
| REQ-REMOTE-009 | Commands SHALL execute within 500ms | Measure execution time |

**Available Commands:**
- `next`, `prev`, `pause`, `play`, `reload`
- `jump` (with image_name)
- `jump_extra` (with image_name)
- `resume_from_extra`, `refresh_extra_crop`

### 6.2 Click-to-Jump

| ID | Requirement | Test |
|----|-------------|------|
| REQ-REMOTE-010 | Clicking thumbnail SHALL jump kiosk | Click, verify jump sent |

---

## 7. Smart Reload System

### 7.1 Change Detection

| ID | Requirement | Test |
|----|-------------|------|
| REQ-RELOAD-001 | System SHALL check every 2 seconds | Verify 2000ms interval |
| REQ-RELOAD-002 | Image vector change SHALL trigger reload | Enable image, verify reload |
| REQ-RELOAD-003 | Interval change SHALL trigger reload | Change interval, verify reload |
| REQ-RELOAD-004 | Crop change SHALL trigger reload | Update crop, verify reload |
| REQ-RELOAD-005 | shuffle_id change SHALL reload from index 0 | Switch theme, verify from first |
| REQ-RELOAD-006 | Time period change SHALL trigger reload | Mock transition, verify reload |
| REQ-RELOAD-007 | No changes SHALL NOT trigger reload | 10 checks stable, verify none |

### 7.2 Vector Comparison

| ID | Requirement | Test |
|----|-------------|------|
| REQ-RELOAD-008 | Vector SHALL be array of enabled names | 3 enabled, verify length=3 |
| REQ-RELOAD-009 | Comparison SHALL detect additions | Add image, verify detected |
| REQ-RELOAD-010 | Comparison SHALL detect removals | Remove image, verify detected |
| REQ-RELOAD-011 | Order SHALL be deterministic per shuffle_id | Same ID, verify same order |

---

## 8. Video Playback

### 8.1 Video Management

| ID | Requirement | Test |
|----|-------------|------|
| REQ-VIDEO-001 | POST /api/videos SHALL add by URL | Add YouTube URL, verify |
| REQ-VIDEO-002 | DELETE SHALL remove video | Delete, verify removed |
| REQ-VIDEO-003 | GET SHALL list all videos | Verify list returned |

### 8.2 Video Playback

| ID | Requirement | Test |
|----|-------------|------|
| REQ-VIDEO-004 | Videos SHALL play via mpv fullscreen | Execute, verify mpv running |
| REQ-VIDEO-005 | System SHALL show /loading during playback | Start, verify navigation |
| REQ-VIDEO-006 | Server timer SHALL track interval | Start, verify timer set |

### 8.3 Video Auto-Transition

| ID | Requirement | Test |
|----|-------------|------|
| REQ-VIDEO-007 | Video SHALL auto-transition after interval | Wait interval, verify transition |
| REQ-VIDEO-008 | Transition SHALL go to correct next item | Index 2 → index 3 |
| REQ-VIDEO-009 | Auto-transition SHALL emit show_kiosk | Verify WebSocket with next item |

### 8.4 Video Stop Conditions

| ID | Requirement | Test |
|----|-------------|------|
| REQ-VIDEO-010 | Video SHALL stop on theme change | Playing, change theme, verify stopped |
| REQ-VIDEO-011 | Video SHALL stop on atmosphere switch | Playing, switch, verify stopped |
| REQ-VIDEO-012 | Video SHALL stop on reload command | Playing, reload, verify stopped |
| REQ-VIDEO-013 | Video SHALL stop on jump to image | Playing, jump, verify stopped |
| REQ-VIDEO-014 | Video SHALL stop on interval advance | Playing, timer, verify stopped |

### 8.5 Video Thumbnails

| ID | Requirement | Test |
|----|-------------|------|
| REQ-VIDEO-015 | Thumbnails SHALL generate after 20s playback | Add, wait, verify thumbnail |
| REQ-VIDEO-016 | Thumbnails SHALL be included in backup | Backup, verify thumbnails/ copied |

---

## 9. Slideshow Display

### 9.1 Image Transitions

| ID | Requirement | Test |
|----|-------------|------|
| REQ-SLIDE-001 | Dissolve SHALL use 0.8s animation | Measure ≈800ms |
| REQ-SLIDE-002 | Transitions SHALL be smooth (no flicker) | Visual test |
| REQ-SLIDE-003 | Interval SHALL match settings.interval | Set 5s, verify timing |
| REQ-SLIDE-004 | Manual navigation SHALL be instant | Press next, verify immediate |

### 9.2 Fill/Fit Modes

| ID | Requirement | Test |
|----|-------------|------|
| REQ-SLIDE-005 | Fill mode SHALL cover entire viewport | Verify no black bars |
| REQ-SLIDE-006 | Fit mode SHALL show complete image | Verify entire image visible |
| REQ-SLIDE-007 | F key SHALL toggle modes | Press F, verify toggle |
| REQ-SLIDE-008 | ?fit=true SHALL start in fit mode | Load URL, verify mode |

### 9.3 Keyboard Controls

| ID | Requirement | Test |
|----|-------------|------|
| REQ-SLIDE-009 | Space/Right SHALL advance | Press, verify index++ |
| REQ-SLIDE-010 | Left SHALL go back | Press, verify index-- |
| REQ-SLIDE-011 | F SHALL toggle fill mode | Press, verify toggle |
| REQ-SLIDE-012 | R SHALL reload display | Press, verify reload |

---

## 10. Settings Persistence

### 10.1 Settings Format

| ID | Requirement | Test |
|----|-------------|------|
| REQ-SET-001 | settings.json SHALL be valid JSON | Parse, verify no errors |
| REQ-SET-002 | Settings SHALL include all required fields | Verify all fields present |
| REQ-SET-003 | "All Images" theme/atmosphere SHALL always exist | Verify both exist |

**Required Fields:**
- `interval`, `check_interval`, `dissolve_enabled`
- `enabled_images`, `image_crops`, `shuffle_id`
- `themes`, `image_themes`, `active_theme`
- `atmospheres`, `atmosphere_themes`, `active_atmosphere`
- `day_scheduling_enabled`, `day_times`

### 10.2 Settings Updates

| ID | Requirement | Test |
|----|-------------|------|
| REQ-SET-004 | GET /api/settings SHALL return current | Verify complete object |
| REQ-SET-005 | POST /api/settings SHALL update | Update, verify persisted |
| REQ-SET-006 | Changes SHALL broadcast settings_update | Update, verify WebSocket |

---

## 11. WebSocket Communication

### 11.1 Connection

| ID | Requirement | Test |
|----|-------------|------|
| REQ-WS-001 | Socket.IO SHALL connect on page load | Verify socket.connected |
| REQ-WS-002 | Disconnect SHALL trigger reconnection | Simulate, verify reconnect |
| REQ-WS-003 | Reconnection SHALL reload debug messages | Reconnect, verify refresh |

### 11.2 Broadcasting

| ID | Requirement | Test |
|----|-------------|------|
| REQ-WS-004 | settings_update SHALL broadcast to all | 2 clients, verify both receive |
| REQ-WS-005 | image_list_changed SHALL broadcast | Upload, verify broadcast |
| REQ-WS-006 | remote_command SHALL broadcast to kiosk | Send, verify kiosk receives |

---

## 12. Debug Console

### 12.1 Logging

| ID | Requirement | Test |
|----|-------------|------|
| REQ-DEBUG-001 | POST /api/debug/log SHALL accept messages | Send, verify stored |
| REQ-DEBUG-002 | System SHALL store last 500 messages | Send 600, verify 500 |
| REQ-DEBUG-003 | Messages SHALL include timestamp | Send, verify timestamp |
| REQ-DEBUG-004 | debug_message SHALL broadcast to clients | Send, verify received |

### 12.2 UI Actions

| ID | Requirement | Test |
|----|-------------|------|
| REQ-DEBUG-005 | Console SHALL auto-scroll to last 20 lines | 100 messages, verify scroll |
| REQ-DEBUG-006 | Clear SHALL delete all messages | Clear, verify empty |
| REQ-DEBUG-007 | Clip SHALL copy to clipboard | Click, verify clipboard |

---

## 13. Performance

### 13.1 Response Times

| ID | Requirement | Test |
|----|-------------|------|
| REQ-PERF-001 | API endpoints SHALL respond within 200ms | Measure < 200ms |
| REQ-PERF-002 | Image transitions SHALL complete within 1s | Measure timing |
| REQ-PERF-003 | WebSocket commands SHALL execute within 500ms | Measure execution |

### 13.2 Resource Usage

| ID | Requirement | Test |
|----|-------------|------|
| REQ-PERF-004 | Smart reload SHALL check every 2 seconds | Monitor requests |
| REQ-PERF-005 | Hour boundary check SHALL occur every 60 seconds | Monitor logs |

---

## 14. Security

### 14.1 File Upload Validation

| ID | Requirement | Test |
|----|-------------|------|
| REQ-SEC-001 | System SHALL reject executable uploads | Upload .exe, expect rejection |
| REQ-SEC-002 | System SHALL validate file extensions | Upload image.jpg.exe, reject |
| REQ-SEC-003 | Size limit SHALL be enforced server-side | Send 100MB, expect rejection |

---

## Test Data Requirements

### Images

| Type | Quantity | Details |
|------|----------|---------|
| Test images | 20+ | Mix of jpg, png, gif, webp |
| Size range | 500KB - 10MB | Various file sizes |
| Dimensions | Various | Portrait, landscape, square |
| Edge cases | 3+ | Very wide (5:1), very tall (1:5), exact (2560×2880) |

### Themes

| Theme | Images | Purpose |
|-------|--------|---------|
| All Images | Default | Built-in, cannot delete |
| TestTheme10Images | 10 | Standard testing |
| TestTheme15Images | 15 | Standard testing |
| TestTheme19ImagesVideoEnd | 19+1 | Video testing |
| TestThemeVideosOnly | 5 videos | Video-only testing |

### Atmospheres

| Atmosphere | Themes | Purpose |
|------------|--------|---------|
| All Images | All | Built-in default |
| TestAtmosphereImageThemes | 2 | Period 1 testing |
| TestAtmosphereAllThemes | 4 | Period 2 testing |

### Day Schedule

| Period | Atmosphere | Purpose |
|--------|------------|---------|
| 1 (6-8 AM) | TestAtmosphereImageThemes | Transition testing |
| 2 (8-10 AM) | TestAtmosphereAllThemes | Transition testing |
| 3-6 | Various | Coverage |

---

## Test Environment

### Prerequisites

- Flask server running on port 80
- 2560×2880 display (or virtual)
- Socket.IO active
- settings.json initialized
- images/ and EXTRA_IMAGES/ directories

### Test Execution Order

1. Image management (upload, toggle, delete)
2. Theme management (create, assign, select)
3. Atmosphere management (create, map, select)
4. Day scheduling (toggle, periods, transitions)
5. Image cropping (save, display)
6. Remote control (commands, jump)
7. Smart reload (detection, vectors)
8. Video playback (management, transitions)
9. WebSocket communication (events)
10. Performance tests

### Screenshot Capture Points

| Scenario | Description |
|----------|-------------|
| Initial display | Kiosk in fill mode |
| Fit mode | Complete image visible |
| Mid-transition | Dissolve in progress |
| Cropped image | Custom crop displayed |
| Management UI | Themes configured |
| Day scheduling | Time periods configured |
| Debug console | Logs visible |
| Extra image | Overlay displayed |

---

## Known Limitations

1. **Time precision**: Hour boundary checks every 60s (up to 60s delay)
2. **Shuffle determinism**: Predictable per shuffle_id, unpredictable across sessions
3. **Browser compatibility**: Tested on Firefox; Chrome not guaranteed
4. **Resolution**: UI optimized for 2560×2880
5. **Network latency**: Assumes local network (<10ms RTT)
