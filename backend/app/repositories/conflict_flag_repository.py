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
