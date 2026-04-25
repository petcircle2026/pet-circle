"""
Order/cart message handler.

Routes order-related text and button payloads to the order service.
Text triggers: "order", "buy", "cart", "shop", etc.
Button payloads: ORDER_CONFIRM_*, ORDER_FULFILL_*, ORDER_CATEGORY_*, etc.
"""

import logging
from sqlalchemy.orm import Session

from app.core.constants import (
    ORDER_COMMANDS,
    ORDER_CONFIRM_PAYLOADS,
    ORDER_FULFILL_YES_PREFIX,
    ORDER_FULFILL_NO_PREFIX,
    ORDER_CATEGORY_PAYLOADS,
)
from app.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class OrderHandler(BaseHandler):
    """Handle order/cart-related messages."""

    def can_handle(self, message_data: dict) -> bool:
        """Return True if this is an order-related message."""
        msg_type = message_data.get("type")

        # Check text commands
        if msg_type == "text":
            text = (message_data.get("text") or "").strip().lower()
            return any(cmd in text for cmd in ORDER_COMMANDS)

        # Check button payloads
        if msg_type == "button":
            payload = message_data.get("button_payload", "").strip()
            return (
                payload in ORDER_CONFIRM_PAYLOADS
                or payload in ORDER_CATEGORY_PAYLOADS
                or payload.startswith(ORDER_FULFILL_YES_PREFIX)
                or payload.startswith(ORDER_FULFILL_NO_PREFIX)
            )

        return False

    async def handle(
        self,
        db: Session,
        user,
        message_data: dict,
        send_fn,
    ) -> None:
        """
        Handle order/cart message.

        Routes to existing order service handlers.
        """
        msg_type = message_data.get("type")
        text = (message_data.get("text") or "").strip()
        payload = message_data.get("button_payload", "").strip()

        # Import here to avoid circular deps
        from app.services.whatsapp.agentic_order import handle_order_intent

        try:
            await handle_order_intent(
                db=db,
                user=user,
                text=text or payload,
                message_data=message_data,
                send_fn=send_fn,
            )
        except Exception as e:
            logger.exception("Order handler failed: %s", str(e))
            raise
