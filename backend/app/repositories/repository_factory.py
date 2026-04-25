"""
Repository Factory â€” Dependency injection for all repositories.

Provides a single factory function that creates all repository instances
with a shared database session. This enables easy testing (mock the factory)
and centralized dependency management.
"""

from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.repositories.pet_repository import PetRepository
from app.repositories.preventive_repository import PreventiveRepository
from app.repositories.health_repository import HealthRepository
from app.repositories.preventive_master_repository import PreventiveMasterRepository
from app.repositories.config_repository import ConfigRepository
from app.repositories.user_repository import UserRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.cart_repository import CartRepository
from app.repositories.diet_repository import DietRepository
from app.repositories.care_repository import CareRepository
from app.repositories.reminder_repository import ReminderRepository
from app.repositories.nudge_repository import NudgeRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.audit_repository import AuditRepository


@dataclass
class Repositories:
    """
    Container for all repositories.

    Usage:
        repos = get_repositories(db)
        pet = repos.pet.find_by_id(pet_id)
        preventive = repos.preventive.find_by_pet_id(pet_id)
    """

    # Core entities
    pet: PetRepository
    preventive: PreventiveRepository
    health: HealthRepository

    # Lookup/config
    preventive_master: PreventiveMasterRepository
    config: ConfigRepository

    # User/access
    user: UserRepository
    contact: ContactRepository

    # Orders/cart
    order: OrderRepository
    cart: CartRepository

    # Health/diet
    diet: DietRepository
    care: CareRepository

    # Reminders/nudges
    reminder: ReminderRepository
    nudge: NudgeRepository

    # Documents/audit
    document: DocumentRepository
    audit: AuditRepository


def get_repositories(db: Session) -> Repositories:
    """
    Factory function to create all repository instances.

    Args:
        db: SQLAlchemy database session

    Returns:
        Repositories container with all repositories initialized.

    Usage:
        from fastapi import Depends
        from app.database import get_db
        from app.repositories.repository_factory import get_repositories

        @app.get("/pet/{pet_id}")
        async def get_pet(pet_id: UUID, repos = Depends(get_repositories)):
            pet = repos.pet.find_by_id(pet_id)
            return pet
    """
    return Repositories(
        # Core entities
        pet=PetRepository(db),
        preventive=PreventiveRepository(db),
        health=HealthRepository(db),
        # Lookup/config
        preventive_master=PreventiveMasterRepository(db),
        config=ConfigRepository(db),
        # User/access
        user=UserRepository(db),
        contact=ContactRepository(db),
        # Orders/cart
        order=OrderRepository(db),
        cart=CartRepository(db),
        # Health/diet
        diet=DietRepository(db),
        care=CareRepository(db),
        # Reminders/nudges
        reminder=ReminderRepository(db),
        nudge=NudgeRepository(db),
        # Documents/audit
        document=DocumentRepository(db),
        audit=AuditRepository(db),
    )

