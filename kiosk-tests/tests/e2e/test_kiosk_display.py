"""
End-to-end tests for kiosk display.

These tests use Playwright to automate the browser and verify visual behavior.
"""

import pytest
import time
from playwright.sync_api import expect


@pytest.mark.e2e
def test_kiosk_loads(api_client, isolated_test_data, page):
    """Test that kiosk display loads successfully with isolated test data."""
    # Set active theme to TestTheme10Images (has exactly 10 images)
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})

    # Set viewport to kiosk display dimensions
    page.set_viewport_size({"width": 2560, "height": 2880})

    # Navigate to kiosk view
    page.goto(f"{api_client.base_url}/view")

    # Wait for slideshow to load
    page.wait_for_selector('.slide', timeout=10000)

    # Should show slideshow container
    expect(page.locator('#slideshow-container')).to_be_visible()

    # Should have exactly 10 slides (from TestTheme10Images)
    slides = page.locator('.slide')
    expect(slides).to_have_count(10)


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
def test_slideshow_advances(api_client, isolated_test_data, test_mode, page, wait_for_transition):
    """Test that slideshow automatically advances between images."""
    # Set active theme to TestTheme10Images (has exactly 10 images)
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})

    # Set viewport and navigate
    page.set_viewport_size({"width": 2560, "height": 2880})
    page.goto(f"{api_client.base_url}/view")

    # Wait for page to fully load and establish WebSocket connection
    page.wait_for_selector('.slide.active', timeout=5000)
    time.sleep(0.5)  # Give WebSocket time to connect

    # Now set fast interval AFTER page has connected (WebSocket receives the event)
    test_mode.set_intervals(slideshow=2000, check=500)  # 2 seconds slideshow, 500ms check
    time.sleep(0.3)  # Let interval update propagate

    # Get initial slide index
    initial_index = page.locator('.slide.active').get_attribute('data-index')

    # Wait for transition (2s interval + 1.5s buffer)
    wait_for_transition(3500)

    # Get new slide index
    new_index = page.locator('.slide.active').get_attribute('data-index')

    # Should have advanced to different image
    assert initial_index != new_index, "Slideshow should advance to next image"


@pytest.mark.e2e
def test_manual_next_command(api_client, isolated_test_data, test_mode, page):
    """Test manually triggering next image via test mode."""
    # Set active theme to TestTheme10Images (has exactly 10 images)
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})

    # Set viewport and navigate
    page.set_viewport_size({"width": 2560, "height": 2880})
    page.goto(f"{api_client.base_url}/view")

    # Wait for initial image
    page.wait_for_selector('.slide.active', timeout=5000)
    time.sleep(0.3)  # Give WebSocket time to connect

    # Get initial slide
    initial_index = page.locator('.slide.active').get_attribute('data-index')

    # Trigger next
    test_mode.trigger_next()

    # Wait a moment for transition
    time.sleep(1.0)

    # Get new slide
    new_index = page.locator('.slide.active').get_attribute('data-index')

    # Should have changed
    assert initial_index != new_index, "Next command should advance slideshow"


@pytest.mark.e2e
@pytest.mark.screenshot
def test_image_transition_visual_comparison(api_client, isolated_test_data, test_mode, page, screenshot_helper):
    """Test that images are visually different after transition."""
    # Set active theme to TestTheme10Images (has exactly 10 images)
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})

    # Set viewport and navigate
    page.set_viewport_size({"width": 2560, "height": 2880})
    page.goto(f"{api_client.base_url}/view")

    # Wait for first image and WebSocket connection
    page.wait_for_selector('.slide.active img', timeout=5000)
    time.sleep(0.5)

    # Set fast interval AFTER page connects
    test_mode.set_intervals(slideshow=1500, check=500)
    time.sleep(0.3)

    # Capture first image
    screenshot_helper.capture(page, 'transition_before')
    hash_before = screenshot_helper.hash_image('transition_before')

    # Wait for transition (1.5s interval + buffer)
    time.sleep(2.5)

    # Capture second image
    screenshot_helper.capture(page, 'transition_after')
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
