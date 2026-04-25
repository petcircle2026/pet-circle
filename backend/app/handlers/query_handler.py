"""
Query/QA handler.

Routes natural language questions to the query engine.
Triggered for general text messages that don't match other handlers.
"""

import logging
from sqlalchemy.orm import Session

from app.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class QueryHandler(BaseHandler):
    """Handle general Q&A queries about pet health."""

    def can_handle(self, message_data: dict) -> bool:
        """
        Return True if this is a text message (fallback handler).

        This should be called LAST, as it's the catch-all for text.
        """
        msg_type = message_data.get("type")
        return msg_type == "text" and bool((message_data.get("text") or "").strip())

    async def handle(
        self,
        db: Session,
        user,
        message_data: dict,
        send_fn,
    ) -> None:
        """
        Handle text query using the query engine.

        Routes to existing query_engine for natural language processing.
        """
        text = (message_data.get("text") or "").strip()

        if not text:
            logger.warning("QueryHandler received empty text")
            return

        # Import here to avoid circular deps
        from app.services.query_engine import handle_query

        try:
            await handle_query(
                db=db,
                user=user,
                text=text,
                send_fn=send_fn,
            )
        except Exception as e:
            logger.exception("Query handler failed: %s", str(e))
            raise
