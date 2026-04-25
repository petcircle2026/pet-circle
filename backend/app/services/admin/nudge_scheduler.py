"""
PetCircle Phase 1 — Nudge Scheduler Service (Excel v5)

Drives WhatsApp nudge delivery for the Level 0/1/2 user system.
Called by the daily 8 AM IST cron AFTER reminder_engine completes.

Architecture (Option A — replaces nudge_sender.py for WA delivery):
    - nudge_scheduler.py  → WhatsApp nudge sends (this file)
    - nudge_engine.py     → Dashboard nudge generation (unchanged)
    - nudge_sender.py     → WA sending removed (kept for record_nudge_engagement)

Levels:
    Level 0 — breed not set OR breed set but no preventive_records
    Level 1 — breed set, no preventive_records
    Level 2 — breed set + at least 1 preventive_record

O+N Schedule (onboarding day = onboarding_completed_at.date()):
    Slots: [1, 5, 10, 20, 30], then every 30 days (post-schedule)

Rules:
    - Skip if any reminder was sent today for any pet of this user.
    - Skip if any nudge was sent in the last NUDGE_MIN_GAP_HOURS hours.
    - Max 1 nudge per user per day.
    - On level transition (N7): reset slot counter, start from slot 1.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.constants import (
    NUDGE_INACTIVITY_TRIGGER_HOURS,
    NUDGE_L2_DATA_PRIORITY,
    NUDGE_LEVEL_0,
    NUDGE_LEVEL_1,
    NUDGE_LEVEL_2,
    NUDGE_MAX_PER_WEEK,
    NUDGE_MIN_GAP_HOURS,
    NUDGE_POST_SCHEDULE_INTERVAL_DAYS,
    NUDGE_SCHEDULE_DAYS,
    OPENAI_QUERY_MODEL,
)
from app.core.encryption import decrypt_field
from app.core.log_sanitizer import mask_phone
from app.models.cache.nudge_delivery_log import NudgeDeliveryLog
from app.models.pet import Pet
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.care_repository import CareRepository
from app.repositories.diet_repository import DietRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.health_repository import HealthRepository
from app.repositories.nudge_repository import NudgeRepository
from app.repositories.pet_repository import PetRepository
from app.repositories.preventive_master_repository import PreventiveMasterRepository
from app.repositories.preventive_repository import PreventiveRepository
from app.repositories.reminder_repository import ReminderRepository
from app.repositories.user_repository import UserRepository
from app.utils.date_utils import get_today_ist

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_nudge_scheduler(db: Session) -> dict:
    """
    Main entry point — called by the daily cron after reminder_engine.

    For each active user with onboarding_completed_at set:
        1. Determine nudge level
        2. Check send guards (reminder sent today, min gap, etc.)
        3. Select next slot message
        4. Send WA template
        5. Log to nudge_delivery_log

    Returns summary dict: {sent, skipped, failed}.
    """
    from app.services.whatsapp.whatsapp_sender import send_template_message

    today = get_today_ist()
    sent = skipped = failed = 0

    user_repo = UserRepository(db)
    pet_repo = PetRepository(db)

    users = user_repo.find_onboarded_active()

    for user in users:
        try:
            pets = pet_repo.find_by_user_id(user.id)
            if not pets:
                continue

            # Use first pet for level calculation and message context.
            # (Per-pet nudges are a future enhancement — v1 is per-user.)
            primary_pet = pets[0]

            level = calculate_nudge_level(db, user, primary_pet)

            # --- Guard: reminder sent today? ---
            reminder_today = _reminder_sent_today(db, user.id, today)
            if reminder_today:
                logger.info("Nudge skipped for user %s: reason=%s", str(user.id), "reminder_sent_today")
                skipped += 1
                continue

            # --- Guard: reminder scheduled today (pending)? ---
            reminder_scheduled_today = _has_reminder_scheduled_today(db, user.id, today)
            if reminder_scheduled_today:
                logger.info("Nudge skipped for user %s: reason=%s", str(user.id), "reminder_scheduled_today")
                skipped += 1
                continue

            # --- Guard: max nudges in rolling 7-day window? ---
            nudge_count_7d = _count_nudges_in_window(db, user.id)
            if nudge_count_7d >= NUDGE_MAX_PER_WEEK:
                logger.info("Nudge skipped for user %s: reason=%s", str(user.id), "7day_cap")
                skipped += 1
                continue

            # --- Guard: nudge sent recently (48h gap)? ---
            last_nudge_at = _last_nudge_sent_at(db, user.id)
            if last_nudge_at:
                gap = datetime.now(timezone.utc) - last_nudge_at
                if gap.total_seconds() < NUDGE_MIN_GAP_HOURS * 3600:
                    logger.info("Nudge skipped for user %s: reason=%s", str(user.id), "min_gap_48h")
                    skipped += 1
                    continue

            # --- Detect level-up and reset slot counter ---
            _handle_level_transition(db, user, level)

            # --- Select next message ---
            message_info = _select_next_message(db, user, primary_pet, level, today)
            if not message_info:
                inactivity_triggered = _check_inactivity_trigger(db, user)
                if not inactivity_triggered:
                    logger.info("Nudge skipped for user %s: reason=%s", str(user.id), "not_scheduled_and_recently_active")
                    skipped += 1
                    continue

                message_info = _select_next_message(
                    db,
                    user,
                    primary_pet,
                    level,
                    today,
                    ignore_schedule=True,
                )
                if not message_info:
                    logger.info("Nudge skipped for user %s: reason=%s", str(user.id), "inactivity_trigger_no_message_available")
                    skipped += 1
                    continue

            template_key, vars_ = message_info

            if not template_key:
                logger.info("Nudge skipped for user %s: reason=%s", str(user.id), "missing_template_key")
                skipped += 1
                continue

            # --- Send WhatsApp template ---
            plaintext_mobile = decrypt_field(user.mobile_number)
            result = await send_template_message(
                db=db,
                to_number=plaintext_mobile,
                template_name=template_key,
                parameters=vars_,
            )

            if result:
                _log_nudge_delivery(db, user, primary_pet, template_key, level,
                                    template_params=vars_)
                sent += 1
            else:
                failed += 1

        except Exception:
            logger.exception("Nudge scheduler failed for user %s", str(user.id))
            try:
                db.rollback()
            except Exception:
                pass
            failed += 1

    logger.info(
        "Nudge scheduler complete: sent=%d, skipped=%d, failed=%d",
        sent, skipped, failed,
    )
    return {"sent": sent, "skipped": skipped, "failed": failed}


# ---------------------------------------------------------------------------
# Level calculation
# ---------------------------------------------------------------------------

def calculate_nudge_level(db: Session, user: User, pet: Pet) -> int:
    """
    Determine the nudge level for a user/pet pair.

    Level 0: breed not set
    Level 1: breed set, no preventive_records
    Level 2: breed set + at least 1 preventive_record row
    """
    breed = getattr(pet, "breed", None) or ""
    if not breed.strip():
        return NUDGE_LEVEL_0

    if not PreventiveRepository(db).has_any(pet.id):
        return NUDGE_LEVEL_1

    return NUDGE_LEVEL_2


# ---------------------------------------------------------------------------
# Level transition handling (N7)
# ---------------------------------------------------------------------------

def _handle_level_transition(db: Session, user: User, current_level: int) -> None:
    """
    If level has increased since last nudge, reset the slot counter so the
    new level sequence starts from slot 1.

    Stores the last known level in a JSON column (agent_nudge_context) or
    in the nudge_delivery_log. We detect a level-up by comparing current_level
    to the level stored on the most recent delivery log row.
    """
    last_log = NudgeRepository(db).find_last_delivery_log(user.id)
    if not last_log:
        return  # First nudge — no transition possible

    prev_level = getattr(last_log, "nudge_level", None)
    if prev_level is not None and prev_level < current_level:
        # Level increased — clear slot counter by deleting old logs is too destructive.
        # Instead we mark the transition with a sentinel row so _completed_slots()
        # only counts rows since the transition.
        logger.info(
            "Nudge level transition for user %s: %d → %d",
            str(user.id), prev_level, current_level,
        )
        # nudge_delivery_log rows retain level; _completed_slots filters by current level.


# ---------------------------------------------------------------------------
# Slot selection
# ---------------------------------------------------------------------------

def _completed_slots(db: Session, user_id: UUID, level: int) -> int:
    """Count how many nudges have been sent at the given level for slot tracking."""
    return NudgeRepository(db).count_deliveries_by_level(user_id, level)


def _select_next_message(
    db: Session,
    user: User,
    pet: Pet,
    level: int,
    today: date,
    ignore_schedule: bool = False,
) -> tuple[str, list] | None:
    """
    Choose the next nudge message for this user/pet based on level and slot.

    Returns (template_key, parameters_list) or None if nothing to send today.
    """
    o_day = user.onboarding_completed_at.date()
    days_since_o = (today - o_day).days

    completed = _completed_slots(db, user.id, level)

    if level == NUDGE_LEVEL_0:
        return _select_level0_message(db, pet, completed, days_since_o, ignore_schedule=ignore_schedule)
    elif level == NUDGE_LEVEL_1:
        return _select_level1_message(db, pet, completed, days_since_o, ignore_schedule=ignore_schedule)
    else:
        return _select_level2_message(db, user, pet, completed, days_since_o, ignore_schedule=ignore_schedule)


# ---- Level 0 ----

def _select_level0_message(
    db: Session,
    pet: Pet,
    completed: int,
    days_since_o: int,
    ignore_schedule: bool = False,
) -> tuple[str, list] | None:
    """
    Level 0 schedule: Value Add messages at O+1, 5, 10, 20, 30, then cycle.

    Template: WHATSAPP_TEMPLATE_NUDGE_VALUE_ADD_PERSONAL
    {{1}} = pet_name  {{2}} = tip text from nudge_message_library.template_var_1
    """
    slot_days = NUDGE_SCHEDULE_DAYS  # [1, 5, 10, 20, 30]

    if not ignore_schedule:
        if completed < len(slot_days):
            target_day = slot_days[completed]
            if days_since_o < target_day:
                return None  # Not yet time for this slot
        else:
            # Post-schedule: send every 30 days
            if days_since_o < slot_days[-1] + (completed - len(slot_days) + 1) * NUDGE_POST_SCHEDULE_INTERVAL_DAYS:
                return None

    # Pick tip text from the library (level=0, breed='All'), cycling by seq
    master_repo = PreventiveMasterRepository(db)
    lib_row = master_repo.find_nudge_message_by_offset(
        level=0, breed="All", offset=completed % _count_level0_rows(db)
    )

    template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_VALUE_ADD_PERSONAL", None)
    if not template_key or not lib_row:
        return None

    pet_name = pet.name or "your pet"
    tip = lib_row.template_var_1 or ""
    # {{1}} = pet_name, {{2}} = tip, {{3}} = pet_name (used in closing line)
    return (template_key, [pet_name, tip, pet_name])


def _count_level0_rows(db: Session) -> int:
    return max(PreventiveMasterRepository(db).count_nudge_messages(level=0, breed="All"), 1)


# ---- Level 1 ----

_L1_MESSAGE_TYPES = [
    "value_add",        # O+1
    "engagement_only",  # O+5
    "value_add",        # O+10
    "engagement_only",  # O+20
    "breed_only",       # O+30
]


def _select_level1_message(
    db: Session,
    pet: Pet,
    completed: int,
    days_since_o: int,
    ignore_schedule: bool = False,
) -> tuple[str, list] | None:
    """
    Level 1 schedule: mixed types at O+1/5/10/20/30, then cycle.
    """
    slot_days = NUDGE_SCHEDULE_DAYS

    if completed < len(slot_days):
        target_day = slot_days[completed]
        if not ignore_schedule and days_since_o < target_day:
            return None
        msg_type = _L1_MESSAGE_TYPES[completed]
    else:
        if (
            not ignore_schedule
            and days_since_o < slot_days[-1] + (completed - len(slot_days) + 1) * NUDGE_POST_SCHEDULE_INTERVAL_DAYS
        ):
            return None
        msg_type = _L1_MESSAGE_TYPES[completed % len(_L1_MESSAGE_TYPES)]

    return _build_l1_message(db, pet, msg_type)


def _build_l1_message(
    db: Session, pet: Pet, msg_type: str,
) -> tuple[str, list] | None:
    """Build a Level 1 message by looking up the library."""
    breed = (getattr(pet, "breed", None) or "").strip() or "All"

    if msg_type in ("engagement_only", "breed_only"):
        master_repo = PreventiveMasterRepository(db)
        lib_row = None
        for fallback_breed in [breed, "Generic", "All"]:
            lib_row = master_repo.find_nudge_message_by_type(
                level=1, message_type=msg_type, breed=fallback_breed
            )
            if lib_row:
                break

        if not lib_row:
            return None

        var1 = (lib_row.template_var_1 or "").replace("{breed}", breed)
        var2 = lib_row.template_var_2 or ""

        if msg_type == "engagement_only":
            # Use no-breed template when the matched row is a Generic row
            if lib_row.breed == "Generic":
                template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_ENGAGEMENT_NO_BREED", None)
            else:
                template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_ENGAGEMENT", None)
            if not template_key:
                return None
            return (template_key, [var1, var2])

        if msg_type == "breed_only":
            # Use no-breed template when the matched row is a Generic row
            if lib_row.breed == "Generic":
                template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_NO_BREED", None)
            else:
                template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_BREED", None)
            if not template_key:
                return None
            return (template_key, [var1, var2])

    lib_row = PreventiveMasterRepository(db).find_nudge_message_by_type(
        level=1, message_type="value_add", breed="All"
    )
    template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_VALUE_ADD_PERSONAL", None)
    if not template_key or not lib_row:
        return None
    pet_name = pet.name or "your pet"
    tip = lib_row.template_var_1 or ""
    # {{1}} = pet_name, {{2}} = tip, {{3}} = pet_name (used in closing line)
    return (template_key, [pet_name, tip, pet_name])


# ---- Level 2 ----

def _select_level2_message(
    db: Session,
    user: User,
    pet: Pet,
    completed: int,
    days_since_o: int,
    ignore_schedule: bool = False,
) -> tuple[str, list] | None:
    """
    Level 2 schedule:
        Slots 1–3: Breed + Data (top missing category from NUDGE_L2_DATA_PRIORITY)
        Slots 4–5: GPT-personalized personal insight
        Post-slot 5: engagement-based (48h gap enforced in caller)

    N9 topic detection: before each nudge, GPT reads last 3 message_logs +
    last dashboard_visit to re-sequence data priority.
    """
    slot_days = NUDGE_SCHEDULE_DAYS

    if not ignore_schedule:
        if completed < len(slot_days):
            target_day = slot_days[completed]
            if days_since_o < target_day:
                return None
        else:
            # After O+30, Level 2 follows the same 30-day cadence.
            next_day = slot_days[-1] + (completed - len(slot_days) + 1) * NUDGE_POST_SCHEDULE_INTERVAL_DAYS
            if days_since_o < next_day:
                return None

    if completed < 3:
        return _build_breed_data_message(db, pet, completed)
    elif completed < 5:
        return _build_personalized_message(db, user, pet)
    else:
        # Post-schedule: rotate breed+data then personal
        idx = completed % 5
        if idx < 3:
            return _build_breed_data_message(db, pet, idx)
        return _build_personalized_message(db, user, pet)


def _build_breed_data_message(
    db: Session, pet: Pet, slot_idx: int,
) -> tuple[str, list] | None:
    """
    Pick the top missing data category (from NUDGE_L2_DATA_PRIORITY) and
    build a Breed + Data nudge. Uses GPT topic detection (N9) to re-sort.
    """
    breed = (getattr(pet, "breed", None) or "").strip()
    category = _pick_data_category(db, pet, slot_idx)

    # Fallback chain: specific breed → 'Generic' (no-breed rows) → 'All'
    master_repo = PreventiveMasterRepository(db)
    lib_row = None
    fallback_breeds = [breed, "Generic", "All"] if breed else ["Generic", "All"]
    for fallback_breed in fallback_breeds:
        lib_row = master_repo.find_nudge_message_by_type_and_category(
            level=2, message_type="breed_data", breed=fallback_breed, category=category
        )
        if lib_row:
            break

    if not lib_row:
        return None

    pet_name = pet.name or "your pet"

    # No-breed Generic rows use a different template with a different variable order:
    #   {{1}}=insight, {{2}}=pet_name, {{3}}=care_category, {{4}}=CTA
    if lib_row.breed == "Generic":
        template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_BREED_DATA_NO_BREED", None)
        if not template_key:
            return None
        insight = lib_row.template_var_1 or ""
        health_area = lib_row.template_var_3 or category
        cta = lib_row.template_var_4 or ""
        return (template_key, [insight, pet_name, health_area, cta])

    # Breed-specific rows use the standard template:
    #   {{1}}=pet_name, {{2}}=insight, {{3}}=health_area, {{4}}=CTA, {{5}}=breed
    template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_BREED_DATA", None)
    if not template_key:
        return None
    insight = (lib_row.template_var_1 or "").replace("{pet_name}", pet_name)
    health_area = lib_row.template_var_3 or category
    cta = lib_row.template_var_4 or ""
    return (template_key, [pet_name, insight, health_area, cta, breed])


def _category_has_meaningful_data(db: Session, pet: Pet, category: str) -> bool:
    """
    True if the pet already has meaningful data in this nudge category.

    Used by _pick_data_category to skip categories the user has already filled
    so the next-day nudge targets a genuinely missing category instead of
    blindly re-asking for data already provided.

    Defensive: any query error returns False (preserves the existing behavior
    of falling through to the static priority list).
    """
    from app.services.admin.nudge_engine import _classify_item

    try:
        if category in ("vaccine", "flea_tick", "deworming", "grooming"):
            target = {
                "vaccine": "vaccine",
                "flea_tick": "flea",
                "deworming": "deworming",
                "grooming": "grooming",
            }[category]
            records = PreventiveRepository(db).find_with_last_done(pet.id)
            return any(
                _classify_item(r.preventive_master.item_name) == target
                for r in records
                if r.preventive_master
            )

        if category == "nutrition":
            return DietRepository(db).has_food(pet.id)

        if category == "supplement":
            return DietRepository(db).has_supplement(pet.id)

        if category == "condition":
            return HealthRepository(db).has_active_condition(pet.id)

        if category == "medication":
            return HealthRepository(db).has_active_medication(pet.id)

        if category == "diagnostics":
            return CareRepository(db).has_any_diagnostic(pet.id)

    except Exception:
        logger.debug(
            "meaningful-data check failed pet=%s cat=%s", str(pet.id), category,
        )
        return False

    return False


def _pick_data_category(db: Session, pet: Pet, slot_idx: int) -> str:
    """
    Return the highest-priority missing data category for Level 2 nudges.

    Selection order:
        1. Urgent/high-priority nudge detection (vaccine→deworming→flea→…).
        2. Walk NUDGE_L2_DATA_PRIORITY and return the first category where
           the pet has NO meaningful data yet. This avoids nudging for
           categories the user has already filled in (e.g. asking for
           vaccine info the day after they provided it).
        3. Final fallback: static slot-index lookup (preserves prior
           behavior when every category is already populated).
    """
    # 1. Urgent/high detection — unchanged.
    try:
        detected_category = _detect_topic_from_health_data(db, pet)
        if detected_category:
            return detected_category
    except Exception:
        logger.debug("Health data topic detection skipped for pet %s", str(pet.id))

    # 2. Walk the priority list, skipping categories that already have data.
    for cat in NUDGE_L2_DATA_PRIORITY:
        if not _category_has_meaningful_data(db, pet, cat):
            return cat

    # 3. Every category already has data — preserve the slot-based fallback.
    if slot_idx < len(NUDGE_L2_DATA_PRIORITY):
        return NUDGE_L2_DATA_PRIORITY[slot_idx]
    return NUDGE_L2_DATA_PRIORITY[-1]


def _detect_topic_from_health_data(db: Session, pet: Pet) -> str | None:
    """
    Deterministically pick the highest-priority data category for Level 2 nudges
    based on the pet's actual health gaps.

    Runs each nudge generator and returns the category of the first urgent/high
    nudge found. Falls back to NUDGE_L2_DATA_PRIORITY in _pick_data_category if
    no urgent items exist.

    Priority order: vaccine → deworming → flea → condition → nutrition → checkup
    Within each: urgent > high priority nudges trigger the category.
    """
    from app.services.admin.nudge_engine import (
        _generate_checkup_nudges,
        _generate_condition_nudges,
        _generate_deworming_nudges,
        _generate_flea_nudges,
        _generate_nutrition_nudges,
        _generate_vaccine_nudges,
    )

    category_map = {
        "vaccine": "vaccine",
        "deworming": "deworming",
        "flea": "flea",
        "condition": "conditions",
        "nutrition": "nutrition",
        "checkup": "checkup",
    }

    pet_name = pet.name or ""
    species = pet.species or ""

    generators = [
        ("vaccine",   lambda: _generate_vaccine_nudges(db, pet.id, pet_name, species)),
        ("deworming", lambda: _generate_deworming_nudges(db, pet.id, pet_name, species)),
        ("flea",      lambda: _generate_flea_nudges(db, pet.id, pet_name, species)),
        ("condition", lambda: _generate_condition_nudges(db, pet.id, pet_name)),
        ("nutrition", lambda: _generate_nutrition_nudges(db, pet.id, pet_name)),
        ("checkup",   lambda: _generate_checkup_nudges(db, pet.id, pet_name)),
    ]

    for cat_key, gen in generators:
        try:
            nudges = gen()
            if any(n.priority in ("urgent", "high") for n in nudges):
                return category_map.get(cat_key, cat_key)
        except Exception:
            logger.debug("Health data topic detection failed for category %s pet %s", cat_key, str(pet.id))

    return None


def _build_personalized_message(
    db: Session, user: User, pet: Pet,
) -> tuple[str, list] | None:
    """
    Slots 4–5 (OQ3): GPT-generated personal insight.

    Generates or retrieves a cached insight from pet_ai_insights table,
    then sends using WHATSAPP_TEMPLATE_NUDGE_VALUE_ADD_PERSONAL.
    """
    template_key = getattr(settings, "WHATSAPP_TEMPLATE_NUDGE_VALUE_ADD_PERSONAL", None)
    if not template_key:
        return None

    insight = _get_or_generate_nudge_insight(db, user, pet)
    if not insight:
        return None

    pet_name = pet.name or "your pet"
    # {{1}} = pet_name, {{2}} = insight, {{3}} = pet_name (used in closing line)
    return (template_key, [pet_name, insight, pet_name])


def _get_or_generate_nudge_insight(db: Session, user: User, pet: Pet) -> str | None:
    """
    Retrieve or generate a GPT insight for personalized Level 2 nudge slots.

    Saves to pet_ai_insights with insight_type='nudge_personal' for caching.
    Cache TTL: 30 days.
    """
    from app.models.pet_ai_insight import PetAiInsight

    INSIGHT_TYPE = "nudge_personal"
    CACHE_DAYS = 30

    audit_repo = AuditRepository(db)
    existing = audit_repo.find_latest_insight_by_type(pet.id, INSIGHT_TYPE)

    if existing:
        age = (datetime.now(timezone.utc) - existing.created_at).days
        if age < CACHE_DAYS:
            return existing.insight_text

    # Generate new insight via GPT
    from app.core.constants import AI_PROVIDER
    if AI_PROVIDER == "openai":
        if not getattr(settings, "OPENAI_API_KEY", None):
            return None
    else:
        if not getattr(settings, "ANTHROPIC_API_KEY", None):
            return None

    breed = getattr(pet, "breed", None) or "unknown breed"
    weight = getattr(pet, "weight_kg", None)
    weight_str = f"{weight} kg" if weight else "unknown weight"

    prompt = (
        f"Write a single warm, 1-2 sentence WhatsApp message for a pet owner. "
        f"It should be an interesting, personalized health or care insight for their {breed} "
        f"weighing {weight_str}. Be specific to the breed. "
        f"Do NOT start with 'Hi' or include the pet's name — that's added separately. "
        f"Keep it under 100 words."
    )

    try:
        from app.utils.ai_client import get_sync_ai_client  # noqa: PLC0415
        client = get_sync_ai_client()
        resp = client.messages.create(
            model=OPENAI_QUERY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.7,
        )
        insight_text = resp.content[0].text.strip()

        row = PetAiInsight(
            pet_id=pet.id,
            insight_type=INSIGHT_TYPE,
            insight_text=insight_text,
        )
        AuditRepository(db).log_ai_insight(row)
        db.commit()
        return insight_text

    except Exception:
        logger.exception("GPT nudge insight generation failed for pet %s", str(pet.id))
        return None


# ---------------------------------------------------------------------------
# Delivery logging
# ---------------------------------------------------------------------------

def _log_nudge_delivery(
    db: Session,
    user: User,
    pet: Pet,
    template_key: str,
    level: int,
    template_params: list | None = None,
) -> None:
    """
    Write a row to nudge_delivery_log to track slot progress, level, and full message.

    Args:
        template_key:    Resolved WhatsApp template name (e.g. 'petcircle_nudge_breed_v1').
        level:           Nudge level (0/1/2) for slot-counter queries.
        template_params: Interpolated parameter list used in the template send.
    """
    from app.services.whatsapp.whatsapp_sender import get_template_body, render_template_body

    log = NudgeDeliveryLog(
        nudge_id=None,       # Not linked to a dashboard nudge row
        pet_id=pet.id,
        user_id=user.id,
        wa_status="sent",
    )
    # Store level on the log if the model supports it (migration 029 adds nudge_level).
    if hasattr(log, "nudge_level"):
        log.nudge_level = level

    # Persist template details and rendered message body (migration 031).
    log.template_name = template_key
    log.template_params = template_params

    body = get_template_body(db, template_key)
    if body:
        log.message_body = render_template_body(body, template_params or [])

    db.add(log)
    db.commit()


# ---------------------------------------------------------------------------
# Guard helpers
# ---------------------------------------------------------------------------

def _reminder_sent_today(db: Session, user_id: UUID, today: date) -> bool:
    """Return True if any reminder was sent today for any of this user's pets."""
    return ReminderRepository(db).has_sent_today_for_user(user_id, today)


def _has_reminder_scheduled_today(db: Session, user_id: UUID, today: date) -> bool:
    """Return True if any reminder is pending today for this user."""
    return ReminderRepository(db).has_pending_today_for_user(user_id, today)


def _count_nudges_in_window(db: Session, user_id: UUID, window_days: int = 7) -> int:
    """Return sent nudge count in a rolling UTC window for this user."""
    return NudgeRepository(db).count_deliveries_in_window(user_id, window_days)


def _check_inactivity_trigger(db: Session, user: User) -> bool:
    """Return True when the user's last message activity exceeds the inactivity threshold."""
    try:
        plaintext_mobile = decrypt_field(user.mobile_number)
    except Exception:
        logger.warning("Inactivity check failed to decrypt mobile for user %s", str(user.id))
        return False

    masked_mobile = mask_phone(plaintext_mobile)
    last_activity = DocumentRepository(db).find_last_message_activity(masked_mobile)
    if not last_activity:
        return True

    inactivity_gap = datetime.now(timezone.utc) - last_activity
    return inactivity_gap.total_seconds() >= NUDGE_INACTIVITY_TRIGGER_HOURS * 3600


def _last_nudge_sent_at(db: Session, user_id: UUID) -> datetime | None:
    """Return the sent_at timestamp of the most recent nudge for this user."""
    return NudgeRepository(db).find_last_sent_at(user_id)
