"""
Unit tests for API endpoints.

These tests verify API responses without browser automation.
They are fast and can run without Playwright.
"""

import pytest


@pytest.mark.unit
def test_api_images_endpoint(api_client):
    """Test GET /api/images returns list of images."""
    response = api_client.get('/api/images')
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Each image should have required fields
    if len(data) > 0:
        image = data[0]
        assert 'name' in image
        assert 'url' in image


@pytest.mark.unit
def test_api_images_enabled_only(api_client):
    """Test GET /api/images?enabled_only=true returns only enabled images."""
    response = api_client.get('/api/images?enabled_only=true')
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


@pytest.mark.unit
def test_api_settings_endpoint(api_client):
    """Test GET /api/settings returns settings."""
    response = api_client.get('/api/settings')
    assert response.status_code == 200

    data = response.json()
    assert 'interval' in data
    assert 'check_interval' in data
    assert 'enabled_images' in data
    assert 'themes' in data


@pytest.mark.unit
def test_api_day_status(api_client):
    """Test GET /api/day/status returns day scheduling status."""
    response = api_client.get('/api/day/status')
    assert response.status_code == 200

    data = response.json()
    assert 'enabled' in data
    assert 'current_time_period' in data
    # API returns 'day_times' (not 'time_periods')
    assert 'day_times' in data


@pytest.mark.unit
@pytest.mark.test_mode
def test_test_mode_enable_disable(api_client):
    """Test enabling and disabling test mode."""
    # Enable test mode
    response = api_client.post('/api/test/enable')
    assert response.status_code == 200

    data = response.json()
    assert data['success'] is True
    assert data['test_mode']['enabled'] is True

    # Check status
    response = api_client.get('/api/test/status')
    assert response.status_code == 200
    assert response.json()['test_mode']['enabled'] is True

    # Disable test mode
    response = api_client.post('/api/test/disable')
    assert response.status_code == 200

    data = response.json()
    assert data['success'] is True
    assert data['test_mode']['enabled'] is False


@pytest.mark.unit
@pytest.mark.test_mode
def test_test_mode_mock_time(api_client):
    """Test setting mock time in test mode."""
    # Enable test mode
    api_client.post('/api/test/enable')

    # Set mock time
    timestamp = 1700040000  # 2023-11-15 07:59:50
    response = api_client.post('/api/test/time', json={'timestamp': timestamp})
    assert response.status_code == 200

    data = response.json()
    assert data['success'] is True
    assert data['mock_time'] == timestamp
    assert 'current_time_period' in data

    # Cleanup
    api_client.post('/api/test/disable')


@pytest.mark.unit
@pytest.mark.test_mode
def test_test_mode_intervals(api_client):
    """Test overriding intervals in test mode."""
    # Enable test mode
    api_client.post('/api/test/enable')

    # Set intervals
    response = api_client.post('/api/test/intervals', json={
        'slideshow_interval': 1000,
        'check_interval': 200
    })
    assert response.status_code == 200

    data = response.json()
    assert data['success'] is True
    assert data['force_interval'] == 1000
    assert data['force_check_interval'] == 200

    # Cleanup
    api_client.post('/api/test/disable')


@pytest.mark.unit
@pytest.mark.test_mode
def test_test_mode_triggers(api_client):
    """Test manual trigger endpoints."""
    # Enable test mode
    api_client.post('/api/test/enable')

    # Trigger hour boundary check
    response = api_client.post('/api/test/trigger-hour-boundary')
    assert response.status_code == 200
    assert response.json()['success'] is True

    # Trigger slideshow advance
    response = api_client.post('/api/test/trigger-slideshow-advance')
    assert response.status_code == 200
    assert response.json()['success'] is True

    # Cleanup
    api_client.post('/api/test/disable')
