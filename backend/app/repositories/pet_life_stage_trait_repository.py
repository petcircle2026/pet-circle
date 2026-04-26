"""
Pet Life Stage Trait Repository — Pet life stage characteristics.

Manages retrieval of life stage trait data for pets.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.pet_profile.pet_life_stage_trait import PetLifeStageTrait


class PetLifeStageTraitRepository:
    """Access to pet life stage traits."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_pet(self, pet_id: UUID) -> List[PetLifeStageTrait]:
        """Find all life stage traits for a pet."""
        return (
            self.db.query(PetLifeStageTrait)
            .filter(PetLifeStageTrait.pet_id == pet_id)
            .order_by(desc(PetLifeStageTrait.generated_at))
            .all()
        )

    def find_latest_by_pet(self, pet_id: UUID) -> PetLifeStageTrait | None:
        """Find the most recent life stage trait for a pet."""
        return (
            self.db.query(PetLifeStageTrait)
            .filter(PetLifeStageTrait.pet_id == pet_id)
            .order_by(desc(PetLifeStageTrait.generated_at))
            .first()
        )

    def create(self, pet_id: UUID, life_stage: str, traits_json: dict) -> PetLifeStageTrait:
        """Create a new life stage trait record."""
        trait = PetLifeStageTrait(
            pet_id=pet_id,
            life_stage=life_stage,
            traits_json=traits_json,
        )
        self.db.add(trait)
        self.db.flush()
        return trait

    def delete_by_pet(self, pet_id: UUID) -> int:
        """Delete all life stage traits for a pet."""
        count = (
            self.db.query(PetLifeStageTrait)
            .filter(PetLifeStageTrait.pet_id == pet_id)
            .delete()
        )
        self.db.flush()
        return count
