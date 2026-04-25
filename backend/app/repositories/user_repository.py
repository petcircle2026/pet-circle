"""
User Repository â€” User and dashboard token access.

Manages:
- User entity CRUD
- Dashboard token lifecycle
- User filtering and search
"""

from uuid import UUID
from typing import List
from datetime import datetime

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.models.core.user import User
from app.models.auth.dashboard_token import DashboardToken


class UserRepository:
    """Manages user data and dashboard token access."""

    def __init__(self, db: Session):
        self.db = db

    # ---- User CRUD ----

    def find_by_id(self, user_id: UUID) -> User | None:
        """Fetch a user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def find_by_id_with_pets(self, user_id: UUID) -> User | None:
        """Fetch user with all their pets (eager-loaded)."""
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .options(selectinload(User.pets))
            .first()
        )

    def find_by_whatsapp_id(self, whatsapp_id: str) -> User | None:
        """
        Find user by WhatsApp phone number.

        Args:
            whatsapp_id: WhatsApp phone number (e.g., "919999999999")

        Returns:
            User or None if not found.
        """
        return (
            self.db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
        )

    def find_by_email(self, email: str) -> User | None:
        """Fetch user by email address."""
        return self.db.query(User).filter(User.email == email).first()

    def find_all(self) -> List[User]:
        """Fetch all users (including soft-deleted)."""
        return self.db.query(User).all()

    def find_all_active(self) -> List[User]:
        """Fetch all non-deleted users."""
        return self.db.query(User).filter(User.is_deleted == False).all()

    def find_all_paginated(self, skip: int = 0, limit: int = 100) -> tuple[List[User], int]:
        """Fetch paginated active users with total count."""
        query = self.db.query(User).filter(User.is_deleted == False)
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def create(self, user: User) -> User:
        """Create a new user."""
        self.db.add(user)
        self.db.flush()
        return user

    def update(self, user: User) -> User:
        """Update an existing user."""
        self.db.merge(user)
        self.db.flush()
        return user

    def soft_delete(self, user_id: UUID) -> bool:
        """
        Soft-delete a user (mark as deleted without removing data).

        Args:
            user_id: User ID to delete

        Returns:
            True if user was found and deleted, False otherwise.
        """
        user = self.find_by_id(user_id)
        if user:
            user.is_deleted = True
            user.deleted_at = datetime.utcnow()
            self.db.merge(user)
            self.db.flush()
            return True
        return False

    def restore(self, user_id: UUID) -> bool:
        """
        Restore a soft-deleted user.

        Args:
            user_id: User ID to restore

        Returns:
            True if user was found and restored.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_deleted = False
            user.deleted_at = None
            self.db.merge(user)
            self.db.flush()
            return True
        return False

    def find_onboarded_active(self) -> List[User]:
        """Fetch active users who have completed onboarding."""
        return (
            self.db.query(User)
            .filter(
                User.is_deleted == False,
                User.onboarding_state == "complete",
                User.onboarding_completed_at.isnot(None),
            )
            .all()
        )

    def count_active(self) -> int:
        """Count non-deleted users."""
        return (
            self.db.query(func.count(User.id))
            .filter(User.is_deleted == False)
            .scalar() or 0
        )

    def count_all(self) -> int:
        """Count all users (including deleted)."""
        return self.db.query(func.count(User.id)).scalar() or 0

    # ---- Dashboard Token ----

    def find_token_by_value(self, token_value: str) -> DashboardToken | None:
        """
        Find a dashboard token by its string value.

        Args:
            token_value: The token string

        Returns:
            DashboardToken or None if not found or revoked.
        """
        return (
            self.db.query(DashboardToken)
            .filter(
                DashboardToken.token == token_value,
                DashboardToken.revoked == False,
            )
            .first()
        )

    def find_token_by_pet_id(self, pet_id: UUID) -> DashboardToken | None:
        """
        Find the active dashboard token for a pet.

        Args:
            pet_id: Pet ID

        Returns:
            Active DashboardToken or None.
        """
        return (
            self.db.query(DashboardToken)
            .filter(
                DashboardToken.pet_id == pet_id,
                DashboardToken.revoked == False,
            )
            .first()
        )

    def find_tokens_by_user_id(self, user_id: UUID) -> List[DashboardToken]:
        """Find all dashboard tokens for a user's pets."""
        return (
            self.db.query(DashboardToken)
            .join(DashboardToken.pet)
            .filter(DashboardToken.pet.user_id == user_id)
            .all()
        )

    def create_dashboard_token(self, token: DashboardToken) -> DashboardToken:
        """
        Create a new dashboard token.

        Args:
            token: DashboardToken object with pet_id and token value set

        Returns:
            Created DashboardToken.
        """
        self.db.add(token)
        self.db.flush()
        return token

    def revoke_token(self, token_id: UUID) -> bool:
        """
        Revoke a dashboard token.

        Args:
            token_id: DashboardToken ID

        Returns:
            True if token was found and revoked.
        """
        token = (
            self.db.query(DashboardToken)
            .filter(DashboardToken.id == token_id)
            .first()
        )
        if token:
            token.revoked = True
            token.revoked_at = datetime.utcnow()
            self.db.merge(token)
            self.db.flush()
            return True
        return False

    def revoke_token_by_pet_id(self, pet_id: UUID) -> bool:
        """Revoke all tokens for a specific pet."""
        tokens = self.find_tokens_by_pet_id(pet_id)
        for token in tokens:
            self.revoke_token(token.id)
        return len(tokens) > 0

    def token_exists(self, token_value: str) -> bool:
        """Check if an active token exists."""
        return self.find_token_by_value(token_value) is not None

