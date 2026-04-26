"""
DashboardVisit Repository — Tracks dashboard access for nudge level calculation.

Records when users access the dashboard for a pet to determine nudge engagement level.
"""

from uuid import UUID
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import DashboardVisit


class DashboardVisitRepository:
    """Access to dashboard visit logs."""

    def __init__(self, db: Session):
        self.db = db

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count total visits for a pet."""
        return (
            self.db.query(func.count(DashboardVisit.id))
            .filter(DashboardVisit.pet_id == pet_id)
            .scalar()
            or 0
        )

    def create(self, user_id: UUID, pet_id: UUID, token: str) -> DashboardVisit:
        """Record a new dashboard visit."""
        visit = DashboardVisit(
            user_id=user_id,
            pet_id=pet_id,
            token=token,
        )
        self.db.add(visit)
        self.db.flush()
        return visit
