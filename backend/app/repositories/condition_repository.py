"""
Condition Repository — Managing pet health conditions.

Provides access to pet conditions (illnesses, chronic diseases, etc.).
"""

from uuid import UUID
from typing import List
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.models.health.condition import Condition
from app.models.health.aggregated_condition import AggregatedCondition


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

    def find_by_pet_and_active_with_relations(self, pet_id: UUID, condition_types: set[str] | None = None) -> List[Condition]:
        """
        Find active conditions for a pet with medications and monitoring eagerly loaded.
        Optionally filter by condition types. Used by health_trends_service.
        """
        query = (
            self.db.query(Condition)
            .options(
                selectinload(Condition.medications),
                selectinload(Condition.monitoring),
            )
            .filter(Condition.pet_id == pet_id, Condition.is_active == True)
        )
        if condition_types:
            query = query.filter(Condition.condition_type.in_(condition_types))
        return query.order_by(Condition.created_at.desc()).all()

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

    # ------------------------------------------------------------------
    # Aggregated condition queries
    # ------------------------------------------------------------------

    def get_aggregated_conditions_for_pet(self, pet_id: UUID) -> List[AggregatedCondition]:
        """Return all aggregated condition family rows for a pet, ordered by last_record_date desc."""
        return (
            self.db.query(AggregatedCondition)
            .filter(AggregatedCondition.pet_id == pet_id)
            .order_by(AggregatedCondition.last_record_date.desc().nullslast())
            .all()
        )

    def upsert_aggregated_condition(self, pet_id: UUID, family_data: dict) -> AggregatedCondition:
        """Insert or update an aggregated condition family row.

        Matches on (pet_id, name). Updates all fields if existing row found.
        Returns the persisted AggregatedCondition instance.
        """
        name = family_data.get("name", "")
        existing = (
            self.db.query(AggregatedCondition)
            .filter(
                AggregatedCondition.pet_id == pet_id,
                AggregatedCondition.name == name,
            )
            .first()
        )
        if existing:
            for key, val in family_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, val)
            existing.updated_at = datetime.now(timezone.utc)
            self.db.flush()
            return existing
        else:
            row = AggregatedCondition(
                pet_id=pet_id,
                **{k: v for k, v in family_data.items() if k != "pet_id"},
            )
            self.db.add(row)
            self.db.flush()
            return row
