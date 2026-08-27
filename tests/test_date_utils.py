# tests/test_date_utils.py
"""Date range math and time formatting."""

from utils.date_utils import calculate_date_range, format_time, get_days_order, get_short_day_name


class TestCalculateDateRange:
    def test_day_mode_spans_one_day(self):
        start, end = calculate_date_range("DAY", True, "America/Chicago")
        assert (end - start).days == 1
        assert start.hour == 0 and start.minute == 0
        assert start.tzinfo is not None

    def test_week_mode_monday_start(self):
        start, end = calculate_date_range("WEEK", True, "America/Chicago")
        assert start.weekday() == 0
        # 7 day span pins register defect 10, the range must not grow to 8 days
        assert (end - start).days == 7

    def test_week_mode_sunday_start(self):
        start, end = calculate_date_range("WEEK", False, "America/Chicago")
        assert start.weekday() == 6
        assert (end - start).days == 7

    def test_unknown_timezone_falls_back_to_utc(self):
        start, _ = calculate_date_range("DAY", True, "Not/AZone")
        assert start.tzinfo is not None


class TestFormatTime:
    def test_24_hour_leading_zero(self):
        assert format_time(9, 5, use_24_hour=True, add_leading_zero=True) == "09:05"

    def test_12_hour_midnight(self):
        assert format_time(0, 5, use_24_hour=False, add_leading_zero=True) == "12:05 AM"

    def test_12_hour_afternoon(self):
        assert format_time(15, 30, use_24_hour=False, add_leading_zero=False) == "3:30 PM"

    def test_slack_separator(self):
        assert format_time(9, 0, platform="slack", use_24_hour=True) == "09.00"


class TestDayOrder:
    def test_monday_first(self):
        assert get_days_order(True)[0] == "Monday"

    def test_sunday_first(self):
        assert get_days_order(False)[0] == "Sunday"

    def test_short_name(self):
        assert get_short_day_name("Wednesday") == "Wed"
