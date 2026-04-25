"""
Health Score Calculation Logic

Pure business logic for calculating pet health scores.
No database access, no side effects — fully testable in isolation.

Formula:
    Health Score = weighted average of 6 categories
    - Vaccinations (25%)
    - Deworming (20%)
    - Tick/Flea Prevention (20%)
    - Vet Checkups (15%)
    - Nutrition (10%)
    - Conditions Management (10%)
"""

from dataclasses import dataclass
from typing import NamedTuple


class HealthCategory(NamedTuple):
    """Weighted health category score."""

    name: str  # 'vaccinations', 'deworming', etc.
    score: float  # 0-100
    weight: float  # 0-1, sum of all = 1.0


@dataclass
class HealthScoreInput:
    """Input data needed to calculate health score."""

    # Preventive care status
    vaccinations_up_to_date: bool
    deworming_up_to_date: bool
    flea_tick_up_to_date: bool

    # Last checkup (None if never, int = days ago)
    last_checkup_days_ago: int | None

    # Condition management
    has_active_conditions: bool
    conditions_properly_monitored: bool

    # Nutrition
    has_diet_record: bool

    @classmethod
    def from_repo_data(cls, repo_data: dict) -> "HealthScoreInput":
        """Factory method to create from repository data."""
        return cls(
            vaccinations_up_to_date=repo_data.get("vaccinations_up_to_date", False),
            deworming_up_to_date=repo_data.get("deworming_up_to_date", False),
            flea_tick_up_to_date=repo_data.get("flea_tick_up_to_date", False),
            last_checkup_days_ago=repo_data.get("last_checkup_days_ago"),
            has_active_conditions=repo_data.get("has_active_conditions", False),
            conditions_properly_monitored=repo_data.get("conditions_properly_monitored", False),
            has_diet_record=repo_data.get("has_diet_record", False),
        )


def calculate_vaccinations_score(up_to_date: bool) -> float:
    """Calculate vaccination category score."""
    return 100.0 if up_to_date else 50.0


def calculate_deworming_score(up_to_date: bool) -> float:
    """Calculate deworming category score."""
    return 100.0 if up_to_date else 50.0


def calculate_flea_tick_score(up_to_date: bool) -> float:
    """Calculate flea/tick prevention category score."""
    return 100.0 if up_to_date else 50.0


def calculate_checkup_score(days_ago: int | None) -> float:
    """
    Calculate checkup category score.

    Scoring:
    - None: 0 (never checked)
    - < 90 days: 100 (recent)
    - < 180 days: 80
    - < 365 days: 60
    - >= 365 days: 40 (overdue)
    """
    if days_ago is None:
        return 0.0
    if days_ago < 90:
        return 100.0
    if days_ago < 180:
        return 80.0
    if days_ago < 365:
        return 60.0
    return 40.0


def calculate_nutrition_score(has_diet_record: bool) -> float:
    """Calculate nutrition category score."""
    return 100.0 if has_diet_record else 50.0


def calculate_conditions_score(
    has_active_conditions: bool, properly_monitored: bool
) -> float:
    """
    Calculate condition management score.

    Scoring:
    - No active conditions: 100 (all clear)
    - Active but monitored: 80 (managed)
    - Active, not monitored: 30 (needs attention)
    """
    if not has_active_conditions:
        return 100.0
    if properly_monitored:
        return 80.0
    return 30.0


def calculate_health_categories(input_data: HealthScoreInput) -> list[HealthCategory]:
    """
    Calculate all health categories.

    Returns list of weighted categories.
    Pure function, fully testable.
    """
    return [
        HealthCategory("vaccinations", calculate_vaccinations_score(input_data.vaccinations_up_to_date), 0.25),
        HealthCategory("deworming", calculate_deworming_score(input_data.deworming_up_to_date), 0.20),
        HealthCategory("flea_tick", calculate_flea_tick_score(input_data.flea_tick_up_to_date), 0.20),
        HealthCategory("checkups", calculate_checkup_score(input_data.last_checkup_days_ago), 0.15),
        HealthCategory("nutrition", calculate_nutrition_score(input_data.has_diet_record), 0.10),
        HealthCategory(
            "conditions",
            calculate_conditions_score(input_data.has_active_conditions, input_data.conditions_properly_monitored),
            0.10,
        ),
    ]


def calculate_composite_score(categories: list[HealthCategory]) -> float:
    """
    Calculate weighted composite score.

    Ensures weights sum to 1.0 and all scores are in [0, 100].
    """
    # Invariant: weights must sum to 1.0
    total_weight = sum(cat.weight for cat in categories)
    assert abs(total_weight - 1.0) < 0.001, f"Weights sum to {total_weight}, expected 1.0"

    # Invariant: all scores must be in [0, 100]
    assert all(0 <= cat.score <= 100 for cat in categories), f"Scores out of range: {categories}"

    # Calculate weighted average
    total = sum(cat.score * cat.weight for cat in categories)
    # Clamp to [0, 100] as safety margin
    return min(100.0, max(0.0, total))


def get_health_status(score: float) -> str:
    """Map health score to status label."""
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "fair"
    return "poor"
