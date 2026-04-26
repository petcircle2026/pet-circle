"""
Deferred Care Plan Repository — Tracks deferred onboarding finalization.

Manages deferred care plan markers when document extractions are pending.
"""

from uuid import UUID
from typing import List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.preventive.deferred_care_plan_pending import DeferredCarePlanPending


class DeferredCarePlanRepository:
    """Manages deferred care plan pending records."""

    def __init__(self, db: Session):
        self.db = db

    def find_uncleared_by_pet(self, pet_id: UUID) -> DeferredCarePlanPending | None:
        """Find uncleared deferred plan for a pet."""
        return (
            self.db.query(DeferredCarePlanPending)
            .filter(
                DeferredCarePlanPending.pet_id == pet_id,
                DeferredCarePlanPending.is_cleared == False,
            )
            .first()
        )

    def find_all_uncleared_by_pet(self, pet_id: UUID) -> List[DeferredCarePlanPending]:
        """Find all uncleared deferred plans for a pet."""
        return (
            self.db.query(DeferredCarePlanPending)
            .filter(
                DeferredCarePlanPending.pet_id == pet_id,
                DeferredCarePlanPending.is_cleared == False,
            )
            .order_by(DeferredCarePlanPending.created_at.desc())
            .all()
        )

    def create(
        self,
        user_id: UUID,
        pet_id: UUID,
        reason: str = "pending_extractions",
    ) -> DeferredCarePlanPending:
        """Create a deferred care plan marker."""
        marker = DeferredCarePlanPending(
            user_id=user_id,
            pet_id=pet_id,
            reason=reason,
        )
        self.db.add(marker)
        self.db.flush()
        return marker

    def mark_cleared(self, pet_id: UUID) -> int:
        """Mark all uncleared deferred plans as cleared for a pet."""
        count = (
            self.db.query(DeferredCarePlanPending)
            .filter(
                DeferredCarePlanPending.pet_id == pet_id,
                DeferredCarePlanPending.is_cleared == False,
            )
            .update({DeferredCarePlanPending.is_cleared: True, DeferredCarePlanPending.cleared_at: datetime.utcnow()})
        )
        self.db.flush()
        return count
