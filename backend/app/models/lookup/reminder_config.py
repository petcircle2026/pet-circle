"""
PetCircle — Reminder Config Model

Key-value store for reminder engine configuration.
All snooze intervals, rate-limit thresholds, and send-time settings are
DB-configurable so they can be changed without a code deploy.
Mirrors the NudgeConfig pattern already in use.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ReminderConfig(Base):
    """DB-configurable reminder engine settings (key-value pairs)."""

    __tablename__ = "reminder_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
