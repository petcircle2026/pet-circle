"""
Nutrition Cache Repository — Nutrition profile and food caching.

Manages caching for nutrition targets (computed per breed/age) and
food recommendation scoring.
"""

from uuid import UUID
from typing import List
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.cache.nutrition_target_cache import NutritionTargetCache
from app.models.cache.food_nutrition_cache import FoodNutritionCache


class NutritionCacheRepository:
    """Manages nutrition-related caches."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Nutrition Target Cache ----

    def find_nutrition_target_cache(
        self, species: str, breed_normalized: str, age_context_key: str
    ) -> NutritionTargetCache | None:
        """Find cached nutrition target for a breed/age combo."""
        return (
            self.db.query(NutritionTargetCache)
            .filter(
                NutritionTargetCache.species == species,
                NutritionTargetCache.breed_normalized == breed_normalized,
                NutritionTargetCache.age_category == age_context_key,
            )
            .first()
        )

    def create_nutrition_target_cache(
        self, cache: NutritionTargetCache
    ) -> NutritionTargetCache:
        """Create a new nutrition target cache record."""
        self.db.add(cache)
        self.db.flush()
        return cache

    # ---- Food Nutrition Cache ----

    def find_food_nutrition_cache(
        self, species: str, breed_normalized: str, age_context_key: str
    ) -> FoodNutritionCache | None:
        """Find cached food recommendation scoring for a breed/age combo."""
        return (
            self.db.query(FoodNutritionCache)
            .filter(
                FoodNutritionCache.species == species,
                FoodNutritionCache.breed_normalized == breed_normalized,
                FoodNutritionCache.age_context == age_context_key,
            )
            .first()
        )

    def find_food_nutrition_cache_by_label_and_type(
        self, food_label_normalized: str, food_type: str
    ) -> FoodNutritionCache | None:
        """Find cached food nutrition by normalized label and type."""
        return (
            self.db.query(FoodNutritionCache)
            .filter(
                FoodNutritionCache.food_label_normalized == food_label_normalized,
                FoodNutritionCache.food_type == food_type,
            )
            .first()
        )

    def create_food_nutrition_cache(
        self, cache: FoodNutritionCache
    ) -> FoodNutritionCache:
        """Create a new food nutrition cache record."""
        self.db.add(cache)
        self.db.flush()
        return cache
