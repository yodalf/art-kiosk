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
# Allow override via environment variable for remote testing
import os
BASE_URL = os.getenv("KIOSK_BASE_URL", "http://localhost")
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

    Usage:
        def test_themes(server_state):
            server_state.create_theme('TestTheme')
            # ... test ...
            server_state.cleanup()
    """
    class ServerState:
        def __init__(self, client):
            self.client = client
            self.created_themes = []
            self.created_atmospheres = []
            self.uploaded_images = []

        def create_theme(self, name: str, interval: int = 3600):
            """Create a theme."""
            response = self.client.post('/api/themes', json={'name': name, 'interval': interval})
            if response.status_code == 200:
                self.created_themes.append(name)
            return response.json()

        def create_atmosphere(self, name: str, cadence: int = 3600):
            """Create an atmosphere."""
            response = self.client.post('/api/atmospheres', json={'name': name, 'cadence': cadence})
            if response.status_code == 200:
                self.created_atmospheres.append(name)
            return response.json()

        def get_images(self, enabled_only=False):
            """Get list of images."""
            params = {'enabled_only': 'true'} if enabled_only else {}
            response = self.client.get('/api/images', params=params)
            return response.json()

        def toggle_image(self, filename: str):
            """Toggle image enabled state."""
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
            """Clean up created resources."""
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

            # Reset lists
            self.created_themes = []
            self.created_atmospheres = []

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
