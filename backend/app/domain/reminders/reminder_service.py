"""
ReminderService â€” Orchestrator for reminder operations.

Responsible for:
1. Using reminder_logic for stage determination and calculations
2. Delegating to repositories for data access
3. Coordinating reminder queries and updates

This service bridges the domain layer (reminder_logic) with existing reminder handlers.
"""

import logging
from datetime import date
from sqlalchemy.orm import Session

from app.domain.reminders.reminder_logic import determine_reminder_stage

logger = logging.getLogger(__name__)


class ReminderService:
    """
    Orchestrates reminder operations.

    Thin wrapper over existing reminder_engine handlers. Will gradually absorb
    logic as we decompose the monolith.
    """

    def __init__(self, db: Session):
        """
        Initialize service.

        Args:
            db: SQLAlchemy Session instance
        """
        self.db = db

    def get_reminder_stage(self, due_date: date, today: date) -> dict:
        """
        Determine reminder stage for a given due date.

        Uses pure logic from reminder_logic module.

        Args:
            due_date: When the item is due
            today: Today's date

        Returns:
            Dict with stage, days_until_due, and send_now
        """
        stage = determine_reminder_stage(due_date, today)
        return {
            "stage": stage.stage,
            "days_until_due": stage.days_until_due,
            "send_now": stage.send_now,
        }

    async def get_due_reminders(self, pet_id) -> list[dict]:
        """
        Get all due reminders for a pet today.

        Routes to existing reminder_engine handlers.
        """
        from app.services.admin.reminder_engine import get_due_items

        try:
            reminders = await get_due_items(self.db, pet_id)
            return reminders
        except Exception as e:
            logger.exception("Failed to get due reminders: %s", str(e))
            raise

    async def snooze_reminder(self, reminder_id, days: int) -> bool:
        """
        Snooze a reminder.

        Routes to existing reminder_engine handlers.
        """
        from app.services.admin.reminder_engine import snooze_reminder as snooze_handler

        try:
            result = await snooze_handler(self.db, reminder_id, days)
            return result
        except Exception as e:
            logger.exception("Failed to snooze reminder: %s", str(e))
            raise

    async def mark_reminder_done(self, reminder_id) -> bool:
        """
        Mark a reminder as completed.

        Routes to existing reminder_engine handlers.
        """
        from app.services.admin.reminder_engine import mark_done as mark_done_handler

        try:
            result = await mark_done_handler(self.db, reminder_id)
            return result
        except Exception as e:
            logger.exception("Failed to mark reminder done: %s", str(e))
            raise

    async def run_reminder_engine(self) -> dict:
        """
        Run the daily reminder engine.

        Routes to existing reminder_engine handlers.
        Typically triggered by cron at 8 AM IST.
        """
        from app.services.admin.reminder_engine import run_reminder_engine

        try:
            result = await run_reminder_engine(self.db)
            return result
        except Exception as e:
            logger.exception("Reminder engine failed: %s", str(e))
            raise

