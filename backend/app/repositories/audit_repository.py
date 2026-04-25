"""
Audit Repository â€” Audit trail and engagement tracking.

Manages:
- Conflict flags
- Deferred care plans
- AI insights
- Agent order sessions
- Dashboard visits
"""

from uuid import UUID
from typing import List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.health.conflict_flag import ConflictFlag
from app.models.preventive.deferred_care_plan_pending import DeferredCarePlanPending
from app.models.pet_profile.pet_ai_insight import PetAIInsight
from app.models.commerce.agent_order_session import AgentOrderSession
from app.models.cache.dashboard_visit import DashboardVisit


class AuditRepository:
    """Manages audit trail and engagement data."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Conflict Flag ----

    def log_conflict(self, conflict: ConflictFlag) -> ConflictFlag:
        """Create a conflict flag."""
        self.db.add(conflict)
        self.db.flush()
        return conflict

    def find_conflict_by_id(self, conflict_id: UUID) -> ConflictFlag | None:
        """Fetch a conflict flag by ID."""
        return (
            self.db.query(ConflictFlag)
            .filter(ConflictFlag.id == conflict_id)
            .first()
        )

    def find_conflicts_by_pet(self, pet_id: UUID) -> List[ConflictFlag]:
        """Fetch all conflicts for a pet."""
        return (
            self.db.query(ConflictFlag)
            .filter(ConflictFlag.pet_id == pet_id)
            .order_by(desc(ConflictFlag.created_at))
            .all()
        )

    def find_conflicts_by_user(self, user_id: UUID) -> List[ConflictFlag]:
        """Fetch all conflicts for a user's pets."""
        return (
            self.db.query(ConflictFlag)
            .join(ConflictFlag.pet)
            .filter(ConflictFlag.pet.user_id == user_id)
            .order_by(desc(ConflictFlag.created_at))
            .all()
        )

    def find_active_conflicts(self) -> List[ConflictFlag]:
        """Fetch all unresolved conflicts."""
        return (
            self.db.query(ConflictFlag)
            .filter(ConflictFlag.resolved == False)
            .order_by(ConflictFlag.created_at)
            .all()
        )

    def find_conflicts_by_type(self, conflict_type: str) -> List[ConflictFlag]:
        """Find conflicts by type."""
        return (
            self.db.query(ConflictFlag)
            .filter(ConflictFlag.conflict_type == conflict_type)
            .all()
        )

    def find_conflicts_by_status_before(
        self, status: str, before: datetime
    ) -> List[ConflictFlag]:
        """Find conflicts with given status created before a timestamp."""
        return (
            self.db.query(ConflictFlag)
            .filter(
                ConflictFlag.status == status,
                ConflictFlag.created_at <= before,
            )
            .all()
        )

    def mark_conflict_resolved(self, conflict_id: UUID) -> ConflictFlag | None:
        """
        Mark a conflict as resolved.

        Args:
            conflict_id: ConflictFlag ID

        Returns:
            Updated ConflictFlag or None if not found.
        """
        conflict = self.find_conflict_by_id(conflict_id)
        if conflict:
            conflict.resolved = True
            conflict.resolved_at = datetime.utcnow()
            self.db.merge(conflict)
            self.db.flush()
            return conflict
        return None

    def clear_expired_conflicts(self, days: int = 30) -> int:
        """
        Delete resolved conflicts older than N days.

        Args:
            days: Age threshold

        Returns:
            Count of deleted conflicts.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        count = (
            self.db.query(ConflictFlag)
            .filter(
                ConflictFlag.resolved == True,
                ConflictFlag.resolved_at < cutoff,
            )
            .delete()
        )
        self.db.flush()
        return count

    def count_active_conflicts(self) -> int:
        """Count unresolved conflicts."""
        return (
            self.db.query(func.count(ConflictFlag.id))
            .filter(ConflictFlag.resolved == False)
            .scalar() or 0
        )

    # ---- Deferred Care Plan ----

    def create_deferred_plan(
        self, plan: DeferredCarePlanPending
    ) -> DeferredCarePlanPending:
        """Create a deferred care plan."""
        self.db.add(plan)
        self.db.flush()
        return plan

    def find_deferred_plan_by_id(
        self, plan_id: UUID
    ) -> DeferredCarePlanPending | None:
        """Fetch a deferred plan by ID."""
        return (
            self.db.query(DeferredCarePlanPending)
            .filter(DeferredCarePlanPending.id == plan_id)
            .first()
        )

    def find_deferred_plans(self, pet_id: UUID) -> List[DeferredCarePlanPending]:
        """Fetch all deferred plans for a pet."""
        return (
            self.db.query(DeferredCarePlanPending)
            .filter(DeferredCarePlanPending.pet_id == pet_id)
            .all()
        )

    def find_pending_deferred_plans(self) -> List[DeferredCarePlanPending]:
        """Fetch all unexecuted deferred plans."""
        return (
            self.db.query(DeferredCarePlanPending)
            .filter(DeferredCarePlanPending.executed == False)
            .order_by(DeferredCarePlanPending.created_at)
            .all()
        )

    def mark_plan_executed(self, plan_id: UUID) -> DeferredCarePlanPending | None:
        """Mark a deferred plan as executed."""
        plan = self.find_deferred_plan_by_id(plan_id)
        if plan:
            plan.executed = True
            plan.executed_at = datetime.utcnow()
            self.db.merge(plan)
            self.db.flush()
            return plan
        return None

    # ---- AI Insight ----

    def log_ai_insight(self, insight: PetAIInsight) -> PetAIInsight:
        """Create an AI insight record."""
        self.db.add(insight)
        self.db.flush()
        return insight

    def find_insight_by_id(self, insight_id: UUID) -> PetAIInsight | None:
        """Fetch an AI insight by ID."""
        return (
            self.db.query(PetAIInsight)
            .filter(PetAIInsight.id == insight_id)
            .first()
        )

    def find_insights_by_pet(self, pet_id: UUID) -> List[PetAIInsight]:
        """Fetch all insights for a pet."""
        return (
            self.db.query(PetAIInsight)
            .filter(PetAIInsight.pet_id == pet_id)
            .order_by(desc(PetAIInsight.created_at))
            .all()
        )

    def find_latest_insight(self, pet_id: UUID) -> PetAIInsight | None:
        """Fetch the most recent insight for a pet."""
        return (
            self.db.query(PetAIInsight)
            .filter(PetAIInsight.pet_id == pet_id)
            .order_by(desc(PetAIInsight.created_at))
            .first()
        )

    def find_latest_insight_by_type(
        self, pet_id: UUID, insight_type: str
    ) -> PetAIInsight | None:
        """Fetch the most recent insight of a specific type for a pet."""
        return (
            self.db.query(PetAIInsight)
            .filter(
                PetAIInsight.pet_id == pet_id,
                PetAIInsight.insight_type == insight_type,
            )
            .order_by(desc(PetAIInsight.created_at))
            .first()
        )

    def find_insights_by_type(self, pet_id: UUID, insight_type: str) -> List[PetAIInsight]:
        """Find insights of a specific type."""
        return (
            self.db.query(PetAIInsight)
            .filter(
                PetAIInsight.pet_id == pet_id,
                PetAIInsight.insight_type == insight_type,
            )
            .order_by(desc(PetAIInsight.created_at))
            .all()
        )

    # ---- Agent Order Session ----

    def create_order_session(
        self, session: AgentOrderSession
    ) -> AgentOrderSession:
        """Create an order session."""
        self.db.add(session)
        self.db.flush()
        return session

    def find_session_by_id(self, session_id: UUID) -> AgentOrderSession | None:
        """Fetch an order session by ID."""
        return (
            self.db.query(AgentOrderSession)
            .filter(AgentOrderSession.id == session_id)
            .first()
        )

    def find_sessions_by_user(self, user_id: UUID) -> List[AgentOrderSession]:
        """Fetch all order sessions for a user."""
        return (
            self.db.query(AgentOrderSession)
            .filter(AgentOrderSession.user_id == user_id)
            .order_by(desc(AgentOrderSession.created_at))
            .all()
        )

    def find_active_session(self, user_id: UUID) -> AgentOrderSession | None:
        """Find the active (not completed) order session for a user."""
        return (
            self.db.query(AgentOrderSession)
            .filter(
                AgentOrderSession.user_id == user_id,
                AgentOrderSession.completed == False,
            )
            .order_by(desc(AgentOrderSession.created_at))
            .first()
        )

    def mark_session_completed(self, session_id: UUID) -> AgentOrderSession | None:
        """Mark an order session as completed."""
        session = self.find_session_by_id(session_id)
        if session:
            session.completed = True
            session.completed_at = datetime.utcnow()
            self.db.merge(session)
            self.db.flush()
            return session
        return None

    # ---- Dashboard Visit ----

    def log_dashboard_visit(self, visit: DashboardVisit) -> DashboardVisit:
        """Log a dashboard visit."""
        self.db.add(visit)
        self.db.flush()
        return visit

    def find_visits_by_token(self, token_id: UUID) -> List[DashboardVisit]:
        """Fetch all visits for a dashboard token."""
        return (
            self.db.query(DashboardVisit)
            .filter(DashboardVisit.token_id == token_id)
            .order_by(desc(DashboardVisit.visited_at))
            .all()
        )

    def find_recent_visits(
        self, token_id: UUID, limit: int = 50
    ) -> List[DashboardVisit]:
        """Fetch recent visits for a token."""
        return (
            self.db.query(DashboardVisit)
            .filter(DashboardVisit.token_id == token_id)
            .order_by(desc(DashboardVisit.visited_at))
            .limit(limit)
            .all()
        )

    def count_visits(self, token_id: UUID) -> int:
        """Count total visits for a token."""
        return (
            self.db.query(func.count(DashboardVisit.id))
            .filter(DashboardVisit.token_id == token_id)
            .scalar() or 0
        )

    def count_visits_today(self, token_id: UUID) -> int:
        """Count visits today."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        return (
            self.db.query(func.count(DashboardVisit.id))
            .filter(
                DashboardVisit.token_id == token_id,
                DashboardVisit.visited_at >= today_start,
            )
            .scalar() or 0
        )

    # ---- Engagement Summary ----

    def get_engagement_summary(self, pet_id: UUID) -> dict:
        """
        Get a summary of user engagement with a pet.

        Returns:
            Dictionary with counts of various engagement metrics.
        """
        return {
            "conflicts": self.db.query(func.count(ConflictFlag.id)).filter(
                ConflictFlag.pet_id == pet_id
            ).scalar() or 0,
            "deferred_plans": self.db.query(func.count(DeferredCarePlanPending.id)).filter(
                DeferredCarePlanPending.pet_id == pet_id
            ).scalar() or 0,
            "insights": self.db.query(func.count(PetAIInsight.id)).filter(
                PetAIInsight.pet_id == pet_id
            ).scalar() or 0,
        }

