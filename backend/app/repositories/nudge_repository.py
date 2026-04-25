"""
Nudge Repository — Nudge campaign management.

Manages:
- Nudge CRUD
- Nudge status (dismissed, acted_on)
- Nudge delivery logs
- Nudge engagement metrics
"""

from uuid import UUID
from typing import List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.nudge import Nudge
from app.models.cache.nudge_delivery_log import NudgeDeliveryLog
from app.models.cache.nudge_engagement import NudgeEngagement


class NudgeRepository:
    """Manages nudge campaign data."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Nudge CRUD ----

    def find_by_id(self, nudge_id: UUID) -> Nudge | None:
        """Fetch a nudge by ID."""
        return self.db.query(Nudge).filter(Nudge.id == nudge_id).first()

    def find_by_pet_id(self, pet_id: UUID) -> List[Nudge]:
        """Fetch all nudges for a pet."""
        return (
            self.db.query(Nudge)
            .filter(Nudge.pet_id == pet_id)
            .order_by(desc(Nudge.created_at))
            .all()
        )

    def find_active_for_pet(self, pet_id: UUID) -> List[Nudge]:
        """
        Fetch active (non-dismissed, not acted on) nudges for a pet.

        Returns:
            List of nudges still pending user action.
        """
        return (
            self.db.query(Nudge)
            .filter(
                Nudge.pet_id == pet_id,
                Nudge.dismissed == False,
                Nudge.acted_on == False,
            )
            .order_by(Nudge.created_at)
            .all()
        )

    def find_dismissed(self, pet_id: UUID) -> List[Nudge]:
        """Fetch dismissed nudges for a pet."""
        return (
            self.db.query(Nudge)
            .filter(Nudge.pet_id == pet_id, Nudge.dismissed == True)
            .all()
        )

    def find_acted_on(self, pet_id: UUID) -> List[Nudge]:
        """Fetch nudges user has acted on."""
        return (
            self.db.query(Nudge)
            .filter(Nudge.pet_id == pet_id, Nudge.acted_on == True)
            .all()
        )

    def find_by_category(self, pet_id: UUID, category: str) -> List[Nudge]:
        """Find nudges by category for a pet."""
        return (
            self.db.query(Nudge)
            .filter(Nudge.pet_id == pet_id, Nudge.category == category)
            .all()
        )

    def find_by_user_id(self, user_id: UUID) -> List[Nudge]:
        """Fetch all nudges for a user's pets."""
        return (
            self.db.query(Nudge)
            .join(Nudge.pet)
            .filter(Nudge.pet.user_id == user_id)
            .order_by(desc(Nudge.created_at))
            .all()
        )

    def create(self, nudge: Nudge) -> Nudge:
        """Create a new nudge."""
        self.db.add(nudge)
        self.db.flush()
        return nudge

    def update(self, nudge: Nudge) -> Nudge:
        """Update a nudge."""
        self.db.merge(nudge)
        self.db.flush()
        return nudge

    def mark_dismissed(self, nudge_id: UUID) -> Nudge | None:
        """
        Mark nudge as dismissed.

        Args:
            nudge_id: Nudge ID

        Returns:
            Updated Nudge or None if not found.
        """
        nudge = self.find_by_id(nudge_id)
        if nudge:
            nudge.dismissed = True
            nudge.dismissed_at = datetime.utcnow()
            self.db.merge(nudge)
            self.db.flush()
            return nudge
        return None

    def mark_acted_on(self, nudge_id: UUID) -> Nudge | None:
        """
        Mark nudge as acted on (user took action).

        Args:
            nudge_id: Nudge ID

        Returns:
            Updated Nudge or None if not found.
        """
        nudge = self.find_by_id(nudge_id)
        if nudge:
            nudge.acted_on = True
            nudge.acted_on_at = datetime.utcnow()
            self.db.merge(nudge)
            self.db.flush()
            return nudge
        return None

    def delete(self, nudge_id: UUID) -> bool:
        """
        Delete a nudge.

        Args:
            nudge_id: Nudge ID

        Returns:
            True if found and deleted.
        """
        nudge = self.find_by_id(nudge_id)
        if nudge:
            self.db.delete(nudge)
            self.db.flush()
            return True
        return False

    # ---- Cleanup ----

    def clear_inactive(self, pet_id: UUID, days: int = 90) -> int:
        """
        Delete nudges older than N days that are dismissed or acted on.

        Args:
            pet_id: Pet ID
            days: Age threshold

        Returns:
            Count of deleted nudges.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        count = (
            self.db.query(Nudge)
            .filter(
                Nudge.pet_id == pet_id,
                Nudge.created_at < cutoff,
                (Nudge.dismissed == True) | (Nudge.acted_on == True),
            )
            .delete()
        )
        self.db.flush()
        return count

    def clear_all_for_pet(self, pet_id: UUID) -> int:
        """Delete all nudges for a pet."""
        count = self.db.query(Nudge).filter(Nudge.pet_id == pet_id).delete()
        self.db.flush()
        return count

    # ---- Nudge Delivery Log ----

    def log_delivery(self, log: NudgeDeliveryLog) -> NudgeDeliveryLog:
        """Record nudge delivery attempt."""
        self.db.add(log)
        self.db.flush()
        return log

    def find_delivery_logs(self, nudge_id: UUID) -> List[NudgeDeliveryLog]:
        """Fetch all delivery logs for a nudge."""
        return (
            self.db.query(NudgeDeliveryLog)
            .filter(NudgeDeliveryLog.nudge_id == nudge_id)
            .order_by(desc(NudgeDeliveryLog.created_at))
            .all()
        )

    def find_delivery_logs_by_user(
        self, user_id: UUID, limit: int = 100
    ) -> List[NudgeDeliveryLog]:
        """Fetch delivery logs for a user."""
        return (
            self.db.query(NudgeDeliveryLog)
            .filter(NudgeDeliveryLog.user_id == user_id)
            .order_by(desc(NudgeDeliveryLog.created_at))
            .limit(limit)
            .all()
        )

    def count_deliveries_by_level(self, user_id: UUID, level: int) -> int:
        """Count nudge deliveries for a user at a specific nudge level."""
        return (
            self.db.query(func.count(NudgeDeliveryLog.id))
            .filter(
                NudgeDeliveryLog.user_id == user_id,
                NudgeDeliveryLog.nudge_level == level,
            )
            .scalar() or 0
        )

    def count_deliveries_in_window(self, user_id: UUID, window_days: int = 7) -> int:
        """Count sent nudges in a rolling window of days."""
        from datetime import timezone
        window_start = datetime.now(timezone.utc) - timedelta(days=window_days)
        return (
            self.db.query(func.count(NudgeDeliveryLog.id))
            .filter(
                NudgeDeliveryLog.user_id == user_id,
                NudgeDeliveryLog.wa_status == "sent",
                NudgeDeliveryLog.sent_at >= window_start,
            )
            .scalar() or 0
        )

    def find_last_delivery_log(self, user_id: UUID) -> NudgeDeliveryLog | None:
        """Fetch the most recent delivery log for a user."""
        return (
            self.db.query(NudgeDeliveryLog)
            .filter(NudgeDeliveryLog.user_id == user_id)
            .order_by(desc(NudgeDeliveryLog.sent_at))
            .first()
        )

    def find_last_sent_at(self, user_id: UUID) -> datetime | None:
        """Return the sent_at of the most recent nudge for a user."""
        log = (
            self.db.query(NudgeDeliveryLog)
            .filter(
                NudgeDeliveryLog.user_id == user_id,
                NudgeDeliveryLog.wa_status == "sent",
            )
            .order_by(desc(NudgeDeliveryLog.sent_at))
            .first()
        )
        return log.sent_at if log else None

    def count_deliveries_today(self, user_id: UUID) -> int:
        """Count nudges delivered to a user today."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        return (
            self.db.query(func.count(NudgeDeliveryLog.id))
            .filter(
                NudgeDeliveryLog.user_id == user_id,
                NudgeDeliveryLog.created_at >= today_start,
            )
            .scalar() or 0
        )

    def count_deliveries_in_range(
        self, user_id: UUID, start_date: datetime, end_date: datetime
    ) -> int:
        """Count nudge deliveries within a date range."""
        return (
            self.db.query(func.count(NudgeDeliveryLog.id))
            .filter(
                NudgeDeliveryLog.user_id == user_id,
                NudgeDeliveryLog.created_at >= start_date,
                NudgeDeliveryLog.created_at <= end_date,
            )
            .scalar() or 0
        )

    # ---- Nudge Engagement ----

    def find_engagement(self, pet_id: UUID) -> NudgeEngagement | None:
        """Fetch engagement metrics for a pet."""
        return (
            self.db.query(NudgeEngagement)
            .filter(NudgeEngagement.pet_id == pet_id)
            .first()
        )

    def update_engagement(
        self, engagement: NudgeEngagement
    ) -> NudgeEngagement:
        """Update engagement metrics."""
        self.db.merge(engagement)
        self.db.flush()
        return engagement

    def create_engagement(
        self, engagement: NudgeEngagement
    ) -> NudgeEngagement:
        """Create engagement record."""
        self.db.add(engagement)
        self.db.flush()
        return engagement

    # ---- Aggregations ----

    def count_fresh(self, pet_id: UUID, since: datetime) -> int:
        """Count non-dismissed nudges created after a cutoff timestamp (cache check)."""
        return (
            self.db.query(func.count(Nudge.id))
            .filter(
                Nudge.pet_id == pet_id,
                Nudge.dismissed == False,
                Nudge.created_at >= since,
            )
            .scalar() or 0
        )

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count total nudges for a pet."""
        return (
            self.db.query(func.count(Nudge.id))
            .filter(Nudge.pet_id == pet_id)
            .scalar() or 0
        )

    def count_active_by_pet(self, pet_id: UUID) -> int:
        """Count active nudges for a pet."""
        return (
            self.db.query(func.count(Nudge.id))
            .filter(
                Nudge.pet_id == pet_id,
                Nudge.dismissed == False,
                Nudge.acted_on == False,
            )
            .scalar() or 0
        )

    def get_engagement_rate(self, pet_id: UUID) -> float:
        """Calculate nudge engagement rate (acted_on / total)."""
        total = self.count_by_pet(pet_id)
        if total == 0:
            return 0.0

        acted = (
            self.db.query(func.count(Nudge.id))
            .filter(Nudge.pet_id == pet_id, Nudge.acted_on == True)
            .scalar() or 0
        )

        return (acted / total) * 100

    # ---- Batch Operations ----

    def bulk_create(self, nudges: List[Nudge]) -> List[Nudge]:
        """Create multiple nudges at once."""
        self.db.add_all(nudges)
        self.db.flush()
        return nudges

    def bulk_mark_dismissed(self, nudge_ids: List[UUID]) -> int:
        """Mark multiple nudges as dismissed."""
        count = (
            self.db.query(Nudge)
            .filter(Nudge.id.in_(nudge_ids))
            .update(
                {
                    Nudge.dismissed: True,
                    Nudge.dismissed_at: datetime.utcnow(),
                }
            )
        )
        self.db.flush()
        return count
