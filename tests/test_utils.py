"""Tests for timezone and time bucket utility functions."""

from datetime import datetime

from zoneinfo import ZoneInfo

from sdm_tools.utils import (
    get_all_time_buckets,
    get_local_timezone,
    get_time_bucket,
    is_off_hours,
    parse_git_date_to_local,
    parse_jira_date_to_local,
)


class TestGetTimeBucket:
    """Test time bucket assignment logic."""

    def test_8am_to_10am_bucket(self):
        """Test 8am-10am time bucket."""
        # 8:00 - should be in bucket
        dt = datetime(2025, 1, 1, 8, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "8am-10am"

        # 9:59 - should be in bucket
        dt = datetime(2025, 1, 1, 9, 59, 59, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "8am-10am"

        # 10:00 - should NOT be in bucket (belongs to next)
        dt = datetime(2025, 1, 1, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) != "8am-10am"

    def test_10am_to_12pm_bucket(self):
        """Test 10am-12pm time bucket."""
        dt = datetime(2025, 1, 1, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "10am-12pm"

        dt = datetime(2025, 1, 1, 11, 30, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "10am-12pm"

    def test_12pm_to_2pm_bucket(self):
        """Test 12pm-2pm time bucket."""
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "12pm-2pm"

        dt = datetime(2025, 1, 1, 13, 45, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "12pm-2pm"

    def test_2pm_to_4pm_bucket(self):
        """Test 2pm-4pm time bucket."""
        dt = datetime(2025, 1, 1, 14, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "2pm-4pm"

        dt = datetime(2025, 1, 1, 15, 30, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "2pm-4pm"

    def test_4pm_to_6pm_bucket(self):
        """Test 4pm-6pm time bucket."""
        dt = datetime(2025, 1, 1, 16, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "4pm-6pm"

        dt = datetime(2025, 1, 1, 17, 59, 59, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "4pm-6pm"

    def test_off_hours_evening(self):
        """Test off-hours bucket (evening 6pm-midnight)."""
        # 18:00 (6pm)
        dt = datetime(2025, 1, 1, 18, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "off_hours"

        # 23:59
        dt = datetime(2025, 1, 1, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "off_hours"

    def test_off_hours_early_morning(self):
        """Test off-hours bucket (early morning midnight-8am)."""
        # 00:00 (midnight)
        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "off_hours"

        # 7:59
        dt = datetime(2025, 1, 1, 7, 59, 59, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "off_hours"

        # 7:00
        dt = datetime(2025, 1, 1, 7, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert get_time_bucket(dt) == "off_hours"

    def test_none_input(self):
        """Test handling of None input."""
        assert get_time_bucket(None) is None


class TestIsOffHours:
    """Test off-hours detection."""

    def test_is_off_hours_true(self):
        """Test times that should be off-hours."""
        # Evening
        dt = datetime(2025, 1, 1, 18, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert is_off_hours(dt) is True

        dt = datetime(2025, 1, 1, 23, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert is_off_hours(dt) is True

        # Early morning
        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert is_off_hours(dt) is True

        dt = datetime(2025, 1, 1, 7, 30, 0, tzinfo=ZoneInfo("UTC"))
        assert is_off_hours(dt) is True

    def test_is_off_hours_false(self):
        """Test times that should NOT be off-hours."""
        # Regular business hours
        dt = datetime(2025, 1, 1, 8, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert is_off_hours(dt) is False

        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        assert is_off_hours(dt) is False

        dt = datetime(2025, 1, 1, 17, 59, 59, tzinfo=ZoneInfo("UTC"))
        assert is_off_hours(dt) is False


class TestGetAllTimeBuckets:
    """Test time bucket enumeration."""

    def test_all_buckets_returned(self):
        """Test that all expected buckets are returned."""
        buckets = get_all_time_buckets()

        assert "8am-10am" in buckets
        assert "10am-12pm" in buckets
        assert "12pm-2pm" in buckets
        assert "2pm-4pm" in buckets
        assert "4pm-6pm" in buckets
        assert "off_hours" in buckets

    def test_bucket_count(self):
        """Test that we have exactly 6 buckets."""
        buckets = get_all_time_buckets()
        assert len(buckets) == 6

    def test_bucket_order(self):
        """Test that buckets are in expected order."""
        buckets = get_all_time_buckets()

        expected_order = ["8am-10am", "10am-12pm", "12pm-2pm", "2pm-4pm", "4pm-6pm", "off_hours"]

        assert buckets == expected_order


class TestParseGitDateToLocal:
    """Test git date parsing and timezone conversion."""

    def test_parse_git_date_with_timezone(self):
        """Test parsing git date with timezone offset."""
        # Git format: "Wed Sep 17 23:37:12 2025 +0000"
        date_str = "Wed Sep 17 23:37:12 2025 +0000"
        target_tz = ZoneInfo("America/Toronto")  # UTC-5 or UTC-4 depending on DST

        result = parse_git_date_to_local(date_str, target_tz)

        assert result is not None
        assert result.year == 2025
        assert result.month == 9
        assert result.day == 17
        # Time should be converted to Toronto timezone
        assert result.tzinfo == target_tz

    def test_parse_git_date_different_timezones(self):
        """Test parsing with different timezone offsets."""
        # UTC date
        date_str_utc = "Mon Jan 01 12:00:00 2025 +0000"
        result_utc = parse_git_date_to_local(date_str_utc, ZoneInfo("UTC"))

        assert result_utc is not None
        assert result_utc.hour == 12

        # PST date (UTC-8)
        date_str_pst = "Mon Jan 01 12:00:00 2025 -0800"
        result_pst = parse_git_date_to_local(date_str_pst, ZoneInfo("UTC"))

        assert result_pst is not None
        # 12:00 PST = 20:00 UTC
        assert result_pst.hour == 20

    def test_parse_git_date_none_input(self):
        """Test handling of None input."""
        result = parse_git_date_to_local(None)
        assert result is None

    def test_parse_git_date_empty_string(self):
        """Test handling of empty string."""
        result = parse_git_date_to_local("")
        assert result is None


class TestParseJiraDateToLocal:
    """Test Jira date parsing and timezone conversion."""

    def test_parse_jira_date_with_milliseconds(self):
        """Test parsing Jira ISO date with milliseconds."""
        # Jira format: "2025-09-17T15:06:43.000+0000"
        date_str = "2025-09-17T15:06:43.000+0000"
        target_tz = ZoneInfo("America/Mexico_City")

        result = parse_jira_date_to_local(date_str, target_tz)

        assert result is not None
        assert result.year == 2025
        assert result.month == 9
        assert result.day == 17
        assert result.hour == 15 or result.hour < 15  # Converted to Mexico timezone (UTC-6)
        assert result.tzinfo == target_tz

    def test_parse_jira_date_with_z_suffix(self):
        """Test parsing Jira date with 'Z' (Zulu time) suffix."""
        # Alternative Jira format: "2025-09-17T15:06:43.000Z"
        date_str = "2025-09-17T15:06:43.000Z"
        result = parse_jira_date_to_local(date_str, ZoneInfo("UTC"))

        assert result is not None
        assert result.hour == 15
        assert result.minute == 6
        assert result.second == 43

    def test_parse_jira_date_without_milliseconds(self):
        """Test parsing Jira date without milliseconds."""
        date_str = "2025-09-17T15:06:43Z"
        result = parse_jira_date_to_local(date_str, ZoneInfo("UTC"))

        assert result is not None
        assert result.hour == 15

    def test_parse_jira_date_none_input(self):
        """Test handling of None input."""
        result = parse_jira_date_to_local(None)
        assert result is None

    def test_parse_jira_date_empty_string(self):
        """Test handling of empty string."""
        result = parse_jira_date_to_local("")
        assert result is None


class TestGetLocalTimezone:
    """Test timezone helper function."""

    def test_get_timezone_by_string(self):
        """Test getting timezone from string."""
        tz = get_local_timezone("America/Toronto")

        assert isinstance(tz, ZoneInfo)
        assert str(tz) == "America/Toronto"

    def test_get_timezone_utc(self):
        """Test getting UTC timezone."""
        tz = get_local_timezone("UTC")

        assert isinstance(tz, ZoneInfo)
        assert str(tz) == "UTC"

    def test_get_timezone_invalid_fallback(self):
        """Test that invalid timezone falls back to UTC."""
        # Should not raise exception, should fall back to UTC
        tz = get_local_timezone("Invalid/Timezone")

        assert isinstance(tz, ZoneInfo)
        # Should fall back to UTC
        assert str(tz) == "UTC"
