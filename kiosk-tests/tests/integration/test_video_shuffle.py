"""
Integration tests for Video Shuffle Requirements.

Tests that the shuffle_id is regenerated when the last item (video) transitions,
causing the list to be re-shuffled.
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
    """Check if mpv is running on the remote device (excludes zombie/defunct processes)."""
    hostname = device_config.get('hostname', 'raspberrypi.local')
    username = device_config.get('username', 'realo')
    password = device_config.get('password', 'toto')

    cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no {username}@{hostname} 'ps aux | grep \"[m]pv\" | grep -v defunct | grep -v grep'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() != ''


def wait_for_mpv_stopped(timeout=15):
    """Wait for mpv to stop, return True if stopped within timeout."""
    start = time.time()
    while time.time() - start < timeout:
        if not is_mpv_running():
            return True
        time.sleep(0.5)
    return False


@pytest.mark.integration
@pytest.mark.video
def test_shuffle_regenerates_when_video_last_item_transitions(api_client, isolated_test_data):
    """
    When the last item in a randomized list is a video and it transitions,
    the shuffle_id SHALL be regenerated to re-shuffle the list.

    Uses the isolated test data with TestTheme19ImagesVideoEnd which has
    19 images and 1 video at the end.
    """
    # Use the pre-configured theme with 19 images + 1 video
    theme_name = 'TestTheme19ImagesVideoEnd'
    test_images = isolated_test_data['themes'][theme_name]['images']
    test_video = isolated_test_data['themes'][theme_name]['videos'][0]

    print(f"\nUsing theme: {theme_name}")
    print(f"  Images: {len(test_images)}")
    print(f"  Video: {test_video}")

    # Step 1: Activate test theme
    print("\nStep 1: Activating test theme...")
    api_client.post('/api/themes/active', json={'theme': theme_name})
    time.sleep(1)

    # Verify theme is active
    response = api_client.get('/api/images', params={'enabled_only': 'true'})
    theme_items = response.json()
    print(f"  Theme has {len(theme_items)} items (expected 20)")
    assert len(theme_items) == 20, f"Expected 20 items, got {len(theme_items)}"

    # Step 2: Find a shuffle_id that puts the video at the last position
    print("\nStep 2: Finding shuffle_id that puts video last...")

    video_index = None
    for attempt in range(200):
        test_shuffle_id = attempt * 0.005  # 0.0, 0.005, 0.01, ...

        # Get full settings, update shuffle_id, save back
        response = api_client.get('/api/settings')
        settings = response.json()
        settings['shuffle_id'] = test_shuffle_id
        api_client.post('/api/settings', json=settings)
        time.sleep(0.05)

        # Get the items in our theme
        response = api_client.get('/api/images', params={'enabled_only': 'true'})
        theme_items = response.json()

        # Find the video's position
        video_index = None
        for i, item in enumerate(theme_items):
            if item.get('name') == test_video:
                video_index = i
                break

        # Check if video is at the last position
        if video_index == len(theme_items) - 1:
            print(f"  ✓ Found shuffle_id={test_shuffle_id} puts video at last position (index {video_index})")
            break
    else:
        print(f"  Items found: {len(theme_items)}, video at index: {video_index}")
        pytest.fail(f"Could not find shuffle_id that puts video at last position after 200 attempts")

    # List the last few items
    print(f"  Theme has {len(theme_items)} items")
    for i in range(max(0, len(theme_items) - 3), len(theme_items)):
        item = theme_items[i]
        item_type = item.get('type', 'image')
        print(f"    {i}: {item.get('name')} ({item_type})")

    # Step 3: Jump to video
    print("\nStep 3: Jumping to video...")
    api_client.post('/api/control/send', json={'command': 'reload'})
    time.sleep(1)
    api_client.post('/api/control/send', json={'command': 'jump', 'image_name': test_video})
    time.sleep(5)

    # Verify video started
    if not is_mpv_running():
        time.sleep(5)
        if not is_mpv_running():
            pytest.skip("Video did not start")

    print("  ✓ Video is playing")

    # Get shuffle_id before transition
    response = api_client.get('/api/settings')
    shuffle_id_before = response.json().get('shuffle_id')
    print(f"\nStep 4: Shuffle_id before transition: {shuffle_id_before}")

    # Step 5: Wait for video to auto-transition
    print("\nStep 5: Waiting for video auto-transition (20 seconds)...")
    time.sleep(20)

    # Check mpv stopped
    mpv_stopped = wait_for_mpv_stopped(timeout=10)
    print(f"  mpv stopped: {mpv_stopped}")

    # Get shuffle_id after transition
    response = api_client.get('/api/settings')
    shuffle_id_after = response.json().get('shuffle_id')
    print(f"\nStep 6: Shuffle_id after transition: {shuffle_id_after}")

    # Check current item
    response = api_client.get('/api/kiosk/current-image')
    current_image = response.json().get('current_image')
    print(f"  Current item after transition: {current_image}")

    # Verify it's one of our test images (not the video)
    is_test_image = current_image in test_images
    print(f"  Is test image: {is_test_image}")

    # Check results
    if shuffle_id_before != shuffle_id_after:
        print("\n✓ Shuffle_id changed - list was re-shuffled!")
    else:
        print("\n✗ Shuffle_id did NOT change - list was NOT re-shuffled!")

    assert shuffle_id_before != shuffle_id_after, \
        f"shuffle_id should change when video (last item) transitions. Before: {shuffle_id_before}, After: {shuffle_id_after}"

    print("\n✓ Video shuffle test PASSED!")


@pytest.mark.integration
@pytest.mark.video
def test_shuffle_id_changes_on_list_wrap(api_client, isolated_test_data):
    """
    Simpler test: Verify that shuffle_id changes when slideshow wraps around.

    This tests the general requirement that shuffle_id regenerates when
    the slideshow completes a full cycle.
    """
    # Use TestTheme10Images for faster test (fewer items)
    theme_name = 'TestTheme10Images'

    print(f"\nUsing theme: {theme_name}")

    # Activate theme
    api_client.post('/api/themes/active', json={'theme': theme_name})
    time.sleep(0.5)

    # Get initial shuffle_id
    response = api_client.get('/api/settings')
    settings = response.json()
    initial_shuffle_id = settings.get('shuffle_id')
    print(f"\nStep 1: Initial shuffle_id: {initial_shuffle_id}")

    # Set very short interval
    print("\nStep 2: Setting 3-second interval...")
    api_client.post(f'/api/themes/{theme_name}/interval', json={'interval': 3})

    # Get enabled items count
    response = api_client.get('/api/images', params={'enabled_only': 'true'})
    items = response.json()
    item_count = len(items)
    print(f"  Item count: {item_count}")

    if item_count == 0:
        pytest.skip("No enabled items")

    # Calculate time to complete one full cycle
    # Each item shows for 3 seconds
    cycle_time = item_count * 3 + 5  # Add buffer

    print(f"\nStep 3: Waiting for full cycle ({cycle_time} seconds)...")

    # Reload to start fresh
    api_client.post('/api/control/send', json={'command': 'reload'})

    # Wait for full cycle
    for i in range(0, cycle_time, 5):
        time.sleep(5)
        print(f"  Waited {i + 5} seconds...")

    # Get final shuffle_id
    response = api_client.get('/api/settings')
    final_shuffle_id = response.json().get('shuffle_id')
    print(f"\nStep 4: Final shuffle_id: {final_shuffle_id}")

    # Check if changed
    if initial_shuffle_id != final_shuffle_id:
        print("\n✓ Shuffle_id changed after full cycle!")
    else:
        print("\n✗ Shuffle_id did NOT change after full cycle")

    assert initial_shuffle_id != final_shuffle_id, \
        f"shuffle_id should change after completing a full cycle"
