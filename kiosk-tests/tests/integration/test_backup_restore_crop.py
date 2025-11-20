"""Test backup and restore with image cropping."""
import pytest
import requests
import os
import time
from PIL import Image
import io

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


def create_test_image(width=200, height=200, color='blue'):
    """Create a test image and upload it. Returns the filename assigned by server."""
    img = Image.new('RGB', (width, height), color=color)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    files = {'file': ('test_crop_image.png', img_bytes, 'image/png')}
    response = requests.post(f"{BASE_URL}/api/images", files=files, timeout=30)
    if response.status_code == 200:
        data = response.json()
        return data.get('filename')
    return None


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


def clear_crop(image_name):
    """Clear crop data for an image."""
    settings = get_settings()
    if 'image_crops' in settings and image_name in settings['image_crops']:
        del settings['image_crops'][image_name]
        return save_settings(settings)
    return True


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


@pytest.mark.integration
def test_backup_restore_crop():
    """
    Test that backup and restore correctly handles image crops:
    1. Create a 200x200 test image
    2. Create first backup (no crop)
    3. Apply crop to remove part of image (50,50,100,100)
    4. Create second backup (with crop)
    5. Restore first backup
    6. Verify no crop data exists
    7. Restore second backup
    8. Verify crop data is restored
    9. Clean up both backups and image
    """
    test_image_name = None
    backup1_name = None
    backup2_name = None

    # Test image dimensions
    IMAGE_WIDTH = 200
    IMAGE_HEIGHT = 200

    # Crop parameters (crop to center 100x100)
    CROP_X = 50
    CROP_Y = 50
    CROP_WIDTH = 100
    CROP_HEIGHT = 100

    try:
        # Pre-test cleanup
        print("\nPre-test cleanup...")
        # Nothing specific to clean for this test
        print("  Pre-test cleanup complete")

        # Step 1: Create test image
        print("\nStep 1: Creating test image (200x200)...")
        test_image_name = create_test_image(IMAGE_WIDTH, IMAGE_HEIGHT)
        assert test_image_name is not None, "Failed to create test image"
        assert image_exists(test_image_name), f"Image {test_image_name} not found after upload"
        print(f"  Created image: {test_image_name}")

        # Step 2: Create first backup (no crop)
        print("\nStep 2: Creating first backup (no crop)...")
        backup1_name = create_backup()
        assert backup1_name is not None, "Failed to create first backup"
        print(f"  Created backup: {backup1_name}")

        # Step 3: Apply crop
        print("\nStep 3: Applying crop (50,50,100,100)...")
        assert set_crop(test_image_name, CROP_X, CROP_Y, CROP_WIDTH, CROP_HEIGHT, IMAGE_WIDTH, IMAGE_HEIGHT), "Failed to set crop"
        crop_data = get_crop(test_image_name)
        assert crop_data is not None, "Crop data not found after setting"
        assert crop_data['x'] == CROP_X, f"Crop X mismatch: expected {CROP_X}, got {crop_data['x']}"
        assert crop_data['y'] == CROP_Y, f"Crop Y mismatch: expected {CROP_Y}, got {crop_data['y']}"
        assert crop_data['width'] == CROP_WIDTH, f"Crop width mismatch: expected {CROP_WIDTH}, got {crop_data['width']}"
        assert crop_data['height'] == CROP_HEIGHT, f"Crop height mismatch: expected {CROP_HEIGHT}, got {crop_data['height']}"
        print(f"  Applied crop: x={CROP_X}, y={CROP_Y}, w={CROP_WIDTH}, h={CROP_HEIGHT}")

        # Step 4: Create second backup (with crop)
        print("\nStep 4: Creating second backup (with crop)...")
        backup2_name = create_backup()
        assert backup2_name is not None, "Failed to create second backup"
        print(f"  Created backup: {backup2_name}")

        # Step 5: Restore first backup (no crop)
        print("\nStep 5: Restoring first backup (no crop)...")
        assert restore_backup(backup1_name), "Failed to restore first backup"
        time.sleep(2)  # Wait for restore to complete
        print(f"  Restored from: {backup1_name}")

        # Step 6: Verify no crop data exists
        print("\nStep 6: Verifying no crop data after first restore...")
        crop_data = get_crop(test_image_name)
        assert crop_data is None, f"Unexpected crop data found after restoring first backup: {crop_data}"
        print("  Verified: no crop data (as expected)")

        # Jump to the image to visually verify
        print("  Jumping to image...")
        jump_to_image(test_image_name)
        time.sleep(1)

        # Step 7: Restore second backup (with crop)
        print("\nStep 7: Restoring second backup (with crop)...")
        assert restore_backup(backup2_name), "Failed to restore second backup"
        time.sleep(2)  # Wait for restore to complete
        print(f"  Restored from: {backup2_name}")

        # Step 8: Verify crop data is restored
        print("\nStep 8: Verifying crop data after second restore...")
        crop_data = get_crop(test_image_name)
        assert crop_data is not None, "Crop data not found after restoring second backup"
        assert crop_data['x'] == CROP_X, f"Crop X mismatch: expected {CROP_X}, got {crop_data['x']}"
        assert crop_data['y'] == CROP_Y, f"Crop Y mismatch: expected {CROP_Y}, got {crop_data['y']}"
        assert crop_data['width'] == CROP_WIDTH, f"Crop width mismatch: expected {CROP_WIDTH}, got {crop_data['width']}"
        assert crop_data['height'] == CROP_HEIGHT, f"Crop height mismatch: expected {CROP_HEIGHT}, got {crop_data['height']}"
        print(f"  Verified crop data: x={crop_data['x']}, y={crop_data['y']}, w={crop_data['width']}, h={crop_data['height']}")

        # Jump to the image to visually verify
        print("  Jumping to image...")
        jump_to_image(test_image_name)
        time.sleep(1)

        print("\n✓ Backup and restore crop test PASSED!")

    finally:
        # Cleanup
        print("\nCleanup: Restoring original state...")

        # Delete image if it exists
        if test_image_name and image_exists(test_image_name):
            delete_image(test_image_name)
            print(f"  Deleted image: {test_image_name}")

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
