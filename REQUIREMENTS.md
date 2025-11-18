# Test Requirements Specification

This document defines testable requirements for the Art Kiosk system. Requirements are organized by functional area and formatted for automated test generation.

## System Overview

- **Display Resolution**: 2560x2880 (portrait orientation)
- **Server**: Flask on port 80
- **Frontend**: HTML/JavaScript with Socket.IO
- **Storage**: JSON file-based (settings.json)
- **Image Formats**: PNG, JPG, JPEG, GIF, WebP, BMP

---

## 1. Image Management

### 1.1 Image Upload

**REQ-IMG-001**: System SHALL accept image uploads via POST /api/images
- **Method**: POST multipart/form-data
- **Max size**: 50MB
- **Valid formats**: .png, .jpg, .jpeg, .gif, .webp, .bmp
- **Expected response**: 200 OK with JSON `{"success": true, "filename": "uuid.ext"}`
- **Test**: Upload valid image, verify UUID-based filename assigned

**REQ-IMG-002**: System SHALL reject uploads exceeding 50MB
- **Test**: Upload 51MB file, expect error response

**REQ-IMG-003**: System SHALL reject unsupported file formats
- **Test**: Upload .txt file, expect error response

**REQ-IMG-004**: Uploaded images SHALL be assigned UUID-based filenames
- **Format**: `[uuid].ext` (e.g., `ab4ab3c1-5c16-48ed-86ab-cd769182ea97.jpg`)
- **Test**: Upload image, verify filename matches UUID pattern with original extension

**REQ-IMG-005**: Newly uploaded images SHALL auto-assign to active theme (if not "All Images")
- **Precondition**: Active theme is "Nature"
- **Test**: Upload image, verify `image_themes[filename]` contains ["Nature"]

**REQ-IMG-006**: System SHALL send jump command to kiosk after upload
- **Test**: Upload image, verify WebSocket `send_command` with `{"command": "jump", "image_name": filename}`

### 1.2 Image Listing

**REQ-IMG-007**: GET /api/images SHALL return all images with metadata
- **Response format**: `[{"name": "file.jpg", "enabled": true, "themes": ["Nature"]}]`
- **Test**: Call endpoint, verify array of image objects

**REQ-IMG-008**: GET /api/images?enabled_only=true SHALL filter disabled images
- **Precondition**: Have 5 images, 3 enabled, 2 disabled
- **Test**: Call with filter, verify only 3 images returned

**REQ-IMG-009**: Images SHALL be randomized using shuffle_id seed
- **Test**: Get images with same shuffle_id twice, verify identical order

**REQ-IMG-010**: Changing theme/atmosphere SHALL regenerate shuffle_id
- **Test**: Switch theme, verify shuffle_id changed in settings.json

### 1.3 Image Enable/Disable

**REQ-IMG-011**: POST /api/images/<filename>/toggle SHALL toggle enabled state
- **Test**: Image enabled=true, toggle, verify enabled=false

**REQ-IMG-012**: Disabled images SHALL NOT appear in kiosk display
- **Test**: Disable image, verify not in GET /api/images?enabled_only=true

**REQ-IMG-013**: Toggle SHALL persist in settings.json
- **Test**: Toggle image, verify settings.enabled_images[filename] updated

### 1.4 Image Deletion

**REQ-IMG-014**: DELETE /api/images/<filename> SHALL remove image file
- **Test**: Delete image, verify file removed from images/ directory

**REQ-IMG-015**: Deletion SHALL remove from all theme assignments
- **Test**: Image in 2 themes, delete, verify removed from settings.image_themes

**REQ-IMG-016**: Deletion SHALL remove crop data
- **Test**: Image has crop, delete, verify removed from settings.image_crops

---

## 2. Theme Management

### 2.1 Theme Creation

**REQ-THEME-001**: POST /api/themes SHALL create new theme
- **Request**: `{"name": "Nature"}`
- **Test**: Create theme, verify in settings.themes

**REQ-THEME-002**: New themes SHALL have default interval of 3600 seconds
- **Test**: Create theme, verify `themes["Nature"]["interval"] == 3600`

**REQ-THEME-003**: Theme names SHALL be unique
- **Test**: Create "Nature", attempt duplicate, expect error

**REQ-THEME-004**: "All Images" theme SHALL NOT be deletable
- **Test**: DELETE /api/themes/All%20Images, expect 400 error

### 2.2 Theme Assignment

**REQ-THEME-005**: POST /api/images/<filename>/themes SHALL update image themes
- **Request**: `{"themes": ["Nature", "Urban"]}`
- **Test**: Assign themes, verify settings.image_themes[filename] = ["Nature", "Urban"]

**REQ-THEME-006**: Images SHALL support multiple theme assignments
- **Test**: Assign image to 3 themes, verify all 3 in image_themes

**REQ-THEME-007**: Removing image from theme SHALL update settings
- **Test**: Assign to theme, remove, verify theme removed from array

### 2.3 Theme Selection

**REQ-THEME-008**: POST /api/themes/active SHALL set active theme
- **Request**: `{"theme_name": "Nature"}`
- **Test**: Set active, verify settings.active_theme = "Nature"

**REQ-THEME-009**: Activating theme SHALL clear active_atmosphere
- **Test**: Atmosphere active, activate theme, verify active_atmosphere = null

**REQ-THEME-010**: Activating theme SHALL regenerate shuffle_id
- **Test**: Record shuffle_id, activate theme, verify shuffle_id changed

**REQ-THEME-011**: "All Images" theme SHALL show all enabled images
- **Test**: Active theme = "All Images", verify /api/images?enabled_only=true returns all enabled

**REQ-THEME-012**: Other themes SHALL filter to assigned images only
- **Precondition**: "Nature" theme has 3 images, 2 other images exist
- **Test**: Active theme = "Nature", verify only 3 images returned

### 2.4 Theme Interval

**REQ-THEME-013**: POST /api/themes/<name>/interval SHALL update interval
- **Request**: `{"interval": 1800}`
- **Test**: Update interval, verify settings.themes["Nature"]["interval"] = 1800

**REQ-THEME-014**: Active theme interval SHALL set slideshow interval
- **Test**: Active theme interval=1800, verify settings.interval = 1800

---

## 3. Atmosphere Management

### 3.1 Atmosphere Creation

**REQ-ATM-001**: POST /api/atmospheres SHALL create new atmosphere
- **Request**: `{"name": "Evening"}`
- **Test**: Create atmosphere, verify in settings.atmospheres

**REQ-ATM-002**: New atmospheres SHALL have default interval of 3600 seconds
- **Test**: Create atmosphere, verify interval = 3600

**REQ-ATM-003**: "All Images" atmosphere SHALL NOT be deletable
- **Test**: DELETE /api/atmospheres/All%20Images, expect 400 error

### 3.2 Atmosphere-Theme Mapping

**REQ-ATM-004**: POST /api/atmospheres/<name>/themes SHALL assign themes
- **Request**: `{"themes": ["Nature", "Urban"]}`
- **Test**: Assign themes, verify settings.atmosphere_themes["Evening"] = ["Nature", "Urban"]

**REQ-ATM-005**: Atmosphere SHALL show images from all assigned themes
- **Precondition**: "Evening" has themes ["Nature", "Urban"], Nature has 3 images, Urban has 2
- **Test**: Active atmosphere = "Evening", verify 5 images returned (union)

### 3.3 Atmosphere Selection

**REQ-ATM-006**: POST /api/atmospheres/active SHALL set active atmosphere
- **Request**: `{"atmosphere_name": "Evening"}`
- **Test**: Set active, verify settings.active_atmosphere = "Evening"

**REQ-ATM-007**: Activating atmosphere SHALL clear active_theme
- **Test**: Theme active, activate atmosphere, verify active_theme cleared

**REQ-ATM-008**: Activating atmosphere SHALL regenerate shuffle_id
- **Test**: Record shuffle_id, activate atmosphere, verify changed

**REQ-ATM-009**: Atmosphere interval SHALL take precedence over theme interval
- **Test**: Atmosphere interval=1800, contained theme interval=3600, verify settings.interval=1800

---

## 4. Day Scheduling

### 4.1 Day Scheduling Toggle

**REQ-DAY-001**: POST /api/day/toggle SHALL enable/disable day scheduling
- **Request**: `{"enabled": true}`
- **Test**: Enable, verify settings.day_scheduling_enabled = true

**REQ-DAY-002**: Enabling day scheduling SHALL disable manual atmosphere selection
- **Test**: Day scheduling enabled, verify atmosphere badges disabled in UI

**REQ-DAY-003**: Disabling day scheduling SHALL revert to "All Images" atmosphere
- **Test**: Disable, verify settings.active_atmosphere = "All Images"

### 4.2 Time Period Configuration

**REQ-DAY-004**: System SHALL support 6 time periods of 2 hours each
- **Time periods**:
  - Time 1: 6 AM - 8 AM (mirrors at 6 PM - 8 PM)
  - Time 2: 8 AM - 10 AM (mirrors at 8 PM - 10 PM)
  - Time 3: 10 AM - 12 PM (mirrors at 10 PM - 12 AM)
  - Time 4: 12 PM - 2 PM (mirrors at 12 AM - 2 AM)
  - Time 5: 2 PM - 4 PM (mirrors at 2 AM - 4 AM)
  - Time 6: 4 PM - 6 PM (mirrors at 4 AM - 6 AM)
- **Test**: Verify GET /api/day/status returns correct current_time_period based on system time

**REQ-DAY-005**: POST /api/day/times/<time_id>/atmospheres SHALL assign atmospheres to time period
- **Request**: `{"atmospheres": ["Evening", "Nature"]}`
- **Test**: Assign, verify settings.day_times["1"]["atmospheres"] = ["Evening", "Nature"]

**REQ-DAY-006**: Time period changes SHALL automatically mirror to corresponding period
- **Test**: Update Time 1, verify Time 7 has identical atmospheres

**REQ-DAY-007**: Changing time atmospheres SHALL regenerate shuffle_id
- **Test**: Update time period, verify shuffle_id changed

### 4.3 Hour Boundary Transitions

**REQ-DAY-008**: System SHALL check for hour boundary crossings every 60 seconds
- **Test**: Mock time, verify checkHourBoundary() called every 60s when day scheduling enabled

**REQ-DAY-009**: Crossing hour boundary SHALL force immediate image transition
- **Test**: Mock time change from 7:59 to 8:00, verify nextSlide() called immediately

**REQ-DAY-010**: Hour transitions SHALL override atmosphere/theme cadence
- **Test**: Cadence=3600s, hour boundary crossed at 8:00, verify transition occurs regardless

**REQ-DAY-011**: Hour boundary checking SHALL start when day scheduling enabled
- **Test**: Enable day scheduling, verify hourCheckTimer started

**REQ-DAY-012**: Hour boundary checking SHALL stop when day scheduling disabled
- **Test**: Disable day scheduling, verify hourCheckTimer cleared

### 4.4 Current Time Period Display

**REQ-DAY-013**: "Current Images" heading SHALL show actual time period atmosphere
- **Precondition**: Day scheduling enabled, current time period has "Nature" atmosphere
- **Test**: Verify heading text = "Current Images - Atmosphere: Nature"

**REQ-DAY-014**: Multiple atmospheres SHALL be comma-separated in heading
- **Precondition**: Time period has ["Evening", "Nature"]
- **Test**: Verify heading = "Current Images - Atmospheres: Evening, Nature"

**REQ-DAY-015**: Empty time period SHALL show "All Images" in heading
- **Test**: Time period with no atmospheres, verify heading = "Current Images - All Images"

**REQ-DAY-016**: Green border SHALL highlight current time period
- **Test**: Verify current time period div has green border CSS

---

## 5. Image Cropping

### 5.1 Crop Data Storage

**REQ-CROP-001**: Crop data SHALL be stored in settings.image_crops
- **Format**: `{"x": 107, "y": 103, "width": 1790, "height": 1793, "imageWidth": 2000, "imageHeight": 2000}`
- **Test**: Save crop, verify format in settings.json

**REQ-CROP-002**: Crop coordinates SHALL be in original image dimensions
- **Test**: Image 2000x2000, crop 500x500 at (250,250), verify stored values

### 5.2 Crop Tool Initialization

**REQ-CROP-003**: Opening crop tool SHALL initialize with display aspect ratio (0.889)
- **Test**: Open crop for new image, verify crop aspect = 2560/2880

**REQ-CROP-004**: Crop tool SHALL load existing crop data if present
- **Precondition**: Image has saved crop
- **Test**: Open crop tool, verify cropper.getData() matches saved crop

**REQ-CROP-005**: Aspect ratio lock checkbox SHALL default to checked
- **Test**: Open crop tool, verify checkbox.checked = true

### 5.3 Aspect Ratio Lock

**REQ-CROP-006**: Locked aspect ratio SHALL maintain 2560/2880 ratio during resize
- **Test**: Lock enabled, resize crop, verify width/height maintain 0.889 aspect

**REQ-CROP-007**: Unlocked aspect ratio SHALL allow free-form resizing
- **Test**: Unlock checkbox, resize crop to arbitrary dimensions, verify aspect varies

**REQ-CROP-008**: Clear Crop SHALL reset to default aspect ratio without saving
- **Test**: Modify crop, click Clear, verify visual reset, settings.json unchanged

**REQ-CROP-009**: Save Crop SHALL persist current crop data
- **Test**: Modify crop, save, verify settings.image_crops updated

### 5.4 Crop Display Algorithm

**REQ-CROP-010**: Crop SHALL use non-uniform scaling to eliminate black bars
- **Formula**: scaleX = viewportW / cropW, scaleY = viewportH / cropH (independent)
- **Test**: Crop 1000x1500, verify scales differ, no black bars visible

**REQ-CROP-011**: Entire crop zone SHALL be visible on display
- **Test**: Set crop boundaries, verify all crop content visible (no clipping of crop edges)

**REQ-CROP-012**: Crop position SHALL be calculated as offsetX = -cropX * scaleX, offsetY = -cropY * scaleY
- **Test**: Crop at (100, 200), verify image positioned correctly

**REQ-CROP-013**: Cropped thumbnails SHALL use same algorithm as kiosk display
- **Test**: Compare thumbnail crop to kiosk display, verify identical positioning

### 5.5 Crop Updates

**REQ-CROP-014**: Crop changes SHALL update kiosk within 2 seconds
- **Test**: Save crop, verify kiosk reloads within 2s (smart reload interval)

**REQ-CROP-015**: Extra image crops SHALL update immediately via WebSocket
- **Test**: Crop extra image, verify refresh_extra_crop WebSocket message sent

---

## 6. Remote Control

### 6.1 WebSocket Commands

**REQ-REMOTE-001**: send_command WebSocket event SHALL send commands to kiosk
- **Commands**: next, prev, pause, play, reload, jump, jump_extra, resume_from_extra, refresh_extra_crop
- **Test**: Emit send_command, verify remote_command broadcast received

**REQ-REMOTE-002**: next command SHALL advance to next image
- **Test**: Current index=2, send next, verify index=3

**REQ-REMOTE-003**: prev command SHALL go to previous image
- **Test**: Current index=2, send prev, verify index=1

**REQ-REMOTE-004**: pause command SHALL stop automatic slideshow
- **Test**: Send pause, verify slideTimer cleared

**REQ-REMOTE-005**: play command SHALL resume slideshow
- **Test**: Send play, verify slideTimer restarted

**REQ-REMOTE-006**: reload command SHALL refresh kiosk display
- **Test**: Send reload, verify loadImages() called

**REQ-REMOTE-007**: jump command SHALL navigate to specific image
- **Request**: `{"command": "jump", "image_name": "photo.jpg"}`
- **Test**: Send jump, verify currentIndex updated to image position

**REQ-REMOTE-008**: jump_extra command SHALL display extra image overlay
- **Request**: `{"command": "jump_extra", "image_name": "extra.jpg"}`
- **Test**: Send jump_extra, verify overlay div created

**REQ-REMOTE-009**: Commands SHALL execute within 500ms
- **Test**: Send command via WebSocket, measure execution time < 500ms

### 6.2 Click-to-Jump

**REQ-REMOTE-010**: Clicking image thumbnail SHALL jump kiosk to that image
- **Test**: Click thumbnail in management UI, verify jump command sent with correct image_name

---

## 7. Smart Reload System

### 7.1 Change Detection

**REQ-RELOAD-001**: System SHALL check for changes every 2 seconds
- **Test**: Verify checkForImageChanges() called every 2000ms

**REQ-RELOAD-002**: Image vector change SHALL trigger reload
- **Precondition**: Current vector = [img1, img2, img3]
- **Test**: Enable img4, verify reload triggered

**REQ-RELOAD-003**: Interval change SHALL trigger reload
- **Test**: Change theme interval, verify reload triggered

**REQ-RELOAD-004**: Crop data change SHALL trigger reload
- **Test**: Update crop, verify reload triggered

**REQ-RELOAD-005**: shuffle_id change SHALL trigger reload from index 0
- **Test**: Switch theme, verify reload from first image

**REQ-RELOAD-006**: Time period change SHALL trigger reload
- **Test**: Mock time transition, verify reload triggered

**REQ-RELOAD-007**: No changes SHALL NOT trigger reload
- **Test**: Monitor for 10 checks with no changes, verify no reload

### 7.2 Vector Comparison

**REQ-RELOAD-008**: Image vector SHALL be array of enabled image names
- **Format**: `["uuid1.jpg", "uuid2.png", "uuid3.jpg"]`
- **Test**: 3 enabled images, verify vector length = 3

**REQ-RELOAD-009**: Vector comparison SHALL detect additions
- **Test**: Add enabled image, verify vectors differ

**REQ-RELOAD-010**: Vector comparison SHALL detect removals
- **Test**: Disable image, verify vectors differ

**REQ-RELOAD-011**: Vector order SHALL be deterministic (based on shuffle_id)
- **Test**: Same shuffle_id, verify vector order identical across checks

---

## 8. Slideshow Display

### 8.1 Image Transitions

**REQ-SLIDE-001**: Dissolve transition SHALL use 0.8s opacity animation
- **Test**: Measure transition duration ≈ 800ms

**REQ-SLIDE-002**: Transitions SHALL be smooth without flicker
- **Visual test**: Record video of transition, verify no flicker

**REQ-SLIDE-003**: Slideshow interval SHALL match settings.interval
- **Test**: Set interval=5s, measure time between auto-transitions ≈ 5000ms

**REQ-SLIDE-004**: Manual navigation SHALL use instant transitions
- **Test**: Press next, verify immediate transition (no dissolve)

### 8.2 Fill/Fit Modes

**REQ-SLIDE-005**: Fill mode (default) SHALL scale to cover entire viewport
- **Test**: Verify no black bars visible in fill mode

**REQ-SLIDE-006**: Fit mode SHALL show complete image with possible black bars
- **Test**: Switch to fit mode, verify entire image visible

**REQ-SLIDE-007**: F key SHALL toggle between fill and fit modes
- **Test**: Press F, verify mode switched

**REQ-SLIDE-008**: ?fit=true URL parameter SHALL start in fit mode
- **Test**: Load /view?fit=true, verify fillMode = true

### 8.3 Keyboard Controls

**REQ-SLIDE-009**: Space/Right Arrow SHALL advance to next slide
- **Test**: Press space, verify currentIndex incremented

**REQ-SLIDE-010**: Left Arrow SHALL go to previous slide
- **Test**: Press left arrow, verify currentIndex decremented

**REQ-SLIDE-011**: F key SHALL toggle fill mode
- **Test**: See REQ-SLIDE-007

**REQ-SLIDE-012**: R key SHALL reload display
- **Test**: Press R, verify page reload

---

## 9. Settings Persistence

### 9.1 Settings Format

**REQ-SET-001**: settings.json SHALL be valid JSON
- **Test**: Parse settings.json, verify no JSON errors

**REQ-SET-002**: Settings SHALL include all required fields
- **Required**: interval, check_interval, enabled_images, dissolve_enabled, themes, image_themes, active_theme, atmospheres, atmosphere_themes, active_atmosphere, day_scheduling_enabled, day_times, shuffle_id, image_crops
- **Test**: Verify all fields present in fresh settings.json

**REQ-SET-003**: Default "All Images" theme/atmosphere SHALL always exist
- **Test**: Parse settings, verify themes["All Images"] and atmospheres["All Images"] exist

### 9.2 Settings Updates

**REQ-SET-004**: GET /api/settings SHALL return current settings
- **Test**: Call endpoint, verify returns complete settings object

**REQ-SET-005**: POST /api/settings SHALL update settings
- **Test**: Update interval, verify persisted to settings.json

**REQ-SET-006**: Settings changes SHALL broadcast settings_update WebSocket event
- **Test**: Update setting, verify WebSocket broadcast received by clients

---

## 10. Debug Console

### 10.1 Logging

**REQ-DEBUG-001**: POST /api/debug/log SHALL accept log messages from kiosk
- **Request**: `{"message": "Test log", "level": "info"}`
- **Test**: Send log, verify stored in debug_messages deque

**REQ-DEBUG-002**: System SHALL store last 500 debug messages
- **Test**: Send 600 messages, verify GET /api/debug/messages returns only 500 most recent

**REQ-DEBUG-003**: Debug messages SHALL include timestamp
- **Format**: `{"message": "text", "level": "info", "timestamp": 1234567890}`
- **Test**: Send log, verify timestamp present in response

### 10.2 Real-time Updates

**REQ-DEBUG-004**: debug_message WebSocket event SHALL broadcast logs to all clients
- **Test**: Send log from kiosk, verify management UI receives via WebSocket

**REQ-DEBUG-005**: Debug console SHALL auto-scroll to show last 20 lines
- **Test**: Load debug page with 100 messages, verify scrolled to show lines 81-100

### 10.3 Console Actions

**REQ-DEBUG-006**: Clear Console button SHALL delete all messages
- **Test**: Click clear, verify GET /api/debug/messages returns empty array

**REQ-DEBUG-007**: Clip button SHALL copy logs to clipboard
- **Test**: Click clip, verify clipboard contains formatted log text

---

## 11. Upload Interface

### 11.1 Drag and Drop

**REQ-UPLOAD-001**: Drag-and-drop SHALL accept multiple files
- **Test**: Drop 5 images, verify all 5 uploaded

**REQ-UPLOAD-002**: Upload progress SHALL be displayed
- **Visual test**: Upload large file, verify progress indicator appears

**REQ-UPLOAD-003**: File input SHALL accept direct selection
- **Test**: Use file picker, verify upload works

### 11.2 Auto-tagging

**REQ-UPLOAD-004**: Upload page SHALL filter to show only untagged images
- **Precondition**: 3 images with themes, 2 without
- **Test**: Load upload page, verify only 2 images shown

**REQ-UPLOAD-005**: Navigating away SHALL auto-tag with "Extras" theme
- **Test**: Navigate to another page, verify untagged images get "Extras" theme

**REQ-UPLOAD-006**: beforeunload event SHALL trigger auto-tagging
- **Test**: Close tab, verify auto-tagging occurs

---

## 12. Extra Images

### 12.1 Extra Images Management

**REQ-EXTRA-001**: Extra images SHALL be stored in extra-images/ directory
- **Test**: Verify separate directory from main images/

**REQ-EXTRA-002**: Import SHALL move extra image to main images/
- **Test**: Import extra image, verify moved and UUID filename assigned

**REQ-EXTRA-003**: Delete SHALL remove extra image file
- **Test**: Delete extra image, verify file removed

### 12.2 Extra Image Display

**REQ-EXTRA-004**: jump_extra command SHALL create overlay on kiosk
- **Test**: Send jump_extra, verify overlay div with extra image created

**REQ-EXTRA-005**: Clicking extra image SHALL dismiss overlay
- **Test**: Click overlay, verify removed, slideshow resumes

**REQ-EXTRA-006**: Cropping extra image SHALL update overlay immediately
- **Test**: Crop extra image, verify overlay refreshes within 100ms

---

## 13. Search Art Interface

### 13.1 Museum API Integration

**REQ-SEARCH-001**: Search SHALL query museum APIs for portrait paintings
- **APIs**: Rijksmuseum, Art Institute of Chicago, Cleveland Museum, Harvard Art Museums
- **Test**: Search "landscape", verify results returned from APIs

**REQ-SEARCH-002**: Results SHALL be filtered to portrait orientation
- **Aspect ratio**: height > width
- **Test**: Verify all results have height > width

**REQ-SEARCH-003**: Download SHALL save to extra-images/ directory
- **Test**: Download artwork, verify saved to extra-images/ with UUID filename

---

## 14. WebSocket Communication

### 14.1 Connection Management

**REQ-WS-001**: Socket.IO client SHALL connect on page load
- **Test**: Load page, verify socket.connected = true

**REQ-WS-002**: Disconnect SHALL trigger reconnection
- **Test**: Simulate disconnect, verify reconnect event fired

**REQ-WS-003**: Reconnection SHALL reload debug messages
- **Test**: Disconnect and reconnect, verify debug console refreshed

### 14.2 Event Broadcasting

**REQ-WS-004**: settings_update SHALL broadcast to all connected clients
- **Test**: 2 clients connected, update setting, verify both receive event

**REQ-WS-005**: image_list_changed SHALL broadcast when images added/removed
- **Test**: Upload image, verify broadcast received

**REQ-WS-006**: remote_command SHALL broadcast to kiosk clients
- **Test**: Management sends command, verify kiosk receives

---

## 15. Performance Requirements

### 15.1 Response Times

**REQ-PERF-001**: API endpoints SHALL respond within 200ms
- **Test**: Measure response time for GET /api/images, verify < 200ms

**REQ-PERF-002**: Image transitions SHALL complete within 1 second
- **Test**: Measure time from nextSlide() call to visible transition

**REQ-PERF-003**: WebSocket commands SHALL execute within 500ms
- **Test**: Send command, measure execution time

### 15.2 Resource Usage

**REQ-PERF-004**: Smart reload SHALL check every 2 seconds
- **Test**: Monitor network requests, verify one per 2 seconds

**REQ-PERF-005**: Hour boundary check SHALL occur every 60 seconds
- **Test**: Monitor console logs, verify check messages every 60s

---

## 16. Security Requirements

### 16.1 File Upload Validation

**REQ-SEC-001**: System SHALL reject executable file uploads
- **Test**: Upload .exe file, expect rejection

**REQ-SEC-002**: System SHALL validate image file extensions
- **Test**: Upload image.jpg.exe, expect rejection

**REQ-SEC-003**: File size limit SHALL be enforced server-side
- **Test**: Bypass client limit, send 100MB file, expect rejection

---

## Test Data Requirements

### Image Test Set
- **Quantity**: Minimum 20 test images
- **Formats**: Mix of .jpg, .png, .gif, .webp
- **Sizes**: Range from 500KB to 10MB
- **Dimensions**: Various aspect ratios (portrait, landscape, square)
- **Edge cases**: Very wide (5:1), very tall (1:5), exact match (2560x2880)

### Theme Test Set
- **Themes**: All Images (default), Nature, Urban, Portrait, Abstract
- **Image distribution**: Each theme 3-5 images, some images in multiple themes

### Atmosphere Test Set
- **Atmospheres**: All Images (default), Morning, Evening, Night
- **Theme mapping**: Each atmosphere contains 2-3 themes

### Day Schedule Test Set
- **Time periods**: All 6 periods configured
- **Period 1**: Morning atmosphere
- **Period 2**: Empty (defaults to All Images)
- **Period 3**: Morning + Evening atmospheres
- **Period 4-6**: Various configurations

---

## Test Environment Setup

### Prerequisites
- Flask server running on port 80
- 2560x2880 display or virtual display
- Socket.IO server active
- settings.json initialized with defaults
- images/ and extra-images/ directories present

### Test Execution Order
1. File upload and management tests
2. Theme and atmosphere tests
3. Day scheduling tests
4. Crop functionality tests
5. Remote control tests
6. Smart reload tests
7. WebSocket communication tests
8. Performance tests

### Screenshot Capture Points
- Initial kiosk display (fill mode)
- Kiosk display (fit mode)
- Image transition mid-dissolve
- Cropped image display
- Management interface with themes
- Day scheduling configuration
- Debug console with logs
- Extra image overlay

---

## Automated Test Implementation Notes

### Headless Browser Tests (Playwright/Puppeteer)
- Launch browser in headless mode
- Navigate to http://<kiosk-ip>/
- Execute JavaScript to interact with UI
- Verify DOM states and WebSocket events
- Capture screenshots for visual regression

### API Tests (pytest/requests)
- Direct HTTP calls to Flask endpoints
- Verify JSON responses
- Check settings.json file contents
- Validate WebSocket events via socket.io-client

### Screenshot Comparison
- Capture kiosk display via screenshot API or VNC
- Compare with baseline images
- Detect visual regressions in crop rendering
- Verify no black bars in various scenarios

### Time-based Tests
- Mock system time for day scheduling tests
- Verify hour boundary transitions
- Test time period mirroring (7-12 mirror 1-6)

### Concurrency Tests
- Multiple clients connected simultaneously
- Verify WebSocket broadcasts to all
- Test command queue behavior

---

## Known Limitations

1. **Time precision**: Hour boundary checks occur every 60s, so transitions may be delayed up to 60s
2. **Shuffle determinism**: Randomization is deterministic per shuffle_id but unpredictable across sessions
3. **Browser compatibility**: Tested on Firefox, Chrome compatibility not guaranteed
4. **Resolution dependency**: UI optimized for 2560x2880, other resolutions may have layout issues
5. **Network latency**: WebSocket timing assumes local network (<10ms RTT)
