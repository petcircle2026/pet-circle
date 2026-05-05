"""
Backfill aggregated_conditions for all pets.

Handles two cases:
  1. Pet has conditions but no aggregated_conditions rows at all
     → runs aggregate_conditions_for_pet to create them.
  2. Pet has aggregated_conditions rows but latest_episode_condition_id is NULL
     → re-runs aggregation to set it (same function, idempotent upsert).

Run:
    cd backend && APP_ENV=production python scripts/backfill_aggregated_conditions.py
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    from app.database import SessionLocal
    from app.models.core.pet import Pet
    from app.models.health.condition import Condition
    from app.models.health.aggregated_condition import AggregatedCondition
    from app.services.dashboard.condition_aggregation_service import aggregate_conditions_for_pet
    from sqlalchemy import func

    db = SessionLocal()
    try:
        # Pets that have at least one active condition.
        pets_with_conditions = (
            db.query(Condition.pet_id)
            .filter(Condition.is_active == True)
            .distinct()
            .all()
        )
        pet_ids = [row.pet_id for row in pets_with_conditions]
        logger.info("Found %d pets with active conditions", len(pet_ids))

        ok = 0
        failed = 0
        for pet_id in pet_ids:
            # Check whether this pet needs backfill:
            # - no aggregated_conditions rows, OR
            # - any aggregated_conditions row has latest_episode_condition_id NULL
            needs_backfill = (
                db.query(AggregatedCondition)
                .filter(
                    AggregatedCondition.pet_id == pet_id,
                    AggregatedCondition.latest_episode_condition_id == None,
                )
                .first()
                is not None
            ) or (
                db.query(func.count(AggregatedCondition.id))
                .filter(AggregatedCondition.pet_id == pet_id)
                .scalar()
                == 0
            )

            if not needs_backfill:
                continue

            try:
                await aggregate_conditions_for_pet(db, pet_id)
                db.commit()
                logger.info("Aggregated pet=%s", pet_id)
                ok += 1
            except Exception as exc:
                db.rollback()
                logger.warning("Failed pet=%s: %s", pet_id, exc)
                failed += 1

        logger.info("Done — %d succeeded, %d failed", ok, failed)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
