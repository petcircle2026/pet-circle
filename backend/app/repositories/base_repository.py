"""
Base Repository â€” Generic CRUD interface for all repositories.

Provides common patterns for database operations:
- Generic find/create/update/delete
- Eager loading helpers
- Transaction support
- Pagination utilities
"""

from typing import Generic, TypeVar, List, Optional, Type, Any, Dict
from uuid import UUID
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic repository providing common CRUD patterns."""

    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def find_by_id(self, entity_id: UUID) -> T | None:
        """Fetch a single entity by primary key ID."""
        return self.db.query(self.model).filter(self.model.id == entity_id).first()

    def find_all(self) -> List[T]:
        """Fetch all entities of this type."""
        return self.db.query(self.model).all()

    def find_all_paginated(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[T], int]:
        """Fetch paginated results with total count."""
        query = self.db.query(self.model)
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def create(self, entity: T) -> T:
        """Create and persist a new entity."""
        self.db.add(entity)
        self.db.flush()
        return entity

    def bulk_create(self, entities: List[T]) -> List[T]:
        """Create multiple entities in a single transaction."""
        self.db.add_all(entities)
        self.db.flush()
        return entities

    def update(self, entity: T) -> T:
        """Update and persist an existing entity."""
        self.db.merge(entity)
        self.db.flush()
        return entity

    def delete(self, entity_id: UUID) -> bool:
        """Delete an entity by ID. Returns True if found and deleted."""
        entity = self.find_by_id(entity_id)
        if entity:
            self.db.delete(entity)
            self.db.flush()
            return True
        return False

    def delete_many(self, entity_ids: List[UUID]) -> int:
        """Delete multiple entities. Returns count of deleted."""
        count = (
            self.db.query(self.model).filter(self.model.id.in_(entity_ids)).delete()
        )
        self.db.flush()
        return count

    def count(self) -> int:
        """Count total entities of this type."""
        return self.db.query(func.count(self.model.id)).scalar() or 0

    def count_where(self, filter_condition) -> int:
        """Count entities matching a filter condition."""
        return (
            self.db.query(func.count(self.model.id))
            .filter(filter_condition)
            .scalar()
            or 0
        )

    def exists(self, entity_id: UUID) -> bool:
        """Check if an entity exists by ID."""
        return (
            self.db.query(self.model)
            .filter(self.model.id == entity_id)
            .first()
            is not None
        )

    def refresh(self, entity: T) -> T:
        """Refresh entity state from database."""
        self.db.refresh(entity)
        return entity

