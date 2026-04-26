"""
Pet Repository â€” Centralized Pet entity data access.

All queries about pets live here. This is the single source of truth
for how pets are fetched, created, updated, and deleted.
"""

from uuid import UUID
from datetime import datetime

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session, selectinload, joinedload

from app.models.core.pet import Pet


class PetRepository:
    """Encapsulates all Pet database queries."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Basic CRUD ----

    def get_by_id(self, pet_id: UUID) -> Pet | None:
        """Fetch a single pet by ID."""
        return self.db.query(Pet).filter(Pet.id == pet_id).first()

    def get_by_id_with_relations(self, pet_id: UUID) -> Pet | None:
        """
        Fetch pet WITH related data (conditions, preventive records).

        Use this when you need pet + full health context.
        Prevents N+1: eager-loads all relations at once.
        """
        return (
            self.db.query(Pet)
            .filter(Pet.id == pet_id)
            .options(
                selectinload(Pet.conditions),
                selectinload(Pet.weight_history),
            )
            .first()
        )

    def get_by_id_with_user(self, pet_id: UUID) -> Pet | None:
        """
        Fetch pet WITH its owner (User).

        Use when building dashboard or detail views that need owner info.
        Prevents N+1: loads pet and user in one query.
        """
        return (
            self.db.query(Pet)
            .options(joinedload(Pet.user))
            .filter(Pet.id == pet_id)
            .first()
        )

    def get_all(self) -> list[Pet]:
        """Fetch all active pets in system (admin use)."""
        return (
            self.db.query(Pet)
            .filter(Pet.is_deleted == False)
            .order_by(desc(Pet.created_at))
            .all()
        )

    def create(
        self, user_id: UUID, name: str, species: str, breed: str | None = None
    ) -> Pet:
        """
        Create a new pet.

        Args:
            user_id: Owner user ID
            name: Pet name
            species: 'dog' or 'cat'
            breed: Optional breed name

        Returns: New Pet instance (not yet committed)
        """
        pet = Pet(
            user_id=user_id,
            name=name,
            species=species,
            breed=breed,
        )
        self.db.add(pet)
        return pet

    # ---- Queries by user ----

    def get_by_user(self, user_id: UUID) -> list[Pet]:
        """Fetch all active pets for a user, sorted by creation date (newest first)."""
        return (
            self.db.query(Pet)
            .filter(and_(Pet.user_id == user_id, Pet.is_deleted == False))
            .order_by(desc(Pet.created_at))
            .all()
        )

    def get_by_user_with_relations(self, user_id: UUID) -> list[Pet]:
        """
        Fetch all pets for user WITH conditions and weight history (eager load).

        Use when building dashboard for multiple pets.
        """
        return (
            self.db.query(Pet)
            .filter(and_(Pet.user_id == user_id, Pet.is_deleted == False))
            .options(
                selectinload(Pet.conditions),
                selectinload(Pet.weight_history),
            )
            .order_by(desc(Pet.created_at))
            .all()
        )

    def get_most_recent(self, user_id: UUID) -> Pet | None:
        """
        Get user's most recently created pet.

        Used in onboarding as the default pet for new records.
        """
        return (
            self.db.query(Pet)
            .filter(and_(Pet.user_id == user_id, Pet.is_deleted == False))
            .order_by(desc(Pet.created_at))
            .first()
        )

    # ---- Validation queries ----

    def count_by_user(self, user_id: UUID) -> int:
        """
        Count active pets for a user.

        Used to enforce MAX_PETS_PER_USER constraint (5 pets max).
        """
        return (
            self.db.query(Pet)
            .filter(and_(Pet.user_id == user_id, Pet.is_deleted == False))
            .count()
        )

    def exists_by_id(self, pet_id: UUID) -> bool:
        """Check if a pet exists (fast check)."""
        return (
            self.db.query(Pet).filter(Pet.id == pet_id).with_entities(Pet.id).first()
            is not None
        )

    # ---- Search queries ----

    def get_by_species(self, species: str) -> list[Pet]:
        """Fetch all pets of a given species ('dog' or 'cat')."""
        return (
            self.db.query(Pet)
            .filter(and_(Pet.species == species, Pet.is_deleted == False))
            .all()
        )

    def get_by_name(self, user_id: UUID, name: str) -> Pet | None:
        """Fetch a pet by name for a specific user (case-insensitive)."""
        return (
            self.db.query(Pet)
            .filter(
                and_(
                    Pet.user_id == user_id,
                    Pet.name.ilike(name),
                    Pet.is_deleted == False,
                )
            )
            .first()
        )

    # ---- Soft delete ----

    def soft_delete(self, pet_id: UUID) -> bool:
        """Mark a pet as deleted without physical removal."""
        pet = self.get_by_id(pet_id)
        if pet:
            pet.is_deleted = True
            pet.deleted_at = datetime.utcnow()
            return True
        return False

    # ---- Update operations ----

    def update_name(self, pet_id: UUID, new_name: str) -> Pet | None:
        """Update pet's name."""
        pet = self.get_by_id(pet_id)
        if pet:
            pet.name = new_name
            return pet
        return None

    def update_weight(self, pet_id: UUID, weight: float) -> Pet | None:
        """Update pet's current weight."""
        pet = self.get_by_id(pet_id)
        if pet:
            pet.weight = weight
            return pet
        return None

    def find_by_user_id(self, user_id: UUID) -> list[Pet]:
        """Fetch all active pets for a user."""
        return (
            self.db.query(Pet)
            .filter(Pet.user_id == user_id, Pet.is_deleted == False)
            .all()
        )

    def find_onboarded_active(self) -> list[Pet]:
        """Fetch all active pets whose owners have completed onboarding."""
        from app.models.core.user import User
        return (
            self.db.query(Pet)
            .join(User)
            .filter(
                Pet.is_deleted == False,
                User.onboarding_state == "complete",
            )
            .all()
        )

    def count_all(self) -> int:
        """Count total active pets in the system."""
        from sqlalchemy import func
        return self.db.query(func.count(Pet.id)).filter(Pet.is_deleted == False).scalar() or 0

    def find_by_user_desc(self, user_id: UUID) -> list:
        """Find pets for a user ordered by creation date (descending)."""
        return (
            self.db.query(Pet)
            .filter(Pet.user_id == user_id, Pet.is_deleted == False)
            .order_by(Pet.created_at.desc())
            .all()
        )

    def has_pet_with_id(self, pet_id: UUID) -> bool:
        """Check if pet exists."""
        return (
            self.db.query(Pet.id)
            .filter(Pet.id == pet_id, Pet.is_deleted == False)
            .first() is not None
        )

