# Test Mode API Documentation

## Overview

The Art Kiosk system includes a comprehensive test mode API that allows external test scripts to control time-dependent events and intervals. This enables deterministic, fast-running automated tests without waiting for real-world time intervals.

## Key Concepts

### Normal Operation (Production)
- **WebSocket Push-Based**: Settings and image changes are pushed via WebSocket events
- **No Polling**: The kiosk display responds to real-time WebSocket events
- **Real Time**: Hour boundaries are checked every 60 seconds using system time
- **Normal Cadence**: Slideshow intervals are measured in seconds/minutes

### Test Mode Operation
- **Polling Enabled**: Test mode enables check interval polling for deterministic testing
- **Mock Time**: Override system time to test hour boundary transitions
- **Accelerated Intervals**: Override slideshow and check intervals to milliseconds
- **Manual Triggers**: Force specific events to occur immediately

## Test Mode API Endpoints

### Enable Test Mode
```
POST /api/test/enable
```
**Response:**
```json
{
  "success": true,
  "test_mode": {
    "enabled": true,
    "mock_time": null,
    "force_interval": null,
    "force_check_interval": null
  }
}
```
**Effect:**
- Enables test mode globally
- Emits `test_mode_enabled` WebSocket event to kiosk
- Kiosk will log "TEST MODE: Enabled"

### Disable Test Mode
```
POST /api/test/disable
```
**Response:**
```json
{
  "success": true,
  "test_mode": {
    "enabled": false,
    "mock_time": null,
    "force_interval": null,
    "force_check_interval": null
  }
}
```
**Effect:**
- Disables test mode and resets all overrides
- Emits `test_mode_disabled` WebSocket event
- Kiosk stops check interval polling
- Returns to normal WebSocket-based operation

### Set Mock Time
```
POST /api/test/time
Content-Type: application/json

{
  "timestamp": 1700000000
}
```
**Parameters:**
- `timestamp` (integer): Unix timestamp in seconds

**Response:**
```json
{
  "success": true,
  "mock_time": 1700000000,
  "current_time_period": 1
}
```
**Effect:**
- Overrides system time for hour boundary checks
- Emits `test_time_changed` WebSocket event
- Immediately triggers hour boundary check with new time
- Returns current time period based on mock time

**Example - Testing Hour Boundary Transition:**
```python
# Set time to 7:59:50 AM
requests.post('http://localhost/api/test/time', json={
    'timestamp': 1700040000  # 2023-11-15 07:59:50
})

# Wait a moment for kiosk to process
time.sleep(0.5)

# Set time to 8:00:10 AM (cross hour boundary)
requests.post('http://localhost/api/test/time', json={
    'timestamp': 1700040010  # 2023-11-15 08:00:10
})

# Hour boundary crossed! Kiosk will transition to next image
```

### Override Intervals
```
POST /api/test/intervals
Content-Type: application/json

{
  "slideshow_interval": 2000,
  "check_interval": 500
}
```
**Parameters:**
- `slideshow_interval` (integer, optional): Override slideshow interval in milliseconds
- `check_interval` (integer, optional): Override check interval in milliseconds

**Response:**
```json
{
  "success": true,
  "force_interval": 2000,
  "force_check_interval": 500
}
```
**Effect:**
- Emits `test_intervals_changed` WebSocket event
- Restarts slideshow timer with new interval
- Starts check interval polling timer (if test mode enabled)
- Kiosk logs show updated intervals

**Example - Fast Testing:**
```python
# Set very short intervals for rapid testing
requests.post('http://localhost/api/test/intervals', json={
    'slideshow_interval': 1000,  # 1 second between images
    'check_interval': 200        # Check for changes every 200ms
})
```

### Get Test Status
```
GET /api/test/status
```
**Response:**
```json
{
  "test_mode": {
    "enabled": true,
    "mock_time": 1700000000,
    "force_interval": 2000,
    "force_check_interval": 500
  },
  "current_time_period": 1
}
```
**Use Case:**
- Verify test mode state before running tests
- Check current time period for day scheduling tests

### Trigger Hour Boundary Check
```
POST /api/test/trigger-hour-boundary
```
**Response:**
```json
{
  "success": true
}
```
**Effect:**
- Emits `test_trigger_hour_check` WebSocket event
- Kiosk immediately runs `checkHourBoundary()`
- Uses mock time if set, otherwise uses real time

**Example:**
```python
# Manually trigger hour boundary check
requests.post('http://localhost/api/test/trigger-hour-boundary')
```

### Trigger Slideshow Advance
```
POST /api/test/trigger-slideshow-advance
```
**Response:**
```json
{
  "success": true
}
```
**Effect:**
- Emits `remote_command` WebSocket event with `next` command
- Kiosk immediately advances to next image
- Transition is instant (no dissolve)

**Example:**
```python
# Manually advance to next image
requests.post('http://localhost/api/test/trigger-slideshow-advance')
```

## WebSocket Events

Test mode uses WebSocket events for real-time communication with the kiosk display.

### Frontend Event Listeners (kiosk.html)

#### test_mode_enabled
Emitted when test mode is enabled.
```javascript
socket.on('test_mode_enabled', (data) => {
    testMode.enabled = true;
});
```

#### test_mode_disabled
Emitted when test mode is disabled.
```javascript
socket.on('test_mode_disabled', () => {
    testMode.enabled = false;
    testMode.mockTime = null;
    testMode.forceInterval = null;
    // Stops check interval polling
});
```

#### test_time_changed
Emitted when mock time is updated.
```javascript
socket.on('test_time_changed', (data) => {
    testMode.mockTime = data.timestamp;
    checkHourBoundary();
});
```

#### test_intervals_changed
Emitted when intervals are overridden.
```javascript
socket.on('test_intervals_changed', (data) => {
    // data.slideshow_interval - milliseconds
    // data.check_interval - milliseconds
});
```

#### test_trigger_hour_check
Emitted to manually trigger hour boundary check.
```javascript
socket.on('test_trigger_hour_check', () => {
    checkHourBoundary();
});
```

## Testing Scenarios

### Scenario 1: Test Hour Boundary Transitions

```python
import requests
import time

BASE_URL = 'http://localhost'

# 1. Enable test mode
requests.post(f'{BASE_URL}/api/test/enable')

# 2. Enable day scheduling
requests.post(f'{BASE_URL}/api/day/enable')

# 3. Assign atmospheres to time periods
requests.post(f'{BASE_URL}/api/day/time-periods/1', json={
    'atmospheres': ['Nature']
})
requests.post(f'{BASE_URL}/api/day/time-periods/2', json={
    'atmospheres': ['Urban']
})

# 4. Set mock time to 7:59:50 (just before 8 AM)
# Time period 1 is 7-8 AM (Nature)
requests.post(f'{BASE_URL}/api/test/time', json={
    'timestamp': 1700040000  # 07:59:50
})

# 5. Verify we're in time period 1
status = requests.get(f'{BASE_URL}/api/test/status').json()
assert status['current_time_period'] == 1

# 6. Wait for kiosk to settle
time.sleep(1)

# 7. Advance time across hour boundary to 8:00:10
# Time period 2 is 8-9 AM (Urban)
requests.post(f'{BASE_URL}/api/test/time', json={
    'timestamp': 1700043610  # 08:00:10
})

# 8. Verify time period changed
status = requests.get(f'{BASE_URL}/api/test/status').json()
assert status['current_time_period'] == 2

# 9. Kiosk should have automatically transitioned to next image
# Check debug logs to verify transition occurred

# 10. Disable test mode when done
requests.post(f'{BASE_URL}/api/test/disable')
```

### Scenario 2: Test Rapid Slideshow Transitions

```python
import requests
import time

BASE_URL = 'http://localhost'

# 1. Enable test mode
requests.post(f'{BASE_URL}/api/test/enable')

# 2. Set very short intervals
requests.post(f'{BASE_URL}/api/test/intervals', json={
    'slideshow_interval': 1000,  # 1 second
    'check_interval': 200        # 200ms
})

# 3. Let slideshow run for a few seconds
time.sleep(5)

# 4. Verify multiple images were displayed
# (Check via screenshot comparison or debug logs)

# 5. Manually trigger specific transitions
for i in range(3):
    requests.post(f'{BASE_URL}/api/test/trigger-slideshow-advance')
    time.sleep(0.5)

# 6. Disable test mode
requests.post(f'{BASE_URL}/api/test/disable')
```

### Scenario 3: Test Settings Changes Detection

```python
import requests
import time

BASE_URL = 'http://localhost'

# 1. Enable test mode with fast check interval
requests.post(f'{BASE_URL}/api/test/enable')
requests.post(f'{BASE_URL}/api/test/intervals', json={
    'check_interval': 100  # Check every 100ms
})

# 2. Get current images list
initial = requests.get(f'{BASE_URL}/api/images?enabled_only=true').json()

# 3. Disable an image
if initial:
    image_name = initial[0]['name']
    requests.post(f'{BASE_URL}/api/images/{image_name}/toggle')

# 4. Wait for check interval to detect change
time.sleep(0.5)

# 5. Kiosk should have reloaded with new image list
# (Verify via debug logs showing "Enabled images changed!")

# 6. Re-enable the image
requests.post(f'{BASE_URL}/api/images/{image_name}/toggle')
time.sleep(0.5)

# 7. Disable test mode
requests.post(f'{BASE_URL}/api/test/disable')
```

## Implementation Details

### Backend (app.py)

Test mode state is stored in a global dictionary:
```python
test_mode = {
    'enabled': False,
    'mock_time': None,  # Unix timestamp
    'force_interval': None,  # Milliseconds
    'force_check_interval': None,  # Milliseconds
}
```

Mock time is used in `get_current_time_period()`:
```python
def get_current_time_period():
    from datetime import datetime

    if test_mode['enabled'] and test_mode['mock_time'] is not None:
        current_hour = datetime.fromtimestamp(test_mode['mock_time']).hour
    else:
        current_hour = datetime.now().hour
    # ... rest of function
```

### Frontend (kiosk.html)

Test mode state is stored in a global object:
```javascript
let testMode = {
    enabled: false,
    mockTime: null,  // Unix timestamp
    checkIntervalTimer: null,  // Timer reference
    forceInterval: null  // Milliseconds
};
```

Mock time is used in `checkHourBoundary()`:
```javascript
async function checkHourBoundary() {
    if (!daySchedulingEnabled) return;

    const now = testMode.mockTime !== null
        ? new Date(testMode.mockTime * 1000)
        : new Date();
    const currentHour = now.getHours();
    // ... rest of function
}
```

Check interval polling is only active in test mode:
```javascript
if (testMode.enabled) {
    testMode.checkIntervalTimer = setInterval(checkForImageChanges, checkInterval);
}
```

## Important Notes

1. **Test mode is global**: Enabling test mode affects all connected kiosk displays
2. **No persistence**: Test mode state is lost on server restart
3. **Manual cleanup**: Always call `/api/test/disable` when tests complete
4. **WebSocket required**: Test mode relies on WebSocket connection
5. **Mock time affects day scheduling only**: Other time-based features still use real time
6. **Interval overrides are immediate**: Slideshow restarts with new interval instantly

## Security Considerations

Test mode API endpoints have no authentication. In production deployments:
- Restrict access to test endpoints via firewall rules
- Only enable test mode on development/testing systems
- Consider adding authentication to test endpoints
- Monitor test mode usage in logs

## Debugging

All test mode operations are logged to the debug console:
- "TEST MODE: Enabled"
- "TEST MODE: Disabled - resetting all overrides"
- "TEST MODE: Mock time set to [date]"
- "TEST MODE: Intervals changed - slideshow: Xms, check: Yms"
- "TEST MODE: Manual hour boundary check triggered"

Access debug logs at `/debug` page or via `/api/debug/messages` endpoint.
