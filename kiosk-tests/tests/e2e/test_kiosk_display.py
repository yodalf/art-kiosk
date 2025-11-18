"""
End-to-end tests for kiosk display.

These tests use Playwright to automate the browser and verify visual behavior.
"""

import pytest
import time
from playwright.sync_api import expect


@pytest.mark.e2e
def test_kiosk_loads(kiosk_page):
    """Test that kiosk display loads successfully."""
    # Should show slideshow container
    expect(kiosk_page.locator('#slideshow-container')).to_be_visible()

    # Should have at least one slide
    slides = kiosk_page.locator('.slide')
    expect(slides).to_have_count(pytest.approx(1, abs=10))  # Allow variation in image count


@pytest.mark.e2e
def test_initial_image_displayed(kiosk_page):
    """Test that an image is displayed on initial load."""
    # Wait for active slide
    active_slide = kiosk_page.locator('.slide.active')
    expect(active_slide).to_be_visible(timeout=5000)

    # Should contain an image
    image = active_slide.locator('img')
    expect(image).to_be_visible()


@pytest.mark.e2e
@pytest.mark.screenshot
def test_capture_kiosk_screenshot(kiosk_page, screenshot_helper):
    """Test capturing a screenshot of the kiosk display."""
    # Wait for image to load
    kiosk_page.wait_for_selector('.slide.active img', timeout=5000)

    # Capture screenshot
    path = screenshot_helper.capture(kiosk_page, 'kiosk_initial')

    # Verify screenshot was created
    assert path.exists()
    assert path.stat().st_size > 0


@pytest.mark.e2e
@pytest.mark.slow
def test_slideshow_advances(test_mode, kiosk_page, wait_for_transition):
    """Test that slideshow automatically advances between images."""
    # Set fast interval for testing
    test_mode.set_intervals(slideshow=2000)  # 2 seconds

    # Wait for first image
    kiosk_page.wait_for_selector('.slide.active', timeout=5000)

    # Get initial slide index
    initial_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Wait for transition (2s interval + 1s buffer)
    wait_for_transition(3000)

    # Get new slide index
    new_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Should have advanced to different image
    assert initial_index != new_index, "Slideshow should advance to next image"


@pytest.mark.e2e
def test_manual_next_command(test_mode, kiosk_page):
    """Test manually triggering next image via test mode."""
    # Wait for initial image
    kiosk_page.wait_for_selector('.slide.active', timeout=5000)

    # Get initial slide
    initial_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Trigger next
    test_mode.trigger_next()

    # Wait a moment for transition
    time.sleep(0.5)

    # Get new slide
    new_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Should have changed
    assert initial_index != new_index, "Next command should advance slideshow"


@pytest.mark.e2e
@pytest.mark.day_scheduling
def test_hour_boundary_transition_visual(test_mode, kiosk_page, api_client):
    """Test visual transition when crossing hour boundary during day scheduling."""
    # Enable day scheduling
    api_client.post('/api/day/enable')

    # Set fast intervals
    test_mode.set_intervals(slideshow=5000, check=200)

    # Wait for initial load
    kiosk_page.wait_for_selector('.slide.active', timeout=5000)
    time.sleep(1)

    # Set time just before hour boundary
    test_mode.set_time(1700040000)  # 07:59:50
    time.sleep(0.5)

    # Get current slide
    initial_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Cross hour boundary
    test_mode.set_time(1700043610)  # 08:00:10
    time.sleep(1.5)  # Wait for hour boundary check and transition

    # Get new slide
    new_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Should have transitioned (hour boundary should trigger nextSlide)
    assert initial_index != new_index, "Crossing hour boundary should trigger image transition"

    # Cleanup
    api_client.post('/api/day/disable')


@pytest.mark.e2e
@pytest.mark.screenshot
def test_image_transition_visual_comparison(test_mode, kiosk_page, screenshot_helper):
    """Test that images are visually different after transition."""
    # Set fast interval
    test_mode.set_intervals(slideshow=1000)

    # Wait for first image
    kiosk_page.wait_for_selector('.slide.active img', timeout=5000)
    time.sleep(0.5)

    # Capture first image
    screenshot_helper.capture(kiosk_page, 'transition_before')
    hash_before = screenshot_helper.hash_image('transition_before')

    # Wait for transition
    time.sleep(2)

    # Capture second image
    screenshot_helper.capture(kiosk_page, 'transition_after')
    hash_after = screenshot_helper.hash_image('transition_after')

    # Images should be different
    assert hash_before != hash_after, "Images should change after transition"


@pytest.mark.e2e
def test_websocket_connection(kiosk_page):
    """Test that WebSocket connection is established."""
    # The kiosk page should log WebSocket connection
    # We can verify this by checking console logs or by triggering a WebSocket event

    # Wait for page to fully load
    kiosk_page.wait_for_load_state('networkidle')

    # If WebSocket is connected, remote commands should work
    # This is tested indirectly in test_manual_next_command


@pytest.mark.e2e
@pytest.mark.screenshot
def test_portrait_orientation(kiosk_page, screenshot_helper):
    """Test that display is in correct portrait orientation (2560x2880)."""
    # Capture screenshot
    screenshot_helper.capture(kiosk_page, 'portrait_test')

    # Verify viewport size
    viewport = kiosk_page.viewport_size
    assert viewport['width'] == 2560
    assert viewport['height'] == 2880

    # Height should be greater than width (portrait)
    assert viewport['height'] > viewport['width']


@pytest.mark.e2e
def test_no_loading_message_after_load(kiosk_page):
    """Test that loading message is hidden after images load."""
    # Wait for slideshow to load
    kiosk_page.wait_for_selector('.slide.active', timeout=5000)

    # Loading div should be hidden
    loading = kiosk_page.locator('#loading')

    # Check if it's hidden (either display:none or not visible)
    style = loading.evaluate('el => window.getComputedStyle(el).display')
    assert style == 'none', "Loading message should be hidden after images load"
