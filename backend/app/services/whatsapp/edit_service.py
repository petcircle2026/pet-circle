"""
PetCircle — Deterministic Edit Service (State Machine)

State-machine-driven post-onboarding profile editor via WhatsApp.
No LLM calls — every step is a fixed menu or value prompt.

Architecture:
    user.edit_state  = "editing"   (constant — keeps router routing here)
    user.edit_data   = {
        "step": str,            # current step name
        "selected_pet_id": str, # UUID string, None until pet is selected
        "ctx": dict,            # step-specific context (item IDs, field names, etc.)
    }

IMPORTANT — JSONB mutation tracking:
    SQLAlchemy does not auto-detect in-place mutations on JSONB columns.
    Always call flag_modified(user, "edit_data") before db.commit() when
    mutating user.edit_data.
"""

import asyncio
import logging
import re
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.repositories.pet_repository import PetRepository
from app.repositories.diet_item_repository import DietItemRepository
from app.repositories.preventive_repository import PreventiveRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.custom_preventive_item_repository import CustomPreventiveItemRepository
from app.repositories.reminder_repository import ReminderRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category menu text + direct-dispatch detection
# ---------------------------------------------------------------------------

_CAT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "1": (  # Pet Profile
        "update name", "change name", "update breed", "change breed",
        "update weight", "change weight", "update age", "change age",
        "update birthday", "change birthday", "update gender", "change gender",
        "update neutered", "update spayed", "update pet profile", "change pet profile",
        "update my pet's", "change my pet's",
    ),
    "2": (  # Diet & Nutrition
        "add food", "add diet", "update diet", "change diet",
        "update food", "change food", "update my diet", "change my diet",
        "add my diet", "add nutrition", "update nutrition",
    ),
    "3": (  # Preventive Care
        "add vaccine", "update vaccine", "add vaccination", "update vaccination",
        "add deworming", "update deworming", "add preventive", "update preventive",
        "add tick", "add flea", "update tick", "update flea",
    ),
    "4": (  # Conditions
        "add condition", "update condition", "add health condition",
        "add medical condition", "new condition",
    ),
    "5": (  # Reminders
        "update reminder", "change reminder", "snooze reminder", "edit reminder",
    ),
    "6": (  # RX Medicines
        "add medicine", "add medication", "add rx", "add prescription",
        "add my medicine", "add my medication", "new medicine", "new medication",
    ),
    "7": (  # Contacts
        "add vet", "add my vet", "add a vet", "update vet", "change vet",
        "add contact", "add my contact", "add a contact", "add new contact",
        "update contact", "change contact", "vet contact", "my vet name",
        "add vet name", "add my vet name",
    ),
    "8": (  # Owner Name
        "update my name", "change my name", "fix my name", "correct my name",
        "update owner name", "change owner name",
    ),
}


def _detect_edit_category(text_lower: str) -> str | None:
    """Return the _CAT_MAP key (1–8) if the message unambiguously maps to one category."""
    for cat_num, phrases in _CAT_KEYWORDS.items():
        for phrase in phrases:
            if phrase in text_lower:
                return cat_num
    return None

_CAT_MENU = (
    "What would you like to update? Reply with a number:\n\n"
    "1. Pet Profile (name, breed, weight, etc.)\n"
    "2. Diet & Nutrition\n"
    "3. Preventive Care (vaccines, deworming)\n"
    "4. Conditions\n"
    "5. Reminders\n"
    "6. RX Medicines\n"
    "7. Contacts (vet, groomer)\n"
    "8. Your Name\n\n"
    "Type *cancel* to exit."
)

_CAT_MAP = {
    "1": "pet_profile",
    "2": "diet",
    "3": "preventive",
    "4": "conditions",
    "5": "reminders",
    "6": "rx_medicines",
    "7": "contacts",
    "8": "owner_name",
}


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def _get_mobile(user) -> str:
    from app.core.encryption import decrypt_field

    cached = getattr(user, "_plaintext_mobile", None)
    if cached:
        return cached
    return decrypt_field(user.mobile_number)


def _set_step(user, db: Session, step: str, ctx: dict | None = None) -> None:
    if user.edit_data is None:
        user.edit_data = {}
    user.edit_data["step"] = step
    if ctx is not None:
        user.edit_data["ctx"] = ctx
    elif "ctx" not in user.edit_data:
        user.edit_data["ctx"] = {}
    flag_modified(user, "edit_data")
    try:
        db.commit()
    except Exception as exc:
        logger.error("edit_service: set_step %s error: %s", step, exc)
        db.rollback()


def _update_ctx(user, db: Session, **kwargs) -> None:
    if user.edit_data is None:
        user.edit_data = {}
    if "ctx" not in user.edit_data:
        user.edit_data["ctx"] = {}
    user.edit_data["ctx"].update(kwargs)
    flag_modified(user, "edit_data")
    try:
        db.commit()
    except Exception as exc:
        logger.error("edit_service: update_ctx error: %s", exc)
        db.rollback()


def _clear_state(user, db: Session) -> None:
    user.edit_state = None
    user.edit_data = None
    try:
        db.commit()
    except Exception as exc:
        logger.error("edit_service: clear_state error: %s", exc)
        db.rollback()


def _schedule_precompute(pet_id_str: str) -> None:
    try:
        from app.services.shared.precompute_service import precompute_dashboard_enrichments
        asyncio.create_task(precompute_dashboard_enrichments(pet_id_str))
    except Exception as exc:
        logger.warning("edit_service: precompute failed for pet %s: %s", pet_id_str, exc)


async def _send_done(db: Session, user, pet, summary: str, send_text_message) -> None:
    from app.config import settings
    from app.services.whatsapp.onboarding import get_or_create_active_dashboard_token

    mobile = _get_mobile(user)
    try:
        token = get_or_create_active_dashboard_token(db, pet.id)
        dashboard_url = f"{settings.FRONTEND_URL}/dashboard/{token}"
        msg = (
            f"Done! {summary}\n\n"
            f"View {pet.name}’s updated profile:\n"
            f"{dashboard_url}\n\n"
            f"\U0001f4cc Tip: Pin this message to always access {pet.name}’s care plan link."
        )
        await send_text_message(db, mobile, msg)
    except Exception as exc:
        logger.error("edit_service: _send_done error: %s", exc)
        await send_text_message(
            db, mobile,
            f"Done! {summary}\n\nSend *dashboard* anytime for the updated profile link.",
        )
    finally:
        _clear_state(user, db)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.strptime(value, "%d %B %Y").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(value, "%d %b %Y").date()
    except ValueError:
        pass
    return None


def _parse_age_or_dob(value: str) -> tuple[date | None, str | None]:
    explicit_date = _parse_date(value)
    if explicit_date:
        today = date.today()
        diff_years = (today - explicit_date).days / 365.25
        if diff_years < 1:
            months = int((today - explicit_date).days / 30.44)
            age_text = f"{months} months"
        else:
            age_text = f"{diff_years:.1f} years".replace(".0 ", " ")
        return explicit_date, age_text

    v = value.lower().strip()
    life_stage_years = {
        "puppy": 0.5, "kitten": 0.5, "junior": 1.5,
        "adult": 4.0, "mature": 8.0, "senior": 10.0, "geriatric": 13.0,
    }
    for stage, years in life_stage_years.items():
        if stage in v:
            dob = date.today() - timedelta(days=int(years * 365.25))
            return dob, value

    total_days = 0
    year_match = re.search(r"(\d+)\s*year", v)
    month_match = re.search(r"(\d+)\s*month", v)
    if year_match:
        total_days += int(year_match.group(1)) * 365
    if month_match:
        total_days += int(month_match.group(1)) * 30
    if total_days > 0:
        dob = date.today() - timedelta(days=total_days)
        return dob, value

    return None, None


def _parse_gender(value: str) -> str | None:
    v = value.lower().strip()
    if v in ("male", "m", "boy", "he", "him", "unneutered male", "male dog", "male cat"):
        return "male"
    if v in ("female", "f", "girl", "she", "her", "female dog", "female cat"):
        return "female"
    return None


def _parse_bool(value: str) -> bool | None:
    v = value.lower().strip()
    if v in ("yes", "y", "true", "1", "neutered", "spayed", "haan", "ha"):
        return True
    if v in ("no", "n", "false", "0", "not neutered", "intact", "nahi", "na"):
        return False
    return None


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def handle_edit_intent(db: Session, user, message_data: dict, send_text_message) -> None:
    """Called when the user triggers the edit flow for the first time."""
    mobile = _get_mobile(user)

    if getattr(user, "edit_state", None) == "editing":
        await handle_edit_step(db, user, message_data, send_text_message)
        return

    pet_repo = PetRepository(db)
    pets = pet_repo.find_by_user_id(user.id)
    if not pets:
        await send_text_message(db, mobile, "No active pets found. Send *add pet* to register one.")
        return

    selected_pet_id = str(pets[0].id) if len(pets) == 1 else None
    initial_step = "cat_select" if selected_pet_id else "pet_select"

    user.edit_state = "editing"
    user.edit_data = {
        "step": initial_step,
        "selected_pet_id": selected_pet_id,
        "ctx": {},
    }
    flag_modified(user, "edit_data")
    try:
        db.commit()
    except Exception as exc:
        logger.error("edit_service: init error: %s", exc)
        db.rollback()
        await send_text_message(db, mobile, "Something went wrong. Please try again.")
        return

    if not selected_pet_id:
        pet_list = "\n".join(f"{i + 1}. {p.name}" for i, p in enumerate(pets))
        await send_text_message(
            db, mobile,
            f"Which pet would you like to update?\n\n{pet_list}\n\nType *cancel* to exit.",
        )
    else:
        text_lower = (message_data.get("text") or "").strip().lower()
        detected = _detect_edit_category(text_lower)
        if detected:
            pet = pets[0]
            await _route_step(db, user, pets, pet, "cat_select", {}, detected, mobile, send_text_message)
        else:
            await send_text_message(db, mobile, _CAT_MENU)


async def handle_edit_step(db: Session, user, message_data: dict, send_text_message) -> None:
    """Process one turn of the deterministic edit flow."""
    mobile = _get_mobile(user)
    text = (message_data.get("text") or "").strip()
    text_lower = text.lower()

    if text_lower in ("cancel", "stop", "exit"):
        _clear_state(user, db)
        await send_text_message(db, mobile, "No changes made. \U0001f43e")
        return

    edit_data = user.edit_data or {"step": "cat_select", "selected_pet_id": None, "ctx": {}}
    step = edit_data.get("step", "cat_select")
    selected_pet_id = edit_data.get("selected_pet_id")
    ctx = edit_data.get("ctx") or {}

    pet_repo = PetRepository(db)
    pets = pet_repo.find_by_user_id(user.id)
    if not pets:
        _clear_state(user, db)
        await send_text_message(db, mobile, "No active pets found.")
        return

    if selected_pet_id:
        pet = next((p for p in pets if str(p.id) == selected_pet_id), pets[0])
    else:
        pet = pets[0]

    await _route_step(db, user, pets, pet, step, ctx, text, mobile, send_text_message)


async def _route_step(db, user, pets, pet, step, ctx, text, mobile, send_text_message):
    """Dispatch to the correct step handler."""
    handlers = {
        "pet_select":           _step_pet_select,
        "cat_select":           _step_cat_select,
        # Pet profile
        "pet_field_select":     _step_pet_field_select,
        "pet_field_val":        _step_pet_field_val,
        # Diet
        "diet_action":          _step_diet_action,
        "diet_add_label":       _step_diet_add_label,
        "diet_add_type":        _step_diet_add_type,
        "diet_add_detail":      _step_diet_add_detail,
        "diet_update_select":   _step_diet_update_select,
        "diet_update_field":    _step_diet_update_field,
        "diet_update_val":      _step_diet_update_val,
        "diet_remove_select":   _step_diet_remove_select,
        # Preventive
        "prev_action":          _step_prev_action,
        "prev_update_select":   _step_prev_update_select,
        "prev_update_field":    _step_prev_update_field,
        "prev_update_date_val": _step_prev_update_date_val,
        "prev_update_med_val":  _step_prev_update_med_val,
        "prev_add_name":        _step_prev_add_name,
        "prev_add_date":        _step_prev_add_date,
        # Conditions
        "cond_name":            _step_cond_name,
        "cond_since":           _step_cond_since,
        # Reminders
        "reminder_select":      _step_reminder_select,
        "reminder_action":      _step_reminder_action,
        "reminder_date_val":    _step_reminder_date_val,
        # RX Medicines
        "rx_name":              _step_rx_name,
        "rx_date":              _step_rx_date,
        # Contacts
        "contact_action":       _step_contact_action,
        "contact_select":       _step_contact_select,
        "contact_field":        _step_contact_field,
        "contact_val":          _step_contact_val,
        "contact_new_name":     _step_contact_new_name,
        "contact_new_role":     _step_contact_new_role,
        "contact_new_phone":    _step_contact_new_phone,
        # Owner name
        "owner_val":            _step_owner_val,
    }
    handler = handlers.get(step)
    if handler:
        await handler(db, user, pets, pet, ctx, text, mobile, send_text_message)
    else:
        logger.warning("edit_service: unknown step '%s'", step)
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, _CAT_MENU)


# ---------------------------------------------------------------------------
# Step: pet select (multi-pet only)
# ---------------------------------------------------------------------------


async def _step_pet_select(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(pets):
            selected = pets[idx]
            user.edit_data["selected_pet_id"] = str(selected.id)
            _set_step(user, db, "cat_select")
            await send_text_message(
                db, mobile,
                f"Got it — updating {selected.name}.\n\n{_CAT_MENU}",
            )
            return
    pet_list = "\n".join(f"{i + 1}. {p.name}" for i, p in enumerate(pets))
    await send_text_message(db, mobile, f"Please reply with the number of your pet:\n\n{pet_list}")


# ---------------------------------------------------------------------------
# Step: category select
# ---------------------------------------------------------------------------


async def _step_cat_select(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if text.lower() in ("back", "menu"):
        await send_text_message(db, mobile, _CAT_MENU)
        return

    cat = _CAT_MAP.get(text.strip())
    if not cat:
        await send_text_message(db, mobile, f"Please reply with a number 1–8.\n\n{_CAT_MENU}")
        return

    if cat == "pet_profile":
        _set_step(user, db, "pet_field_select")
        await send_text_message(
            db, mobile,
            f"Updating {pet.name}’s profile. What would you like to change?\n\n"
            "1. Name\n2. Breed\n3. Weight (kg)\n4. Gender\n5. Age / Birthday\n6. Neutered / Spayed\n\n"
            "Type *back* to see all categories.",
        )

    elif cat == "diet":
        diet_repo = DietItemRepository(db)
        items = diet_repo.find_by_pet(pet.id)
        if items:
            items_display = "\n".join(f"  [{it.type}] {it.label}" for it in items)
        else:
            items_display = "  (none recorded)"
        _set_step(user, db, "diet_action")
        await send_text_message(
            db, mobile,
            f"Current diet for {pet.name}:\n{items_display}\n\n"
            "What would you like to do?\n1. Add new item\n2. Update existing\n3. Remove an item\n\n"
            "Type *back* to see all categories.",
        )

    elif cat == "preventive":
        preventive_repo = PreventiveRepository(db)
        records = preventive_repo.find_with_master_ordered_by_last_done(pet.id, limit=15)
        if records:
            lines = []
            for rec in records:
                item = rec.item
                name = item.item_name if item else "Unknown"
                last = str(rec.last_done_date) if rec.last_done_date else "—"
                lines.append(f"  {name}: {last}")
            items_display = "\n".join(lines)
        else:
            items_display = "  (none recorded)"
        _set_step(user, db, "prev_action")
        await send_text_message(
            db, mobile,
            f"Preventive records for {pet.name}:\n{items_display}\n\n"
            "What would you like to do?\n1. Update a record\n2. Add a custom item\n\n"
            "Type *back* to see all categories.",
        )

    elif cat == "conditions":
        _set_step(user, db, "cond_name")
        await send_text_message(
            db, mobile,
            f"Adding a health condition for {pet.name}.\n\nWhat is the condition name? "
            "(e.g., Diabetes, Hypothyroidism)",
        )

    elif cat == "reminders":
        from app.models.preventive.reminder import Reminder as _Reminder
        reminders = (
            db.query(_Reminder)
            .filter(_Reminder.pet_id == pet.id, _Reminder.status == "pending")
            .order_by(_Reminder.next_due_date)
            .limit(10)
            .all()
        )
        if not reminders:
            await send_text_message(
                db, mobile,
                f"No pending reminders for {pet.name}.\n\n{_CAT_MENU}",
            )
            return
        lines = [
            f"{i + 1}. {r.item_desc or 'Reminder'} — due {r.next_due_date}"
            for i, r in enumerate(reminders)
        ]
        new_ctx = {"reminder_ids": [str(r.id) for r in reminders]}
        _set_step(user, db, "reminder_select", new_ctx)
        await send_text_message(
            db, mobile,
            f"Pending reminders for {pet.name}:\n\n" + "\n".join(lines) + "\n\nWhich reminder? Reply with a number.",
        )

    elif cat == "rx_medicines":
        _set_step(user, db, "rx_name")
        await send_text_message(
            db, mobile,
            f"Adding a prescription medicine reminder for {pet.name}.\n\nWhat is the medicine name?",
        )

    elif cat == "contacts":
        contact_repo = ContactRepository(db)
        contacts = contact_repo.find_by_pet(pet.id)
        if contacts:
            lines = [f"{i + 1}. {c.name} ({c.role})" for i, c in enumerate(contacts)]
            new_ctx = {"contact_ids": [str(c.id) for c in contacts]}
            _set_step(user, db, "contact_action", new_ctx)
            await send_text_message(
                db, mobile,
                f"Contacts for {pet.name}:\n" + "\n".join(lines) + "\n\n1. Update a contact\n2. Add new contact",
            )
        else:
            _set_step(user, db, "contact_new_name")
            await send_text_message(
                db, mobile,
                f"No contacts recorded for {pet.name}. Let’s add one.\n\nWhat is the contact’s name?",
            )

    elif cat == "owner_name":
        current = user.full_name or "Not recorded"
        _set_step(user, db, "owner_val")
        await send_text_message(db, mobile, f"Current name: {current}\n\nWhat would you like to change it to?")


# ---------------------------------------------------------------------------
# Step: pet profile
# ---------------------------------------------------------------------------

_PET_FIELD_MAP = {
    "1": "name", "2": "breed", "3": "weight",
    "4": "gender", "5": "age_or_dob", "6": "neutered",
}
_PET_FIELD_PROMPTS = {
    "name":       "Enter the new name for your pet:",
    "breed":      "Enter the new breed:",
    "weight":     "Enter the new weight in kg (e.g., 12.5):",
    "gender":     "Enter gender — male or female:",
    "age_or_dob": "Enter age or birthday (e.g., '3 years', '15/04/2021'):",
    "neutered":   "Is the pet neutered/spayed? Reply yes or no:",
}


async def _step_pet_field_select(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if text.lower() in ("back", "menu"):
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, _CAT_MENU)
        return

    field = _PET_FIELD_MAP.get(text.strip())
    if not field:
        await send_text_message(
            db, mobile,
            "Reply with a number:\n1. Name\n2. Breed\n3. Weight\n4. Gender\n5. Age / Birthday\n6. Neutered / Spayed",
        )
        return

    new_ctx = dict(ctx)
    new_ctx["field"] = field
    _set_step(user, db, "pet_field_val", new_ctx)
    await send_text_message(db, mobile, _PET_FIELD_PROMPTS[field])


async def _step_pet_field_val(db, user, pets, pet, ctx, text, mobile, send_text_message):
    field = ctx.get("field")
    if not field:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, _CAT_MENU)
        return

    result, ok = _do_update_pet_field(db, pet, field, text)
    if not ok:
        await send_text_message(db, mobile, result)
        return

    _schedule_precompute(str(pet.id))
    await _send_done(db, user, pet, result, send_text_message)


def _do_update_pet_field(db, pet, field: str, value: str) -> tuple[str, bool]:
    value = value.strip()
    if not value:
        return "No value provided. Please try again.", False

    if field == "name":
        if len(value) > 100:
            return "Name too long (max 100 characters).", False
        old = pet.name
        pet.name = value
        db.commit()
        return f"Updated name from '{old}' to '{value}'.", True

    if field == "breed":
        if len(value) > 100:
            return "Breed too long (max 100 characters).", False
        old = pet.breed or "not set"
        pet.breed = value
        db.commit()
        return f"Breed updated from '{old}' to '{value}'.", True

    if field == "weight":
        try:
            w = float(value.replace("kg", "").replace("Kg", "").strip())
        except ValueError:
            return f"'{value}' is not a valid number. Please enter weight in kg (e.g., 12.5).", False
        if not (0.5 <= w <= 150):
            return f"Weight {w} kg is outside the valid range (0.5–150 kg).", False
        old = pet.weight
        pet.weight = w
        pet.weight_flagged = False
        db.commit()
        try:
            from app.models.health.weight_history import WeightHistory
            db.add(WeightHistory(pet_id=pet.id, weight_kg=w, recorded_at=date.today()))
            db.commit()
        except Exception:
            pass
        return f"Weight updated from {old} kg to {w} kg.", True

    if field == "gender":
        normalized = _parse_gender(value)
        if not normalized:
            return f"Could not recognise '{value}'. Please reply 'male' or 'female'.", False
        old = pet.gender or "not set"
        pet.gender = normalized
        db.commit()
        return f"Gender updated from '{old}' to '{normalized}'.", True

    if field == "age_or_dob":
        dob, age_text = _parse_age_or_dob(value)
        if dob is None and age_text is None:
            return f"Could not parse '{value}'. Try '3 years' or '15/04/2021'.", False
        pet.age_text = age_text or value
        if dob:
            pet.dob = dob
        db.commit()
        display = str(dob) if dob else age_text
        return f"Age/birthday updated to {display}.", True

    if field == "neutered":
        val = _parse_bool(value)
        if val is None:
            return "Please reply 'yes' or 'no'.", False
        pet.neutered = val
        db.commit()
        label = "neutered/spayed" if val else "not neutered/spayed"
        return f"{pet.name} is now marked as {label}.", True

    return f"Unknown field: {field}", False


# ---------------------------------------------------------------------------
# Step: diet
# ---------------------------------------------------------------------------


async def _step_diet_action(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if text.lower() in ("back", "menu"):
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, _CAT_MENU)
        return
    if text == "1":
        _set_step(user, db, "diet_add_label")
        await send_text_message(
            db, mobile,
            "What is the name of the food item? (e.g., Royal Canin Adult, boiled chicken)",
        )
    elif text == "2":
        diet_repo = DietItemRepository(db)
        items = diet_repo.find_by_pet(pet.id)
        if not items:
            await send_text_message(db, mobile, "No diet items recorded yet. Type 1 to add one.")
            return
        lines = "\n".join(f"{i + 1}. {it.label} [{it.type}]" for i, it in enumerate(items))
        new_ctx = {"diet_ids": [str(it.id) for it in items]}
        _set_step(user, db, "diet_update_select", new_ctx)
        await send_text_message(db, mobile, f"Which item to update?\n\n{lines}")
    elif text == "3":
        diet_repo = DietItemRepository(db)
        items = diet_repo.find_by_pet(pet.id)
        if not items:
            await send_text_message(db, mobile, "No diet items to remove.")
            return
        lines = "\n".join(f"{i + 1}. {it.label}" for i, it in enumerate(items))
        new_ctx = {"diet_ids": [str(it.id) for it in items]}
        _set_step(user, db, "diet_remove_select", new_ctx)
        await send_text_message(db, mobile, f"Which item to remove?\n\n{lines}")
    else:
        await send_text_message(db, mobile, "Please reply 1 (Add), 2 (Update), or 3 (Remove).")


async def _step_diet_add_label(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.strip():
        await send_text_message(db, mobile, "Please enter the food item name.")
        return
    new_ctx = dict(ctx)
    new_ctx["label"] = text.strip()
    _set_step(user, db, "diet_add_type", new_ctx)
    await send_text_message(db, mobile, "What type of food?\n1. Packaged\n2. Homemade\n3. Supplement")


async def _step_diet_add_type(db, user, pets, pet, ctx, text, mobile, send_text_message):
    type_map = {"1": "packaged", "2": "homemade", "3": "supplement"}
    item_type = type_map.get(text.strip())
    if not item_type:
        await send_text_message(db, mobile, "Please reply 1 (Packaged), 2 (Homemade), or 3 (Supplement).")
        return
    new_ctx = dict(ctx)
    new_ctx["type"] = item_type
    _set_step(user, db, "diet_add_detail", new_ctx)
    await send_text_message(
        db, mobile,
        "Any details? (e.g., '200g twice a day') — or reply *skip* to continue.",
    )


async def _step_diet_add_detail(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.nutrition.diet_item import DietItem

    label = ctx.get("label", "")
    item_type = ctx.get("type", "packaged")
    detail = None if text.lower() == "skip" else text.strip()

    _ICONS = {"packaged": "\U0001f6cd️", "homemade": "\U0001f373", "supplement": "\U0001f48a"}
    icon = _ICONS.get(item_type, "\U0001f37d️")

    db.add(DietItem(pet_id=pet.id, type=item_type, icon=icon, label=label, detail=detail))
    db.commit()
    _schedule_precompute(str(pet.id))
    await _send_done(db, user, pet, f"Added '{label}' to {pet.name}’s diet.", send_text_message)


async def _step_diet_update_select(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.isdigit():
        await send_text_message(db, mobile, "Please reply with a number to select an item.")
        return
    idx = int(text) - 1
    ids = ctx.get("diet_ids", [])
    if idx < 0 or idx >= len(ids):
        await send_text_message(db, mobile, f"Please choose a number between 1 and {len(ids)}.")
        return
    new_ctx = dict(ctx)
    new_ctx["selected_diet_id"] = ids[idx]
    _set_step(user, db, "diet_update_field", new_ctx)
    await send_text_message(
        db, mobile,
        "What would you like to update?\n1. Food name\n2. Details (portion, frequency)",
    )


async def _step_diet_update_field(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if text == "1":
        new_ctx = dict(ctx)
        new_ctx["diet_field"] = "label"
        _set_step(user, db, "diet_update_val", new_ctx)
        await send_text_message(db, mobile, "Enter the new food name:")
    elif text == "2":
        new_ctx = dict(ctx)
        new_ctx["diet_field"] = "detail"
        _set_step(user, db, "diet_update_val", new_ctx)
        await send_text_message(db, mobile, "Enter the new details (e.g., '200g once a day'):")
    else:
        await send_text_message(db, mobile, "Please reply 1 (Name) or 2 (Details).")


async def _step_diet_update_val(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.nutrition.diet_item import DietItem

    diet_id = ctx.get("selected_diet_id")
    field = ctx.get("diet_field", "label")
    if not diet_id:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, _CAT_MENU)
        return

    item = db.query(DietItem).filter(DietItem.id == diet_id).first()
    if not item:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, "Item not found.\n\n" + _CAT_MENU)
        return

    setattr(item, field, text.strip())
    db.commit()
    _schedule_precompute(str(pet.id))
    await _send_done(
        db, user, pet,
        f"Diet item '{item.label}' updated ({field} changed).",
        send_text_message,
    )


async def _step_diet_remove_select(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.nutrition.diet_item import DietItem

    if not text.isdigit():
        await send_text_message(db, mobile, "Please reply with a number to select an item.")
        return
    idx = int(text) - 1
    ids = ctx.get("diet_ids", [])
    if idx < 0 or idx >= len(ids):
        await send_text_message(db, mobile, f"Please choose a number between 1 and {len(ids)}.")
        return

    item = db.query(DietItem).filter(DietItem.id == ids[idx]).first()
    if not item:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, "Item not found.\n\n" + _CAT_MENU)
        return

    label = item.label
    db.delete(item)
    db.commit()
    _schedule_precompute(str(pet.id))
    await _send_done(db, user, pet, f"Removed '{label}' from {pet.name}’s diet.", send_text_message)


# ---------------------------------------------------------------------------
# Step: preventive
# ---------------------------------------------------------------------------


async def _step_prev_action(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if text.lower() in ("back", "menu"):
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, _CAT_MENU)
        return
    if text == "1":
        preventive_repo = PreventiveRepository(db)
        all_records = preventive_repo.find_with_master_ordered_by_last_done(pet.id, limit=20)

        all_items = []
        for rec in all_records:
            item = rec.item
            if item is None:
                continue
            suffix = " (custom)" if rec.custom_preventive_item_id else ""
            last = str(rec.last_done_date) if rec.last_done_date else "—"
            all_items.append((str(rec.id), f"{item.item_name}{suffix} — last done {last}"))

        if not all_items:
            await send_text_message(db, mobile, "No preventive records found. Type 2 to add a custom item.")
            return

        lines = "\n".join(f"{i + 1}. {label}" for i, (_, label) in enumerate(all_items))
        new_ctx = {"record_ids": [rid for rid, _ in all_items]}
        _set_step(user, db, "prev_update_select", new_ctx)
        await send_text_message(db, mobile, f"Which record to update?\n\n{lines}")

    elif text == "2":
        _set_step(user, db, "prev_add_name")
        await send_text_message(
            db, mobile,
            "What is the name of the medicine or supplement? (e.g., Heartgard, Omega-3)",
        )
    else:
        await send_text_message(db, mobile, "Please reply 1 (Update a record) or 2 (Add custom item).")


async def _step_prev_update_select(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.isdigit():
        await send_text_message(db, mobile, "Please reply with a number.")
        return
    idx = int(text) - 1
    ids = ctx.get("record_ids", [])
    if idx < 0 or idx >= len(ids):
        await send_text_message(db, mobile, f"Please choose 1–{len(ids)}.")
        return
    new_ctx = dict(ctx)
    new_ctx["selected_record_id"] = ids[idx]
    _set_step(user, db, "prev_update_field", new_ctx)
    await send_text_message(
        db, mobile,
        "What would you like to update?\n1. Last done date\n2. Medicine / product name",
    )


async def _step_prev_update_field(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if text == "1":
        new_ctx = dict(ctx)
        _set_step(user, db, "prev_update_date_val", new_ctx)
        await send_text_message(db, mobile, "Enter the new date (DD/MM/YYYY):")
    elif text == "2":
        new_ctx = dict(ctx)
        _set_step(user, db, "prev_update_med_val", new_ctx)
        await send_text_message(db, mobile, "Enter the new medicine or product name:")
    else:
        await send_text_message(db, mobile, "Please reply 1 (Date) or 2 (Medicine name).")


async def _step_prev_update_date_val(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.preventive.preventive_record import PreventiveRecord
    from app.models.lookup.preventive_master import PreventiveMaster
    from app.models.preventive.custom_preventive_item import CustomPreventiveItem
    from app.services.shared.preventive_calculator import compute_next_due_date, compute_status, get_effective_recurrence_days

    record_id = ctx.get("selected_record_id")
    new_date = _parse_date(text)
    if not new_date:
        await send_text_message(
            db, mobile,
            "Could not parse date. Please use DD/MM/YYYY (e.g., 15/03/2025).",
        )
        return

    record = db.query(PreventiveRecord).filter(PreventiveRecord.id == record_id).first()
    if not record:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, "Record not found.\n\n" + _CAT_MENU)
        return

    master = (
        db.query(PreventiveMaster).filter(PreventiveMaster.id == record.preventive_master_id).first()
        if record.preventive_master_id else None
    )
    custom = (
        db.query(CustomPreventiveItem).filter(CustomPreventiveItem.id == record.custom_preventive_item_id).first()
        if record.custom_preventive_item_id else None
    )

    if master:
        recurrence = get_effective_recurrence_days(db, master, record, pet)
    else:
        recurrence = custom.recurrence_days if custom else 365
    reminder_before = (
        master.reminder_before_days if master else (custom.reminder_before_days if custom else 7)
    )

    old_next = record.next_due_date
    record.last_done_date = new_date
    record.next_due_date = compute_next_due_date(new_date, recurrence)
    record.status = compute_status(record.next_due_date, reminder_before)

    if old_next and old_next != record.next_due_date:
        reminder_repo = ReminderRepository(db)
        stale = reminder_repo.find_stale_by_record_and_date(record.id, old_next)
        for r in stale:
            r.status = "completed"

    db.commit()
    name = master.item_name if master else (custom.item_name if custom else "Record")
    _schedule_precompute(str(pet.id))
    await _send_done(
        db, user, pet,
        f"'{name}' updated: last done {new_date}, next due {record.next_due_date}.",
        send_text_message,
    )


async def _step_prev_update_med_val(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.preventive.preventive_record import PreventiveRecord

    record_id = ctx.get("selected_record_id")
    if not text.strip():
        await send_text_message(db, mobile, "Please enter the medicine name.")
        return

    record = db.query(PreventiveRecord).filter(PreventiveRecord.id == record_id).first()
    if not record:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, "Record not found.\n\n" + _CAT_MENU)
        return

    record.medicine_name = text.strip()
    db.commit()
    _schedule_precompute(str(pet.id))
    await _send_done(
        db, user, pet,
        f"Medicine name updated to '{text.strip()}'.",
        send_text_message,
    )


async def _step_prev_add_name(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.strip():
        await send_text_message(db, mobile, "Please enter the item name.")
        return
    new_ctx = dict(ctx)
    new_ctx["item_name"] = text.strip()
    _set_step(user, db, "prev_add_date", new_ctx)
    await send_text_message(
        db, mobile,
        "When was it last given? (DD/MM/YYYY) — or reply *skip* if unknown.",
    )


async def _step_prev_add_date(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.preventive.custom_preventive_item import CustomPreventiveItem
    from app.models.preventive.preventive_record import PreventiveRecord
    from app.services.shared.preventive_calculator import compute_next_due_date, compute_status

    item_name = ctx.get("item_name", "")
    if text.lower() == "skip":
        last_done = None
    else:
        last_done = _parse_date(text)
        if not last_done:
            await send_text_message(
                db, mobile,
                "Could not parse date. Please use DD/MM/YYYY or reply *skip*.",
            )
            return

    species = pet.species or "both"
    custom_item_repo = CustomPreventiveItemRepository(db)
    custom_item = custom_item_repo.find_by_user_and_name(user.id, item_name)
    if not custom_item:
        custom_item = CustomPreventiveItem(
            user_id=user.id,
            item_name=item_name,
            category="complete",
            circle="health",
            species=species,
            recurrence_days=30,
            reminder_before_days=7,
            overdue_after_days=7,
        )
        db.add(custom_item)
        db.flush()

    if last_done:
        next_due = compute_next_due_date(last_done, 30)
        status = compute_status(next_due, 7)
    else:
        next_due = None
        status = "upcoming"

    db.add(
        PreventiveRecord(
            pet_id=pet.id,
            custom_preventive_item_id=custom_item.id,
            last_done_date=last_done,
            next_due_date=next_due,
            status=status,
        )
    )
    db.commit()
    date_display = f", last done {last_done}" if last_done else ""
    _schedule_precompute(str(pet.id))
    await _send_done(
        db, user, pet,
        f"Added '{item_name}'{date_display} to {pet.name}’s records.",
        send_text_message,
    )


# ---------------------------------------------------------------------------
# Step: conditions
# ---------------------------------------------------------------------------


async def _step_cond_name(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.strip():
        await send_text_message(db, mobile, "Please enter the condition name.")
        return
    new_ctx = dict(ctx)
    new_ctx["cond_name"] = text.strip()
    _set_step(user, db, "cond_since", new_ctx)
    await send_text_message(
        db, mobile,
        "When was it diagnosed? (DD/MM/YYYY) — or reply *skip* if unknown.",
    )


async def _step_cond_since(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.health.condition import Condition

    cond_name = ctx.get("cond_name", "")
    if text.lower() == "skip":
        diagnosed_at = None
    else:
        diagnosed_at = _parse_date(text)
        if not diagnosed_at:
            await send_text_message(
                db, mobile,
                "Could not parse date. Please use DD/MM/YYYY or reply *skip*.",
            )
            return

    db.add(
        Condition(
            pet_id=pet.id,
            name=cond_name,
            condition_type="chronic",
            source="manual",
            diagnosed_at=diagnosed_at,
            is_active=True,
        )
    )
    db.commit()
    _schedule_precompute(str(pet.id))
    await _send_done(
        db, user, pet,
        f"Condition '{cond_name}' added for {pet.name}.",
        send_text_message,
    )


# ---------------------------------------------------------------------------
# Step: reminders
# ---------------------------------------------------------------------------


async def _step_reminder_select(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.preventive.reminder import Reminder

    if not text.isdigit():
        await send_text_message(db, mobile, "Please reply with a number to select a reminder.")
        return
    idx = int(text) - 1
    ids = ctx.get("reminder_ids", [])
    if idx < 0 or idx >= len(ids):
        await send_text_message(db, mobile, f"Please choose 1–{len(ids)}.")
        return

    reminder = db.query(Reminder).filter(Reminder.id == ids[idx]).first()
    if not reminder:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, "Reminder not found.\n\n" + _CAT_MENU)
        return

    new_ctx = dict(ctx)
    new_ctx["selected_reminder_id"] = ids[idx]
    desc = reminder.item_desc or "Reminder"
    _set_step(user, db, "reminder_action", new_ctx)
    await send_text_message(
        db, mobile,
        f"*{desc}* — due {reminder.next_due_date}\n\n"
        "What would you like to do?\n1. Edit due date\n2. Mark as done",
    )


async def _step_reminder_action(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.preventive.reminder import Reminder

    reminder_id = ctx.get("selected_reminder_id")
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, "Reminder not found.\n\n" + _CAT_MENU)
        return

    if text == "1":
        _set_step(user, db, "reminder_date_val", dict(ctx))
        await send_text_message(db, mobile, "Enter the new due date (DD/MM/YYYY):")
    elif text == "2":
        reminder.status = "completed"
        db.commit()
        desc = reminder.item_desc or "Reminder"
        await _send_done(db, user, pet, f"Marked '{desc}' as done.", send_text_message)
    else:
        await send_text_message(db, mobile, "Please reply 1 (Edit date) or 2 (Mark as done).")


async def _step_reminder_date_val(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.preventive.reminder import Reminder

    reminder_id = ctx.get("selected_reminder_id")
    new_date = _parse_date(text)
    if not new_date:
        await send_text_message(db, mobile, "Could not parse date. Please use DD/MM/YYYY.")
        return

    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, "Reminder not found.\n\n" + _CAT_MENU)
        return

    reminder.next_due_date = new_date
    db.commit()
    desc = reminder.item_desc or "Reminder"
    await _send_done(db, user, pet, f"'{desc}' rescheduled to {new_date}.", send_text_message)


# ---------------------------------------------------------------------------
# Step: RX medicines
# ---------------------------------------------------------------------------


async def _step_rx_name(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.strip():
        await send_text_message(db, mobile, "Please enter the medicine name.")
        return
    new_ctx = dict(ctx)
    new_ctx["rx_name"] = text.strip()
    _set_step(user, db, "rx_date", new_ctx)
    await send_text_message(
        db, mobile,
        "When is the next dose due? (DD/MM/YYYY) — or reply *today* for today.",
    )


async def _step_rx_date(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.preventive.reminder import Reminder

    rx_name = ctx.get("rx_name", "Medicine")

    if text.lower() == "today":
        due_date = date.today()
    else:
        due_date = _parse_date(text)
        if not due_date:
            await send_text_message(
                db, mobile,
                "Could not parse date. Please use DD/MM/YYYY or reply *today*.",
            )
            return

    db.add(
        Reminder(
            pet_id=pet.id,
            next_due_date=due_date,
            stage="due",
            status="pending",
            source_type="rx_medicine",
            source_id=None,
            item_desc=rx_name,
        )
    )
    db.commit()
    await _send_done(
        db, user, pet,
        f"Medicine reminder added: '{rx_name}' due {due_date}.",
        send_text_message,
    )


# ---------------------------------------------------------------------------
# Step: contacts
# ---------------------------------------------------------------------------


async def _step_contact_action(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if text == "1":
        ids = ctx.get("contact_ids", [])
        if not ids:
            _set_step(user, db, "cat_select")
            await send_text_message(db, mobile, _CAT_MENU)
            return
        from app.models.core.contact import Contact
        contacts = db.query(Contact).filter(Contact.id.in_(ids)).all()
        contacts_by_id = {str(c.id): c for c in contacts}
        ordered = [contacts_by_id[cid] for cid in ids if cid in contacts_by_id]
        if not ordered:
            _set_step(user, db, "cat_select")
            await send_text_message(db, mobile, _CAT_MENU)
            return
        lines = "\n".join(f"{i + 1}. {c.name} ({c.role})" for i, c in enumerate(ordered))
        new_ctx = {"contact_ids": [str(c.id) for c in ordered]}
        _set_step(user, db, "contact_select", new_ctx)
        await send_text_message(db, mobile, f"Which contact?\n\n{lines}")
    elif text == "2":
        _set_step(user, db, "contact_new_name")
        await send_text_message(db, mobile, "What is the new contact’s name?")
    else:
        await send_text_message(db, mobile, "Please reply 1 (Update existing) or 2 (Add new).")


async def _step_contact_select(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.isdigit():
        await send_text_message(db, mobile, "Please reply with a number.")
        return
    idx = int(text) - 1
    ids = ctx.get("contact_ids", [])
    if idx < 0 or idx >= len(ids):
        await send_text_message(db, mobile, f"Please choose 1–{len(ids)}.")
        return
    new_ctx = dict(ctx)
    new_ctx["selected_contact_id"] = ids[idx]
    _set_step(user, db, "contact_field", new_ctx)
    await send_text_message(
        db, mobile,
        "What would you like to update?\n1. Name\n2. Clinic name\n3. Phone number\n4. Role",
    )


async def _step_contact_field(db, user, pets, pet, ctx, text, mobile, send_text_message):
    field_map = {"1": "name", "2": "clinic_name", "3": "phone", "4": "role"}
    field = field_map.get(text)
    if not field:
        await send_text_message(db, mobile, "Please reply 1–4.")
        return
    new_ctx = dict(ctx)
    new_ctx["contact_field"] = field
    _set_step(user, db, "contact_val", new_ctx)
    prompts = {
        "name":        "Enter the new name:",
        "clinic_name": "Enter the clinic / hospital name:",
        "phone":       "Enter the phone number:",
        "role":        "Enter the role (veterinarian / groomer / trainer / specialist / other):",
    }
    await send_text_message(db, mobile, prompts[field])


async def _step_contact_val(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.core.contact import Contact

    contact_id = ctx.get("selected_contact_id")
    field = ctx.get("contact_field", "name")
    if not text.strip():
        await send_text_message(db, mobile, "Please enter a value.")
        return

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        _set_step(user, db, "cat_select")
        await send_text_message(db, mobile, "Contact not found.\n\n" + _CAT_MENU)
        return

    setattr(contact, field, text.strip())
    db.commit()
    await _send_done(
        db, user, pet,
        f"Contact '{contact.name}' updated: {field} → '{text.strip()}'.",
        send_text_message,
    )


async def _step_contact_new_name(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.strip():
        await send_text_message(db, mobile, "Please enter the contact’s name.")
        return
    new_ctx = dict(ctx)
    new_ctx["new_contact_name"] = text.strip()
    _set_step(user, db, "contact_new_role", new_ctx)
    await send_text_message(
        db, mobile,
        "What is their role?\n1. Veterinarian\n2. Groomer\n3. Trainer\n4. Specialist\n5. Other",
    )


async def _step_contact_new_role(db, user, pets, pet, ctx, text, mobile, send_text_message):
    role_map = {
        "1": "veterinarian", "2": "groomer", "3": "trainer", "4": "specialist", "5": "other",
        "veterinarian": "veterinarian", "groomer": "groomer", "trainer": "trainer",
        "specialist": "specialist", "other": "other", "vet": "veterinarian",
    }
    role = role_map.get(text.strip().lower(), "veterinarian")
    new_ctx = dict(ctx)
    new_ctx["new_contact_role"] = role
    _set_step(user, db, "contact_new_phone", new_ctx)
    await send_text_message(db, mobile, "Phone number? — or reply *skip*.")


async def _step_contact_new_phone(db, user, pets, pet, ctx, text, mobile, send_text_message):
    from app.models.core.contact import Contact

    name = ctx.get("new_contact_name", "Contact")
    role = ctx.get("new_contact_role", "veterinarian")
    phone = None if text.lower() == "skip" else text.strip()

    db.add(Contact(pet_id=pet.id, name=name, role=role, phone=phone, source="manual"))
    db.commit()
    await _send_done(
        db, user, pet,
        f"Added {role} '{name}' to {pet.name}’s contacts.",
        send_text_message,
    )


# ---------------------------------------------------------------------------
# Step: owner name
# ---------------------------------------------------------------------------


async def _step_owner_val(db, user, pets, pet, ctx, text, mobile, send_text_message):
    if not text.strip():
        await send_text_message(db, mobile, "Please enter your name.")
        return
    if len(text.strip()) > 120:
        await send_text_message(db, mobile, "Name too long (max 120 characters).")
        return
    old = user.full_name or "not set"
    user.full_name = text.strip()
    db.commit()
    await _send_done(
        db, user, pet,
        f"Your name updated from '{old}' to '{text.strip()}'.",
        send_text_message,
    )
