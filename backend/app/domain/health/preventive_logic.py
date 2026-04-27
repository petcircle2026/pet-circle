"""
Preventive Care Calculation Logic

Pure business logic for calculating preventive care status and due dates.
No database access, no side effects - fully testable in isolation.

Core formula:
    next_due_date = last_done_date + frequency_days

Status determination:
    - today > next_due_date -> 'overdue'
    - today + reminder_before_days >= next_due_date -> 'upcoming'
    - else -> 'up_to_date'
"""

import logging
from datetime import date, timedelta

from app.core.constants import (
    PUPPY_AGE_CUTOFF_DAYS,
    PUPPY_VACCINE_MIN_AGE_DAYS,
)
from app.utils.frequency import days_to_frequency_label, frequency_to_days

logger = logging.getLogger(__name__)


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
    - today > next_due_date -> 'overdue'
    - today + reminder_before_days >= next_due_date -> 'upcoming'
    - else -> 'up_to_date'

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

    Delegates to the canonical frequency_to_days() utility so that
    this module and preventive_calculator share identical conversion logic.

    Returns:
        Frequency in days, or None if unable to parse
    """
    return frequency_to_days(frequency_str)


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
    return days_to_frequency_label(frequency_days)


# ─── Vaccine Eligibility ─────────────────────────────────────────────
# Age-based vaccine filtering for puppies/kittens.
# Eligibility data lives in constants.py so it can be tuned without
# touching domain logic.

def is_vaccine_eligible_for_age(
    vaccine_item_name: str,
    pet_age_days: int | None,
    species: str = "dog",
) -> bool:
    """
    Determine if a vaccine is eligible for a pet based on age.

    For dogs/cats < 1 year: only show if age >= minimum age for that vaccine
    For dogs/cats >= 1 year: hide all puppy-specific vaccines

    Args:
        vaccine_item_name: Name of the vaccine (e.g. "DHPPI 1st dose")
        pet_age_days: Pet age in days (None = unknown/treat as ineligible)
        species: Pet species ('dog', 'cat', etc.)

    Returns:
        True if vaccine should be shown for this pet's age, False otherwise
    """
    if not vaccine_item_name or pet_age_days is None:
        return True

    if species and species.lower() not in ("dog", "cat"):
        return True

    vaccine_lower = vaccine_item_name.lower()
    min_age = PUPPY_VACCINE_MIN_AGE_DAYS.get(vaccine_lower)

    if min_age is None:
        return True

    if pet_age_days >= PUPPY_AGE_CUTOFF_DAYS:
        logger.debug(
            "is_vaccine_eligible_for_age: vaccine=%s age_days=%d >= cutoff=%d -> ineligible (adult pet)",
            vaccine_item_name, pet_age_days, PUPPY_AGE_CUTOFF_DAYS,
        )
        return False

    eligible = pet_age_days >= min_age
    logger.debug(
        "is_vaccine_eligible_for_age: vaccine=%s age_days=%d min_age=%d -> %s",
        vaccine_item_name, pet_age_days, min_age, "eligible" if eligible else "too young",
    )
    return eligible
