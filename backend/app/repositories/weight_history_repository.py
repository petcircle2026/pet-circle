"""
Weight History Repository — Pet weight tracking.

Manages weight history records and queries for pets.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.health.weight_history import WeightHistory


class WeightHistoryRepository:
    """Manages weight history data."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_pet(self, pet_id: UUID) -> List[WeightHistory]:
        """Find all weight history records for a pet, ordered by date (desc)."""
        return (
            self.db.query(WeightHistory)
            .filter(WeightHistory.pet_id == pet_id)
            .order_by(desc(WeightHistory.recorded_at))
            .all()
        )

    def create(self, weight_history: WeightHistory) -> WeightHistory:
        """Create a new weight history record."""
        self.db.add(weight_history)
        self.db.flush()
        return weight_history

    def update(self, weight_history: WeightHistory) -> WeightHistory:
        """Update a weight history record."""
        self.db.merge(weight_history)
        self.db.flush()
        return weight_history

    def delete(self, record_id: UUID) -> bool:
        """Delete a weight history record."""
        record = self.db.query(WeightHistory).filter(WeightHistory.id == record_id).first()
        if record:
            self.db.delete(record)
            self.db.flush()
            return True
        return False
