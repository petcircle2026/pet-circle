"""
PetCircle — Reminder Config Loader

Reads reminder engine configuration from the reminder_config DB table.
Falls back to the hardcoded constants in app.core.constants and
app.services.admin.reminder_templates when the DB row is absent or
the value cannot be parsed. This means the engine continues working
correctly even before migration 024 is applied.

Usage:
    from app.services.admin.reminder_config_loader import ReminderConfigLoader

    loader = ReminderConfigLoader(db)
    cfg = loader.load()
    snooze = cfg.snooze_days("vaccine")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import time

from sqlalchemy.orm import Session

from app.core.constants import (
    REMINDER_IGNORE_THRESHOLD,
    REMINDER_MIN_GAP_DAYS,
    REMINDER_MONTHLY_INTERVAL_DAYS,
    SNOOZE_DAYS_DEWORMING,
    SNOOZE_DAYS_FLEA,
    SNOOZE_DAYS_FOOD,
    SNOOZE_DAYS_HYGIENE,
    SNOOZE_DAYS_MEDICINE,
    SNOOZE_DAYS_SUPPLEMENT,
    SNOOZE_DAYS_VACCINE,
    SNOOZE_DAYS_VET_FOLLOWUP,
    STAGE_D3,
    STAGE_DUE,
    STAGE_OVERDUE,
    STAGE_T7,
)
from app.services.admin.reminder_templates import (
    HYGIENE_DUE_SEND_TIME,
    MAX_REMINDERS_PER_PET_PER_DAY,
    MIN_DAYS_BETWEEN_SAME_ITEM_REMINDERS,
    STANDARD_STAGE_SEND_TIMES,
)

logger = logging.getLogger(__name__)

_SNOOZE_DEFAULTS: dict[str, int] = {
    "vaccine": SNOOZE_DAYS_VACCINE,
    "deworming": SNOOZE_DAYS_DEWORMING,
    "flea": SNOOZE_DAYS_FLEA,
    "food": SNOOZE_DAYS_FOOD,
    "supplement": SNOOZE_DAYS_SUPPLEMENT,
    "medicine": SNOOZE_DAYS_MEDICINE,
    "vet_followup": SNOOZE_DAYS_VET_FOLLOWUP,
    "hygiene": SNOOZE_DAYS_HYGIENE,
}

_SEND_TIME_DEFAULTS: dict[str, time] = {
    "t7": STANDARD_STAGE_SEND_TIMES[STAGE_T7],
    "due": STANDARD_STAGE_SEND_TIMES[STAGE_DUE],
    "d3": STANDARD_STAGE_SEND_TIMES[STAGE_D3],
    "overdue": STANDARD_STAGE_SEND_TIMES[STAGE_OVERDUE],
    "hygiene_due": HYGIENE_DUE_SEND_TIME,
}


@dataclass
class ReminderSettings:
    """Resolved reminder engine settings."""

    snooze_days: dict[str, int] = field(default_factory=dict)
    max_reminders_per_pet_per_day: int = MAX_REMINDERS_PER_PET_PER_DAY
    min_days_between_same_item: int = MIN_DAYS_BETWEEN_SAME_ITEM_REMINDERS
    ignore_threshold: int = REMINDER_IGNORE_THRESHOLD
    monthly_interval_days: int = REMINDER_MONTHLY_INTERVAL_DAYS
    min_gap_days: int = REMINDER_MIN_GAP_DAYS
    send_times: dict[str, time] = field(default_factory=dict)

    def snooze_for(self, category: str) -> int:
        """Return snooze days for a category, falling back to the vaccine default."""
        return self.snooze_days.get(category, self.snooze_days.get("vaccine", 7))

    def send_time_for(self, category: str, stage: str) -> time:
        """Resolve send time, with special-case for hygiene/due."""
        if category == "hygiene" and stage == STAGE_DUE:
            return self.send_times.get("hygiene_due", _SEND_TIME_DEFAULTS["hygiene_due"])
        key = stage.replace("overdue_insight", "overdue")
        return self.send_times.get(key, _SEND_TIME_DEFAULTS.get(key, _SEND_TIME_DEFAULTS["due"]))


class ReminderConfigLoader:
    """Loads ReminderSettings from the DB, falling back to constants."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def load(self) -> ReminderSettings:
        rows = self._fetch_all()
        settings = ReminderSettings(
            snooze_days=dict(_SNOOZE_DEFAULTS),
            send_times=dict(_SEND_TIME_DEFAULTS),
        )
        for key, value in rows.items():
            self._apply(settings, key, value)
        return settings

    def _fetch_all(self) -> dict[str, str]:
        try:
            from app.models.lookup.reminder_config import ReminderConfig
            rows = self._db.query(ReminderConfig).all()
            return {r.key: r.value for r in rows}
        except Exception:
            logger.warning("reminder_config table not available — using constant defaults")
            return {}

    @staticmethod
    def _apply(settings: ReminderSettings, key: str, raw: str) -> None:
        try:
            if key.startswith("snooze_days_"):
                category = key[len("snooze_days_"):]
                settings.snooze_days[category] = int(raw)
            elif key == "max_reminders_per_pet_per_day":
                settings.max_reminders_per_pet_per_day = int(raw)
            elif key == "min_days_between_same_item_reminders":
                settings.min_days_between_same_item = int(raw)
            elif key == "reminder_ignore_threshold":
                settings.ignore_threshold = int(raw)
            elif key == "reminder_monthly_interval_days":
                settings.monthly_interval_days = int(raw)
            elif key == "reminder_min_gap_days":
                settings.min_gap_days = int(raw)
            elif key.startswith("send_time_"):
                slot = key[len("send_time_"):]
                h, m = (int(x) for x in raw.split(":"))
                settings.send_times[slot] = time(hour=h, minute=m)
        except (ValueError, AttributeError) as exc:
            logger.warning("reminder_config: cannot parse key=%s value=%r — %s", key, raw, exc)
