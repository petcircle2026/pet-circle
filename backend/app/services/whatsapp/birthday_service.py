"""
PetCircle — Birthday Reminder Service

Handles creation and management of birthday reminders for pets.
Integrates with the preventive record system to track annual birthday events.

Key functions:
    - calculate_next_birthday: Calculates next birthday date from pet DOB
"""

import logging
from datetime import date as DateType

from sqlalchemy.orm import Session

from app.models.core.pet import Pet
from app.models.preventive.preventive_record import PreventiveRecord
from app.utils.date_utils import get_today_ist

logger = logging.getLogger(__name__)


def calculate_next_birthday(dob: DateType) -> DateType:
    """
    Calculate the next birthday date from a given date of birth.

    This function takes a pet's DOB and calculates the upcoming birthday,
    accounting for whether the pet's birthday has already passed this year.

    Args:
        dob: The pet's date of birth.

    Returns:
        The date of the next birthday (this year or next year).
    """
    today = get_today_ist()

    # Extract month and day from DOB
    birthday_this_year = DateType(today.year, dob.month, dob.day)

    # If birthday hasn't occurred yet this year, return this year's date
    if birthday_this_year >= today:
        return birthday_this_year

    # Otherwise, return next year's birthday
    return DateType(today.year + 1, dob.month, dob.day)


