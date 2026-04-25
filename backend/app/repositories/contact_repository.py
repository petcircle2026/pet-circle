"""
Contact Repository â€” Pet contact management.

Manages:
- Veterinarian contacts
- Emergency contacts
- Primary care contacts
"""

from uuid import UUID
from typing import List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.core.contact import Contact


class ContactRepository:
    """Manages pet contact information (vets, emergency, etc.)."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Basic CRUD ----

    def find_by_id(self, contact_id: UUID) -> Contact | None:
        """Fetch a contact by ID."""
        return self.db.query(Contact).filter(Contact.id == contact_id).first()

    def find_by_pet_id(self, pet_id: UUID) -> List[Contact]:
        """Fetch all contacts for a pet."""
        return self.db.query(Contact).filter(Contact.pet_id == pet_id).all()

    def find_by_pet_and_type(self, pet_id: UUID, contact_type: str) -> List[Contact]:
        """
        Find contacts of a specific type for a pet.

        Args:
            pet_id: Pet ID
            contact_type: e.g. "veterinarian", "emergency", "groomer"

        Returns:
            List of matching contacts.
        """
        return (
            self.db.query(Contact)
            .filter(Contact.pet_id == pet_id, Contact.contact_type == contact_type)
            .all()
        )

    def find_by_pet_and_name(self, pet_id: UUID, name: str) -> Contact | None:
        """Find a contact by pet and name."""
        return (
            self.db.query(Contact)
            .filter(Contact.pet_id == pet_id, Contact.name == name)
            .first()
        )

    def create(self, contact: Contact) -> Contact:
        """Create a new contact."""
        self.db.add(contact)
        self.db.flush()
        return contact

    def update(self, contact: Contact) -> Contact:
        """Update an existing contact."""
        self.db.merge(contact)
        self.db.flush()
        return contact

    def delete(self, contact_id: UUID) -> bool:
        """
        Delete a contact.

        Args:
            contact_id: Contact ID

        Returns:
            True if contact was found and deleted.
        """
        contact = self.find_by_id(contact_id)
        if contact:
            self.db.delete(contact)
            self.db.flush()
            return True
        return False

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count contacts for a pet."""
        return (
            self.db.query(func.count(Contact.id))
            .filter(Contact.pet_id == pet_id)
            .scalar() or 0
        )

    # ---- Specialized Queries ----

    def find_primary_vet(self, pet_id: UUID) -> Contact | None:
        """
        Find the primary veterinarian for a pet.

        Returns:
            First veterinarian marked as primary, or None.
        """
        return (
            self.db.query(Contact)
            .filter(
                Contact.pet_id == pet_id,
                Contact.contact_type == "veterinarian",
                Contact.is_primary == True,
            )
            .first()
        )

    def set_primary_vet(self, pet_id: UUID, contact_id: UUID) -> bool:
        """
        Mark a contact as the primary veterinarian.

        Unmarks any other primary vet for the same pet.

        Args:
            pet_id: Pet ID
            contact_id: Contact ID

        Returns:
            True if successful.
        """
        # Unmark previous primary
        vets = self.find_by_pet_and_type(pet_id, "veterinarian")
        for vet in vets:
            vet.is_primary = False
            self.db.merge(vet)

        # Mark new primary
        contact = self.find_by_id(contact_id)
        if contact and contact.pet_id == pet_id:
            contact.is_primary = True
            self.db.merge(contact)
            self.db.flush()
            return True

        return False

    def find_vet_for_pet(self, pet_id: UUID) -> Contact | None:
        """Find the first veterinarian contact for a pet (oldest by created_at)."""
        return (
            self.db.query(Contact)
            .filter(Contact.pet_id == pet_id, Contact.role == "veterinarian")
            .order_by(Contact.created_at)
            .first()
        )

    def find_emergency_contacts(self, pet_id: UUID) -> List[Contact]:
        """Find all emergency contacts for a pet."""
        return self.find_by_pet_and_type(pet_id, "emergency")

    def find_recent_contacts(self, pet_id: UUID, days: int = 30) -> List[Contact]:
        """
        Find contacts created or updated in the last N days.

        Args:
            pet_id: Pet ID
            days: Number of days to look back

        Returns:
            List of recently modified contacts.
        """
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        return (
            self.db.query(Contact)
            .filter(
                Contact.pet_id == pet_id,
                Contact.updated_at >= cutoff,
            )
            .all()
        )

    # ---- Batch Operations ----

    def bulk_create(self, contacts: List[Contact]) -> List[Contact]:
        """Create multiple contacts at once."""
        self.db.add_all(contacts)
        self.db.flush()
        return contacts

    def delete_all_for_pet(self, pet_id: UUID) -> int:
        """
        Delete all contacts for a pet.

        Args:
            pet_id: Pet ID

        Returns:
            Count of deleted contacts.
        """
        count = (
            self.db.query(Contact).filter(Contact.pet_id == pet_id).delete()
        )
        self.db.flush()
        return count

