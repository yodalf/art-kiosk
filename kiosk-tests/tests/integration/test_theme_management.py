"""
Integration tests for Theme Management (REQ-THEME-001 through REQ-THEME-014).

Tests theme creation, assignment, intervals, and deletion.
"""

import pytest


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_001_create_theme(api_client, server_state):
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
def test_req_theme_002_default_interval(api_client, server_state):
    """REQ-THEME-002: New themes SHALL have default interval of 3600 seconds."""
    server_state.create_theme('DefaultIntervalTest')

    settings = api_client.get('/api/settings').json()
    theme_interval = settings['themes']['DefaultIntervalTest']['interval']

    assert theme_interval == 3600


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_003_unique_names(api_client, server_state):
    """REQ-THEME-003: Theme names SHALL be unique."""
    server_state.create_theme('UniqueTest')

    # Try to create duplicate
    response = api_client.post('/api/themes', json={'name': 'UniqueTest'})

    # Should fail
    assert response.status_code in [400, 409]


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_004_all_images_not_deletable(api_client):
    """REQ-THEME-004: 'All Images' theme SHALL NOT be deletable."""
    response = api_client.delete('/api/themes/All%20Images')

    # Should fail
    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_005_assign_image_to_theme(api_client, image_uploader, server_state):
    """REQ-THEME-005: POST /api/images/<filename>/themes SHALL assign to themes."""
    filename = image_uploader.upload_test_image()
    server_state.create_theme('AssignTest')

    # Assign to theme
    response = api_client.post(f'/api/images/{filename}/themes', json={
        'themes': ['AssignTest']
    })
    assert response.status_code == 200

    # Verify assignment
    settings = api_client.get('/api/settings').json()
    assert 'AssignTest' in settings.get('image_themes', {}).get(filename, [])


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_006_images_many_to_many(api_client, image_uploader, server_state):
    """REQ-THEME-006: Images can belong to multiple themes (many-to-many)."""
    filename = image_uploader.upload_test_image()
    server_state.create_theme('Theme1')
    server_state.create_theme('Theme2')

    # Assign to both themes
    api_client.post(f'/api/images/{filename}/themes', json={
        'themes': ['Theme1', 'Theme2']
    })

    # Verify
    settings = api_client.get('/api/settings').json()
    image_themes = settings.get('image_themes', {}).get(filename, [])

    assert 'Theme1' in image_themes
    assert 'Theme2' in image_themes


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_007_active_theme_selection(api_client, server_state):
    """REQ-THEME-007: POST /api/themes/active SHALL set active theme."""
    server_state.create_theme('ActiveTest')

    response = api_client.post('/api/themes/active', json={'theme': 'ActiveTest'})
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_theme') == 'ActiveTest'


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_008_active_theme_filters(api_client, image_uploader, server_state):
    """REQ-THEME-008: Active theme SHALL filter displayed images."""
    # Ensure day scheduling is disabled for this test (in case previous tests enabled it)
    api_client.post('/api/day/disable')

    # Upload image and assign to specific theme
    filename = image_uploader.upload_test_image()
    server_state.create_theme('FilterTest')
    api_client.post(f'/api/images/{filename}/themes', json={'themes': ['FilterTest']})

    # Activate the theme
    api_client.post('/api/themes/active', json={'theme': 'FilterTest'})

    # Get filtered images
    response = api_client.get('/api/images?enabled_only=true')
    images = response.json()

    # Should only contain images in FilterTest theme
    for img in images:
        settings = api_client.get('/api/settings').json()
        img_themes = settings.get('image_themes', {}).get(img['name'], [])
        # Image should either be in FilterTest or have no themes (All Images)
        assert 'FilterTest' in img_themes or len(img_themes) == 0


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_009_all_images_shows_all(api_client, image_uploader, server_state):
    """REQ-THEME-009: 'All Images' theme SHALL show all enabled images."""
    # Upload some images
    file1 = image_uploader.upload_test_image(color=(255, 0, 0))
    file2 = image_uploader.upload_test_image(color=(0, 255, 0))

    # Activate All Images
    api_client.post('/api/themes/active', json={'theme': 'All Images'})

    # Get images
    response = api_client.get('/api/images?enabled_only=true')
    images = response.json()
    image_names = [img['name'] for img in images]

    # Both should be present
    assert file1 in image_names
    assert file2 in image_names


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_010_update_interval(api_client, server_state):
    """REQ-THEME-010: POST /api/themes/<name>/interval SHALL update interval."""
    server_state.create_theme('IntervalTest')

    # Update interval to 1800 seconds (30 minutes)
    response = api_client.post('/api/themes/IntervalTest/interval', json={
        'interval': 1800
    })
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    assert settings['themes']['IntervalTest']['interval'] == 1800


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_011_delete_theme(api_client, server_state):
    """REQ-THEME-011: DELETE /api/themes/<name> SHALL remove theme."""
    server_state.create_theme('DeleteTest')

    response = api_client.delete('/api/themes/DeleteTest')
    assert response.status_code == 200

    # Verify removed
    settings = api_client.get('/api/settings').json()
    assert 'DeleteTest' not in settings['themes']

    # Don't cleanup in server_state since we deleted it
    server_state.created_themes.remove('DeleteTest')


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_012_delete_removes_assignments(api_client, image_uploader, server_state):
    """REQ-THEME-012: Deleting theme SHALL remove image assignments."""
    filename = image_uploader.upload_test_image()
    server_state.create_theme('RemoveTest')

    # Assign image to theme
    api_client.post(f'/api/images/{filename}/themes', json={'themes': ['RemoveTest']})

    # Delete theme
    api_client.delete('/api/themes/RemoveTest')
    server_state.created_themes.remove('RemoveTest')

    # Verify image assignment removed
    settings = api_client.get('/api/settings').json()
    image_themes = settings.get('image_themes', {}).get(filename, [])
    assert 'RemoveTest' not in image_themes


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_013_delete_switches_to_all_images(api_client, server_state):
    """REQ-THEME-013: Deleting active theme SHALL switch to 'All Images'."""
    server_state.create_theme('ActiveDeleteTest')

    # Make it active
    api_client.post('/api/themes/active', json={'theme': 'ActiveDeleteTest'})

    # Delete it
    api_client.delete('/api/themes/ActiveDeleteTest')
    server_state.created_themes.remove('ActiveDeleteTest')

    # Verify switched to All Images
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_theme') == 'All Images'


@pytest.mark.integration
@pytest.mark.themes
def test_req_theme_014_interval_sync_with_settings(api_client, server_state):
    """REQ-THEME-014: Active theme's interval SHALL sync with global settings.interval."""
    server_state.create_theme('SyncTest', interval=2400)

    # Activate theme
    api_client.post('/api/themes/active', json={'theme': 'SyncTest'})

    # Global interval should update
    settings = api_client.get('/api/settings').json()
    assert settings['interval'] == 2400
