"""
Unit tests for onboarding validators (pure functions, no DB).

Tests: pet name, breed, weight, age, gender, phone validation.
"""

import pytest
from app.domain.onboarding.validators import (
    is_valid_pet_name,
    is_valid_breed,
    is_valid_weight_kg,
    is_valid_age,
    is_valid_gender,
    is_valid_neuter_spay_status,
    is_valid_phone,
    is_doc_skip_intent,
    is_yes_intent,
    is_no_intent,
    is_skip_intent,
)


class TestPetNameValidation:
    """Tests for pet name validation."""

    def test_valid_names(self):
        names = ["Buddy", "Max", "Bella", "A1", "Buddy's"]
        for name in names:
            valid, msg = is_valid_pet_name(name)
            assert valid is True, f"'{name}' should be valid"

    def test_empty_name(self):
        valid, msg = is_valid_pet_name("")
        assert valid is False
        assert "empty" in msg.lower()

    def test_name_too_short(self):
        valid, msg = is_valid_pet_name("A")
        assert valid is False
        assert "short" in msg.lower()

    def test_name_too_long(self):
        valid, msg = is_valid_pet_name("A" * 51)
        assert valid is False
        assert "long" in msg.lower()

    def test_name_with_invalid_chars(self):
        valid, msg = is_valid_pet_name("Buddy@#$")
        assert valid is False
        assert "invalid" in msg.lower()


class TestBreedValidation:
    """Tests for breed validation."""

    def test_valid_breeds(self):
        breeds = ["Labrador", "German Shepherd", "Pug", "Golden Retriever"]
        for breed in breeds:
            valid, msg = is_valid_breed(breed)
            assert valid is True

    def test_empty_breed(self):
        valid, msg = is_valid_breed("")
        assert valid is False

    def test_breed_too_long(self):
        valid, msg = is_valid_breed("A" * 101)
        assert valid is False


class TestWeightValidation:
    """Tests for weight validation."""

    def test_valid_weights(self):
        for weight in [5.0, 35.5, 75.0, 150.0]:
            valid, msg = is_valid_weight_kg(weight)
            assert valid is True

    def test_zero_weight(self):
        valid, msg = is_valid_weight_kg(0)
        assert valid is False

    def test_negative_weight(self):
        valid, msg = is_valid_weight_kg(-10)
        assert valid is False

    def test_weight_too_high(self):
        valid, msg = is_valid_weight_kg(151)
        assert valid is False
        assert "high" in msg.lower()

    def test_non_numeric_weight(self):
        valid, msg = is_valid_weight_kg("35kg")
        assert valid is False


class TestAgeValidation:
    """Tests for age validation."""

    def test_valid_ages(self):
        for age in [0.5, 1.0, 5.5, 15.0, 30.0]:
            valid, msg = is_valid_age(age)
            assert valid is True

    def test_negative_age(self):
        valid, msg = is_valid_age(-1)
        assert valid is False
        assert "negative" in msg.lower()

    def test_age_unreasonably_high(self):
        valid, msg = is_valid_age(31)
        assert valid is False
        assert "unreasonable" in msg.lower()

    def test_non_numeric_age(self):
        valid, msg = is_valid_age("5 years")
        assert valid is False


class TestGenderValidation:
    """Tests for gender validation."""

    def test_valid_genders(self):
        genders = ["male", "female", "other", "m", "f"]
        for gender in genders:
            valid, msg = is_valid_gender(gender)
            assert valid is True

    def test_invalid_gender(self):
        valid, msg = is_valid_gender("unknown")
        assert valid is False

    def test_case_insensitive(self):
        valid, msg = is_valid_gender("MALE")
        assert valid is True


class TestNeuterSpayValidation:
    """Tests for neuter/spay status validation."""

    def test_valid_statuses(self):
        statuses = ["yes", "no", "unknown"]
        for status in statuses:
            valid, msg = is_valid_neuter_spay_status(status)
            assert valid is True

    def test_invalid_status(self):
        valid, msg = is_valid_neuter_spay_status("maybe")
        assert valid is False


class TestPhoneValidation:
    """Tests for phone number validation."""

    def test_valid_phone(self):
        valid, msg = is_valid_phone("9876543210")
        assert valid is True

    def test_phone_with_spaces(self):
        valid, msg = is_valid_phone("98765 43210")
        assert valid is True  # Spaces are stripped

    def test_phone_with_dashes(self):
        valid, msg = is_valid_phone("9876-543210")
        assert valid is True  # Dashes are stripped

    def test_too_short(self):
        valid, msg = is_valid_phone("123456789")  # 9 digits
        assert valid is False
        assert "10 digits" in msg

    def test_too_long(self):
        valid, msg = is_valid_phone("98765432101")  # 11 digits
        assert valid is False

    def test_empty_phone(self):
        valid, msg = is_valid_phone("")
        assert valid is False


class TestIntentDetection:
    """Tests for intent detection (yes/no/skip)."""

    def test_yes_intent(self):
        yes_variants = ["yes", "yep", "yeah", "sure", "ok", "haan"]
        for text in yes_variants:
            assert is_yes_intent(text) is True

    def test_no_intent(self):
        no_variants = ["no", "nope", "nah", "nahi"]
        for text in no_variants:
            assert is_no_intent(text) is True

    def test_skip_intent(self):
        skip_variants = ["skip", "later"]
        for text in skip_variants:
            assert is_skip_intent(text) is True

    def test_case_insensitive_intent(self):
        assert is_yes_intent("YES") is True
        assert is_no_intent("NO") is True


class TestDocSkipIntent:
    """Tests for document skip intent detection."""

    def test_explicit_skip(self):
        assert is_doc_skip_intent("skip") is True

    def test_no_means_skip(self):
        assert is_doc_skip_intent("no") is True

    def test_skip_phrases(self):
        phrases = [
            "no documents",
            "no docs",
            "later",
            "what next",
        ]
        for phrase in phrases:
            assert is_doc_skip_intent(phrase) is True

    def test_upload_intent(self):
        # Should NOT skip if user says they're uploading
        assert is_doc_skip_intent("uploading now") is False

    def test_not_skip(self):
        assert is_doc_skip_intent("actually have documents") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

