"""Request DTOs â€” structured input validation for all API endpoints."""

from app.schemas.requests.onboarding import (
    CreatePetRequest,
    OnboardingStepRequest,
)
from app.schemas.requests.orders import (
    AddToCartRequest,
    RemoveFromCartRequest,
    CheckoutRequest,
)
from app.schemas.requests.reminders import (
    SnoozeReminderRequest,
    MarkReminderDoneRequest,
)

__all__ = [
    # Onboarding
    "CreatePetRequest",
    "OnboardingStepRequest",
    # Orders
    "AddToCartRequest",
    "RemoveFromCartRequest",
    "CheckoutRequest",
    # Reminders
    "SnoozeReminderRequest",
    "MarkReminderDoneRequest",
]

