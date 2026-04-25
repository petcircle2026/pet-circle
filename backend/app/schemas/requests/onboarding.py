"""Onboarding request DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class CreatePetRequest(BaseModel):
    """Request to create a new pet during onboarding."""

    pet_name: str = Field(..., min_length=2, max_length=50, description="Pet name")
    species: Optional[str] = Field(None, description="dog | cat | rabbit | bird | etc.")
    breed: Optional[str] = Field(None, max_length=100, description="Pet breed")
    age_years: Optional[float] = Field(None, ge=0, le=30, description="Age in years")
    dob: Optional[str] = Field(None, description="ISO date (YYYY-MM-DD) if known")
    gender: Optional[str] = Field(None, description="male | female | other")
    weight_kg: Optional[float] = Field(None, gt=0, le=150, description="Weight in kg")
    neutered_spayed: Optional[str] = Field(None, description="yes | no | unknown")

    class Config:
        json_schema_extra = {
            "example": {
                "pet_name": "Buddy",
                "species": "dog",
                "breed": "Labrador Retriever",
                "age_years": 2.5,
                "gender": "male",
                "weight_kg": 35.0,
                "neutered_spayed": "yes",
            }
        }


class OnboardingStepRequest(BaseModel):
    """Request to process one onboarding step."""

    user_id: str = Field(..., description="User ID")
    pet_id: Optional[str] = Field(None, description="Pet ID (if updating existing pet)")
    text: str = Field(..., min_length=1, max_length=2000, description="User reply text")
    button_payload: Optional[str] = Field(None, description="Button payload if reply is from button")
    message_metadata: Optional[dict] = Field(None, description="Additional WhatsApp message metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "text": "Buddy, Labrador, 2 years",
            }
        }
