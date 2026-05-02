"""
PetCircle Phase 1 — Condition Medication Model

Tracks medications prescribed for a specific condition.
Linked to a condition via condition_id FK.

Constraints:
    - condition_id: FK to conditions(id), ON DELETE CASCADE

Note: Medication "active" status is computed at runtime from end_date vs today,
not stored. The stored columns are: end_date (explicit), started_at, refill_due_date.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ConditionMedication(Base):
    """A medication prescribed for a condition."""

    __tablename__ = "condition_medications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(UUID(as_uuid=True), ForeignKey("conditions.id", ondelete="CASCADE"), index=True, nullable=False)

    name = Column(String(200), nullable=False)
    # "medicine" = pharmaceutical drug; "supplement" = nutritional/supportive.
    # Supplements are routed to diet_items at extraction time; this column
    # stores the GPT classification for the medicines that land here.
    item_type = Column(String(20), nullable=False, default="medicine")
    dose = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    route = Column(String(50), nullable=True)
    started_at = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)  # Treatment end date (extracted from prescription or computed from duration_days)
    refill_due_date = Column(Date, nullable=True)  # When refill is due
    price = Column(String(20), nullable=True)  # e.g. "₹280"
    notes = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    condition = relationship("Condition", back_populates="medications")

    @property
    def status(self) -> str:
        """Compute medication status from date fields.

        'completed'  — end_date is in the past
        'upcoming'   — started_at is in the future
        'active'     — everything else (ongoing or no dates set)
        """
        today = date.today()
        if self.end_date and self.end_date < today:
            return "completed"
        if self.started_at and self.started_at > today:
            return "upcoming"
        return "active"
