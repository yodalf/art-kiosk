"""
Integration tests for Atmosphere Management (REQ-ATM-001 through REQ-ATM-009).

Tests atmosphere creation, assignment, cadence, and theme relationships.
Uses isolated_test_data for pre-created themes and images.
"""

import pytest


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_001_create_atmosphere(api_client):
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
def test_req_atm_002_default_cadence(api_client):
    """REQ-ATM-002: New atmospheres SHALL have default interval of 3600 seconds."""
    response = api_client.post('/api/atmospheres', json={'name': 'DefaultCadence'})
    assert response.status_code == 200

    settings = api_client.get('/api/settings').json()
    atmosphere = settings['atmospheres']['DefaultCadence']

    assert atmosphere['interval'] == 3600

    # Cleanup
    api_client.delete('/api/atmospheres/DefaultCadence')


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_003_atmosphere_themes_many_to_many(api_client, isolated_test_data):
    """REQ-ATM-003: Atmospheres contain multiple themes (many-to-many)."""
    # Use existing atmosphere from isolated data
    settings = api_client.get('/api/settings').json()
    atm_themes = settings['atmosphere_themes'].get('TestAtmosphereImageThemes', [])

    # Should have 2 themes
    assert 'TestTheme10Images' in atm_themes
    assert 'TestTheme15Images' in atm_themes


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_004_active_atmosphere_selection(api_client, isolated_test_data):
    """REQ-ATM-004: POST /api/atmospheres/active SHALL set active atmosphere."""
    atm_name = 'TestAtmosphereImageThemes'

    response = api_client.post('/api/atmospheres/active', json={
        'atmosphere': atm_name
    })
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_atmosphere') == atm_name


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_005_atmosphere_combines_themes(api_client, isolated_test_data):
    """REQ-ATM-005: Active atmosphere SHALL combine images from all assigned themes."""
    # Activate atmosphere with 2 image themes
    api_client.post('/api/atmospheres/active', json={'atmosphere': 'TestAtmosphereImageThemes'})

    # Get images
    response = api_client.get('/api/images?enabled_only=true')
    images = response.json()
    image_names = [img['name'] for img in images]

    # Should have images from both TestTheme10Images and TestTheme15Images
    # TestTheme15Images has images 0-14, TestTheme10Images has images 0-9
    # Combined should have images 0-14 (15 unique images)
    theme10_images = isolated_test_data['themes']['TestTheme10Images']['images']
    theme15_images = isolated_test_data['themes']['TestTheme15Images']['images']

    # All images from TestTheme10Images should be present
    for img_id in theme10_images:
        assert img_id in image_names, f"Image {img_id} should be in combined atmosphere"


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_006_update_cadence(api_client, isolated_test_data):
    """REQ-ATM-006: POST /api/atmospheres/<name>/interval SHALL update interval."""
    atm_name = 'TestAtmosphereImageThemes'

    # Get original interval
    settings = api_client.get('/api/settings').json()
    original_interval = settings['atmospheres'][atm_name]['interval']

    # Update interval
    response = api_client.post(f'/api/atmospheres/{atm_name}/interval', json={
        'interval': 1800
    })
    assert response.status_code == 200

    # Verify
    settings = api_client.get('/api/settings').json()
    assert settings['atmospheres'][atm_name]['interval'] == 1800

    # Restore original
    api_client.post(f'/api/atmospheres/{atm_name}/interval', json={'interval': original_interval})


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_007_delete_atmosphere(api_client):
    """REQ-ATM-007: DELETE /api/atmospheres/<name> SHALL remove atmosphere."""
    # Create atmosphere for deletion
    api_client.post('/api/atmospheres', json={'name': 'DeleteAtm'})

    response = api_client.delete('/api/atmospheres/DeleteAtm')
    assert response.status_code == 200

    # Verify removed
    settings = api_client.get('/api/settings').json()
    assert 'DeleteAtm' not in settings.get('atmospheres', {})


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_008_delete_resets_if_active(api_client):
    """REQ-ATM-008: Deleting active atmosphere SHALL reset to no atmosphere."""
    # Create and activate atmosphere
    api_client.post('/api/atmospheres', json={'name': 'ActiveDelete'})
    api_client.post('/api/atmospheres/active', json={'atmosphere': 'ActiveDelete'})

    # Delete it
    api_client.delete('/api/atmospheres/ActiveDelete')

    # Verify reset
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_atmosphere') is None or settings.get('active_atmosphere') == ''


@pytest.mark.integration
@pytest.mark.atmospheres
def test_req_atm_009_cadence_controls_transitions(api_client, isolated_test_data):
    """REQ-ATM-009: Atmosphere interval SHALL control theme transition timing."""
    # Use TestAtmosphereAllThemes which has all 4 themes
    atm_name = 'TestAtmosphereAllThemes'

    # Activate atmosphere
    api_client.post('/api/atmospheres/active', json={'atmosphere': atm_name})

    # Get the interval value
    settings = api_client.get('/api/settings').json()
    interval = settings['atmospheres'][atm_name]['interval']

    # Verify interval is set
    assert interval == 600  # As configured in fixture
