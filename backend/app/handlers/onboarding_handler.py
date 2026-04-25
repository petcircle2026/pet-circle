"""
Onboarding message handler.

Routes onboarding messages to the OnboardingService.
Used when user.onboarding_state != "complete".
"""

import logging
from sqlalchemy.orm import Session

from app.domain.onboarding import OnboardingService
from app.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class OnboardingHandler(BaseHandler):
    """Handle messages during onboarding flow."""

    def can_handle(self, message_data: dict) -> bool:
        """
        Return True if user is in onboarding (checked by caller, not here).

        This handler is only called when user.onboarding_state != "complete".
        We accept text or button payloads.
        """
        msg_type = message_data.get("type")
        if msg_type == "text":
            return bool(message_data.get("text", "").strip())
        elif msg_type == "button":
            return bool(message_data.get("button_payload", "").strip())
        return False

    async def handle(
        self,
        db: Session,
        user,
        message_data: dict,
        send_fn,
    ) -> None:
        """Route to OnboardingService."""
        text = (
            message_data.get("text")
            or message_data.get("button_payload")
            or ""
        ).strip()

        if not text:
            logger.warning("OnboardingHandler received empty text")
            return

        service = OnboardingService(db)
        await service.handle_message(user, text, send_fn, message_data=message_data)

