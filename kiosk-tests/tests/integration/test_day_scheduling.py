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

    # Set mock time to 7:00 AM local time (Period 1: 6-8 AM)
    # Timestamp converts to local time, so we need to account for timezone
    test_mode.set_time(1700049600)
    time.sleep(0.5)

    # Get current time period
    status = test_mode.get_status()
    initial_period = status['current_time_period']
    assert initial_period == '1', f"Expected period 1 at 7:00 AM, got {initial_period}"

    # Advance time across period boundary to 8:30 AM local time (Period 2: 8-10 AM)
    test_mode.set_time(1700055000)
    time.sleep(0.5)

    # Get new time period
    status = test_mode.get_status()
    new_period = status['current_time_period']

    # Time period should have changed from 1 to 2
    assert new_period == '2', f"Expected period 2 at 8:30 AM, got {new_period}"
    assert new_period != initial_period, "Time period should change when period boundary crossed"

    # Cleanup
    api_client.post('/api/day/disable')


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_time_period_calculation(api_client):
    """Test that time periods are calculated correctly for different hours."""
    # Test various hours and their expected time periods (2-hour blocks)
    # Periods 1-6: 6 AM - 6 PM (AM hours)
    # Periods 7-12: 6 PM - 6 AM (PM hours, mirroring AM)
    # Period 1: 6-8 AM, Period 7: 6-8 PM (mirror)
    # Period 2: 8-10 AM, Period 8: 8-10 PM (mirror)
    # Period 3: 10-12 PM, Period 9: 10 PM-12 AM (mirror)
    # Period 4: 12-2 PM, Period 10: 12-2 AM (mirror)
    # Period 5: 2-4 PM, Period 11: 2-4 AM (mirror)
    # Period 6: 4-6 PM, Period 12: 4-6 AM (mirror)

    test_cases = [
        (1700046000, '1'),  # Period 1: 6-8 AM
        (1700051400, '1'),  # Period 1: 7:30 AM
        (1700053200, '2'),  # Period 2: 8-10 AM
        (1700058600, '2'),  # Period 2: 9:30 AM
        (1700060400, '3'),  # Period 3: 10 AM-12 PM
        (1700065800, '3'),  # Period 3: 11:30 AM
        (1700067600, '4'),  # Period 4: 12-2 PM
        (1700073000, '4'),  # Period 4: 1:30 PM
        (1700074800, '5'),  # Period 5: 2-4 PM
        (1700080200, '5'),  # Period 5: 3:30 PM
        (1700082000, '6'),  # Period 6: 4-6 PM
        (1700087400, '6'),  # Period 6: 5:30 PM
        (1700089200, '7'),  # Period 7: 6-8 PM (mirrors Period 1)
        (1700096400, '8'),  # Period 8: 8-10 PM (mirrors Period 2)
        (1700103600, '9'),  # Period 9: 10 PM-12 AM (mirrors Period 3)
        (1700024400, '10'),  # Period 10: 12-2 AM (mirrors Period 4)
        (1700031600, '11'),  # Period 11: 2-4 AM (mirrors Period 5)
        (1700038800, '12'),  # Period 12: 4-6 AM (mirrors Period 6)
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
def test_time_period_atmosphere_assignment(api_client, server_state, isolated_test_data):
    """Test assigning atmospheres to time periods."""
    # Enable day scheduling
    server_state.enable_day_scheduling()

    # Use atmospheres from isolated test data
    morning_atmosphere = 'TestAtmosphereImageThemes'
    evening_atmosphere = 'TestAtmosphereAllThemes'

    # Assign atmosphere to time period 1
    response = api_client.post('/api/day/time-periods/1', json={
        'atmospheres': [morning_atmosphere]
    })
    assert response.status_code == 200

    # Verify assignment
    status = api_client.get('/api/day/status').json()
    period_1 = status['time_periods']['1']
    assert morning_atmosphere in period_1['atmospheres']

    # Cleanup
    server_state.disable_day_scheduling()
