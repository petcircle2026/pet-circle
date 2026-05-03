"""
PetCircle — Order Service v2

Unified WhatsApp order flow. All logic is deterministic using signal_resolver
for SKU resolution and rule-based product recommendations.

Flow overview:
    User types "order"
        → start_order_flow        — category buttons (food, supplements, medicines, treats)
    User taps category
        → start_order_for_category
            ├─ food        → (pet select?) → diet type? → SKU list → cart buttons
            ├─ supplements → (pet select?) → current items / recommended → SKU list → cart
            ├─ medicines   → type (preventive | prescription)
            │   ├─ preventive → sub-type (deworming | flea-tick) → (pet select?) → SKU list → cart
            │   └─ prescription → numbered RX list → admin notified
            └─ treats      → (pet select?) → treat name → admin notified

State is tracked via:
    user.order_state   — str  current step name
    user.order_context — JSONB context dict (pet_id, sku_options, selected_sku, …)

IMPORTANT — JSONB mutation tracking:
    Always call flag_modified(user, "order_context") before db.commit() when
    modifying user.order_context in place.
"""
import asyncio
import logging
from uuid import UUID
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.core.constants import (
    ORDER_CANCEL,
    ORDER_CATEGORY_FOOD,
    ORDER_CATEGORY_MEDICINES,
    ORDER_CATEGORY_SUPPLEMENTS,
    ORDER_CATEGORY_TREATS,
    ORDER_CATEGORY_LABELS,
    ORDER_CONFIRM,
    ORDER_FULFILL_NO,
    ORDER_FULFILL_NO_PREFIX,
    ORDER_FULFILL_YES,
    ORDER_FULFILL_YES_PREFIX,
    MED_DEWORMING,
    MED_FLEA_TICK,
    MED_PRESCRIPTION,
    MED_PREVENTIVE,
    ORDER_ADD_CART,
    ORDER_CHECKOUT,
    FOOD_PRESCRIBED,
    FOOD_REGULAR,
)
from app.core.encryption import decrypt_field
from app.core.log_sanitizer import mask_phone
from app.models.health.condition import Condition
from app.models.health.condition_medication import ConditionMedication
from app.models.nutrition.diet_item import DietItem
from app.models.commerce.order import Order
from app.models.core.pet import Pet
from app.repositories.pet_repository import PetRepository
from app.repositories.order_repository import OrderRepository
from app.services.dashboard.signal_resolver import (
    resolve_food_signal,
    resolve_supplement_signal,
    resolve_deworming_signal,
    resolve_flea_tick_signal,
    _get_pet_life_stage,
)
from app.services.whatsapp.whatsapp_sender import (
    send_interactive_buttons,
    send_template_message,
    send_text_message,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_mobile(user) -> str:
    cached = getattr(user, "_plaintext_mobile", None)
    if cached:
        return cached
    return decrypt_field(user.mobile_number)


def _get_active_pets(db: Session, user) -> list:
    pet_repo = PetRepository(db)
    pets = pet_repo.find_by_user_id(user.id)
    return sorted(pets, key=lambda p: p.name or "")


def _set_order_state(user, db: Session, state: str, ctx: dict | None = None) -> None:
    user.order_state = state
    if ctx is not None:
        user.order_context = ctx
    elif user.order_context is None:
        user.order_context = {}
    flag_modified(user, "order_context")
    try:
        db.commit()
    except Exception as exc:
        logger.error("order_service: set_state %s error: %s", state, exc)
        db.rollback()


def _update_order_ctx(user, db: Session, **kwargs) -> None:
    if user.order_context is None:
        user.order_context = {}
    user.order_context.update(kwargs)
    flag_modified(user, "order_context")
    try:
        db.commit()
    except Exception as exc:
        logger.error("order_service: update_ctx error: %s", exc)
        db.rollback()


def _clear_order_state(db: Session, user) -> None:
    user.order_state = None
    user.order_context = None
    try:
        db.commit()
    except Exception as exc:
        logger.error("order_service: clear_state error: %s", exc)
        db.rollback()


def _get_conditions(db: Session, pet_id) -> list[str]:
    try:
        conditions = (
            db.query(Condition)
            .filter(Condition.pet_id == pet_id, Condition.is_active.is_(True))
            .all()
        )
        return [c.name for c in conditions]
    except Exception:
        return []


def _format_sku_list(sku_options: list[dict]) -> str:
    lines = []
    for i, sku in enumerate(sku_options, 1):
        brand = sku.get("brand_name", "")
        line_name = sku.get("product_line") or sku.get("product_name", "")
        price = sku.get("discounted_price") or sku.get("mrp", 0)
        pack = sku.get("pack_size", "")
        label = f"{brand} {line_name}".strip()
        if pack:
            label += f" ({pack})"
        lines.append(f"{i}. {label} — ₹{price}")
    return "\n".join(lines)


async def _send_sku_results(
    db: Session,
    mobile: str,
    pet_name: str,
    sku_options: list[dict],
    status_prefix: str = "",
) -> None:
    if not sku_options:
        await send_text_message(
            db, mobile,
            "Sorry, I couldn't find matching products in our catalog. "
            "Please contact us to order.",
        )
        return
    sku_list = _format_sku_list(sku_options)
    await send_text_message(
        db, mobile,
        f"{status_prefix}Here are the recommended products for {pet_name}:\n\n{sku_list}\n\n"
        "Reply with a number to select, or *cancel* to exit.",
    )


async def _notify_admin_order(db: Session, user, pet_name: str, category: str, items_desc: str) -> None:
    admin_phone = settings.ORDER_NOTIFICATION_PHONE
    if not admin_phone:
        return
    try:
        user_phone = decrypt_field(user.mobile_number)
        admin_phone_norm = admin_phone.strip().replace("+", "")
        user_phone_norm = user_phone.strip().replace("+", "")
        if admin_phone_norm == user_phone_norm:
            return
        user_name = user.full_name or "Unknown"
        label = ORDER_CATEGORY_LABELS.get(category, category)
        await send_template_message(
            db=db,
            to_number=admin_phone,
            template_name=settings.WHATSAPP_TEMPLATE_ORDER_FULFILLMENT_CHECK,
            parameters=[user_name, user_phone, pet_name, label, items_desc, "N/A"],
        )
    except Exception as exc:
        logger.error("order_service: admin notify error: %s", exc)


# ---------------------------------------------------------------------------
# Entry points (called by message_router start triggers)
# ---------------------------------------------------------------------------


async def start_order_flow(db: Session, user) -> None:
    """Send category selection buttons. Called when user types 'order'."""
    mobile = _get_mobile(user)
    pets = _get_active_pets(db, user)

    if pets and len(pets) == 1:
        body = f"What would you like to order for *{pets[0].name}*?"
    elif pets:
        names = ", ".join(p.name for p in pets)
        body = f"What would you like to order? (Pets: {names})"
    else:
        body = "What would you like to order?"

    buttons = [
        {"id": ORDER_CATEGORY_MEDICINES, "title": "Medicines"},
        {"id": ORDER_CATEGORY_FOOD, "title": "Food & Nutrition"},
        {"id": ORDER_CATEGORY_SUPPLEMENTS, "title": "Supplements"},
        {"id": ORDER_CATEGORY_TREATS, "title": "Treats"},
    ][:3]  # WhatsApp interactive buttons max = 3; Treats fits only if we merge

    _clear_order_state(db, user)
    await send_interactive_buttons(db, mobile, body, buttons)


async def start_order_for_category(db: Session, user, payload: str) -> None:
    """Handle category button tap. Route to pet selection or sub-flow."""
    mobile = _get_mobile(user)
    pets = _get_active_pets(db, user)

    category_state_prefix = {
        ORDER_CATEGORY_FOOD:        "food",
        ORDER_CATEGORY_SUPPLEMENTS: "supp",
        ORDER_CATEGORY_MEDICINES:   "med",
        ORDER_CATEGORY_TREATS:      "treat",
    }.get(payload)

    if not category_state_prefix:
        await send_text_message(db, mobile, "Unknown category. Please try again.")
        return

    ctx = {"category": category_state_prefix}

    if len(pets) > 1:
        # Need to pick a pet first
        pet_list = "\n".join(f"{i + 1}. {p.name}" for i, p in enumerate(pets))
        _set_order_state(user, db, f"{category_state_prefix}_awaiting_pet", ctx)
        await send_text_message(
            db, mobile,
            f"Which pet is this for?\n\n{pet_list}\n\nReply with a number.",
        )
        return

    pet = pets[0] if pets else None
    if pet:
        ctx["pet_id"] = str(pet.id)
    await _enter_category_flow(db, user, pet, category_state_prefix, ctx, mobile)


async def _enter_category_flow(db, user, pet, cat: str, ctx: dict, mobile: str) -> None:
    """Start the category-specific sub-flow once a pet is known."""
    if cat == "food":
        await _start_food_flow(db, user, pet, ctx, mobile)
    elif cat == "supp":
        await _start_supplement_flow(db, user, pet, ctx, mobile)
    elif cat == "med":
        _set_order_state(user, db, "med_type_sel", ctx)
        await send_interactive_buttons(
            db, mobile,
            "Which type of medicine would you like to order?",
            [
                {"id": MED_PREVENTIVE, "title": "Preventive"},
                {"id": MED_PRESCRIPTION, "title": "Prescription / RX"},
            ],
        )
    elif cat == "treat":
        _set_order_state(user, db, "treat_awaiting_name", ctx)
        pet_name = pet.name if pet else "your pet"
        await send_text_message(
            db, mobile,
            f"What treat would you like to order for {pet_name}? "
            "(e.g., Pedigree Dentastix, raw hide chew)",
        )


# ---------------------------------------------------------------------------
# Pet selection (shared across food / supp / med / treat)
# ---------------------------------------------------------------------------


async def handle_pet_selection_for_category(db: Session, user, text: str, category: str) -> None:
    """Handle numbered pet selection for any category awaiting pet."""
    mobile = _get_mobile(user)
    pets = _get_active_pets(db, user)

    pet = None
    if text.strip().isdigit():
        idx = int(text.strip()) - 1
        if 0 <= idx < len(pets):
            pet = pets[idx]
    if pet is None:
        # Try name match
        for p in pets:
            if p.name.lower() == text.strip().lower():
                pet = p
                break

    if pet is None:
        pet_list = "\n".join(f"{i + 1}. {p.name}" for i, p in enumerate(pets))
        await send_text_message(
            db, mobile,
            f"Please reply with a number:\n\n{pet_list}",
        )
        return

    ctx = user.order_context or {}
    ctx["pet_id"] = str(pet.id)
    flag_modified(user, "order_context")
    await _enter_category_flow(db, user, pet, category, ctx, mobile)


# ---------------------------------------------------------------------------
# Food flow
# ---------------------------------------------------------------------------


async def _start_food_flow(db, user, pet, ctx: dict, mobile: str) -> None:
    """Begin food ordering — ask prescribed vs regular if applicable."""
    if pet is None:
        _set_order_state(user, db, "food_awaiting_pet", ctx)
        await send_text_message(db, mobile, "Which pet is this food for? Reply with a number.")
        return

    conditions = _get_conditions(db, pet.id)
    diet_items = db.query(DietItem).filter(DietItem.pet_id == pet.id, DietItem.type == "packaged").all()

    if conditions:
        # Pet has conditions — ask if prescribed or regular
        _set_order_state(user, db, "food_awaiting_diet_confirm", ctx)
        await send_interactive_buttons(
            db, mobile,
            f"Would you like prescribed diet or regular food for {pet.name}?",
            [
                {"id": FOOD_PRESCRIBED, "title": "Prescribed Diet"},
                {"id": FOOD_REGULAR, "title": "Regular Food"},
            ],
        )
    else:
        # Go straight to SKU resolution
        await _resolve_and_show_food(db, user, pet, diet_items, conditions, ctx, mobile)


async def handle_diet_confirm(db: Session, user, payload: str) -> None:
    """Handle the prescribed / regular diet button tap."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    pet_id = ctx.get("pet_id")

    pets = _get_active_pets(db, user)
    pet = next((p for p in pets if str(p.id) == pet_id), None) if pet_id else None
    if not pet:
        await send_text_message(db, mobile, "Session expired. Type *order* to start again.")
        _clear_order_state(db, user)
        return

    ctx["diet_type"] = "prescribed" if payload == FOOD_PRESCRIBED else "regular"
    conditions = _get_conditions(db, pet.id) if payload == FOOD_PRESCRIBED else []
    diet_items = (
        db.query(DietItem).filter(DietItem.pet_id == pet.id, DietItem.type == "packaged").all()
    )
    await _resolve_and_show_food(db, user, pet, diet_items, conditions, ctx, mobile)


async def _resolve_and_show_food(db, user, pet, diet_items, conditions, ctx, mobile):
    """Resolve food signal and display SKU options."""
    sku_options = []
    if diet_items:
        for item in diet_items:
            try:
                result = resolve_food_signal(db, item, pet, conditions)
                if result.products:
                    sku_options = result.products
                    ctx["diet_item_id"] = str(item.id)
                    break
            except Exception as exc:
                logger.warning("order_service: food signal error: %s", exc)

    if not sku_options:
        # Fallback: query by life stage directly
        try:
            life_stage = _get_pet_life_stage(pet)
            from app.models import ProductFood as _PF
            filters = [
                _PF.life_stage.ilike(f"%{life_stage}%"),
                _PF.in_stock.is_(True),
            ]
            rows = (
                db.query(_PF)
                .filter(*filters)
                .order_by(_PF.popularity_rank.asc())
                .limit(3)
                .all()
            )
            sku_options = [
                {
                    "sku_id": r.sku_id, "brand_name": r.brand_name,
                    "product_line": r.product_line, "pack_size": f"{r.pack_size_kg} kg",
                    "mrp": int(r.mrp), "discounted_price": int(r.discounted_price),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.warning("order_service: food fallback error: %s", exc)

    ctx["sku_options"] = sku_options
    if sku_options:
        _set_order_state(user, db, "food_awaiting_sku_sel", ctx)
    else:
        _clear_order_state(db, user)
    await _send_sku_results(db, mobile, pet.name, sku_options)


async def handle_food_sku_selection(db: Session, user, text: str) -> None:
    """Handle numbered food SKU selection from the list."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    sku_options = ctx.get("sku_options", [])
    pet_id = ctx.get("pet_id")

    if not text.strip().isdigit():
        await send_text_message(db, mobile, "Please reply with a number to select a product.")
        return

    idx = int(text.strip()) - 1
    if idx < 0 or idx >= len(sku_options):
        await send_text_message(db, mobile, f"Please choose 1–{len(sku_options)}.")
        return

    selected = sku_options[idx]
    ctx["selected_sku"] = selected
    _set_order_state(user, db, "awaiting_cart_action", ctx)

    brand = selected.get("brand_name", "")
    line = selected.get("product_line") or selected.get("product_name", "")
    price = selected.get("discounted_price") or selected.get("mrp", 0)
    pack = selected.get("pack_size", "")
    label = f"{brand} {line}".strip()
    if pack:
        label += f" ({pack})"

    await send_interactive_buttons(
        db, mobile,
        f"Selected: *{label}* — ₹{price}\n\nWhat would you like to do?",
        [
            {"id": ORDER_ADD_CART, "title": "Add to Cart"},
            {"id": ORDER_CHECKOUT, "title": "Checkout Now"},
        ],
    )


# ---------------------------------------------------------------------------
# Supplement flow
# ---------------------------------------------------------------------------


async def _start_supplement_flow(db, user, pet, ctx: dict, mobile: str) -> None:
    """Show current supplement diet items + recommended option."""
    if pet is None:
        _set_order_state(user, db, "supp_awaiting_pet", ctx)
        await send_text_message(db, mobile, "Which pet is this for? Reply with a number.")
        return

    supp_items = (
        db.query(DietItem)
        .filter(DietItem.pet_id == pet.id, DietItem.type == "supplement")
        .all()
    )

    if supp_items:
        lines = [f"{i + 1}. {it.label}" for i, it in enumerate(supp_items)]
        lines.append(f"{len(supp_items) + 1}. See recommended supplements")
        ctx["supp_item_ids"] = [str(it.id) for it in supp_items]
        ctx["supp_item_count"] = len(supp_items)
        _set_order_state(user, db, "supp_sel_current", ctx)
        await send_text_message(
            db, mobile,
            f"Supplements for {pet.name}:\n\n" + "\n".join(lines) + "\n\nReply with a number.",
        )
    else:
        # No current supplements — go straight to recommended
        await _resolve_and_show_supplement(db, user, pet, None, ctx, mobile)


async def handle_supplement_current_selection(db: Session, user, text: str) -> None:
    """Handle supplement selection from current items list."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    pet_id = ctx.get("pet_id")
    item_ids = ctx.get("supp_item_ids", [])
    item_count = ctx.get("supp_item_count", 0)

    pets = _get_active_pets(db, user)
    pet = next((p for p in pets if str(p.id) == pet_id), None) if pet_id else None
    if not pet:
        await send_text_message(db, mobile, "Session expired. Type *order* to start again.")
        _clear_order_state(db, user)
        return

    if not text.strip().isdigit():
        await send_text_message(db, mobile, "Please reply with a number.")
        return

    idx = int(text.strip()) - 1
    if idx == item_count:
        # "See recommended supplements"
        await _resolve_and_show_supplement(db, user, pet, None, ctx, mobile)
        return

    if idx < 0 or idx >= len(item_ids):
        await send_text_message(db, mobile, f"Please choose 1–{item_count + 1}.")
        return

    diet_item = db.query(DietItem).filter(DietItem.id == item_ids[idx]).first()
    await _resolve_and_show_supplement(db, user, pet, diet_item, ctx, mobile)


async def _resolve_and_show_supplement(db, user, pet, diet_item, ctx, mobile):
    """Resolve supplement signal and display SKU options."""
    sku_options = []
    conditions = _get_conditions(db, pet.id)

    if diet_item:
        try:
            result = resolve_supplement_signal(db, diet_item, pet, conditions)
            if result.products:
                sku_options = result.products
                ctx["diet_item_id"] = str(diet_item.id)
        except Exception as exc:
            logger.warning("order_service: supplement signal error: %s", exc)

    if not sku_options:
        # Fallback: top supplements for species
        try:
            from app.models import ProductSupplement as _PS
            filters = [_PS.in_stock.is_(True)]
            rows = (
                db.query(_PS)
                .filter(*filters)
                .order_by(_PS.popularity_rank.asc())
                .limit(3)
                .all()
            )
            sku_options = [
                {
                    "sku_id": r.sku_id, "brand_name": r.brand_name,
                    "product_name": r.product_name, "pack_size": r.pack_size,
                    "mrp": int(r.mrp), "discounted_price": int(r.discounted_price),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.warning("order_service: supplement fallback error: %s", exc)

    ctx["sku_options"] = sku_options
    if sku_options:
        _set_order_state(user, db, "supp_sel_recommended", ctx)
    else:
        _clear_order_state(db, user)
    await _send_sku_results(db, mobile, pet.name, sku_options)


async def handle_supplement_recommended_selection(db: Session, user, text: str) -> None:
    """Handle supplement SKU selection (reused for recommended flow)."""
    await handle_food_sku_selection(db, user, text)


# ---------------------------------------------------------------------------
# Medicine flow
# ---------------------------------------------------------------------------


async def handle_medicine_type_selection(db: Session, user, payload: str) -> None:
    """Handle Preventive / Prescription button tap."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    pets = _get_active_pets(db, user)

    if payload == MED_PREVENTIVE:
        _set_order_state(user, db, "med_prev_type_sel", ctx)
        await send_interactive_buttons(
            db, mobile,
            "Which type of preventive medicine?",
            [
                {"id": MED_DEWORMING, "title": "Deworming"},
                {"id": MED_FLEA_TICK, "title": "Flea & Tick"},
            ],
        )
    elif payload == MED_PRESCRIPTION:
        # Show pet's RX medicines
        pet_id = ctx.get("pet_id")
        pet = next((p for p in pets if str(p.id) == pet_id), None) if pet_id else None
        if pet is None and len(pets) == 1:
            pet = pets[0]
            ctx["pet_id"] = str(pet.id)
        if pet is None:
            pet_list = "\n".join(f"{i + 1}. {p.name}" for i, p in enumerate(pets))
            _set_order_state(user, db, "med_prev_awaiting_pet", ctx)
            await send_text_message(db, mobile, f"Which pet?\n\n{pet_list}")
            return
        await _show_rx_medicines(db, user, pet, ctx, mobile)
    else:
        await send_text_message(db, mobile, "Please select Preventive or Prescription.")


async def handle_preventive_type_selection(db: Session, user, payload: str) -> None:
    """Handle Deworming / Flea & Tick button tap."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    pets = _get_active_pets(db, user)

    if payload not in (MED_DEWORMING, MED_FLEA_TICK):
        await send_text_message(db, mobile, "Please select Deworming or Flea & Tick.")
        return

    ctx["med_sub_type"] = payload
    pet_id = ctx.get("pet_id")
    pet = next((p for p in pets if str(p.id) == pet_id), None) if pet_id else None
    if pet is None and len(pets) == 1:
        pet = pets[0]
        ctx["pet_id"] = str(pet.id)

    if pet is None:
        pet_list = "\n".join(f"{i + 1}. {p.name}" for i, p in enumerate(pets))
        _set_order_state(user, db, "med_prev_awaiting_pet", ctx)
        await send_text_message(db, mobile, f"Which pet?\n\n{pet_list}")
        return

    await _resolve_and_show_medicine(db, user, pet, payload, ctx, mobile)


async def _resolve_and_show_medicine(db, user, pet, sub_type: str, ctx: dict, mobile: str) -> None:
    """Resolve medicine signal and display SKU options with need-status context."""
    sku_options = []
    result = None
    try:
        if sub_type == MED_DEWORMING:
            result = resolve_deworming_signal(db, pet)
        else:
            result = resolve_flea_tick_signal(db, pet)
        if result.products:
            sku_options = result.products
    except Exception as exc:
        logger.warning("order_service: medicine signal error: %s", exc)

    ctx["sku_options"] = sku_options
    if sku_options:
        _set_order_state(user, db, "med_prev_sku_sel", ctx)
    else:
        _clear_order_state(db, user)

    # Build a status-aware intro derived from the pet's actual preventive record
    # rather than always showing a generic "order now" prompt.
    status_prefix = ""
    if result is not None:
        p_status = result.preventive_status
        due_date = result.next_due_date
        due_str = due_date.strftime("%d %b %Y") if due_date else None
        if p_status == "overdue":
            status_prefix = f"*{pet.name}* is overdue for this treatment!\n\n"
        elif p_status == "upcoming":
            due_part = f" (due {due_str})" if due_str else " soon"
            status_prefix = f"*{pet.name}* is due{due_part} — good time to order!\n\n"
        elif p_status == "up_to_date":
            due_part = f" Next due: {due_str}." if due_str else ""
            status_prefix = f"*{pet.name}* is currently up to date.{due_part} Ordering in advance?\n\n"

    await _send_sku_results(db, mobile, pet.name, sku_options, status_prefix=status_prefix)


async def handle_preventive_sku_selection(db: Session, user, text: str) -> None:
    """Handle numbered medicine SKU selection."""
    await handle_food_sku_selection(db, user, text)


async def _show_rx_medicines(db, user, pet, ctx, mobile):
    """Show list of pet's prescription medicines (from ConditionMedication)."""
    rx_items = []
    try:
        conditions = (
            db.query(Condition)
            .filter(Condition.pet_id == pet.id, Condition.is_active.is_(True))
            .all()
        )
        for cond in conditions:
            meds = (
                db.query(ConditionMedication)
                .filter(ConditionMedication.condition_id == cond.id)
                .all()
            )
            for m in meds:
                rx_items.append({
                    "name": m.name or m.medicine_name or "Medicine",
                    "condition": cond.name,
                    "dosage": m.dosage or "",
                })
    except Exception as exc:
        logger.warning("order_service: rx query error: %s", exc)

    if not rx_items:
        await send_text_message(
            db, mobile,
            f"No prescription medicines found for {pet.name}. "
            "Please contact us directly to order RX medicines.",
        )
        _clear_order_state(db, user)
        return

    lines = [
        f"{i + 1}. {m['name']} (for {m['condition']})" + (f" — {m['dosage']}" if m["dosage"] else "")
        for i, m in enumerate(rx_items)
    ]
    ctx["rx_medicines"] = rx_items
    _set_order_state(user, db, "med_rx_sel_items", ctx)
    await send_text_message(
        db, mobile,
        f"Prescription medicines for {pet.name}:\n\n" + "\n".join(lines) + "\n\n"
        "Reply with a number. Our team will contact you to process the order.",
    )


async def handle_prescription_medicine_selection(db: Session, user, text: str) -> None:
    """Handle numbered RX medicine selection → notify admin."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    rx_items = ctx.get("rx_medicines", [])
    pet_id = ctx.get("pet_id")

    if not text.strip().isdigit():
        await send_text_message(db, mobile, "Please reply with a number.")
        return

    idx = int(text.strip()) - 1
    if idx < 0 or idx >= len(rx_items):
        await send_text_message(db, mobile, f"Please choose 1–{len(rx_items)}.")
        return

    selected = rx_items[idx]
    pets = _get_active_pets(db, user)
    pet = next((p for p in pets if str(p.id) == pet_id), None) if pet_id else None
    pet_name = pet.name if pet else "your pet"

    items_desc = f"{selected['name']} (for {selected['condition']})"
    await send_text_message(
        db, mobile,
        f"Got it! We'll process your request for *{selected['name']}* for {pet_name}. "
        "Our team will call you shortly.",
    )

    asyncio.create_task(_notify_admin_order(db, user, pet_name, "medicines", items_desc))
    _clear_order_state(db, user)


# ---------------------------------------------------------------------------
# Treats flow
# ---------------------------------------------------------------------------


async def handle_treat_name(db: Session, user, text: str) -> None:
    """Handle treat name input → notify admin."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    pet_id = ctx.get("pet_id")

    if not text.strip():
        await send_text_message(db, mobile, "Please enter the treat name.")
        return

    pets = _get_active_pets(db, user)
    pet = next((p for p in pets if str(p.id) == pet_id), None) if pet_id else None
    pet_name = pet.name if pet else "your pet"
    treat_name = text.strip()

    await send_text_message(
        db, mobile,
        f"Got it! We'll process your request for *{treat_name}* for {pet_name}. "
        "Our team will contact you shortly.",
    )

    asyncio.create_task(_notify_admin_order(db, user, pet_name, "treats", treat_name))
    _clear_order_state(db, user)


# ---------------------------------------------------------------------------
# Cart actions
# ---------------------------------------------------------------------------


async def handle_add_to_cart(db: Session, user) -> None:
    """Add selected SKU to cart and confirm."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    selected = ctx.get("selected_sku")
    pet_id = ctx.get("pet_id")

    if not selected or not pet_id:
        await send_text_message(db, mobile, "Session expired. Type *order* to start again.")
        _clear_order_state(db, user)
        return

    try:
        from app.services.dashboard.cart_service import add_to_cart as _add_to_cart
        await _add_to_cart(
            db=db,
            pet_id=pet_id,
            product_id=selected.get("sku_id"),
            name=f"{selected.get('brand_name', '')} {selected.get('product_line', '')}".strip(),
            price=selected.get("discounted_price") or selected.get("mrp", 0),
        )
        pets = _get_active_pets(db, user)
        pet = next((p for p in pets if str(p.id) == pet_id), None)
        pet_name = pet.name if pet else "your pet"
        await send_text_message(
            db, mobile,
            f"Added to {pet_name}'s cart!\n\n"
            "You can complete checkout on the dashboard. "
            "Send *dashboard* for the link.",
        )
    except Exception as exc:
        logger.error("order_service: add_to_cart error: %s", exc)
        await send_text_message(db, mobile, "Couldn't add to cart. Please try again.")

    _clear_order_state(db, user)


async def handle_checkout(db: Session, user) -> None:
    """Initiate checkout — send dashboard link to complete payment."""
    mobile = _get_mobile(user)
    ctx = user.order_context or {}
    selected = ctx.get("selected_sku")
    pet_id = ctx.get("pet_id")

    if not selected or not pet_id:
        await send_text_message(db, mobile, "Session expired. Type *order* to start again.")
        _clear_order_state(db, user)
        return

    try:
        from app.services.dashboard.cart_service import add_to_cart as _add_to_cart
        from app.services.whatsapp.onboarding import get_or_create_active_dashboard_token

        await _add_to_cart(
            db=db,
            pet_id=pet_id,
            product_id=selected.get("sku_id"),
            name=f"{selected.get('brand_name', '')} {selected.get('product_line', '')}".strip(),
            price=selected.get("discounted_price") or selected.get("mrp", 0),
        )

        token = get_or_create_active_dashboard_token(db, pet_id)
        checkout_url = f"{settings.FRONTEND_URL}/dashboard/{token}?tab=cart"

        await send_text_message(
            db, mobile,
            f"Your item has been added to cart.\n\nComplete checkout here:\n{checkout_url}",
        )
    except Exception as exc:
        logger.error("order_service: checkout error: %s", exc)
        await send_text_message(db, mobile, "Couldn't process checkout. Please try again.")

    _clear_order_state(db, user)


# ---------------------------------------------------------------------------
# Preserved from v1 — unchanged API
# ---------------------------------------------------------------------------


async def cancel_order_flow(db: Session, user) -> None:
    """Cancel the active order flow and notify user."""
    mobile = _get_mobile(user)

    # Clean up any stale draft Order rows
    if hasattr(user, "active_order_id") and user.active_order_id:
        try:
            order_repo = OrderRepository(db)
            old_order = order_repo.find_by_id(user.active_order_id)
            if old_order and not old_order.items_description:
                db.delete(old_order)
            user.active_order_id = None
        except Exception:
            pass

    _clear_order_state(db, user)
    await send_text_message(db, mobile, "Order cancelled. Let me know if you need anything else!")


async def handle_order_confirmation(db: Session, user, payload: str) -> None:
    """
    Handle ORDER_CONFIRM / ORDER_CANCEL button press on old-style order summary.
    Kept for backwards compatibility with any in-flight orders during deployment.
    """
    mobile = _get_mobile(user)

    if not hasattr(user, "active_order_id") or not user.active_order_id:
        await send_text_message(
            db, mobile,
            "No active order found. Type *order* to start again.",
        )
        _clear_order_state(db, user)
        return

    order_repo = OrderRepository(db)
    order = order_repo.find_by_id(user.active_order_id)

    if not order:
        _clear_order_state(db, user)
        await send_text_message(
            db, mobile,
            "Something went wrong with your order. Type *order* to start again.",
        )
        return

    if payload == ORDER_CONFIRM:
        order.status = "pending"
        _clear_order_state(db, user)
        user.active_order_id = None
        db.commit()

        pet = None
        if order.pet_id:
            pet_repo = PetRepository(db)
            pet = pet_repo.get_by_id(order.pet_id)

        await send_text_message(
            db, mobile,
            "Your order has been received! Our team will call you shortly to process it.",
        )

        admin_phone = settings.ORDER_NOTIFICATION_PHONE
        if admin_phone:
            try:
                user_phone = decrypt_field(user.mobile_number)
                pet_name = pet.name if pet else "N/A"
                label = ORDER_CATEGORY_LABELS.get(str(order.category), str(order.category))
                await send_template_message(
                    db=db,
                    to_number=admin_phone,
                    template_name=settings.WHATSAPP_TEMPLATE_ORDER_FULFILLMENT_CHECK,
                    parameters=[
                        user.full_name or "Unknown",
                        user_phone,
                        pet_name,
                        label,
                        order.items_description,
                        str(order.id),
                    ],
                )
            except Exception as exc:
                logger.error("order_service: admin notify error: %s", exc)

    elif payload == ORDER_CANCEL:
        await cancel_order_flow(db, user)


async def handle_admin_order_status_feedback(db: Session, from_number: str, payload: str) -> None:
    """Handle admin WhatsApp fulfillment feedback and update order status."""
    is_yes = payload == ORDER_FULFILL_YES or payload.startswith(ORDER_FULFILL_YES_PREFIX)
    is_no = payload == ORDER_FULFILL_NO or payload.startswith(ORDER_FULFILL_NO_PREFIX)

    if not (is_yes or is_no):
        await send_text_message(db, from_number, "I couldn't process that response.")
        return

    order = None
    if ":" in payload:
        order_id_str = payload.split(":", 1)[1]
        try:
            order_repo = OrderRepository(db)
            order = order_repo.find_by_id(UUID(order_id_str))
        except Exception:
            pass

    if not order:
        order_repo = OrderRepository(db)
        pending_orders = order_repo.find_pending()
        order = pending_orders[0] if pending_orders else None

    if not order:
        await send_text_message(db, from_number, "No pending orders found.")
        return

    if is_yes:
        order.status = "completed"
        note = "Admin confirmed via WhatsApp: fulfilled."
        order.admin_notes = (
            f"{order.admin_notes}\n{note}".strip() if order.admin_notes else note
        )
        db.commit()
        await send_text_message(db, from_number, "Marked as fulfilled (completed).")
    else:
        order.status = "cancelled"
        note = "Admin reported via WhatsApp: not fulfilled, order cancelled."
        order.admin_notes = (
            f"{order.admin_notes}\n{note}".strip() if order.admin_notes else note
        )
        db.commit()
        await send_text_message(db, from_number, "Marked as not fulfilled yet and cancelled.")
