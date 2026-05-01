"""
PetCircle — Recommendation Service (Preference Tracking)

Records purchase history for pets to track what items have been ordered.
Used by cart_service to exclude previously bought items from recommendations.

All deterministic recommendations now use signal_resolver (see dashboard/signal_resolver.py).
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.pet_profile.pet_preference import PetPreference
from app.repositories.pet_preference_repository import PetPreferenceRepository

logger = logging.getLogger(__name__)


def record_preference(
    db: Session,
    pet_id,
    category,
    item_name,
    preference_type: str = "custom",
) -> None:
    """
    Record that a user ordered an item (preference).

    If this item was previously ordered, increment used_count.
    Otherwise, create a new preference record.

    Args:
        db: Database session
        pet_id: Pet UUID
        category: Order category
        item_name: Item name
        preference_type: "recommendation" or "custom"
    """
    try:
        normalized_name = item_name.strip()
        if not normalized_name:
            return

        existing = PetPreferenceRepository(db).find_by_pet_category_item(
            pet_id, category, normalized_name
        )

        if existing:
            existing.used_count = (getattr(existing, "used_count", 0) or 0) + 1
            existing.updated_at = datetime.now(timezone.utc)
        else:
            preference = PetPreference(
                pet_id=pet_id,
                category=category,
                item_name=normalized_name,
                preference_type=preference_type,
                used_count=1,
            )
            db.add(preference)

        db.commit()
        logger.debug(f"Recorded preference for pet {pet_id}: {item_name}")

    except Exception as e:
        logger.error(f"Failed to record preference: {e}", exc_info=True)
        db.rollback()
