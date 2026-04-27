"""
PetAiInsight Repository — AI-generated insights for pets.

Manages caching and retrieval of insight data (health trends, recognition, etc.).
"""

import json
from uuid import UUID
from typing import List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.pet_profile.pet_ai_insight import PetAiInsight


class PetAiInsightRepository:
    """Access to pet AI insights."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_pet_and_types(self, pet_id: UUID, insight_types: List[str]) -> List[PetAiInsight]:
        """Find AI insights for a pet, filtered by insight types."""
        return (
            self.db.query(PetAiInsight)
            .filter(
                PetAiInsight.pet_id == pet_id,
                PetAiInsight.insight_type.in_(insight_types),
            )
            .all()
        )

    def find_recent_by_pet(self, pet_id: UUID, limit: int = 3) -> List[PetAiInsight]:
        """Find recent AI insights for a pet (most recent first)."""
        return (
            self.db.query(PetAiInsight)
            .filter(PetAiInsight.pet_id == pet_id)
            .order_by(desc(PetAiInsight.generated_at))
            .limit(limit)
            .all()
        )

    def create(self, pet_id: UUID, insight_type: str, content_json: dict) -> PetAiInsight:
        """Create a new AI insight."""
        insight = PetAiInsight(
            pet_id=pet_id,
            insight_type=insight_type,
            content_json=content_json,
            generated_at=datetime.now(timezone.utc),
        )
        self.db.add(insight)
        self.db.flush()
        return insight

    def delete_by_pet_and_type(self, pet_id: UUID, insight_type: str) -> None:
        """Delete insights of a specific type for a pet."""
        self.db.query(PetAiInsight).filter(
            PetAiInsight.pet_id == pet_id,
            PetAiInsight.insight_type == insight_type,
        ).delete()
        self.db.flush()

    def find_non_stale_by_pet_and_type(
        self, pet_id: UUID, insight_type: str, stale_cutoff: datetime
    ) -> PetAiInsight | None:
        """Find non-stale insight by pet and type, returning None if stale or not found."""
        return (
            self.db.query(PetAiInsight)
            .filter(
                PetAiInsight.pet_id == pet_id,
                PetAiInsight.insight_type == insight_type,
                PetAiInsight.generated_at >= stale_cutoff,
            )
            .first()
        )

    def upsert_insight(
        self, pet_id: UUID, insight_type: str, content_json: dict
    ) -> None:
        """Upsert an insight to the database."""
        from sqlalchemy import text
        self.db.execute(
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
                "content_json": json.dumps(content_json),
            },
        )
        self.db.flush()
