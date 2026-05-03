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

from app.models.preventive.preventive_record import PreventiveRecord
from app.repositories.preventive_master_repository import PreventiveMasterRepository
from app.repositories.preventive_repository import PreventiveRepository
from app.utils.date_utils import get_today_ist

logger = logging.getLogger(__name__)

# Item types where life-stage-adjusted baseline applies.
# Must match canonical test_type strings from care_plan_engine._normalize_item_name.
_LIFE_STAGE_TYPES = {"deworming", "tick_flea"}


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
        from app.models import ProductMedicines

        product = (
            db.query(ProductMedicines)
            .filter(
                ProductMedicines.active == True,
                ProductMedicines.product_name.ilike(f"%{medicine_name}%"),
            )
            .first()
        )

        # Fallback: try brand name only (first token before space/dash) so that
        # "Bravecto Chew 10-20 kg" still matches "Bravecto--Chew--10–20 kg".
        if not product:
            brand = re.split(r"[\s\-–—]+", medicine_name.strip())[0]
            if brand and brand.lower() != medicine_name.strip().lower():
                product = (
                    db.query(ProductMedicines)
                    .filter(
                        ProductMedicines.active == True,
                        ProductMedicines.product_name.ilike(f"%{brand}%"),
                    )
                    .first()
                )

        if not product or not product.repeat_frequency:
            return None

        freq = str(product.repeat_frequency).lower()

        match = re.search(r"every\s+(\d+)\s+weeks?", freq)
        if match:
            return int(match.group(1)) * 7

        match = re.search(r"every\s+(\d+)\s+months?", freq)
        if match:
            return int(match.group(1)) * 30

        match = re.search(r"every\s+(\d+)\s+days?", freq)
        if match:
            return int(match.group(1))

        if "monthly" in freq or "once a month" in freq:
            return 30
        if "quarterly" in freq or "3 month" in freq:
            return 90
        if "annually" in freq or "yearly" in freq:
            return 365
        if "fortnightly" in freq or "bi-weekly" in freq or "biweekly" in freq:
            return 14
        if "weekly" in freq:
            return 7

        return None

    except Exception as exc:
        logger.warning(f"Could not extract recurrence from medicine '{medicine_name}': {exc}")
        return None


def get_effective_recurrence_days(
    db: Session,
    master,
    record,
    pet=None,
) -> int:
    """
    Resolve the effective recurrence interval for a preventive record.

    This is the SINGLE source of truth for recurrence resolution.
    All callers — dashboard_service, health_trends_service, care_plan_engine —
    must use this function instead of inlining their own priority logic.

    Priority order (highest → lowest):
        1. record.custom_recurrence_days
               User-set override or medicine-detected override already persisted.
        2. Medicine-specific days (get_medicine_recurrence_days)
               Only when master.medicine_dependent=True and record.medicine_name is set.
               Persists the found value to record.custom_recurrence_days.
        3. Life-stage baseline (get_preventive_baseline_days)
               Only for deworming and tick_flea when pet is provided.
        4. master.recurrence_days
               Seeded default fallback.

    Args:
        db:     SQLAlchemy session.
        master: PreventiveMaster instance for this item.
        record: PreventiveRecord (or proxy with custom_recurrence_days + medicine_name).
        pet:    Pet instance (required for life-stage logic; safe to pass None).

    Returns:
        Effective recurrence interval in days.
    """
    # Priority 1 — user-set or previously medicine-detected custom override.
    if record.custom_recurrence_days:
        logger.debug(
            "Recurrence: custom_recurrence_days=%d for record_id=%s",
            record.custom_recurrence_days, str(getattr(record, "id", None)),
        )
        return record.custom_recurrence_days

    if master is None:
        return 365

    # Priority 2 — medicine-specific frequency from product catalog.
    if master.medicine_dependent and getattr(record, "medicine_name", None):
        med_days = get_medicine_recurrence_days(db, record.medicine_name)
        if med_days:
            record.custom_recurrence_days = med_days
            try:
                db.flush()
            except Exception:
                pass  # Non-fatal — value still used for this call.
            logger.info(
                "Recurrence: medicine '%s' → %d days (master default was %d) "
                "for record_id=%s",
                record.medicine_name, med_days,
                master.recurrence_days, str(getattr(record, "id", None)),
            )
            return med_days

    # Priority 3 — life-stage-adjusted baseline.
    # Only for deworming and tick_flea, and only when pet is available.
    if pet is not None:
        try:
            from app.services.shared.care_plan_engine import (
                _classify_item_type_llm,
                get_preventive_baseline_days,
            )
            test_type = _classify_item_type_llm(master.item_name)
            if test_type in _LIFE_STAGE_TYPES:
                baseline = get_preventive_baseline_days(pet, test_type)
                logger.debug(
                    "Recurrence: life-stage baseline=%d for test_type=%s, record_id=%s",
                    baseline, test_type, str(getattr(record, "id", None)),
                )
                return baseline
        except Exception as exc:
            logger.warning(
                "Could not resolve life-stage baseline for record_id=%s: %s",
                str(getattr(record, "id", None)), exc,
            )

    # Priority 4 — master default fallback.
    logger.debug(
        "Recurrence: master.recurrence_days=%d for record_id=%s",
        master.recurrence_days, str(getattr(record, "id", None)),
    )
    return master.recurrence_days


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
    next_due = last_done_date + timedelta(days=recurrence_days)
    logger.debug(
        "compute_next_due_date: last_done=%s recurrence_days=%d next_due=%s",
        last_done_date,
        recurrence_days,
        next_due,
    )
    return next_due


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
        logger.debug(
            "compute_status: today=%s next_due=%s reminder_before=%d -> overdue",
            today, next_due_date, reminder_before_days,
        )
        return "overdue"

    reminder_window_start = next_due_date - timedelta(days=reminder_before_days)
    if today >= reminder_window_start:
        logger.debug(
            "compute_status: today=%s next_due=%s reminder_before=%d window_start=%s -> upcoming",
            today, next_due_date, reminder_before_days, reminder_window_start,
        )
        return "upcoming"

    logger.debug(
        "compute_status: today=%s next_due=%s reminder_before=%d -> up_to_date",
        today, next_due_date, reminder_before_days,
    )
    return "up_to_date"


def calculate_and_update_record(
    db: Session,
    preventive_record_id: UUID,
    pet=None,
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

    item = record.item

    if not item:
        raise ValueError(
            f"Preventive item not found for record: {preventive_record_id}"
        )

    # Skip if last_done_date is not set (newly seeded record with no data).
    if record.last_done_date is None:
        logger.info(
            "Skipping recalculation — no last_done_date: record_id=%s",
            str(preventive_record_id),
        )
        return record

    # Resolve effective recurrence using unified priority logic.
    effective_days = get_effective_recurrence_days(db, item, record, pet)

    new_next_due = compute_next_due_date(record.last_done_date, effective_days)
    new_status = compute_status(new_next_due, item.reminder_before_days)

    record.next_due_date = new_next_due
    record.status = new_status

    db.commit()

    logger.info(
        "Preventive record updated: record_id=%s, next_due=%s, status=%s, "
        "effective_recurrence=%d",
        str(preventive_record_id), str(new_next_due), new_status, effective_days,
    )

    return record


def create_preventive_record(
    db: Session,
    pet_id: UUID,
    preventive_master_id: UUID,
    last_done_date: date,
    medicine_name: str | None = None,
    pet=None,
) -> PreventiveRecord:
    """
    Create a new preventive record with computed next_due_date and status.

    Uses get_effective_recurrence_days() so medicine-specific frequency
    (e.g. Bravecto = 90 days) is applied from the moment of creation.

    Args:
        db: SQLAlchemy database session.
        pet_id: UUID of the pet.
        preventive_master_id: UUID of the preventive master item.
        last_done_date: Date the preventive action was performed.
        medicine_name: Product name used (e.g. "Bravecto"). Optional.
        pet: Pet instance (optional — enables life-stage logic).

    Returns:
        The newly created (or updated placeholder) PreventiveRecord.

    Raises:
        ValueError: If the preventive master item is not found.
    """
    preventive_repo = PreventiveRepository(db)
    master_repo = PreventiveMasterRepository(db)

    master = master_repo.find_by_id(preventive_master_id)

    if not master:
        raise ValueError(
            f"Preventive master not found: {preventive_master_id}"
        )

    # Use a proxy so get_effective_recurrence_days can read medicine_name
    # without a real DB row (avoids flushing an uncommitted record).
    class _RecordProxy:
        custom_recurrence_days = None
        id = None

    proxy = _RecordProxy()
    proxy.medicine_name = medicine_name

    effective_days = get_effective_recurrence_days(db, master, proxy, pet)

    # Persist medicine-derived recurrence on the real record.
    medicine_recurrence = None
    if master.medicine_dependent and medicine_name:
        med_days = get_medicine_recurrence_days(db, medicine_name)
        if med_days:
            medicine_recurrence = med_days

    next_due = compute_next_due_date(last_done_date, effective_days)
    status = compute_status(next_due, master.reminder_before_days)

    existing_record = preventive_repo.find_existing_record(pet_id, preventive_master_id, last_done_date)
    if existing_record:
        existing_record.next_due_date = next_due
        existing_record.status = status
        if medicine_name and not existing_record.medicine_name:
            existing_record.medicine_name = medicine_name
        if medicine_recurrence and not existing_record.custom_recurrence_days:
            existing_record.custom_recurrence_days = medicine_recurrence
        db.commit()
        return existing_record

    placeholder_record = preventive_repo.find_placeholder_record(pet_id, preventive_master_id)
    if placeholder_record:
        placeholder_record.last_done_date = last_done_date
        placeholder_record.next_due_date = next_due
        placeholder_record.status = status
        if medicine_name and not placeholder_record.medicine_name:
            placeholder_record.medicine_name = medicine_name
        if medicine_recurrence and not placeholder_record.custom_recurrence_days:
            placeholder_record.custom_recurrence_days = medicine_recurrence
        db.commit()
        logger.info(
            "Preventive placeholder filled: pet_id=%s, item=%s, last_done=%s, "
            "next_due=%s, status=%s, effective_recurrence=%d",
            str(pet_id), master.item_name, str(last_done_date),
            str(next_due), status, effective_days,
        )
        return placeholder_record

    # Create a new preventive record when there is no existing exact or placeholder row.
    record = PreventiveRecord(
        pet_id=pet_id,
        preventive_master_id=preventive_master_id,
        last_done_date=last_done_date,
        next_due_date=next_due,
        status=status,
        medicine_name=medicine_name,
        custom_recurrence_days=medicine_recurrence,
    )

    db.add(record)
    db.commit()

    logger.info(
        "Preventive record created: pet_id=%s, item=%s, last_done=%s, "
        "next_due=%s, status=%s, effective_recurrence=%d, medicine=%s",
        str(pet_id), master.item_name, str(last_done_date),
        str(next_due), status, effective_days, medicine_name,
    )

    return record


def days_to_freq_label(days: int) -> str:
    """Convert recurrence interval in days to a human-readable label."""
    if days <= 7:   return "Weekly"
    if days <= 14:  return "Every 2 weeks"
    if days <= 31:  return "Monthly"
    if days <= 45:  return "Every 6 weeks"
    if days <= 93:  return "Every 3 months"
    if days <= 186: return "Every 6 months"
    if days <= 366: return "Annual"
    if days <= 731: return "Every 2 years"
    return "Every 3+ years"


def status_tag_for_display(
    next_due: "date | None",
    has_history: bool,
    reminder_before_days: int = 7,
) -> str:
    """
    UI status string for a preventive item.

    Delegates to compute_status so the same IST timezone and reminder_before_days
    window are used everywhere.

    No history / no next_due → "Not started"
    today > next_due         → "Overdue"
    within reminder window   → "Upcoming"
    Otherwise                → "On track"
    """
    if not has_history or next_due is None:
        return "Not started"
    status = compute_status(next_due, reminder_before_days)
    if status == "overdue":
        return "Overdue"
    if status == "upcoming":
        return "Upcoming"
    return "Up to date"


def resolve_item_display(
    db: Session,
    records: list,
    pet=None,
) -> dict:
    """
    Single source of truth for the display values of a preventive item.

    Given all PreventiveRecord objects for one item_key, returns the canonical
    display values that care plan, reminders, and cadence views must all agree on:

        last_done       — date of the most recent completion (or None)
        next_due        — compute_next_due_date(last_done, effective_recurrence)
        status_display  — "Up to date" | "Upcoming" | "Overdue" | "Not started"
        freq_label      — human-readable frequency e.g. "Every 3 months"
        recurrence_days — integer used to compute next_due (0 when no records)

    The canonical record is the one with the most recent last_done_date.
    When multiple records share an item_key (e.g. repeated deworming sessions)
    only the latest one drives last_done / next_due / status.
    """
    records_with_done = [r for r in records if getattr(r, "last_done_date", None)]
    if records_with_done:
        canonical = max(records_with_done, key=lambda r: r.last_done_date)
    elif records:
        canonical = records[0]
    else:
        return {
            "last_done": None,
            "next_due": None,
            "status_display": "Not started",
            "freq_label": "—",
            "recurrence_days": 0,
        }

    master = getattr(canonical, "item", None)
    recurrence = get_effective_recurrence_days(db, master, canonical, pet)
    reminder_days = getattr(master, "reminder_before_days", 7) if master else 7
    last_done: "date | None" = getattr(canonical, "last_done_date", None)
    if last_done:
        next_due: "date | None" = compute_next_due_date(last_done, recurrence)
    else:
        next_due = getattr(canonical, "next_due_date", None)

    return {
        "last_done": last_done,
        "next_due": next_due,
        "status_display": status_tag_for_display(next_due, bool(last_done), reminder_days),
        "freq_label": days_to_freq_label(recurrence),
        "recurrence_days": recurrence,
    }
