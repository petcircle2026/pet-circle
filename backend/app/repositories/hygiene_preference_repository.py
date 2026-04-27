"""
Hygiene Preference Repository — Pet grooming and hygiene preferences.

Manages CRUD operations for hygiene_preferences and tip caching.
"""

from uuid import UUID
from typing import List
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.nutrition.hygiene_preference import HygienePreference
from app.models.cache.hygiene_tip_cache import HygieneTipCache


class HygienePreferenceRepository:
    """Manages hygiene preference data."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Hygiene Preferences CRUD ----

    def find_by_pet(self, pet_id: UUID) -> List[HygienePreference]:
        """Fetch all hygiene preferences for a pet."""
        return (
            self.db.query(HygienePreference)
            .filter(HygienePreference.pet_id == pet_id)
            .order_by(HygienePreference.item_id)
            .all()
        )

    def find_by_pet_and_item(self, pet_id: UUID, item_id: str) -> HygienePreference | None:
        """Fetch a specific hygiene preference by pet and item ID."""
        return (
            self.db.query(HygienePreference)
            .filter(
                HygienePreference.pet_id == pet_id,
                HygienePreference.item_id == item_id,
            )
            .first()
        )

    def create(self, hygiene_pref: HygienePreference) -> HygienePreference:
        """Create a new hygiene preference."""
        self.db.add(hygiene_pref)
        self.db.flush()
        return hygiene_pref

    def update(self, hygiene_pref: HygienePreference) -> HygienePreference:
        """Update an existing hygiene preference."""
        self.db.merge(hygiene_pref)
        self.db.flush()
        return hygiene_pref

    def delete(self, pet_id: UUID, item_id: str) -> bool:
        """Delete a hygiene preference by pet and item ID."""
        count = (
            self.db.query(HygienePreference)
            .filter(
                HygienePreference.pet_id == pet_id,
                HygienePreference.item_id == item_id,
            )
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return count > 0

    def delete_by_pet(self, pet_id: UUID) -> int:
        """Delete all hygiene preferences for a pet."""
        count = (
            self.db.query(HygienePreference)
            .filter(HygienePreference.pet_id == pet_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        return count

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count hygiene preferences for a pet."""
        return (
            self.db.query(HygienePreference)
            .filter(HygienePreference.pet_id == pet_id)
            .count()
        )

    # ---- Hygiene Tip Cache ----

    def find_tip_cache(
        self, species: str, breed_normalized: str, item_ids: List[str], stale_cutoff: datetime
    ) -> dict[str, str]:
        """
        Fetch cached tips for items, returning dict mapping item_id to tip.
        Used by _generate_hygiene_tips for batch cache lookup.
        """
        cached_rows = (
            self.db.query(HygieneTipCache)
            .filter(
                HygieneTipCache.species == species,
                HygieneTipCache.breed_normalized == breed_normalized,
                HygieneTipCache.item_id.in_(item_ids),
                HygieneTipCache.created_at >= stale_cutoff,
            )
            .all()
        )
        return {row.item_id: row.tip for row in cached_rows}

    def delete_stale_tip_cache(self, species: str, breed_normalized: str, item_ids: List[str]) -> None:
        """Delete stale tip cache rows before bulk inserting fresh ones."""
        self.db.query(HygieneTipCache).filter(
            HygieneTipCache.species == species,
            HygieneTipCache.breed_normalized == breed_normalized,
            HygieneTipCache.item_id.in_(item_ids),
        ).delete(synchronize_session=False)
        self.db.flush()

    def bulk_insert_tips(self, tips: List[HygieneTipCache]) -> None:
        """Bulk insert multiple hygiene tip cache rows."""
        self.db.add_all(tips)
        self.db.flush()
