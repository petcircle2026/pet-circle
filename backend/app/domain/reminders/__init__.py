"""Reminders domain â€” reminder logic, calculations, and orchestration."""

from app.domain.reminders.reminder_logic import (
    ReminderStage,
    determine_reminder_stage,
    get_snooze_days,
    calculate_snooze_until,
    is_valid_category,
    classify_item_category,
    should_batch_reminders,
    max_reminders_per_pet_per_day,
    min_days_between_same_item_reminders,
    ignored_threshold,
    SNOOZE_INTERVALS,
    REMINDER_CATEGORIES,
    VACCINE_KEYWORDS,
    DEWORMING_KEYWORDS,
    FLEA_KEYWORDS,
    BLOOD_KEYWORDS,
    DIAGNOSTICS_KEYWORDS,
)
from app.domain.reminders.reminder_service import ReminderService

__all__ = [
    # Reminder logic
    "ReminderStage",
    "determine_reminder_stage",
    "get_snooze_days",
    "calculate_snooze_until",
    "is_valid_category",
    "classify_item_category",
    "should_batch_reminders",
    "max_reminders_per_pet_per_day",
    "min_days_between_same_item_reminders",
    "ignored_threshold",
    "SNOOZE_INTERVALS",
    "REMINDER_CATEGORIES",
    "VACCINE_KEYWORDS",
    "DEWORMING_KEYWORDS",
    "FLEA_KEYWORDS",
    "BLOOD_KEYWORDS",
    "DIAGNOSTICS_KEYWORDS",
    # Service
    "ReminderService",
]

