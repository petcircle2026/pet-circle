"""
PetCircle Phase 1 — Preventive Calculator (Module 9)

Computes next_due_date and determines preventive status for pet health records.

Core formula:
    next_due_date = last_done_date + recurrence_days

Status logic (all comparisons use Asia/Kolkata timezone):
    - today > next_due_date → 'overdue'
    - today + reminder_before_days >= next_due_date → 'upcoming'
    - else → 'up_to_date'

Rules:
    - recurrence_days is ALWAYS read from preventive_master table — never hardcoded.
    - reminder_before_days and overdue_after_days come from preventive_master.
    - All date comparisons use IST (Asia/Kolkata).
    - No hidden logic — every calculation is documented.
"""
import logging
import re
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.preventive_record import PreventiveRecord
from app.repositories.preventive_master_repository import PreventiveMasterRepository
from app.repositories.preventive_repository import PreventiveRepository
from app.utils.date_utils import get_today_ist

logger = logging.getLogger(__name__)


def get_medicine_recurrence_days(db: Session, medicine_name: str | None) -> int | None:
    """
    Look up a medicine in product_medicines and extract recurrence days from repeat_frequency.

    Supports patterns like:
        - "Every 3 months (12 weeks)" → 90 days
        - "Every 4 weeks" → 28 days
        - "Every 12 weeks" → 84 days
        - "Monthly" → 30 days
        - "Quarterly" → 90 days

    Args:
        db: SQLAlchemy session
        medicine_name: Product name to search for

    Returns:
        Number of days between doses, or None if not found
    """
    if not medicine_name or not db:
        return None

    try:
        product = PreventiveMasterRepository(db).find_medicine_by_name_ilike(medicine_name)

        if not product or not product.repeat_frequency:
            return None

        freq = str(product.repeat_frequency).lower()

        # Extract number and unit from repeat_frequency
        # Patterns: "Every N weeks", "Every N months", "Monthly", "Quarterly", "Annually"

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
        elif "quarterly" in freq or "3 month" in freq:
            return 90
        elif "annually" in freq or "yearly" in freq:
            return 365
        elif "fortnightly" in freq or "bi-weekly" in freq or "biweekly" in freq:
            return 14
        elif "weekly" in freq:
            return 7

        return None

    except Exception as exc:
        logger.warning(f"Could not extract recurrence from medicine '{medicine_name}': {exc}")
        return None


def compute_next_due_date(last_done_date: date, recurrence_days: int) -> date:
    """
    Compute the next due date for a preventive item.

    Formula:
        next_due_date = last_done_date + recurrence_days

    The recurrence_days value must come from preventive_master.recurrence_days
    in the database. It is passed as a parameter here to keep this function
    pure and testable.

    Args:
        last_done_date: The date the preventive action was last performed.
        recurrence_days: Number of days between occurrences (from DB).

    Returns:
        The computed next due date.
    """
    return last_done_date + timedelta(days=recurrence_days)


def compute_status(next_due_date: date, reminder_before_days: int) -> str:
    """
    Determine the preventive status based on today's date vs next_due_date.

    Status logic (all comparisons in IST):
        - today > next_due_date → 'overdue'
            The preventive action is past due.
        - today + reminder_before_days >= next_due_date → 'upcoming'
            The due date is approaching — within the reminder window.
        - else → 'up_to_date'
            The preventive action is not yet due.

    Args:
        next_due_date: The computed next due date for the preventive item.
        reminder_before_days: Days before due date to trigger 'upcoming'
            status (from preventive_master.reminder_before_days in DB).

    Returns:
        Status string: 'overdue', 'upcoming', or 'up_to_date'.
    """
    # All date comparisons use Asia/Kolkata timezone.
    today = get_today_ist()

    if today > next_due_date:
        # Past the due date — action is overdue.
        return "overdue"

    # Check if today falls within the reminder window.
    # reminder_window_start = next_due_date - reminder_before_days
    # If today >= reminder_window_start, the item is 'upcoming'.
    reminder_window_start = next_due_date - timedelta(days=reminder_before_days)
    if today >= reminder_window_start:
        return "upcoming"

    # Not yet within the reminder window — fully up to date.
    return "up_to_date"


def calculate_and_update_record(
    db: Session,
    preventive_record_id: UUID,
) -> PreventiveRecord:
    """
    Recalculate next_due_date and status for an existing preventive record.

    This function is called whenever a preventive record's last_done_date
    changes (e.g., after recording a new event or resolving a conflict).
    It reads recurrence_days from the preventive_master table in the DB.

    Steps:
        1. Load the preventive record and its linked master item.
        2. Compute next_due_date = last_done_date + recurrence_days.
        3. Compute status based on today vs next_due_date.
        4. Update and commit the record.

    Args:
        db: SQLAlchemy database session.
        preventive_record_id: UUID of the preventive record to update.

    Returns:
        The updated PreventiveRecord object.

    Raises:
        ValueError: If the preventive record or its master item is not found.
    """
    record = PreventiveRepository(db).get_by_id(preventive_record_id)

    if not record:
        raise ValueError(
            f"Preventive record not found: {preventive_record_id}"
        )

    master = PreventiveMasterRepository(db).find_by_id(record.preventive_master_id)

    if not master:
        raise ValueError(
            f"Preventive master not found for record: {preventive_record_id}"
        )

    # Skip if last_done_date is not set (newly seeded record with no data).
    if record.last_done_date is None:
        logger.info(
            "Skipping recalculation — no last_done_date: record_id=%s",
            str(preventive_record_id),
        )
        return record

    # Compute next_due_date from last_done_date and DB recurrence_days.
    new_next_due = compute_next_due_date(record.last_done_date, master.recurrence_days)

    # Compute status based on today (IST) vs the new next_due_date.
    new_status = compute_status(new_next_due, master.reminder_before_days)

    # Update the record fields.
    record.next_due_date = new_next_due
    record.status = new_status

    db.commit()

    logger.info(
        "Preventive record updated: record_id=%s, next_due=%s, status=%s",
        str(preventive_record_id),
        str(new_next_due),
        new_status,
    )

    return record


def create_preventive_record(
    db: Session,
    pet_id: UUID,
    preventive_master_id: UUID,
    last_done_date: date,
) -> PreventiveRecord:
    """
    Create a new preventive record with computed next_due_date and status.

    This function is called when a new preventive event is recorded
    (e.g., from GPT extraction or manual entry). It reads recurrence_days
    from the preventive_master table — never hardcoded.

    The UNIQUE(pet_id, preventive_master_id, last_done_date) constraint
    on the table provides idempotency protection. If a duplicate record
    is attempted, the database will raise an IntegrityError.

    Args:
        db: SQLAlchemy database session.
        pet_id: UUID of the pet.
        preventive_master_id: UUID of the preventive master item.
        last_done_date: Date the preventive action was performed.

    Returns:
        The newly created PreventiveRecord.

    Raises:
        ValueError: If the preventive master item is not found.
        sqlalchemy.exc.IntegrityError: If a duplicate record exists
            (same pet, same item, same date).
    """
    preventive_repo = PreventiveRepository(db)
    master_repo = PreventiveMasterRepository(db)

    master = master_repo.find_by_id(preventive_master_id)

    if not master:
        raise ValueError(
            f"Preventive master not found: {preventive_master_id}"
        )

    next_due = compute_next_due_date(last_done_date, master.recurrence_days)
    status = compute_status(next_due, master.reminder_before_days)

    existing_record = preventive_repo.find_existing_record(pet_id, preventive_master_id, last_done_date)
    if existing_record:
        existing_record.next_due_date = next_due
        existing_record.status = status
        db.commit()
        return existing_record

    placeholder_record = preventive_repo.find_placeholder_record(pet_id, preventive_master_id)
    if placeholder_record:
        placeholder_record.last_done_date = last_done_date
        placeholder_record.next_due_date = next_due
        placeholder_record.status = status
        db.commit()
        logger.info(
            "Preventive placeholder filled: pet_id=%s, item=%s, last_done=%s, next_due=%s, status=%s",
            str(pet_id),
            master.item_name,
            str(last_done_date),
            str(next_due),
            status,
        )
        return placeholder_record

    # Create a new preventive record when there is no existing exact or placeholder row.
    record = PreventiveRecord(
        pet_id=pet_id,
        preventive_master_id=preventive_master_id,
        last_done_date=last_done_date,
        next_due_date=next_due,
        status=status,
    )

    db.add(record)
    db.commit()

    logger.info(
        "Preventive record created: pet_id=%s, item=%s, last_done=%s, "
        "next_due=%s, status=%s",
        str(pet_id),
        master.item_name,
        str(last_done_date),
        str(next_due),
        status,
    )

    return record


def recalculate_all_for_pet(db: Session, pet_id: UUID) -> int:
    """
    Recalculate next_due_date and status for all preventive records of a pet.

    Called when the dashboard needs a fresh view or after bulk updates.
    Each record's recurrence_days is read from its linked preventive_master.

    Args:
        db: SQLAlchemy database session.
        pet_id: UUID of the pet whose records should be recalculated.

    Returns:
        Number of records updated.
    """
    rows = PreventiveRepository(db).find_with_master_non_cancelled(pet_id)

    updated = 0
    for record, master in rows:
        # Skip records with no last_done_date (newly seeded, no data yet).
        # These cannot have next_due_date computed — leave them as-is.
        if record.last_done_date is None:
            continue

        # Recompute from DB values.
        new_next_due = compute_next_due_date(record.last_done_date, master.recurrence_days)
        new_status = compute_status(new_next_due, master.reminder_before_days)

        record.next_due_date = new_next_due
        record.status = new_status
        updated += 1

    db.commit()

    logger.info(
        "Recalculated %d preventive records for pet_id=%s",
        updated,
        str(pet_id),
    )

    return updated
