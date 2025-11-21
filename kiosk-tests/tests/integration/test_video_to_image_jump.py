"""Test video to image jump transition."""
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
    """Check if mpv is running on the remote device via SSH."""
    hostname = device_config.get('hostname', 'raspberrypi.local')
    username = device_config.get('username', 'realo')
    password = device_config.get('password', 'toto')

    cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{hostname} 'ps aux | grep \"[m]pv\" | grep -v defunct | grep -v grep'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() != ''


def wait_for_video_playing(timeout=30):
    """Wait for video to start playing."""
    start = time.time()
    while time.time() - start < timeout:
        if is_mpv_running():
            return True
        time.sleep(1.0)
    return False


def wait_for_video_stopped(timeout=15):
    """Wait for video to stop."""
    start = time.time()
    while time.time() - start < timeout:
        if not is_mpv_running():
            return True
        time.sleep(0.5)
    return False


@pytest.mark.integration
def test_video_to_image_jump(api_client, isolated_test_data):
    """
    Test that clicking an image while video is playing:
    1. Stops the video
    2. Shows the CORRECT clicked image (not first image)
    3. Does not show spinner
    """
    # Use isolated test data
    images = isolated_test_data['images']
    videos = isolated_test_data['videos']

    assert len(images) >= 3, f"Need at least 3 images, got {len(images)}"
    assert len(videos) >= 1, f"Need at least 1 video, got {len(videos)}"

    # Pick the third image (not first, not second)
    target_image = images[2]
    first_image = images[0]
    video_id = videos[0]

    # Get video URL
    response = api_client.get('/api/videos')
    videos_data = response.json()
    video = next((v for v in videos_data if v['id'] == video_id), None)

    if not video:
        pytest.skip(f"Video {video_id} not found")

    print(f"\nTest setup:")
    print(f"  Target image (3rd): {target_image}")
    print(f"  First image: {first_image}")
    print(f"  Video: {video_id}")

    # Activate theme with our test images so jump works correctly
    print("\nActivating test theme...")
    api_client.post('/api/themes/active', json={'theme': 'TestTheme19ImagesVideoEnd'})

    # Reload kiosk to pick up theme change
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(2)

    # Step 1: Start video playback
    print("\nStep 1: Starting video...")
    response = api_client.post(
        '/api/videos/execute-mpv',
        json={'url': video['url'], 'video_id': video_id},
        timeout=10
    )
    assert response.status_code == 200, f"Failed to start video: {response.text}"

    # Wait for video to start
    assert wait_for_video_playing(timeout=30), "Video did not start playing"
    print("  Video is playing")

    # Let it play for a moment
    time.sleep(2)

    # Step 2: Stop video and jump to specific image
    print(f"\nStep 2: Stopping video and jumping to {target_image}...")
    response = api_client.post(
        '/api/videos/stop-mpv',
        json={'jump_to': target_image},
        timeout=10
    )
    assert response.status_code == 200, f"Failed to stop video: {response.text}"

    # Wait for video to stop
    assert wait_for_video_stopped(timeout=15), "Video did not stop"
    print("  Video stopped")

    # Wait for jump to complete
    time.sleep(2)

    # Step 3: Verify correct image is shown
    print("\nStep 3: Verifying correct image...")
    response = api_client.get('/api/kiosk/current-image')
    current = response.json()
    current_image = current.get('current_image')

    print(f"  Current image: {current_image}")
    print(f"  Expected: {target_image}")

    # Assert it's not the first image
    assert current_image != first_image, \
        f"Wrong image! Got first image '{first_image}' instead of '{target_image}'"

    # Assert it's the target image
    assert current_image == target_image, \
        f"Wrong image! Expected '{target_image}' but got '{current_image}'"

    # Assert it's not showing spinner (spinner would be empty or 'loading')
    assert current_image and not current_image.lower().startswith('load'), \
        f"Kiosk is showing spinner/loading state: {current_image}"

    print("\n✓ Test passed! Correct image is displayed")
