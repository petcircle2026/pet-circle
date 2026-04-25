"""Response DTOs — structured output for all API endpoints."""

from app.schemas.responses.onboarding import (
    OnboardingStepResponse,
    PetCreatedResponse,
)
from app.schemas.responses.orders import (
    CartItemResponse,
    CartResponse,
    OrderResponse,
)
from app.schemas.responses.reminders import (
    ReminderResponse,
    RemindersListResponse,
)

__all__ = [
    # Onboarding
    "OnboardingStepResponse",
    "PetCreatedResponse",
    # Orders
    "CartItemResponse",
    "CartResponse",
    "OrderResponse",
    # Reminders
    "ReminderResponse",
    "RemindersListResponse",
]
