"""
Conflict Flag Repository — Tracks date conflicts in preventive records.

Manages conflict detection and resolution for extracted preventive dates.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from app.models.health.conflict_flag import ConflictFlag


class ConflictFlagRepository:
    """Manages conflict flag records."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, conflict_id: UUID) -> ConflictFlag | None:
        """Find a conflict flag by ID."""
        return (
            self.db.query(ConflictFlag)
            .filter(ConflictFlag.id == conflict_id)
            .first()
        )

    def find_pending_by_record(self, preventive_record_id: UUID) -> ConflictFlag | None:
        """Find pending conflict for a preventive record."""
        return (
            self.db.query(ConflictFlag)
            .filter(
                ConflictFlag.preventive_record_id == preventive_record_id,
                ConflictFlag.status == "pending",
            )
            .first()
        )

    def find_all_pending_by_record(self, preventive_record_id: UUID) -> List[ConflictFlag]:
        """Find all pending conflicts for a preventive record."""
        return (
            self.db.query(ConflictFlag)
            .filter(
                ConflictFlag.preventive_record_id == preventive_record_id,
                ConflictFlag.status == "pending",
            )
            .all()
        )

    def find_pending_by_records(self, record_ids: List[str]) -> List[ConflictFlag]:
        """Find all pending conflicts for a list of record IDs, ordered by created_at descending."""
        from uuid import UUID as UUIDType
        return (
            self.db.query(ConflictFlag)
            .filter(
                ConflictFlag.preventive_record_id.in_(record_ids),
                ConflictFlag.status == "pending",
            )
            .order_by(ConflictFlag.created_at.desc())
            .all()
        )

    def create(
        self,
        preventive_record_id: UUID,
        new_date,
        status: str = "pending",
    ) -> ConflictFlag:
        """Create a new conflict flag."""
        conflict = ConflictFlag(
            preventive_record_id=preventive_record_id,
            new_date=new_date,
            status=status,
        )
        self.db.add(conflict)
        self.db.flush()
        return conflict

    def update_status(self, conflict_id: UUID, new_status: str) -> ConflictFlag | None:
        """Update conflict status."""
        conflict = (
            self.db.query(ConflictFlag)
            .filter(ConflictFlag.id == conflict_id)
            .first()
        )
        if conflict:
            conflict.status = new_status
            self.db.merge(conflict)
            self.db.flush()
            return conflict
        return None

    def find_latest_pending_for_user(self, user_id: UUID) -> ConflictFlag | None:
        """Find the most recently created pending conflict for any of the user's pets."""
        from app.models.health.preventive_record import PreventiveRecord
        from app.models.core.pet import Pet
        return (
            self.db.query(ConflictFlag)
            .join(PreventiveRecord, ConflictFlag.preventive_record_id == PreventiveRecord.id)
            .join(Pet, PreventiveRecord.pet_id == Pet.id)
            .filter(
                Pet.user_id == user_id,
                Pet.is_deleted == False,
                ConflictFlag.status == "pending",
            )
            .order_by(ConflictFlag.created_at.desc())
            .first()
        )

    def find_pet_by_conflict_id(self, conflict_id: UUID):
        """Find the pet associated with a conflict flag."""
        from app.models.health.preventive_record import PreventiveRecord
        from app.models.core.pet import Pet
        return (
            self.db.query(Pet)
            .join(PreventiveRecord, Pet.id == PreventiveRecord.pet_id)
            .join(ConflictFlag, ConflictFlag.preventive_record_id == PreventiveRecord.id)
            .filter(ConflictFlag.id == conflict_id)
            .first()
        )
