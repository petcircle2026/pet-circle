"""
Condition Repository — Managing pet health conditions.

Provides access to pet conditions (illnesses, chronic diseases, etc.).
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from app.models.health.condition import Condition


class ConditionRepository:
    """Access to pet condition records."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_pet(self, pet_id: UUID) -> List[Condition]:
        """Find all conditions for a pet."""
        return (
            self.db.query(Condition)
            .filter(Condition.pet_id == pet_id)
            .all()
        )

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count conditions for a pet."""
        return (
            self.db.query(Condition)
            .filter(Condition.pet_id == pet_id)
            .count()
        )

    def find_active_by_pet(self, pet_id: UUID) -> List[Condition]:
        """Find active (non-resolved) conditions for a pet."""
        return (
            self.db.query(Condition)
            .filter(
                Condition.pet_id == pet_id,
                Condition.is_resolved == False,
            )
            .all()
        )

    def find_by_pet_and_active(self, pet_id: UUID) -> List[Condition]:
        """Find active conditions for a pet, ordered by creation date."""
        return (
            self.db.query(Condition)
            .filter(Condition.pet_id == pet_id, Condition.is_active == True)
            .order_by(Condition.created_at.asc())
            .all()
        )

    def create(
        self,
        pet_id: UUID,
        condition_name: str,
    ) -> Condition:
        """Create a new condition record."""
        condition = Condition(
            pet_id=pet_id,
            condition_name=condition_name,
        )
        self.db.add(condition)
        self.db.flush()
        return condition
