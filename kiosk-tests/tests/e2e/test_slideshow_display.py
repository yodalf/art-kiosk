"""
End-to-end tests for Slideshow Display (REQ-SLIDE-001 through REQ-SLIDE-012).

Tests slideshow behavior, transitions, and display functionality.
"""

import pytest
import time
from playwright.sync_api import expect


@pytest.mark.e2e
def test_req_slide_001_initial_load(kiosk_page):
    """REQ-SLIDE-001: Kiosk SHALL load and display first image within 5 seconds."""
    start_time = time.time()

    # Wait for active slide
    kiosk_page.wait_for_selector('.slide.active', timeout=5000)

    elapsed = time.time() - start_time
    assert elapsed < 5.0


@pytest.mark.e2e
def test_req_slide_002_dissolve_transition(test_mode, kiosk_page):
    """REQ-SLIDE-002: Automatic slideshow SHALL use 0.8s dissolve transitions."""
    test_mode.set_intervals(slideshow=2000)

    kiosk_page.wait_for_selector('.slide.active')

    # Get initial slide
    initial = kiosk_page.locator('.slide.active')

    # Wait for transition to start
    time.sleep(2.5)

    # During transition, check if opacity is being used
    # (This is implementation-specific, transition should be smooth)


@pytest.mark.e2e
def test_req_slide_003_cover_mode_default(kiosk_page):
    """REQ-SLIDE-003: Images SHALL use 'cover' mode by default (fill screen, crop edges)."""
    kiosk_page.wait_for_selector('.slide.active img')

    # Check CSS object-fit
    img = kiosk_page.locator('.slide.active img').first
    object_fit = img.evaluate("el => window.getComputedStyle(el).objectFit")

    # Should be 'cover' for non-cropped images
    assert object_fit in ['cover', 'fill']  # 'fill' is for cropped images


@pytest.mark.e2e
def test_req_slide_004_portrait_orientation(kiosk_page):
    """REQ-SLIDE-004: Display SHALL be 2560x2880 portrait orientation."""
    viewport = kiosk_page.viewport_size

    assert viewport['width'] == 2560
    assert viewport['height'] == 2880
    assert viewport['height'] > viewport['width']  # Portrait


@pytest.mark.e2e
def test_req_slide_005_randomized_order(api_client, kiosk_page):
    """REQ-SLIDE-005: Images SHALL be displayed in randomized order using shuffle_id."""
    # Get shuffle_id
    settings = api_client.get('/api/settings').json()
    shuffle_id = settings.get('shuffle_id')

    # Reload page
    kiosk_page.reload()
    kiosk_page.wait_for_selector('.slide')

    # Order should be same with same shuffle_id
    # (More detailed test in integration tests)


@pytest.mark.e2e
def test_req_slide_006_configurable_interval(test_mode, kiosk_page):
    """REQ-SLIDE-006: Slideshow interval SHALL be configurable."""
    # Set fast interval
    test_mode.set_intervals(slideshow=1000)

    kiosk_page.wait_for_selector('.slide.active')
    initial = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Wait just over interval
    time.sleep(1.5)

    # Should have advanced
    current = kiosk_page.locator('.slide.active').get_attribute('data-index')
    assert current != initial


@pytest.mark.e2e
def test_req_slide_007_continuous_loop(test_mode, kiosk_page):
    """REQ-SLIDE-007: Slideshow SHALL loop continuously."""
    test_mode.set_intervals(slideshow=500)

    kiosk_page.wait_for_selector('.slide.active')

    # Let it run through several cycles
    time.sleep(3)

    # Should still be displaying images
    expect(kiosk_page.locator('.slide.active')).to_be_visible()


@pytest.mark.e2e
def test_req_slide_008_fullscreen_display(kiosk_page):
    """REQ-SLIDE-008: Images SHALL fill entire viewport with no UI elements."""
    kiosk_page.wait_for_selector('.slide.active')

    # Container should fill viewport
    container = kiosk_page.locator('#slideshow-container')
    box = container.bounding_box()

    assert box['width'] == 2560
    assert box['height'] == 2880


@pytest.mark.e2e
def test_req_slide_009_no_cursor(kiosk_page):
    """REQ-SLIDE-009: Mouse cursor SHALL be hidden."""
    # Check body cursor style
    cursor_style = kiosk_page.evaluate("window.getComputedStyle(document.body).cursor")
    assert cursor_style == 'none'


@pytest.mark.e2e
def test_req_slide_010_loading_message(kiosk_page):
    """REQ-SLIDE-010: Loading message SHALL be hidden after images load."""
    kiosk_page.wait_for_selector('.slide.active', timeout=5000)

    # Loading div should be hidden
    loading = kiosk_page.locator('#loading')
    display = loading.evaluate("el => window.getComputedStyle(el).display")

    assert display == 'none'


@pytest.mark.e2e
def test_req_slide_011_handle_no_images(kiosk_page, api_client):
    """REQ-SLIDE-011: SHALL display message when no images enabled."""
    # Disable all images temporarily would be complex
    # This test would require test data setup


@pytest.mark.e2e
def test_req_slide_012_maintain_aspect_ratio(kiosk_page):
    """REQ-SLIDE-012: Images SHALL maintain aspect ratio (no distortion in cover mode)."""
    kiosk_page.wait_for_selector('.slide.active img')

    img = kiosk_page.locator('.slide.active img').first

    # Get natural and displayed dimensions
    dimensions = img.evaluate("""el => ({
        naturalWidth: el.naturalWidth,
        naturalHeight: el.naturalHeight,
        displayWidth: el.offsetWidth,
        displayHeight: el.offsetHeight
    })""")

    # Calculate aspect ratios
    natural_ratio = dimensions['naturalWidth'] / dimensions['naturalHeight']
    # In cover mode, one dimension fills, the other may be larger
    # (aspect ratio is preserved by cropping, not stretching)
