from typing import List
"""
PetCircle Phase 8 — Cart & Orders Service

Manages the pet's shopping cart. Cart items are added by users or
generated as recommendations based on species, breed, life stage and
any diagnosed health conditions.

Key design:
    - No hardcoded cart items — everything from DB
    - Recommendations pulled from product_food + product_supplement
      (signal-level catalog tables, see .spec/cart-rules-engine/design.md)
    - Orders stored in the orders table for admin processing
    - cart_items.product_id stores the sku_id of a ProductFood (F###)
      or ProductSupplement (S###) row — the prefix disambiguates which
      table to query.
"""
from app.models import ProductFood, ProductSupplement
from app.services.dashboard.signal_resolver import (
    _get_breed_size,
    _get_pet_life_stage,
    resolve_food_signal,
    resolve_supplement_signal,
)

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.models.commerce.cart_item import CartItem
from app.models.health.condition import Condition
from app.models.commerce.order import Order
from app.models.core.pet import Pet
from app.models.pet_profile.pet_preference import PetPreference
from app.models.core.user import User
from app.repositories.product_repository import ProductRepository
from app.repositories.cart_item_repository import CartItemRepository
from app.repositories.condition_repository import ConditionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.pet_preference_repository import PetPreferenceRepository
from app.domain.orders.cart_logic import (
    FREE_DELIVERY_THRESHOLD,
    DELIVERY_FEE,
    calculate_cart_summary,
)

logger = logging.getLogger(__name__)


# --- Catalog lookup helpers ---

def _lookup_sku(db: Session, sku_id: str):
    """
    Return the catalog row for a sku_id from product_food or product_supplement.

    The sku_id prefix determines the table (F### = food, S### = supplement).
    Returns a tuple (row, category) or (None, None) when not found.
    """
    if not sku_id:
        return None, None
    prefix = sku_id[:1].upper()
    prod_repo = ProductRepository(db)
    if prefix == "F":
        row = prod_repo.find_food_by_sku(sku_id)
        return row, "food"
    if prefix == "S":
        row = prod_repo.find_supplement_by_sku(sku_id)
        return row, "supplement"
    return None, None


def _food_display_name(product: ProductFood) -> str:
    return f"{product.brand_name} {product.product_line}".strip()


def _supplement_display_name(product: ProductSupplement) -> str:
    return product.product_name


def _food_sub(product: ProductFood) -> str:
    return f"{product.pack_size_kg} kg • {product.life_stage} / {product.breed_size}"


def _supplement_sub(product: ProductSupplement) -> str:
    base = f"{product.brand_name} · {product.pack_size}" if product.pack_size else product.brand_name
    return f"{base} · {product.type.replace('_', ' ')}"


def _category_icon(category: str) -> str:
    """Return an icon for a product category."""
    icons = {
        "food": "🥣",
        "supplement": "💊",
    }
    return icons.get(category, "📦")


# --- Cart CRUD ---

async def get_cart(db: Session, pet_id) -> dict:
    """
    Get all non-expired cart items for a pet.

    C6: Items with cart_expires_at < now() are excluded.
    If non-expired items exist, a resume_prompt is included in the response.

    Returns:
        {
            "items": [...],
            "summary": { "count": int, "subtotal": int },
            "resume_prompt": str | None
        }
    """
    from app.repositories.cart_item_repository import CartItemRepository
    cart_item_repo = CartItemRepository(db)
    items = cart_item_repo.find_active_by_pet(pet_id)

    cart_items = [_serialize_cart_item(item) for item in items]
    in_cart = [i for i in cart_items if i["in_cart"]]

    # C6: Surface resume prompt when items are waiting in cart
    resume_prompt: str | None = None
    if cart_items:
        from app.repositories.pet_repository import PetRepository
        pet_repo = PetRepository(db)
        pet = pet_repo.find_by_id(pet_id)
        pet_name = pet.name if pet else "your pet"
        resume_prompt = f"Resume your order for {pet_name}?"

    summary = calculate_cart_summary([
        {"price_paise": i["price"] * 100, "quantity": i["quantity"]}
        for i in in_cart
    ])

    return {
        "items": cart_items,
        "summary": {
            "count": summary.item_count,
            "subtotal": summary.subtotal_inr,
            "delivery_fee": summary.delivery_fee_inr,
            "total": summary.total_inr,
            "free_delivery": summary.free_delivery,
            "amount_for_free_delivery": max(0.0, FREE_DELIVERY_THRESHOLD - summary.subtotal_inr),
        },
        "resume_prompt": resume_prompt,
    }


async def add_to_cart(
    db: Session,
    pet_id,
    product_id: str,
    name: str,
    price: int,
    icon: str | None = None,
    sub: str | None = None,
    tag: str | None = None,
    tag_color: str | None = None,
) -> dict:
    """Add a product to the pet's cart. If already exists, set in_cart=True."""
    existing = CartItemRepository(db).find_by_pet_and_product(pet_id, product_id)
    if existing:
        existing.in_cart = True
        db.commit()
        db.refresh(existing)
        return _serialize_cart_item(existing)

    item = CartItem(
        pet_id=pet_id,
        product_id=product_id,
        icon=icon,
        name=name,
        sub=sub,
        price=price,
        tag=tag,
        tag_color=tag_color,
        in_cart=True,
        quantity=1,
        cart_expires_at=datetime.now(timezone.utc) + timedelta(hours=72),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_cart_item(item)


async def toggle_cart_item(db: Session, pet_id, product_id: str) -> dict:
    """Toggle in_cart status for a cart item. Creates entry if from recommendations."""
    item = CartItemRepository(db).find_by_pet_and_product(pet_id, product_id)

    if item:
        item.in_cart = not item.in_cart
        db.commit()
        db.refresh(item)
        return _serialize_cart_item(item)

    # Item not in cart_items yet — look up in the SKU tables by product_id.
    product, category = _lookup_sku(db, product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    if category == "food":
        name = _food_display_name(product)
        sub = _food_sub(product)
    else:
        name = _supplement_display_name(product)
        sub = _supplement_sub(product)

    new_item = CartItem(
        pet_id=pet_id,
        product_id=product_id,
        icon=_category_icon(category),
        name=name,
        sub=sub,
        price=int(product.discounted_price),
        tag=None,
        tag_color=None,
        in_cart=True,
        quantity=1,
        cart_expires_at=datetime.now(timezone.utc) + timedelta(hours=72),
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return _serialize_cart_item(new_item)


async def update_quantity(db: Session, pet_id, product_id: str, quantity: int) -> dict:
    """Update quantity for a cart item."""
    item = CartItemRepository(db).find_by_pet_and_product(pet_id, product_id)
    if not item:
        raise ValueError(f"Cart item {product_id} not found")

    item.quantity = max(1, quantity)
    db.commit()
    db.refresh(item)
    return _serialize_cart_item(item)


async def remove_from_cart(db: Session, pet_id, product_id: str) -> dict:
    """Remove item from cart entirely."""
    item = CartItemRepository(db).find_by_pet_and_product(pet_id, product_id)
    if not item:
        raise ValueError(f"Cart item {product_id} not found")

    db.delete(item)
    db.commit()
    return {"status": "deleted", "product_id": product_id}


async def initialize_cart(db: Session, pet_id) -> dict:
    """No-op — cart initializes empty. Users add items themselves."""
    return await get_cart(db, pet_id)


# --- Recommendations ---

async def get_recommendations(
    db: Session,
    pet_id,
    nutrition_gaps: dict | None = None,
) -> list[dict]:
    """
    Get recommended products using ONLY signal_resolver (deterministic rules).

    For each of pet's DietItems (food + supplements), runs through the
    appropriate signal_resolver (resolve_food_signal / resolve_supplement_signal).
    If no diet items exist, synthesizes generic recommendations via signal_resolver's
    L2/L2b logic (life-stage + breed-size aware).

    Returns products NOT already in the pet's cart. Capped at 15.
    nutrition_gaps parameter is ignored—all logic driven by signal_resolver rules.
    """
    from app.models.nutrition.diet_item import DietItem
    from app.repositories.pet_repository import PetRepository

    pet_repo = PetRepository(db)
    pet = pet_repo.find_by_id(pet_id)
    if not pet:
        return []

    # Get existing cart product_ids to exclude
    existing_ids = set(
        row[0] for row in
        CartItemRepository(db).find_product_ids_by_pet(pet_id)
    )

    # Get pet conditions for context (passed to signal_resolver)
    conditions = ConditionRepository(db).find_by_pet_and_active(pet_id)
    condition_names = [c.name.lower() for c in conditions]

    recommendations: list[dict] = []
    seen_skus: set[str] = set()

    # Attempt to resolve via existing diet items (all types: food, supplement, homemade)
    diet_items = (
        db.query(DietItem)
        .filter(DietItem.pet_id == pet_id)
        .all()
    )

    for item in diet_items:
        try:
            if item.type == "supplement":
                # Supplement item → use resolve_supplement_signal
                result = resolve_supplement_signal(db, item, pet, condition_names)
            else:
                # Food item (packaged, homemade) → use resolve_food_signal
                result = resolve_food_signal(db, item, pet, condition_names)

            # Process results
            if result.products:
                for prod in result.products[:3]:
                    sku_id = prod.get("sku_id")
                    if not sku_id or sku_id in existing_ids or sku_id in seen_skus:
                        continue

                    # Look up the actual product row to get display details
                    product, category = _lookup_sku(db, sku_id)
                    if not product:
                        continue

                    if category == "food":
                        rec = _food_to_recommendation(
                            product,
                            reason=f"Matches {pet.name}'s current diet",
                            priority="high",
                        )
                    elif category == "supplement":
                        rec = _supplement_to_recommendation(
                            product,
                            reason=f"Complements {pet.name}'s diet",
                            priority="high",
                        )
                    else:
                        continue

                    recommendations.append(rec)
                    seen_skus.add(sku_id)
                    existing_ids.add(sku_id)

                    if len(recommendations) >= 15:
                        break
        except Exception as exc:
            logger.warning("signal_resolver for diet item %s failed: %s", item.id, exc)
            continue

        if len(recommendations) >= 15:
            break

    # If no recommendations from diet items, fallback to generic life-stage/breed signal
    # by synthesizing a generic DietItem and running through the resolver.
    if not recommendations and diet_items:
        # User has diet items but none resolved â skip fallback
        pass
    elif not recommendations and not diet_items:
        # No diet items at all â use generic fallback via signal_resolver
        try:
            from app.models.nutrition.diet_item import DietItem as DI
            synthetic = DI.__new__(DI)
            synthetic.pet_id = pet_id
            synthetic.label = f"Default diet for {pet.name}"
            synthetic.type = "packaged"
            synthetic.brand = None
            synthetic.detail = None
            synthetic.pack_size_g = None

            result = resolve_food_signal(db, synthetic, pet, condition_names)
            if result.products:
                for prod in result.products[:3]:
                    sku_id = prod.get("sku_id")
                    if not sku_id or sku_id in existing_ids or sku_id in seen_skus:
                        continue
                    product, category = _lookup_sku(db, sku_id)
                    if not product or category != "food":
                        continue
                    rec = _food_to_recommendation(
                        product,
                        reason=f"Recommended for {_get_pet_life_stage(pet)} {pet.breed or 'pet'}".strip(),
                        priority="medium",
                    )
                    recommendations.append(rec)
                    seen_skus.add(sku_id)
                    existing_ids.add(sku_id)
        except Exception as exc:
            logger.warning("Generic food signal fallback failed: %s", exc)

    # Exclude previously bought items by name similarity
    bought_names = _get_bought_names(db, pet_id)
    recommendations = [
        r for r in recommendations
        if not _is_previously_bought(r["name"], bought_names)
    ]

    return recommendations[:15]


def _get_bought_names(db: Session, pet_id) -> set:
    """Return set of lowercased item names from pet_preferences for this pet."""
    rows = PetPreferenceRepository(db).find_item_names_by_pet(pet_id)
    return {row[0].strip().lower() for row in rows if row[0]}


def _is_previously_bought(product_name: str, bought_names: set) -> bool:
    """
    Return True if this product name matches any previously bought item name.
    Uses substring matching in both directions (case-insensitive).
    """
    product_lower = product_name.strip().lower()
    for bought in bought_names:
        if bought in product_lower or product_lower in bought:
            return True
    return False


def get_last_bought(
    db: Session,
    pet_id,
    exclude_names: set | None = None,
) -> list[dict]:
    """
    Return previously bought items for a pet from pet_preferences.

    Args:
        exclude_names: Set of lowercased names to exclude (e.g. items currently
                       in cart, or items just ordered).

    Returns:
        List of {name, used_count, last_bought_at, category}
        Empty list if no history or all history is excluded.
    """
    rows = PetPreferenceRepository(db).find_recent_by_pet(pet_id, limit=10)
    result = []
    for row in rows:
        name = (row.item_name or "").strip()
        if not name:
            continue
        if exclude_names and name.lower() in exclude_names:
            continue
        result.append({
            "name": name,
            "used_count": int(row.used_count or 0),
            "last_bought_at": row.updated_at,
            "category": row.category,
        })
    return result


def _format_last_bought_label(last_bought_at) -> str:
    """Convert a datetime to a human-readable recency label."""
    if not last_bought_at:
        return ""
    today = date.today()
    try:
        if hasattr(last_bought_at, "date"):
            bought_date = last_bought_at.date()
        else:
            bought_date = last_bought_at
        delta = (today - bought_date).days
        if delta == 0:
            return "Today"
        elif delta == 1:
            return "Yesterday"
        else:
            return f"{delta} days ago"
    except Exception:
        return ""


# --- Place Order ---

async def place_order(
    db: Session,
    pet_id,
    user_id,
    payment_method: str,
    address: dict | None = None,
    coupon: str | None = None,
    client_items: list[dict] | None = None,
) -> dict:
    """
    Place an order from items currently in cart (in_cart=True).

    Creates an Order record and clears cart items.
    client_items, when provided, are used for the order totals instead of
    the DB cart (frontend cart may include care-plan items not synced to DB).
    """
    # Always load DB cart items for cleanup and preference tracking
    in_cart = CartItemRepository(db).find_in_cart_by_pet(pet_id)

    if client_items:
        # Resolve server-side prices from DB; ignore client-supplied price values.
        verified_items: list[dict] = []
        for client_item in client_items:
            product, _ = _lookup_sku(db, client_item["id"])
            if product is not None:
                server_price = int(product.discounted_price)
            else:
                # Fall back to DB cart price if SKU not in catalog (care-plan items)
                db_item = CartItemRepository(db).find_by_pet_and_product(pet_id, client_item["id"])
                server_price = db_item.price if db_item else client_item.get("price", 0)
            verified_items.append({
                "name": client_item["name"],
                "price": server_price,
                "quantity": client_item["quantity"],
            })
        items_desc = "; ".join(
            f"{item['name']} x{item['quantity']} (Rs.{item['price'] * item['quantity']})"
            for item in verified_items
        )
        subtotal = sum(item["price"] * item["quantity"] for item in verified_items)
        client_items = verified_items
    else:
        if not in_cart:
            raise ValueError("No items in cart")
        items_desc = "; ".join(
            f"{item.name} x{item.quantity} (Rs.{item.price * item.quantity})"
            for item in in_cart
        )
        subtotal = sum(item.price * item.quantity for item in in_cart)
    discount = round(subtotal * 0.1) if coupon else 0
    delivery = 0 if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_FEE
    total = subtotal - discount + delivery

    order_id = f"PC-{uuid.uuid4().hex[:8].upper()}"

    # Determine payment status — COD confirmed immediately, online handled via Razorpay
    pay_status = "cod" if payment_method == "cod" else "pending"

    # Create order record
    order = Order(
        user_id=user_id,
        pet_id=pet_id,
        category="dashboard_order",
        items_description=items_desc,
        status="pending",
        payment_status=pay_status,
        admin_notes=f"Order {order_id} | Payment: {payment_method} | Total: Rs.{total}"
                    + (f" | Coupon: {coupon} (-Rs.{discount})" if coupon else "")
                    + (f" | Address: {address}" if address else ""),
    )
    db.add(order)

    # Build response items using server-verified prices
    if client_items:
        order_items = [
            {
                "product_id": None,
                "name": item["name"],
                "icon": None,
                "price": item["price"],
                "quantity": item["quantity"],
                "total": item["price"] * item["quantity"],
            }
            for item in client_items
        ]
    else:
        order_items = [
            {
                "product_id": item.product_id,
                "name": item.name,
                "icon": item.icon,
                "price": item.price,
                "quantity": item.quantity,
                "total": item.price * item.quantity,
            }
            for item in in_cart
        ]

    # Record each ordered item into pet_preferences so purchase history is tracked.
    # Look up the SKU to tag the preference category; fall back to "dashboard_order".
    from app.services.shared.recommendation_service import record_preference
    for item in in_cart:
        _product, sku_category = _lookup_sku(db, item.product_id)
        item_category = sku_category or "dashboard_order"
        record_preference(db, pet_id, item_category, item.name, "custom")

    # Clear cart
    for item in in_cart:
        db.delete(item)

    db.commit()

    # C4: Send WhatsApp confirmation — non-blocking, failure must not rollback order
    asyncio.create_task(_send_order_confirmation(db, user_id, pet_id, order_items, total))

    return {
        "order_id": order_id,
        "items": order_items,
        "subtotal": subtotal,
        "discount": discount,
        "delivery": delivery,
        "total": total,
        "payment_method": payment_method,
        "status": "confirmed",
    }


async def _send_order_confirmation(
    db: Session,
    user_id,
    pet_id,
    order_items: list[dict],
    total: int,
) -> None:
    """
    Send a WhatsApp order confirmation message to the user.

    C4: "Your [Product Name] for [Pet Name] has been ordered! Expected delivery: [date]."
    Runs as a background task — any failure is logged but never raises.
    """
    from app.services.whatsapp.whatsapp_sender import send_text_message

    try:
        user = UserRepository(db).find_by_id(user_id)
        from app.repositories.pet_repository import PetRepository
        pet_repo = PetRepository(db)
        pet = pet_repo.find_by_id(pet_id)
        if not user or not user.mobile_display:
            logger.warning("Order confirmation skipped — no phone for user %s", user_id)
            return

        pet_name = pet.name if pet else "your pet"
        product_names = ", ".join(i["name"] for i in order_items[:3])
        if len(order_items) > 3:
            product_names += f" and {len(order_items) - 3} more"

        # Expected delivery: 3–5 business days
        delivery_date = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%d %b %Y")

        message = (
            f"Your {product_names} for {pet_name} has been ordered! "
            f"Expected delivery: {delivery_date}. "
            f"Total paid: Rs.{total}. Thank you for ordering with PetCircle! \U0001f43e"
        )

        await send_text_message(db, user.mobile_display, message)
        logger.info("Order confirmation sent to %s for pet %s", user.mobile_display, pet_id)
    except Exception as exc:
        # Never raise — order is already committed
        logger.error("Failed to send order confirmation: %s", exc)


# --- Helpers ---

def _serialize_cart_item(item: CartItem) -> dict:
    """Serialize a CartItem to a dict for API response."""
    return {
        "id": str(item.id),
        "product_id": item.product_id,
        "icon": item.icon,
        "name": item.name,
        "sub": item.sub,
        "price": item.price,
        "tag": item.tag,
        "tag_color": item.tag_color,
        "in_cart": item.in_cart,
        "quantity": item.quantity,
    }


def _food_to_recommendation(
    product: ProductFood,
    reason: str,
    priority: str = "medium",
    tag: str | None = None,
    tag_color: str | None = None,
) -> dict:
    """Convert a ProductFood row to a recommendation dict."""
    return {
        "product_id": product.sku_id,
        "icon": _category_icon("food"),
        "name": _food_display_name(product),
        "sub": _food_sub(product),
        "price": int(product.discounted_price),
        "tag": tag,
        "tag_color": tag_color,
        "reason": reason,
        "priority": priority,
        "category": "food",
    }


def _supplement_to_recommendation(
    product: ProductSupplement,
    reason: str,
    priority: str = "medium",
    tag: str | None = None,
    tag_color: str | None = None,
) -> dict:
    """Convert a ProductSupplement row to a recommendation dict."""
    return {
        "product_id": product.sku_id,
        "icon": _category_icon("supplement"),
        "name": _supplement_display_name(product),
        "sub": _supplement_sub(product),
        "price": int(product.discounted_price),
        "tag": tag,
        "tag_color": tag_color,
        "reason": reason,
        "priority": priority,
        "category": "supplement",
    }



