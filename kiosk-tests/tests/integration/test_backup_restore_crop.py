"""Test backup and restore with image cropping - verifies visual crop application."""
import pytest
import requests
import os
import time
import hashlib
from PIL import Image
import io
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


def download_test_image():
    """
    Download a test image with clear visual features.
    Uses a colorful test pattern image that will show obvious differences when cropped.
    """
    # Download a test pattern image from a reliable source
    test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"

    response = requests.get(test_image_url, timeout=30)
    if response.status_code != 200:
        # Fallback: create a gradient image with text-like patterns
        return create_gradient_test_image()

    # Upload the downloaded image
    img_bytes = io.BytesIO(response.content)
    files = {'file': ('test_crop_image.png', img_bytes, 'image/png')}
    upload_response = requests.post(f"{BASE_URL}/api/images", files=files, timeout=30)
    if upload_response.status_code == 200:
        data = upload_response.json()
        return data.get('filename'), 280, 220  # Return filename and dimensions
    return None, 0, 0


def create_gradient_test_image():
    """
    Fallback: Create a test image with gradients and patterns.
    Top half: horizontal gradient (red to blue)
    Bottom half: vertical gradient (green to yellow)
    Plus diagonal lines for texture.
    """
    width, height = 400, 400
    img = Image.new('RGB', (width, height))

    for x in range(width):
        for y in range(height):
            if y < height // 2:
                # Top half: horizontal gradient red to blue
                r = int(255 * (1 - x / width))
                b = int(255 * (x / width))
                img.putpixel((x, y), (r, 0, b))
            else:
                # Bottom half: vertical gradient green to yellow
                g = 255
                r = int(255 * ((y - height//2) / (height//2)))
                img.putpixel((x, y), (r, g, 0))

            # Add diagonal lines for texture
            if (x + y) % 20 < 2:
                current = img.getpixel((x, y))
                img.putpixel((x, y), (min(255, current[0]+50), min(255, current[1]+50), min(255, current[2]+50)))

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    files = {'file': ('test_gradient_image.png', img_bytes, 'image/png')}
    response = requests.post(f"{BASE_URL}/api/images", files=files, timeout=30)
    if response.status_code == 200:
        data = response.json()
        return data.get('filename'), width, height
    return None, 0, 0


def get_settings():
    """Get full settings."""
    response = requests.get(f"{BASE_URL}/api/settings", timeout=5)
    return response.json()


def save_settings(settings):
    """Save settings."""
    response = requests.post(
        f"{BASE_URL}/api/settings",
        json=settings,
        headers={'Content-Type': 'application/json'},
        timeout=5
    )
    return response.status_code == 200


def set_crop(image_name, x, y, width, height, image_width, image_height):
    """Set crop data for an image."""
    settings = get_settings()
    if 'image_crops' not in settings:
        settings['image_crops'] = {}

    settings['image_crops'][image_name] = {
        'x': x,
        'y': y,
        'width': width,
        'height': height,
        'imageWidth': image_width,
        'imageHeight': image_height
    }
    return save_settings(settings)


def get_crop(image_name):
    """Get crop data for an image."""
    settings = get_settings()
    return settings.get('image_crops', {}).get(image_name)


def delete_image(image_name):
    """Delete an image."""
    response = requests.delete(f"{BASE_URL}/api/images/{image_name}", timeout=5)
    return response.status_code == 200


def image_exists(image_name):
    """Check if an image exists."""
    response = requests.get(f"{BASE_URL}/api/images", timeout=5)
    images = response.json()
    return any(img['name'] == image_name for img in images)


def create_backup():
    """Create a backup and return the backup name."""
    response = requests.post(
        f"{BASE_URL}/api/backup",
        json={'testing': True},
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return data['backup']['name']
    return None


def restore_backup(backup_name):
    """Restore from a backup."""
    response = requests.post(
        f"{BASE_URL}/api/backup/restore/{backup_name}",
        timeout=60
    )
    if response.status_code != 200:
        print(f"  Restore failed: {response.status_code} - {response.text}")
    return response.status_code == 200


def delete_backup(backup_name):
    """Delete a backup."""
    response = requests.delete(f"{BASE_URL}/api/backup/{backup_name}", timeout=5)
    return response.status_code == 200


def jump_to_image(image_name):
    """Send command to jump to a specific image."""
    response = requests.post(
        f"{BASE_URL}/api/control/send",
        json={'command': 'jump', 'image_name': image_name},
        timeout=5
    )
    return response.status_code == 200


def take_screenshot_hash(page, description="", save_path=None):
    """Take a screenshot and return its hash for comparison."""
    # Wait for any transitions to complete
    time.sleep(1)

    screenshot = page.screenshot()
    hash_value = hashlib.md5(screenshot).hexdigest()

    if description:
        print(f"    Screenshot hash ({description}): {hash_value[:16]}...")

    # Save screenshot to disk for inspection
    if save_path:
        with open(save_path, 'wb') as f:
            f.write(screenshot)
        print(f"    Saved screenshot to: {save_path}")

    return hash_value, screenshot


@pytest.mark.integration
def test_backup_restore_crop(isolated_test_data):
    """
    Test that backup and restore correctly handles image crops visually:
    1. Use test image from isolated_test_data
    2. Create first backup (no crop - shows all quadrants)
    3. Apply crop to bottom-right quadrant only (yellow)
    4. Create second backup (with crop)
    5. Restore first backup, take screenshot
    6. Restore second backup, take screenshot
    7. Verify screenshots are different (proves crop is applied)
    8. Clean up
    """
    backup1_name = None
    backup2_name = None

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        try:
            # Pre-test cleanup
            print("\nPre-test cleanup...")

            # Disable day scheduling and activate test theme
            requests.post(f"{BASE_URL}/api/day/disable", timeout=5)
            theme_name = 'TestTheme15Images'
            requests.post(f"{BASE_URL}/api/themes/active", json={'theme': theme_name}, timeout=5)
            requests.post(f"{BASE_URL}/api/control/send", json={'command': 'reload'}, timeout=5)
            time.sleep(2)
            print("  Pre-test cleanup complete")

            # Step 1: Use crop-test image from isolated_test_data (first image is the crop-test one)
            print("\nStep 1: Creating test image with visual features...")
            test_image_name = isolated_test_data['images'][0]  # First image is the crop-test image
            IMAGE_WIDTH, IMAGE_HEIGHT = 400, 400  # Known size from conftest.py
            assert image_exists(test_image_name), f"Image {test_image_name} not found"
            print(f"  Created image: {test_image_name} ({IMAGE_WIDTH}x{IMAGE_HEIGHT})")

            # Crop to bottom-right quarter of the image
            CROP_X = IMAGE_WIDTH // 2
            CROP_Y = IMAGE_HEIGHT // 2
            CROP_WIDTH = IMAGE_WIDTH // 2
            CROP_HEIGHT = IMAGE_HEIGHT // 2
            print(f"  Will crop to: x={CROP_X}, y={CROP_Y}, w={CROP_WIDTH}, h={CROP_HEIGHT}")

            # Step 2: Create first backup (no crop)
            print("\nStep 2: Creating first backup (no crop)...")
            backup1_name = create_backup()
            assert backup1_name is not None, "Failed to create first backup"
            print(f"  Created backup: {backup1_name}")

            # Step 3: Apply crop to bottom-right quarter
            print(f"\nStep 3: Applying crop to bottom-right quarter ({CROP_X},{CROP_Y},{CROP_WIDTH},{CROP_HEIGHT})...")
            assert set_crop(test_image_name, CROP_X, CROP_Y, CROP_WIDTH, CROP_HEIGHT, IMAGE_WIDTH, IMAGE_HEIGHT), "Failed to set crop"
            crop_data = get_crop(test_image_name)
            assert crop_data is not None, "Crop data not found after setting"
            print(f"  Applied crop: x={CROP_X}, y={CROP_Y}, w={CROP_WIDTH}, h={CROP_HEIGHT}")
            print("  This should show only the bottom-right quarter of the image")

            # Step 4: Create second backup (with crop)
            print("\nStep 4: Creating second backup (with crop)...")
            backup2_name = create_backup()
            assert backup2_name is not None, "Failed to create second backup"
            print(f"  Created backup: {backup2_name}")

            # Step 5: Restore first backup (no crop) and take screenshot
            print("\nStep 5: Restoring first backup (no crop)...")
            assert restore_backup(backup1_name), "Failed to restore first backup"
            time.sleep(3)  # Wait for restore and kiosk reload
            print(f"  Restored from: {backup1_name}")

            # Verify server-side: crop should NOT exist after restoring first backup
            server_crop = get_crop(test_image_name)
            if server_crop:
                print(f"  WARNING: Server still has crop data after restore: {server_crop}")
            else:
                print("  Server verified: no crop data in settings")

            # Navigate to kiosk view and jump to the image
            page.goto(f"{BASE_URL}/view")
            time.sleep(2)  # Wait for page load

            # Jump to the test image
            jump_to_image(test_image_name)
            time.sleep(2)  # Wait for image display

            print("\nStep 6: Taking screenshot of uncropped image...")
            hash1, screenshot1 = take_screenshot_hash(page, "uncropped - full image", "/tmp/crop_test_uncropped.png")

            # Step 7: Restore second backup (with crop) and take screenshot
            print("\nStep 7: Restoring second backup (with crop)...")
            assert restore_backup(backup2_name), "Failed to restore second backup"
            time.sleep(3)  # Wait for restore and kiosk reload
            print(f"  Restored from: {backup2_name}")

            # Reload the page and jump to image again
            page.reload()
            time.sleep(2)

            jump_to_image(test_image_name)
            time.sleep(2)

            print("\nStep 8: Taking screenshot of cropped image...")
            hash2, screenshot2 = take_screenshot_hash(page, "cropped - bottom-right only", "/tmp/crop_test_cropped.png")

            # Step 9: Verify screenshots are different
            print("\nStep 9: Comparing screenshots...")
            print(f"  Uncropped hash: {hash1}")
            print(f"  Cropped hash:   {hash2}")

            assert hash1 != hash2, f"Screenshots are identical! Crop was not visually applied. Hash: {hash1}"
            print("  ✓ Screenshots differ - crop was visually applied!")

            # Verify crop data is present
            crop_data = get_crop(test_image_name)
            assert crop_data is not None, "Crop data not found after restore"
            assert crop_data['x'] == CROP_X, f"Crop X mismatch"
            assert crop_data['y'] == CROP_Y, f"Crop Y mismatch"
            print("  ✓ Crop data verified in settings")

            print("\n✓ Backup and restore crop test PASSED!")

        finally:
            browser.close()

            # Cleanup - only delete backups, image is managed by isolated_test_data
            print("\nCleanup: Restoring original state...")

            # Clear any crop data we added
            settings = get_settings()
            if 'image_crops' in settings and test_image_name in settings.get('image_crops', {}):
                del settings['image_crops'][test_image_name]
                save_settings(settings)
                print(f"  Cleared crop data for: {test_image_name}")

            # Delete backups
            if backup1_name:
                delete_backup(backup1_name)
                print(f"  Deleted backup: {backup1_name}")

            if backup2_name:
                delete_backup(backup2_name)
                print(f"  Deleted backup: {backup2_name}")

            print("  Cleanup complete")


if __name__ == "__main__":
    test_backup_restore_crop()
