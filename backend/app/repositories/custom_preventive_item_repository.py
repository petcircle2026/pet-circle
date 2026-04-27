"""
Custom Preventive Item Repository — User-custom preventive items (supplements, medications).

Manages user-scoped custom preventive items that are not in the master list.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from app.models.preventive.custom_preventive_item import CustomPreventiveItem


class CustomPreventiveItemRepository:
    """Manages custom preventive item data."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, item_id: UUID) -> CustomPreventiveItem | None:
        """Fetch a custom item by ID."""
        return (
            self.db.query(CustomPreventiveItem)
            .filter(CustomPreventiveItem.id == item_id)
            .first()
        )

    def find_by_user_and_name(self, user_id: UUID, item_name: str) -> CustomPreventiveItem | None:
        """Find a custom item by user and item name."""
        return (
            self.db.query(CustomPreventiveItem)
            .filter(
                CustomPreventiveItem.user_id == user_id,
                CustomPreventiveItem.item_name == item_name,
            )
            .first()
        )

    def create(self, custom_item: CustomPreventiveItem) -> CustomPreventiveItem:
        """Create a new custom preventive item."""
        self.db.add(custom_item)
        self.db.flush()
        return custom_item

    def update(self, custom_item: CustomPreventiveItem) -> CustomPreventiveItem:
        """Update a custom preventive item."""
        self.db.merge(custom_item)
        self.db.flush()
        return custom_item

    def delete(self, item_id: UUID) -> bool:
        """Delete a custom item."""
        item = self.find_by_id(item_id)
        if item:
            self.db.delete(item)
            self.db.flush()
            return True
        return False

    def find_by_user(self, user_id: UUID) -> List[CustomPreventiveItem]:
        """Find all custom items for a user."""
        return (
            self.db.query(CustomPreventiveItem)
            .filter(CustomPreventiveItem.user_id == user_id)
            .all()
        )
