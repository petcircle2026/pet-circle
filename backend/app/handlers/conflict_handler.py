"""
Conflict resolution handler.

Routes conflict-related button payloads (e.g., "use new value" vs "keep existing").
Triggered during preventive record conflicts detected by the conflict engine.
"""

import logging
from sqlalchemy.orm import Session

from app.core.constants import (
    CONFLICT_KEEP_EXISTING,
    CONFLICT_USE_NEW,
)
from app.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)

CONFLICT_PAYLOADS = frozenset({
    CONFLICT_KEEP_EXISTING,
    CONFLICT_USE_NEW,
})


class ConflictHandler(BaseHandler):
    """Handle conflict resolution button responses."""

    def can_handle(self, message_data: dict) -> bool:
        """Return True if this is a conflict resolution button response."""
        if message_data.get("type") != "button":
            return False

        payload = message_data.get("button_payload", "").strip()
        return payload in CONFLICT_PAYLOADS

    async def handle(
        self,
        db: Session,
        user,
        message_data: dict,
        send_fn,
    ) -> None:
        """
        Handle conflict resolution response.

        Routes to existing conflict_engine handlers.
        """
        payload = message_data.get("button_payload", "").strip()

        if not payload:
            logger.warning("ConflictHandler received empty payload")
            return

        # Import here to avoid circular deps
        from app.services.conflict_engine import handle_conflict_response

        try:
            await handle_conflict_response(
                db=db,
                user=user,
                payload=payload,
                send_fn=send_fn,
            )
        except Exception as e:
            logger.exception("Conflict handler failed: %s", str(e))
            raise
