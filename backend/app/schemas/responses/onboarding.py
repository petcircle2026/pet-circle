"""Onboarding response DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class OnboardingStepResponse(BaseModel):
    """Response after processing one onboarding step."""

    success: bool = Field(..., description="Whether step was processed successfully")
    next_state: str = Field(..., description="Next onboarding state (e.g., awaiting_breed_age)")
    is_complete: bool = Field(..., description="Whether onboarding is fully complete")
    message_to_send: Optional[str] = Field(None, description="Message to send to user")
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "next_state": "awaiting_breed_age",
                "is_complete": False,
                "message_to_send": "What breed is Buddy? And how old?",
                "error": None,
            }
        }


class PetCreatedResponse(BaseModel):
    """Response after creating a pet."""

    pet_id: str = Field(..., description="Newly created pet ID")
    pet_name: str = Field(..., description="Pet name")
    species: Optional[str] = Field(None, description="Species (dog, cat, etc.)")
    breed: Optional[str] = Field(None, description="Breed")
    onboarding_complete: bool = Field(..., description="Whether pet onboarding is complete")

    class Config:
        json_schema_extra = {
            "example": {
                "pet_id": "123e4567-e89b-12d3-a456-426614174000",
                "pet_name": "Buddy",
                "species": "dog",
                "breed": "Labrador Retriever",
                "onboarding_complete": False,
            }
        }
