"""Reminders response DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class ReminderResponse(BaseModel):
    """Response containing a single reminder."""

    reminder_id: str = Field(..., description="Reminder ID")
    pet_id: str = Field(..., description="Pet ID")
    category: str = Field(..., description="vaccine | deworming | flea_tick | food | etc.")
    item_description: str = Field(..., description="Human-readable description (e.g., 'Rabies vaccine')")
    due_date: str = Field(..., description="ISO date when due")
    stage: str = Field(..., description="t7 | due | d3 | overdue")
    days_until_due: int = Field(..., description="Days until/past due (negative if overdue)")
    snooze_until: Optional[str] = Field(None, description="ISO date if snoozed")
    status: str = Field(..., description="pending | completed | ignored")
    sent_at: Optional[str] = Field(None, description="ISO datetime when reminder was sent")

    class Config:
        json_schema_extra = {
            "example": {
                "reminder_id": "123e4567-e89b-12d3-a456-426614174000",
                "pet_id": "456f7890-a1b2-34d5-b678-901234567890",
                "category": "vaccine",
                "item_description": "Rabies vaccine booster",
                "due_date": "2026-04-20",
                "stage": "t7",
                "days_until_due": 7,
                "snooze_until": None,
                "status": "pending",
                "sent_at": "2026-04-13T08:00:00Z",
            }
        }


class RemindersListResponse(BaseModel):
    """Response containing list of reminders."""

    pet_id: str = Field(..., description="Pet ID")
    total_count: int = Field(..., description="Total reminders for this pet")
    pending_count: int = Field(..., description="Number of pending reminders")
    completed_count: int = Field(..., description="Number of completed reminders")
    reminders: list[ReminderResponse] = Field(..., description="List of reminders")

    class Config:
        json_schema_extra = {
            "example": {
                "pet_id": "456f7890-a1b2-34d5-b678-901234567890",
                "total_count": 3,
                "pending_count": 2,
                "completed_count": 1,
                "reminders": [
                    {
                        "reminder_id": "123e4567-e89b-12d3-a456-426614174000",
                        "pet_id": "456f7890-a1b2-34d5-b678-901234567890",
                        "category": "vaccine",
                        "item_description": "Rabies vaccine booster",
                        "due_date": "2026-04-20",
                        "stage": "t7",
                        "days_until_due": 7,
                        "snooze_until": None,
                        "status": "pending",
                        "sent_at": "2026-04-13T08:00:00Z",
                    },
                    {
                        "reminder_id": "234f5678-b6cd-78e9-f012-345678901234",
                        "pet_id": "456f7890-a1b2-34d5-b678-901234567890",
                        "category": "deworming",
                        "item_description": "Deworming tablet",
                        "due_date": "2026-05-01",
                        "stage": "pending",
                        "days_until_due": 18,
                        "snooze_until": None,
                        "status": "pending",
                        "sent_at": None,
                    },
                ],
            }
        }

