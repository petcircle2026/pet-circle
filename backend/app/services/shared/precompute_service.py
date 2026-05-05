"""
PetCircle — Dashboard Precompute Service

Pre-warms the pet_ai_insights cache with all enrichments that the dashboard
needs but that are expensive to compute on demand (Anthropic API calls).

Trigger this BEFORE sending the dashboard link to the user so that the first
dashboard load reads entirely from DB with no blocking API calls.

Hook points:
    1. gpt_extraction.extract_and_process_document — after extraction success
    2. message_router._send_dashboard_links — before sending each pet's URL
    3. Any service that changes diet items (diet_service CRUD)

All functions are fire-and-forget (use asyncio.create_task) — failures are
logged but never propagate.

Performance: all 6 enrichment steps run in parallel via asyncio.gather.
Each step opens its own DB session so concurrent Anthropic API calls cannot
corrupt shared session state. Total wall-clock time drops from ~10–25 s
(sequential) to ~5 s (parallel, bottlenecked by the slowest Anthropic call).
"""

import asyncio
import json
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# TTLs for each precomputed enrichment stored in pet_ai_insights.
_DIET_SUMMARY_TTL_HOURS = 24
_RECOGNITION_BULLETS_TTL_HOURS = 24
# care_plan_reasons TTL is owned by ai_insights_service (1h) — not overridden here.


def _upsert_insight(db: Session, pet_id: UUID, insight_type: str, content: dict | list) -> None:
    """Persist an enrichment to pet_ai_insights via upsert."""
    try:
        db.execute(
            text("""
                INSERT INTO pet_ai_insights (pet_id, insight_type, content_json, generated_at)
                VALUES (:pet_id, :insight_type, CAST(:content_json AS jsonb), NOW())
                ON CONFLICT (pet_id, insight_type)
                DO UPDATE SET content_json = EXCLUDED.content_json,
                              generated_at = NOW()
            """),
            {
                "pet_id": str(pet_id),
                "insight_type": insight_type,
                "content_json": json.dumps(content),
            },
        )
        db.commit()
    except Exception as exc:
        logger.error("_upsert_insight failed pet=%s type=%s: %s", pet_id, insight_type, exc)
        db.rollback()


async def refresh_recognition_bullets(pet_id: UUID) -> None:
    """Recompute and cache recognition_bullets for a pet. Pure-DB, no GPT."""
    from app.database import SessionLocal
    from app.repositories.pet_repository import PetRepository
    db: Session = SessionLocal()
    try:
        pet_repo = PetRepository(db)
        pet = pet_repo.get_by_id(pet_id)
        if not pet:
            return
        from app.services.dashboard.ai_insights_service import generate_recognition_bullets
        bullets = await generate_recognition_bullets(db, pet)
        _upsert_insight(db, pet_id, "recognition_bullets", bullets)
        logger.info("precompute: recognition_bullets cached for pet=%s", pet_id)
    except Exception as exc:
        logger.warning("precompute: recognition_bullets failed for pet=%s: %s", pet_id, exc)
    finally:
        db.close()


async def refresh_nutrition_analysis(pet_id: UUID) -> dict:
    """Compute and cache nutrition_analysis for a pet. Returns the analysis dict."""
    from app.database import SessionLocal
    from app.services.dashboard.nutrition_service import analyze_nutrition
    db: Session = SessionLocal()
    try:
        analysis = await analyze_nutrition(db, pet_id)
        _upsert_insight(db, pet_id, "nutrition_analysis", analysis)
        logger.info("precompute: nutrition_analysis cached for pet=%s", pet_id)
        return analysis
    except Exception as exc:
        logger.warning("precompute: nutrition_analysis failed for pet=%s: %s", pet_id, exc)
        return {}
    finally:
        db.close()


async def precompute_dashboard_enrichments(pet_id_str: str) -> None:
    """
    Warm all dashboard enrichments for a pet into the pet_ai_insights cache.

    All six enrichment steps run in parallel via asyncio.gather. Each step
    opens its own DB session to avoid concurrent access on a shared session.
    diet_summary is awaited first because care_plan_reasons depends on it;
    the remaining five steps run concurrently.

    Args:
        pet_id_str: String UUID of the pet to precompute for.

    Returns:
        None. All failures are logged; the function never raises.
    """
    from app.database import SessionLocal
    from app.models.core.pet import Pet

    # Quick existence check — abort early if pet is gone.
    db_check: Session = SessionLocal()
    try:
        pet_id = UUID(pet_id_str)
        from app.repositories.pet_repository import PetRepository
        pet_repo_check = PetRepository(db_check)
        if not pet_repo_check.get_by_id(pet_id):
            logger.warning("precompute_dashboard_enrichments: pet %s not found", pet_id_str)
            return
    except Exception as exc:
        logger.error("precompute_dashboard_enrichments: setup failed for pet=%s: %s", pet_id_str, exc)
        return
    finally:
        db_check.close()

    logger.info("precompute_dashboard_enrichments: starting for pet=%s", pet_id_str)

    # ------------------------------------------------------------------
    # Helper: each step loads its own Pet + Session so concurrent tasks
    # never share session state.
    # ------------------------------------------------------------------

    async def _run_diet_summary(analysis: dict) -> dict:
        """Reformat a pre-computed nutrition analysis into the diet_summary shape."""
        from app.services.dashboard.nutrition_service import get_diet_summary
        db: Session = SessionLocal()
        try:
            result = get_diet_summary(analysis)
            _upsert_insight(db, pet_id, "diet_summary", result)
            logger.info("precompute: diet_summary cached for pet=%s", pet_id_str)
            return result
        except Exception as exc:
            logger.warning("precompute: diet_summary failed for pet=%s: %s", pet_id_str, exc)
            return {"macros": [], "missing_micros": []}
        finally:
            db.close()

    async def _run_life_stage() -> None:
        from app.repositories.pet_repository import PetRepository
        db: Session = SessionLocal()
        try:
            pet_repo = PetRepository(db)
            pet = pet_repo.get_by_id(pet_id)
            if not pet:
                return
            from app.services.dashboard.life_stage_service import get_life_stage_data
            await get_life_stage_data(db, pet)
            logger.info("precompute: life_stage_insights cached for pet=%s", pet_id_str)
        except Exception as exc:
            logger.warning("precompute: life_stage_insights failed for pet=%s: %s", pet_id_str, exc)
        finally:
            db.close()

    async def _run_health_conditions_v2() -> None:
        from app.models.core.pet import Pet as _Pet
        from app.models.health.diagnostic_test_result import DiagnosticTestResult
        from app.models.nutrition.diet_item import DietItem
        from app.services.shared.care_plan_engine import _get_life_stage, _get_pet_age_months, _get_breed_size
        from app.services.dashboard.ai_insights_service import _generate_health_conditions_v2_gpt
        from sqlalchemy import text as sa_text
        from datetime import date as _date

        db: Session = SessionLocal()
        try:
            pet = db.query(_Pet).filter(_Pet.id == pet_id).first()
            if not pet:
                return

            today = _date.today()
            age_months = _get_pet_age_months(pet)
            age_years = round(age_months / 12, 1) if age_months else None
            breed_size = _get_breed_size(float(pet.weight) if pet.weight else None, pet.breed)
            life_stage = _get_life_stage(age_months or 0, breed_size)

            pet_profile = {
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "age_years": age_years,
                "life_stage": life_stage,
                "gender": pet.gender,
                "neutered": pet.neutered,
            }

            # Aggregated conditions — one row per condition family.
            # condition_status is computed fresh here; the stored value is never trusted.
            # treatment_route and vet_resolved come from the latest episode conditions row via JOIN.
            _NON_CONDITION_NAMES = {
                "prescription medications",
                "prescription medication",
                "medications",
                "medication",
                "supplements",
                "supplement",
                "rx medications",
            }

            agg_rows = db.execute(
                sa_text("""
                    SELECT
                        ac.id                           AS condition_family_id,
                        ac.name,
                        ac.condition_type,
                        ac.episode_dates,
                        ac.diagnosed_at,
                        ac.last_record_date,
                        ac.medication_end_date,
                        ac.latest_episode_condition_id,
                        ac.soft_resolution,
                        ac.recurrence_watch,
                        ac.medications,
                        ac.monitoring,
                        c.treatment_route,
                        c.vet_resolved,
                        c.source
                    FROM aggregated_conditions ac
                    LEFT JOIN conditions c
                        ON c.id = ac.latest_episode_condition_id
                    WHERE ac.pet_id = :pet_id
                    ORDER BY ac.last_record_date DESC NULLS LAST
                """),
                {"pet_id": str(pet_id)},
            ).fetchall()

            from app.services.dashboard.condition_aggregation_service import _compute_condition_status

            def compute_status(row):
                # vet_resolved overrides all computed logic
                if row.vet_resolved:
                    return "resolved"
                return _compute_condition_status(
                    row.condition_type,
                    row.medication_end_date,
                    row.episode_dates or [],
                )

            conditions_payload = [
                {
                    "id": str(row.condition_family_id),
                    "name": row.name,
                    "condition_type": row.condition_type,
                    "condition_status": compute_status(row),
                    "soft_resolution": bool(row.soft_resolution) if row.soft_resolution is not None else False,
                    "recurrence_watch": bool(row.recurrence_watch) if row.recurrence_watch is not None else False,
                    "inferred_from_medication": (row.source or "").lower() == "inferred",
                    "episode_dates": row.episode_dates or [],
                    "diagnosed_at": str(row.diagnosed_at) if row.diagnosed_at else None,
                    "last_record_date": str(row.last_record_date) if row.last_record_date else None,
                    "medications": row.medications or [],
                    "monitoring": row.monitoring or [],
                }
                for row in agg_rows
                if row.name.lower().strip() not in _NON_CONDITION_NAMES
            ]

            # Active medications — one row per unique med name.
            # NULL end_date (lifelong/ongoing) wins over dated prescriptions;
            # among dated prescriptions the latest end_date wins.
            active_meds_raw = db.execute(
                sa_text("""
                    SELECT DISTINCT ON (LOWER(cm.name))
                        cm.name         AS med_name,
                        cm.dose,
                        cm.frequency,
                        cm.end_date,
                        c.id            AS condition_id,
                        c.name          AS condition_name,
                        c.document_id,
                        c.episode_dates
                    FROM condition_medications cm
                    JOIN conditions c ON cm.condition_id = c.id
                    WHERE c.pet_id = :pet_id
                      AND (cm.end_date >= :today OR cm.end_date IS NULL)
                    ORDER BY LOWER(cm.name), cm.end_date DESC NULLS FIRST
                """),
                {"pet_id": str(pet_id), "today": today},
            ).fetchall()

            def _null_end_date_active_pre(row) -> bool:
                episode_dates = row.episode_dates or []
                if not episode_dates:
                    return False
                try:
                    from app.utils.date_utils import parse_date
                    latest = parse_date(max(episode_dates))
                    return (today - latest).days <= 30
                except Exception:
                    return False

            active_meds = [
                m for m in active_meds_raw
                if m.end_date is not None or _null_end_date_active_pre(m)
            ]

            medications_payload = [
                {
                    "name": m.med_name,
                    "dose": m.dose,
                    "frequency": m.frequency,
                    "end_date": str(m.end_date) if m.end_date else "lifelong",
                    "for_condition": m.condition_name,
                    "condition_id": str(m.condition_id) if m.condition_id else None,
                }
                for m in active_meds
            ]

            # Abnormal lab results from DiagnosticTestResult (status_flag low/high/abnormal).
            abnormal_results = (
                db.query(DiagnosticTestResult)
                .filter(
                    DiagnosticTestResult.pet_id == pet_id,
                    DiagnosticTestResult.status_flag.in_(["low", "high", "abnormal"]),
                )
                .order_by(DiagnosticTestResult.observed_at.desc())
                .limit(50)
                .all()
            )

            labs_payload = [
                {
                    "test_name": r.parameter_name,
                    "value": str(r.value_numeric) if r.value_numeric is not None else r.value_text,
                    "unit": r.unit,
                    "status_flag": r.status_flag,
                    "report_date": str(r.observed_at),
                }
                for r in abnormal_results
            ]

            # Current diet items.
            diet_rows = db.query(DietItem).filter(DietItem.pet_id == pet_id, DietItem.is_active == True).all()

            diet_payload = [
                {
                    "item_name": d.label,
                    "item_type": d.type,
                    "daily_portion_g": d.daily_portion_g,
                    "pack_size_g": d.pack_size_g,
                    "doses_per_day": d.doses_per_day,
                }
                for d in diet_rows
            ]

            user_payload = {
                "today": today.isoformat(),
                "pet": pet_profile,
                "conditions": conditions_payload,
                "active_medications": medications_payload,
                "abnormal_labs": labs_payload,
                "current_diet": diet_payload,
            }

            result = await _generate_health_conditions_v2_gpt(user_payload)
            _upsert_insight(db, pet_id, "health_conditions_v2", result)
            logger.info("precompute: health_conditions_v2 cached for pet=%s", pet_id_str)
        except Exception as exc:
            logger.warning("precompute: health_conditions_v2 failed for pet=%s: %s", pet_id_str, exc)
        finally:
            db.close()

    async def _run_vet_questions() -> None:
        """Pre-warm per-condition ask-vet questions for every active condition.

        Uses the same insight_type key pattern (vet_questions:{condition_id}) and
        condition filter (chronic/episodic) as _get_condition_questions in
        health_trends_service so the health-trends endpoint always hits cache.
        """
        from app.repositories.pet_repository import PetRepository
        from app.repositories.care_repository import CareRepository
        db: Session = SessionLocal()
        try:
            pet_repo = PetRepository(db)
            pet = pet_repo.get_by_id(pet_id)
            if not pet:
                return
            from app.services.dashboard.ai_insights_service import get_or_generate_insight

            care_repo = CareRepository(db)
            condition_rows = care_repo.find_active_conditions_for_pet(pet_id)
            # Filter to chronic/episodic only (additional filter beyond active)
            condition_rows = [c for c in condition_rows if c.condition_type in {"chronic", "episodic", "recurrent"}]

            if not condition_rows:
                return

            pet_dict = {"name": pet.name, "species": pet.species, "breed": pet.breed}

            async def _warm_one(cond: Condition) -> None:
                condition_payload = {
                    "name": cond.name,
                    "condition_type": cond.condition_type,
                    "medications": [
                        {"name": m.name, "dose": m.dose, "frequency": m.frequency}
                        for m in (cond.medications or [])
                    ],
                    "monitoring": [
                        {
                            "name": m.name,
                            "next_due_date": m.next_due_date.isoformat() if m.next_due_date else None,
                            "last_done_date": m.last_done_date.isoformat() if m.last_done_date else None,
                        }
                        for m in (cond.monitoring or [])
                    ],
                }
                await get_or_generate_insight(
                    db=db,
                    pet_id=pet.id,
                    insight_type=f"vet_questions:{cond.id}",
                    pet=pet_dict,
                    conditions=[condition_payload],
                    force=False,
                )

            # Warm all conditions concurrently — each uses a different insight_type key.
            await asyncio.gather(*[_warm_one(cond) for cond in condition_rows])
            logger.info(
                "precompute: vet_questions cached for pet=%s (%d conditions)",
                pet_id_str, len(condition_rows),
            )
        except Exception as exc:
            logger.warning("precompute: vet_questions failed for pet=%s: %s", pet_id_str, exc)
        finally:
            db.close()

    async def _run_care_plan_reasons(diet_summary: dict) -> None:
        from app.repositories.pet_repository import PetRepository
        db: Session = SessionLocal()
        try:
            pet_repo = PetRepository(db)
            pet = pet_repo.get_by_id(pet_id)
            if not pet:
                return
            from app.services.shared.care_plan_engine import compute_care_plan
            from app.services.dashboard.ai_insights_service import generate_care_plan_reasons
            from app.services.dashboard.dashboard_service import (
                _normalize_care_plan_shape,
                _collect_orderable_items,
            )
            care_plan_raw = compute_care_plan(db, pet)
            care_plan = _normalize_care_plan_shape(care_plan_raw)
            orderable_items = _collect_orderable_items(care_plan)
            if orderable_items:
                await generate_care_plan_reasons(
                    db, pet, orderable_items, diet_summary=diet_summary
                )
                logger.info("precompute: care_plan_reasons cached for pet=%s", pet_id_str)
        except Exception as exc:
            logger.warning("precompute: care_plan_reasons failed for pet=%s: %s", pet_id_str, exc)
        finally:
            db.close()

    try:
        # Phase 1: run all independent AI enrichments in parallel.
        # refresh_nutrition_analysis returns the analysis dict so Phase 2 can reuse it
        # without a second analyze_nutrition() call.
        analysis, *_ = await asyncio.gather(
            refresh_nutrition_analysis(pet_id),
            refresh_recognition_bullets(pet_id),
            _run_life_stage(),
            _run_health_conditions_v2(),
            _run_vet_questions(),
        )

        # Phase 2: diet_summary reformats the already-computed analysis (no AI call).
        diet_summary = await _run_diet_summary(analysis)

        # Phase 3: care_plan_reasons depends on diet_summary.
        await _run_care_plan_reasons(diet_summary)

        logger.info("precompute_dashboard_enrichments: completed for pet=%s", pet_id_str)

    except Exception as exc:
        logger.error("precompute_dashboard_enrichments: fatal error for pet=%s: %s", pet_id_str, exc)
