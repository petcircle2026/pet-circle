"""
Dashboard Token Repository — Secure dashboard access tokens.

Manages 128-bit random tokens for sharing pet health dashboard access.
"""

from uuid import UUID
from typing import List
from datetime import datetime, timezone

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

    def find_active_by_pet(self, pet_id: UUID) -> DashboardToken | None:
        """Find the active (is_active=True) dashboard token for a pet."""
        return (
            self.db.query(DashboardToken)
            .filter(DashboardToken.pet_id == pet_id, DashboardToken.is_active == True)
            .first()
        )

    def find_active_by_pet_ids(self, pet_ids: List[UUID]) -> List[DashboardToken]:
        """Find all non-revoked dashboard tokens for multiple pets."""
        return (
            self.db.query(DashboardToken)
            .filter(DashboardToken.pet_id.in_(pet_ids), DashboardToken.revoked == False)
            .all()
        )

    def find_active_non_expired_by_pet(self, pet_id: UUID) -> DashboardToken | None:
        """Find the most recent non-revoked, non-expired token for a pet."""
        now_utc = datetime.now(timezone.utc)
        return (
            self.db.query(DashboardToken)
            .filter(
                DashboardToken.pet_id == pet_id,
                DashboardToken.revoked == False,
                DashboardToken.expires_at.isnot(None),
                DashboardToken.expires_at > now_utc,
            )
            .order_by(DashboardToken.created_at.desc())
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

    def revoke_active_tokens(self, pet_id: UUID) -> int:
        """Revoke all non-revoked tokens for a pet."""
        count = (
            self.db.query(DashboardToken)
            .filter(DashboardToken.pet_id == pet_id, DashboardToken.revoked == False)
            .update({DashboardToken.revoked: True})
        )
        self.db.flush()
        return count
