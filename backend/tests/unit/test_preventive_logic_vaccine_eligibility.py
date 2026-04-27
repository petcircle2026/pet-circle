"""
Unit tests for vaccine eligibility logic in preventive_logic.

Tests: age-based filtering, puppy vaccines, adult vaccines, species handling.
"""

import pytest
from app.domain.health.preventive_logic import (
    is_vaccine_eligible_for_age,
    PUPPY_VACCINE_MIN_AGE_DAYS,
    PUPPY_AGE_CUTOFF_DAYS,
)


class TestPuppyVaccineEligibility:
    """Tests for puppy-specific vaccines."""

    def test_dhppi_1st_dose_at_minimum_age(self):
        """DHPPI 1st dose eligible at exactly 42 days (6 weeks)."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 42)
        assert result is True

    def test_dhppi_1st_dose_before_minimum_age(self):
        """DHPPI 1st dose not eligible before 42 days."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 41)
        assert result is False

    def test_dhppi_1st_dose_after_minimum_age(self):
        """DHPPI 1st dose eligible after 42 days."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 100)
        assert result is True

    def test_dhppi_2nd_dose_at_minimum_age(self):
        """DHPPI 2nd dose eligible at exactly 63 days (9 weeks)."""
        result = is_vaccine_eligible_for_age("dhppi 2nd dose", 63)
        assert result is True

    def test_dhppi_2nd_dose_before_minimum_age(self):
        """DHPPI 2nd dose not eligible before 63 days."""
        result = is_vaccine_eligible_for_age("dhppi 2nd dose", 62)
        assert result is False

    def test_dhppi_3rd_dose_at_minimum_age(self):
        """DHPPI 3rd dose eligible at exactly 84 days (12 weeks)."""
        result = is_vaccine_eligible_for_age("dhppi 3rd dose", 84)
        assert result is True

    def test_puppy_booster_at_minimum_age(self):
        """Puppy booster eligible at exactly 90 days (3 months)."""
        result = is_vaccine_eligible_for_age("puppy booster", 90)
        assert result is True

    def test_puppy_booster_before_minimum_age(self):
        """Puppy booster not eligible before 90 days."""
        result = is_vaccine_eligible_for_age("puppy booster", 89)
        assert result is False


class TestAdultPuppyVaccineHiding:
    """Tests for hiding puppy vaccines from adult dogs."""

    def test_puppy_vaccine_hidden_at_cutoff_age(self):
        """Puppy vaccines hidden at exactly 365 days (1 year)."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 365)
        assert result is False

    def test_puppy_vaccine_hidden_after_cutoff_age(self):
        """Puppy vaccines hidden after 365 days."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 366)
        assert result is False

    def test_puppy_vaccine_hidden_well_after_cutoff(self):
        """Puppy vaccines hidden for old dogs."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 1000)
        assert result is False

    def test_puppy_booster_hidden_for_adults(self):
        """Puppy booster hidden for adult dogs."""
        result = is_vaccine_eligible_for_age("puppy booster", 365)
        assert result is False

    def test_puppy_vaccines_hidden_near_cutoff(self):
        """All puppy vaccines hidden at 365 days."""
        for vaccine in ["dhppi 1st dose", "dhppi 2nd dose", "dhppi 3rd dose", "puppy booster"]:
            result = is_vaccine_eligible_for_age(vaccine, 365)
            assert result is False, f"{vaccine} should be hidden at 365 days"


class TestPuppyAgeTransition:
    """Tests around the 365-day boundary (when puppies become adults)."""

    def test_one_day_before_cutoff(self):
        """Puppy vaccines still shown at 364 days (not yet 1 year)."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 364)
        assert result is True

    def test_exactly_at_cutoff(self):
        """Puppy vaccines hidden at exactly 365 days."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 365)
        assert result is False

    def test_one_day_after_cutoff(self):
        """Puppy vaccines hidden at 366 days."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 366)
        assert result is False


class TestFelinesVaccines:
    """Tests for feline-specific vaccines."""

    def test_feline_core_1st_dose_at_minimum_age(self):
        """Feline core 1st dose eligible at 42 days."""
        result = is_vaccine_eligible_for_age("feline core 1st dose", 42, species="cat")
        assert result is True

    def test_feline_core_2nd_dose_at_minimum_age(self):
        """Feline core 2nd dose eligible at 63 days."""
        result = is_vaccine_eligible_for_age("feline core 2nd dose", 63, species="cat")
        assert result is True

    def test_feline_core_3rd_dose_at_minimum_age(self):
        """Feline core 3rd dose eligible at 84 days."""
        result = is_vaccine_eligible_for_age("feline core 3rd dose", 84, species="cat")
        assert result is True

    def test_feline_vaccine_hidden_after_cutoff(self):
        """Feline vaccines hidden for adult cats (>= 365 days)."""
        result = is_vaccine_eligible_for_age("feline core 1st dose", 365, species="cat")
        assert result is False


class TestNonPuppyVaccines:
    """Tests for non-puppy-specific vaccines (should always show for valid ages)."""

    def test_rabies_vaccine_always_eligible(self):
        """Rabies vaccine not in puppy list: always eligible."""
        result = is_vaccine_eligible_for_age("rabies", 50, species="dog")
        assert result is True

    def test_rabies_vaccine_for_adult(self):
        """Rabies vaccine eligible for adults."""
        result = is_vaccine_eligible_for_age("rabies", 1000, species="dog")
        assert result is True

    def test_unknown_vaccine_always_eligible(self):
        """Unknown vaccine name: always eligible."""
        result = is_vaccine_eligible_for_age("unknown vaccine xyz", 100, species="dog")
        assert result is True

    def test_empty_vaccine_name_eligible(self):
        """Empty vaccine name treated as unknown: eligible."""
        result = is_vaccine_eligible_for_age("", 100, species="dog")
        assert result is True


class TestSpeciesHandling:
    """Tests for species-specific behavior."""

    def test_dog_species_applies_filtering(self):
        """Dogs apply age filtering."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 41, species="dog")
        assert result is False

    def test_cat_species_applies_filtering(self):
        """Cats apply age filtering."""
        result = is_vaccine_eligible_for_age("feline core 1st dose", 41, species="cat")
        assert result is False

    def test_dog_lowercase_applies_filtering(self):
        """Lowercase 'dog' applies filtering."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 41, species="dog")
        assert result is False

    def test_cat_lowercase_applies_filtering(self):
        """Lowercase 'cat' applies filtering."""
        result = is_vaccine_eligible_for_age("feline core 1st dose", 41, species="cat")
        assert result is False

    def test_dog_uppercase_applies_filtering(self):
        """Uppercase 'DOG' applies filtering."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 41, species="DOG")
        assert result is False

    def test_other_species_no_filtering(self):
        """Non-dog/cat species: no age filtering."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 41, species="rabbit")
        assert result is True

    def test_bird_species_no_filtering(self):
        """Bird species: no age filtering."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 10, species="bird")
        assert result is True


class TestNoneAndNullHandling:
    """Tests for None and null values."""

    def test_none_age_returns_true(self):
        """None age should return True (show vaccine, age unknown)."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", None)
        assert result is True

    def test_none_vaccine_name_returns_true(self):
        """None vaccine name should return True."""
        result = is_vaccine_eligible_for_age(None, 50)
        assert result is True

    def test_none_vaccine_and_none_age_returns_true(self):
        """Both None should return True."""
        result = is_vaccine_eligible_for_age(None, None)
        assert result is True

    def test_empty_vaccine_name_returns_true(self):
        """Empty vaccine name should return True."""
        result = is_vaccine_eligible_for_age("", 50)
        assert result is True


class TestCaseSensitivity:
    """Tests for vaccine name case sensitivity."""

    def test_vaccine_name_uppercase(self):
        """Uppercase vaccine name should work."""
        result = is_vaccine_eligible_for_age("DHPPI 1ST DOSE", 42)
        assert result is True

    def test_vaccine_name_mixed_case(self):
        """Mixed case vaccine name should work."""
        result = is_vaccine_eligible_for_age("DHPPI 1st Dose", 42)
        assert result is True

    def test_vaccine_name_lowercase(self):
        """Lowercase vaccine name should work."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 42)
        assert result is True


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_age_zero(self):
        """Age 0 (newborn): only vaccines with min_age <= 0 shown."""
        # Only vaccines with min_age > 0 should be hidden
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 0)
        assert result is False  # dhppi requires 42 days

    def test_age_one(self):
        """Age 1 day: no vaccines with min_age >= 1 shown."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 1)
        assert result is False

    def test_very_old_age(self):
        """Very old age: no puppy vaccines shown."""
        result = is_vaccine_eligible_for_age("dhppi 1st dose", 10000)
        assert result is False

    def test_negative_age_treated_as_unknown(self):
        """Negative age: treated as valid number, not None."""
        # This is technically valid Python, negative ages don't make sense
        # but the function should handle gracefully
        result = is_vaccine_eligible_for_age("dhppi 1st dose", -10)
        # Negative age < all min ages, so False
        assert result is False


class TestPentavalentVaccines:
    """Tests for pentavalent vaccines (alternative to DHPPI)."""

    def test_pentavalent_1st_dose_at_minimum_age(self):
        """Pentavalent 1st dose eligible at 42 days."""
        result = is_vaccine_eligible_for_age("pentavalent 1st dose", 42)
        assert result is True

    def test_pentavalent_1st_dose_before_minimum_age(self):
        """Pentavalent 1st dose not eligible before 42 days."""
        result = is_vaccine_eligible_for_age("pentavalent 1st dose", 41)
        assert result is False

    def test_pentavalent_2nd_dose_at_minimum_age(self):
        """Pentavalent 2nd dose eligible at 63 days."""
        result = is_vaccine_eligible_for_age("pentavalent 2nd dose", 63)
        assert result is True

    def test_pentavalent_3rd_dose_at_minimum_age(self):
        """Pentavalent 3rd dose eligible at 84 days."""
        result = is_vaccine_eligible_for_age("pentavalent 3rd dose", 84)
        assert result is True

    def test_pentavalent_hidden_for_adults(self):
        """Pentavalent vaccines hidden for adult dogs (>= 365 days)."""
        result = is_vaccine_eligible_for_age("pentavalent 1st dose", 365)
        assert result is False


class TestConstantValues:
    """Tests for constant values used in eligibility logic."""

    def test_puppy_age_cutoff_is_365(self):
        """Puppy age cutoff should be 365 days."""
        assert PUPPY_AGE_CUTOFF_DAYS == 365

    def test_puppy_vaccine_min_ages_defined(self):
        """Puppy vaccine minimum ages should be defined."""
        assert len(PUPPY_VACCINE_MIN_AGE_DAYS) > 0

    def test_dhppi_1st_dose_min_age_is_42(self):
        """DHPPI 1st dose minimum age should be 42 days."""
        assert PUPPY_VACCINE_MIN_AGE_DAYS["dhppi 1st dose"] == 42

    def test_dhppi_2nd_dose_min_age_is_63(self):
        """DHPPI 2nd dose minimum age should be 63 days."""
        assert PUPPY_VACCINE_MIN_AGE_DAYS["dhppi 2nd dose"] == 63

    def test_dhppi_3rd_dose_min_age_is_84(self):
        """DHPPI 3rd dose minimum age should be 84 days."""
        assert PUPPY_VACCINE_MIN_AGE_DAYS["dhppi 3rd dose"] == 84

    def test_puppy_booster_min_age_is_90(self):
        """Puppy booster minimum age should be 90 days."""
        assert PUPPY_VACCINE_MIN_AGE_DAYS["puppy booster"] == 90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
