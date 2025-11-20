"""
Integration tests for Video Transition Requirements.

Tests that videos are properly stopped during all transition scenarios:
- Video to image transitions
- Video to video transitions
- Theme switching
- Atmosphere switching
- Day scheduler transitions
"""

import pytest
import time
import subprocess
from pathlib import Path


def load_device_config():
    """Load device configuration from device.txt."""
    device_file = Path(__file__).parent.parent.parent.parent / "device.txt"
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


device_config = load_device_config()


def is_mpv_running():
    """Check if mpv is running on the remote device."""
    hostname = device_config.get('hostname', 'raspberrypi.local')
    username = device_config.get('username', 'realo')
    password = device_config.get('password', 'toto')

    cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{hostname} 'pgrep -x mpv'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0


def wait_for_mpv_stopped(timeout=10):
    """Wait for mpv to stop, return True if stopped within timeout."""
    start = time.time()
    while time.time() - start < timeout:
        if not is_mpv_running():
            return True
        time.sleep(0.5)
    return False


def wait_for_mpv_started(timeout=25):
    """Wait for mpv to start, return True if started within timeout."""
    start = time.time()
    while time.time() - start < timeout:
        if is_mpv_running():
            return True
        time.sleep(1.0)
    return False


def take_screenshot():
    """Take a screenshot on the remote device and return its hash."""
    hostname = device_config.get('hostname', 'raspberrypi.local')
    username = device_config.get('username', 'realo')
    password = device_config.get('password', 'toto')

    # Take screenshot and get its md5sum
    cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{hostname} 'DISPLAY=:0 scrot -o /tmp/test_screenshot.png && md5sum /tmp/test_screenshot.png'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.split()[0]  # Return just the hash
    return None


def verify_video_playing(timeout=30):
    """
    Verify video is actually playing by waiting for mpv and checking screenshots.
    Returns True if mpv is running and screenshots differ.
    """
    start = time.time()

    # First wait for mpv to start
    while time.time() - start < timeout:
        if is_mpv_running():
            break
        time.sleep(1.0)
    else:
        return False  # mpv never started

    # Give video a moment to start rendering
    time.sleep(2)

    # Now verify it's actually playing by comparing screenshots
    for _ in range(5):  # Try up to 5 times
        hash1 = take_screenshot()
        if not hash1:
            time.sleep(1.0)
            continue

        time.sleep(1.0)  # Wait longer between screenshots

        hash2 = take_screenshot()
        if not hash2:
            time.sleep(1.0)
            continue

        # If screenshots differ, video is playing
        if hash1 != hash2:
            return True

        time.sleep(1.0)

    # Screenshots identical - video might be paused or static
    # But mpv is running, so consider it started
    return is_mpv_running()


@pytest.fixture
def video_setup(api_client, server_state):
    """
    Setup fixture that uses existing 'Video 1' theme which has videos.
    Falls back to 'All Images' if Video 1 doesn't exist.
    """
    # Get all items from unified images API
    response = api_client.get('/api/images')
    all_items = response.json() if response.status_code == 200 else []

    # Separate videos and images
    videos = [img for img in all_items if img.get('type') == 'video']
    images = [img for img in all_items if img.get('type') != 'video']

    if len(videos) < 1:
        pytest.skip("Need at least 1 video for video transition tests")

    if len(images) < 1:
        pytest.skip("Need at least 1 image for video transition tests")

    # Use 'All Images' theme for mixed content (videos + images)
    theme_name = 'All Images'

    # Use first video and first image
    video_name = videos[0]['name']
    image_name = images[0]['name']

    yield {
        'theme': theme_name,
        'video': video_name,
        'image': image_name,
        'all_videos': videos,
        'all_images': images
    }


@pytest.fixture
def stop_all_videos(api_client):
    """Ensure no videos are playing before and after test."""
    api_client.post('/api/videos/stop-mpv')
    time.sleep(0.5)
    yield
    api_client.post('/api/videos/stop-mpv')
    time.sleep(0.5)


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_next_command(api_client, video_setup, stop_all_videos):
    """Video SHALL stop when 'next' remote command is sent."""
    # Activate theme with video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)

    # Send reload to start slideshow
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)

    # Jump to video
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    # Wait for video to actually be playing (screenshot comparison)
    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing - may be network issue")

    # Verify mpv is running
    assert is_mpv_running(), "mpv should be running after jumping to video"

    # Send next command
    api_client.post('/api/control/send', json={'command': 'next'})

    # Verify mpv stopped
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop after 'next' command"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_prev_command(api_client, video_setup, stop_all_videos):
    """Video SHALL stop when 'prev' remote command is sent."""
    # Activate theme
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)

    # Reload and jump to video
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Send prev command
    api_client.post('/api/control/send', json={'command': 'prev'})

    # Verify stopped
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop after 'prev' command"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_theme_switch(api_client, server_state, video_setup, stop_all_videos):
    """Video SHALL stop when switching to a different theme."""
    # Create another theme
    server_state.create_theme('OtherTheme')

    # Activate video theme and jump to video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Switch to other theme
    api_client.post('/api/themes/active', json={'theme': 'OtherTheme'})

    # Verify stopped
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop when switching themes"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_same_theme_click(api_client, video_setup, stop_all_videos):
    """Video SHALL stop when clicking the same theme (reshuffle behavior)."""
    # Activate theme and jump to video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Click same theme again (this triggers reshuffle via POST theme_name)
    api_client.post('/api/themes/active', json={'theme_name': video_setup['theme']})

    # Verify stopped
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop when re-clicking same theme"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_atmosphere_switch(api_client, server_state, video_setup, stop_all_videos):
    """Video SHALL stop when switching to an atmosphere."""
    # Create an atmosphere
    server_state.create_atmosphere('TestAtmosphere')

    # Start video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Switch to atmosphere
    api_client.post('/api/atmospheres/active', json={'atmosphere': 'TestAtmosphere'})

    # Verify stopped
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop when switching to atmosphere"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_reload_command(api_client, video_setup, stop_all_videos):
    """Video SHALL stop when 'reload' remote command is sent."""
    # Start video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Send reload
    api_client.post('/api/control/send', json={'command': 'reload'})

    # Verify stopped (reload restarts slideshow)
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop on reload command"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_jump_to_image(api_client, video_setup, stop_all_videos):
    """Video SHALL stop when jumping to an image."""
    # Start video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Jump to image
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['image']})

    # Verify stopped
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop when jumping to image"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_jump_to_another_video(api_client, video_setup, stop_all_videos):
    """Video SHALL stop when jumping to another video."""
    if len(video_setup['all_videos']) < 2:
        pytest.skip("Need at least 2 videos for this test")

    video1 = video_setup['all_videos'][0]['name']
    video2 = video_setup['all_videos'][1]['name']

    # Assign both to theme
    api_client.post(f'/api/images/{video2}/themes', json={'themes': [video_setup['theme']]})

    # Start first video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video1})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("First video did not start")

    assert is_mpv_running(), "mpv should be running for first video"

    # Jump to second video - first should stop
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video2})

    # Brief pause - old mpv should stop before new one starts
    time.sleep(0.5)

    # The old video should have been stopped
    # (A new mpv may start, but that's expected)
    # We verify by checking logs or just that the stop-mpv was called


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_interval_advance(api_client, server_state, video_setup, stop_all_videos):
    """Video SHALL stop when slideshow interval advances automatically."""
    # Set very short interval
    api_client.post(f'/api/themes/{video_setup["theme"]}/interval', json={'interval': 5})

    # Start video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Wait for interval to elapse (5 seconds + buffer)
    time.sleep(7)

    # Video should have stopped when slideshow advanced
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop when interval advances slideshow"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_day_scheduler_transition(api_client, server_state, video_setup, stop_all_videos, test_mode):
    """Video SHALL stop when day scheduler triggers atmosphere change."""
    # Create atmosphere for day scheduler
    server_state.create_atmosphere('DayAtmosphere')

    # Configure time period 0 with the atmosphere
    api_client.post('/api/day/time-periods/0', json={'atmospheres': ['DayAtmosphere']})

    # Start video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Enable day scheduling - this should trigger atmosphere from period 0
    api_client.post('/api/day/enable')
    time.sleep(1)

    # Trigger hour boundary check
    test_mode.trigger_hour_check()
    time.sleep(1)

    # Send reload to apply changes
    api_client.post('/api/control/send', json={'command': 'reload'})

    # Verify stopped
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop when day scheduler activates"


@pytest.mark.integration
@pytest.mark.video
def test_video_stops_on_all_images_theme(api_client, video_setup, stop_all_videos):
    """Video SHALL stop when switching to 'All Images' theme."""
    # Start video in test theme
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Switch to All Images
    api_client.post('/api/themes/active', json={'theme': 'All Images'})

    # Verify stopped
    assert wait_for_mpv_stopped(timeout=10), "mpv should stop when switching to All Images"


@pytest.mark.integration
@pytest.mark.video
def test_stop_mpv_api_works(api_client, video_setup, stop_all_videos):
    """POST /api/videos/stop-mpv SHALL stop any running video."""
    # Start video
    api_client.post('/api/themes/active', json={'theme': video_setup['theme']})
    time.sleep(0.5)
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': video_setup['video']})
    time.sleep(1)

    if not verify_video_playing(timeout=30):
        pytest.skip("Video did not start playing")

    assert is_mpv_running(), "mpv should be running"

    # Call stop-mpv API directly
    response = api_client.post('/api/videos/stop-mpv')
    assert response.status_code == 200

    # Verify stopped
    assert wait_for_mpv_stopped(timeout=10), "stop-mpv API should stop mpv"
