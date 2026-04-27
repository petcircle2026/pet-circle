"""
Agent Order Session Repository — Agent order conversation state.

Manages storage and retrieval of agent order conversation sessions.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.commerce.agent_order_session import AgentOrderSession


class AgentOrderSessionRepository:
    """Manages agent order session data."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, session_id: UUID) -> AgentOrderSession | None:
        """Fetch a session by ID."""
        return (
            self.db.query(AgentOrderSession)
            .filter(AgentOrderSession.id == session_id)
            .first()
        )

    def find_active_by_user(self, user_id: UUID) -> AgentOrderSession | None:
        """Find the most recent active order session for a user."""
        return (
            self.db.query(AgentOrderSession)
            .filter(
                AgentOrderSession.user_id == user_id,
                AgentOrderSession.status == "in_progress",
            )
            .order_by(desc(AgentOrderSession.created_at))
            .first()
        )

    def create(self, session: AgentOrderSession) -> AgentOrderSession:
        """Create a new agent order session."""
        self.db.add(session)
        self.db.flush()
        return session

    def update(self, session: AgentOrderSession) -> AgentOrderSession:
        """Update an agent order session."""
        self.db.merge(session)
        self.db.flush()
        return session

    def delete(self, session_id: UUID) -> bool:
        """Delete a session."""
        session = self.find_by_id(session_id)
        if session:
            self.db.delete(session)
            self.db.flush()
            return True
        return False

    def find_by_user(self, user_id: UUID) -> List[AgentOrderSession]:
        """Find all sessions for a user."""
        return (
            self.db.query(AgentOrderSession)
            .filter(AgentOrderSession.user_id == user_id)
            .order_by(desc(AgentOrderSession.created_at))
            .all()
        )
