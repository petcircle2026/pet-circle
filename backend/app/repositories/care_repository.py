"""
Care Repository â€” Pet care records (hygiene, diagnostics, weight).

Manages:
- Hygiene preferences
- Diagnostic test results
- Weight history
- Ideal weight caches
"""

from uuid import UUID
from typing import List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.nutrition.hygiene_preference import HygienePreference
from app.models.health.diagnostic_test_result import DiagnosticTestResult
from app.models.health.weight_history import WeightHistory
from app.models.cache.ideal_weight_cache import IdealWeightCache


class CareRepository:
    """Manages pet care records and health metrics."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Hygiene Preferences ----

    def find_hygiene_preference(self, pet_id: UUID) -> HygienePreference | None:
        """Fetch hygiene preferences for a pet."""
        return (
            self.db.query(HygienePreference)
            .filter(HygienePreference.pet_id == pet_id)
            .first()
        )

    def create_hygiene_preference(
        self, preference: HygienePreference
    ) -> HygienePreference:
        """Create hygiene preferences for a pet."""
        self.db.add(preference)
        self.db.flush()
        return preference

    def update_hygiene_preference(
        self, preference: HygienePreference
    ) -> HygienePreference:
        """Update hygiene preferences."""
        self.db.merge(preference)
        self.db.flush()
        return preference

    def find_hygiene_preferences_list(self, pet_id: UUID) -> List[HygienePreference]:
        """Fetch all hygiene preference rows for a pet (grooming nudge use-case)."""
        return (
            self.db.query(HygienePreference)
            .filter(HygienePreference.pet_id == pet_id)
            .all()
        )

    def get_or_create_hygiene_preference(
        self, pet_id: UUID
    ) -> HygienePreference:
        """
        Get hygiene preferences or create with defaults if missing.

        Args:
            pet_id: Pet ID

        Returns:
            HygienePreference (existing or newly created).
        """
        pref = self.find_hygiene_preference(pet_id)
        if not pref:
            pref = HygienePreference(pet_id=pet_id)
            pref = self.create_hygiene_preference(pref)
        return pref

    # ---- Diagnostic Test Results ----

    def find_diagnostic_by_id(
        self, test_id: UUID
    ) -> DiagnosticTestResult | None:
        """Fetch a diagnostic test result by ID."""
        return (
            self.db.query(DiagnosticTestResult)
            .filter(DiagnosticTestResult.id == test_id)
            .first()
        )

    def find_diagnostics_by_pet(self, pet_id: UUID) -> List[DiagnosticTestResult]:
        """Fetch all diagnostic test results for a pet."""
        return (
            self.db.query(DiagnosticTestResult)
            .filter(DiagnosticTestResult.pet_id == pet_id)
            .order_by(desc(DiagnosticTestResult.observed_at))
            .all()
        )

    def find_diagnostics_by_type(
        self, pet_id: UUID, test_type: str
    ) -> List[DiagnosticTestResult]:
        """
        Find diagnostic results of a specific type.

        Args:
            pet_id: Pet ID
            test_type: e.g. "blood_work", "ultrasound", "xray"

        Returns:
            List of matching test results.
        """
        return (
            self.db.query(DiagnosticTestResult)
            .filter(
                DiagnosticTestResult.pet_id == pet_id,
                DiagnosticTestResult.test_type == test_type,
            )
            .order_by(desc(DiagnosticTestResult.observed_at))
            .all()
        )

    def find_last_diagnostic(
        self, pet_id: UUID, test_type: str | None = None
    ) -> DiagnosticTestResult | None:
        """
        Find the most recent diagnostic for a pet.

        Args:
            pet_id: Pet ID
            test_type: Optional type filter

        Returns:
            Most recent DiagnosticTestResult or None.
        """
        query = self.db.query(DiagnosticTestResult).filter(
            DiagnosticTestResult.pet_id == pet_id
        )

        if test_type:
            query = query.filter(DiagnosticTestResult.test_type == test_type)

        return query.order_by(desc(DiagnosticTestResult.observed_at)).first()

    def find_last_checkup(self, pet_id: UUID) -> DiagnosticTestResult | None:
        """Find the most recent veterinary checkup."""
        return self.find_last_diagnostic(pet_id, test_type="checkup")

    def create_diagnostic(
        self, diagnostic: DiagnosticTestResult
    ) -> DiagnosticTestResult:
        """Create a diagnostic test result."""
        self.db.add(diagnostic)
        self.db.flush()
        return diagnostic

    def update_diagnostic(
        self, diagnostic: DiagnosticTestResult
    ) -> DiagnosticTestResult:
        """Update a diagnostic test result."""
        self.db.merge(diagnostic)
        self.db.flush()
        return diagnostic

    def delete_diagnostic(self, test_id: UUID) -> bool:
        """
        Delete a diagnostic test result.

        Args:
            test_id: DiagnosticTestResult ID

        Returns:
            True if found and deleted.
        """
        test = self.find_diagnostic_by_id(test_id)
        if test:
            self.db.delete(test)
            self.db.flush()
            return True
        return False

    def count_diagnostics_by_pet(self, pet_id: UUID) -> int:
        """Count total diagnostic tests for a pet."""
        return (
            self.db.query(func.count(DiagnosticTestResult.id))
            .filter(DiagnosticTestResult.pet_id == pet_id)
            .scalar() or 0
        )

    # ---- Weight History ----

    def find_weight_by_id(self, weight_id: UUID) -> WeightHistory | None:
        """Fetch a weight record by ID."""
        return (
            self.db.query(WeightHistory)
            .filter(WeightHistory.id == weight_id)
            .first()
        )

    def find_weight_history(self, pet_id: UUID) -> List[WeightHistory]:
        """Fetch all weight records for a pet, ordered by date."""
        return (
            self.db.query(WeightHistory)
            .filter(WeightHistory.pet_id == pet_id)
            .order_by(desc(WeightHistory.recorded_at))
            .all()
        )

    def find_weight_history_paginated(
        self, pet_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[List[WeightHistory], int]:
        """Fetch paginated weight history."""
        query = self.db.query(WeightHistory).filter(
            WeightHistory.pet_id == pet_id
        )
        total = query.count()
        results = (
            query.order_by(desc(WeightHistory.recorded_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return results, total

    def find_last_weight(self, pet_id: UUID) -> WeightHistory | None:
        """Find the most recent weight record."""
        return (
            self.db.query(WeightHistory)
            .filter(WeightHistory.pet_id == pet_id)
            .order_by(desc(WeightHistory.recorded_at))
            .first()
        )

    def find_weights_in_range(
        self, pet_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[WeightHistory]:
        """Find weight records within a date range."""
        return (
            self.db.query(WeightHistory)
            .filter(
                WeightHistory.pet_id == pet_id,
                WeightHistory.recorded_at >= start_date,
                WeightHistory.recorded_at <= end_date,
            )
            .order_by(desc(WeightHistory.recorded_at))
            .all()
        )

    def add_weight_record(self, weight: WeightHistory) -> WeightHistory:
        """Add a weight record for a pet."""
        self.db.add(weight)
        self.db.flush()
        return weight

    def update_weight_record(self, weight: WeightHistory) -> WeightHistory:
        """Update a weight record."""
        self.db.merge(weight)
        self.db.flush()
        return weight

    def delete_weight_record(self, weight_id: UUID) -> bool:
        """
        Delete a weight record.

        Args:
            weight_id: WeightHistory ID

        Returns:
            True if found and deleted.
        """
        weight = self.find_weight_by_id(weight_id)
        if weight:
            self.db.delete(weight)
            self.db.flush()
            return True
        return False

    def count_weight_records(self, pet_id: UUID) -> int:
        """Count total weight records for a pet."""
        return (
            self.db.query(func.count(WeightHistory.id))
            .filter(WeightHistory.pet_id == pet_id)
            .scalar() or 0
        )

    # ---- Ideal Weight Cache ----

    def find_ideal_weight_cache(self, pet_id: UUID) -> IdealWeightCache | None:
        """Fetch cached ideal weight for a pet."""
        return (
            self.db.query(IdealWeightCache)
            .filter(IdealWeightCache.pet_id == pet_id)
            .first()
        )

    def create_ideal_weight_cache(
        self, cache: IdealWeightCache
    ) -> IdealWeightCache:
        """Create ideal weight cache."""
        self.db.add(cache)
        self.db.flush()
        return cache

    def update_ideal_weight_cache(
        self, cache: IdealWeightCache
    ) -> IdealWeightCache:
        """Update ideal weight cache."""
        self.db.merge(cache)
        self.db.flush()
        return cache

    # ---- Aggregations ----

    def get_average_weight(self, pet_id: UUID) -> float | None:
        """Calculate average weight for a pet."""
        avg = (
            self.db.query(func.avg(WeightHistory.weight_kg))
            .filter(WeightHistory.pet_id == pet_id)
            .scalar()
        )
        return float(avg) if avg else None

    def get_weight_trend(self, pet_id: UUID, days: int = 90) -> List[WeightHistory]:
        """Get weight records from the last N days (for trend analysis)."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return self.find_weights_in_range(pet_id, cutoff, datetime.utcnow())

    def find_active_medications_with_pets(self):
        """
        Fetch (ConditionMedication, Condition, Pet, User) for active medications.
        Used by reminder_engine for chronic medicine candidate collection.
        """
        from app.models.health.condition import Condition
        from app.models.health.condition_medication import ConditionMedication
        from app.models.core.pet import Pet
        from app.models.core.user import User
        return (
            self.db.query(ConditionMedication, Condition, Pet, User)
            .join(Condition, ConditionMedication.condition_id == Condition.id)
            .join(Pet, Condition.pet_id == Pet.id)
            .join(User, Pet.user_id == User.id)
            .filter(
                ConditionMedication.status == "active",
                Pet.is_deleted == False,
                User.is_deleted == False,
            )
            .all()
        )

    def find_monitoring_with_due_date_and_pets(self):
        """
        Fetch (ConditionMonitoring, Condition, Pet, User) for monitoring items with a due date.
        Used by reminder_engine for vet follow-up candidate collection.
        """
        from app.models.health.condition import Condition
        from app.models.health.condition_monitoring import ConditionMonitoring
        from app.models.core.pet import Pet
        from app.models.core.user import User
        return (
            self.db.query(ConditionMonitoring, Condition, Pet, User)
            .join(Condition, ConditionMonitoring.condition_id == Condition.id)
            .join(Pet, Condition.pet_id == Pet.id)
            .join(User, Pet.user_id == User.id)
            .filter(
                ConditionMonitoring.next_due_date.isnot(None),
                Pet.is_deleted == False,
                User.is_deleted == False,
            )
            .all()
        )

    def find_hygiene_prefs_with_reminder_and_pets(self):
        """
        Fetch (HygienePreference, Pet, User) where reminder=True.
        Used by reminder_engine for hygiene candidate collection.
        """
        from app.models.core.pet import Pet
        from app.models.core.user import User
        return (
            self.db.query(HygienePreference, Pet, User)
            .join(Pet, HygienePreference.pet_id == Pet.id)
            .join(User, Pet.user_id == User.id)
            .filter(
                HygienePreference.reminder == True,
                Pet.is_deleted == False,
                User.is_deleted == False,
            )
            .all()
        )

    def has_any_diagnostic(self, pet_id: UUID) -> bool:
        """Return True if the pet has at least one diagnostic test result."""
        return (
            self.db.query(DiagnosticTestResult.id)
            .filter(DiagnosticTestResult.pet_id == pet_id)
            .first() is not None
        )

    def find_active_condition_medications_with_refill(
        self, pet_id: UUID
    ) -> list:
        """
        Fetch active condition medications with refill_due_date for a pet.
        Used by care_plan_engine to build prescriptions dict.

        Returns list of ConditionMedication with eager-loaded condition.
        """
        from app.models.health.condition_medication import ConditionMedication
        from app.models.health.condition import Condition
        from sqlalchemy.orm import joinedload

        return (
            self.db.query(ConditionMedication)
            .join(Condition, ConditionMedication.condition_id == Condition.id)
            .options(joinedload(ConditionMedication.condition))
            .filter(
                Condition.pet_id == pet_id,
                ConditionMedication.status == "active",
                ConditionMedication.refill_due_date.isnot(None),
            )
            .all()
        )

    def find_active_condition_medications_all(
        self, pet_id: UUID
    ) -> list:
        """
        Fetch all active condition medications (item_type='medicine') for a pet.
        Used by care_plan_engine for clinical medication section.

        Returns list of ConditionMedication with eager-loaded condition.
        """
        from app.models.health.condition_medication import ConditionMedication
        from app.models.health.condition import Condition
        from sqlalchemy.orm import joinedload

        return (
            self.db.query(ConditionMedication)
            .join(Condition, ConditionMedication.condition_id == Condition.id)
            .options(joinedload(ConditionMedication.condition))
            .filter(
                Condition.pet_id == pet_id,
                ConditionMedication.status == "active",
                ConditionMedication.item_type == "medicine",
            )
            .all()
        )

    def find_active_conditions_for_pet(self, pet_id: UUID) -> list:
        """
        Fetch all active conditions for a pet.
        Used by care_plan_engine for signal resolution.

        Returns list of Condition.
        """
        from app.models.health.condition import Condition

        return (
            self.db.query(Condition)
            .filter(Condition.pet_id == pet_id, Condition.is_active.is_(True))
            .all()
        )

