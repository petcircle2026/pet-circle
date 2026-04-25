"""
Health Service Orchestrator

Coordinates health data retrieval and calculation.
Uses repositories for data access + domain logic for calculations.

This is the main entry point for all health-related operations.
"""

from uuid import UUID
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.pet_repository import PetRepository
from app.repositories.preventive_repository import PreventiveRepository
from app.repositories.health_repository import HealthRepository
from app.domain.health.preventive_logic import (
    get_preventive_status,
    days_until_due,
    get_frequency_label,
)


class HealthService:
    """
    Orchestrates health-related operations.

    Responsible for:
    - Querying repositories
    - Applying domain logic
    - Returning aggregated results

    Does NOT:
    - Know about WhatsApp messages
    - Access database directly
    - Format responses for display
    """

    def __init__(self, db: Session):
        self.db = db
        self.pet_repo = PetRepository(db)
        self.preventive_repo = PreventiveRepository(db)
        self.health_repo = HealthRepository(db)

    def get_overdue_preventives(self, pet_id: UUID) -> list[dict]:
        """Get all overdue preventive items for a pet."""
        today = date.today()
        overdue_records = self.preventive_repo.get_overdue_by_pet(pet_id, today)

        result = []
        for record in overdue_records:
            item_name = self._get_preventive_item_name(record)
            days_overdue = (today - record.next_due_date).days

            result.append(
                {
                    "id": str(record.id),
                    "name": item_name,
                    "last_done": record.last_done_date.isoformat(),
                    "next_due": record.next_due_date.isoformat(),
                    "days_overdue": days_overdue,
                }
            )

        return result

    def get_upcoming_preventives(self, pet_id: UUID, days_ahead: int = 30) -> list[dict]:
        """Get upcoming preventive items within days_ahead."""
        today = date.today()
        upcoming_records = self.preventive_repo.get_upcoming_by_pet(
            pet_id, today, days_ahead
        )

        result = []
        for record in upcoming_records:
            item_name = self._get_preventive_item_name(record)
            days_until = (record.next_due_date - today).days

            result.append(
                {
                    "id": str(record.id),
                    "name": item_name,
                    "last_done": record.last_done_date.isoformat(),
                    "next_due": record.next_due_date.isoformat(),
                    "days_until": days_until,
                }
            )

        return result

    def get_weight_trend(self, pet_id: UUID, limit: int = 12) -> list[dict]:
        """Get weight history trend."""
        weights = self.health_repo.get_weight_history(pet_id, limit=limit)

        return [
            {
                "date": w.recorded_at.isoformat(),
                "weight": float(w.weight) if w.weight else None,
                "bcs": w.bcs,
            }
            for w in reversed(weights)  # Oldest first
        ]

    def get_active_conditions_summary(self, pet_id: UUID) -> list[dict]:
        """Get summary of active conditions."""
        conditions = self.health_repo.get_active_conditions_with_relations(pet_id)

        result = []
        for condition in conditions:
            result.append(
                {
                    "id": str(condition.id),
                    "name": condition.name,
                    "diagnosis_date": condition.diagnosis_date.isoformat(),
                    "status": condition.status,
                    "medication_count": len(condition.medications) if condition.medications else 0,
                    "monitoring_count": len(condition.monitoring_items) if condition.monitoring_items else 0,
                }
            )

        return result

    # ---- Helper methods ----

    def _is_preventive_type_up_to_date(
        self, records: list, preventive_type: str, today: date
    ) -> bool:
        """Check if a preventive type is up to date."""
        for record in records:
            if (
                record.preventive_master
                and record.preventive_master.type == preventive_type
            ):
                status = get_preventive_status(record.next_due_date, today)
                return status in ("up_to_date", "upcoming")

        # If no records found, not up to date
        return False

    def _get_last_checkup_days_ago(self, pet_id: UUID, today: date) -> int | None:
        """Get days since last checkup."""
        # Look for checkup records in preventive_records
        checkup_records = self.preventive_repo.get_by_pet_with_master(pet_id)

        last_checkup_date = None
        for record in checkup_records:
            if (
                record.preventive_master
                and record.preventive_master.type == "checkup"
            ):
                if (
                    last_checkup_date is None
                    or record.last_done_date > last_checkup_date
                ):
                    last_checkup_date = record.last_done_date

        if last_checkup_date is None:
            return None

        return (today - last_checkup_date).days

    def _are_conditions_monitored(self, conditions: list) -> bool:
        """Check if all active conditions have monitoring items."""
        if not conditions:
            return True  # No conditions = no monitoring needed

        for condition in conditions:
            if (
                not condition.monitoring_items
                or len(condition.monitoring_items) == 0
            ):
                return False

        return True

    def _get_latest_diet_record(self, pet_id: UUID):
        """Get latest diet record for pet."""
        from app.models.diet_item import DietItem

        record = (
            self.db.query(DietItem)
            .filter(DietItem.pet_id == pet_id)
            .order_by(DietItem.created_at.desc())
            .first()
        )
        return record

    def _get_preventive_item_name(self, record) -> str:
        """Get human-readable name of preventive item."""
        if record.preventive_master:
            return record.preventive_master.name
        if record.custom_preventive_item:
            return record.custom_preventive_item.name
        return "Unknown"
