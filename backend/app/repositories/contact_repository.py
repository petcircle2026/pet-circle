from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from app.models.core.contact import Contact


class ContactRepository:

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, contact_id: UUID) -> Contact | None:
        return self.db.query(Contact).filter(Contact.id == contact_id).first()

    def find_by_pet_id(self, pet_id: UUID) -> List[Contact]:
        return self.db.query(Contact).filter(Contact.pet_id == pet_id).all()

    def create(self, contact: Contact) -> Contact:
        self.db.add(contact)
        self.db.flush()
        return contact

    def update(self, contact: Contact) -> Contact:
        self.db.merge(contact)
        self.db.flush()
        return contact

    def delete(self, contact_id: UUID) -> bool:
        contact = self.find_by_id(contact_id)
        if contact:
            self.db.delete(contact)
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

    def find_by_pet_name_and_role(
        self, pet_id: UUID, contact_name: str, role: str
    ) -> Contact | None:
        return (
            self.db.query(Contact)
            .filter(Contact.pet_id == pet_id, Contact.name == contact_name, Contact.role == role)
            .first()
        )

    def find_by_pet(self, pet_id: UUID) -> List[Contact]:
        return self.db.query(Contact).filter(Contact.pet_id == pet_id).all()

    def find_best_vet_contact(self, pet_id: UUID) -> Contact | None:
        """
        Return the best veterinarian Contact for a pet.

        Sorting priority:
          1. Contacts with a last_visit_date — most recent first.
          2. Contacts with no last_visit_date — prescriptions before vaccinations.
        """
        from sqlalchemy import case

        category_rank = case(
            (Contact.source_document_category == "prescription", 0),
            (Contact.source_document_category == "vaccination", 1),
            else_=2,
        )

        return (
            self.db.query(Contact)
            .filter(
                Contact.pet_id == pet_id,
                Contact.role == "veterinarian",
            )
            .order_by(
                Contact.last_visit_date.desc().nullslast(),
                category_rank,
                Contact.created_at.desc(),
            )
            .first()
        )
