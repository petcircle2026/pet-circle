"""
OrderService â€” Orchestrator for cart and order operations.

Responsible for:
1. Using cart_logic for calculations
2. Delegating to repositories for data access
3. Coordinating cart CRUD and order creation

This service bridges the domain layer (cart_logic) with existing order handlers.
"""

import logging
from sqlalchemy.orm import Session

from app.domain.orders.cart_logic import calculate_cart_summary, meets_minimum_order

logger = logging.getLogger(__name__)


class OrderService:
    """
    Orchestrates cart and order operations.

    Thin wrapper over existing order.py handlers. Will gradually absorb
    logic as we decompose the monolith.
    """

    def __init__(self, db: Session):
        """
        Initialize service.

        Args:
            db: SQLAlchemy Session instance
        """
        self.db = db

    async def get_cart_summary(self, pet_id) -> dict:
        """
        Get cart summary with calculated totals.

        Routes to existing cart_service handlers.
        """
        from app.services.dashboard.cart_service import get_cart

        try:
            cart = await get_cart(self.db, pet_id)
            return cart
        except Exception as e:
            logger.exception("Failed to get cart: %s", str(e))
            raise

    async def add_to_cart(self, pet_id, product_id: str, quantity: int) -> dict:
        """
        Add item to cart.

        Routes to existing cart_service handlers.
        """
        from app.services.dashboard.cart_service import add_to_cart as add_to_cart_handler

        try:
            result = await add_to_cart_handler(self.db, pet_id, product_id, quantity)
            return result
        except Exception as e:
            logger.exception("Failed to add to cart: %s", str(e))
            raise

    async def remove_from_cart(self, pet_id, cart_item_id) -> bool:
        """
        Remove item from cart.

        Routes to existing cart_service handlers.
        """
        from app.services.dashboard.cart_service import remove_from_cart as remove_from_cart_handler

        try:
            result = await remove_from_cart_handler(self.db, pet_id, cart_item_id)
            return result
        except Exception as e:
            logger.exception("Failed to remove from cart: %s", str(e))
            raise

    async def create_order(self, user_id, pet_id, items: list[dict]) -> dict:
        """
        Create order from cart items.

        Routes to existing order_service handlers.
        """
        from app.services.whatsapp.order_service import create_order as create_order_handler

        try:
            order = await create_order_handler(self.db, user_id, pet_id, items)
            return order
        except Exception as e:
            logger.exception("Failed to create order: %s", str(e))
            raise

