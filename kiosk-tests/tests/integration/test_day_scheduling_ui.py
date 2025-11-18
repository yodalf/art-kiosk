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
    # Mock the time to 10:00 AM to force AM cycle
    # Override Date constructor and methods
    manage_page.evaluate("""
        window.OriginalDate = Date;
        window.Date = function(...args) {
            if (args.length === 0) {
                // Create a date at 10:00 AM
                const mockDate = new window.OriginalDate();
                mockDate.setHours(10, 0, 0, 0);
                return mockDate;
            } else {
                return new window.OriginalDate(...args);
            }
        };
        window.Date.now = function() {
            const mockDate = new window.OriginalDate();
            mockDate.setHours(10, 0, 0, 0);
            return mockDate.getTime();
        };
        window.Date.prototype = window.OriginalDate.prototype;
    """)

    # Trigger label update by calling the function
    manage_page.evaluate("updateTimePeriodLabels()")

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


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_req_day_017_dynamic_time_labels_pm_cycle(manage_page):
    """
    REQ-DAY-017: Time period labels SHALL dynamically display PM cycle during evening/night.

    Test that time period labels show PM times when current hour is between 6pm-6am.
    """
    # Mock the time to 22:00 (10:00 PM) to force PM cycle
    # Override Date constructor and methods
    manage_page.evaluate("""
        window.OriginalDate = Date;
        window.Date = function(...args) {
            if (args.length === 0) {
                // Create a date at 10:00 PM (22:00)
                const mockDate = new window.OriginalDate();
                mockDate.setHours(22, 0, 0, 0);
                return mockDate;
            } else {
                return new window.OriginalDate(...args);
            }
        };
        window.Date.now = function() {
            const mockDate = new window.OriginalDate();
            mockDate.setHours(22, 0, 0, 0);
            return mockDate.getTime();
        };
        window.Date.prototype = window.OriginalDate.prototype;
    """)

    # Trigger label update by calling the function
    manage_page.evaluate("updateTimePeriodLabels()")

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
