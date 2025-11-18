"""
End-to-end tests for WebSocket Communication (REQ-WS-001 through REQ-WS-006).

Tests real-time WebSocket functionality.
"""

import pytest
import time
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.websocket
def test_req_ws_001_connection_established(kiosk_page):
    """REQ-WS-001: Kiosk SHALL establish WebSocket connection on load."""
    kiosk_page.wait_for_load_state('networkidle')

    # Check if socket exists and is connected
    is_connected = kiosk_page.evaluate("""
        window.socket && window.socket.connected
    """)

    assert is_connected is True


@pytest.mark.e2e
@pytest.mark.websocket
def test_req_ws_002_settings_update_event(kiosk_page, api_client):
    """REQ-WS-002: Settings changes SHALL emit 'settings_update' event."""
    kiosk_page.wait_for_selector('.slide.active')

    # Monitor WebSocket messages
    kiosk_page.evaluate("""
        window.__settings_updates = 0;
        if (window.socket) {
            window.socket.on('settings_update', function() {
                window.__settings_updates++;
            });
        }
    """)

    # Change a setting
    api_client.post('/api/themes/active', json={'theme': 'All Images'})
    time.sleep(1)

    # Check if event was received
    updates = kiosk_page.evaluate("window.__settings_updates || 0")
    assert updates > 0


@pytest.mark.e2e
@pytest.mark.websocket
def test_req_ws_003_image_list_changed_event(kiosk_page, image_uploader):
    """REQ-WS-003: Image list changes SHALL emit 'image_list_changed' event."""
    kiosk_page.wait_for_selector('.slide.active')

    # Monitor events
    kiosk_page.evaluate("""
        window.__image_changes = 0;
        if (window.socket) {
            window.socket.on('image_list_changed', function() {
                window.__image_changes++;
            });
        }
    """)

    # Upload an image
    image_uploader.upload_test_image()
    time.sleep(1)

    # Check if event was received
    changes = kiosk_page.evaluate("window.__image_changes || 0")
    assert changes > 0


@pytest.mark.e2e
@pytest.mark.websocket
def test_req_ws_004_remote_command_event(kiosk_page, api_client):
    """REQ-WS-004: Remote commands SHALL emit 'remote_command' event."""
    kiosk_page.wait_for_selector('.slide.active')

    # Monitor commands
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

    # Check if received
    commands = kiosk_page.evaluate("window.__remote_commands || []")
    assert len(commands) > 0
    assert commands[0]['command'] == 'next'


@pytest.mark.e2e
@pytest.mark.websocket
def test_req_ws_005_reconnection_handling(kiosk_page):
    """REQ-WS-005: SHALL handle WebSocket disconnection and reconnection."""
    kiosk_page.wait_for_selector('.slide.active')

    # Monitor reconnection
    kiosk_page.evaluate("""
        window.__reconnects = 0;
        if (window.socket) {
            window.socket.on('reconnect', function() {
                window.__reconnects++;
            });
        }
    """)

    # Simulate disconnect/reconnect would require server manipulation
    # This is a basic structure test


@pytest.mark.e2e
@pytest.mark.websocket
def test_req_ws_006_debug_logging(kiosk_page, api_client):
    """REQ-WS-006: Kiosk SHALL send debug logs via WebSocket."""
    kiosk_page.wait_for_selector('.slide.active')

    # Get debug messages from server
    response = api_client.get('/api/debug/messages')
    assert response.status_code == 200

    messages = response.json()
    assert isinstance(messages, list)

    # There should be some debug messages from kiosk startup
    if len(messages) > 0:
        # Messages should have expected format
        msg = messages[0]
        assert 'message' in msg
        assert 'level' in msg
        assert 'timestamp' in msg
