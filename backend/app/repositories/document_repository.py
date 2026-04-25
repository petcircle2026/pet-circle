"""
Document Repository â€” Document and message log access.

Manages:
- Document upload records
- Document extraction status
- Storage backend tracking
- Message logs
"""

from uuid import UUID
from typing import List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.auth.document import Document
from app.models.messaging.message_log import MessageLog


class DocumentRepository:
    """Manages document and message log data."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Document CRUD ----

    def find_by_id(self, document_id: UUID) -> Document | None:
        """Fetch a document by ID."""
        return self.db.query(Document).filter(Document.id == document_id).first()

    def find_by_pet_id(self, pet_id: UUID) -> List[Document]:
        """Fetch all documents for a pet."""
        return (
            self.db.query(Document)
            .filter(Document.pet_id == pet_id)
            .order_by(desc(Document.created_at))
            .all()
        )

    def find_by_pet_id_paginated(
        self, pet_id: UUID, skip: int = 0, limit: int = 50
    ) -> tuple[List[Document], int]:
        """Fetch paginated documents for a pet."""
        query = self.db.query(Document).filter(Document.pet_id == pet_id)
        total = query.count()
        results = (
            query.order_by(desc(Document.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return results, total

    def find_by_status(self, status: str) -> List[Document]:
        """
        Find documents by extraction status.

        Args:
            status: e.g. "pending", "extracted", "failed", "verified"

        Returns:
            List of matching documents.
        """
        return (
            self.db.query(Document)
            .filter(Document.extraction_status == status)
            .all()
        )

    def find_pending_extraction(self) -> List[Document]:
        """Fetch all documents awaiting extraction."""
        return (
            self.db.query(Document)
            .filter(Document.extraction_status == "pending")
            .order_by(Document.created_at)
            .all()
        )

    def find_by_storage_backend(self, backend: str) -> List[Document]:
        """
        Find documents stored in a specific backend.

        Args:
            backend: e.g. "gcp", "supabase"

        Returns:
            List of documents.
        """
        return (
            self.db.query(Document)
            .filter(Document.storage_backend == backend)
            .all()
        )

    def find_unsynced_documents(self) -> List[Document]:
        """Fetch documents not yet synced to GCP."""
        return (
            self.db.query(Document)
            .filter(Document.storage_backend == "supabase", Document.synced_to_gcp == False)
            .all()
        )

    def create(self, document: Document) -> Document:
        """Create a document record."""
        self.db.add(document)
        self.db.flush()
        return document

    def update(self, document: Document) -> Document:
        """Update a document record."""
        self.db.merge(document)
        self.db.flush()
        return document

    def update_extraction_status(
        self, document_id: UUID, status: str, extracted_data: dict | None = None
    ) -> Document | None:
        """
        Update document extraction status.

        Args:
            document_id: Document ID
            status: New status
            extracted_data: Extracted JSON data (optional)

        Returns:
            Updated Document or None if not found.
        """
        doc = self.find_by_id(document_id)
        if doc:
            doc.extraction_status = status
            if extracted_data:
                doc.extracted_data = extracted_data
            if status in ["extracted", "failed"]:
                doc.extracted_at = datetime.utcnow()
            self.db.merge(doc)
            self.db.flush()
            return doc
        return None

    def mark_synced(self, document_id: UUID, backend: str = "gcp") -> Document | None:
        """
        Mark document as synced to a storage backend.

        Args:
            document_id: Document ID
            backend: Backend name (default: "gcp")

        Returns:
            Updated Document or None if not found.
        """
        doc = self.find_by_id(document_id)
        if doc:
            if backend == "gcp":
                doc.synced_to_gcp = True
                doc.synced_to_gcp_at = datetime.utcnow()
            self.db.merge(doc)
            self.db.flush()
            return doc
        return None

    def delete(self, document_id: UUID) -> bool:
        """
        Delete a document record.

        Args:
            document_id: Document ID

        Returns:
            True if found and deleted.
        """
        doc = self.find_by_id(document_id)
        if doc:
            self.db.delete(doc)
            self.db.flush()
            return True
        return False

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count total documents for a pet."""
        return (
            self.db.query(func.count(Document.id))
            .filter(Document.pet_id == pet_id)
            .scalar() or 0
        )

    def count_by_status(self, status: str) -> int:
        """Count documents by extraction status."""
        return (
            self.db.query(func.count(Document.id))
            .filter(Document.extraction_status == status)
            .scalar() or 0
        )

    # ---- Message Logs ----

    def log_message(self, message: MessageLog) -> MessageLog:
        """Create a message log entry."""
        self.db.add(message)
        self.db.flush()
        return message

    def find_message_log_by_id(self, log_id: UUID) -> MessageLog | None:
        """Fetch a message log by ID."""
        return (
            self.db.query(MessageLog)
            .filter(MessageLog.id == log_id)
            .first()
        )

    def find_message_logs(
        self, pet_id: UUID, limit: int = 100
    ) -> List[MessageLog]:
        """Fetch recent message logs for a pet."""
        return (
            self.db.query(MessageLog)
            .filter(MessageLog.pet_id == pet_id)
            .order_by(desc(MessageLog.received_at))
            .limit(limit)
            .all()
        )

    def find_message_logs_paginated(
        self, pet_id: UUID, skip: int = 0, limit: int = 50
    ) -> tuple[List[MessageLog], int]:
        """Fetch paginated message logs."""
        query = self.db.query(MessageLog).filter(MessageLog.pet_id == pet_id)
        total = query.count()
        results = (
            query.order_by(desc(MessageLog.received_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return results, total

    def find_message_logs_by_type(
        self, pet_id: UUID, message_type: str, limit: int = 50
    ) -> List[MessageLog]:
        """Find message logs of a specific type."""
        return (
            self.db.query(MessageLog)
            .filter(
                MessageLog.pet_id == pet_id,
                MessageLog.message_type == message_type,
            )
            .order_by(desc(MessageLog.received_at))
            .limit(limit)
            .all()
        )

    def find_message_logs_by_date_range(
        self, pet_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[MessageLog]:
        """Find message logs within a date range."""
        return (
            self.db.query(MessageLog)
            .filter(
                MessageLog.pet_id == pet_id,
                MessageLog.received_at >= start_date,
                MessageLog.received_at <= end_date,
            )
            .order_by(desc(MessageLog.received_at))
            .all()
        )

    def count_message_logs(self, pet_id: UUID) -> int:
        """Count total message logs for a pet."""
        return (
            self.db.query(func.count(MessageLog.id))
            .filter(MessageLog.pet_id == pet_id)
            .scalar() or 0
        )

    def count_message_logs_by_type(self, pet_id: UUID, message_type: str) -> int:
        """Count message logs of a specific type."""
        return (
            self.db.query(func.count(MessageLog.id))
            .filter(
                MessageLog.pet_id == pet_id,
                MessageLog.message_type == message_type,
            )
            .scalar() or 0
        )

    def delete_message_logs_older_than(self, days: int = 90) -> int:
        """
        Delete message logs older than N days.

        Args:
            days: Age threshold

        Returns:
            Count of deleted logs.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        count = (
            self.db.query(MessageLog)
            .filter(MessageLog.received_at < cutoff)
            .delete()
        )
        self.db.flush()
        return count

    def bulk_log_messages(self, messages: List[MessageLog]) -> List[MessageLog]:
        """Create multiple message logs at once."""
        self.db.add_all(messages)
        self.db.flush()
        return messages

    def find_last_message_activity(self, masked_mobile: str) -> datetime | None:
        """Return the created_at of the most recent message log for a phone number."""
        result = (
            self.db.query(MessageLog.created_at)
            .filter(MessageLog.mobile_number == masked_mobile)
            .order_by(desc(MessageLog.created_at))
            .first()
        )
        return result[0] if result else None

    def count_uploads_in_window(
        self, pet_id: UUID, start: datetime, end: datetime, statuses: list[str]
    ) -> int:
        """Count documents for a pet uploaded within a datetime window and matching statuses."""
        from sqlalchemy import func
        return (
            self.db.query(func.count(Document.id))
            .filter(
                Document.pet_id == pet_id,
                Document.created_at >= start,
                Document.created_at < end,
                Document.extraction_status.in_(statuses),
            )
            .scalar() or 0
        )

    def find_by_content_hash(
        self, pet_id: UUID, content_hash: str, statuses: list[str]
    ) -> Document | None:
        """Find an existing document with a matching content hash and status."""
        return (
            self.db.query(Document)
            .filter(
                Document.pet_id == pet_id,
                Document.content_hash == content_hash,
                Document.extraction_status.in_(statuses),
            )
            .first()
        )

    def count_inbound_after(self, phone_number: str, after: datetime) -> int:
        """Count inbound messages from a phone number received after a given datetime."""
        return (
            self.db.query(MessageLog)
            .filter(
                MessageLog.phone_number == phone_number,
                MessageLog.direction == "inbound",
                MessageLog.created_at > after,
            )
            .count()
        )

