"""
PetCircle — Vet Summary Service

Reads directly from the contacts table (no joins required).
last_visit_date is stored on the contact row itself, populated at extraction
time from the source document's event_date.

Primary vet = the veterinarian contact for the pet with the most recent
last_visit_date. Falls back to created_at for contacts without a visit date.
"""

import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contact import Contact

logger = logging.getLogger(__name__)

ROLE_VETERINARIAN = "veterinarian"


@dataclass
class VetSummary:
    name: str
    last_visit: date | None


def get_vet_summary(db: Session, pet_id: UUID) -> VetSummary | None:
    row = (
        db.query(Contact)
        .filter(
            Contact.pet_id == pet_id,
            Contact.role == ROLE_VETERINARIAN,
        )
        .order_by(
            Contact.last_visit_date.desc().nullslast(),
            Contact.created_at.desc(),
        )
        .first()
    )

    if row is None:
        return None

    return VetSummary(name=row.name, last_visit=row.last_visit_date)
