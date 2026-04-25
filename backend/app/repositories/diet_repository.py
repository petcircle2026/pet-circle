"""
Diet Repository — Pet nutrition and diet management.

Manages:
- Diet items (current foods)
- Nutrition caches
- Nutrition targets
"""

from uuid import UUID
from typing import List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.diet_item import DietItem
from app.models.cache.food_nutrition_cache import FoodNutritionCache
from app.models.cache.nutrition_target_cache import NutritionTargetCache


class DietRepository:
    """Manages pet diet and nutrition data."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Diet Items ----

    def find_by_id(self, item_id: UUID) -> DietItem | None:
        """Fetch a diet item by ID."""
        return self.db.query(DietItem).filter(DietItem.id == item_id).first()

    def find_by_pet_id(self, pet_id: UUID) -> List[DietItem]:
        """Fetch all diet items (foods) for a pet."""
        return (
            self.db.query(DietItem)
            .filter(DietItem.pet_id == pet_id, DietItem.is_active == True)
            .all()
        )

    def find_all_by_pet_id(self, pet_id: UUID) -> List[DietItem]:
        """Fetch all diet items including inactive ones."""
        return self.db.query(DietItem).filter(DietItem.pet_id == pet_id).all()

    def find_by_pet_and_food(
        self, pet_id: UUID, food_id: UUID
    ) -> DietItem | None:
        """Find a specific food item in a pet's diet."""
        return (
            self.db.query(DietItem)
            .filter(
                DietItem.pet_id == pet_id,
                DietItem.food_id == food_id,
            )
            .first()
        )

    def create(self, diet_item: DietItem) -> DietItem:
        """Add a food to a pet's diet."""
        self.db.add(diet_item)
        self.db.flush()
        return diet_item

    def update(self, diet_item: DietItem) -> DietItem:
        """Update a diet item."""
        self.db.merge(diet_item)
        self.db.flush()
        return diet_item

    def delete(self, item_id: UUID) -> bool:
        """
        Remove a diet item (hard delete).

        Args:
            item_id: DietItem ID

        Returns:
            True if found and deleted.
        """
        item = self.find_by_id(item_id)
        if item:
            self.db.delete(item)
            self.db.flush()
            return True
        return False

    def deactivate(self, item_id: UUID) -> DietItem | None:
        """
        Soft-delete a diet item (mark inactive).

        Args:
            item_id: DietItem ID

        Returns:
            Updated DietItem or None if not found.
        """
        item = self.find_by_id(item_id)
        if item:
            item.is_active = False
            self.db.merge(item)
            self.db.flush()
            return item
        return None

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count active diet items for a pet."""
        return (
            self.db.query(func.count(DietItem.id))
            .filter(DietItem.pet_id == pet_id, DietItem.is_active == True)
            .scalar() or 0
        )

    # ---- Nutrition Cache ----

    def find_food_nutrition_cache(
        self, food_id: UUID
    ) -> FoodNutritionCache | None:
        """Fetch cached nutrition data for a food."""
        return (
            self.db.query(FoodNutritionCache)
            .filter(FoodNutritionCache.food_id == food_id)
            .first()
        )

    def create_food_nutrition_cache(
        self, cache: FoodNutritionCache
    ) -> FoodNutritionCache:
        """Create nutrition cache for a food."""
        self.db.add(cache)
        self.db.flush()
        return cache

    def update_food_nutrition_cache(
        self, cache: FoodNutritionCache
    ) -> FoodNutritionCache:
        """Update nutrition cache."""
        self.db.merge(cache)
        self.db.flush()
        return cache

    def find_by_pet_ordered(self, pet_id: UUID) -> List[DietItem]:
        """Fetch all diet items for a pet ordered by created_at."""
        from sqlalchemy import asc
        return (
            self.db.query(DietItem)
            .filter(DietItem.pet_id == pet_id)
            .order_by(asc(DietItem.created_at))
            .all()
        )

    def find_by_pet_label_type(self, pet_id: UUID, label: str, item_type: str) -> DietItem | None:
        """Find a diet item by pet, label, and type (for duplicate check)."""
        return (
            self.db.query(DietItem)
            .filter(
                DietItem.pet_id == pet_id,
                DietItem.label == label,
                DietItem.type == item_type,
            )
            .first()
        )

    def find_by_id_and_pet(self, item_id: UUID, pet_id: UUID) -> DietItem | None:
        """Find a diet item by ID scoped to a pet."""
        return (
            self.db.query(DietItem)
            .filter(DietItem.id == item_id, DietItem.pet_id == pet_id)
            .first()
        )

    def find_stale_food_caches(self, days: int = 30) -> List[FoodNutritionCache]:
        """Find nutrition caches older than N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(FoodNutritionCache)
            .filter(FoodNutritionCache.updated_at < cutoff)
            .all()
        )

    # ---- Nutrition Target Cache ----

    def find_nutrition_target_cache(
        self, pet_id: UUID
    ) -> NutritionTargetCache | None:
        """Fetch cached nutrition targets for a pet."""
        return (
            self.db.query(NutritionTargetCache)
            .filter(NutritionTargetCache.pet_id == pet_id)
            .first()
        )

    def create_nutrition_target_cache(
        self, cache: NutritionTargetCache
    ) -> NutritionTargetCache:
        """Create nutrition target cache for a pet."""
        self.db.add(cache)
        self.db.flush()
        return cache

    def update_nutrition_target_cache(
        self, cache: NutritionTargetCache
    ) -> NutritionTargetCache:
        """Update nutrition target cache."""
        self.db.merge(cache)
        self.db.flush()
        return cache

    def find_stale_target_caches(self, days: int = 30) -> List[NutritionTargetCache]:
        """Find target caches older than N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(NutritionTargetCache)
            .filter(NutritionTargetCache.updated_at < cutoff)
            .all()
        )

    # ---- Aggregations ----

    def has_diet(self, pet_id: UUID) -> bool:
        """Check if a pet has at least one food in diet."""
        return self.count_by_pet(pet_id) > 0

    def has_food(self, pet_id: UUID) -> bool:
        """Return True if the pet has at least one non-supplement food."""
        return (
            self.db.query(DietItem.id)
            .filter(DietItem.pet_id == pet_id, DietItem.type != "supplement")
            .first() is not None
        )

    def has_supplement(self, pet_id: UUID) -> bool:
        """Return True if the pet has at least one supplement."""
        return (
            self.db.query(DietItem.id)
            .filter(DietItem.pet_id == pet_id, DietItem.type == "supplement")
            .first() is not None
        )

    def find_packaged_and_supplements_with_pets(self):
        """
        Fetch (DietItem, Pet, User) tuples for packaged food and supplement items.
        Used by reminder_engine to collect food/supplement order candidates.
        """
        from app.models.pet import Pet
        from app.models.user import User
        return (
            self.db.query(DietItem, Pet, User)
            .join(Pet, DietItem.pet_id == Pet.id)
            .join(User, Pet.user_id == User.id)
            .filter(
                DietItem.type.in_(["packaged", "supplement"]),
                Pet.is_deleted == False,
                User.is_deleted == False,
            )
            .all()
        )

    def clear_diet(self, pet_id: UUID) -> int:
        """Remove all foods from a pet's diet."""
        count = (
            self.db.query(DietItem)
            .filter(DietItem.pet_id == pet_id)
            .delete()
        )
        self.db.flush()
        return count

    # ---- Batch Operations ----

    def bulk_add(self, items: List[DietItem]) -> List[DietItem]:
        """Add multiple diet items at once."""
        self.db.add_all(items)
        self.db.flush()
        return items

    def bulk_deactivate(self, item_ids: List[UUID]) -> int:
        """Deactivate multiple diet items."""
        count = (
            self.db.query(DietItem)
            .filter(DietItem.id.in_(item_ids))
            .update({"is_active": False})
        )
        self.db.flush()
        return count
