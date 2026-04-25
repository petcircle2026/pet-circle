"""
Preventive Care Calculation Logic

Pure business logic for calculating preventive care status and due dates.
No database access, no side effects — fully testable in isolation.

Core formula:
    next_due_date = last_done_date + frequency_days

Status determination:
    - today > next_due_date → 'overdue'
    - today + reminder_before_days >= next_due_date → 'upcoming'
    - else → 'up_to_date'
"""

from datetime import date, timedelta


def calculate_next_due_date(last_done_date: date, frequency_days: int) -> date:
    """
    Calculate when preventive is next due.

    Args:
        last_done_date: When preventive was last performed
        frequency_days: How many days between occurrences

    Returns:
        Next due date
    """
    return last_done_date + timedelta(days=frequency_days)


def get_preventive_status(
    next_due_date: date,
    current_date: date = None,
    reminder_before_days: int = 7,
) -> str:
    """
    Determine preventive status based on due date.

    Status logic (all comparisons use current date):
    - today > next_due_date → 'overdue'
    - today + reminder_before_days >= next_due_date → 'upcoming'
    - else → 'up_to_date'

    Args:
        next_due_date: When preventive is due
        current_date: Date to use for comparison (default: today)
        reminder_before_days: Days before due date to mark as 'upcoming'

    Returns:
        Status: 'overdue', 'upcoming', or 'up_to_date'
    """
    if current_date is None:
        current_date = date.today()

    if current_date > next_due_date:
        return "overdue"

    reminder_date = current_date + timedelta(days=reminder_before_days)
    if reminder_date >= next_due_date:
        return "upcoming"

    return "up_to_date"


def is_overdue(next_due_date: date, current_date: date = None) -> bool:
    """Check if preventive is overdue."""
    if current_date is None:
        current_date = date.today()
    return current_date > next_due_date


def is_upcoming(
    next_due_date: date,
    current_date: date = None,
    reminder_before_days: int = 7,
) -> bool:
    """Check if preventive is coming up soon."""
    if current_date is None:
        current_date = date.today()
    reminder_date = current_date + timedelta(days=reminder_before_days)
    return current_date <= next_due_date <= reminder_date


def days_until_due(next_due_date: date, current_date: date = None) -> int:
    """
    Calculate days until preventive is due.

    Returns:
        Positive = days until due
        Zero or negative = already due (overdue)
    """
    if current_date is None:
        current_date = date.today()
    return (next_due_date - current_date).days


def get_frequency_in_days(frequency_months: int | None) -> int:
    """
    Convert frequency from months to approximate days.

    Uses 30 days per month for calculation.
    """
    if frequency_months is None:
        return 0
    return frequency_months * 30


def parse_frequency_string(frequency_str: str) -> int | None:
    """
    Parse frequency from string like "Every 3 months" or "Monthly".

    Supports patterns:
    - "Every N weeks" → N * 7 days
    - "Every N months" → N * 30 days
    - "Every N days" → N days
    - "Monthly" → 30 days
    - "Quarterly" → 90 days
    - "Annually" → 365 days

    Returns:
        Frequency in days, or None if unable to parse
    """
    if not frequency_str:
        return None

    import re

    freq = str(frequency_str).lower().strip()

    # Try "Every N weeks" pattern
    match = re.search(r"every\s+(\d+)\s+weeks?", freq)
    if match:
        weeks = int(match.group(1))
        return weeks * 7

    # Try "Every N months" pattern
    match = re.search(r"every\s+(\d+)\s+months?", freq)
    if match:
        months = int(match.group(1))
        return months * 30

    # Try "Every N days" pattern
    match = re.search(r"every\s+(\d+)\s+days?", freq)
    if match:
        return int(match.group(1))

    # Check for common keywords
    if "monthly" in freq or "once a month" in freq:
        return 30
    if "quarterly" in freq or "3 month" in freq or "3-month" in freq:
        return 90
    if "bi-monthly" in freq or "bimonthly" in freq:
        return 60
    if "annually" in freq or "yearly" in freq or "once a year" in freq:
        return 365
    if "semi-annually" in freq or "every 6 month" in freq:
        return 180

    return None


def should_send_reminder(
    next_due_date: date,
    current_date: date = None,
    reminder_before_days: int = 7,
) -> bool:
    """
    Determine if a reminder should be sent for this preventive.

    Reminders are sent when status is 'overdue' or 'upcoming'.
    """
    status = get_preventive_status(next_due_date, current_date, reminder_before_days)
    return status in ("overdue", "upcoming")


def calculate_overdue_duration(next_due_date: date, current_date: date = None) -> int:
    """
    Calculate how many days overdue a preventive is.

    Returns:
        Days overdue (0 if not overdue)
    """
    if current_date is None:
        current_date = date.today()

    if not is_overdue(next_due_date, current_date):
        return 0

    return (current_date - next_due_date).days


def get_frequency_label(frequency_days: int) -> str:
    """Get human-readable label for frequency."""
    if frequency_days == 7:
        return "Weekly"
    if frequency_days == 30:
        return "Monthly"
    if frequency_days == 60:
        return "Bi-monthly"
    if frequency_days == 90:
        return "Quarterly"
    if frequency_days == 180:
        return "Semi-annually"
    if frequency_days == 365:
        return "Annually"
    if frequency_days % 7 == 0:
        weeks = frequency_days // 7
        return f"Every {weeks} weeks"
    if frequency_days % 30 == 0:
        months = frequency_days // 30
        return f"Every {months} months"
    return f"Every {frequency_days} days"
