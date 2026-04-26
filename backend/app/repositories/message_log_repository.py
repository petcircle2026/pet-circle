from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import String, cast
from app.models.messaging.message_log import MessageLog


class MessageLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_sent_setup_prompt(self, mobile_number: str) -> MessageLog | None:
        """Find if setup prompt was already sent to this number."""
        return (
            self.db.query(MessageLog.id)
            .filter(
                MessageLog.mobile_number == mobile_number,
                MessageLog.direction == "outgoing",
                MessageLog.message_type == "text",
                cast(MessageLog.payload["text"]["body"], String).like(
                    "%Please send a text%"
                ),
            )
            .first()
        )
