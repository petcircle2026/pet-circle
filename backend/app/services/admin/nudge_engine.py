"""
PetCircle Phase 1 — Nudge Engine Service

Generates prioritized health action nudges for pets across 7 categories:
vaccine, deworming, flea, condition, nutrition, grooming, checkup.

Two entry points:
    - generate_nudges(db, pet_id): For dashboard — returns cached or fresh nudges
    - run_nudge_engine(db): For daily cron — regenerates nudges for all active pets
"""
import logging
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session, selectinload

from app.core.constants import (
    NUDGE_CACHE_HOURS,
    NUDGE_PRIORITY_ORDER,
    NUDGE_SOURCE_ORDER,
    NUDGE_TRIGGER_CRON,
)
from app.models.nudge import Nudge
from app.models.pet import Pet
from app.models.preventive_record import PreventiveRecord
from app.repositories.care_repository import CareRepository
from app.repositories.diet_repository import DietRepository
from app.repositories.health_repository import HealthRepository
from app.repositories.nudge_repository import NudgeRepository
from app.repositories.pet_repository import PetRepository
from app.repositories.preventive_master_repository import PreventiveMasterRepository
from app.repositories.preventive_repository import PreventiveRepository
from app.services.admin.nudge_config_service import get_nudge_config_int

logger = logging.getLogger(__name__)

# Keyword sets for matching preventive_master items to nudge categories.
# Keep this in sync with reminder and trends classifiers so generic
# "vaccines done" updates include all dog/cat vaccine variants.
VACCINE_KEYWORDS = {
    "vaccine",
    "rabies",
    "dhpp",
    "core vaccine",
    "feline core",
    "bordetella",
    "kennel cough",
    "nobivac",
    "coronavirus",
    "ccov",
}
DEWORMING_KEYWORDS = {"deworming", "deworm"}
FLEA_KEYWORDS = {"tick", "flea"}
CHECKUP_KEYWORDS = {"checkup", "annual", "wellness", "blood test", "preventive blood"}


def _classify_item(item_name: str) -> str | None:
    """Classify a preventive_master item_name into a nudge category."""
    name_lower = item_name.lower()
    if re.search(r"\b\d+\s*[- ]?in\s*[- ]?1\b", name_lower):
        return "vaccine"
    for kw in VACCINE_KEYWORDS:
        if kw in name_lower:
            return "vaccine"
    for kw in DEWORMING_KEYWORDS:
        if kw in name_lower:
            return "deworming"
    for kw in FLEA_KEYWORDS:
        if kw in name_lower:
            return "flea"
    for kw in CHECKUP_KEYWORDS:
        if kw in name_lower:
            return "checkup"
    return None


def _record_item_name(record: PreventiveRecord) -> str:
    """Resolve a human-readable preventive item name for master/custom records."""
    if record.preventive_master and record.preventive_master.item_name:
        return record.preventive_master.item_name
    if record.custom_preventive_item and record.custom_preventive_item.item_name:
        return record.custom_preventive_item.item_name
    return record.medicine_name or "Unknown"


def _make_nudge(pet_id, category: str, priority: str, title: str, message: str,
                mandatory: bool = False, icon: str | None = None,
                source: str = "record", trigger_type: str = NUDGE_TRIGGER_CRON) -> Nudge:
    """Create a Nudge object (not yet added to session)."""
    return Nudge(
        pet_id=pet_id,
        category=category,
        priority=priority,
        icon=icon,
        title=title,
        message=message,
        mandatory=mandatory,
        source=source,
        trigger_type=trigger_type,
    )


# ──────────────────────────────────────────────────────────────────
# Category generators
# ──────────────────────────────────────────────────────────────────

def _generate_vaccine_nudges(db: Session, pet_id, pet_name: str, species: str) -> list[Nudge]:
    """Generate nudges for overdue/upcoming/missing vaccines."""
    nudges = []
    today = date.today()
    preventive_repo = PreventiveRepository(db)
    master_repo = PreventiveMasterRepository(db)

    records = preventive_repo.find_active_by_pet_id(pet_id)

    for rec in records:
        item_name = _record_item_name(rec)
        if _classify_item(item_name) != "vaccine":
            continue

        if rec.status == "overdue":
            nudges.append(_make_nudge(
                pet_id, "vaccine", "urgent",
                f"{item_name} is overdue",
                f"{pet_name}'s {item_name} is past due. Please schedule it soon.",
                mandatory=True, icon="💉",
            ))
        elif rec.next_due_date and (rec.next_due_date - today).days <= 7 and rec.status != "up_to_date":
            nudges.append(_make_nudge(
                pet_id, "vaccine", "high",
                f"{item_name} due soon",
                f"{pet_name}'s {item_name} is due within 7 days.",
                icon="💉",
            ))

    masters = master_repo.find_by_species(species)
    recorded_master_ids = {r.preventive_master_id for r in records}
    for m in masters:
        if _classify_item(m.item_name) == "vaccine" and m.id not in recorded_master_ids:
            nudges.append(_make_nudge(
                pet_id, "vaccine", "medium",
                f"No {m.item_name} record",
                f"We have no record of {m.item_name} for {pet_name}. Upload a document or update manually.",
                icon="💉",
            ))

    return nudges


def _get_medicine_warning(medicine_name: str | None, db: Session) -> str:
    """Return a warning suffix from product_medicines.notes for the given medicine.

    Returns an empty string when medicine_name is absent or not found in catalog.
    Only TOXIC warnings (e.g., "TOXIC TO CATS") are included in nudge messages.
    """
    if not medicine_name:
        return ""
    try:
        med = PreventiveMasterRepository(db).find_medicine_by_name_ilike(medicine_name)
        if med and med.notes and "toxic" in med.notes.lower():
            return f" ⚠️ {med.notes}"
    except Exception:
        pass
    return ""


def _generate_deworming_nudges(db: Session, pet_id, pet_name: str, species: str) -> list[Nudge]:
    """Generate nudges for overdue/upcoming deworming."""
    nudges = []
    today = date.today()
    records = PreventiveRepository(db).find_active_by_pet_id(pet_id)

    for rec in records:
        item_name = _record_item_name(rec)
        if _classify_item(item_name) != "deworming":
            continue

        warning = _get_medicine_warning(rec.medicine_name, db)
        if rec.status == "overdue":
            nudges.append(_make_nudge(
                pet_id, "deworming", "urgent",
                f"{item_name} is overdue",
                f"{pet_name}'s {item_name} is past due.{warning}",
                mandatory=True, icon="💊",
            ))
        elif rec.next_due_date and (rec.next_due_date - today).days <= 7 and rec.status != "up_to_date":
            nudges.append(_make_nudge(
                pet_id, "deworming", "high",
                f"{item_name} due soon",
                f"{pet_name}'s {item_name} is due within 7 days.{warning}",
                icon="💊",
            ))

    return nudges


def _generate_flea_nudges(db: Session, pet_id, pet_name: str, species: str) -> list[Nudge]:
    """Generate nudges for overdue/upcoming flea & tick treatment."""
    nudges = []
    today = date.today()
    records = PreventiveRepository(db).find_active_by_pet_id(pet_id)

    for rec in records:
        item_name = _record_item_name(rec)
        if _classify_item(item_name) != "flea":
            continue

        warning = _get_medicine_warning(rec.medicine_name, db)
        if rec.status == "overdue":
            nudges.append(_make_nudge(
                pet_id, "flea", "urgent",
                f"{item_name} is overdue",
                f"{pet_name}'s {item_name} is past due.{warning}",
                icon="🐛",
            ))
        elif rec.next_due_date and (rec.next_due_date - today).days <= 7 and rec.status != "up_to_date":
            nudges.append(_make_nudge(
                pet_id, "flea", "high",
                f"{item_name} due soon",
                f"{pet_name}'s {item_name} is due within 7 days.{warning}",
                icon="🐛",
            ))

    return nudges


def _generate_condition_nudges(db: Session, pet_id, pet_name: str) -> list[Nudge]:
    """Generate nudges for medication refills and monitoring tasks."""
    nudges = []
    today = date.today()

    conditions = HealthRepository(db).find_active_conditions(pet_id)

    for cond in conditions:
        # Medication refill nudges
        for med in cond.medications:
            if med.status != "active":
                continue
            if med.refill_due_date and med.refill_due_date <= today:
                nudges.append(_make_nudge(
                    pet_id, "condition", "urgent",
                    f"Refill {med.name}",
                    f"{pet_name}'s {med.name} for {cond.name} needs a refill.",
                    mandatory=True, icon="💊",
                ))

        # Monitoring overdue nudges
        for mon in cond.monitoring:
            if mon.next_due_date and mon.next_due_date < today:
                nudges.append(_make_nudge(
                    pet_id, "condition", "high",
                    f"{mon.name} overdue for {cond.name}",
                    f"{pet_name}'s {mon.name} monitoring for {cond.name} is overdue.",
                    icon="📋",
                ))

        # No vet visit > 180 days
        last_monitoring = None
        for mon in cond.monitoring:
            if mon.last_done_date:
                if last_monitoring is None or mon.last_done_date > last_monitoring:
                    last_monitoring = mon.last_done_date

        if last_monitoring and (today - last_monitoring).days > 180:
            nudges.append(_make_nudge(
                pet_id, "condition", "medium",
                f"Schedule vet visit for {cond.name}",
                f"No vet check for {cond.name} in over 6 months.",
                icon="🏥",
            ))

    return nudges


def _generate_nutrition_nudges(db: Session, pet_id, pet_name: str) -> list[Nudge]:
    """Generate nudges for missing diet data or nutrition gaps."""
    nudges = []

    if not DietRepository(db).has_diet(pet_id):
        nudges.append(_make_nudge(
            pet_id, "nutrition", "high",
            "Add diet information",
            f"No diet data recorded for {pet_name}. Add food items to get nutrition insights.",
            icon="🍽️",
        ))

    return nudges


def _generate_grooming_nudges(db: Session, pet_id, pet_name: str) -> list[Nudge]:
    """Generate nudges for overdue grooming tasks."""
    nudges = []
    today = date.today()

    prefs = CareRepository(db).find_hygiene_preferences_list(pet_id)

    for pref in prefs:
        if not pref.last_done:
            continue
        # Parse last_done (DD/MM/YYYY format)
        try:
            parts = pref.last_done.split("/")
            last_done = date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            continue

        # Calculate expected interval in days
        freq_days = _freq_to_days(pref.freq, pref.unit)
        if freq_days and (today - last_done).days > freq_days:
            display_name = pref.name or pref.item_id
            nudges.append(_make_nudge(
                pet_id, "grooming", "medium",
                f"{display_name} overdue",
                f"{pet_name}'s {display_name} is past the scheduled frequency.",
                icon="✂️",
            ))

    return nudges


def _freq_to_days(freq: int, unit: str) -> int | None:
    """Convert frequency + unit to approximate days."""
    multipliers = {"day": 1, "week": 7, "month": 30, "year": 365}
    m = multipliers.get(unit)
    if m is None or freq <= 0:
        return None
    return freq * m


def _generate_checkup_nudges(db: Session, pet_id, pet_name: str) -> list[Nudge]:
    """Generate nudges for blood test and full panel intervals."""
    nudges = []
    today = date.today()

    care_repo = CareRepository(db)
    last_blood_test = care_repo.find_last_diagnostic(pet_id, test_type="blood")
    latest_blood = last_blood_test.observed_at if last_blood_test else None

    blood_interval = get_nudge_config_int(db, "checkup_blood_test_interval_days", 365)
    panel_interval = get_nudge_config_int(db, "checkup_full_panel_interval_days", 365)

    if latest_blood:
        days_since = (today - latest_blood).days
        if days_since > blood_interval:
            nudges.append(_make_nudge(
                pet_id, "checkup", "high",
                "Blood test recommended",
                f"{pet_name} hasn't had a blood test in {days_since} days.",
                icon="🩸",
            ))
    else:
        # No blood test on record at all — urgent priority
        nudges.append(_make_nudge(
            pet_id, "checkup", "urgent",
            "No blood test on record",
            f"Consider scheduling a blood test for {pet_name}.",
            icon="🩸",
        ))

    checkup_records = PreventiveRepository(db).find_active_by_pet_id(pet_id)
    latest_checkup_date = None
    for rec in checkup_records:
        item_name = _record_item_name(rec)
        if _classify_item(item_name) == "checkup":
            if rec.last_done_date:
                if latest_checkup_date is None or rec.last_done_date > latest_checkup_date:
                    latest_checkup_date = rec.last_done_date

    if latest_checkup_date and (today - latest_checkup_date).days > panel_interval:
        nudges.append(_make_nudge(
            pet_id, "checkup", "medium",
            "Full preventive panel due",
            f"{pet_name}'s last full checkup was over {panel_interval} days ago.",
            icon="📋",
        ))

    return nudges


# ──────────────────────────────────────────────────────────────────
# Sorting
# ──────────────────────────────────────────────────────────────────

def _sort_nudges(nudges: list[Nudge]) -> list[Nudge]:
    """Sort nudges: mandatory first → source (record > ai) → priority (urgent > high > medium)."""
    return sorted(nudges, key=lambda n: (
        0 if n.mandatory else 1,
        NUDGE_SOURCE_ORDER.get(n.source or "record", 9),
        NUDGE_PRIORITY_ORDER.get(n.priority, 9),
    ))


# ──────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────

def generate_nudges(db: Session, pet_id) -> list[dict]:
    """
    Generate nudges for a single pet (dashboard endpoint).

    Returns cached nudges if fresh (< NUDGE_CACHE_HOURS old),
    otherwise regenerates from all 7 category generators.
    """
    nudge_repo = NudgeRepository(db)
    cache_cutoff = datetime.now(timezone.utc) - timedelta(hours=NUDGE_CACHE_HOURS)

    fresh_count = nudge_repo.count_fresh(pet_id, cache_cutoff)
    if fresh_count > 0:
        existing = nudge_repo.find_active_for_pet(pet_id)
        return [_nudge_to_dict(n) for n in _sort_nudges(existing)]

    pet = PetRepository(db).get_by_id(pet_id)
    if not pet or pet.is_deleted:
        return []

    return _regenerate_nudges_for_pet(db, pet)


def _regenerate_nudges_for_pet(db: Session, pet: Pet) -> list[dict]:
    """Run all 7 generators, dedup, persist, and return sorted nudges."""
    pet_id = pet.id
    pet_name = pet.name
    species = pet.species
    nudge_repo = NudgeRepository(db)

    new_nudges: list[Nudge] = []
    new_nudges.extend(_generate_vaccine_nudges(db, pet_id, pet_name, species))
    new_nudges.extend(_generate_deworming_nudges(db, pet_id, pet_name, species))
    new_nudges.extend(_generate_flea_nudges(db, pet_id, pet_name, species))
    new_nudges.extend(_generate_condition_nudges(db, pet_id, pet_name))
    new_nudges.extend(_generate_nutrition_nudges(db, pet_id, pet_name))
    new_nudges.extend(_generate_grooming_nudges(db, pet_id, pet_name))
    new_nudges.extend(_generate_checkup_nudges(db, pet_id, pet_name))

    existing = nudge_repo.find_active_for_pet(pet_id)
    existing_keys = {(str(n.pet_id), n.category, n.title) for n in existing}

    inserted = 0
    for nudge in new_nudges:
        key = (str(nudge.pet_id), nudge.category, nudge.title)
        if key not in existing_keys:
            nudge_repo.create(nudge)
            existing.append(nudge)
            existing_keys.add(key)
            inserted += 1

    if inserted > 0:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist nudges for pet %s", pet_id)
            return [_nudge_to_dict(n) for n in _sort_nudges(existing)]

    return [_nudge_to_dict(n) for n in _sort_nudges(existing)]


def run_nudge_engine(db: Session) -> dict:
    """
    Daily cron entry point — regenerate nudges for all active pets.

    Returns summary dict with counts.
    """
    pets = PetRepository(db).find_onboarded_active()

    total_generated = 0
    errors = 0

    for pet in pets:
        try:
            nudges = _regenerate_nudges_for_pet(db, pet)
            total_generated += len(nudges)
        except Exception:
            logger.exception("Nudge engine failed for pet %s", pet.id)
            errors += 1

    logger.info(
        "Nudge engine complete: %d pets processed, %d total nudges, %d errors",
        len(pets), total_generated, errors,
    )

    return {
        "pets_processed": len(pets),
        "total_nudges": total_generated,
        "errors": errors,
    }


def _nudge_to_dict(nudge: Nudge) -> dict:
    """Serialize a Nudge to a dict for API response."""
    return {
        "id": str(nudge.id),
        "category": nudge.category,
        "priority": nudge.priority,
        "icon": nudge.icon,
        "title": nudge.title,
        "message": nudge.message,
        "mandatory": nudge.mandatory,
        "orderable": nudge.orderable,
        "price": nudge.price,
        "order_type": nudge.order_type,
        "cart_item_id": nudge.cart_item_id,
        "dismissed": nudge.dismissed,
        "acted_on": nudge.acted_on or False,
        "source": nudge.source or "record",
        "trigger_type": nudge.trigger_type or "cron",
        "created_at": nudge.created_at.isoformat() if nudge.created_at else None,
    }
