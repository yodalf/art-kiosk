"""
Integration tests for day scheduling UI features.

Tests the management interface's day scheduling display elements.
"""

import pytest


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_req_day_017_fixed_time_labels(manage_page):
    """
    REQ-DAY-017: Time period labels SHALL display fixed labels for all 12 independent periods.

    Test that all 12 time period labels show the correct fixed time ranges.
    """
    # Trigger label update by calling the function
    manage_page.evaluate("updateTimePeriodLabels()")

    expected_labels = {
        '1': '6 AM - 8 AM',
        '2': '8 AM - 10 AM',
        '3': '10 AM - 12 PM',
        '4': '12 PM - 2 PM',
        '5': '2 PM - 4 PM',
        '6': '4 PM - 6 PM',
        '7': '6 PM - 8 PM',
        '8': '8 PM - 10 PM',
        '9': '10 PM - 12 AM',
        '10': '12 AM - 2 AM',
        '11': '2 AM - 4 AM',
        '12': '4 AM - 6 AM',
    }

    for time_id, expected_range in expected_labels.items():
        label = manage_page.text_content(f'.time-period-label[data-time-id="{time_id}"]')
        assert expected_range in label, (
            f"Time period {time_id} label should contain '{expected_range}', got '{label}'"
        )


@pytest.mark.integration
@pytest.mark.day_scheduling
def test_dynamic_time_labels_update_on_page_load(manage_page):
    """
    Test that time period labels are updated automatically when page loads.

    Verifies that all 12 time period labels exist and have content.
    """
    # Page is already navigated by fixture
    # Verify all 12 time period labels exist and have content
    for i in range(1, 13):
        label = manage_page.text_content(f'.time-period-label[data-time-id="{i}"]')
        assert label is not None, f"Time period {i} label should exist"
        assert f'Time {i}:' in label, f"Time period {i} label should start with 'Time {i}:'"

        # Verify label contains either AM or PM times
        has_am_or_pm = ('AM' in label or 'PM' in label)
        assert has_am_or_pm, f"Time period {i} label should contain AM or PM: {label}"
