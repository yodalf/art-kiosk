# Art Kiosk Test Suite

Comprehensive automated testing for the Art Kiosk image display system.

## Setup

### Initial Setup

```bash
# Navigate to test directory
cd kiosk-tests

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Chromium browser
playwright install chromium
```

### Activating Environment (for subsequent sessions)

```bash
cd kiosk-tests
source venv/bin/activate
```

## Running Tests

### Prerequisites

The kiosk server must be running on `http://localhost`:

```bash
# In the main kiosk directory
cd ..
sudo ./venv/bin/python app.py
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only (fast, no browser)
pytest -m unit

# Integration tests (requires running server)
pytest -m integration

# End-to-end tests (browser automation)
pytest -m e2e

# Tests for specific features
pytest -m day_scheduling
pytest -m test_mode
pytest -m screenshot
```

### Run Specific Test Files

```bash
# Test day scheduling
pytest tests/integration/test_day_scheduling.py

# Test kiosk display
pytest tests/e2e/test_kiosk_display.py

# Test API endpoints
pytest tests/unit/test_api_endpoints.py
```

### Run with Visible Browser

```bash
# See browser window during tests
pytest --headed

# Run slower for visual inspection
pytest --headed --slowmo 1000
```

### Run Specific Test

```bash
pytest tests/e2e/test_kiosk_display.py::test_kiosk_loads
```

## Test Organization

```
tests/
├── unit/               # Fast tests, no browser
│   └── test_api_endpoints.py
├── integration/        # API + server interaction
│   └── test_day_scheduling.py
├── e2e/               # Full browser automation
│   └── test_kiosk_display.py
└── fixtures/          # Test data (future)
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests (fast)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end browser tests
- `@pytest.mark.slow` - Tests that take longer
- `@pytest.mark.screenshot` - Tests that capture screenshots
- `@pytest.mark.day_scheduling` - Day scheduling feature
- `@pytest.mark.test_mode` - Test mode API
- `@pytest.mark.crop` - Image cropping
- `@pytest.mark.remote_control` - Remote control
- `@pytest.mark.themes` - Theme management
- `@pytest.mark.atmospheres` - Atmosphere management
- `@pytest.mark.websocket` - WebSocket communication

## Fixtures

Shared fixtures in `conftest.py`:

### API Testing
- `api_client` - HTTP client for API requests
- `test_mode` - Enable/disable test mode automatically
- `server_state` - Manage server resources (themes, atmospheres)

### Browser Testing
- `kiosk_page` - Page configured for kiosk display (2560x2880)
- `manage_page` - Page for management interface (1920x1080)
- `screenshot_helper` - Capture and compare screenshots
- `wait_for_transition` - Helper for timing-based tests

### Example Usage

```python
import pytest

@pytest.mark.integration
def test_hour_boundary(test_mode, api_client):
    """Test hour boundary detection."""
    # test_mode is automatically enabled/disabled
    test_mode.set_time(1700040000)

    # api_client provides HTTP methods
    response = api_client.get('/api/day/status')
    assert response.status_code == 200

@pytest.mark.e2e
def test_display(kiosk_page, screenshot_helper):
    """Test kiosk display."""
    # kiosk_page is already at /view with correct viewport
    screenshot_helper.capture(kiosk_page, 'test_name')
```

## Screenshots

Screenshots are saved to `screenshots/` directory and are git-ignored.

Capture screenshots:
```python
def test_visual(kiosk_page, screenshot_helper):
    screenshot_helper.capture(kiosk_page, 'my_test')
```

Compare screenshots:
```python
def test_compare(screenshot_helper):
    same = screenshot_helper.compare('image1', 'image2', threshold=0.01)
    assert same
```

## Test Mode API

Tests use the test mode API to control time-dependent behavior:

```python
def test_example(test_mode):
    # Set mock time (Unix timestamp)
    test_mode.set_time(1700040000)

    # Set fast intervals (milliseconds)
    test_mode.set_intervals(slideshow=1000, check=200)

    # Trigger events manually
    test_mode.trigger_hour_check()
    test_mode.trigger_next()

    # Get status
    status = test_mode.get_status()
```

## Writing New Tests

### Unit Test Template

```python
import pytest

@pytest.mark.unit
def test_something(api_client):
    """Test description."""
    response = api_client.get('/api/endpoint')
    assert response.status_code == 200
    assert response.json()['field'] == 'value'
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.day_scheduling
def test_feature(test_mode, api_client, server_state):
    """Test description."""
    # Setup
    server_state.enable_day_scheduling()
    test_mode.set_intervals(check=100)

    # Test
    response = api_client.get('/api/day/status')
    assert response.json()['enabled'] is True

    # Cleanup (automatic via fixtures)
```

### E2E Test Template

```python
import pytest
from playwright.sync_api import expect

@pytest.mark.e2e
def test_visual_behavior(kiosk_page, test_mode):
    """Test description."""
    # Wait for element
    kiosk_page.wait_for_selector('.slide.active')

    # Verify visibility
    expect(kiosk_page.locator('.slide.active')).to_be_visible()

    # Interact
    test_mode.trigger_next()

    # Assert change
    new_slide = kiosk_page.locator('.slide.active')
    expect(new_slide).to_have_attribute('data-index')
```

## Troubleshooting

### Server Not Running
```
Error: Connection refused
```
**Solution:** Start the kiosk server before running tests

### Browser Installation
```
Error: Executable doesn't exist
```
**Solution:** Run `playwright install chromium`

### Import Errors
```
ModuleNotFoundError: No module named 'playwright'
```
**Solution:** Activate venv: `source venv/bin/activate`

### Slow Tests
**Solution:** Use `-m unit` to run only fast unit tests

### Screenshot Comparison Fails
**Solution:** Adjust threshold in `screenshot_helper.compare()` call

## Coverage (Optional)

Install coverage tool:
```bash
pip install pytest-cov
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Continuous Integration (Future)

When setting up CI/CD:

```yaml
# .github/workflows/test.yml
- name: Install dependencies
  run: |
    pip install -r kiosk-tests/requirements.txt
    playwright install chromium

- name: Start server
  run: python app.py &

- name: Run tests
  run: pytest -m "not slow"
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Python](https://playwright.dev/python/)
- [Art Kiosk Test Mode API](../TEST_MODE.md)
- [Art Kiosk Requirements](../REQUIREMENTS.md)
