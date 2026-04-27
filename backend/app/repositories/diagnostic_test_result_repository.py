"""
Diagnostic Test Result Repository — Diagnostic test records.

Manages diagnostic test results and queries for pet health records.
"""

from uuid import UUID
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.models.health.diagnostic_test_result import DiagnosticTestResult


class DiagnosticTestResultRepository:
    """Manages diagnostic test result data."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_pet(self, pet_id: UUID) -> List[DiagnosticTestResult]:
        """Find all diagnostic test results for a pet."""
        return (
            self.db.query(DiagnosticTestResult)
            .filter(DiagnosticTestResult.pet_id == pet_id)
            .all()
        )

    def find_by_document_ids(self, pet_id: UUID, document_ids: List[UUID]) -> Dict[Any, List[DiagnosticTestResult]]:
        """
        Find diagnostic results for a pet grouped by document ID.
        Used by records_service to organize results by source document.
        """
        rows = (
            self.db.query(DiagnosticTestResult)
            .filter(
                DiagnosticTestResult.pet_id == pet_id,
                DiagnosticTestResult.document_id.in_(document_ids),
            )
            .all()
        )
        grouped: Dict[Any, List[DiagnosticTestResult]] = {}
        for row in rows:
            grouped.setdefault(row.document_id, []).append(row)
        return grouped

    def create(self, result: DiagnosticTestResult) -> DiagnosticTestResult:
        """Create a new diagnostic test result."""
        self.db.add(result)
        self.db.flush()
        return result

    def update(self, result: DiagnosticTestResult) -> DiagnosticTestResult:
        """Update a diagnostic test result."""
        self.db.merge(result)
        self.db.flush()
        return result

    def delete(self, result_id: UUID) -> bool:
        """Delete a diagnostic test result."""
        result = self.db.query(DiagnosticTestResult).filter(DiagnosticTestResult.id == result_id).first()
        if result:
            self.db.delete(result)
            self.db.flush()
            return True
        return False
