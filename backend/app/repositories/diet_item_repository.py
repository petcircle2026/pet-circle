"""
Diet Item Repository — Managing diet records for pets.

Provides CRUD operations for diet items (food, supplements, homemade meals).
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from app.models.nutrition.diet_item import DietItem


class DietItemRepository:
    """Access to diet item records."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_pet(self, pet_id: UUID) -> List[DietItem]:
        """Find all diet items for a pet."""
        return (
            self.db.query(DietItem)
            .filter(DietItem.pet_id == pet_id)
            .all()
        )

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count diet items for a pet."""
        return (
            self.db.query(DietItem)
            .filter(DietItem.pet_id == pet_id)
            .count()
        )

    def count_by_pet_and_type(self, pet_id: UUID, item_type: str) -> int:
        """Count diet items of a specific type for a pet."""
        return (
            self.db.query(DietItem)
            .filter(
                DietItem.pet_id == pet_id,
                DietItem.type == item_type,
            )
            .count()
        )

    def create(
        self,
        pet_id: UUID,
        item_type: str,
        item_name: str,
        quantity: str | None = None,
        unit: str | None = None,
        frequency_per_day: int | None = None,
    ) -> DietItem:
        """Create a new diet item."""
        item = DietItem(
            pet_id=pet_id,
            item_type=item_type,
            item_name=item_name,
            quantity=quantity,
            unit=unit,
            frequency_per_day=frequency_per_day,
        )
        self.db.add(item)
        self.db.flush()
        return item
