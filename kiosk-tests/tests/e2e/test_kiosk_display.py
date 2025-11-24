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


@pytest.mark.e2e
@pytest.mark.day_scheduling
def test_kiosk_updates_on_time_period_transition(api_client, test_mode, isolated_test_data, page):
    """
    Test that kiosk display updates when time period transitions during day scheduling.

    This is the critical E2E test for the day scheduling bug:
    when the time period changes, the kiosk should reload and display
    images from the new time period's atmosphere.
    """
    # Use two different atmospheres from isolated test data
    atmosphere_period_1 = 'TestAtmosphereImageThemes'  # Has 2 themes
    atmosphere_period_2 = 'TestAtmosphereAllThemes'    # Has 4 themes

    # Set mock time to period 1 (6-8 AM)
    test_mode.set_time(1700049600)  # 7:00 AM - Period 1

    # Enable day scheduling
    api_client.post('/api/day/enable')

    # Assign different atmospheres to periods 1 and 2
    response = api_client.post('/api/day/time-periods/1', json={
        'atmospheres': [atmosphere_period_1]
    })
    assert response.status_code == 200

    response = api_client.post('/api/day/time-periods/2', json={
        'atmospheres': [atmosphere_period_2]
    })
    assert response.status_code == 200

    # Set fast check interval so kiosk detects changes quickly
    test_mode.set_intervals(check=500)  # Check every 500ms

    # Wait for settings to propagate
    time.sleep(0.5)

    # Navigate to kiosk view
    page.set_viewport_size({"width": 2560, "height": 2880})
    page.goto(f"{api_client.base_url}/view")

    # Wait for kiosk to load and connect WebSocket
    page.wait_for_selector('.slide.active', timeout=10000)
    time.sleep(1)  # Allow WebSocket to connect

    # Get the current image names displayed (from slide elements)
    def get_displayed_image_names():
        slides = page.locator('.slide')
        count = slides.count()
        names = []
        for i in range(count):
            slide = slides.nth(i)
            # For images, get from img src
            img = slide.locator('img')
            if img.count() > 0:
                src = img.first.get_attribute('src')
                if src:
                    # Extract filename from /images/filename
                    name = src.split('/')[-1]
                    names.append(name)
        return set(names)

    # Record images shown in period 1
    period_1_images = get_displayed_image_names()
    assert len(period_1_images) > 0, "Period 1 should show some images"

    # Transition to period 2 (8-10 AM)
    test_mode.set_time(1700055000)  # 8:30 AM - Period 2

    # Wait for kiosk to detect and reload (up to 5 seconds)
    # The kiosk checks every 500ms and should reload when it detects period change
    time.sleep(5)

    # Force a check by verifying the page is still responsive
    page.wait_for_selector('.slide.active', timeout=5000)

    # Record images shown in period 2
    period_2_images = get_displayed_image_names()
    assert len(period_2_images) > 0, "Period 2 should show some images"

    # THE KEY ASSERTION: Images should be different between periods
    assert period_1_images != period_2_images, (
        f"Kiosk display should update when time period transitions!\n"
        f"Period 1 images: {period_1_images}\n"
        f"Period 2 images: {period_2_images}\n"
        f"Kiosk is still showing the same images - this is the day scheduling bug!"
    )

    # Cleanup
    api_client.post('/api/day/disable')
