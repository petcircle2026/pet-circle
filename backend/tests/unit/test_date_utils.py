"""
Unit tests for date_utils (UTC date handling).

Tests: date parsing, arithmetic, ISO conversion, timezone safety.
All tests use naive UTC dates — no timezone objects.
"""

import pytest
from datetime import date, datetime, timedelta, timezone

from app.domain.shared.date_utils import (
    today_utc,
    now_utc,
    parse_iso_date,
    to_iso_date,
    days_between,
    add_days,
    subtract_days,
)


class TestTodayUTC:
    """Tests for today_utc() function."""

    def test_today_utc_returns_date(self):
        """today_utc should return a date object."""
        result = today_utc()
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_today_utc_is_reasonable(self):
        """today_utc should return a date close to today."""
        result = today_utc()
        # Within 1 second of real today (UTC)
        real_today = datetime.now(timezone.utc).date()
        assert result == real_today or result == real_today - timedelta(days=1)


class TestNowUTC:
    """Tests for now_utc() function."""

    def test_now_utc_returns_datetime(self):
        """now_utc should return a datetime object."""
        result = now_utc()
        assert isinstance(result, datetime)

    def test_now_utc_has_timezone_info(self):
        """now_utc should return UTC timezone-aware datetime."""
        result = now_utc()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc


class TestParseISODate:
    """Tests for parse_iso_date() function."""

    def test_parse_valid_iso_date(self):
        """Parse valid ISO 8601 date string."""
        result = parse_iso_date("2026-04-25")
        assert result == date(2026, 4, 25)

    def test_parse_iso_date_with_time(self):
        """Parse ISO date with time component (should extract date)."""
        result = parse_iso_date("2026-04-25T14:30:00")
        assert result == date(2026, 4, 25)

    def test_parse_iso_date_leap_year(self):
        """Parse valid leap year date."""
        result = parse_iso_date("2024-02-29")
        assert result == date(2024, 2, 29)

    def test_parse_iso_date_year_boundary(self):
        """Parse date at year boundary."""
        result = parse_iso_date("2026-01-01")
        assert result == date(2026, 1, 1)

    def test_parse_invalid_iso_date(self):
        """Parse invalid date string should return None."""
        result = parse_iso_date("invalid-date")
        assert result is None

    def test_parse_iso_date_invalid_month(self):
        """Parse date with invalid month should return None."""
        result = parse_iso_date("2026-13-01")
        assert result is None

    def test_parse_iso_date_invalid_day(self):
        """Parse date with invalid day should return None."""
        result = parse_iso_date("2026-02-30")
        assert result is None

    def test_parse_iso_date_empty_string(self):
        """Parse empty string should return None."""
        result = parse_iso_date("")
        assert result is None

    def test_parse_iso_date_none(self):
        """Parse None should return None."""
        result = parse_iso_date(None)
        assert result is None

    def test_parse_iso_date_wrong_format(self):
        """Parse date in wrong format should return None."""
        result = parse_iso_date("25-04-2026")  # DD-MM-YYYY instead of YYYY-MM-DD
        assert result is None


class TestToISODate:
    """Tests for to_iso_date() function."""

    def test_convert_date_to_iso(self):
        """Convert date object to ISO 8601 string."""
        d = date(2026, 4, 25)
        result = to_iso_date(d)
        assert result == "2026-04-25"

    def test_convert_date_with_padding(self):
        """ISO string should have zero-padded month and day."""
        d = date(2026, 1, 5)
        result = to_iso_date(d)
        assert result == "2026-01-05"

    def test_convert_none_to_iso(self):
        """Convert None should return None."""
        result = to_iso_date(None)
        assert result is None

    def test_round_trip_conversion(self):
        """Convert date → ISO → date should preserve value."""
        original = date(2026, 4, 25)
        iso_string = to_iso_date(original)
        restored = parse_iso_date(iso_string)
        assert restored == original

    def test_round_trip_leap_year(self):
        """Round-trip conversion should preserve leap year date."""
        original = date(2024, 2, 29)
        iso_string = to_iso_date(original)
        restored = parse_iso_date(iso_string)
        assert restored == original


class TestDaysBetween:
    """Tests for days_between() function."""

    def test_same_date(self):
        """Days between same date should be 0."""
        d = date(2026, 4, 25)
        result = days_between(d, d)
        assert result == 0

    def test_forward_difference(self):
        """Days from earlier to later date should be positive."""
        start = date(2026, 4, 25)
        end = date(2026, 4, 30)
        result = days_between(start, end)
        assert result == 5

    def test_backward_difference(self):
        """Days from later to earlier date should be negative."""
        start = date(2026, 4, 30)
        end = date(2026, 4, 25)
        result = days_between(start, end)
        assert result == -5

    def test_one_day_forward(self):
        """One day forward should return 1."""
        start = date(2026, 4, 25)
        end = date(2026, 4, 26)
        result = days_between(start, end)
        assert result == 1

    def test_one_day_backward(self):
        """One day backward should return -1."""
        start = date(2026, 4, 26)
        end = date(2026, 4, 25)
        result = days_between(start, end)
        assert result == -1

    def test_month_boundary(self):
        """Days across month boundary."""
        start = date(2026, 3, 30)
        end = date(2026, 4, 2)
        result = days_between(start, end)
        assert result == 3

    def test_year_boundary(self):
        """Days across year boundary."""
        start = date(2025, 12, 30)
        end = date(2026, 1, 2)
        result = days_between(start, end)
        assert result == 3

    def test_large_difference(self):
        """Days between distant dates."""
        start = date(2020, 1, 1)
        end = date(2026, 4, 25)
        result = days_between(start, end)
        # Should be around 2300+ days
        assert result > 2300
        assert isinstance(result, int)


class TestAddDays:
    """Tests for add_days() function."""

    def test_add_zero_days(self):
        """Adding 0 days should return same date."""
        d = date(2026, 4, 25)
        result = add_days(d, 0)
        assert result == d

    def test_add_positive_days(self):
        """Adding positive days should advance date."""
        d = date(2026, 4, 25)
        result = add_days(d, 5)
        assert result == date(2026, 4, 30)

    def test_add_one_day(self):
        """Adding 1 day."""
        d = date(2026, 4, 25)
        result = add_days(d, 1)
        assert result == date(2026, 4, 26)

    def test_add_days_month_boundary(self):
        """Adding days crossing month boundary."""
        d = date(2026, 3, 30)
        result = add_days(d, 2)
        assert result == date(2026, 4, 1)

    def test_add_days_year_boundary(self):
        """Adding days crossing year boundary."""
        d = date(2025, 12, 30)
        result = add_days(d, 2)
        assert result == date(2026, 1, 1)

    def test_add_negative_days(self):
        """Adding negative days should go backwards."""
        d = date(2026, 4, 25)
        result = add_days(d, -5)
        assert result == date(2026, 4, 20)

    def test_add_large_days(self):
        """Adding large number of days."""
        d = date(2026, 1, 1)
        result = add_days(d, 365)
        assert result == date(2027, 1, 1)

    def test_add_leap_day(self):
        """Adding to leap year Feb 28 should work correctly."""
        d = date(2024, 2, 28)
        result = add_days(d, 1)
        assert result == date(2024, 2, 29)


class TestSubtractDays:
    """Tests for subtract_days() function."""

    def test_subtract_zero_days(self):
        """Subtracting 0 days should return same date."""
        d = date(2026, 4, 25)
        result = subtract_days(d, 0)
        assert result == d

    def test_subtract_positive_days(self):
        """Subtracting positive days should go backwards."""
        d = date(2026, 4, 25)
        result = subtract_days(d, 5)
        assert result == date(2026, 4, 20)

    def test_subtract_one_day(self):
        """Subtracting 1 day."""
        d = date(2026, 4, 25)
        result = subtract_days(d, 1)
        assert result == date(2026, 4, 24)

    def test_subtract_days_month_boundary(self):
        """Subtracting days crossing month boundary backwards."""
        d = date(2026, 4, 1)
        result = subtract_days(d, 2)
        assert result == date(2026, 3, 30)

    def test_subtract_days_year_boundary(self):
        """Subtracting days crossing year boundary backwards."""
        d = date(2026, 1, 1)
        result = subtract_days(d, 2)
        assert result == date(2025, 12, 30)

    def test_subtract_negative_days(self):
        """Subtracting negative days should go forwards."""
        d = date(2026, 4, 25)
        result = subtract_days(d, -5)
        assert result == date(2026, 4, 30)

    def test_subtract_large_days(self):
        """Subtracting large number of days."""
        d = date(2027, 1, 1)
        result = subtract_days(d, 365)
        assert result == date(2026, 1, 1)

    def test_subtract_leap_day(self):
        """Subtracting from leap year Mar 1 should work correctly."""
        d = date(2024, 3, 1)
        result = subtract_days(d, 1)
        assert result == date(2024, 2, 29)


class TestAddSubtractInverse:
    """Tests verifying add/subtract are inverse operations."""

    def test_add_then_subtract(self):
        """Adding then subtracting same days should restore original."""
        original = date(2026, 4, 25)
        after_add = add_days(original, 10)
        after_subtract = subtract_days(after_add, 10)
        assert after_subtract == original

    def test_subtract_then_add(self):
        """Subtracting then adding same days should restore original."""
        original = date(2026, 4, 25)
        after_subtract = subtract_days(original, 10)
        after_add = add_days(after_subtract, 10)
        assert after_add == original

    def test_add_negative_equals_subtract_positive(self):
        """Adding negative days equals subtracting positive."""
        d = date(2026, 4, 25)
        result1 = add_days(d, -5)
        result2 = subtract_days(d, 5)
        assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
