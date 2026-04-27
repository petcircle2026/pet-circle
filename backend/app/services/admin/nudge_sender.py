"""
PetCircle Phase 1 — Nudge Sender Service

Engagement tracking and inactivity detection.

WhatsApp nudge delivery (Excel v5) is handled by nudge_scheduler.py.

Entry points:
    - check_inactivity_nudges(db): Detect 30d inactive users, create re-engagement nudges
    - record_nudge_engagement(db, user_id, pet_id): On user action (button tap)
"""
from app.models.cache.nudge_engagement import NudgeEngagement

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.constants import NUDGE_TRIGGER_INACTIVITY
from app.models.messaging.nudge import Nudge
from app.repositories.pet_repository import PetRepository
from app.repositories.nudge_repository import NudgeRepository
from app.services.admin.nudge_config_service import get_nudge_config_int

logger = logging.getLogger(__name__)


def check_inactivity_nudges(db: Session) -> dict:
    """
    Find users with no activity in N days and create re-engagement nudges.

    Inactivity threshold is configured via nudge_config table.
    """
    threshold_days = get_nudge_config_int(db, "inactivity_threshold_days", 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)

    pet_repo = PetRepository(db)
    nudge_repo = NudgeRepository(db)

    pets = pet_repo.find_active_with_user_by_onboarding_state("complete")

    created = 0
    for pet in pets:
        engagement = nudge_repo.find_engagement_by_user_and_pet(pet.user_id, pet.id)

        # Skip if recently engaged or paused
        if engagement:
            if engagement.last_engagement_at and engagement.last_engagement_at > cutoff:
                continue
            if engagement.paused_until and engagement.paused_until > datetime.now(timezone.utc):
                continue

        # Check if we already have a recent inactivity nudge
        existing = nudge_repo.find_by_pet_id(pet.id)
        has_recent_inactivity = any(
            n.trigger_type == NUDGE_TRIGGER_INACTIVITY
            and n.dismissed == False
            and n.created_at >= cutoff
            for n in existing
        )
        if has_recent_inactivity:
            continue

        nudge = Nudge(
            pet_id=pet.id,
            category="checkup",
            priority="medium",
            icon="👋",
            title=f"We miss {pet.name}!",
            message=f"It's been a while since you checked in on {pet.name}'s health. Open the dashboard to review.",
            trigger_type=NUDGE_TRIGGER_INACTIVITY,
            source="record",
        )
        nudge_repo.create(nudge)
        created += 1

    if created > 0:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to create inactivity nudges")

    logger.info("Inactivity nudges created: %d", created)
    return {"inactivity_nudges_created": created}


def record_nudge_engagement(db: Session, user_id, pet_id):
    """
    Record that a user acted on a nudge (button tap).
    Clears pause, updates counters.
    """
    nudge_repo = NudgeRepository(db)
    engagement = nudge_repo.find_engagement_by_user_and_pet(user_id, pet_id)

    if engagement:
        engagement.last_engagement_at = datetime.now(timezone.utc)
        engagement.paused_until = None
        engagement.total_acted_on = (engagement.total_acted_on or 0) + 1
        nudge_repo.update_engagement(engagement)
    else:
        engagement = NudgeEngagement(
            user_id=user_id,
            pet_id=pet_id,
            last_engagement_at=datetime.now(timezone.utc),
            total_acted_on=1,
        )
        nudge_repo.create_engagement(engagement)

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to record nudge engagement")
