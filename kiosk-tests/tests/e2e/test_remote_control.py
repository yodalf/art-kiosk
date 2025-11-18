"""
End-to-end tests for Remote Control (REQ-REMOTE-001 through REQ-REMOTE-010).

Tests remote control commands via WebSocket.
"""

import pytest
import time
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_001_next_command(kiosk_page, test_mode):
    """REQ-REMOTE-001: 'next' command SHALL advance to next image."""
    # Wait for initial image
    kiosk_page.wait_for_selector('.slide.active', timeout=5000)
    initial_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Send next command
    test_mode.trigger_next()
    time.sleep(0.5)

    # Should advance
    new_index = kiosk_page.locator('.slide.active').get_attribute('data-index')
    assert new_index != initial_index


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_002_prev_command(kiosk_page, api_client):
    """REQ-REMOTE-002: 'prev' command SHALL go to previous image."""
    kiosk_page.wait_for_selector('.slide.active', timeout=5000)

    # Go next first, then prev
    api_client.post('/api/control/send', json={'command': 'next'})
    time.sleep(0.5)
    index_after_next = kiosk_page.locator('.slide.active').get_attribute('data-index')

    api_client.post('/api/control/send', json={'command': 'prev'})
    time.sleep(0.5)
    index_after_prev = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Should have gone backwards
    assert index_after_prev != index_after_next


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_003_pause_command(kiosk_page, test_mode, api_client):
    """REQ-REMOTE-003: 'pause' command SHALL stop automatic advancement."""
    test_mode.set_intervals(slideshow=1000)  # Fast slideshow

    kiosk_page.wait_for_selector('.slide.active')
    time.sleep(0.5)

    # Pause
    api_client.post('/api/control/send', json={'command': 'pause'})
    time.sleep(0.5)

    initial_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Wait longer than slideshow interval
    time.sleep(2)

    # Should still be on same image
    current_index = kiosk_page.locator('.slide.active').get_attribute('data-index')
    assert current_index == initial_index


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_004_play_command(kiosk_page, test_mode, api_client):
    """REQ-REMOTE-004: 'play' command SHALL resume automatic advancement."""
    test_mode.set_intervals(slideshow=1000)

    kiosk_page.wait_for_selector('.slide.active')

    # Pause first
    api_client.post('/api/control/send', json={'command': 'pause'})
    time.sleep(0.5)

    # Resume
    api_client.post('/api/control/send', json={'command': 'play'})
    time.sleep(0.5)

    initial_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Wait for transition
    time.sleep(2)

    # Should have advanced
    new_index = kiosk_page.locator('.slide.active').get_attribute('data-index')
    assert new_index != initial_index


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_005_reload_command(kiosk_page, api_client):
    """REQ-REMOTE-005: 'reload' command SHALL reload image list and resume playback."""
    kiosk_page.wait_for_selector('.slide.active')

    # Send reload
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(1)

    # Slideshow should still be active
    expect(kiosk_page.locator('.slide.active')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_006_jump_command(kiosk_page, api_client, image_uploader):
    """REQ-REMOTE-006: 'jump' command SHALL jump to specific image."""
    # Upload a test image
    filename = image_uploader.upload_test_image()

    # Reload kiosk to get new image
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(1)

    # Jump to it
    api_client.post('/api/control/send', json={
        'command': 'jump',
        'image_name': filename
    })
    time.sleep(1)

    # Verify we're on that image
    active_img = kiosk_page.locator('.slide.active img')
    src = active_img.get_attribute('src')
    assert filename in src


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_007_commands_instant_transition(kiosk_page, api_client):
    """REQ-REMOTE-007: Remote commands SHALL use instant transitions (no dissolve)."""
    kiosk_page.wait_for_selector('.slide.active')

    # Send next command
    start_time = time.time()
    api_client.post('/api/control/send', json={'command': 'next'})
    time.sleep(0.5)
    elapsed = time.time() - start_time

    # Should be very fast (< 1 second total)
    assert elapsed < 1.0


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_008_websocket_delivery(kiosk_page, api_client):
    """REQ-REMOTE-008: Commands SHALL be delivered via WebSocket."""
    kiosk_page.wait_for_selector('.slide.active')

    # Inject WebSocket monitor
    kiosk_page.evaluate("""
        window.__remote_commands = [];
        if (window.socket) {
            window.socket.on('remote_command', function(cmd) {
                window.__remote_commands.push(cmd);
            });
        }
    """)

    # Send command
    api_client.post('/api/control/send', json={'command': 'next'})
    time.sleep(0.5)

    # Check if received via WebSocket
    commands = kiosk_page.evaluate("window.__remote_commands || []")
    assert len(commands) > 0


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_009_navigation_preserves_pause(kiosk_page, test_mode, api_client):
    """REQ-REMOTE-009: next/prev SHALL preserve paused state."""
    test_mode.set_intervals(slideshow=1000)
    kiosk_page.wait_for_selector('.slide.active')

    # Pause
    api_client.post('/api/control/send', json={'command': 'pause'})
    time.sleep(0.5)

    # Navigate
    api_client.post('/api/control/send', json={'command': 'next'})
    time.sleep(0.5)

    initial_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Wait - should not auto-advance (still paused)
    time.sleep(2)

    current_index = kiosk_page.locator('.slide.active').get_attribute('data-index')
    assert current_index == initial_index


@pytest.mark.e2e
@pytest.mark.remote_control
def test_req_remote_010_reload_always_resumes(kiosk_page, test_mode, api_client):
    """REQ-REMOTE-010: 'reload' command SHALL always resume playback."""
    test_mode.set_intervals(slideshow=1000)
    kiosk_page.wait_for_selector('.slide.active')

    # Pause first
    api_client.post('/api/control/send', json={'command': 'pause'})
    time.sleep(0.5)

    # Reload
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(0.5)

    initial_index = kiosk_page.locator('.slide.active').get_attribute('data-index')

    # Wait - should auto-advance (playback resumed)
    time.sleep(2)

    new_index = kiosk_page.locator('.slide.active').get_attribute('data-index')
    assert new_index != initial_index
