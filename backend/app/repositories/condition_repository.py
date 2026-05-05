"""
Condition Repository — Managing pet health conditions.

Provides access to pet conditions (illnesses, chronic diseases, etc.).
"""

from uuid import UUID
from typing import List
from datetime import datetime, timezone

from sqlalchemy import text as sa_text
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

    # Condition types and names shown on dashboard surfaces (Ask Your Vet, Overview).
    DISPLAYABLE_CONDITION_TYPES: frozenset[str] = frozenset({"chronic", "episodic", "recurrent"})
    EXCLUDED_CONDITION_NAMES: frozenset[str] = frozenset({"Prescription Medications"})

    def find_displayable_active(self, pet_id: UUID) -> List[Condition]:
        """
        Return active conditions suitable for display on all dashboard surfaces
        (conditions tab, Ask Your Vet, Overview recognition bullets).

        Filters applied consistently:
        - condition_type restricted to DISPLAYABLE_CONDITION_TYPES
        - excludes synthetic entries in EXCLUDED_CONDITION_NAMES
        - excludes GPT-inferred conditions (source == 'inferred')
        """
        rows = (
            self.db.query(Condition)
            .options(
                selectinload(Condition.medications),
                selectinload(Condition.monitoring),
            )
            .filter(
                Condition.pet_id == pet_id,
                Condition.is_active == True,
                Condition.condition_type.in_(self.DISPLAYABLE_CONDITION_TYPES),
                Condition.source != "inferred",
            )
            .order_by(Condition.diagnosed_at.desc().nullslast(), Condition.name.asc())
            .all()
        )
        return [
            c for c in rows
            if c.name not in self.EXCLUDED_CONDITION_NAMES
        ]

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

    def get_aggregated_conditions_for_insights(self, pet_id: UUID):
        """
        Return aggregated condition rows with their latest episode condition loaded,
        ordered by last_record_date desc. Each row exposes vet_resolved and source
        via the latest_episode_condition relationship.
        """
        from sqlalchemy.orm import joinedload
        rows = (
            self.db.query(AggregatedCondition)
            .options(joinedload(AggregatedCondition.latest_episode_condition))
            .filter(AggregatedCondition.pet_id == pet_id)
            .order_by(AggregatedCondition.last_record_date.desc().nullslast(), AggregatedCondition.name.asc())
            .all()
        )

        class _Row:
            """Adapter to keep the same attribute interface as the old raw SQL rows."""
            __slots__ = (
                "condition_family_id", "name", "condition_type", "episode_dates",
                "diagnosed_at", "last_record_date", "medication_end_date",
                "latest_episode_condition_id", "soft_resolution", "recurrence_watch",
                "medications", "monitoring", "vet_resolved", "source",
            )

            def __init__(self, ac: AggregatedCondition):
                self.condition_family_id = ac.id
                self.name = ac.name
                self.condition_type = ac.condition_type
                self.episode_dates = ac.episode_dates
                self.diagnosed_at = ac.diagnosed_at
                self.last_record_date = ac.last_record_date
                self.medication_end_date = ac.medication_end_date
                self.latest_episode_condition_id = ac.latest_episode_condition_id
                self.soft_resolution = ac.soft_resolution
                self.recurrence_watch = ac.recurrence_watch
                self.medications = ac.medications
                self.monitoring = ac.monitoring
                lec = ac.latest_episode_condition
                self.vet_resolved = lec.vet_resolved if lec else None
                self.source = lec.source if lec else None

        return [
            r for r in (_Row(ac) for ac in rows)
            if (r.source or "").lower() != "inferred"
            and r.name not in self.EXCLUDED_CONDITION_NAMES
            and "(inferred)" not in (r.name or "").lower()
        ]

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
