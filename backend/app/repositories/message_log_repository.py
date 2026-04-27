from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import String, cast, desc
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

    def find_recent_outgoing_by_type(
        self, message_type: str, lookback_seconds: int
    ) -> list[MessageLog]:
        """
        Find recent outgoing messages of a specific type within the lookback window.
        Used by whatsapp_sender to check for duplicate sends.
        """
        cutoff = datetime.now() - timedelta(seconds=lookback_seconds)
        return (
            self.db.query(MessageLog)
            .filter(
                MessageLog.direction == "outgoing",
                MessageLog.message_type == message_type,
                MessageLog.created_at >= cutoff,
            )
            .order_by(desc(MessageLog.created_at))
            .all()
        )
