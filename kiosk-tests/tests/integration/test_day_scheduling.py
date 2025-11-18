"""
Integration tests for day scheduling feature.

Tests the interaction between test mode, day scheduling, and hour boundaries.
"""

import pytest
import time


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_hour_boundary_detection(test_mode, api_client):
    """Test that hour boundaries are detected correctly with mock time."""
    # Enable day scheduling
    api_client.post('/api/day/enable')

    # Set mock time to 7:59:50 (just before 8 AM)
    test_mode.set_time(1700040000)
    time.sleep(0.5)

    # Get current time period
    status = test_mode.get_status()
    initial_period = status['current_time_period']

    # Advance time across hour boundary to 8:00:10
    test_mode.set_time(1700043610)
    time.sleep(0.5)

    # Get new time period
    status = test_mode.get_status()
    new_period = status['current_time_period']

    # Time period should have changed
    assert new_period != initial_period, "Time period should change when hour boundary crossed"

    # Cleanup
    api_client.post('/api/day/disable')


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_time_period_calculation(api_client):
    """Test that time periods are calculated correctly for different hours."""
    # Test various hours and their expected time periods
    # Time periods: 1=7-8, 2=8-9, 3=9-10, 4=10-11, 5=11-12, 6=12-1
    # Then mirrors: 7=1-2, 8=2-3, etc.

    test_cases = [
        (1700038800, 1),  # 07:00:00 -> Period 1
        (1700042400, 2),  # 08:00:00 -> Period 2
        (1700046000, 3),  # 09:00:00 -> Period 3
        (1700049600, 4),  # 10:00:00 -> Period 4
        (1700053200, 5),  # 11:00:00 -> Period 5
        (1700056800, 6),  # 12:00:00 -> Period 6
        (1700060400, 1),  # 13:00:00 -> Period 1 (mirrors 7-8)
        (1700064000, 2),  # 14:00:00 -> Period 2 (mirrors 8-9)
    ]

    # Enable test mode
    api_client.post('/api/test/enable')

    for timestamp, expected_period in test_cases:
        # Set mock time
        api_client.post('/api/test/time', json={'timestamp': timestamp})
        time.sleep(0.1)

        # Get status
        response = api_client.get('/api/test/status')
        status = response.json()

        actual_period = status['current_time_period']
        assert actual_period == expected_period, \
            f"Timestamp {timestamp} should be period {expected_period}, got {actual_period}"

    # Cleanup
    api_client.post('/api/test/disable')


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_day_scheduling_enable_disable(api_client, server_state):
    """Test enabling and disabling day scheduling."""
    # Initially disabled
    status = api_client.get('/api/day/status').json()
    initial_enabled = status['enabled']

    # Enable day scheduling
    server_state.enable_day_scheduling()

    status = api_client.get('/api/day/status').json()
    assert status['enabled'] is True

    # Disable day scheduling
    server_state.disable_day_scheduling()

    status = api_client.get('/api/day/status').json()
    assert status['enabled'] is False


@pytest.mark.integration
@pytest.mark.day_scheduling
@pytest.mark.slow
def test_rapid_hour_transitions(test_mode, api_client):
    """Test multiple rapid hour boundary transitions."""
    # Enable day scheduling
    api_client.post('/api/day/enable')

    # Set very fast check interval
    test_mode.set_intervals(check=100)

    # Simulate multiple hour transitions
    hours = [
        1700038800,  # 07:00
        1700042400,  # 08:00
        1700046000,  # 09:00
        1700049600,  # 10:00
    ]

    for timestamp in hours:
        test_mode.set_time(timestamp)
        time.sleep(0.2)

        status = test_mode.get_status()
        assert status['test_mode']['mock_time'] == timestamp

    # Cleanup
    api_client.post('/api/day/disable')


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_time_period_atmosphere_assignment(api_client, server_state):
    """Test assigning atmospheres to time periods."""
    # Enable day scheduling
    server_state.enable_day_scheduling()

    # Create test atmospheres
    server_state.create_atmosphere('Morning')
    server_state.create_atmosphere('Evening')

    # Assign atmosphere to time period 1
    response = api_client.post('/api/day/time-periods/1', json={
        'atmospheres': ['Morning']
    })
    assert response.status_code == 200

    # Verify assignment
    status = api_client.get('/api/day/status').json()
    period_1 = status['time_periods']['1']
    assert 'Morning' in period_1['atmospheres']

    # Cleanup
    server_state.disable_day_scheduling()
