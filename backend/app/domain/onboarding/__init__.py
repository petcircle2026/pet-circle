"""Onboarding domain â€” state machine, validators, parsers, orchestrator."""

from app.domain.onboarding.state_machine import (
    OnboardingState,
    OnboardingStateMachine,
    StateTransition,
    VALID_TRANSITIONS,
)
from app.domain.onboarding.validators import (
    is_yes_intent,
    is_no_intent,
    is_skip_intent,
    is_generic_vaccine_mention,
    is_flea_without_brand,
    is_pending_vaccine_intent,
    looks_like_vaccine_selection,
    is_valid_pet_name,
    is_valid_breed,
    is_valid_weight_kg,
    is_valid_age,
    is_valid_gender,
    is_valid_neuter_spay_status,
    is_valid_phone,
    is_doc_skip_intent,
)
from app.domain.onboarding.parsers import (
    strip_json_fences,
    parse_breed_age,
    parse_gender_weight,
    parse_gender_weight_neutered,
    ai_decide_neuter_question,
)
from app.domain.onboarding.onboarding_service import OnboardingService

__all__ = [
    # State machine
    "OnboardingState",
    "OnboardingStateMachine",
    "StateTransition",
    "VALID_TRANSITIONS",
    # Validators
    "is_yes_intent",
    "is_no_intent",
    "is_skip_intent",
    "is_generic_vaccine_mention",
    "is_flea_without_brand",
    "is_pending_vaccine_intent",
    "looks_like_vaccine_selection",
    "is_valid_pet_name",
    "is_valid_breed",
    "is_valid_weight_kg",
    "is_valid_age",
    "is_valid_gender",
    "is_valid_neuter_spay_status",
    "is_valid_phone",
    "is_doc_skip_intent",
    # Parsers
    "strip_json_fences",
    "parse_breed_age",
    "parse_gender_weight",
    "parse_gender_weight_neutered",
    "ai_decide_neuter_question",
    # Service
    "OnboardingService",
]

