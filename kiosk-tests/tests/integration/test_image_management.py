"""
Integration tests for Image Management (REQ-IMG-001 through REQ-IMG-016).

Tests image upload, listing, enable/disable, and deletion functionality.
"""

import pytest
import re


@pytest.mark.integration
def test_req_img_001_image_upload(image_uploader):
    """REQ-IMG-001: System SHALL accept image uploads via POST /api/images."""
    filename = image_uploader.upload_test_image()

    assert filename is not None
    assert filename.endswith('.png')


@pytest.mark.integration
def test_req_img_002_reject_large_files(api_client, test_image_generator):
    """REQ-IMG-002: System SHALL reject uploads exceeding 50MB."""
    # Create a 51MB file
    large_file = test_image_generator.create_large_file(51, '.jpg')

    with open(large_file, 'rb') as f:
        response = api_client.post('/api/images', files={'file': f})

    # Should reject (413 Payload Too Large or 400 Bad Request)
    assert response.status_code in [400, 413]


@pytest.mark.integration
def test_req_img_003_reject_unsupported_formats(api_client, test_image_generator):
    """REQ-IMG-003: System SHALL reject unsupported file formats."""
    # Create a text file disguised as image
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.txt')
    with open(path, 'w') as f:
        f.write("This is not an image")

    with open(path, 'rb') as f:
        response = api_client.post('/api/images', files={'file': ('test.txt', f)})

    # Should reject
    assert response.status_code in [400, 415]


@pytest.mark.integration
def test_req_img_004_uuid_filenames(image_uploader):
    """REQ-IMG-004: Uploaded images SHALL be assigned UUID-based filenames."""
    filename = image_uploader.upload_test_image()

    # UUID pattern: 8-4-4-4-12 hexadecimal
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(png|jpg|jpeg|gif|webp|bmp)$'
    assert re.match(uuid_pattern, filename), f"Filename {filename} doesn't match UUID pattern"


@pytest.mark.integration
def test_req_img_007_list_all_images(api_client, image_uploader):
    """REQ-IMG-007: GET /api/images SHALL return all images with metadata."""
    # Upload a test image
    filename = image_uploader.upload_test_image()

    response = api_client.get('/api/images')
    assert response.status_code == 200

    images = response.json()
    assert isinstance(images, list)

    # Find our uploaded image
    uploaded_image = next((img for img in images if img['name'] == filename), None)
    assert uploaded_image is not None
    assert 'name' in uploaded_image
    assert 'enabled' in uploaded_image


@pytest.mark.integration
def test_req_img_008_filter_enabled_only(api_client, image_uploader):
    """REQ-IMG-008: GET /api/images?enabled_only=true SHALL filter disabled images."""
    # Upload and immediately disable an image
    filename = image_uploader.upload_test_image()

    # Disable it
    api_client.post(f'/api/images/{filename}/toggle')

    # Get enabled only
    response = api_client.get('/api/images?enabled_only=true')
    images = response.json()

    # Our disabled image should not be in the list
    assert filename not in [img['name'] for img in images]


@pytest.mark.integration
def test_req_img_011_toggle_enabled_state(api_client, image_uploader):
    """REQ-IMG-011: POST /api/images/<filename>/toggle SHALL toggle enabled state."""
    filename = image_uploader.upload_test_image()

    # Get initial state
    response = api_client.get('/api/images')
    images = response.json()
    initial_state = next(img for img in images if img['name'] == filename)['enabled']

    # Toggle
    response = api_client.post(f'/api/images/{filename}/toggle')
    assert response.status_code == 200

    # Verify state changed
    response = api_client.get('/api/images')
    images = response.json()
    new_state = next(img for img in images if img['name'] == filename)['enabled']

    assert new_state != initial_state


@pytest.mark.integration
def test_req_img_012_disabled_not_in_kiosk(api_client, image_uploader):
    """REQ-IMG-012: Disabled images SHALL NOT appear in kiosk display."""
    filename = image_uploader.upload_test_image()

    # Disable it
    api_client.post(f'/api/images/{filename}/toggle')

    # Check enabled_only endpoint (used by kiosk)
    response = api_client.get('/api/images?enabled_only=true')
    images = response.json()

    assert filename not in [img['name'] for img in images]


@pytest.mark.integration
def test_req_img_013_toggle_persists(api_client, image_uploader):
    """REQ-IMG-013: Toggle SHALL persist in settings.json."""
    filename = image_uploader.upload_test_image()

    # Toggle to disabled
    api_client.post(f'/api/images/{filename}/toggle')

    # Check settings
    response = api_client.get('/api/settings')
    settings = response.json()

    assert filename in settings.get('enabled_images', {})
    assert settings['enabled_images'][filename] is False


@pytest.mark.integration
def test_req_img_014_delete_removes_file(api_client, image_uploader):
    """REQ-IMG-014: DELETE /api/images/<filename> SHALL remove image file."""
    filename = image_uploader.upload_test_image()

    # Delete
    response = api_client.delete(f'/api/images/{filename}')
    assert response.status_code == 200

    # Verify it's gone
    response = api_client.get('/api/images')
    images = response.json()
    assert filename not in [img['name'] for img in images]

    # Don't cleanup in fixture since we deleted it
    image_uploader.uploaded_files.remove(filename)


@pytest.mark.integration
def test_req_img_009_shuffle_id_consistency(api_client, server_state):
    """REQ-IMG-009: Images SHALL be randomized using shuffle_id seed."""
    # Get images with current shuffle_id
    settings1 = api_client.get('/api/settings').json()
    shuffle_id1 = settings1.get('shuffle_id')

    images1 = api_client.get('/api/images?enabled_only=true').json()
    order1 = [img['name'] for img in images1]

    # Get images again with same shuffle_id
    images2 = api_client.get('/api/images?enabled_only=true').json()
    order2 = [img['name'] for img in images2]

    # Order should be identical with same shuffle_id
    assert order1 == order2


@pytest.mark.integration
def test_req_img_010_shuffle_id_regenerates(api_client, server_state):
    """REQ-IMG-010: Changing theme/atmosphere SHALL regenerate shuffle_id."""
    # Get initial shuffle_id
    settings1 = api_client.get('/api/settings').json()
    shuffle_id1 = settings1.get('shuffle_id')

    # Create and switch to a new theme
    server_state.create_theme('TestTheme')
    api_client.post('/api/themes/active', json={'theme': 'TestTheme'})

    # Get new shuffle_id
    settings2 = api_client.get('/api/settings').json()
    shuffle_id2 = settings2.get('shuffle_id')

    # Should have changed
    assert shuffle_id1 != shuffle_id2
