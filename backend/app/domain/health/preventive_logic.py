"""
Preventive Care — Vaccine Eligibility and Frequency Utilities

Utility functions for vaccine age-eligibility and frequency label conversion.

Status computation (overdue / upcoming / up_to_date) is handled exclusively by
compute_status() in app.services.shared.preventive_calculator, which uses the
IST timezone.  Do NOT add status logic here.
"""

import logging

from app.core.constants import (
    PUPPY_AGE_CUTOFF_DAYS,
    PUPPY_VACCINE_MIN_AGE_DAYS,
)
from app.utils.frequency import days_to_frequency_label, frequency_to_days

logger = logging.getLogger(__name__)


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
