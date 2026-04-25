"""
Preventive Repository — Centralized PreventiveRecord data access.

All queries about preventive care records (vaccines, deworming, flea/tick, etc.)
live here. This is the single source of truth for preventive data access.
"""

from uuid import UUID
from datetime import date, timedelta

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session, selectinload

from app.models.preventive_record import PreventiveRecord
from app.models.preventive_master import PreventiveMaster
from app.models.custom_preventive_item import CustomPreventiveItem


class PreventiveRepository:
    """Encapsulates all PreventiveRecord database queries."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Basic CRUD ----

    def get_by_id(self, record_id: UUID) -> PreventiveRecord | None:
        """Fetch a single preventive record by ID."""
        return self.db.query(PreventiveRecord).filter(PreventiveRecord.id == record_id).first()

    def create(
        self,
        pet_id: UUID,
        preventive_master_id: UUID | None,
        custom_preventive_item_id: UUID | None,
        last_done_date: date,
        next_due_date: date,
        status: str = "up_to_date",
    ) -> PreventiveRecord:
        """
        Create a new preventive record.

        Exactly one of preventive_master_id or custom_preventive_item_id must be set.

        Args:
            pet_id: Pet ID
            preventive_master_id: Standard item ID (vaccine, deworming, etc.)
            custom_preventive_item_id: User-custom item ID
            last_done_date: When preventive was last performed
            next_due_date: When it's due again
            status: 'up_to_date', 'upcoming', 'overdue', or 'cancelled'

        Returns: New PreventiveRecord instance (not yet committed)
        """
        record = PreventiveRecord(
            pet_id=pet_id,
            preventive_master_id=preventive_master_id,
            custom_preventive_item_id=custom_preventive_item_id,
            last_done_date=last_done_date,
            next_due_date=next_due_date,
            status=status,
        )
        self.db.add(record)
        return record

    # ---- Queries by pet ----

    def get_by_pet(self, pet_id: UUID) -> list[PreventiveRecord]:
        """Fetch all preventive records for a pet."""
        return (
            self.db.query(PreventiveRecord)
            .filter(PreventiveRecord.pet_id == pet_id)
            .order_by(desc(PreventiveRecord.created_at))
            .all()
        )

    def get_by_pet_with_master(self, pet_id: UUID) -> list[PreventiveRecord]:
        """
        Fetch all preventive records WITH their master items (eager load).

        Use when you need record names/types/frequencies.
        Prevents N+1: fetch records and types in one query.
        """
        return (
            self.db.query(PreventiveRecord)
            .filter(PreventiveRecord.pet_id == pet_id)
            .options(
                selectinload(PreventiveRecord.preventive_master),
                selectinload(PreventiveRecord.custom_preventive_item),
            )
            .order_by(desc(PreventiveRecord.created_at))
            .all()
        )

    def get_recent_by_pet(self, pet_id: UUID, limit: int = 10) -> list[PreventiveRecord]:
        """Fetch most recent preventive records for a pet."""
        return (
            self.db.query(PreventiveRecord)
            .filter(PreventiveRecord.pet_id == pet_id)
            .order_by(desc(PreventiveRecord.created_at))
            .limit(limit)
            .all()
        )

    # ---- Status queries (for reminders, nudges, care plan) ----

    def get_overdue_by_pet(self, pet_id: UUID, today: date) -> list[PreventiveRecord]:
        """
        Fetch overdue preventive records for a pet.

        Used by:
        - reminder_engine: to generate due reminders
        - care_plan_engine: to highlight gaps
        - nudge_engine: to identify action items
        """
        return (
            self.db.query(PreventiveRecord)
            .filter(
                and_(
                    PreventiveRecord.pet_id == pet_id,
                    PreventiveRecord.next_due_date < today,
                    PreventiveRecord.status != "cancelled",
                )
            )
            .order_by(PreventiveRecord.next_due_date)
            .all()
        )

    def get_upcoming_by_pet(
        self, pet_id: UUID, today: date, days_ahead: int = 30
    ) -> list[PreventiveRecord]:
        """
        Fetch upcoming (not yet due) preventive records within days_ahead.

        Used by care_plan_engine and nudge_scheduler.
        """
        due_window_end = today + timedelta(days=days_ahead)

        return (
            self.db.query(PreventiveRecord)
            .filter(
                and_(
                    PreventiveRecord.pet_id == pet_id,
                    PreventiveRecord.next_due_date >= today,
                    PreventiveRecord.next_due_date <= due_window_end,
                    PreventiveRecord.status != "cancelled",
                )
            )
            .order_by(PreventiveRecord.next_due_date)
            .all()
        )

    def get_by_status(self, pet_id: UUID, status: str) -> list[PreventiveRecord]:
        """Fetch records with a specific status ('up_to_date', 'overdue', etc.)."""
        return (
            self.db.query(PreventiveRecord)
            .filter(
                and_(PreventiveRecord.pet_id == pet_id, PreventiveRecord.status == status)
            )
            .all()
        )

    def get_by_type(
        self, pet_id: UUID, preventive_type: str
    ) -> list[PreventiveRecord]:
        """
        Fetch records of a specific type (vaccine, deworming, flea_tick, checkup).

        Used by preventive_calculator to find most recent of type.
        """
        return (
            self.db.query(PreventiveRecord)
            .join(
                PreventiveMaster,
                PreventiveRecord.preventive_master_id == PreventiveMaster.id,
                isouter=True,
            )
            .filter(
                and_(
                    PreventiveRecord.pet_id == pet_id,
                    PreventiveMaster.type == preventive_type,
                )
            )
            .order_by(desc(PreventiveRecord.last_done_date))
            .all()
        )

    def get_most_recent_by_type(
        self, pet_id: UUID, preventive_type: str
    ) -> PreventiveRecord | None:
        """Fetch the most recent record of a specific type."""
        return (
            self.db.query(PreventiveRecord)
            .join(
                PreventiveMaster,
                PreventiveRecord.preventive_master_id == PreventiveMaster.id,
                isouter=True,
            )
            .filter(
                and_(
                    PreventiveRecord.pet_id == pet_id,
                    PreventiveMaster.type == preventive_type,
                )
            )
            .order_by(desc(PreventiveRecord.last_done_date))
            .first()
        )

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count total preventive records for a pet."""
        return self.db.query(PreventiveRecord).filter(PreventiveRecord.pet_id == pet_id).count()

    def count_overdue_by_pet(self, pet_id: UUID, today: date) -> int:
        """Count overdue preventive records for a pet."""
        return (
            self.db.query(PreventiveRecord)
            .filter(
                and_(
                    PreventiveRecord.pet_id == pet_id,
                    PreventiveRecord.next_due_date < today,
                    PreventiveRecord.status != "cancelled",
                )
            )
            .count()
        )

    # ---- Update operations ----

    def update_status(self, record_id: UUID, new_status: str) -> PreventiveRecord | None:
        """Update preventive record status."""
        record = self.get_by_id(record_id)
        if record:
            record.status = new_status
            return record
        return None

    def update_next_due_date(
        self, record_id: UUID, new_next_due: date
    ) -> PreventiveRecord | None:
        """Update the next due date for a preventive record."""
        record = self.get_by_id(record_id)
        if record:
            record.next_due_date = new_next_due
            return record
        return None

    def cancel_record(self, record_id: UUID) -> PreventiveRecord | None:
        """Mark a preventive record as cancelled."""
        record = self.get_by_id(record_id)
        if record:
            record.status = "cancelled"
            return record
        return None

    # ---- Batch operations ----

    def get_all_overdue(self, today: date) -> list[PreventiveRecord]:
        """Fetch ALL overdue records across all pets (used by reminder engine)."""
        return (
            self.db.query(PreventiveRecord)
            .filter(
                and_(
                    PreventiveRecord.next_due_date < today,
                    PreventiveRecord.status != "cancelled",
                )
            )
            .all()
        )

    def delete_by_pet(self, pet_id: UUID) -> int:
        """Delete all preventive records for a pet (used on pet deletion)."""
        count = (
            self.db.query(PreventiveRecord)
            .filter(PreventiveRecord.pet_id == pet_id)
            .delete()
        )
        return count
