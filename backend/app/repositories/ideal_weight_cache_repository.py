"""
Ideal Weight Cache Repository — Cached ideal weight lookups.

Manages ideal weight cache entries for breed/species/gender/age combinations.
"""

from sqlalchemy.orm import Session

from app.models.health.ideal_weight_cache import IdealWeightCache


class IdealWeightCacheRepository:
    """Manages ideal weight cache data."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_criteria(
        self,
        species: str,
        breed_normalized: str,
        gender: str,
        age_category: str,
    ) -> IdealWeightCache | None:
        """Find cached ideal weight by species, breed, gender, and age category."""
        return (
            self.db.query(IdealWeightCache)
            .filter(
                IdealWeightCache.species == species,
                IdealWeightCache.breed_normalized == breed_normalized,
                IdealWeightCache.gender == gender,
                IdealWeightCache.age_category == age_category,
            )
            .first()
        )

    def create(self, cache_entry: IdealWeightCache) -> IdealWeightCache:
        """Create or update a cache entry."""
        self.db.add(cache_entry)
        self.db.flush()
        return cache_entry

    def update(self, cache_entry: IdealWeightCache) -> IdealWeightCache:
        """Update a cache entry."""
        self.db.merge(cache_entry)
        self.db.flush()
        return cache_entry
