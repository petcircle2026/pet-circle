"""
Document upload handler.

Routes image and document uploads to the document extraction pipeline.
Used for health record uploads during onboarding or general queries.
"""

import logging
from sqlalchemy.orm import Session

from app.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class DocumentHandler(BaseHandler):
    """Handle image and document uploads."""

    def can_handle(self, message_data: dict) -> bool:
        """Return True if this is an image or document upload."""
        msg_type = message_data.get("type")
        return msg_type in ("image", "document")

    async def handle(
        self,
        db: Session,
        user,
        message_data: dict,
        send_fn,
    ) -> None:
        """
        Handle document/image upload.

        Routes to existing document_upload handlers.
        """
        msg_type = message_data.get("type")

        if msg_type not in ("image", "document"):
            logger.warning("DocumentHandler received unexpected type: %s", msg_type)
            return

        # Import here to avoid circular deps
        from app.services.shared.document_upload import handle_document_upload

        try:
            await handle_document_upload(
                db=db,
                user=user,
                message_data=message_data,
                send_fn=send_fn,
            )
        except Exception as e:
            logger.exception("Document handler failed: %s", str(e))
            raise
