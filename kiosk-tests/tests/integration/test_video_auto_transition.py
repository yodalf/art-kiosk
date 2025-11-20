"""Test that videos auto-transition after the interval expires."""
import pytest
import requests
import os
import time
from playwright.sync_api import sync_playwright

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
def test_video_auto_transition():
    """
    Test that a video automatically transitions to the next item after the interval.

    Steps:
    1. Get the current "All Images" interval and save it
    2. Set a short interval (10 seconds)
    3. Get list of videos
    4. Jump to a video
    5. Wait for interval + buffer
    6. Verify kiosk has transitioned to a different item
    7. Restore original interval
    """
    original_interval = None
    TEST_INTERVAL = 10  # 10 seconds for testing

    try:
        # Step 1: Save original interval
        print("\nStep 1: Saving original interval...")
        themes_data = get_themes()
        all_images_theme = themes_data.get('themes', {}).get('All Images', {})
        original_interval = all_images_theme.get('interval', 3600)
        print(f"  Original interval: {original_interval} seconds")

        # Step 2: Set short test interval
        print(f"\nStep 2: Setting test interval to {TEST_INTERVAL} seconds...")
        assert set_theme_interval('All Images', TEST_INTERVAL), "Failed to set theme interval"

        # Verify it was set
        themes_data = get_themes()
        new_interval = themes_data.get('themes', {}).get('All Images', {}).get('interval')
        assert new_interval == TEST_INTERVAL, f"Interval not set correctly: {new_interval}"
        print(f"  Interval set to: {new_interval} seconds")

        # Step 3: Get videos
        print("\nStep 3: Getting video list...")
        videos = get_videos()
        if not videos:
            pytest.skip("No videos available for testing")

        video = videos[0]
        video_id = video.get('id')
        print(f"  Found video: {video_id}")

        # Step 4: Jump to video
        print("\nStep 4: Jumping to video...")
        assert jump_to_video(video_id), "Failed to jump to video"
        time.sleep(2)  # Wait for video to start

        # Get initial state
        initial_state = get_current_kiosk_state()
        print(f"  Initial state: {initial_state}")

        # Step 5: Wait for interval + buffer
        wait_time = TEST_INTERVAL + 5  # Add 5 second buffer
        print(f"\nStep 5: Waiting {wait_time} seconds for auto-transition...")
        time.sleep(wait_time)

        # Step 6: Check if transitioned
        print("\nStep 6: Checking if kiosk transitioned...")
        final_state = get_current_kiosk_state()
        print(f"  Final state: {final_state}")

        # The kiosk should have moved to a different item
        initial_image = initial_state.get('current_image') if initial_state else None
        final_image = final_state.get('current_image') if final_state else None

        # If we started on a video, we should now be on something different
        # (either another video or an image)
        if initial_image and initial_image.startswith('video:'):
            assert final_image != initial_image, \
                f"Kiosk did not auto-transition! Still showing: {final_image}"
            print(f"  ✓ Kiosk transitioned from {initial_image} to {final_image}")
        else:
            print(f"  Warning: Initial state was not a video: {initial_image}")

        print("\n✓ Video auto-transition test PASSED!")

    finally:
        # Restore original interval
        if original_interval is not None:
            print(f"\nCleanup: Restoring original interval ({original_interval} seconds)...")
            set_theme_interval('All Images', original_interval)
            print("  Cleanup complete")


@pytest.mark.integration
def test_video_auto_transition_with_playwright():
    """
    Test video auto-transition using Playwright to observe actual display.

    This test uses a browser to verify the visual transition.
    """
    original_interval = None
    TEST_INTERVAL = 10  # 10 seconds for testing

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        try:
            # Step 1: Save original interval
            print("\nStep 1: Saving original interval...")
            themes_data = get_themes()
            all_images_theme = themes_data.get('themes', {}).get('All Images', {})
            original_interval = all_images_theme.get('interval', 3600)
            print(f"  Original interval: {original_interval} seconds")

            # Step 2: Set short test interval
            print(f"\nStep 2: Setting test interval to {TEST_INTERVAL} seconds...")
            assert set_theme_interval('All Images', TEST_INTERVAL), "Failed to set theme interval"
            print(f"  Interval set to: {TEST_INTERVAL} seconds")

            # Step 3: Get videos
            print("\nStep 3: Getting video list...")
            videos = get_videos()
            if not videos:
                pytest.skip("No videos available for testing")

            video = videos[0]
            video_id = video.get('id')
            print(f"  Found video: {video_id}")

            # Step 4: Navigate to kiosk view
            print("\nStep 4: Navigating to kiosk view...")
            page.goto(f"{BASE_URL}/view")
            time.sleep(3)  # Wait for page to load

            # Step 5: Jump to video
            print("\nStep 5: Jumping to video...")
            assert jump_to_video(video_id), "Failed to jump to video"
            time.sleep(3)  # Wait for video to start

            # Take initial screenshot
            screenshot1 = page.screenshot()
            print("  Took initial screenshot")

            # Step 6: Wait for interval + buffer
            wait_time = TEST_INTERVAL + 5
            print(f"\nStep 6: Waiting {wait_time} seconds for auto-transition...")
            time.sleep(wait_time)

            # Take final screenshot
            screenshot2 = page.screenshot()
            print("  Took final screenshot")

            # Step 7: Compare screenshots
            print("\nStep 7: Comparing screenshots...")
            import hashlib
            hash1 = hashlib.md5(screenshot1).hexdigest()
            hash2 = hashlib.md5(screenshot2).hexdigest()

            print(f"  Initial hash: {hash1[:16]}...")
            print(f"  Final hash:   {hash2[:16]}...")

            # Screenshots should be different if transition occurred
            if hash1 != hash2:
                print("  ✓ Screenshots differ - transition occurred!")
            else:
                print("  ✗ Screenshots identical - NO transition!")
                # Save screenshots for debugging
                with open('/tmp/video_transition_before.png', 'wb') as f:
                    f.write(screenshot1)
                with open('/tmp/video_transition_after.png', 'wb') as f:
                    f.write(screenshot2)
                print("  Saved screenshots to /tmp/ for debugging")
                assert False, "Video did not auto-transition after interval"

            print("\n✓ Video auto-transition (Playwright) test PASSED!")

        finally:
            browser.close()

            # Restore original interval
            if original_interval is not None:
                print(f"\nCleanup: Restoring original interval ({original_interval} seconds)...")
                set_theme_interval('All Images', original_interval)
                print("  Cleanup complete")


if __name__ == "__main__":
    test_video_auto_transition_with_playwright()
