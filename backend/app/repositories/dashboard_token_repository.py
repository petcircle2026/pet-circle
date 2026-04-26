"""
Dashboard Token Repository — Secure dashboard access tokens.

Manages 128-bit random tokens for sharing pet health dashboard access.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from app.models.auth.dashboard_token import DashboardToken


class DashboardTokenRepository:
    """Manages dashboard access tokens."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_token(self, token: str) -> DashboardToken | None:
        """Find a dashboard token by its token string."""
        return (
            self.db.query(DashboardToken)
            .filter(DashboardToken.token == token)
            .first()
        )

    def find_by_pet_id(self, pet_id: UUID) -> DashboardToken | None:
        """Find the active dashboard token for a pet."""
        return (
            self.db.query(DashboardToken)
            .filter(DashboardToken.pet_id == pet_id)
            .first()
        )

    def find_active_by_pet_id(self, pet_id: UUID) -> DashboardToken | None:
        """Find the active (non-revoked) dashboard token for a pet."""
        return (
            self.db.query(DashboardToken)
            .filter(
                DashboardToken.pet_id == pet_id,
                DashboardToken.revoked == False,
            )
            .first()
        )

    def create(
        self, pet_id: UUID, token: str, expires_at
    ) -> DashboardToken:
        """Create a new dashboard token."""
        dashboard_token = DashboardToken(
            pet_id=pet_id,
            token=token,
            expires_at=expires_at,
        )
        self.db.add(dashboard_token)
        self.db.flush()
        return dashboard_token

    def revoke(self, pet_id: UUID) -> int:
        """Revoke all tokens for a pet."""
        count = (
            self.db.query(DashboardToken)
            .filter(DashboardToken.pet_id == pet_id)
            .update({DashboardToken.revoked: True})
        )
        self.db.flush()
        return count
