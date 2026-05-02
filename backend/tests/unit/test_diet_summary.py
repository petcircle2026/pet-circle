"""
Unit tests for get_diet_summary() and _diet_summary_threshold() in nutrition_service.py.

Covers:
  - _diet_summary_threshold: all 4 macros across every threshold boundary
  - Omega-3 at exactly 15 % -> RED / "Deficient"  (explicit requirement)
  - Green is never returned for >110 %
  - get_diet_summary: correct colour mapping from analysis dict
  - get_diet_summary: max 3 missing_micros, sorted by severity_score
  - get_diet_summary: guardrail fallbacks (no diet items, empty analysis)

All tests are pure Python - no DB, no network, no OpenAI.
"""

import os

os.environ.setdefault("APP_ENV", "test")

from app.services.dashboard.nutrition_service import (
    _diet_summary_threshold,
    get_diet_summary,
)

# ---------------------------------------------------------------------------
# _diet_summary_threshold - Calories
# ---------------------------------------------------------------------------


class TestDietSummaryThresholdCalories:
    def test_calories_at_100_pct_is_green(self):
        color, note = _diet_summary_threshold("Calories", 100.0)
        assert color == "green"
        assert note == "On track"

    def test_calories_below_100_pct_is_green(self):
        color, note = _diet_summary_threshold("Calories", 75.0)
        assert color == "green"

    def test_calories_above_100_pct_is_amber(self):
        color, note = _diet_summary_threshold("Calories", 100.1)
        assert color == "amber"
        assert note == "Slightly over target"

    def test_calories_well_over_is_amber_not_red(self):
        # Calories has no red zone - only green / amber
        color, _ = _diet_summary_threshold("Calories", 200.0)
        assert color == "amber"


# ---------------------------------------------------------------------------
# _diet_summary_threshold - Omega-3
# ---------------------------------------------------------------------------


class TestDietSummaryThresholdOmega3:
    def test_omega3_at_15_pct_is_red_critical(self):
        color, note = _diet_summary_threshold("Omega-3", 15.0)
        assert color == "red"
        assert note == "Deficient"

    def test_omega3_at_5_pct_is_red_critical(self):
        color, note = _diet_summary_threshold("Omega-3", 5.0)
        assert color == "red"
        assert note == "Deficient"

    def test_omega3_at_0_pct_is_red_critical(self):
        color, note = _diet_summary_threshold("Omega-3", 0.0)
        assert color == "red"
        assert note == "Deficient"

    def test_omega3_at_16_pct_is_red_deficient(self):
        color, note = _diet_summary_threshold("Omega-3", 16.0)
        assert color == "red"
        assert note == "Deficient"

    def test_omega3_at_79_pct_is_red(self):
        color, _ = _diet_summary_threshold("Omega-3", 79.0)
        assert color == "red"

    def test_omega3_at_80_pct_is_green(self):
        color, _ = _diet_summary_threshold("Omega-3", 80.0)
        assert color == "green"

    def test_omega3_at_100_pct_is_green(self):
        color, _ = _diet_summary_threshold("Omega-3", 100.0)
        assert color == "green"

    def test_omega3_at_110_pct_is_green(self):
        color, _ = _diet_summary_threshold("Omega-3", 110.0)
        assert color == "green"

    def test_omega3_above_110_pct_is_amber(self):
        """Green NOT used for >110 %."""
        color, note = _diet_summary_threshold("Omega-3", 111.0)
        assert color == "amber"
        assert note == "Slightly over"

    def test_omega3_at_200_pct_is_amber_not_green(self):
        color, _ = _diet_summary_threshold("Omega-3", 200.0)
        assert color == "amber"


# ---------------------------------------------------------------------------
# _diet_summary_threshold - Protein
# ---------------------------------------------------------------------------


class TestDietSummaryThresholdProtein:
    def test_protein_at_79_pct_is_red(self):
        color, note = _diet_summary_threshold("Protein", 79.0)
        assert color == "red"
        assert note == "Deficient"

    def test_protein_at_80_pct_is_green(self):
        color, _ = _diet_summary_threshold("Protein", 80.0)
        assert color == "green"

    def test_protein_at_100_pct_is_green(self):
        color, _ = _diet_summary_threshold("Protein", 100.0)
        assert color == "green"

    def test_protein_at_110_pct_is_green(self):
        color, _ = _diet_summary_threshold("Protein", 110.0)
        assert color == "green"

    def test_protein_above_110_pct_is_amber(self):
        """Green NOT used for >110 %."""
        color, note = _diet_summary_threshold("Protein", 110.1)
        assert color == "amber"
        assert note == "Slightly over"


# ---------------------------------------------------------------------------
# _diet_summary_threshold - Fat
# ---------------------------------------------------------------------------


class TestDietSummaryThresholdFat:
    def test_fat_at_79_pct_is_red(self):
        color, _ = _diet_summary_threshold("Fat", 79.0)
        assert color == "red"

    def test_fat_at_80_pct_is_green(self):
        color, _ = _diet_summary_threshold("Fat", 80.0)
        assert color == "green"

    def test_fat_above_110_pct_is_amber(self):
        color, _ = _diet_summary_threshold("Fat", 120.0)
        assert color == "amber"

    def test_fat_at_110_pct_is_green_not_amber(self):
        color, _ = _diet_summary_threshold("Fat", 110.0)
        assert color == "green"


# ---------------------------------------------------------------------------
# get_diet_summary - direct analysis input (synchronous formatter)
# ---------------------------------------------------------------------------


def _base_analysis() -> dict:
    """Return a realistic analyze_nutrition output for a healthy pet."""
    return {
        "calories_per_day": 1100,
        "has_diet_items": True,
        "calories": {"actual": 1100, "target": 1200, "status": "adequate"},
        "macros": [
            {"name": "Protein", "actual": 22.0, "target": 25.0},
            {"name": "Fat",     "actual": 14.5, "target": 14.0},
            {"name": "Carbs",   "actual": 45.0, "target": 50.0},
            {"name": "Fibre",   "actual": 4.0,  "target": 4.0},
        ],
        "micronutrient_gaps": [
            {"name": "omega_3", "status": "missing", "severity_score": 0.9},
            {"name": "vitamin_e", "status": "low", "severity_score": 0.6},
            {"name": "glucosamine", "status": "low", "severity_score": 0.4},
            {"name": "calcium", "status": "sufficient", "severity_score": 0.0},
            {"name": "phosphorus", "status": "sufficient", "severity_score": 0.0},
            {"name": "omega_6", "status": "sufficient", "severity_score": 0.0},
        ],
        "overall_label": "moderate",
        "recommendation": "Consider Omega-3 supplementation.",
        "diet_summary": "Current diet: Royal Canin.",
        "analysis_context": "Analysis based on Golden Retriever breed profile",
        "gap_count": 3,
    }


class TestGetDietSummary:
    """Tests for get_diet_summary - synchronous formatter from analysis dict."""

    # --- Macro structure ---

    def test_returns_five_macros(self):
        result = get_diet_summary(_base_analysis())
        assert len(result["macros"]) == 5

    def test_macro_names_are_correct(self):
        result = get_diet_summary(_base_analysis())
        names = [m["name"] for m in result["macros"]]
        assert names == ["Calories", "Protein", "Fat", "Carbs", "Fibre"]

    def test_macro_fields_present(self):
        result = get_diet_summary(_base_analysis())
        for macro in result["macros"]:
            assert "name" in macro
            assert "pct_of_need" in macro
            assert "color" in macro
            assert "note" in macro

    # --- Colour correctness ---

    def test_calories_under_target_is_green(self):
        """1100 kcal / 1200 target = ~91.7 % -> green."""
        result = get_diet_summary(_base_analysis())
        calories_macro = next(m for m in result["macros"] if m["name"] == "Calories")
        assert calories_macro["color"] == "green"

    def test_fibre_critical_deficiency_is_red(self):
        """Fibre actual=2, target=4 -> 50% -> RED 'Deficient'."""
        analysis = _base_analysis()
        for m in analysis["macros"]:
            if m["name"] == "Fibre":
                m["actual"] = 2.0
                m["target"] = 4.0
                break
        result = get_diet_summary(analysis)
        fibre_macro = next(m for m in result["macros"] if m["name"] == "Fibre")
        assert fibre_macro["color"] == "red"
        assert fibre_macro["note"] == "Deficient"
        assert fibre_macro["pct_of_need"] == 50.0

    def test_fat_slightly_over_is_amber(self):
        """fat actual=16, target=14 -> 114.3 % -> amber."""
        analysis = _base_analysis()
        for m in analysis["macros"]:
            if m["name"] == "Fat":
                m["actual"] = 16.0
                m["target"] = 14.0
                break
        result = get_diet_summary(analysis)
        fat_macro = next(m for m in result["macros"] if m["name"] == "Fat")
        assert fat_macro["color"] == "amber"

    def test_protein_deficient_is_red(self):
        """protein actual=18, target=25 -> 72 % -> red."""
        analysis = _base_analysis()
        for m in analysis["macros"]:
            if m["name"] == "Protein":
                m["actual"] = 18.0
                m["target"] = 25.0
                break
        result = get_diet_summary(analysis)
        protein_macro = next(m for m in result["macros"] if m["name"] == "Protein")
        assert protein_macro["color"] == "red"

    def test_no_green_for_over_110_pct(self):
        """All macros with >110 % must not return green."""
        analysis = _base_analysis()
        for m in analysis["macros"]:
            if m["name"] == "Protein":
                m["actual"] = 30.0
                m["target"] = 25.0    # 120 %
            if m["name"] == "Fat":
                m["actual"] = 20.0
                m["target"] = 14.0    # ~143 %
            if m["name"] == "Carbs":
                m["actual"] = 60.0
                m["target"] = 50.0    # 120 %
            if m["name"] == "Fibre":
                m["actual"] = 6.0
                m["target"] = 4.0     # 150 %
        analysis["calories"]["actual"] = 1500
        analysis["calories"]["target"] = 1200  # 125 %

        result = get_diet_summary(analysis)

        for macro in result["macros"]:
            assert macro["color"] != "green", (
                f"{macro['name']} at {macro['pct_of_need']}% returned green but should not"
            )

    # --- missing_micros ---

    def test_missing_micros_max_3(self):
        """Even if many nutrients are deficient, only 3 are returned."""
        result = get_diet_summary(_base_analysis())
        assert len(result["missing_micros"]) <= 3

    def test_missing_micros_sorted_by_severity(self):
        """Higher severity_score appears first."""
        result = get_diet_summary(_base_analysis())
        names = [m["name"] for m in result["missing_micros"]]
        # omega_3 (0.9) > vitamin_e (0.6) > glucosamine (0.4)
        assert names == ["omega_3", "vitamin_e", "glucosamine"]

    def test_missing_micro_fields_present(self):
        result = get_diet_summary(_base_analysis())
        for micro in result["missing_micros"]:
            assert "icon" in micro
            assert "name" in micro
            assert "reason" in micro

    def test_missing_micros_excludes_sufficient_nutrients(self):
        """Nutrients with status 'sufficient' must not appear."""
        result = get_diet_summary(_base_analysis())
        returned_names = {m["name"] for m in result["missing_micros"]}
        assert "calcium" not in returned_names
        assert "phosphorus" not in returned_names
        assert "omega_6" not in returned_names

    # --- Guardrail fallbacks ---

    def test_no_diet_items_returns_empty(self):
        """has_diet_items=False suppresses all results."""
        analysis = _base_analysis()
        analysis["has_diet_items"] = False
        result = get_diet_summary(analysis)
        assert result == {"macros": [], "missing_micros": []}

    def test_empty_analysis_returns_empty(self):
        """Empty dict (LLM could not analyse) returns empty."""
        result = get_diet_summary({})
        assert result == {"macros": [], "missing_micros": []}
