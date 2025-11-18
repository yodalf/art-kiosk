"""
Integration tests for day scheduling UI features.

Tests the management interface's day scheduling display elements.
"""

import pytest


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_req_day_017_dynamic_time_labels_am_cycle(manage_page):
    """
    REQ-DAY-017: Time period labels SHALL dynamically display AM cycle during daytime.

    Test that time period labels show AM times when current hour is between 6am-6pm.
    """
    # Page is already navigated by fixture
    # Get current hour from JavaScript
    current_hour = manage_page.evaluate("new Date().getHours()")

    # Determine expected cycle based on current hour
    is_pm_cycle = current_hour >= 18 or current_hour < 6

    if not is_pm_cycle:
        # AM cycle - verify labels show AM times
        label1 = manage_page.text_content('.time-period-label[data-time-id="1"]')
        label2 = manage_page.text_content('.time-period-label[data-time-id="2"]')
        label3 = manage_page.text_content('.time-period-label[data-time-id="3"]')
        label4 = manage_page.text_content('.time-period-label[data-time-id="4"]')
        label5 = manage_page.text_content('.time-period-label[data-time-id="5"]')
        label6 = manage_page.text_content('.time-period-label[data-time-id="6"]')

        assert '6 AM - 8 AM' in label1
        assert '8 AM - 10 AM' in label2
        assert '10 AM - 12 PM' in label3
        assert '12 PM - 2 PM' in label4
        assert '2 PM - 4 PM' in label5
        assert '4 PM - 6 PM' in label6
    else:
        # PM cycle - skip this test and run the PM cycle test instead
        pytest.skip("Current hour is in PM cycle, run test_req_day_017_dynamic_time_labels_pm_cycle instead")


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_req_day_017_dynamic_time_labels_pm_cycle(manage_page):
    """
    REQ-DAY-017: Time period labels SHALL dynamically display PM cycle during evening/night.

    Test that time period labels show PM times when current hour is between 6pm-6am.
    """
    # Page is already navigated by fixture
    # Get current hour from JavaScript
    current_hour = manage_page.evaluate("new Date().getHours()")

    # Determine expected cycle based on current hour
    is_pm_cycle = current_hour >= 18 or current_hour < 6

    if is_pm_cycle:
        # PM cycle - verify labels show PM times
        label1 = manage_page.text_content('.time-period-label[data-time-id="1"]')
        label2 = manage_page.text_content('.time-period-label[data-time-id="2"]')
        label3 = manage_page.text_content('.time-period-label[data-time-id="3"]')
        label4 = manage_page.text_content('.time-period-label[data-time-id="4"]')
        label5 = manage_page.text_content('.time-period-label[data-time-id="5"]')
        label6 = manage_page.text_content('.time-period-label[data-time-id="6"]')

        assert '6 PM - 8 PM' in label1
        assert '8 PM - 10 PM' in label2
        assert '10 PM - 12 AM' in label3
        assert '12 AM - 2 AM' in label4
        assert '2 AM - 4 AM' in label5
        assert '4 AM - 6 AM' in label6
    else:
        # AM cycle - skip this test and run the AM cycle test instead
        pytest.skip("Current hour is in AM cycle, run test_req_day_017_dynamic_time_labels_am_cycle instead")


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_dynamic_time_labels_update_on_page_load(manage_page):
    """
    Test that time period labels are updated automatically when page loads.

    Verifies that the updateTimePeriodLabels() function is called during page initialization.
    """
    # Page is already navigated by fixture
    # Verify all 6 time period labels exist and have content
    for i in range(1, 7):
        label = manage_page.text_content(f'.time-period-label[data-time-id="{i}"]')
        assert label is not None, f"Time period {i} label should exist"
        assert f'Time {i}:' in label, f"Time period {i} label should start with 'Time {i}:'"

        # Verify label contains either AM or PM times
        has_am_or_pm = ('AM' in label or 'PM' in label)
        assert has_am_or_pm, f"Time period {i} label should contain AM or PM: {label}"
