"""Test video to image jump transition."""
import pytest
import time
import requests

# Test configuration
BASE_URL = "http://raspberrypi.local"


def is_mpv_running():
    """Check if mpv is running on the device."""
    try:
        response = requests.get(f"{BASE_URL}/api/videos/playback-status", timeout=5)
        data = response.json()
        return data.get('playing', False)
    except:
        return False


def wait_for_video_playing(timeout=30):
    """Wait for video to start playing."""
    start = time.time()
    while time.time() - start < timeout:
        if is_mpv_running():
            return True
        time.sleep(0.5)
    return False


def wait_for_video_stopped(timeout=10):
    """Wait for video to stop."""
    start = time.time()
    while time.time() - start < timeout:
        if not is_mpv_running():
            return True
        time.sleep(0.5)
    return False


def get_current_image():
    """Get the current image being displayed."""
    response = requests.get(f"{BASE_URL}/api/kiosk/current-image", timeout=5)
    return response.json()


def get_enabled_images():
    """Get list of enabled images."""
    response = requests.get(f"{BASE_URL}/api/images?enabled_only=true", timeout=5)
    return response.json()


def get_videos():
    """Get list of videos."""
    response = requests.get(f"{BASE_URL}/api/videos", timeout=5)
    return response.json()


@pytest.mark.integration
def test_video_to_image_jump():
    """
    Test that clicking an image while video is playing:
    1. Stops the video
    2. Shows the CORRECT clicked image (not first image)
    3. Does not show spinner
    """
    # Get available images and videos
    images = get_enabled_images()
    videos = get_videos()

    assert len(images) >= 3, f"Need at least 3 images, got {len(images)}"
    assert len(videos) >= 1, f"Need at least 1 video, got {len(videos)}"

    # Pick the third image (not first, not second)
    target_image = images[2]['name']
    first_image = images[0]['name']
    video = videos[0]

    print(f"\nTest setup:")
    print(f"  Target image (3rd): {target_image}")
    print(f"  First image: {first_image}")
    print(f"  Video: {video['id']}")

    # Step 1: Start video playback
    print("\nStep 1: Starting video...")
    response = requests.post(
        f"{BASE_URL}/api/videos/execute-mpv",
        json={'url': video['url'], 'video_id': video['id']},
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
    response = requests.post(
        f"{BASE_URL}/api/videos/stop-mpv",
        json={'jump_to': target_image},
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    assert response.status_code == 200, f"Failed to stop video: {response.text}"

    # Wait for video to stop
    assert wait_for_video_stopped(timeout=10), "Video did not stop"
    print("  Video stopped")

    # Wait for jump to complete
    time.sleep(2)

    # Step 3: Verify correct image is shown
    print("\nStep 3: Verifying correct image...")
    current = get_current_image()
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


if __name__ == "__main__":
    test_video_to_image_jump()
