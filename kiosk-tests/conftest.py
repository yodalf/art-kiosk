"""
Shared pytest fixtures for Art Kiosk testing.

This module provides reusable fixtures for:
- API client setup
- Browser configuration
- Test mode management
- Screenshot comparison
- Server state management
"""

import pytest
import requests
import time
from pathlib import Path
from playwright.sync_api import Page, Browser, expect
from PIL import Image, ImageChops
import hashlib


# Configuration
# Load device configuration from ../device.txt if available
import os


def load_device_config():
    """Load device configuration from device.txt in parent directory."""
    device_file = Path(__file__).parent.parent / "device.txt"
    if device_file.exists():
        config = {}
        with open(device_file) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        return config
    return {}


# Load device config
device_config = load_device_config()

# Determine base URL:
# 1. Environment variable KIOSK_BASE_URL takes precedence
# 2. device.txt hostname if available
# 3. Default to localhost
if os.getenv("KIOSK_BASE_URL"):
    BASE_URL = os.getenv("KIOSK_BASE_URL")
elif device_config.get('hostname'):
    BASE_URL = f"http://{device_config['hostname']}"
else:
    BASE_URL = "http://localhost"

KIOSK_URL = f"{BASE_URL}/view"
MANAGE_URL = f"{BASE_URL}/"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the kiosk server."""
    return BASE_URL


@pytest.fixture(scope="session")
def api_client():
    """
    HTTP client for API requests.

    Usage:
        def test_something(api_client):
            response = api_client.get('/api/images')
            assert response.status_code == 200
    """
    class APIClient:
        def __init__(self, base_url):
            self.base_url = base_url
            self.session = requests.Session()

        def get(self, path, **kwargs):
            return self.session.get(f"{self.base_url}{path}", **kwargs)

        def post(self, path, **kwargs):
            return self.session.post(f"{self.base_url}{path}", **kwargs)

        def put(self, path, **kwargs):
            return self.session.put(f"{self.base_url}{path}", **kwargs)

        def delete(self, path, **kwargs):
            return self.session.delete(f"{self.base_url}{path}", **kwargs)

    return APIClient(BASE_URL)


@pytest.fixture(scope="session", autouse=True)
def cleanup_mpv_at_end(api_client):
    """
    Session-scoped fixture that ensures mpv is stopped at the end of tests.
    This runs ONCE at the end of the test session.
    autouse=True means it runs automatically.
    """
    yield
    # Always stop mpv at end of session
    try:
        api_client.post('/api/videos/stop-mpv')
        time.sleep(0.5)
    except:
        pass


@pytest.fixture(autouse=True)
def stop_mpv_before_each_test(api_client, request):
    """
    Autouse fixture that stops any running mpv before EACH test.
    This ensures only one video plays at a time and prevents orphaned processes.
    """
    # Stop any running video before test starts
    try:
        api_client.post('/api/videos/stop-mpv')
        time.sleep(0.3)
    except:
        pass

    yield

    # Also stop after test (belt and suspenders)
    try:
        api_client.post('/api/videos/stop-mpv')
        time.sleep(0.3)
    except:
        pass


@pytest.fixture(scope="session", autouse=True)
def manage_day_scheduling(api_client):
    """
    Session-scoped fixture that saves and restores day scheduling state.
    This runs ONCE at the start of the test session and ONCE at the end.
    autouse=True means it runs automatically for all tests.
    """
    import copy

    # Save original day scheduling state at session start
    try:
        day_status = api_client.get('/api/day/status').json()
        original_day_scheduling = day_status.get('enabled', False)

        settings = api_client.get('/api/settings').json()
        original_day_times = copy.deepcopy(settings.get('day_times', {}))

        if original_day_scheduling:
            print(f"\n⚠ SESSION START: Day scheduling was ON - disabling for all tests")
            api_client.post('/api/day/disable')
    except Exception as e:
        print(f"\n⚠ Warning: Could not save day scheduling state: {e}")
        original_day_scheduling = False
        original_day_times = {}

    # Run all tests
    yield

    # Restore original day scheduling state at session end
    try:
        # Restore day_times first
        current_settings = api_client.get('/api/settings').json()
        current_day_times = current_settings.get('day_times', {})

        for time_id, original_config in original_day_times.items():
            original_atmospheres = original_config.get('atmospheres', [])
            current_config = current_day_times.get(time_id, {})
            current_atmospheres = current_config.get('atmospheres', [])

            if original_atmospheres != current_atmospheres:
                api_client.post(f'/api/day/time-periods/{time_id}',
                              json={'atmospheres': original_atmospheres})

        # Restore day scheduling state
        if original_day_scheduling:
            print(f"\n✓ SESSION END: Restoring day scheduling to ON")
            response = api_client.post('/api/day/enable')
            if response.status_code != 200:
                print(f"⚠ ERROR: Failed to enable day scheduling: {response.status_code}")
            else:
                # Verify and wait
                import time
                time.sleep(0.2)
                verify = api_client.get('/api/day/status').json()
                if not verify.get('enabled'):
                    print(f"⚠ ERROR: Day scheduling enable succeeded but status shows disabled!")
                time.sleep(0.3)

                # Send reload command to kiosk
                api_client.post('/api/control/send', json={'command': 'reload'})
    except Exception as e:
        print(f"\n⚠ ERROR restoring day scheduling at session end: {e}")


@pytest.fixture
def test_mode(api_client):
    """
    Enable test mode for the duration of the test, then disable it.

    Usage:
        def test_something(test_mode):
            # Test mode is now enabled
            test_mode.set_time(1700000000)
            test_mode.set_intervals(slideshow=1000, check=200)
    """
    class TestMode:
        def __init__(self, client):
            self.client = client

        def enable(self):
            response = self.client.post('/api/test/enable')
            assert response.status_code == 200
            return response.json()

        def disable(self):
            response = self.client.post('/api/test/disable')
            assert response.status_code == 200
            return response.json()

        def set_time(self, timestamp):
            """Set mock time (Unix timestamp in seconds)."""
            response = self.client.post('/api/test/time', json={'timestamp': timestamp})
            assert response.status_code == 200
            return response.json()

        def set_intervals(self, slideshow=None, check=None):
            """Set intervals in milliseconds."""
            data = {}
            if slideshow is not None:
                data['slideshow_interval'] = slideshow
            if check is not None:
                data['check_interval'] = check
            response = self.client.post('/api/test/intervals', json=data)
            assert response.status_code == 200
            return response.json()

        def trigger_hour_check(self):
            """Manually trigger hour boundary check."""
            response = self.client.post('/api/test/trigger-hour-boundary')
            assert response.status_code == 200
            return response.json()

        def trigger_next(self):
            """Manually advance to next image."""
            response = self.client.post('/api/test/trigger-slideshow-advance')
            assert response.status_code == 200
            return response.json()

        def get_status(self):
            """Get current test mode status."""
            response = self.client.get('/api/test/status')
            assert response.status_code == 200
            return response.json()

    tm = TestMode(api_client)
    tm.enable()
    yield tm
    tm.disable()


@pytest.fixture
def kiosk_page(page: Page):
    """
    Playwright page configured for kiosk display testing.

    - Portrait orientation (2560x2880)
    - Navigated to /view
    - Waits for initial image load

    Usage:
        def test_display(kiosk_page):
            # Page is already at /view with correct viewport
            assert kiosk_page.locator('.slide.active').is_visible()
    """
    # Set viewport to kiosk display dimensions
    page.set_viewport_size({"width": 2560, "height": 2880})

    # Navigate to kiosk view
    page.goto(KIOSK_URL)

    # Wait for slideshow to load
    page.wait_for_selector('.slide', timeout=10000)

    yield page


@pytest.fixture
def manage_page(page: Page):
    """
    Playwright page configured for management interface testing.

    - Standard desktop viewport (1920x1080)
    - Navigated to /

    Usage:
        def test_upload(manage_page):
            # Page is already at management interface
            manage_page.click('button:has-text("Upload")')
    """
    # Standard desktop viewport
    page.set_viewport_size({"width": 1920, "height": 1080})

    # Navigate to management interface
    page.goto(MANAGE_URL)

    # Wait for page load
    page.wait_for_load_state('networkidle')

    yield page


@pytest.fixture
def screenshot_dir():
    """Directory for storing test screenshots."""
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    return SCREENSHOTS_DIR


@pytest.fixture
def screenshot_helper(screenshot_dir):
    """
    Helper for capturing and comparing screenshots.

    Usage:
        def test_visual(kiosk_page, screenshot_helper):
            screenshot_helper.capture(kiosk_page, 'test_name')
            # Later:
            if screenshot_helper.compare('test_name', 'baseline_name'):
                print("Screenshots match!")
    """
    class ScreenshotHelper:
        def __init__(self, directory):
            self.directory = directory

        def capture(self, page: Page, name: str) -> Path:
            """Capture screenshot with given name."""
            path = self.directory / f"{name}.png"
            page.screenshot(path=str(path))
            return path

        def compare(self, image1_name: str, image2_name: str, threshold: float = 0.01) -> bool:
            """
            Compare two screenshots.

            Args:
                image1_name: First image name (without extension)
                image2_name: Second image name (without extension)
                threshold: Acceptable difference ratio (0.0 to 1.0)

            Returns:
                True if images are similar within threshold
            """
            img1_path = self.directory / f"{image1_name}.png"
            img2_path = self.directory / f"{image2_name}.png"

            if not img1_path.exists() or not img2_path.exists():
                return False

            img1 = Image.open(img1_path)
            img2 = Image.open(img2_path)

            # Compare dimensions
            if img1.size != img2.size:
                return False

            # Calculate difference
            diff = ImageChops.difference(img1, img2)

            # Calculate difference ratio
            stat = diff.histogram()
            sum_of_squares = sum(i * (stat[i] ** 2) for i in range(256))
            total_pixels = img1.size[0] * img1.size[1] * 3  # RGB
            rms = (sum_of_squares / total_pixels) ** 0.5

            # Normalize to 0-1 range
            normalized_diff = rms / 255.0

            return normalized_diff <= threshold

        def hash_image(self, name: str) -> str:
            """Get hash of image file."""
            path = self.directory / f"{name}.png"
            if not path.exists():
                return ""

            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()

    return ScreenshotHelper(screenshot_dir)


@pytest.fixture
def server_state(api_client):
    """
    Helper for managing server state (images, themes, settings).

    IMPORTANT: Saves and restores original state to prevent data loss.

    Usage:
        def test_themes(server_state):
            server_state.create_theme('TestTheme')
            # ... test ...
            # Automatic cleanup on fixture teardown
    """
    class ServerState:
        def __init__(self, client):
            self.client = client
            self.created_themes = []
            self.created_atmospheres = []
            self.uploaded_images = []
            self.modified_images = {}  # Track original state of toggled images

            # Save original state
            self._save_original_state()

        def _save_original_state(self):
            """Save current server state for restoration (themes, atmospheres, images)."""
            try:
                settings = self.client.get('/api/settings').json()
                self.original_active_theme = settings.get('active_theme')
                self.original_active_atmosphere = settings.get('active_atmosphere')
            except Exception as e:
                print(f"⚠ Warning: Error saving original state: {e}")
                pass

        def create_theme(self, name: str, interval: int = 3600):
            """Create a theme."""
            response = self.client.post('/api/themes', json={'name': name, 'interval': interval})
            if response.status_code == 200:
                self.created_themes.append(name)
            return response.json()

        def create_atmosphere(self, name: str, interval: int = 3600):
            """Create an atmosphere."""
            response = self.client.post('/api/atmospheres', json={'name': name, 'interval': interval})
            if response.status_code == 200:
                self.created_atmospheres.append(name)
            return response.json()

        def get_images(self, enabled_only=False):
            """Get list of images."""
            params = {'enabled_only': 'true'} if enabled_only else {}
            response = self.client.get('/api/images', params=params)
            return response.json()

        def toggle_image(self, filename: str):
            """Toggle image enabled state - SAVES ORIGINAL STATE."""
            # Save original state before toggling
            if filename not in self.modified_images:
                images = self.get_images()
                img = next((i for i in images if i['name'] == filename), None)
                if img:
                    self.modified_images[filename] = img.get('enabled', True)

            response = self.client.post(f'/api/images/{filename}/toggle')
            return response.json()

        def enable_day_scheduling(self):
            """Enable day scheduling mode."""
            response = self.client.post('/api/day/enable')
            return response.json()

        def disable_day_scheduling(self):
            """Disable day scheduling mode."""
            response = self.client.post('/api/day/disable')
            return response.json()

        def cleanup(self):
            """Clean up created resources and restore original state."""
            # Restore toggled images to original state
            for filename, original_enabled in self.modified_images.items():
                try:
                    images = self.get_images()
                    current_img = next((i for i in images if i['name'] == filename), None)
                    if current_img and current_img.get('enabled') != original_enabled:
                        # Toggle back to original state
                        self.client.post(f'/api/images/{filename}/toggle')
                except:
                    pass

            # Delete created themes
            for theme in self.created_themes:
                try:
                    self.client.delete(f'/api/themes/{theme}')
                except:
                    pass

            # Delete created atmospheres
            for atmosphere in self.created_atmospheres:
                try:
                    self.client.delete(f'/api/atmospheres/{atmosphere}')
                except:
                    pass

            # Restore theme and atmosphere (only if day scheduling is OFF)
            # Note: Day scheduling state is managed by the session-scoped manage_day_scheduling fixture
            try:
                day_status = self.client.get('/api/day/status').json()
                if not day_status.get('enabled', False):
                    # Day scheduling is off - restore theme and atmosphere manually
                    if hasattr(self, 'original_active_theme') and self.original_active_theme:
                        self.client.post('/api/themes/active', json={'theme': self.original_active_theme})

                    if hasattr(self, 'original_active_atmosphere') and self.original_active_atmosphere:
                        self.client.post('/api/atmospheres/active', json={'atmosphere': self.original_active_atmosphere})
            except:
                pass

            # Reset lists
            self.created_themes = []
            self.created_atmospheres = []
            self.modified_images = {}

    state = ServerState(api_client)
    yield state
    state.cleanup()


@pytest.fixture
def wait_for_transition():
    """
    Helper to wait for slideshow transitions.

    Usage:
        def test_slideshow(kiosk_page, wait_for_transition):
            initial = kiosk_page.locator('.slide.active').text_content()
            wait_for_transition(1000)  # Wait 1 second
            new = kiosk_page.locator('.slide.active').text_content()
            assert initial != new
    """
    def wait(milliseconds: int):
        time.sleep(milliseconds / 1000.0)

    return wait


# Playwright-specific configuration
def pytest_configure(config):
    """Configure Playwright browser launch options."""
    config.option.browser = ["chromium"]
    config.option.headed = False  # Set to True to see browser during tests


# Custom assertion helpers
def assert_image_displayed(page: Page, timeout: int = 5000):
    """Assert that an image is currently displayed in the slideshow."""
    expect(page.locator('.slide.active img')).to_be_visible(timeout=timeout)


def assert_slideshow_running(page: Page, interval_ms: int):
    """Assert that slideshow is advancing between images."""
    # Get current image
    initial = page.locator('.slide.active').get_attribute('data-index')

    # Wait for transition (with buffer)
    time.sleep((interval_ms + 1000) / 1000.0)

    # Check that image changed
    current = page.locator('.slide.active').get_attribute('data-index')
    assert initial != current, "Slideshow did not advance"


@pytest.fixture
def test_image_generator():
    """
    Generator for creating test images.

    Usage:
        def test_upload(test_image_generator):
            img_path = test_image_generator.create_png(100, 100, (255, 0, 0))
            # Upload img_path
    """
    from PIL import Image
    import tempfile

    class ImageGenerator:
        def __init__(self):
            self.temp_files = []

        def create_png(self, width: int, height: int, color=(255, 255, 255)):
            """Create a solid color PNG image."""
            img = Image.new('RGB', (width, height), color)
            fd, path = tempfile.mkstemp(suffix='.png')
            img.save(path)
            self.temp_files.append(path)
            return Path(path)

        def create_jpg(self, width: int, height: int, color=(255, 255, 255)):
            """Create a solid color JPG image."""
            img = Image.new('RGB', (width, height), color)
            fd, path = tempfile.mkstemp(suffix='.jpg')
            img.save(path, 'JPEG')
            self.temp_files.append(path)
            return Path(path)

        def create_large_file(self, size_mb: int, extension='.jpg'):
            """Create a large file of specified size."""
            fd, path = tempfile.mkstemp(suffix=extension)
            with open(path, 'wb') as f:
                f.write(b'0' * (size_mb * 1024 * 1024))
            self.temp_files.append(path)
            return Path(path)

        def cleanup(self):
            """Remove all temporary files."""
            for path in self.temp_files:
                try:
                    Path(path).unlink()
                except:
                    pass

    generator = ImageGenerator()
    yield generator
    generator.cleanup()


@pytest.fixture
def websocket_monitor(kiosk_page):
    """
    Monitor WebSocket messages on the kiosk page.

    Usage:
        def test_ws(kiosk_page, websocket_monitor):
            messages = websocket_monitor.get_messages('remote_command')
            assert len(messages) > 0
    """
    class WebSocketMonitor:
        def __init__(self, page):
            self.page = page
            self.messages = []

            # Inject monitoring script
            page.evaluate("""
                window.__ws_messages = [];
                if (window.socket) {
                    const originalOn = window.socket.on.bind(window.socket);
                    window.socket.on = function(event, handler) {
                        const wrappedHandler = function(...args) {
                            window.__ws_messages.push({event, args, timestamp: Date.now()});
                            return handler(...args);
                        };
                        return originalOn(event, wrappedHandler);
                    };
                }
            """)

        def get_messages(self, event_name=None):
            """Get all captured WebSocket messages, optionally filtered by event name."""
            messages = self.page.evaluate("window.__ws_messages || []")
            if event_name:
                return [m for m in messages if m['event'] == event_name]
            return messages

        def clear(self):
            """Clear all captured messages."""
            self.page.evaluate("window.__ws_messages = []")

        def wait_for_message(self, event_name, timeout_ms=5000):
            """Wait for a specific WebSocket message."""
            start = time.time()
            while (time.time() - start) * 1000 < timeout_ms:
                messages = self.get_messages(event_name)
                if messages:
                    return messages[-1]
                time.sleep(0.1)
            raise TimeoutError(f"WebSocket message '{event_name}' not received within {timeout_ms}ms")

    return WebSocketMonitor(kiosk_page)


@pytest.fixture
def image_uploader(api_client, test_image_generator):
    """
    Helper for uploading test images with GUARANTEED cleanup.

    CRITICAL: All uploaded images are tracked and deleted after test.
    Uses try/finally to ensure cleanup even if test fails.

    Usage:
        def test_upload(image_uploader):
            filename = image_uploader.upload_test_image()
            # Image is AUTOMATICALLY deleted after test
    """
    class ImageUploader:
        def __init__(self, client, generator):
            self.client = client
            self.generator = generator
            self.uploaded_files = []
            self._cleanup_registered = False

        def upload_test_image(self, width=100, height=100, color=(255, 0, 0)):
            """Upload a test image and return the server filename."""
            img_path = self.generator.create_png(width, height, color)

            with open(img_path, 'rb') as f:
                response = self.client.post('/api/images', files={'file': f})

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    filename = data['filename']
                    self.uploaded_files.append(filename)
                    return filename

            raise Exception(f"Upload failed: {response.status_code}")

        def cleanup(self):
            """
            Delete ALL uploaded images - GUARANTEED.

            CRITICAL: This MUST run to prevent polluting production database.
            """
            deleted_count = 0
            failed_deletes = []

            for filename in self.uploaded_files[:]:  # Copy list to avoid modification during iteration
                try:
                    response = self.client.delete(f'/api/images/{filename}')
                    if response.status_code == 200:
                        deleted_count += 1
                        self.uploaded_files.remove(filename)
                    else:
                        failed_deletes.append(filename)
                except Exception as e:
                    failed_deletes.append(filename)

            # Log cleanup results
            if deleted_count > 0:
                print(f"\n✓ Cleaned up {deleted_count} test images")

            if failed_deletes:
                print(f"\n⚠ WARNING: Failed to delete {len(failed_deletes)} test images: {failed_deletes}")
                # Try one more time
                for filename in failed_deletes:
                    try:
                        self.client.delete(f'/api/images/{filename}')
                    except:
                        pass

    uploader = ImageUploader(api_client, test_image_generator)
    try:
        yield uploader
    finally:
        # CRITICAL: Cleanup ALWAYS runs, even if test fails
        uploader.cleanup()


@pytest.fixture(scope="session")
def isolated_test_data(api_client):
    """
    Session-scoped fixture providing completely isolated synthetic test data.

    Creates:
    - 20 images (including one suitable for crop tests)
    - 5 videos
    - 4 themes:
      - 'TestTheme10Images': 10 images
      - 'TestTheme15Images': 15 images
      - 'TestThemeVideosOnly': 5 videos only
      - 'TestTheme19ImagesVideoEnd': 19 images + 1 video at end
    - 2 atmospheres:
      - 'TestAtmosphereImageThemes': points to the 2 image themes
      - 'TestAtmosphereAllThemes': points to all 4 themes

    All data is cleaned up after the session.

    Usage:
        def test_something(isolated_test_data):
            images = isolated_test_data['images']
            themes = isolated_test_data['themes']
    """
    from PIL import Image, ImageDraw
    from io import BytesIO
    import random

    created_data = {
        'images': [],
        'videos': [],
        'themes': {},
        'atmospheres': {},
        'original_settings': None
    }

    try:
        # Save original settings
        response = api_client.get('/api/settings')
        if response.status_code == 200:
            created_data['original_settings'] = response.json()

        print("\n" + "="*60)
        print("SETTING UP ISOLATED TEST DATA")
        print("="*60)

        # Pre-cleanup: Delete any leftover test themes/atmospheres from previous runs
        print("\nPre-cleanup: Removing any leftover test data...")
        for atm_name in ['TestAtmosphereImageThemes', 'TestAtmosphereAllThemes']:
            try:
                api_client.delete(f'/api/atmospheres/{atm_name}')
            except:
                pass
        for theme_name in ['TestTheme10Images', 'TestTheme15Images', 'TestThemeVideosOnly', 'TestTheme19ImagesVideoEnd']:
            try:
                api_client.delete(f'/api/themes/{theme_name}')
            except:
                pass
        print("  Pre-cleanup complete")

        # Step 1: Create 20 test images
        print("\nStep 1: Creating 20 test images...")
        for i in range(20):
            # Create varied images - some solid colors, some with patterns
            if i == 0:
                # First image: gradient with shapes (good for crop tests)
                img = Image.new('RGB', (800, 600), (255, 255, 255))
                draw = ImageDraw.Draw(img)
                # Add gradient background
                for y in range(600):
                    r = int(255 * y / 600)
                    g = int(255 * (600 - y) / 600)
                    b = 128
                    draw.line([(0, y), (800, y)], fill=(r, g, b))
                # Add shapes
                draw.rectangle([100, 100, 300, 300], fill=(255, 0, 0))
                draw.ellipse([400, 200, 600, 400], fill=(0, 255, 0))
                draw.polygon([(650, 100), (750, 300), (550, 300)], fill=(0, 0, 255))
            elif i % 3 == 0:
                # Striped pattern
                img = Image.new('RGB', (400, 400), (255, 255, 255))
                draw = ImageDraw.Draw(img)
                for stripe in range(0, 400, 20):
                    color = ((i * 30) % 256, (stripe * 3) % 256, ((i + stripe) * 2) % 256)
                    draw.rectangle([0, stripe, 400, stripe + 10], fill=color)
            elif i % 3 == 1:
                # Checkered pattern
                img = Image.new('RGB', (400, 400), (255, 255, 255))
                draw = ImageDraw.Draw(img)
                for x in range(0, 400, 40):
                    for y in range(0, 400, 40):
                        if (x // 40 + y // 40) % 2 == 0:
                            color = ((i * 25) % 256, (i * 50) % 256, (i * 75) % 256)
                            draw.rectangle([x, y, x + 40, y + 40], fill=color)
            else:
                # Solid color with border
                color = ((i * 30) % 256, (i * 60) % 256, (i * 90) % 256)
                img = Image.new('RGB', (400, 400), color)
                draw = ImageDraw.Draw(img)
                draw.rectangle([10, 10, 390, 390], outline=(255, 255, 255), width=5)

            # Convert to bytes
            img_bytes = BytesIO()
            img.save(img_bytes, format='JPEG', quality=85)
            img_bytes.seek(0)

            # Upload
            files = {'file': (f'test_image_{i:02d}.jpg', img_bytes, 'image/jpeg')}
            response = api_client.post('/api/images', files=files)

            if response.status_code == 200:
                data = response.json()
                image_id = data.get('filename')
                created_data['images'].append(image_id)
                if i == 0:
                    print(f"  ✓ Created crop-test image: {image_id}")
                elif (i + 1) % 5 == 0:
                    print(f"  ✓ Created {i + 1} images...")
            else:
                print(f"  ✗ Failed to create image {i}: {response.text}")

        print(f"  Total images created: {len(created_data['images'])}")

        # Step 2: Add 5 videos
        print("\nStep 2: Adding 5 test videos...")
        test_video_urls = [
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # "Me at the zoo"
            "https://www.youtube.com/watch?v=9bZkp7q19f0",  # Gangnam Style
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Never Gonna Give You Up
            "https://www.youtube.com/watch?v=kJQP7kiw5Fk",  # Despacito
            "https://www.youtube.com/watch?v=JGwWNGJdvx8",  # Shape of You
        ]

        for i, url in enumerate(test_video_urls):
            response = api_client.post('/api/videos', json={'url': url})
            if response.status_code == 200:
                data = response.json()
                video_id = data.get('id')
                created_data['videos'].append(video_id)
                print(f"  ✓ Added video {i + 1}: {video_id}")
            else:
                print(f"  ✗ Failed to add video {i + 1}: {response.text}")

        print(f"  Total videos created: {len(created_data['videos'])}")

        # Step 3: Create themes
        print("\nStep 3: Creating themes...")

        # Create all themes first
        theme_names = ['TestTheme10Images', 'TestTheme15Images', 'TestThemeVideosOnly', 'TestTheme19ImagesVideoEnd']
        theme_intervals = [30, 30, 60, 15]

        for theme_name, interval in zip(theme_names, theme_intervals):
            response = api_client.post('/api/themes', json={'name': theme_name, 'interval': interval})
            if response.status_code == 200:
                created_data['themes'][theme_name] = {'images': [], 'videos': []}

        # Build theme assignments for each image (accumulate, don't replace)
        image_themes = {img_id: [] for img_id in created_data['images']}
        video_themes = {vid_id: [] for vid_id in created_data['videos']}

        # Theme 1: 10 images (first 10)
        for img_id in created_data['images'][:10]:
            image_themes[img_id].append('TestTheme10Images')
            created_data['themes']['TestTheme10Images']['images'].append(img_id)

        # Theme 2: 15 images (first 15)
        for img_id in created_data['images'][:15]:
            image_themes[img_id].append('TestTheme15Images')
            created_data['themes']['TestTheme15Images']['images'].append(img_id)

        # Theme 3: Videos only
        for video_id in created_data['videos']:
            video_themes[video_id].append('TestThemeVideosOnly')
            created_data['themes']['TestThemeVideosOnly']['videos'].append(video_id)

        # Theme 4: 19 images + 1 video
        for img_id in created_data['images'][:19]:
            image_themes[img_id].append('TestTheme19ImagesVideoEnd')
            created_data['themes']['TestTheme19ImagesVideoEnd']['images'].append(img_id)

        if created_data['videos']:
            video_id = created_data['videos'][0]
            video_themes[video_id].append('TestTheme19ImagesVideoEnd')
            created_data['themes']['TestTheme19ImagesVideoEnd']['videos'].append(video_id)

        # Now apply all theme assignments at once for each image
        for img_id, themes in image_themes.items():
            if themes:
                api_client.post(f'/api/images/{img_id}/themes', json={'themes': themes})

        # Apply video theme assignments
        for video_id, themes in video_themes.items():
            if themes:
                api_client.post(f'/api/videos/{video_id}/themes', json={'themes': themes})

        print(f"  ✓ Created 'TestTheme10Images' with 10 images")
        print(f"  ✓ Created 'TestTheme15Images' with 15 images")
        print(f"  ✓ Created 'TestThemeVideosOnly' with 3 videos")
        print(f"  ✓ Created 'TestTheme19ImagesVideoEnd' with 19 images + 1 video")
        print(f"  Total themes created: {len(created_data['themes'])}")

        # Step 4: Create atmospheres
        print("\nStep 4: Creating atmospheres...")

        # Atmosphere 1: Points to 2 image themes
        atm_name = 'TestAtmosphereImageThemes'
        response = api_client.post('/api/atmospheres', json={'name': atm_name, 'interval': 300})
        if response.status_code == 200:
            # Assign themes
            theme_list = ['TestTheme10Images', 'TestTheme15Images']
            api_client.post(f'/api/atmospheres/{atm_name}/themes', json={'themes': theme_list})
            created_data['atmospheres'][atm_name] = {'themes': theme_list}
            print(f"  ✓ Created '{atm_name}' with 2 image themes")

        # Atmosphere 2: Points to all 4 themes (like "All Images")
        atm_name = 'TestAtmosphereAllThemes'
        response = api_client.post('/api/atmospheres', json={'name': atm_name, 'interval': 600})
        if response.status_code == 200:
            # Assign all themes
            theme_list = list(created_data['themes'].keys())
            api_client.post(f'/api/atmospheres/{atm_name}/themes', json={'themes': theme_list})
            created_data['atmospheres'][atm_name] = {'themes': theme_list}
            print(f"  ✓ Created '{atm_name}' with all 4 themes")

        print(f"  Total atmospheres created: {len(created_data['atmospheres'])}")

        print("\n" + "="*60)
        print("ISOLATED TEST DATA SETUP COMPLETE")
        print(f"  Images: {len(created_data['images'])}")
        print(f"  Videos: {len(created_data['videos'])}")
        print(f"  Themes: {len(created_data['themes'])}")
        print(f"  Atmospheres: {len(created_data['atmospheres'])}")
        print("="*60 + "\n")

        yield created_data

    finally:
        # Cleanup ALL created data
        print("\n" + "="*60)
        print("CLEANING UP ISOLATED TEST DATA")
        print("="*60)

        # Stop any playing videos (critical - must always run)
        try:
            api_client.post('/api/videos/stop-mpv')
            time.sleep(1)
            # Double-check mpv is stopped
            api_client.post('/api/videos/stop-mpv')
            time.sleep(0.5)
            print("  ✓ Stopped any running videos")
        except Exception as e:
            print(f"  ⚠ Warning: Could not stop videos: {e}")

        # Delete atmospheres
        for atm_name in created_data['atmospheres']:
            try:
                response = api_client.delete(f'/api/atmospheres/{atm_name}')
                if response.status_code == 200:
                    print(f"  ✓ Deleted atmosphere: {atm_name}")
            except Exception as e:
                print(f"  ✗ Failed to delete atmosphere {atm_name}: {e}")

        # Delete themes
        for theme_name in created_data['themes']:
            try:
                response = api_client.delete(f'/api/themes/{theme_name}')
                if response.status_code == 200:
                    print(f"  ✓ Deleted theme: {theme_name}")
            except Exception as e:
                print(f"  ✗ Failed to delete theme {theme_name}: {e}")

        # Delete videos
        for video_id in created_data['videos']:
            try:
                response = api_client.delete(f'/api/videos/{video_id}')
                if response.status_code == 200:
                    print(f"  ✓ Deleted video: {video_id}")
            except Exception as e:
                print(f"  ✗ Failed to delete video {video_id}: {e}")

        # Delete images
        deleted_images = 0
        for image_id in created_data['images']:
            try:
                response = api_client.delete(f'/api/images/{image_id}')
                if response.status_code == 200:
                    deleted_images += 1
            except Exception as e:
                pass
        print(f"  ✓ Deleted {deleted_images} images")

        # Restore original settings if needed
        if created_data['original_settings']:
            try:
                original = created_data['original_settings']
                if original.get('active_theme'):
                    api_client.post('/api/themes/active', json={'theme': original['active_theme']})
            except:
                pass

        print("="*60)
        print("CLEANUP COMPLETE")
        print("="*60 + "\n")
