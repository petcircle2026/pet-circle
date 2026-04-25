"""Reminders request DTOs."""

from pydantic import BaseModel, Field


class SnoozeReminderRequest(BaseModel):
    """Request to snooze a reminder."""

    reminder_id: str = Field(..., description="Reminder ID")
    days: int = Field(..., ge=1, le=90, description="Number of days to snooze")

    class Config:
        json_schema_extra = {
            "example": {
                "reminder_id": "123e4567-e89b-12d3-a456-426614174000",
                "days": 7,
            }
        }


class MarkReminderDoneRequest(BaseModel):
    """Request to mark a reminder as completed."""

    reminder_id: str = Field(..., description="Reminder ID")
    completion_date: str = Field(..., description="ISO date (YYYY-MM-DD) when completed")

    class Config:
        json_schema_extra = {
            "example": {
                "reminder_id": "123e4567-e89b-12d3-a456-426614174000",
                "completion_date": "2026-04-25",
            }
        }
