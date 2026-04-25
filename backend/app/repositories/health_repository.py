"""
Health Repository â€” Centralized health-related data access.

Manages queries for WeightHistory, Condition, DiagnosticTestResult, and related
health metrics. This is the single source of truth for all health-related queries.
"""

from uuid import UUID
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session, selectinload

from app.models.health.weight_history import WeightHistory
from app.models.health.condition import Condition
from app.models.health.condition_medication import ConditionMedication
from app.models.health.condition_monitoring import ConditionMonitoring
from app.models.health.diagnostic_test_result import DiagnosticTestResult


class HealthRepository:
    """Encapsulates all health-related queries (weights, conditions, diagnostics)."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Weight history queries ----

    def get_weight_history(self, pet_id: UUID, limit: int = 24) -> list[WeightHistory]:
        """Fetch recent weight records for a pet (most recent first)."""
        return (
            self.db.query(WeightHistory)
            .filter(WeightHistory.pet_id == pet_id)
            .order_by(desc(WeightHistory.recorded_at))
            .limit(limit)
            .all()
        )

    def get_latest_weight(self, pet_id: UUID) -> WeightHistory | None:
        """Fetch most recent weight measurement for a pet."""
        return (
            self.db.query(WeightHistory)
            .filter(WeightHistory.pet_id == pet_id)
            .order_by(desc(WeightHistory.recorded_at))
            .first()
        )

    def get_weight_history_by_date_range(
        self, pet_id: UUID, start_date: date, end_date: date
    ) -> list[WeightHistory]:
        """Fetch weight records within a date range."""
        return (
            self.db.query(WeightHistory)
            .filter(
                and_(
                    WeightHistory.pet_id == pet_id,
                    WeightHistory.recorded_at >= start_date,
                    WeightHistory.recorded_at <= end_date,
                )
            )
            .order_by(desc(WeightHistory.recorded_at))
            .all()
        )

    def add_weight(
        self,
        pet_id: UUID,
        weight: Decimal,
        recorded_at: date,
        bcs: int | None = None,
        note: str | None = None,
    ) -> WeightHistory:
        """
        Record a new weight measurement.

        Args:
            pet_id: Pet ID
            weight: Weight in kg
            recorded_at: Date measurement was taken
            bcs: Body Condition Score (1-9)
            note: Optional note

        Returns: New WeightHistory instance (not yet committed)
        """
        record = WeightHistory(
            pet_id=pet_id,
            weight=weight,
            recorded_at=recorded_at,
            bcs=bcs,
            note=note,
        )
        self.db.add(record)
        return record

    def count_weights_by_pet(self, pet_id: UUID) -> int:
        """Count total weight records for a pet."""
        return self.db.query(WeightHistory).filter(WeightHistory.pet_id == pet_id).count()

    # ---- Condition queries ----

    def get_active_conditions(self, pet_id: UUID) -> list[Condition]:
        """Fetch all active conditions for a pet."""
        return (
            self.db.query(Condition)
            .filter(and_(Condition.pet_id == pet_id, Condition.status == "active"))
            .all()
        )

    def get_active_conditions_with_relations(self, pet_id: UUID) -> list[Condition]:
        """
        Fetch conditions WITH medications and monitoring (eager load).

        Use when building dashboard to display condition details.
        Prevents N+1: fetch conditions, medications, and monitoring in one query.
        """
        return (
            self.db.query(Condition)
            .filter(and_(Condition.pet_id == pet_id, Condition.status == "active"))
            .options(
                selectinload(Condition.medications),
                selectinload(Condition.monitoring_items),
            )
            .all()
        )

    def get_condition_by_id(self, condition_id: UUID) -> Condition | None:
        """Fetch a single condition by ID."""
        return self.db.query(Condition).filter(Condition.id == condition_id).first()

    def get_condition_with_relations(self, condition_id: UUID) -> Condition | None:
        """Fetch condition WITH medications and monitoring (eager load)."""
        return (
            self.db.query(Condition)
            .filter(Condition.id == condition_id)
            .options(
                selectinload(Condition.medications),
                selectinload(Condition.monitoring_items),
            )
            .first()
        )

    def create_condition(
        self, pet_id: UUID, name: str, diagnosis_date: date, description: str | None = None
    ) -> Condition:
        """
        Create a new condition record.

        Args:
            pet_id: Pet ID
            name: Condition name (e.g., "Diabetes", "Allergies")
            diagnosis_date: When diagnosed
            description: Optional description

        Returns: New Condition instance (not yet committed)
        """
        condition = Condition(
            pet_id=pet_id,
            name=name,
            diagnosis_date=diagnosis_date,
            description=description,
            status="active",
        )
        self.db.add(condition)
        return condition

    def get_all_conditions_by_pet(self, pet_id: UUID) -> list[Condition]:
        """Fetch all conditions (active and resolved) for a pet."""
        return (
            self.db.query(Condition).filter(Condition.pet_id == pet_id).all()
        )

    def count_active_conditions(self, pet_id: UUID) -> int:
        """Count active conditions for a pet (used by health score)."""
        return (
            self.db.query(Condition)
            .filter(and_(Condition.pet_id == pet_id, Condition.status == "active"))
            .count()
        )

    def update_condition_status(
        self, condition_id: UUID, new_status: str
    ) -> Condition | None:
        """Update condition status ('active', 'resolved', 'chronic')."""
        condition = self.get_condition_by_id(condition_id)
        if condition:
            condition.status = new_status
            return condition
        return None

    # ---- Condition medication queries ----

    def get_medications_by_condition(self, condition_id: UUID) -> list[ConditionMedication]:
        """Fetch all medications for a condition."""
        return (
            self.db.query(ConditionMedication)
            .filter(ConditionMedication.condition_id == condition_id)
            .all()
        )

    def add_medication(
        self,
        condition_id: UUID,
        name: str,
        dosage: str,
        frequency: str,
        start_date: date,
    ) -> ConditionMedication:
        """
        Add a medication to a condition.

        Returns: New ConditionMedication instance (not yet committed)
        """
        medication = ConditionMedication(
            condition_id=condition_id,
            name=name,
            dosage=dosage,
            frequency=frequency,
            start_date=start_date,
        )
        self.db.add(medication)
        return medication

    # ---- Condition monitoring queries ----

    def get_monitoring_items_by_condition(
        self, condition_id: UUID
    ) -> list[ConditionMonitoring]:
        """Fetch all monitoring items for a condition."""
        return (
            self.db.query(ConditionMonitoring)
            .filter(ConditionMonitoring.condition_id == condition_id)
            .all()
        )

    def add_monitoring_item(
        self,
        condition_id: UUID,
        item_name: str,
        monitoring_frequency: str,
    ) -> ConditionMonitoring:
        """
        Add a monitoring item to a condition.

        Returns: New ConditionMonitoring instance (not yet committed)
        """
        item = ConditionMonitoring(
            condition_id=condition_id,
            item_name=item_name,
            monitoring_frequency=monitoring_frequency,
        )
        self.db.add(item)
        return item

    # ---- Diagnostic test queries ----

    def get_diagnostics_by_pet(self, pet_id: UUID) -> list[DiagnosticTestResult]:
        """Fetch all diagnostic test results for a pet."""
        return (
            self.db.query(DiagnosticTestResult)
            .filter(DiagnosticTestResult.pet_id == pet_id)
            .order_by(
                desc(DiagnosticTestResult.observed_at),
                desc(DiagnosticTestResult.created_at),
            )
            .all()
        )

    def get_diagnostics_by_type(
        self, pet_id: UUID, test_type: str
    ) -> list[DiagnosticTestResult]:
        """Fetch diagnostics of a specific type (blood panel, urinalysis, etc.)."""
        return (
            self.db.query(DiagnosticTestResult)
            .filter(
                and_(
                    DiagnosticTestResult.pet_id == pet_id,
                    DiagnosticTestResult.test_type == test_type,
                )
            )
            .order_by(
                desc(DiagnosticTestResult.observed_at),
                desc(DiagnosticTestResult.created_at),
            )
            .all()
        )

    def get_latest_diagnostic_by_type(
        self, pet_id: UUID, test_type: str
    ) -> DiagnosticTestResult | None:
        """Fetch the most recent diagnostic test of a specific type."""
        return (
            self.db.query(DiagnosticTestResult)
            .filter(
                and_(
                    DiagnosticTestResult.pet_id == pet_id,
                    DiagnosticTestResult.test_type == test_type,
                )
            )
            .order_by(
                desc(DiagnosticTestResult.observed_at),
                desc(DiagnosticTestResult.created_at),
            )
            .first()
        )

    def add_diagnostic_result(
        self,
        pet_id: UUID,
        test_type: str,
        test_name: str,
        value_numeric: Decimal | None = None,
        unit: str | None = None,
        value_text: str | None = None,
        test_date: date | None = None,
    ) -> DiagnosticTestResult:
        """
        Record a new diagnostic test result.

        Returns: New DiagnosticTestResult instance (not yet committed)
        """
        result = DiagnosticTestResult(
            pet_id=pet_id,
            test_type=test_type,
            test_name=test_name,
            value_numeric=value_numeric,
            unit=unit,
            value_text=value_text,
            test_date=test_date or date.today(),
        )
        self.db.add(result)
        return result

    def count_diagnostics_by_pet(self, pet_id: UUID) -> int:
        """Count total diagnostic tests for a pet."""
        return (
            self.db.query(DiagnosticTestResult)
            .filter(DiagnosticTestResult.pet_id == pet_id)
            .count()
        )

    def find_active_conditions(self, pet_id: UUID) -> list[Condition]:
        """Alias for get_active_conditions_with_relations â€” used by nudge engine."""
        return self.get_active_conditions_with_relations(pet_id)

    def has_active_condition(self, pet_id: UUID) -> bool:
        """Return True if the pet has at least one active condition."""
        return (
            self.db.query(Condition.id)
            .filter(Condition.pet_id == pet_id, Condition.is_active == True)
            .first() is not None
        )

    def has_active_medication(self, pet_id: UUID) -> bool:
        """Return True if the pet has any medication under an active condition."""
        return (
            self.db.query(ConditionMedication.id)
            .join(Condition)
            .filter(Condition.pet_id == pet_id)
            .first() is not None
        )

