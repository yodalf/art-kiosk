"""Test backup and restore functionality."""
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

# Unique names for test objects
TEST_THEME_NAME = "TestBackupTheme12345"
TEST_ATMOSPHERE_NAME = "TestBackupAtmosphere12345"
TEST_TIME_PERIOD = "1"  # First time period (6:00 AM - 8:00 AM)


def create_test_image():
    """Create a simple test image and upload it. Returns the filename assigned by server."""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    files = {'file': ('test_backup_image.png', img_bytes, 'image/png')}
    response = requests.post(f"{BASE_URL}/api/images", files=files, timeout=30)
    if response.status_code == 200:
        data = response.json()
        return data.get('filename')
    return None


def get_images():
    """Get list of all images."""
    response = requests.get(f"{BASE_URL}/api/images", timeout=5)
    return response.json()


def get_themes():
    """Get list of all themes."""
    response = requests.get(f"{BASE_URL}/api/themes", timeout=5)
    return response.json()


def get_atmospheres():
    """Get list of all atmospheres."""
    response = requests.get(f"{BASE_URL}/api/atmospheres", timeout=5)
    return response.json()


def get_settings():
    """Get full settings."""
    response = requests.get(f"{BASE_URL}/api/settings", timeout=5)
    return response.json()


def create_theme(name):
    """Create a new theme."""
    response = requests.post(
        f"{BASE_URL}/api/themes",
        json={'name': name},
        timeout=5
    )
    return response.status_code == 200


def delete_theme(name):
    """Delete a theme."""
    response = requests.delete(f"{BASE_URL}/api/themes/{name}", timeout=5)
    return response.status_code == 200


def create_atmosphere(name):
    """Create a new atmosphere."""
    response = requests.post(
        f"{BASE_URL}/api/atmospheres",
        json={'name': name},
        timeout=5
    )
    return response.status_code == 200


def delete_atmosphere(name):
    """Delete an atmosphere."""
    response = requests.delete(f"{BASE_URL}/api/atmospheres/{name}", timeout=5)
    return response.status_code == 200


def assign_image_to_theme(image_name, theme_name):
    """Assign an image to a theme."""
    response = requests.post(
        f"{BASE_URL}/api/images/{image_name}/themes",
        json={'themes': [theme_name]},
        timeout=5
    )
    return response.status_code == 200


def assign_themes_to_atmosphere(atmosphere_name, theme_names):
    """Assign themes to an atmosphere."""
    response = requests.post(
        f"{BASE_URL}/api/atmospheres/{atmosphere_name}/themes",
        json={'themes': theme_names},
        timeout=5
    )
    return response.status_code == 200


def assign_atmosphere_to_time_period(time_id, atmosphere_names):
    """Assign atmospheres to a time period."""
    response = requests.post(
        f"{BASE_URL}/api/day/times/{time_id}/atmospheres",
        json={'atmospheres': atmosphere_names},
        timeout=5
    )
    return response.status_code == 200


def get_time_period_atmospheres(time_id):
    """Get atmospheres assigned to a time period."""
    settings = get_settings()
    day_times = settings.get('day_times', {})
    period = day_times.get(time_id, {})
    return period.get('atmospheres', [])


def delete_image(image_name):
    """Delete an image."""
    response = requests.delete(f"{BASE_URL}/api/images/{image_name}", timeout=5)
    return response.status_code == 200


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
        timeout=30
    )
    return response.status_code == 200


def delete_backup(backup_name):
    """Delete a backup."""
    response = requests.delete(f"{BASE_URL}/api/backup/{backup_name}", timeout=5)
    return response.status_code == 200


def image_exists(image_name):
    """Check if an image exists."""
    images = get_images()
    return any(img['name'] == image_name for img in images)


def theme_exists(theme_name):
    """Check if a theme exists."""
    data = get_themes()
    themes = data.get('themes', {})
    return theme_name in themes


def atmosphere_exists(atmosphere_name):
    """Check if an atmosphere exists."""
    data = get_atmospheres()
    atmospheres = data.get('atmospheres', {})
    return atmosphere_name in atmospheres


def image_in_theme(image_name, theme_name):
    """Check if an image is assigned to a theme."""
    settings = get_settings()
    image_themes = settings.get('image_themes', {})
    return theme_name in image_themes.get(image_name, [])


def theme_in_atmosphere(theme_name, atmosphere_name):
    """Check if a theme is assigned to an atmosphere."""
    settings = get_settings()
    atmosphere_themes = settings.get('atmosphere_themes', {})
    return theme_name in atmosphere_themes.get(atmosphere_name, [])


@pytest.mark.integration
def test_backup_restore():
    """
    Test that backup and restore works correctly:
    1. Create a new image
    2. Create a new theme
    3. Create a new atmosphere
    4. Assign image to theme
    5. Assign theme to atmosphere
    6. Assign atmosphere to time period
    7. Create a backup
    8. Delete all created objects
    9. Verify they are absent
    10. Restore the backup
    11. Verify objects are restored with all relationships
    12. Clean up
    """
    backup_name = None
    test_image_name = None

    try:
        # Pre-test cleanup: remove any leftover test artifacts
        print("\nPre-test cleanup...")
        assign_atmosphere_to_time_period(TEST_TIME_PERIOD, [])
        if atmosphere_exists(TEST_ATMOSPHERE_NAME):
            delete_atmosphere(TEST_ATMOSPHERE_NAME)
        if theme_exists(TEST_THEME_NAME):
            delete_theme(TEST_THEME_NAME)
        print("  Pre-test cleanup complete")

        # Step 1: Create test image
        print("\nStep 1: Creating test image...")
        test_image_name = create_test_image()
        assert test_image_name is not None, "Failed to create test image"
        assert image_exists(test_image_name), f"Image {test_image_name} not found after upload"
        print(f"  Created image: {test_image_name}")

        # Step 2: Create test theme
        print("\nStep 2: Creating test theme...")
        assert create_theme(TEST_THEME_NAME), "Failed to create test theme"
        assert theme_exists(TEST_THEME_NAME), f"Theme {TEST_THEME_NAME} not found after creation"
        print(f"  Created theme: {TEST_THEME_NAME}")

        # Step 3: Create test atmosphere
        print("\nStep 3: Creating test atmosphere...")
        assert create_atmosphere(TEST_ATMOSPHERE_NAME), "Failed to create test atmosphere"
        assert atmosphere_exists(TEST_ATMOSPHERE_NAME), f"Atmosphere {TEST_ATMOSPHERE_NAME} not found after creation"
        print(f"  Created atmosphere: {TEST_ATMOSPHERE_NAME}")

        # Step 4: Assign image to theme
        print("\nStep 4: Assigning image to theme...")
        assert assign_image_to_theme(test_image_name, TEST_THEME_NAME), "Failed to assign image to theme"
        assert image_in_theme(test_image_name, TEST_THEME_NAME), "Image not in theme after assignment"
        print(f"  Assigned {test_image_name} to {TEST_THEME_NAME}")

        # Step 5: Assign theme to atmosphere
        print("\nStep 5: Assigning theme to atmosphere...")
        assert assign_themes_to_atmosphere(TEST_ATMOSPHERE_NAME, [TEST_THEME_NAME]), "Failed to assign theme to atmosphere"
        assert theme_in_atmosphere(TEST_THEME_NAME, TEST_ATMOSPHERE_NAME), "Theme not in atmosphere after assignment"
        print(f"  Assigned {TEST_THEME_NAME} to {TEST_ATMOSPHERE_NAME}")

        # Step 6: Assign atmosphere to time period
        print("\nStep 6: Assigning atmosphere to time period...")
        assert assign_atmosphere_to_time_period(TEST_TIME_PERIOD, [TEST_ATMOSPHERE_NAME]), "Failed to assign atmosphere to time period"
        period_atmospheres = get_time_period_atmospheres(TEST_TIME_PERIOD)
        assert TEST_ATMOSPHERE_NAME in period_atmospheres, f"Atmosphere not in time period after assignment: {period_atmospheres}"
        print(f"  Assigned {TEST_ATMOSPHERE_NAME} to time period {TEST_TIME_PERIOD}")

        # Step 7: Create backup
        print("\nStep 7: Creating backup...")
        backup_name = create_backup()
        assert backup_name is not None, "Failed to create backup"
        print(f"  Created backup: {backup_name}")

        # Step 8: Delete the created objects
        print("\nStep 8: Deleting created objects...")

        # Clear time period assignment first
        assign_atmosphere_to_time_period(TEST_TIME_PERIOD, [])
        print(f"  Cleared time period {TEST_TIME_PERIOD}")

        # Delete atmosphere
        assert delete_atmosphere(TEST_ATMOSPHERE_NAME), "Failed to delete test atmosphere"
        print(f"  Deleted atmosphere: {TEST_ATMOSPHERE_NAME}")

        # Delete theme
        assert delete_theme(TEST_THEME_NAME), "Failed to delete test theme"
        print(f"  Deleted theme: {TEST_THEME_NAME}")

        # Delete image
        assert delete_image(test_image_name), "Failed to delete test image"
        print(f"  Deleted image: {test_image_name}")

        # Step 9: Verify objects are absent
        print("\nStep 9: Verifying objects are absent...")
        assert not image_exists(test_image_name), f"Image {test_image_name} still exists after deletion"
        assert not theme_exists(TEST_THEME_NAME), f"Theme {TEST_THEME_NAME} still exists after deletion"
        assert not atmosphere_exists(TEST_ATMOSPHERE_NAME), f"Atmosphere {TEST_ATMOSPHERE_NAME} still exists after deletion"
        print("  Verified: image, theme, and atmosphere are absent")

        # Step 10: Restore from backup
        print("\nStep 10: Restoring from backup...")
        assert restore_backup(backup_name), "Failed to restore backup"
        print(f"  Restored from: {backup_name}")

        # Wait for restore to complete
        time.sleep(2)

        # Step 11: Verify objects are restored
        print("\nStep 11: Verifying objects are restored...")

        # Check image
        assert image_exists(test_image_name), f"Image {test_image_name} not restored"
        print(f"  Image restored: {test_image_name}")

        # Check theme
        assert theme_exists(TEST_THEME_NAME), f"Theme {TEST_THEME_NAME} not restored"
        print(f"  Theme restored: {TEST_THEME_NAME}")

        # Check atmosphere
        assert atmosphere_exists(TEST_ATMOSPHERE_NAME), f"Atmosphere {TEST_ATMOSPHERE_NAME} not restored"
        print(f"  Atmosphere restored: {TEST_ATMOSPHERE_NAME}")

        # Check image-theme assignment
        assert image_in_theme(test_image_name, TEST_THEME_NAME), "Image-theme assignment not restored"
        print(f"  Image-theme assignment restored")

        # Check theme-atmosphere assignment
        assert theme_in_atmosphere(TEST_THEME_NAME, TEST_ATMOSPHERE_NAME), "Theme-atmosphere assignment not restored"
        print(f"  Theme-atmosphere assignment restored")

        # Check atmosphere-time period assignment
        period_atmospheres = get_time_period_atmospheres(TEST_TIME_PERIOD)
        assert TEST_ATMOSPHERE_NAME in period_atmospheres, f"Atmosphere-time period assignment not restored: {period_atmospheres}"
        print(f"  Atmosphere-time period assignment restored")

        print("\n✓ Backup and restore test PASSED!")

    finally:
        # Cleanup: restore original state
        print("\nCleanup: Restoring original state...")

        # Clear time period assignment
        assign_atmosphere_to_time_period(TEST_TIME_PERIOD, [])
        print(f"  Cleared time period {TEST_TIME_PERIOD}")

        # Delete atmosphere if it exists
        if atmosphere_exists(TEST_ATMOSPHERE_NAME):
            delete_atmosphere(TEST_ATMOSPHERE_NAME)
            print(f"  Deleted atmosphere: {TEST_ATMOSPHERE_NAME}")

        # Delete theme if it exists
        if theme_exists(TEST_THEME_NAME):
            delete_theme(TEST_THEME_NAME)
            print(f"  Deleted theme: {TEST_THEME_NAME}")

        # Delete image if it exists
        if test_image_name and image_exists(test_image_name):
            delete_image(test_image_name)
            print(f"  Deleted image: {test_image_name}")

        # Delete backup if it was created
        if backup_name:
            delete_backup(backup_name)
            print(f"  Deleted backup: {backup_name}")

        print("  Cleanup complete")


if __name__ == "__main__":
    test_backup_restore()
