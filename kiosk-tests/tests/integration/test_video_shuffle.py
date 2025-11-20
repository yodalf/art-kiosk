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
def test_shuffle_regenerates_when_video_last_item_transitions(api_client, server_state):
    """
    When the last item in a randomized list is a video and it transitions,
    the shuffle_id SHALL be regenerated to re-shuffle the list.

    This test creates a controlled environment with:
    - A test theme with exactly 2 images and 1 video
    - Video set as the last item
    - Short interval for quick testing
    """
    import requests
    from io import BytesIO
    from PIL import Image

    # Track items to clean up
    test_theme_name = "TestShuffleTheme"
    test_image_ids = []
    test_video_id = None

    try:
        print("\nStep 1: Creating test theme...")
        response = api_client.post('/api/themes', json={'name': test_theme_name})
        if response.status_code != 200:
            pytest.fail(f"Failed to create test theme: {response.text}")
        print(f"  Created theme: {test_theme_name}")

        # Set short interval on test theme
        api_client.post(f'/api/themes/{test_theme_name}/interval', json={'interval': 10})
        print("  Set interval to 10 seconds")

        print("\nStep 2: Creating test images...")
        # Create 10 test images for better shuffle testing
        for i in range(10):
            # Create a simple colored image with different colors
            img = Image.new('RGB', (100, 100), color=((i * 25) % 256, (i * 50) % 256, (i * 75) % 256))
            img_bytes = BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)

            # Upload image
            files = {'file': (f'test_shuffle_{i}.jpg', img_bytes, 'image/jpeg')}
            response = api_client.post('/api/images', files=files)
            if response.status_code != 200:
                pytest.fail(f"Failed to upload test image {i}: {response.text}")

            image_data = response.json()
            image_id = image_data.get('filename')
            test_image_ids.append(image_id)
            print(f"  Created image {i+1}: {image_id}")

            # Assign to test theme
            api_client.post(f'/api/images/{image_id}/themes', json={'themes': [test_theme_name]})

        print("\nStep 3: Adding test video...")
        # Use a short test video
        test_video_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo"
        response = api_client.post('/api/videos', json={'url': test_video_url})
        if response.status_code != 200:
            pytest.fail(f"Failed to add test video: {response.text}")

        video_data = response.json()
        test_video_id = video_data.get('id')
        print(f"  Created video: {test_video_id}")

        # Assign video to test theme
        api_client.post(f'/api/videos/{test_video_id}/themes', json={'themes': [test_theme_name]})
        print(f"  Assigned video to {test_theme_name}")

        print("\nStep 4: Activating test theme and ensuring video is last...")
        api_client.post('/api/themes/active', json={'theme': test_theme_name})
        time.sleep(1)

        # Keep reshuffling until video is at the last position
        max_attempts = 20
        for attempt in range(max_attempts):
            # Get the items in our theme
            response = api_client.get('/api/images', params={'enabled_only': 'true'})
            theme_items = response.json()

            # Find the video's position
            video_index = None
            for i, item in enumerate(theme_items):
                if item.get('name') == test_video_id:
                    video_index = i
                    break

            # Check if video is at the last position
            if video_index == len(theme_items) - 1:
                print(f"  ✓ Video is at last position (index {video_index}) after {attempt + 1} attempts")
                break

            # Reshuffle by regenerating shuffle_id
            response = api_client.get('/api/settings')
            settings = response.json()
            import random as rand
            settings['shuffle_id'] = rand.random()
            # We need to trigger a reshuffle - reactivate the theme
            api_client.post('/api/themes/active', json={'theme': test_theme_name})
            time.sleep(0.3)
        else:
            pytest.skip(f"Could not get video to last position after {max_attempts} attempts")

        print(f"  Theme has {len(theme_items)} items")

        # List the items
        for i, item in enumerate(theme_items):
            item_type = item.get('type', 'image')
            print(f"    {i}: {item.get('name')} ({item_type})")

        print("\nStep 5: Jumping to video...")
        api_client.post('/api/control/send', json={'command': 'reload'})
        time.sleep(1)
        api_client.post('/api/control/send', json={'command': 'jump', 'image_name': test_video_id})
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
        print(f"\nStep 6: Shuffle_id before transition: {shuffle_id_before}")

        # Wait for video to auto-transition
        print("\nStep 7: Waiting for video auto-transition (15 seconds)...")
        time.sleep(15)

        # Check mpv stopped
        mpv_stopped = wait_for_mpv_stopped(timeout=10)
        print(f"  mpv stopped: {mpv_stopped}")

        # Get shuffle_id after transition
        response = api_client.get('/api/settings')
        shuffle_id_after = response.json().get('shuffle_id')
        print(f"\nStep 8: Shuffle_id after transition: {shuffle_id_after}")

        # Check current item
        response = api_client.get('/api/kiosk/current-image')
        current_image = response.json().get('current_image')
        print(f"  Current item after transition: {current_image}")

        # Verify it's one of our test images (not the video)
        is_test_image = current_image in test_image_ids
        print(f"  Is test image: {is_test_image}")

        # Check results
        if shuffle_id_before != shuffle_id_after:
            print("\n✓ Shuffle_id changed - list was re-shuffled!")
        else:
            print("\n✗ Shuffle_id did NOT change - list was NOT re-shuffled!")

        assert shuffle_id_before != shuffle_id_after, \
            f"shuffle_id should change when video (last item) transitions. Before: {shuffle_id_before}, After: {shuffle_id_after}"

        print("\n✓ Video shuffle test PASSED!")

    finally:
        print("\nCleanup: Deleting test resources...")

        # Stop any playing video
        api_client.post('/api/videos/stop-mpv')
        time.sleep(1)

        # Switch back to All Images theme
        api_client.post('/api/themes/active', json={'theme': 'All Images'})

        # Delete test video
        if test_video_id:
            response = api_client.delete(f'/api/videos/{test_video_id}')
            if response.status_code == 200:
                print(f"  Deleted video: {test_video_id}")
            else:
                print(f"  Warning: Failed to delete video: {response.text}")

        # Delete test images
        for image_id in test_image_ids:
            response = api_client.delete(f'/api/images/{image_id}')
            if response.status_code == 200:
                print(f"  Deleted image: {image_id}")
            else:
                print(f"  Warning: Failed to delete image: {response.text}")

        # Delete test theme
        response = api_client.delete(f'/api/themes/{test_theme_name}')
        if response.status_code == 200:
            print(f"  Deleted theme: {test_theme_name}")
        else:
            print(f"  Warning: Failed to delete theme: {response.text}")

        print("  Cleanup complete")


@pytest.mark.integration
@pytest.mark.video
def test_shuffle_id_changes_on_list_wrap(api_client, server_state):
    """
    Simpler test: Verify that shuffle_id changes when slideshow wraps around.

    This tests the general requirement that shuffle_id regenerates when
    the slideshow completes a full cycle.
    """
    # Get initial shuffle_id
    response = api_client.get('/api/settings')
    settings = response.json()
    original_interval = settings.get('interval', 3600)

    print("\nStep 1: Getting initial shuffle_id...")
    initial_shuffle_id = settings.get('shuffle_id')
    print(f"  Initial shuffle_id: {initial_shuffle_id}")

    try:
        # Set very short interval
        print("\nStep 2: Setting 3-second interval...")
        api_client.post('/api/themes/All Images/interval', json={'interval': 3})
        api_client.post('/api/themes/active', json={'theme': 'All Images'})
        time.sleep(0.5)

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

        # Note: This test may not always pass depending on timing
        # The important thing is that it documents the expected behavior
        assert initial_shuffle_id != final_shuffle_id, \
            f"shuffle_id should change after completing a full cycle"

    finally:
        # Cleanup
        print(f"\nCleanup: Restoring original interval ({original_interval} seconds)...")
        api_client.post('/api/themes/All Images/interval', json={'interval': original_interval})
        api_client.post('/api/videos/stop-mpv')
        print("  Cleanup complete")
