"""
Onboarding State Machine

Pure state transition logic for the onboarding flow.
Defines valid states, transitions, and prompts.

States (in order):
    1. awaiting_pet_name - Ask for pet name
    2. awaiting_breed_age - Ask for breed + age
    3. awaiting_gender_weight - Ask for gender + weight
    4. awaiting_neuter_spay - Ask if neutered/spayed
    5. awaiting_food_type - Ask for food type
    6. awaiting_meal_details - Ask for meal frequency/amount
    7. awaiting_supplements - Ask for supplements
    8. awaiting_preventive - Ask for preventive care
    9. awaiting_prev_retry - (optional) Re-ask preventive if unclear
    10. awaiting_documents - Ask for medical documents or skip
    11. complete - Onboarding done
"""

from enum import Enum
from typing import NamedTuple


class OnboardingState(str, Enum):
    """Valid onboarding states."""

    PENDING = "pending"  # Initial state, no interaction yet
    AWAITING_PET_NAME = "awaiting_pet_name"
    AWAITING_BREED_AGE = "awaiting_breed_age"
    AWAITING_GENDER_WEIGHT = "awaiting_gender_weight"
    AWAITING_NEUTER_SPAY = "awaiting_neuter_spay"
    AWAITING_FOOD_TYPE = "awaiting_food_type"
    AWAITING_MEAL_DETAILS = "awaiting_meal_details"
    AWAITING_SUPPLEMENTS = "awaiting_supplements"
    AWAITING_PREVENTIVE = "awaiting_preventive"
    AWAITING_PREV_RETRY = "awaiting_prev_retry"  # Re-ask if parsing failed
    AWAITING_DOCUMENTS = "awaiting_documents"
    COMPLETE = "complete"


class StateTransition(NamedTuple):
    """Defines a valid state transition."""

    from_state: OnboardingState
    to_state: OnboardingState
    description: str


# Valid transitions (directed graph of state machine)
VALID_TRANSITIONS = [
    StateTransition(OnboardingState.PENDING, OnboardingState.AWAITING_PET_NAME, "Start onboarding"),
    StateTransition(OnboardingState.AWAITING_PET_NAME, OnboardingState.AWAITING_BREED_AGE, "Pet name received"),
    StateTransition(OnboardingState.AWAITING_BREED_AGE, OnboardingState.AWAITING_GENDER_WEIGHT, "Breed and age received"),
    StateTransition(OnboardingState.AWAITING_GENDER_WEIGHT, OnboardingState.AWAITING_NEUTER_SPAY, "Gender and weight received"),
    StateTransition(OnboardingState.AWAITING_NEUTER_SPAY, OnboardingState.AWAITING_FOOD_TYPE, "Neuter/spay status received"),
    StateTransition(OnboardingState.AWAITING_FOOD_TYPE, OnboardingState.AWAITING_MEAL_DETAILS, "Food type received"),
    StateTransition(OnboardingState.AWAITING_MEAL_DETAILS, OnboardingState.AWAITING_SUPPLEMENTS, "Meal details received"),
    StateTransition(OnboardingState.AWAITING_SUPPLEMENTS, OnboardingState.AWAITING_PREVENTIVE, "Supplements received"),
    StateTransition(OnboardingState.AWAITING_PREVENTIVE, OnboardingState.AWAITING_DOCUMENTS, "Preventive info received"),
    StateTransition(OnboardingState.AWAITING_PREVENTIVE, OnboardingState.AWAITING_PREV_RETRY, "Preventive unclear, retry"),
    StateTransition(OnboardingState.AWAITING_PREV_RETRY, OnboardingState.AWAITING_DOCUMENTS, "Preventive retry received"),
    StateTransition(OnboardingState.AWAITING_DOCUMENTS, OnboardingState.COMPLETE, "Documents uploaded or skipped"),
]


class OnboardingStateMachine:
    """
    Manages onboarding state transitions.

    Pure logic â€” no database access, fully testable.
    """

    def __init__(self):
        self.transitions = {t.from_state: t for t in VALID_TRANSITIONS}

    def get_next_state(self, current_state: str | OnboardingState) -> OnboardingState | None:
        """
        Get the next state after current state.

        Returns None if current state is terminal or invalid.
        """
        if isinstance(current_state, str):
            try:
                current_state = OnboardingState(current_state)
            except ValueError:
                return None

        if current_state == OnboardingState.COMPLETE:
            return None  # Terminal state

        if current_state not in self.transitions:
            return None

        transition = self.transitions[current_state]
        return transition.to_state

    def is_valid_transition(
        self, from_state: str | OnboardingState, to_state: str | OnboardingState
    ) -> bool:
        """Check if transition from -> to is valid."""
        if isinstance(from_state, str):
            try:
                from_state = OnboardingState(from_state)
            except ValueError:
                return False

        if isinstance(to_state, str):
            try:
                to_state = OnboardingState(to_state)
            except ValueError:
                return False

        for transition in VALID_TRANSITIONS:
            if transition.from_state == from_state and transition.to_state == to_state:
                return True

        return False

    def is_complete(self, state: str | OnboardingState) -> bool:
        """Check if onboarding is complete."""
        if isinstance(state, str):
            try:
                state = OnboardingState(state)
            except ValueError:
                return False

        return state == OnboardingState.COMPLETE

    def get_prompt_for_state(self, state: str | OnboardingState) -> str:
        """Get the question/prompt for a given state."""
        if isinstance(state, str):
            try:
                state = OnboardingState(state)
            except ValueError:
                return "Invalid state"

        prompts = {
            OnboardingState.PENDING: "Starting onboarding...",
            OnboardingState.AWAITING_PET_NAME: "What's your pet's name?",
            OnboardingState.AWAITING_BREED_AGE: "What breed is your pet, and how old? (e.g., 'Golden Retriever, 3 years')",
            OnboardingState.AWAITING_GENDER_WEIGHT: "What's the gender and weight? (e.g., 'Male, 25 kg')",
            OnboardingState.AWAITING_NEUTER_SPAY: "Is your pet neutered/spayed? (Yes/No)",
            OnboardingState.AWAITING_FOOD_TYPE: "What type of food? (e.g., 'Dry kibble', 'Wet food', 'Raw', 'Homemade')",
            OnboardingState.AWAITING_MEAL_DETAILS: "How many meals per day, and how much per meal?",
            OnboardingState.AWAITING_SUPPLEMENTS: "Any supplements or additional foods? (or 'None')",
            OnboardingState.AWAITING_PREVENTIVE: "Does your pet have vaccines, deworming, or flea/tick prevention? (or 'None')",
            OnboardingState.AWAITING_PREV_RETRY: "Could you clarify the preventive care information?",
            OnboardingState.AWAITING_DOCUMENTS: "Upload medical records or vaccination certificates (or type 'Skip')",
            OnboardingState.COMPLETE: "Onboarding complete! Your pet's health profile is ready.",
        }

        return prompts.get(state, "Unknown state")

    def get_all_states(self) -> list[str]:
        """Get all valid state names."""
        return [state.value for state in OnboardingState]

    def get_progress_percentage(self, current_state: str | OnboardingState) -> int:
        """Get percentage progress through onboarding."""
        states_list = [
            OnboardingState.PENDING,
            OnboardingState.AWAITING_PET_NAME,
            OnboardingState.AWAITING_BREED_AGE,
            OnboardingState.AWAITING_GENDER_WEIGHT,
            OnboardingState.AWAITING_NEUTER_SPAY,
            OnboardingState.AWAITING_FOOD_TYPE,
            OnboardingState.AWAITING_MEAL_DETAILS,
            OnboardingState.AWAITING_SUPPLEMENTS,
            OnboardingState.AWAITING_PREVENTIVE,
            OnboardingState.AWAITING_DOCUMENTS,
            OnboardingState.COMPLETE,
        ]

        if isinstance(current_state, str):
            try:
                current_state = OnboardingState(current_state)
            except ValueError:
                return 0

        try:
            index = states_list.index(current_state)
            progress = int((index / len(states_list)) * 100)
            return min(progress, 100)
        except ValueError:
            return 0

