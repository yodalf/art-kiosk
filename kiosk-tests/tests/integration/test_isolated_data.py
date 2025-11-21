"""
Test to verify the isolated_test_data fixture works correctly.

This test validates that the synthetic test data is properly created
and cleaned up.
"""

import pytest


@pytest.mark.integration
def test_isolated_data_setup(isolated_test_data):
    """Verify that isolated test data is properly created."""
    # Check images
    assert len(isolated_test_data['images']) == 20, \
        f"Expected 20 images, got {len(isolated_test_data['images'])}"

    # Check videos
    assert len(isolated_test_data['videos']) == 3, \
        f"Expected 3 videos, got {len(isolated_test_data['videos'])}"

    # Check themes
    assert len(isolated_test_data['themes']) == 4, \
        f"Expected 4 themes, got {len(isolated_test_data['themes'])}"

    # Verify theme contents
    assert 'TestTheme10Images' in isolated_test_data['themes']
    assert len(isolated_test_data['themes']['TestTheme10Images']['images']) == 10

    assert 'TestTheme15Images' in isolated_test_data['themes']
    assert len(isolated_test_data['themes']['TestTheme15Images']['images']) == 15

    assert 'TestThemeVideosOnly' in isolated_test_data['themes']
    assert len(isolated_test_data['themes']['TestThemeVideosOnly']['videos']) == 3

    assert 'TestTheme19ImagesVideoEnd' in isolated_test_data['themes']
    assert len(isolated_test_data['themes']['TestTheme19ImagesVideoEnd']['images']) == 19
    assert len(isolated_test_data['themes']['TestTheme19ImagesVideoEnd']['videos']) == 1

    # Check atmospheres
    assert len(isolated_test_data['atmospheres']) == 2, \
        f"Expected 2 atmospheres, got {len(isolated_test_data['atmospheres'])}"

    assert 'TestAtmosphereImageThemes' in isolated_test_data['atmospheres']
    assert 'TestAtmosphereAllThemes' in isolated_test_data['atmospheres']

    print("\n✓ All isolated test data verified successfully!")


@pytest.mark.integration
def test_isolated_data_theme_activation(isolated_test_data, api_client):
    """Test that we can activate themes from isolated data."""
    # Activate one of our test themes
    theme_name = 'TestTheme10Images'
    response = api_client.post('/api/themes/active', json={'theme': theme_name})
    assert response.status_code == 200

    # Verify it's active
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_theme') == theme_name

    # Get images and verify count
    response = api_client.get('/api/images', params={'enabled_only': 'true'})
    images = response.json()

    # Should only show images from TestTheme10Images
    assert len(images) == 10, f"Expected 10 images, got {len(images)}"

    print(f"\n✓ Theme '{theme_name}' activated with {len(images)} images")


@pytest.mark.integration
def test_isolated_data_atmosphere_activation(isolated_test_data, api_client):
    """Test that we can activate atmospheres from isolated data."""
    # Activate one of our test atmospheres
    atm_name = 'TestAtmosphereImageThemes'
    response = api_client.post('/api/atmospheres/active', json={'atmosphere': atm_name})
    assert response.status_code == 200

    # Verify it's active
    settings = api_client.get('/api/settings').json()
    assert settings.get('active_atmosphere') == atm_name

    print(f"\n✓ Atmosphere '{atm_name}' activated successfully")
