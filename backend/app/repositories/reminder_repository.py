"""
Reminder Repository â€” Reminder management.

Manages:
- Reminder CRUD
- Reminder status tracking
- Reminders by pet, user, and status
"""

from uuid import UUID
from typing import List
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from app.models.preventive.reminder import Reminder


class ReminderRepository:
    """Manages reminder data."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Reminder CRUD ----

    def find_by_id(self, reminder_id: UUID) -> Reminder | None:
        """Fetch a reminder by ID."""
        return self.db.query(Reminder).filter(Reminder.id == reminder_id).first()

    def find_by_pet_id(self, pet_id: UUID) -> List[Reminder]:
        """Fetch all reminders for a pet."""
        return (
            self.db.query(Reminder)
            .filter(Reminder.pet_id == pet_id)
            .order_by(desc(Reminder.due_date))
            .all()
        )

    def find_by_user_id(self, user_id: UUID) -> List[Reminder]:
        """Fetch all reminders for a user's pets."""
        return (
            self.db.query(Reminder)
            .join(Reminder.pet)
            .filter(Reminder.pet.user_id == user_id)
            .order_by(desc(Reminder.due_date))
            .all()
        )

    def find_by_status(self, status: str) -> List[Reminder]:
        """
        Find reminders by status.

        Args:
            status: e.g. "pending", "sent", "dismissed", "acknowledged"

        Returns:
            List of matching reminders.
        """
        return (
            self.db.query(Reminder)
            .filter(Reminder.status == status)
            .order_by(desc(Reminder.due_date))
            .all()
        )

    def find_pending(self) -> List[Reminder]:
        """Fetch all pending reminders across all users."""
        return (
            self.db.query(Reminder)
            .filter(Reminder.status == "pending")
            .order_by(Reminder.due_date)
            .all()
        )

    def find_pending_for_pet(self, pet_id: UUID) -> List[Reminder]:
        """Fetch pending reminders for a specific pet."""
        return (
            self.db.query(Reminder)
            .filter(Reminder.pet_id == pet_id, Reminder.status == "pending")
            .order_by(Reminder.due_date)
            .all()
        )

    def find_overdue(self) -> List[Reminder]:
        """Fetch all overdue reminders (due_date < now, status = pending)."""
        now = datetime.utcnow()
        return (
            self.db.query(Reminder)
            .filter(
                Reminder.due_date < now,
                Reminder.status == "pending",
            )
            .order_by(Reminder.due_date)
            .all()
        )

    def find_due_today(self) -> List[Reminder]:
        """Fetch reminders due today."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        return (
            self.db.query(Reminder)
            .filter(
                Reminder.due_date >= today_start,
                Reminder.due_date < today_end,
                Reminder.status == "pending",
            )
            .order_by(Reminder.due_date)
            .all()
        )

    def find_by_preventive_record_id(
        self, record_id: UUID
    ) -> Reminder | None:
        """Find reminder associated with a preventive record."""
        return (
            self.db.query(Reminder)
            .filter(Reminder.preventive_record_id == record_id)
            .first()
        )

    def create(self, reminder: Reminder) -> Reminder:
        """Create a new reminder."""
        self.db.add(reminder)
        self.db.flush()
        return reminder

    def update(self, reminder: Reminder) -> Reminder:
        """Update a reminder."""
        self.db.merge(reminder)
        self.db.flush()
        return reminder

    def update_status(self, reminder_id: UUID, status: str) -> Reminder | None:
        """
        Update reminder status.

        Args:
            reminder_id: Reminder ID
            status: New status

        Returns:
            Updated Reminder or None if not found.
        """
        reminder = self.find_by_id(reminder_id)
        if reminder:
            reminder.status = status
            if status == "sent":
                reminder.sent_at = datetime.utcnow()
            self.db.merge(reminder)
            self.db.flush()
            return reminder
        return None

    def mark_sent(self, reminder_id: UUID) -> Reminder | None:
        """Mark a reminder as sent."""
        return self.update_status(reminder_id, "sent")

    def mark_acknowledged(self, reminder_id: UUID) -> Reminder | None:
        """Mark a reminder as acknowledged."""
        return self.update_status(reminder_id, "acknowledged")

    def delete(self, reminder_id: UUID) -> bool:
        """
        Delete a reminder.

        Args:
            reminder_id: Reminder ID

        Returns:
            True if found and deleted.
        """
        reminder = self.find_by_id(reminder_id)
        if reminder:
            self.db.delete(reminder)
            self.db.flush()
            return True
        return False

    # ---- Cleanup Operations ----

    def delete_expired(self, days_old: int = 30) -> int:
        """
        Delete acknowledged reminders older than N days.

        Args:
            days_old: Age threshold in days

        Returns:
            Count of deleted reminders.
        """
        cutoff = datetime.utcnow() - timedelta(days=days_old)

        count = (
            self.db.query(Reminder)
            .filter(
                Reminder.status == "acknowledged",
                Reminder.updated_at < cutoff,
            )
            .delete()
        )
        self.db.flush()
        return count

    def delete_for_pet(self, pet_id: UUID) -> int:
        """
        Delete all reminders for a pet.

        Args:
            pet_id: Pet ID

        Returns:
            Count of deleted reminders.
        """
        count = (
            self.db.query(Reminder).filter(Reminder.pet_id == pet_id).delete()
        )
        self.db.flush()
        return count

    # ---- Aggregations ----

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count total reminders for a pet."""
        return (
            self.db.query(func.count(Reminder.id))
            .filter(Reminder.pet_id == pet_id)
            .scalar() or 0
        )

    def count_pending(self) -> int:
        """Count all pending reminders."""
        return (
            self.db.query(func.count(Reminder.id))
            .filter(Reminder.status == "pending")
            .scalar() or 0
        )

    def count_pending_by_user(self, user_id: UUID) -> int:
        """Count pending reminders for a user's pets."""
        return (
            self.db.query(func.count(Reminder.id))
            .join(Reminder.pet)
            .filter(
                Reminder.pet.user_id == user_id,
                Reminder.status == "pending",
            )
            .scalar() or 0
        )

    # ---- Batch Operations ----

    def has_sent_today_for_user(self, user_id: UUID, today: date) -> bool:
        """Return True if any reminder was sent today for any pet belonging to user."""
        from app.models.core.pet import Pet
        start = datetime.combine(today, datetime.min.time())
        end = start + timedelta(days=1)
        result = (
            self.db.query(Reminder.id)
            .join(Pet, Reminder.pet_id == Pet.id)
            .filter(
                Pet.user_id == user_id,
                Pet.is_deleted == False,
                Reminder.status == "sent",
                Reminder.sent_at >= start,
                Reminder.sent_at < end,
            )
            .first()
        )
        return result is not None

    def has_pending_today_for_user(self, user_id: UUID, today: date) -> bool:
        """Return True if any reminder is pending (due today) for any of the user's pets."""
        from app.models.core.pet import Pet
        result = (
            self.db.query(Reminder.id)
            .join(Pet, Reminder.pet_id == Pet.id)
            .filter(
                Pet.user_id == user_id,
                Pet.is_deleted == False,
                Reminder.status == "pending",
                Reminder.next_due_date == today,
            )
            .first()
        )
        return result is not None

    def bulk_create(self, reminders: List[Reminder]) -> List[Reminder]:
        """Create multiple reminders at once."""
        self.db.add_all(reminders)
        self.db.flush()
        return reminders

    def bulk_mark_sent(self, reminder_ids: List[UUID]) -> int:
        """Mark multiple reminders as sent."""
        count = (
            self.db.query(Reminder)
            .filter(Reminder.id.in_(reminder_ids))
            .update(
                {
                    Reminder.status: "sent",
                    Reminder.sent_at: datetime.utcnow(),
                }
            )
        )
        self.db.flush()
        return count

    # ---- Reminder Engine helpers ----

    def find_sent_unacknowledged_older_than(self, cutoff: datetime):
        """
        Fetch (Reminder, Pet, User) tuples for sent reminders with no reply.
        Used by ignore detection in reminder_engine.
        """
        from app.models.core.pet import Pet
        from app.models.core.user import User
        return (
            self.db.query(Reminder, Pet, User)
            .join(Pet, Reminder.pet_id == Pet.id)
            .join(User, Pet.user_id == User.id)
            .filter(
                Reminder.status == "sent",
                Reminder.sent_at <= cutoff,
                Pet.is_deleted == False,
                User.is_deleted == False,
            )
            .all()
        )

    def find_by_source_and_due(self, source_id: UUID, due_date: date) -> List[Reminder]:
        """Fetch all reminder rows for a given source_id + next_due_date combination."""
        return (
            self.db.query(Reminder)
            .filter(
                Reminder.source_id == source_id,
                Reminder.next_due_date == due_date,
            )
            .all()
        )

    def find_sent_today_summary(self, day_start: datetime):
        """
        Return (source_id, stage, pet_id) tuples for all reminders sent since day_start.
        Used by _apply_send_rules to build dedup sets.
        """
        return (
            self.db.query(Reminder.source_id, Reminder.stage, Reminder.pet_id)
            .filter(
                Reminder.status == "sent",
                Reminder.sent_at >= day_start,
            )
            .all()
        )

    def find_recently_sent_for_sources(self, source_ids, cutoff: datetime):
        """
        Return (source_id, sent_at) for sources sent after cutoff.
        Used by min-gap enforcement in _apply_send_rules.
        """
        return (
            self.db.query(Reminder.source_id, Reminder.sent_at)
            .filter(
                Reminder.status == "sent",
                Reminder.sent_at.isnot(None),
                Reminder.source_id.in_(source_ids),
                Reminder.sent_at >= cutoff,
            )
            .all()
        )

    def find_hygiene_dedup(self, pet_id: UUID, due_date: date, stage: str) -> Reminder | None:
        """Check if a hygiene due reminder was already sent for this pet/date/stage."""
        return (
            self.db.query(Reminder)
            .filter(
                Reminder.pet_id == pet_id,
                Reminder.source_type == "hygiene_preference",
                Reminder.next_due_date == due_date,
                Reminder.stage == stage,
            )
            .first()
        )

    def find_unresponded_by_pet_and_type(
        self, pet_id: UUID, reminder_type: str
    ) -> list:
        """Find unresponded reminders of a specific type for a pet."""
        return (
            self.db.query(Reminder)
            .filter(
                Reminder.pet_id == pet_id,
                Reminder.reminder_type == reminder_type,
                Reminder.responded == False,
            )
            .all()
        )

