"""
Pet Preference Repository â€” Pet preference and recommendation tracking.

Manages:
- Pet preferences (user-curated item history)
- Recommendation tracking
"""

from uuid import UUID
from typing import List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.pet_profile.pet_preference import PetPreference


class PetPreferenceRepository:
    """Manages pet preference data."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Pet Preference CRUD ----

    def find_by_id(self, preference_id: UUID) -> PetPreference | None:
        """Fetch a pet preference by ID."""
        return (
            self.db.query(PetPreference)
            .filter(PetPreference.id == preference_id)
            .first()
        )

    def find_by_pet_and_category(
        self, pet_id: UUID, category: str
    ) -> List[PetPreference]:
        """Fetch all preferences for a pet in a specific category."""
        return (
            self.db.query(PetPreference)
            .filter(
                PetPreference.pet_id == pet_id,
                PetPreference.category == category,
            )
            .order_by(desc(PetPreference.updated_at))
            .all()
        )

    def find_by_pet_category_item(
        self, pet_id: UUID, category: str, item_name: str
    ) -> PetPreference | None:
        """Find a preference by pet, category, and item name (case-insensitive)."""
        return (
            self.db.query(PetPreference)
            .filter(
                PetPreference.pet_id == pet_id,
                PetPreference.category == category,
                PetPreference.item_name.ilike(item_name),
            )
            .first()
        )

    def find_by_pet_and_category_ordered(
        self, pet_id: UUID, category: str
    ) -> List[PetPreference]:
        """Fetch preferences for a pet in a category, ordered by updated_at descending."""
        return (
            self.db.query(PetPreference)
            .filter(
                PetPreference.pet_id == pet_id,
                PetPreference.category == category,
            )
            .order_by(desc(PetPreference.updated_at))
            .all()
        )

    def create(self, preference: PetPreference) -> PetPreference:
        """Create a new pet preference."""
        self.db.add(preference)
        self.db.flush()
        return preference

    def update(self, preference: PetPreference) -> PetPreference:
        """Update a pet preference."""
        self.db.merge(preference)
        self.db.flush()
        return preference

    def delete(self, preference_id: UUID) -> bool:
        """Delete a pet preference."""
        preference = self.find_by_id(preference_id)
        if preference:
            self.db.delete(preference)
            self.db.flush()
            return True
        return False

    def delete_for_pet_and_category(self, pet_id: UUID, category: str) -> int:
        """Delete all preferences for a pet in a specific category."""
        count = (
            self.db.query(PetPreference)
            .filter(
                PetPreference.pet_id == pet_id,
                PetPreference.category == category,
            )
            .delete()
        )
        self.db.flush()
        return count

    def has_preference(self, pet_id: UUID, category: str, item_name: str) -> bool:
        """Check if a preference exists for a pet."""
        return (
            self.db.query(PetPreference.id)
            .filter(
                PetPreference.pet_id == pet_id,
                PetPreference.category == category,
                PetPreference.item_name.ilike(item_name),
            )
            .first() is not None
        )

    def find_recent_by_pet(self, pet_id: UUID, limit: int = 10) -> List[PetPreference]:
        """Find recent preferences for a pet, ordered by update date."""
        return (
            self.db.query(PetPreference)
            .filter(PetPreference.pet_id == pet_id)
            .order_by(desc(PetPreference.updated_at))
            .limit(limit)
            .all()
        )

