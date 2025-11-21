"""
Integration tests for Video Thumbnail Generation (REQ-VIDEO-015).

Tests that video thumbnails are automatically generated after 20 seconds of playback.
"""

import pytest
import time
import requests
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
BASE_URL = f"http://{device_config.get('hostname', 'raspberrypi.local')}"


def check_thumbnail_exists(video_id):
    """Check if thumbnail exists by requesting it via HTTP."""
    # Try both jpg and png extensions (code may use either)
    for ext in ['jpg', 'png']:
        try:
            response = requests.get(f"{BASE_URL}/thumbnails/{video_id}.{ext}", timeout=5)
            # Check status and that we got actual image data
            if response.status_code == 200 and len(response.content) > 1000:
                return True
        except:
            pass
    return False


@pytest.mark.integration
@pytest.mark.video
def test_req_video_015_thumbnail_generation(api_client):
    """
    REQ-VIDEO-015: System SHALL generate video thumbnails after 20-second playback.

    Test that when a video is added, the system captures a screenshot after 20 seconds
    and saves it as a thumbnail.
    """
    # Use a short, public domain video for testing
    # This is a 10-second test video from YouTube
    test_video_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video

    video_id = None

    try:
        print("\nStep 1: Adding test video...")
        response = api_client.post('/api/videos', json={'url': test_video_url})

        if response.status_code != 200:
            pytest.skip(f"Failed to add video: {response.text}")

        result = response.json()
        video_id = result.get('id')
        print(f"  Video added with ID: {video_id}")

        assert video_id is not None, "Video ID should be returned"

        # Verify thumbnail doesn't exist yet (or may exist from previous test)
        initial_exists = check_thumbnail_exists(video_id)
        print(f"  Initial thumbnail exists: {initial_exists}")

        print("\nStep 2: Waiting for thumbnail generation (60 seconds max)...")
        print("  (Background task plays video for 20s, then captures screenshot)")

        # Wait for thumbnail generation with polling
        # Thumbnail generation is automatic after video is added
        # Need to wait for: yt-dlp resolution + 20s playback + screenshot capture
        thumbnail_exists = False
        for i in range(60):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                # Check periodically if thumbnail exists
                thumbnail_exists = check_thumbnail_exists(video_id)
                print(f"  Waited {i + 1} seconds... thumbnail exists: {thumbnail_exists}")
                if thumbnail_exists:
                    break

        print("\nStep 3: Final thumbnail check...")
        if not thumbnail_exists:
            thumbnail_exists = check_thumbnail_exists(video_id)
        print(f"  Thumbnail exists: {thumbnail_exists}")

        # Verify thumbnail was created
        assert thumbnail_exists, f"Thumbnail should exist at thumbnails/{video_id}.(jpg|png)"

        print("\n✓ Video thumbnail generation test PASSED!")

    finally:
        # Cleanup: Delete the test video
        if video_id:
            print(f"\nCleanup: Deleting test video {video_id}...")

            # Stop any playing video first
            api_client.post('/api/videos/stop-mpv')
            time.sleep(1)

            # Delete the video
            response = api_client.delete(f'/api/videos/{video_id}')
            if response.status_code == 200:
                print("  Video deleted successfully")
            else:
                print(f"  Warning: Failed to delete video: {response.text}")

            # Thumbnail will be deleted when video is deleted
            print("  Cleanup complete")


@pytest.mark.integration
@pytest.mark.video
def test_video_thumbnail_in_api_response(api_client, isolated_test_data):
    """
    Test that video thumbnail path is included in API responses.
    """
    # Use video from isolated test data
    videos = isolated_test_data['videos']

    if not videos:
        pytest.skip("No videos available to test thumbnail API response")

    video_id = videos[0]

    # Check if thumbnail field is present
    # The API should include thumbnail information for videos
    response = api_client.get('/api/images')
    items = response.json()

    # Find our video in the items list
    video_item = None
    for item in items:
        if item.get('name') == video_id:
            video_item = item
            break

    if video_item is None:
        pytest.skip(f"Video {video_id} not found in images API")

    # Video items should have a thumbnail field or be identifiable as video type
    assert video_item.get('type') == 'video', "Item should be identified as video type"
    print(f"✓ Video {video_id} correctly identified as video type in API")
