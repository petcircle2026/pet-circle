"""
Reminder response handler.

Routes reminder-related button payloads to the reminder engine.
Button payloads: REMINDER_DONE, REMINDER_SNOOZE_7, REMINDER_CANCEL, etc.
"""

import logging
from sqlalchemy.orm import Session

from app.core.constants import REMINDER_PAYLOADS as REMINDER_PAYLOAD_CONST
from app.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class ReminderHandler(BaseHandler):
    """Handle reminder-related button responses."""

    def can_handle(self, message_data: dict) -> bool:
        """Return True if this is a reminder button response."""
        if message_data.get("type") != "button":
            return False

        payload = message_data.get("button_payload", "").strip()
        return payload in REMINDER_PAYLOAD_CONST

    async def handle(
        self,
        db: Session,
        user,
        message_data: dict,
        send_fn,
    ) -> None:
        """
        Handle reminder button response.

        Routes to existing reminder_engine handlers.
        """
        payload = message_data.get("button_payload", "").strip()

        if not payload:
            logger.warning("ReminderHandler received empty payload")
            return

        # Import here to avoid circular deps
        from app.services.reminder_engine import handle_reminder_response

        try:
            await handle_reminder_response(
                db=db,
                user=user,
                payload=payload,
                send_fn=send_fn,
            )
        except Exception as e:
            logger.exception("Reminder handler failed: %s", str(e))
            raise
