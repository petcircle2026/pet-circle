"""
PetCircle Phase 1 — Conflict Expiry Cron (Module 19)

Automatically resolves pending conflicts that have exceeded the
expiry window (CONFLICT_EXPIRY_DAYS = 5 days).

Expiry logic:
    - Query all conflict_flags with status='pending' and
      created_at older than CONFLICT_EXPIRY_DAYS.
    - Set status to 'auto_resolved' — the existing date is kept.
    - This implements the KEEP_EXISTING strategy by default.
    - Log every auto-resolution as a system action.
    - No user notification is sent for auto-resolved conflicts.

This function is designed to be called from the daily cron job
(same schedule as the reminder engine — 8 AM IST).
Execution is stateless — safe to re-run multiple times.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.constants import CONFLICT_EXPIRY_DAYS
from app.repositories.audit_repository import AuditRepository
from app.utils.date_utils import IST

logger = logging.getLogger(__name__)


def expire_pending_conflicts(db: Session) -> int:
    """
    Auto-resolve all conflicts that have exceeded the expiry window.

    Conflicts older than CONFLICT_EXPIRY_DAYS (5 days) are automatically
    resolved with the KEEP_EXISTING strategy:
        - status is set to 'auto_resolved'
        - The new_date is effectively discarded
        - The existing preventive record remains unchanged
        - No user notification is sent

    This function is stateless and idempotent — it can be safely called
    multiple times without side effects. Already resolved or auto_resolved
    conflicts are not affected.

    The expiry cutoff is computed in Asia/Kolkata timezone to ensure
    consistent behavior regardless of server timezone.

    Args:
        db: SQLAlchemy database session.

    Returns:
        Number of conflicts that were auto-resolved.
    """
    now_ist = datetime.now(IST)
    expiry_cutoff = now_ist - timedelta(days=CONFLICT_EXPIRY_DAYS)

    audit_repo = AuditRepository(db)
    expired_conflicts = audit_repo.find_conflicts_by_status_before("pending", expiry_cutoff)

    if not expired_conflicts:
        logger.info("No expired conflicts found. Nothing to auto-resolve.")
        return 0

    resolved_count = 0
    for conflict in expired_conflicts:
        conflict.status = "auto_resolved"
        resolved_count += 1

        logger.info(
            "Conflict auto-resolved (expired): conflict_id=%s, "
            "preventive_record_id=%s, discarded_date=%s, "
            "created_at=%s, expiry_days=%d",
            str(conflict.id),
            str(conflict.preventive_record_id),
            str(conflict.new_date),
            str(conflict.created_at),
            CONFLICT_EXPIRY_DAYS,
        )

    db.commit()

    logger.info(
        "Auto-resolved %d expired conflicts (older than %d days).",
        resolved_count,
        CONFLICT_EXPIRY_DAYS,
    )

    return resolved_count
