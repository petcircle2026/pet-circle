"""Schemas â€” DTOs for API requests and responses."""

from app.schemas.requests import (
    # Onboarding
    CreatePetRequest,
    OnboardingStepRequest,
    # Orders
    AddToCartRequest,
    RemoveFromCartRequest,
    CheckoutRequest,
    # Reminders
    SnoozeReminderRequest,
    MarkReminderDoneRequest,
)
from app.schemas.responses import (
    # Onboarding
    OnboardingStepResponse,
    PetCreatedResponse,
    # Orders
    CartItemResponse,
    CartResponse,
    OrderResponse,
    # Reminders
    ReminderResponse,
    RemindersListResponse,
)

__all__ = [
    # Requests
    "CreatePetRequest",
    "OnboardingStepRequest",
    "AddToCartRequest",
    "RemoveFromCartRequest",
    "CheckoutRequest",
    "SnoozeReminderRequest",
    "MarkReminderDoneRequest",
    # Responses
    "OnboardingStepResponse",
    "PetCreatedResponse",
    "CartItemResponse",
    "CartResponse",
    "OrderResponse",
    "ReminderResponse",
    "RemindersListResponse",
]

