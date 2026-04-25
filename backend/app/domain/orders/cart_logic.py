"""
Pure cart calculation logic (no DB, no I/O).

Handles cart totals, item validation, and delivery fee calculations.
All functions are pure and testable.
"""

from typing import NamedTuple

FREE_DELIVERY_THRESHOLD = 599  # Free delivery for orders >= Rs.599
DELIVERY_FEE = 49
MAX_QUANTITY_PER_ITEM = 10
MIN_ORDER_VALUE = 99  # Minimum order value in INR


class CartSummary(NamedTuple):
    """Summary of cart calculations."""

    item_count: int
    subtotal_paise: int  # in paise (1 INR = 100 paise)
    subtotal_inr: float
    delivery_fee_paise: int
    delivery_fee_inr: float
    total_paise: int
    total_inr: float
    free_delivery: bool


def calculate_delivery_fee(subtotal_paise: int) -> int:
    """
    Calculate delivery fee based on subtotal.

    Args:
        subtotal_paise: Total in paise (1 INR = 100 paise)

    Returns:
        Delivery fee in paise (0 if free delivery applies)
    """
    subtotal_inr = subtotal_paise / 100.0
    if subtotal_inr >= FREE_DELIVERY_THRESHOLD:
        return 0
    return DELIVERY_FEE * 100  # Convert to paise


def calculate_cart_summary(items: list[dict]) -> CartSummary:
    """
    Calculate cart summary from a list of items.

    Args:
        items: List of dicts with keys:
            - price_paise (int): Price in paise
            - quantity (int): Quantity

    Returns:
        CartSummary with all calculations
    """
    if not items:
        return CartSummary(
            item_count=0,
            subtotal_paise=0,
            subtotal_inr=0.0,
            delivery_fee_paise=0,
            delivery_fee_inr=0.0,
            total_paise=0,
            total_inr=0.0,
            free_delivery=True,
        )

    # Sum up subtotal
    subtotal_paise = sum(item.get("price_paise", 0) * item.get("quantity", 0) for item in items)
    item_count = sum(item.get("quantity", 0) for item in items)

    # Calculate delivery fee
    delivery_fee_paise = calculate_delivery_fee(subtotal_paise)
    free_delivery = delivery_fee_paise == 0

    # Calculate totals
    total_paise = subtotal_paise + delivery_fee_paise

    return CartSummary(
        item_count=item_count,
        subtotal_paise=subtotal_paise,
        subtotal_inr=round(subtotal_paise / 100.0, 2),
        delivery_fee_paise=delivery_fee_paise,
        delivery_fee_inr=round(delivery_fee_paise / 100.0, 2),
        total_paise=total_paise,
        total_inr=round(total_paise / 100.0, 2),
        free_delivery=free_delivery,
    )


def is_valid_quantity(quantity: int) -> tuple[bool, str]:
    """
    Validate item quantity.

    Args:
        quantity: Quantity to add/update

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(quantity, int):
        return False, "Quantity must be an integer"

    if quantity < 1:
        return False, "Quantity must be at least 1"

    if quantity > MAX_QUANTITY_PER_ITEM:
        return False, f"Maximum quantity is {MAX_QUANTITY_PER_ITEM}"

    return True, ""


def is_valid_price(price_paise: int) -> tuple[bool, str]:
    """
    Validate product price.

    Args:
        price_paise: Price in paise (1 INR = 100 paise)

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(price_paise, int):
        return False, "Price must be an integer"

    if price_paise <= 0:
        return False, "Price must be positive"

    if price_paise > 10_000_000:  # Max 100k INR
        return False, "Price seems unreasonably high"

    return True, ""


def meets_minimum_order(subtotal_paise: int) -> tuple[bool, int]:
    """
    Check if cart meets minimum order value.

    Args:
        subtotal_paise: Cart subtotal in paise

    Returns:
        (meets_minimum, shortfall_paise) — if meets_minimum=True, shortfall=0
    """
    min_paise = MIN_ORDER_VALUE * 100
    if subtotal_paise >= min_paise:
        return True, 0
    return False, min_paise - subtotal_paise
