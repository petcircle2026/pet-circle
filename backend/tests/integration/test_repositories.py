"""
Integration tests for repositories.

Tests verify that repositories correctly encapsulate database access
and return expected data structures.
"""

import pytest
from uuid import uuid4
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, Column, String, ForeignKey, DateTime, Date, Numeric, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID

from app.repositories.pet_repository import PetRepository
from app.repositories.preventive_repository import PreventiveRepository
from app.repositories.health_repository import HealthRepository

# Create simple test models that don't have JSONB fields
TestBase = declarative_base()


class TestUser(TestBase):
    """Minimal User model for testing."""

    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone_hash = Column(String, nullable=False, unique=True)
    phone_encrypted = Column(String, nullable=False)


class TestPet(TestBase):
    """Minimal Pet model for testing."""

    __tablename__ = "pets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    species = Column(String, nullable=False)
    breed = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: date.today())


class TestPreventiveMaster(TestBase):
    """Minimal PreventiveMaster model for testing."""

    __tablename__ = "preventive_master"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    species = Column(String, nullable=False)
    frequency_months = Column(Numeric, nullable=False)


class TestPreventiveRecord(TestBase):
    """Minimal PreventiveRecord model for testing."""

    __tablename__ = "preventive_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id"), nullable=False)
    preventive_master_id = Column(UUID(as_uuid=True), ForeignKey("preventive_master.id"), nullable=True)
    custom_preventive_item_id = Column(UUID(as_uuid=True), nullable=True)
    last_done_date = Column(Date, nullable=False)
    next_due_date = Column(Date, nullable=False)
    status = Column(String, default="up_to_date")
    created_at = Column(DateTime, nullable=False, default=lambda: date.today())


class TestWeightHistory(TestBase):
    """Minimal WeightHistory model for testing."""

    __tablename__ = "weight_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id"), nullable=False)
    weight = Column(Numeric, nullable=False)
    recorded_at = Column(Date, nullable=False)
    bcs = Column(Numeric, nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: date.today())


class TestCondition(TestBase):
    """Minimal Condition model for testing."""

    __tablename__ = "conditions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id"), nullable=False)
    name = Column(String, nullable=False)
    diagnosis_date = Column(Date, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, nullable=False, default=lambda: date.today())


class TestDiagnosticTestResult(TestBase):
    """Minimal DiagnosticTestResult model for testing."""

    __tablename__ = "diagnostic_test_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id"), nullable=False)
    test_type = Column(String, nullable=False)
    test_name = Column(String, nullable=False)
    value_numeric = Column(Numeric, nullable=True)
    unit = Column(String, nullable=True)
    value_text = Column(String, nullable=True)
    test_date = Column(Date, nullable=False)


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    TestBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def user(db_session):
    """Create a test user."""
    user = TestUser(
        id=uuid4(),
        phone_hash="test_hash",
        phone_encrypted="test_encrypted",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def pet(db_session, user):
    """Create a test pet."""
    pet = TestPet(
        id=uuid4(),
        user_id=user.id,
        name="Fluffy",
        species="dog",
        breed="Golden Retriever",
    )
    db_session.add(pet)
    db_session.commit()
    return pet


@pytest.fixture
def preventive_master(db_session):
    """Create a preventive master item."""
    item = TestPreventiveMaster(
        id=uuid4(),
        name="Rabies Vaccine",
        type="vaccine",
        species="dog",
        frequency_months=12,
    )
    db_session.add(item)
    db_session.commit()
    return item


# ---- PetRepository Tests ----


class TestPetRepository:
    """Test PetRepository methods."""

    def test_get_by_id(self, db_session, pet):
        repo = PetRepository(db_session)
        found_pet = repo.get_by_id(pet.id)
        assert found_pet is not None
        assert found_pet.name == "Fluffy"
        assert found_pet.species == "dog"

    def test_get_by_id_not_found(self, db_session):
        repo = PetRepository(db_session)
        found_pet = repo.get_by_id(uuid4())
        assert found_pet is None

    def test_get_by_user(self, db_session, user, pet):
        repo = PetRepository(db_session)
        pets = repo.get_by_user(user.id)
        assert len(pets) == 1
        assert pets[0].id == pet.id

    def test_get_by_user_empty(self, db_session, user):
        repo = PetRepository(db_session)
        pets = repo.get_by_user(user.id)
        assert len(pets) == 0

    def test_get_by_user_multiple_pets(self, db_session, user):
        repo = PetRepository(db_session)
        pet1 = TestPet(id=uuid4(), user_id=user.id, name="Max", species="dog")
        pet2 = TestPet(id=uuid4(), user_id=user.id, name="Luna", species="cat")
        db_session.add(pet1)
        db_session.add(pet2)
        db_session.commit()

        pets = repo.get_by_user(user.id)
        assert len(pets) == 2

    def test_count_by_user(self, db_session, user):
        repo = PetRepository(db_session)
        # Create 3 pets
        for i in range(3):
            pet = TestPet(id=uuid4(), user_id=user.id, name=f"Pet{i}", species="dog")
            db_session.add(pet)
        db_session.commit()

        count = repo.count_by_user(user.id)
        assert count == 3

    def test_create(self, db_session, user):
        repo = PetRepository(db_session)
        new_pet = repo.create(
            user_id=user.id, name="Buddy", species="dog", breed="Labrador"
        )
        db_session.commit()

        assert new_pet.name == "Buddy"
        assert new_pet.species == "dog"

        # Verify it was actually saved
        found = repo.get_by_id(new_pet.id)
        assert found is not None

    def test_get_most_recent(self, db_session, user):
        repo = PetRepository(db_session)
        pet1 = TestPet(id=uuid4(), user_id=user.id, name="Old", species="dog")
        pet2 = TestPet(id=uuid4(), user_id=user.id, name="New", species="dog")
        db_session.add(pet1)
        db_session.commit()
        # Slight delay to ensure different timestamps
        import time
        time.sleep(0.01)
        db_session.add(pet2)
        db_session.commit()

        most_recent = repo.get_most_recent(user.id)
        assert most_recent.name == "New"

    def test_exists_by_id(self, db_session, pet):
        repo = PetRepository(db_session)
        assert repo.exists_by_id(pet.id) is True
        assert repo.exists_by_id(uuid4()) is False

    def test_get_by_species(self, db_session, user):
        repo = PetRepository(db_session)
        dog = TestPet(id=uuid4(), user_id=user.id, name="Rex", species="dog")
        cat = TestPet(id=uuid4(), user_id=user.id, name="Whiskers", species="cat")
        db_session.add(dog)
        db_session.add(cat)
        db_session.commit()

        dogs = repo.get_by_species("dog")
        assert len(dogs) == 1
        assert dogs[0].name == "Rex"


# ---- PreventiveRepository Tests ----


class TestPreventiveRepository:
    """Test PreventiveRepository methods."""

    def test_get_by_pet(self, db_session, pet, preventive_master):
        repo = PreventiveRepository(db_session)
        record = TestPreventiveRecord(
            id=uuid4(),
            pet_id=pet.id,
            preventive_master_id=preventive_master.id,
            last_done_date=date.today() - timedelta(days=365),
            next_due_date=date.today(),
            status="overdue",
        )
        db_session.add(record)
        db_session.commit()

        records = repo.get_by_pet(pet.id)
        assert len(records) == 1
        assert records[0].status == "overdue"

    def test_create(self, db_session, pet, preventive_master):
        repo = PreventiveRepository(db_session)
        new_record = repo.create(
            pet_id=pet.id,
            preventive_master_id=preventive_master.id,
            custom_preventive_item_id=None,
            last_done_date=date.today(),
            next_due_date=date.today() + timedelta(days=365),
        )
        db_session.commit()

        assert new_record.status == "up_to_date"

        # Verify it was saved
        found = repo.get_by_pet(pet.id)
        assert len(found) == 1

    def test_get_overdue_by_pet(self, db_session, pet, preventive_master):
        repo = PreventiveRepository(db_session)
        # Create overdue record
        overdue = TestPreventiveRecord(
            id=uuid4(),
            pet_id=pet.id,
            preventive_master_id=preventive_master.id,
            last_done_date=date.today() - timedelta(days=400),
            next_due_date=date.today() - timedelta(days=1),
            status="overdue",
        )
        # Create upcoming record
        upcoming = TestPreventiveRecord(
            id=uuid4(),
            pet_id=pet.id,
            preventive_master_id=preventive_master.id,
            last_done_date=date.today(),
            next_due_date=date.today() + timedelta(days=30),
            status="upcoming",
        )
        db_session.add(overdue)
        db_session.add(upcoming)
        db_session.commit()

        overdue_records = repo.get_overdue_by_pet(pet.id, date.today())
        assert len(overdue_records) == 1
        assert overdue_records[0].status == "overdue"

    def test_get_upcoming_by_pet(self, db_session, pet, preventive_master):
        repo = PreventiveRepository(db_session)
        # Create upcoming record
        upcoming = TestPreventiveRecord(
            id=uuid4(),
            pet_id=pet.id,
            preventive_master_id=preventive_master.id,
            last_done_date=date.today(),
            next_due_date=date.today() + timedelta(days=15),
            status="upcoming",
        )
        db_session.add(upcoming)
        db_session.commit()

        upcoming_records = repo.get_upcoming_by_pet(pet.id, date.today(), days_ahead=30)
        assert len(upcoming_records) == 1

    def test_count_overdue_by_pet(self, db_session, pet, preventive_master):
        repo = PreventiveRepository(db_session)
        # Create 2 overdue records
        for i in range(2):
            record = TestPreventiveRecord(
                id=uuid4(),
                pet_id=pet.id,
                preventive_master_id=preventive_master.id,
                last_done_date=date.today() - timedelta(days=400),
                next_due_date=date.today() - timedelta(days=1),
                status="overdue",
            )
            db_session.add(record)
        db_session.commit()

        count = repo.count_overdue_by_pet(pet.id, date.today())
        assert count == 2


# ---- HealthRepository Tests ----


class TestHealthRepository:
    """Test HealthRepository methods."""

    def test_add_weight(self, db_session, pet):
        repo = HealthRepository(db_session)
        weight = repo.add_weight(
            pet_id=pet.id,
            weight=Decimal("25.5"),
            recorded_at=date.today(),
            bcs=5,
        )
        db_session.commit()

        found = repo.get_latest_weight(pet.id)
        assert found is not None
        assert found.weight == Decimal("25.5")
        assert found.bcs == 5

    def test_get_weight_history(self, db_session, pet):
        repo = HealthRepository(db_session)
        # Add multiple weights
        for i in range(5):
            repo.add_weight(
                pet_id=pet.id,
                weight=Decimal("25.0") + Decimal(i),
                recorded_at=date.today() - timedelta(days=i),
            )
        db_session.commit()

        history = repo.get_weight_history(pet.id, limit=10)
        assert len(history) == 5
        # Should be in descending order (most recent first)
        assert history[0].weight > history[-1].weight

    def test_create_condition(self, db_session, pet):
        repo = HealthRepository(db_session)
        condition = repo.create_condition(
            pet_id=pet.id,
            name="Diabetes",
            diagnosis_date=date.today() - timedelta(days=30),
        )
        db_session.commit()

        found = repo.get_condition_by_id(condition.id)
        assert found is not None
        assert found.name == "Diabetes"
        assert found.status == "active"

    def test_get_active_conditions(self, db_session, pet):
        repo = HealthRepository(db_session)
        # Create active condition
        active = TestCondition(
            id=uuid4(),
            pet_id=pet.id,
            name="Allergies",
            diagnosis_date=date.today(),
            status="active",
        )
        # Create resolved condition
        resolved = TestCondition(
            id=uuid4(),
            pet_id=pet.id,
            name="Fever",
            diagnosis_date=date.today() - timedelta(days=10),
            status="resolved",
        )
        db_session.add(active)
        db_session.add(resolved)
        db_session.commit()

        active_conditions = repo.get_active_conditions(pet.id)
        assert len(active_conditions) == 1
        assert active_conditions[0].name == "Allergies"

    def test_count_active_conditions(self, db_session, pet):
        repo = HealthRepository(db_session)
        for i in range(3):
            condition = TestCondition(
                id=uuid4(),
                pet_id=pet.id,
                name=f"Condition{i}",
                diagnosis_date=date.today(),
                status="active",
            )
            db_session.add(condition)
        db_session.commit()

        count = repo.count_active_conditions(pet.id)
        assert count == 3

    def test_add_diagnostic_result(self, db_session, pet):
        repo = HealthRepository(db_session)
        result = repo.add_diagnostic_result(
            pet_id=pet.id,
            test_type="blood_panel",
            test_name="Hemoglobin",
            value_numeric=Decimal("13.5"),
            unit="g/dL",
        )
        db_session.commit()

        found = repo.get_latest_diagnostic_by_type(pet.id, "blood_panel")
        assert found is not None
        assert found.test_name == "Hemoglobin"
        assert found.value_numeric == Decimal("13.5")
