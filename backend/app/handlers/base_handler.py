"""
Abstract base handler for WhatsApp message routing.

All message handlers inherit from BaseHandler and implement:
- can_handle(message_data) -> bool â€” return True if this handler should process the message
- handle(db, user, message_data, send_fn) -> None â€” process the message

Pattern: Handlers are tried in priority order. First handler where can_handle() returns True wins.
"""

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session


class BaseHandler(ABC):
    """Abstract base for WhatsApp message handlers."""

    @abstractmethod
    def can_handle(self, message_data: dict) -> bool:
        """
        Return True if this handler should process the message.

        Args:
            message_data: Dict from WhatsApp webhook with keys:
                - type: "text" | "button" | "image" | "document" | "audio"
                - text: message text (if type="text")
                - button_payload: button payload (if type="button")
                - media_type, media_id, file_name (if type="image"/"document")
        """
        pass

    @abstractmethod
    async def handle(
        self,
        db: Session,
        user,
        message_data: dict,
        send_fn,
    ) -> None:
        """
        Process the message.

        Args:
            db: SQLAlchemy session
            user: User model instance
            message_data: Dict with message details (see can_handle docstring)
            send_fn: Async function(db, phone, text) to send WhatsApp messages
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

