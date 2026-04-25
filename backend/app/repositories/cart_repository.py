"""
Cart Repository â€” Shopping cart item access.

Manages:
- Cart CRUD operations
- Cart item quantity and removal
- Cart aggregations (total, item count)
"""

from uuid import UUID
from typing import List
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.commerce.cart_item import CartItem


class CartRepository:
    """Manages shopping cart items."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Cart Item CRUD ----

    def find_by_id(self, item_id: UUID) -> CartItem | None:
        """Fetch a cart item by ID."""
        return self.db.query(CartItem).filter(CartItem.id == item_id).first()

    def find_by_user_id(self, user_id: UUID) -> List[CartItem]:
        """Fetch all cart items for a user."""
        return self.db.query(CartItem).filter(CartItem.user_id == user_id).all()

    def find_item(
        self, user_id: UUID, product_id: UUID
    ) -> CartItem | None:
        """
        Find a specific cart item by user and product.

        Args:
            user_id: User ID
            product_id: Product ID (food, medicine, or supplement)

        Returns:
            CartItem or None if not in cart.
        """
        return (
            self.db.query(CartItem)
            .filter(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
            )
            .first()
        )

    def create(self, cart_item: CartItem) -> CartItem:
        """Add a product to cart."""
        self.db.add(cart_item)
        self.db.flush()
        return cart_item

    def update(self, cart_item: CartItem) -> CartItem:
        """Update a cart item (e.g., quantity)."""
        self.db.merge(cart_item)
        self.db.flush()
        return cart_item

    def delete(self, item_id: UUID) -> bool:
        """
        Remove a cart item.

        Args:
            item_id: CartItem ID

        Returns:
            True if item was found and deleted.
        """
        item = self.find_by_id(item_id)
        if item:
            self.db.delete(item)
            self.db.flush()
            return True
        return False

    def delete_by_product(self, user_id: UUID, product_id: UUID) -> bool:
        """
        Remove a cart item by product ID.

        Args:
            user_id: User ID
            product_id: Product ID

        Returns:
            True if item was found and deleted.
        """
        item = self.find_item(user_id, product_id)
        if item:
            self.db.delete(item)
            self.db.flush()
            return True
        return False

    # ---- Cart Operations ----

    def update_quantity(self, item_id: UUID, quantity: int) -> CartItem | None:
        """
        Update the quantity of a cart item.

        Args:
            item_id: CartItem ID
            quantity: New quantity (>0)

        Returns:
            Updated CartItem or None if not found.
        """
        item = self.find_by_id(item_id)
        if item:
            item.quantity = quantity
            self.db.merge(item)
            self.db.flush()
            return item
        return None

    def clear_cart(self, user_id: UUID) -> int:
        """
        Remove all items from a user's cart.

        Args:
            user_id: User ID

        Returns:
            Count of items deleted.
        """
        count = (
            self.db.query(CartItem).filter(CartItem.user_id == user_id).delete()
        )
        self.db.flush()
        return count

    # ---- Cart Aggregations ----

    def get_cart_count(self, user_id: UUID) -> int:
        """Get the total number of items in cart (quantity)."""
        total = (
            self.db.query(func.sum(CartItem.quantity))
            .filter(CartItem.user_id == user_id)
            .scalar() or 0
        )
        return int(total)

    def get_item_count(self, user_id: UUID) -> int:
        """Get the number of distinct products in cart."""
        count = (
            self.db.query(func.count(CartItem.id))
            .filter(CartItem.user_id == user_id)
            .scalar() or 0
        )
        return count

    def get_cart_total(self, user_id: UUID) -> Decimal:
        """
        Calculate total cart value.

        Assumes CartItem has a price and quantity field.

        Returns:
            Total value as Decimal.
        """
        total = (
            self.db.query(
                func.sum(CartItem.price * CartItem.quantity)
            )
            .filter(CartItem.user_id == user_id)
            .scalar() or Decimal("0.00")
        )
        return Decimal(total) if total else Decimal("0.00")

    def is_empty(self, user_id: UUID) -> bool:
        """Check if a user's cart is empty."""
        return self.get_item_count(user_id) == 0

    # ---- Batch Operations ----

    def bulk_add(self, items: List[CartItem]) -> List[CartItem]:
        """Add multiple items to cart at once."""
        self.db.add_all(items)
        self.db.flush()
        return items

    def bulk_update(self, items: List[CartItem]) -> List[CartItem]:
        """Update multiple cart items at once."""
        for item in items:
            self.db.merge(item)
        self.db.flush()
        return items

    def bulk_delete(self, item_ids: List[UUID]) -> int:
        """Delete multiple cart items."""
        count = (
            self.db.query(CartItem)
            .filter(CartItem.id.in_(item_ids))
            .delete()
        )
        self.db.flush()
        return count

    # ---- Specialized Queries ----

    def find_by_product_type(
        self, user_id: UUID, product_type: str
    ) -> List[CartItem]:
        """
        Find cart items of a specific product type.

        Args:
            user_id: User ID
            product_type: e.g. "food", "medicine", "supplement"

        Returns:
            List of matching cart items.
        """
        return (
            self.db.query(CartItem)
            .filter(
                CartItem.user_id == user_id,
                CartItem.product_type == product_type,
            )
            .all()
        )

    def find_oldest_items(self, user_id: UUID, limit: int = 5) -> List[CartItem]:
        """Find the oldest items in cart (added first)."""
        return (
            self.db.query(CartItem)
            .filter(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
            .limit(limit)
            .all()
        )

