"""
PetCircle — AggregatedCondition Model

One row per complaint family per pet. Written by condition_aggregation_service
after each document extraction. Document-level Condition rows link back here
via condition_family_id.

Fields are merged from all document-level Condition rows in the same family
according to the merge rules in condition_aggregation_service.py.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AggregatedCondition(Base):
    """
    A merged, pet-level view of one condition complaint family.

    condition_type: highest rank wins across all docs in family (chronic > recurrent > episodic)
    condition_status: computed from merged episode_dates + medication_end_date
    episode_dates: union of all document-level arrays, deduplicated, sorted ascending
    medications: union by name (case-insensitive), MAX end_date per drug
    monitoring: union by name, MAX recheck_due_date per item
    """

    __tablename__ = "aggregated_conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), index=True, nullable=False)

    name = Column(String(200), nullable=False)
    condition_type = Column(String(20), nullable=False, default="episodic")  # chronic | episodic | recurrent
    condition_status = Column(String(20), nullable=True)  # active | monitoring | resolved

    episode_dates = Column(JSONB, nullable=False, default=list)  # sorted YYYY-MM-DD strings
    diagnosed_at = Column(Date, nullable=True)          # MIN diagnosed_at across family
    last_record_date = Column(Date, nullable=True)      # MAX of merged episode_dates
    medication_end_date = Column(Date, nullable=True)   # MAX end_date across all medications in family

    medications = Column(JSONB, nullable=False, default=list)  # [{name, end_date, dose, frequency}]
    monitoring = Column(JSONB, nullable=False, default=list)   # [{name, recheck_due_date}]

    soft_resolution = Column(Boolean, nullable=False, default=False)
    recurrence_watch = Column(Boolean, nullable=False, default=False)

    # Points to the document-level Condition row with the earliest diagnosed_at in this family
    canonical_condition_id = Column(UUID(as_uuid=True), ForeignKey("conditions.id", ondelete="SET NULL"), nullable=True)
    # Points to the most-recently-diagnosed Condition row in this family (used in precompute JOIN)
    latest_episode_condition_id = Column(UUID(as_uuid=True), ForeignKey("conditions.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    pet = relationship("Pet")
    canonical_condition = relationship("Condition", foreign_keys=[canonical_condition_id])
    latest_episode_condition = relationship("Condition", foreign_keys=[latest_episode_condition_id])
    conditions = relationship(
        "Condition",
        back_populates="aggregated_condition",
        foreign_keys="Condition.condition_family_id",
    )
