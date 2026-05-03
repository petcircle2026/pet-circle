"""
PetCircle — Condition Model (document-level)

One row per named condition per uploaded document. The upsert-by-(pet_id, name)
approach was removed; duplicates across documents are intentional and are
consolidated by the aggregation layer (aggregated_conditions table).

Constraints:
    - pet_id: FK to pets(id), ON DELETE CASCADE
    - document_id: FK to documents(id), ON DELETE SET NULL (source document)
    - condition_type: CHECK IN ('chronic', 'episodic', 'recurrent', 'resolved')
    - source: CHECK IN ('extraction', 'inferred', 'manual')
    - is_active: soft delete flag
    - condition_family_id: FK to aggregated_conditions(id), written by aggregation service
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Condition(Base):
    """
    A diagnosed medical condition extracted from one document for a pet.

    condition_type:
        - chronic: ongoing condition requiring long-term management
        - episodic: single episode, no prior similar history
        - recurrent: repeated episodes meeting the recurrence threshold
        - resolved: legacy value from old extraction prompts

    source:
        - extraction: automatically extracted from an uploaded document
        - inferred: deduced by GPT from medications (no explicit diagnosis written)
        - manual: manually added by the user via dashboard
    """

    __tablename__ = "conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), index=True, nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), index=True, nullable=True)

    name = Column(String(200), nullable=False)
    diagnosis = Column(String(500), nullable=True)
    condition_type = Column(String(20), nullable=False, default="episodic")  # chronic | episodic | recurrent | resolved
    condition_status = Column(String(20), nullable=True)  # active | monitoring | resolved (computed at runtime)
    episode_dates = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list)  # sorted list of YYYY-MM-DD strings
    diagnosed_at = Column(Date, nullable=True)
    medication_end_date = Column(Date, nullable=True)  # MAX(medications.end_date) for this condition (denormalized for query perf)
    notes = Column(String(1000), nullable=True)
    icon = Column(String(10), nullable=True)  # Emoji icon for condition display
    managed_by = Column(String(200), nullable=True)  # Managing doctor/vet name and location
    treatment_route = Column(String(100), nullable=True)  # topical | oral | systemic | etc.
    vet_resolved = Column(Boolean, nullable=False, default=False)  # vet-confirmed resolution override
    source = Column(String(20), nullable=False, default="extraction")  # extraction | inferred | manual
    is_active = Column(Boolean, default=True)

    # Set by aggregation service after grouping into complaint families
    condition_family_id = Column(UUID(as_uuid=True), ForeignKey("aggregated_conditions.id", ondelete="SET NULL"), nullable=True)
    recurrence_watch = Column(Boolean, default=False)  # True if 1 episode but threshold not yet met

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    pet = relationship("Pet", back_populates="conditions")
    document = relationship("Document")
    medications = relationship("ConditionMedication", back_populates="condition", cascade="all, delete-orphan")
    monitoring = relationship("ConditionMonitoring", back_populates="condition", cascade="all, delete-orphan")
    aggregated_condition = relationship("AggregatedCondition", back_populates="conditions", foreign_keys=[condition_family_id])
