"""
Backfill aggregated_conditions for all pets.

Re-aggregates every pet that has at least one active condition, whether or not
aggregated rows already exist. This is safe to re-run at any time — the
aggregation function is an idempotent upsert.

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
    from app.models.health.condition import Condition
    from app.services.dashboard.condition_aggregation_service import aggregate_conditions_for_pet

    db = SessionLocal()
    try:
        pet_ids = [
            row.pet_id
            for row in db.query(Condition.pet_id)
            .filter(Condition.is_active == True)
            .distinct()
            .all()
        ]
        logger.info("Found %d pets with active conditions", len(pet_ids))

        ok = 0
        failed = 0
        for pet_id in pet_ids:
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
