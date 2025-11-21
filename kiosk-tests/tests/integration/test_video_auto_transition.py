"""Test that videos auto-transition after the interval expires.

This test verifies that when a video is playing, the kiosk automatically
transitions to the next item after the configured interval expires.
"""
import pytest
import requests
import os
import time

# Load device configuration
def load_device_config():
    """Load device configuration from device.txt."""
    config = {}
    device_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'device.txt')
    with open(device_file, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                config[key] = value
    return config

DEVICE_CONFIG = load_device_config()
BASE_URL = f"http://{DEVICE_CONFIG['hostname']}"


def get_settings():
    """Get full settings."""
    response = requests.get(f"{BASE_URL}/api/settings", timeout=5)
    return response.json()


def get_themes():
    """Get themes."""
    response = requests.get(f"{BASE_URL}/api/themes", timeout=5)
    return response.json()


def set_theme_interval(theme_name, interval_seconds):
    """Set the interval for a theme."""
    response = requests.post(
        f"{BASE_URL}/api/themes/{theme_name}/interval",
        json={'interval': interval_seconds},
        timeout=5
    )
    return response.status_code == 200


def get_current_kiosk_state():
    """Get the current state of the kiosk (what's being displayed)."""
    response = requests.get(f"{BASE_URL}/api/kiosk/current-image", timeout=5)
    if response.status_code == 200:
        return response.json()
    return None


def get_videos():
    """Get list of videos."""
    response = requests.get(f"{BASE_URL}/api/videos", timeout=5)
    if response.status_code == 200:
        return response.json()
    return []


def jump_to_video(video_id):
    """Jump to a specific video."""
    response = requests.post(
        f"{BASE_URL}/api/control/send",
        json={'command': 'jump', 'image_name': f'video:{video_id}'},
        timeout=5
    )
    return response.status_code == 200


def send_command(command):
    """Send a command to the kiosk."""
    response = requests.post(
        f"{BASE_URL}/api/control/send",
        json={'command': command},
        timeout=5
    )
    return response.status_code == 200


@pytest.mark.integration
def test_video_auto_transition(isolated_test_data):
    """
    Test that a video automatically transitions to the next item after the interval.

    This test uses the jump command (same as clicking Play in manage.html) to start
    a video, then verifies the kiosk auto-transitions after the interval expires.

    Steps:
    1. Disable day scheduling and activate test theme
    2. Set a short interval (15 seconds)
    3. Get list of videos
    4. Jump to a video using jump command
    5. Wait for interval + buffer
    6. Verify kiosk has transitioned to a different item
    7. Restore original interval
    """
    # Use test theme with videos
    theme_name = 'TestTheme19ImagesVideoEnd'
    original_interval = None
    TEST_INTERVAL = 15  # 15 seconds for testing

    try:
        # Step 1: Disable day scheduling and activate test theme
        print("\nStep 1: Setting up test theme...")
        requests.post(f"{BASE_URL}/api/day/disable", timeout=5)
        requests.post(f"{BASE_URL}/api/themes/active", json={'theme': theme_name}, timeout=5)

        # Reload kiosk to pick up theme change
        requests.post(f"{BASE_URL}/api/control/send", json={'command': 'reload'}, timeout=5)
        time.sleep(2)

        # Save original interval
        themes_data = get_themes()
        test_theme = themes_data.get('themes', {}).get(theme_name, {})
        original_interval = test_theme.get('interval', 3600)
        print(f"  Original interval: {original_interval} seconds")

        # Step 2: Set short test interval
        print(f"\nStep 2: Setting test interval to {TEST_INTERVAL} seconds...")
        assert set_theme_interval(theme_name, TEST_INTERVAL), "Failed to set theme interval"

        # Verify it was set
        themes_data = get_themes()
        new_interval = themes_data.get('themes', {}).get(theme_name, {}).get('interval')
        assert new_interval == TEST_INTERVAL, f"Interval not set correctly: {new_interval}"
        print(f"  Interval set to: {new_interval} seconds")

        # Step 3: Get videos from isolated test data
        print("\nStep 3: Getting video list...")
        videos = isolated_test_data['themes'][theme_name]['videos']
        if not videos:
            pytest.skip("No videos available for testing")

        video_id = videos[0]
        print(f"  Found video: {video_id}")

        # Step 4: Jump to video using jump command (same as manage.html Play button)
        print("\nStep 4: Jumping to video via jump command...")
        # Note: videos in images array have name = video_id (without 'video:' prefix)
        response = requests.post(
            f"{BASE_URL}/api/control/send",
            json={'command': 'jump', 'image_name': video_id},
            timeout=5
        )
        assert response.status_code == 200, f"Failed to send jump command: {response.status_code}"

        # Wait for video to start (YouTube videos need time for yt-dlp to resolve and buffer)
        # Poll for up to 15 seconds for the video to be playing
        initial_image = None
        for _ in range(15):
            time.sleep(1)
            initial_state = get_current_kiosk_state()
            initial_image = initial_state.get('current_image') if initial_state else None
            if initial_image == video_id:
                break
        print(f"  Initial state: {initial_image}")

        # Verify the video is actually playing
        assert initial_image == video_id, \
            f"Video did not start! Expected {video_id}, got {initial_image}"
        print(f"  ✓ Video {video_id} is playing")

        # Step 5: Wait for interval + buffer
        wait_time = TEST_INTERVAL + 5  # Add 5 second buffer
        print(f"\nStep 5: Waiting {wait_time} seconds for auto-transition...")
        time.sleep(wait_time)

        # Step 6: Check if transitioned
        print("\nStep 6: Checking if kiosk transitioned...")
        final_state = get_current_kiosk_state()
        final_image = final_state.get('current_image') if final_state else None
        print(f"  Final state: {final_image}")

        # The kiosk should have moved to a different item
        assert final_image != initial_image, \
            f"Kiosk did not auto-transition! Still showing: {final_image}"
        print(f"  ✓ Kiosk transitioned from {initial_image} to {final_image}")

        print("\n✓ Video auto-transition test PASSED!")

    finally:
        # Restore original interval
        if original_interval is not None:
            print(f"\nCleanup: Restoring original interval ({original_interval} seconds)...")
            set_theme_interval(theme_name, original_interval)
            print("  Cleanup complete")

        # Stop any playing video
        try:
            requests.post(f"{BASE_URL}/api/videos/stop-mpv", timeout=5)
        except:
            pass


def get_images_list():
    """Get the current images list in order."""
    response = requests.get(f"{BASE_URL}/api/images?enabled_only=true", timeout=5)
    if response.status_code == 200:
        return response.json()
    return []


@pytest.mark.integration
def test_video_auto_transition_to_next_item(isolated_test_data):
    """
    Test that after video auto-transition, the kiosk shows the NEXT item
    in the list, not the first item.

    Steps:
    1. Disable day scheduling and activate test theme
    2. Set a short interval
    3. Get images list and find video position
    4. Jump to the video
    5. Wait for auto-transition
    6. Verify the kiosk shows the item AFTER the video in the list
    """
    theme_name = 'TestTheme19ImagesVideoEnd'
    original_interval = None
    TEST_INTERVAL = 10  # 10 seconds for testing

    try:
        # Step 1: Disable day scheduling and activate test theme
        print("\nStep 1: Setting up test theme...")
        requests.post(f"{BASE_URL}/api/day/disable", timeout=5)
        requests.post(f"{BASE_URL}/api/themes/active", json={'theme': theme_name}, timeout=5)

        # Reload kiosk to pick up theme change
        requests.post(f"{BASE_URL}/api/control/send", json={'command': 'reload'}, timeout=5)
        time.sleep(2)

        # Save original interval
        themes_data = get_themes()
        test_theme = themes_data.get('themes', {}).get(theme_name, {})
        original_interval = test_theme.get('interval', 3600)
        print(f"  Original interval: {original_interval} seconds")

        # Step 2: Set short test interval
        print(f"\nStep 2: Setting test interval to {TEST_INTERVAL} seconds...")
        assert set_theme_interval(theme_name, TEST_INTERVAL), "Failed to set theme interval"

        # Step 3: Get images list and find video position
        print("\nStep 3: Getting images list...")
        images = get_images_list()
        if len(images) < 2:
            pytest.skip("Need at least 2 items for this test")

        # Find a video from isolated test data in the list
        test_videos = isolated_test_data['themes'][theme_name]['videos']
        video_index = None
        video_id = None
        for i, item in enumerate(images):
            if item.get('name') in test_videos:
                video_index = i
                video_id = item.get('name')
                break

        if video_id is None:
            pytest.skip("No videos available for testing")

        # Get the next item after the video
        next_index = (video_index + 1) % len(images)
        next_item = images[next_index]
        next_item_name = next_item.get('name')

        print(f"  Video: {video_id} at index {video_index}")
        print(f"  Next item: {next_item_name} at index {next_index}")
        print(f"  Total items: {len(images)}")

        # Step 4: Jump to video
        print("\nStep 4: Jumping to video...")
        response = requests.post(
            f"{BASE_URL}/api/control/send",
            json={'command': 'jump', 'image_name': video_id},
            timeout=5
        )
        assert response.status_code == 200, f"Failed to send jump command"

        # Poll for up to 15 seconds for the video to be playing
        initial_image = None
        for _ in range(15):
            time.sleep(1)
            initial_state = get_current_kiosk_state()
            initial_image = initial_state.get('current_image') if initial_state else None
            if initial_image == video_id:
                break

        assert initial_image == video_id, f"Video did not start! Got {initial_image}"
        print(f"  ✓ Video {video_id} is playing")

        # Step 5: Wait for interval + buffer
        wait_time = TEST_INTERVAL + 5
        print(f"\nStep 5: Waiting {wait_time} seconds for auto-transition...")
        time.sleep(wait_time)

        # Step 6: Check that it transitioned to the NEXT item
        print("\nStep 6: Checking transition to next item...")
        final_state = get_current_kiosk_state()
        final_image = final_state.get('current_image') if final_state else None
        print(f"  Final state: {final_image}")
        print(f"  Expected: {next_item_name}")

        assert final_image == next_item_name, \
            f"Did not transition to next item! Expected {next_item_name}, got {final_image}"
        print(f"  ✓ Correctly transitioned to next item: {next_item_name}")

        print("\n✓ Video auto-transition to next item test PASSED!")

    finally:
        # Restore original interval
        if original_interval is not None:
            print(f"\nCleanup: Restoring original interval ({original_interval} seconds)...")
            set_theme_interval(theme_name, original_interval)
            print("  Cleanup complete")

        # Stop any playing video
        try:
            requests.post(f"{BASE_URL}/api/videos/stop-mpv", timeout=5)
        except:
            pass
