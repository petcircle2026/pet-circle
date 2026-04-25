"""
Pure reminder calculation logic (no DB, no I/O).

Handles reminder stage determination, snooze calculations, and batching logic.
All functions are pure and testable.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import NamedTuple


class ReminderStage(NamedTuple):
    """Reminder stage and details."""

    stage: str  # "t7" | "due" | "d3" | "overdue"
    days_until_due: int  # Negative if overdue
    send_now: bool  # True if reminder should be sent today


# Snooze intervals (days) by reminder category
SNOOZE_INTERVALS = {
    "vaccine": 7,
    "deworming": 7,
    "flea_tick": 7,
    "food": 3,
    "supplement": 7,
    "chronic_medicine": 7,
    "vet_followup": 7,
    "blood_checkup": 7,
    "vet_diagnostics": 7,
    "hygiene": 30,
}

# Reminder categories (from preventive_master and other sources)
REMINDER_CATEGORIES = frozenset({
    "vaccine",
    "deworming",
    "flea_tick",
    "food",
    "supplement",
    "chronic_medicine",
    "vet_followup",
    "blood_checkup",
    "vet_diagnostics",
    "hygiene",
})

# Vaccine-related keywords for batching reminders
VACCINE_KEYWORDS = (
    "vaccine",
    "vaccin",
    "dhpp",
    "rabies",
    "nobivac",
    "kennel cough",
    "bordetella",
    "coronavirus",
    "ccov",
    "fvrcp",
    "felv",
    "fiv",
)

DEWORMING_KEYWORDS = ("deworm", "worm")
FLEA_KEYWORDS = ("flea", "tick", "parasite")
BLOOD_KEYWORDS = ("blood", "cbc", "haematology")
DIAGNOSTICS_KEYWORDS = ("diagnostic", "x-ray", "ultrasound", "biopsy", "pcr", "urinalysis")


def determine_reminder_stage(due_date: date, today: date) -> ReminderStage:
    """
    Determine which stage of the reminder lifecycle an item is in.

    4-stage lifecycle:
    - T-7: 7 days before due date
    - Due: on due date or 1-6 days after
    - D+3: 3-6 days after due date (check-in stage)
    - Overdue: 7+ days after due date

    Args:
        due_date: Date when item is due
        today: Today's date

    Returns:
        ReminderStage with stage name and days until/past due
    """
    days_diff = (due_date - today).days

    if days_diff == 7:
        return ReminderStage(stage="t7", days_until_due=7, send_now=True)

    if days_diff == 0:
        return ReminderStage(stage="due", days_until_due=0, send_now=True)

    if -6 <= days_diff <= -1:
        # 1-6 days past due (D+1 to D+6)
        return ReminderStage(stage="d3", days_until_due=days_diff, send_now=True)

    if days_diff <= -7:
        # 7+ days overdue
        return ReminderStage(stage="overdue", days_until_due=days_diff, send_now=True)

    # Not yet at T-7 or past D+3
    return ReminderStage(stage="pending", days_until_due=days_diff, send_now=False)


def get_snooze_days(category: str) -> int:
    """
    Get snooze interval for a reminder category.

    Args:
        category: Reminder category string

    Returns:
        Number of days to snooze (default 7 for unknown categories)
    """
    return SNOOZE_INTERVALS.get(category, 7)


def calculate_snooze_until(today: date, category: str) -> date:
    """
    Calculate the snooze-until date for a reminder.

    Args:
        today: Today's date
        category: Reminder category

    Returns:
        Date when the snooze expires
    """
    snooze_days = get_snooze_days(category)
    return today + timedelta(days=snooze_days)


def is_valid_category(category: str) -> bool:
    """Check if a reminder category is valid."""
    return category in REMINDER_CATEGORIES


def classify_item_category(item_name: str) -> str | None:
    """
    Classify a preventive item into a reminder category based on keywords.

    Args:
        item_name: Name of the preventive item

    Returns:
        Category string or None if no match
    """
    name_lower = (item_name or "").lower()

    # Check in order of specificity
    if any(kw in name_lower for kw in VACCINE_KEYWORDS):
        return "vaccine"
    if any(kw in name_lower for kw in DEWORMING_KEYWORDS):
        return "deworming"
    if any(kw in name_lower for kw in FLEA_KEYWORDS):
        return "flea_tick"
    if any(kw in name_lower for kw in BLOOD_KEYWORDS):
        return "blood_checkup"
    if any(kw in name_lower for kw in DIAGNOSTICS_KEYWORDS):
        return "vet_diagnostics"

    return None


def should_batch_reminders(category: str) -> bool:
    """
    Return True if reminders in this category should be batched together.

    Vaccines are batched to reduce message volume; others sent individually.
    """
    return category == "vaccine"


def max_reminders_per_pet_per_day() -> int:
    """Maximum number of reminders to send to one pet per day."""
    return 1


def min_days_between_same_item_reminders() -> int:
    """Minimum days between reminders for the same preventive item."""
    return 3


def ignored_threshold() -> int:
    """Number of ignored reminders before activating monthly_fallback."""
    return 3
