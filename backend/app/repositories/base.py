"""
Base repository interface for all data access patterns.

Defines the common CRUD operations that all repositories implement.
"""

from typing import Generic, TypeVar, Protocol
from uuid import UUID

T = TypeVar('T')


class Repository(Generic[T], Protocol):
    """
    Base protocol for all repositories.

    All repositories must implement these core methods for consistency.
    Specific repositories may add domain-specific query methods.
    """

    def get_by_id(self, id: UUID) -> T | None:
        """Fetch single entity by ID. Return None if not found."""
        ...

    def get_all(self) -> list[T]:
        """Fetch all entities."""
        ...

    def create(self, **kwargs) -> T:
        """Create new entity. Caller must commit session."""
        ...

    def update(self, id: UUID, updates: dict) -> T | None:
        """Update entity by ID. Return updated entity or None if not found."""
        ...

    def delete(self, id: UUID) -> bool:
        """Delete entity by ID. Return True if found and deleted."""
        ...
