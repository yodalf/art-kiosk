"""
Integration tests for Theme Management (REQ-THEME-001 through REQ-THEME-014).

Tests theme creation, assignment, intervals, and deletion.
Uses isolated_test_data for pre-created images and themes.
"""

import pytest


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_001_create_theme(api_client):
    """REQ-THEME-001: POST /api/themes SHALL create new theme."""
    response = api_client.post('/api/themes', json={'name': 'NatureTest'})
    assert response.status_code == 200

    data = response.json()
    assert data.get('success') is True

    # Verify in settings
    settings = api_client.get('/api/settings').json()
    assert 'NatureTest' in settings['themes']

    # Cleanup
    api_client.delete('/api/themes/NatureTest')


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_002_default_interval(api_client):
    """REQ-THEME-002: New themes SHALL have default interval of 3600 seconds."""
    response = api_client.post('/api/themes', json={'name': 'DefaultIntervalTest'})
    assert response.status_code == 200

    settings = api_client.get('/api/settings').json()
    theme_interval = settings['themes']['DefaultIntervalTest']['interval']

    assert theme_interval == 3600

    # Cleanup
    api_client.delete('/api/themes/DefaultIntervalTest')


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_003_unique_names(api_client):
    """REQ-THEME-003: Theme names SHALL be unique."""
    # Create first theme
    api_client.post('/api/themes', json={'name': 'UniqueTest'})

    # Try to create duplicate
    response = api_client.post('/api/themes', json={'name': 'UniqueTest'})

    # Should fail
    assert response.status_code in [400, 409]

    # Cleanup
    api_client.delete('/api/themes/UniqueTest')


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_004_all_images_not_deletable(api_client):
    """REQ-THEME-004: 'All Images' theme SHALL NOT be deletable."""
    response = api_client.delete('/api/themes/All%20Images')

    # Should fail
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_005_assign_image_to_theme(api_client, isolated_test_data):
    """REQ-THEME-005: POST /api/images/<filename>/themes SHALL assign to themes."""
    # Use an image from isolated data
    image_id = isolated_test_data['images'][19]  # Use the last image (not in any theme initially)

    # Create a test theme
    api_client.post('/api/themes', json={'name': 'AssignTest'})

    # Assign to theme
    response = api_client.post(f'/api/images/{image_id}/themes', json={
        'themes': ['AssignTest']
    })
    assert response.status_code == 200

    # Verify assignment
    settings = api_client.get('/api/settings').json()
    assert 'AssignTest' in settings.get('image_themes', {}).get(image_id, [])

    # Cleanup
    api_client.delete('/api/themes/AssignTest')


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_006_images_many_to_many(api_client, isolated_test_data):
    """REQ-THEME-006: Images can belong to multiple themes (many-to-many)."""
    # The first 10 images belong to both TestTheme10Images and TestTheme15Images
    image_id = isolated_test_data['images'][0]

    settings = api_client.get('/api/settings').json()
    image_themes = settings.get('image_themes', {}).get(image_id, [])

    # Should belong to multiple themes
    assert 'TestTheme10Images' in image_themes
    assert 'TestTheme15Images' in image_themes
    assert 'TestTheme19ImagesVideoEnd' in image_themes


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_007_active_theme_selection(api_client, isolated_test_data):
    """REQ-THEME-007: POST /api/themes/active SHALL set active theme."""
    theme_name = 'TestTheme10Images'

    response = api_client.post('/api/themes/active', json={'theme': theme_name})
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_theme') == theme_name


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_008_active_theme_filters(api_client, isolated_test_data):
    """REQ-THEME-008: Active theme SHALL filter displayed images."""
    # Ensure day scheduling is disabled
    api_client.post('/api/day/disable')

    # Activate TestTheme10Images
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})

    # Get filtered images
    response = api_client.get('/api/images?enabled_only=true')
    images = response.json()

    # Should only show 10 images
    assert len(images) == 10, f"Expected 10 images, got {len(images)}"

    # All images should be from the theme
    expected_images = isolated_test_data['themes']['TestTheme10Images']['images']
    for img in images:
        assert img['name'] in expected_images


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_009_all_images_shows_all(api_client, isolated_test_data):
    """REQ-THEME-009: 'All Images' theme SHALL show all enabled images."""
    # Activate All Images
    api_client.post('/api/themes/active', json={'theme': 'All Images'})

    # Get images
    response = api_client.get('/api/images?enabled_only=true')
    images = response.json()
    image_names = [img['name'] for img in images]

    # All test images should be present
    for img_id in isolated_test_data['images']:
        assert img_id in image_names, f"Image {img_id} should be in All Images"


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_010_update_interval(api_client, isolated_test_data):
    """REQ-THEME-010: POST /api/themes/<name>/interval SHALL update interval."""
    theme_name = 'TestTheme10Images'

    # Get original interval
    settings = api_client.get('/api/settings').json()
    original_interval = settings['themes'][theme_name]['interval']

    # Update interval to 1800 seconds (30 minutes)
    response = api_client.post(f'/api/themes/{theme_name}/interval', json={
        'interval': 1800
    })
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    assert settings['themes'][theme_name]['interval'] == 1800

    # Restore original interval
    api_client.post(f'/api/themes/{theme_name}/interval', json={'interval': original_interval})


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_011_delete_theme(api_client):
    """REQ-THEME-011: DELETE /api/themes/<name> SHALL remove theme."""
    # Create theme for deletion
    api_client.post('/api/themes', json={'name': 'DeleteTest'})

    response = api_client.delete('/api/themes/DeleteTest')
    assert response.status_code == 200

    # Verify removed
    settings = api_client.get('/api/settings').json()
    assert 'DeleteTest' not in settings['themes']


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_012_delete_removes_assignments(api_client, isolated_test_data):
    """REQ-THEME-012: Deleting theme SHALL remove image assignments."""
    # Use an image from isolated data
    image_id = isolated_test_data['images'][19]

    # Create theme and assign image
    api_client.post('/api/themes', json={'name': 'RemoveTest'})
    api_client.post(f'/api/images/{image_id}/themes', json={'themes': ['RemoveTest']})

    # Delete theme
    api_client.delete('/api/themes/RemoveTest')

    # Verify image assignment removed
    settings = api_client.get('/api/settings').json()
    image_themes = settings.get('image_themes', {}).get(image_id, [])
    assert 'RemoveTest' not in image_themes


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_013_delete_switches_to_all_images(api_client):
    """REQ-THEME-013: Deleting active theme SHALL switch to 'All Images'."""
    # Create and activate theme
    api_client.post('/api/themes', json={'name': 'ActiveDeleteTest'})
    api_client.post('/api/themes/active', json={'theme': 'ActiveDeleteTest'})

    # Delete it
    api_client.delete('/api/themes/ActiveDeleteTest')

    # Verify switched to All Images
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_theme') == 'All Images'


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_014_interval_sync_with_settings(api_client):
    """REQ-THEME-014: Active theme's interval SHALL sync with global settings.interval."""
    # Create theme with specific interval
    api_client.post('/api/themes', json={'name': 'SyncTest'})
    api_client.post('/api/themes/SyncTest/interval', json={'interval': 2400})

    # Activate theme
    api_client.post('/api/themes/active', json={'theme': 'SyncTest'})

    # Global interval should update
    settings = api_client.get('/api/settings').json()
    assert settings['interval'] == 2400

    # Cleanup
    api_client.delete('/api/themes/SyncTest')
