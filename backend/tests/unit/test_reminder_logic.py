"""
Unit tests for reminder_logic (pure functions, no DB).

Tests: stage determination, snooze calculation, category classification.
"""

import pytest
from datetime import date, timedelta
from app.domain.reminders.reminder_logic import (
    ReminderStage,
    determine_reminder_stage,
    get_snooze_days,
    calculate_snooze_until,
    is_valid_category,
    classify_item_category,
    should_batch_reminders,
)


class TestReminderStage:
    """Tests for 4-stage reminder lifecycle."""

    def test_t7_stage(self):
        """7 days before due date = T-7 stage."""
        due = date(2026, 4, 20)
        today = date(2026, 4, 13)
        stage = determine_reminder_stage(due, today)

        assert stage.stage == "t7"
        assert stage.days_until_due == 7
        assert stage.send_now is True

    def test_due_stage(self):
        """On due date = Due stage."""
        due = date(2026, 4, 20)
        today = date(2026, 4, 20)
        stage = determine_reminder_stage(due, today)

        assert stage.stage == "due"
        assert stage.days_until_due == 0
        assert stage.send_now is True

    def test_d3_stage_one_day_late(self):
        """1 day after due = D+3 stage (check-in)."""
        due = date(2026, 4, 20)
        today = date(2026, 4, 21)
        stage = determine_reminder_stage(due, today)

        assert stage.stage == "d3"
        assert stage.days_until_due == -1
        assert stage.send_now is True

    def test_d3_stage_six_days_late(self):
        """6 days after due = D+3 stage (still check-in)."""
        due = date(2026, 4, 20)
        today = date(2026, 4, 26)
        stage = determine_reminder_stage(due, today)

        assert stage.stage == "d3"
        assert stage.days_until_due == -6
        assert stage.send_now is True

    def test_overdue_stage(self):
        """7+ days after due = Overdue stage."""
        due = date(2026, 4, 20)
        today = date(2026, 4, 27)
        stage = determine_reminder_stage(due, today)

        assert stage.stage == "overdue"
        assert stage.days_until_due == -7
        assert stage.send_now is True

    def test_pending_not_yet_t7(self):
        """8+ days before due = Pending (not yet T-7)."""
        due = date(2026, 4, 20)
        today = date(2026, 4, 11)
        stage = determine_reminder_stage(due, today)

        assert stage.stage == "pending"
        assert stage.days_until_due == 9
        assert stage.send_now is False

    def test_pending_between_d3_and_overdue(self):
        """Between D+3 and Overdue = Pending."""
        due = date(2026, 4, 20)
        # 6 days after due
        today = date(2026, 4, 26)
        stage = determine_reminder_stage(due, today)
        assert stage.send_now is True  # Still D+3

        # 7 days after due
        today = date(2026, 4, 27)
        stage = determine_reminder_stage(due, today)
        assert stage.stage == "overdue"
        assert stage.send_now is True


class TestSnoozeCalculation:
    """Tests for snooze duration and calculation."""

    def test_default_snooze_days(self):
        """Default snooze is 7 days."""
        days = get_snooze_days("vaccine")
        assert days == 7

    def test_food_snooze_is_3_days(self):
        """Food reminders snooze for 3 days."""
        days = get_snooze_days("food")
        assert days == 3

    def test_hygiene_snooze_is_30_days(self):
        """Hygiene reminders snooze for 30 days."""
        days = get_snooze_days("hygiene")
        assert days == 30

    def test_unknown_category_defaults_to_7(self):
        """Unknown category defaults to 7 days."""
        days = get_snooze_days("unknown_category")
        assert days == 7

    def test_calculate_snooze_until(self):
        """Calculate snooze-until date correctly."""
        today = date(2026, 4, 25)
        snooze_until = calculate_snooze_until(today, "vaccine")
        expected = today + timedelta(days=7)
        assert snooze_until == expected

    def test_calculate_snooze_until_food(self):
        """Calculate snooze for food (3 days)."""
        today = date(2026, 4, 25)
        snooze_until = calculate_snooze_until(today, "food")
        expected = today + timedelta(days=3)
        assert snooze_until == expected


class TestCategoryValidation:
    """Tests for category validation."""

    def test_valid_categories(self):
        valid_cats = [
            "vaccine", "deworming", "flea_tick", "food", "supplement",
            "chronic_medicine", "vet_followup", "blood_checkup",
            "vet_diagnostics", "hygiene"
        ]
        for cat in valid_cats:
            assert is_valid_category(cat) is True

    def test_invalid_category(self):
        assert is_valid_category("unknown") is False
        assert is_valid_category("") is False
        assert is_valid_category("VACCINE") is False  # Case sensitive


class TestCategoryClassification:
    """Tests for classifying items by keyword."""

    def test_classify_vaccine(self):
        names = [
            "Rabies vaccine",
            "DHPPi booster",
            "Nobivac L4",
            "Kennel Cough vaccine",
        ]
        for name in names:
            assert classify_item_category(name) == "vaccine"

    def test_classify_deworming(self):
        names = [
            "Deworming tablet",
            "Worm medicine",
        ]
        for name in names:
            assert classify_item_category(name) == "deworming"

    def test_classify_flea_tick(self):
        names = [
            "Flea and tick spray",
            "Flea prevention",
            "Tick treatment",
        ]
        for name in names:
            assert classify_item_category(name) == "flea_tick"

    def test_classify_blood_checkup(self):
        assert classify_item_category("Blood test") == "blood_checkup"
        assert classify_item_category("CBC") == "blood_checkup"

    def test_classify_diagnostics(self):
        names = [
            "X-ray",
            "Ultrasound",
            "Biopsy",
        ]
        for name in names:
            assert classify_item_category(name) == "vet_diagnostics"

    def test_classify_unknown(self):
        assert classify_item_category("Unknown item") is None
        assert classify_item_category("") is None


class TestReminderBatching:
    """Tests for reminder batching policy."""

    def test_vaccine_should_batch(self):
        """Vaccines should be batched to reduce message volume."""
        assert should_batch_reminders("vaccine") is True

    def test_non_vaccines_no_batch(self):
        """Non-vaccines should not be batched."""
        for cat in ["deworming", "food", "supplement", "vet_followup"]:
            assert should_batch_reminders(cat) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

