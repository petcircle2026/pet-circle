"""
Standardized Date Utilities

All date handling uses UTC to prevent timezone inconsistencies.
Frontend converts to local timezone for display only.

Key principles:
1. Backend stores and computes with UTC dates only (date, datetime.utcnow())
2. All date calculations use naive UTC dates (no timezone objects)
3. Frontend receives ISO 8601 strings and displays in local timezone
4. No timezone conversions in business logic — only at display boundaries
"""

from datetime import date, datetime, timedelta, timezone


def today_utc() -> date:
    """Get today's date in UTC."""
    return datetime.now(timezone.utc).date()


def now_utc() -> datetime:
    """Get current datetime in UTC."""
    return datetime.now(timezone.utc)


def parse_iso_date(iso_string: str | None) -> date | None:
    """
    Parse ISO 8601 date string (YYYY-MM-DD) to date object.

    Args:
        iso_string: ISO format date string

    Returns:
        date object or None if invalid
    """
    if not iso_string:
        return None
    try:
        return datetime.fromisoformat(iso_string).date()
    except (ValueError, AttributeError):
        return None


def to_iso_date(d: date | None) -> str | None:
    """Convert date object to ISO 8601 string."""
    if d is None:
        return None
    return d.isoformat()


def days_between(start: date, end: date) -> int:
    """
    Calculate days between two dates.

    Args:
        start: Start date
        end: End date

    Returns:
        Number of days (positive if end > start, negative if end < start)
    """
    return (end - start).days


def add_days(d: date, days: int) -> date:
    """Add days to a date."""
    return d + timedelta(days=days)


def subtract_days(d: date, days: int) -> date:
    """Subtract days from a date."""
    return d - timedelta(days=days)
