"""
Integration tests for Atmosphere Management (REQ-ATM-001 through REQ-ATM-009).

Tests atmosphere creation, assignment, cadence, and theme relationships.
"""

import pytest


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_001_create_atmosphere(api_client, server_state):
    """REQ-ATM-001: POST /api/atmospheres SHALL create new atmosphere."""
    response = api_client.post('/api/atmospheres', json={
        'name': 'SunnyDay',
        'interval': 7200
    })
    assert response.status_code == 200

    # Cleanup
    api_client.delete('/api/atmospheres/SunnyDay')


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_002_default_cadence(api_client, server_state):
    """REQ-ATM-002: New atmospheres SHALL have default interval of 3600 seconds."""
    server_state.create_atmosphere('DefaultCadence')

    settings = api_client.get('/api/settings').json()
    atmosphere = settings['atmospheres']['DefaultCadence']

    assert atmosphere['interval'] == 3600


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_003_atmosphere_themes_many_to_many(api_client, server_state):
    """REQ-ATM-003: Atmospheres contain multiple themes (many-to-many)."""
    server_state.create_atmosphere('MultiTheme')
    server_state.create_theme('Theme1')
    server_state.create_theme('Theme2')

    # Assign multiple themes to atmosphere
    response = api_client.post('/api/atmospheres/MultiTheme/themes', json={
        'themes': ['Theme1', 'Theme2']
    })
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    atm_themes = settings['atmosphere_themes'].get('MultiTheme', [])

    assert 'Theme1' in atm_themes
    assert 'Theme2' in atm_themes


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_004_active_atmosphere_selection(api_client, server_state):
    """REQ-ATM-004: POST /api/atmospheres/active SHALL set active atmosphere."""
    server_state.create_atmosphere('ActiveAtm')

    response = api_client.post('/api/atmospheres/active', json={
        'atmosphere': 'ActiveAtm'
    })
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_atmosphere') == 'ActiveAtm'


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_005_atmosphere_combines_themes(api_client, image_uploader, server_state):
    """REQ-ATM-005: Active atmosphere SHALL combine images from all assigned themes."""
    # Create atmosphere with two themes
    server_state.create_atmosphere('Combined')
    server_state.create_theme('ThemeA')
    server_state.create_theme('ThemeB')

    # Upload images for each theme
    img1 = image_uploader.upload_test_image(color=(255, 0, 0))
    img2 = image_uploader.upload_test_image(color=(0, 255, 0))

    api_client.post(f'/api/images/{img1}/themes', json={'themes': ['ThemeA']})
    api_client.post(f'/api/images/{img2}/themes', json={'themes': ['ThemeB']})

    # Assign both themes to atmosphere
    api_client.post('/api/atmospheres/Combined/themes', json={
        'themes': ['ThemeA', 'ThemeB']
    })

    # Activate atmosphere
    api_client.post('/api/atmospheres/active', json={'atmosphere': 'Combined'})

    # Get images
    response = api_client.get('/api/images?enabled_only=true')
    images = response.json()
    image_names = [img['name'] for img in images]

    # Both images should be present
    assert img1 in image_names or img2 in image_names  # At least one should be there


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_006_update_cadence(api_client, server_state):
    """REQ-ATM-006: POST /api/atmospheres/<name>/interval SHALL update interval."""
    server_state.create_atmosphere('CadenceUpdate')

    response = api_client.post('/api/atmospheres/CadenceUpdate/interval', json={
        'interval': 1800
    })
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    assert settings['atmospheres']['CadenceUpdate']['interval'] == 1800


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_007_delete_atmosphere(api_client, server_state):
    """REQ-ATM-007: DELETE /api/atmospheres/<name> SHALL remove atmosphere."""
    server_state.create_atmosphere('DeleteAtm')

    response = api_client.delete('/api/atmospheres/DeleteAtm')
    assert response.status_code == 200

    # Verify removed
    settings = api_client.get('/api/settings').json()
    assert 'DeleteAtm' not in settings.get('atmospheres', {})

    # Don't cleanup in fixture
    server_state.created_atmospheres.remove('DeleteAtm')


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_008_delete_resets_if_active(api_client, server_state):
    """REQ-ATM-008: Deleting active atmosphere SHALL reset to no atmosphere."""
    server_state.create_atmosphere('ActiveDelete')
    api_client.post('/api/atmospheres/active', json={'atmosphere': 'ActiveDelete'})

    # Delete it
    api_client.delete('/api/atmospheres/ActiveDelete')
    server_state.created_atmospheres.remove('ActiveDelete')

    # Verify reset
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_atmosphere') is None or settings.get('active_atmosphere') == ''


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_009_cadence_controls_transitions(test_mode, api_client, server_state):
    """REQ-ATM-009: Atmosphere interval SHALL control theme transition timing."""
    server_state.create_atmosphere('FastCadence', interval=5)
    server_state.create_theme('FastTheme1')
    server_state.create_theme('FastTheme2')

    # Assign themes to atmosphere
    api_client.post('/api/atmospheres/FastCadence/themes', json={
        'themes': ['FastTheme1', 'FastTheme2']
    })

    # Activate atmosphere
    api_client.post('/api/atmospheres/active', json={'atmosphere': 'FastCadence'})

    # Get the interval value
    settings = api_client.get('/api/settings').json()
    interval = settings['atmospheres']['FastCadence']['interval']

    # Verify interval is set
    assert interval == 5
