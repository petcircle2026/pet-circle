"""
Integration tests for cart service and cart operations.

Tests: API endpoints for cart, delivery fee calculations, price validation.
Uses real database (in-memory SQLite) to test cart operations.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal, engine, Base
from app.models import User, Pet, Product, CartItem, Order
from app.services.orders.cart_service import (
    get_cart,
    add_to_cart,
    remove_from_cart,
    get_or_create_cart,
    clear_cart,
)
from app.domain.orders.cart_logic import (
    FREE_DELIVERY_THRESHOLD,
    DELIVERY_FEE,
)
from datetime import date


@pytest.fixture(scope="function")
def setup_db():
    """Create tables and yield session, then cleanup."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Provide test client."""
    return TestClient(app)


@pytest.fixture
def test_user_and_pet(setup_db):
    """Create a test user and pet for cart tests."""
    db = setup_db
    user = User(phone_number="9876543210", name="Test User")
    pet = Pet(
        user_id=user.id,
        name="Buddy",
        species="dog",
        breed="Labrador",
        dob=date(2022, 1, 15),
    )
    db.add(user)
    db.add(pet)
    db.commit()
    db.refresh(user)
    db.refresh(pet)
    return user, pet, db


@pytest.fixture
def products_in_db(setup_db):
    """Create test products in database."""
    db = setup_db
    products = [
        Product(
            name="Dog Food Premium",
            sku="DF-001",
            price_inr=250.0,
            category="food",
            quantity_in_stock=50,
        ),
        Product(
            name="Dog Treats",
            sku="DT-002",
            price_inr=150.0,
            category="treats",
            quantity_in_stock=30,
        ),
        Product(
            name="Dog Collar",
            sku="DC-003",
            price_inr=400.0,
            category="accessories",
            quantity_in_stock=20,
        ),
    ]
    for product in products:
        db.add(product)
    db.commit()
    return {p.sku: p for p in products}


class TestGetOrCreateCart:
    """Tests for cart creation/retrieval."""

    def test_get_or_create_new_cart(self, test_user_and_pet):
        """Getting cart for user without one should create it."""
        user, pet, db = test_user_and_pet
        cart = get_or_create_cart(db, user.id)
        assert cart is not None
        assert cart.user_id == user.id

    def test_get_existing_cart(self, test_user_and_pet):
        """Getting cart for user with one should return it."""
        user, pet, db = test_user_and_pet
        cart1 = get_or_create_cart(db, user.id)
        cart2 = get_or_create_cart(db, user.id)
        assert cart1.id == cart2.id


class TestAddToCart:
    """Tests for adding items to cart."""

    def test_add_single_item(self, test_user_and_pet, products_in_db):
        """Adding single item to cart."""
        user, pet, db = test_user_and_pet
        product = list(products_in_db.values())[0]

        cart = add_to_cart(db, user.id, product.sku, quantity=1, price_inr=product.price_inr)
        db.refresh(cart)

        assert len(cart.items) == 1
        assert cart.items[0].quantity == 1
        assert cart.items[0].sku == product.sku

    def test_add_multiple_items(self, test_user_and_pet, products_in_db):
        """Adding multiple different items to cart."""
        user, pet, db = test_user_and_pet
        products = list(products_in_db.values())

        cart = add_to_cart(db, user.id, products[0].sku, quantity=1, price_inr=products[0].price_inr)
        add_to_cart(db, user.id, products[1].sku, quantity=2, price_inr=products[1].price_inr)

        db.refresh(cart)
        assert len(cart.items) == 2

    def test_add_same_item_twice_increments_quantity(self, test_user_and_pet, products_in_db):
        """Adding same item twice should increment quantity."""
        user, pet, db = test_user_and_pet
        product = list(products_in_db.values())[0]

        add_to_cart(db, user.id, product.sku, quantity=1, price_inr=product.price_inr)
        cart = add_to_cart(db, user.id, product.sku, quantity=2, price_inr=product.price_inr)

        db.refresh(cart)
        assert len(cart.items) == 1  # Still 1 item, just more quantity
        assert cart.items[0].quantity == 3  # 1 + 2


class TestRemoveFromCart:
    """Tests for removing items from cart."""

    def test_remove_item_from_cart(self, test_user_and_pet, products_in_db):
        """Removing item should reduce quantity or remove entry."""
        user, pet, db = test_user_and_pet
        product = list(products_in_db.values())[0]

        cart = add_to_cart(db, user.id, product.sku, quantity=3, price_inr=product.price_inr)
        remove_from_cart(db, user.id, product.sku, quantity=1)

        db.refresh(cart)
        assert cart.items[0].quantity == 2

    def test_remove_all_quantity_deletes_item(self, test_user_and_pet, products_in_db):
        """Removing all quantity should delete the cart item."""
        user, pet, db = test_user_and_pet
        product = list(products_in_db.values())[0]

        cart = add_to_cart(db, user.id, product.sku, quantity=2, price_inr=product.price_inr)
        remove_from_cart(db, user.id, product.sku, quantity=2)

        db.refresh(cart)
        assert len(cart.items) == 0


class TestClearCart:
    """Tests for clearing entire cart."""

    def test_clear_cart_removes_all_items(self, test_user_and_pet, products_in_db):
        """Clearing cart should remove all items."""
        user, pet, db = test_user_and_pet
        products = list(products_in_db.values())

        # Add multiple items
        for product in products[:2]:
            add_to_cart(db, user.id, product.sku, quantity=1, price_inr=product.price_inr)

        cart = clear_cart(db, user.id)
        db.refresh(cart)

        assert len(cart.items) == 0


class TestGetCart:
    """Tests for getting cart with summary."""

    def test_get_empty_cart_returns_summary(self, test_user_and_pet):
        """Empty cart should return valid summary."""
        user, pet, db = test_user_and_pet
        cart_response = get_cart(db, user.id)

        assert cart_response is not None
        assert cart_response["summary"]["count"] == 0
        assert cart_response["summary"]["subtotal"] == 0.0
        assert cart_response["summary"]["delivery_fee"] == 0.0
        assert cart_response["summary"]["total"] == 0.0
        assert cart_response["summary"]["free_delivery"] is True

    def test_get_cart_below_free_threshold(self, test_user_and_pet, products_in_db):
        """Cart below 599 INR should include delivery fee."""
        user, pet, db = test_user_and_pet
        product = list(products_in_db.values())[0]  # 250 INR

        add_to_cart(db, user.id, product.sku, quantity=2, price_inr=product.price_inr)
        cart_response = get_cart(db, user.id)

        summary = cart_response["summary"]
        assert summary["subtotal"] == 500.0
        assert summary["delivery_fee"] == DELIVERY_FEE
        assert summary["total"] == 500.0 + DELIVERY_FEE
        assert summary["free_delivery"] is False

    def test_get_cart_above_free_threshold(self, test_user_and_pet, products_in_db):
        """Cart above 599 INR should have no delivery fee."""
        user, pet, db = test_user_and_pet
        products = list(products_in_db.values())
        # 250 + 150 + 400 = 800 INR

        for product in products:
            add_to_cart(db, user.id, product.sku, quantity=1, price_inr=product.price_inr)

        cart_response = get_cart(db, user.id)

        summary = cart_response["summary"]
        assert summary["subtotal"] == 800.0
        assert summary["delivery_fee"] == 0.0
        assert summary["total"] == 800.0
        assert summary["free_delivery"] is True

    def test_get_cart_exactly_at_threshold(self, test_user_and_pet, products_in_db):
        """Cart exactly at 599 INR should have free delivery."""
        user, pet, db = test_user_and_pet
        # Create an item with exact 599 INR price
        product = Product(name="Exact Item", sku="EX-001", price_inr=599.0, category="test")
        db.add(product)
        db.commit()

        add_to_cart(db, user.id, product.sku, quantity=1, price_inr=599.0)
        cart_response = get_cart(db, user.id)

        summary = cart_response["summary"]
        assert summary["subtotal"] == 599.0
        assert summary["delivery_fee"] == 0.0
        assert summary["free_delivery"] is True

    def test_get_cart_just_below_threshold(self, test_user_and_pet, products_in_db):
        """Cart at 598.99 INR should have delivery fee."""
        user, pet, db = test_user_and_pet
        # Create an item with 598.99 INR price
        product = Product(name="Test Item", sku="TE-001", price_inr=598.99, category="test")
        db.add(product)
        db.commit()

        add_to_cart(db, user.id, product.sku, quantity=1, price_inr=598.99)
        cart_response = get_cart(db, user.id)

        summary = cart_response["summary"]
        assert summary["subtotal"] == 598.99
        assert summary["delivery_fee"] == DELIVERY_FEE
        assert summary["free_delivery"] is False

    def test_get_cart_amount_for_free_delivery(self, test_user_and_pet, products_in_db):
        """Cart should show amount needed for free delivery."""
        user, pet, db = test_user_and_pet
        product = list(products_in_db.values())[0]  # 250 INR

        add_to_cart(db, user.id, product.sku, quantity=2, price_inr=product.price_inr)
        cart_response = get_cart(db, user.id)

        summary = cart_response["summary"]
        # Need 599 - 500 = 99 more INR
        assert summary["amount_for_free_delivery"] == 99.0

    def test_get_cart_no_amount_for_free_delivery_when_threshold_crossed(self, test_user_and_pet, products_in_db):
        """Cart already having free delivery should show 0 amount needed."""
        user, pet, db = test_user_and_pet
        products = list(products_in_db.values())

        for product in products:
            add_to_cart(db, user.id, product.sku, quantity=1, price_inr=product.price_inr)

        cart_response = get_cart(db, user.id)

        summary = cart_response["summary"]
        assert summary["amount_for_free_delivery"] == 0.0

    def test_get_cart_item_count(self, test_user_and_pet, products_in_db):
        """Cart should return correct item count."""
        user, pet, db = test_user_and_pet
        products = list(products_in_db.values())

        add_to_cart(db, user.id, products[0].sku, quantity=3, price_inr=products[0].price_inr)
        add_to_cart(db, user.id, products[1].sku, quantity=2, price_inr=products[1].price_inr)

        cart_response = get_cart(db, user.id)

        summary = cart_response["summary"]
        assert summary["count"] == 5  # 3 + 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
