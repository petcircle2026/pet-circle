"""
Cart Item Repository — Shopping cart management.

Manages cart items for pet-related products.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.orders.cart_item import CartItem


class CartItemRepository:
    """Manages shopping cart items."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, item_id: UUID) -> CartItem | None:
        """Fetch cart item by ID."""
        return (
            self.db.query(CartItem)
            .filter(CartItem.id == item_id)
            .first()
        )

    def find_by_pet(self, pet_id: UUID) -> List[CartItem]:
        """Fetch all cart items for a pet."""
        return (
            self.db.query(CartItem)
            .filter(CartItem.pet_id == pet_id)
            .all()
        )

    def find_by_pet_and_product(self, pet_id: UUID, product_id: UUID) -> CartItem | None:
        """Find cart item for a pet and product."""
        return (
            self.db.query(CartItem)
            .filter(CartItem.pet_id == pet_id, CartItem.product_id == product_id)
            .first()
        )

    def create(self, item: CartItem) -> CartItem:
        """Create a new cart item."""
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, item: CartItem) -> CartItem:
        """Update a cart item."""
        self.db.merge(item)
        self.db.flush()
        return item

    def delete(self, item_id: UUID) -> bool:
        """Delete a cart item."""
        item = self.find_by_id(item_id)
        if item:
            self.db.delete(item)
            self.db.flush()
            return True
        return False

    def delete_by_pet(self, pet_id: UUID) -> int:
        """Delete all cart items for a pet."""
        count = (
            self.db.query(CartItem)
            .filter(CartItem.pet_id == pet_id)
            .delete()
        )
        self.db.flush()
        return count

    def has_item(self, item_id: UUID) -> bool:
        """Check if cart item exists."""
        return (
            self.db.query(CartItem.id)
            .filter(CartItem.id == item_id)
            .first() is not None
        )

    def find_active_by_pet(self, pet_id: UUID) -> List[CartItem]:
        """Find non-expired cart items for a pet."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return (
            self.db.query(CartItem)
            .filter(
                CartItem.pet_id == pet_id,
                (CartItem.cart_expires_at.is_(None)) | (CartItem.cart_expires_at > now),
            )
            .order_by(CartItem.created_at.asc())
            .all()
        )

    def find_in_cart_by_pet(self, pet_id: UUID) -> List[CartItem]:
        """Find all items marked in_cart for a pet."""
        return (
            self.db.query(CartItem)
            .filter(CartItem.pet_id == pet_id, CartItem.in_cart == True)
            .all()
        )

    def find_product_ids_by_pet(self, pet_id: UUID) -> List:
        """Find all product IDs in cart for a pet."""
        return (
            self.db.query(CartItem.product_id)
            .filter(CartItem.pet_id == pet_id)
            .all()
        )
