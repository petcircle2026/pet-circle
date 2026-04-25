"""
Unit tests for cart_logic (pure functions, no DB).

Tests: calculation, validation, minimum order checks.
"""

import pytest
from app.domain.orders.cart_logic import (
    CartSummary,
    calculate_cart_summary,
    calculate_delivery_fee,
    is_valid_quantity,
    is_valid_price,
    meets_minimum_order,
    FREE_DELIVERY_THRESHOLD,
    DELIVERY_FEE,
)


class TestDeliveryFee:
    """Tests for delivery fee calculation."""

    def test_free_delivery_threshold(self):
        """Free delivery for orders >= 599 INR."""
        # 599 INR = 59900 paise
        fee = calculate_delivery_fee(59900)
        assert fee == 0

    def test_paid_delivery_below_threshold(self):
        """Paid delivery for orders < 599 INR."""
        # 500 INR = 50000 paise
        fee = calculate_delivery_fee(50000)
        assert fee == DELIVERY_FEE * 100  # Convert to paise

    def test_paid_delivery_exact_before_threshold(self):
        """Paid delivery for orders exactly 1 paise below threshold."""
        # 59899 paise = 598.99 INR
        fee = calculate_delivery_fee(59899)
        assert fee == DELIVERY_FEE * 100

    def test_free_delivery_large_order(self):
        """Free delivery for large orders."""
        # 10000 INR = 1000000 paise
        fee = calculate_delivery_fee(1000000)
        assert fee == 0


class TestCartSummary:
    """Tests for cart summary calculations."""

    def test_empty_cart(self):
        """Empty cart should return zeros."""
        summary = calculate_cart_summary([])
        assert summary.item_count == 0
        assert summary.subtotal_paise == 0
        assert summary.subtotal_inr == 0.0
        assert summary.total_paise == 0
        assert summary.free_delivery is True

    def test_single_item_below_free_threshold(self):
        """Cart with single item below free delivery."""
        items = [
            {"price_paise": 50000, "quantity": 1}  # 500 INR
        ]
        summary = calculate_cart_summary(items)
        assert summary.item_count == 1
        assert summary.subtotal_paise == 50000
        assert summary.subtotal_inr == 500.0
        assert summary.delivery_fee_inr == 49.0
        assert summary.total_inr == 549.0
        assert summary.free_delivery is False

    def test_multiple_items_with_free_delivery(self):
        """Cart with multiple items triggering free delivery."""
        items = [
            {"price_paise": 50000, "quantity": 2},  # 1000 INR (2 items)
            {"price_paise": 10000, "quantity": 1},  # 100 INR (1 item)
        ]
        summary = calculate_cart_summary(items)
        assert summary.item_count == 3  # 2 + 1
        assert summary.subtotal_inr == 1100.0
        assert summary.delivery_fee_inr == 0.0
        assert summary.total_inr == 1100.0
        assert summary.free_delivery is True

    def test_cart_rounding(self):
        """Verify proper rounding to 2 decimal places."""
        items = [
            {"price_paise": 33333, "quantity": 1}  # 333.33 INR
        ]
        summary = calculate_cart_summary(items)
        assert summary.subtotal_inr == 333.33
        assert summary.total_inr == 382.33  # 333.33 + 49


class TestQuantityValidation:
    """Tests for quantity validation."""

    def test_valid_quantities(self):
        for qty in [1, 2, 5, 10]:
            valid, msg = is_valid_quantity(qty)
            assert valid is True
            assert msg == ""

    def test_zero_quantity(self):
        valid, msg = is_valid_quantity(0)
        assert valid is False
        assert "at least 1" in msg

    def test_negative_quantity(self):
        valid, msg = is_valid_quantity(-5)
        assert valid is False

    def test_quantity_exceeds_max(self):
        valid, msg = is_valid_quantity(11)
        assert valid is False
        assert "Maximum" in msg

    def test_non_integer_quantity(self):
        valid, msg = is_valid_quantity("5")
        assert valid is False
        assert "integer" in msg


class TestPriceValidation:
    """Tests for price validation."""

    def test_valid_prices(self):
        for price in [100, 50000, 1000000]:
            valid, msg = is_valid_price(price)
            assert valid is True
            assert msg == ""

    def test_zero_price(self):
        valid, msg = is_valid_price(0)
        assert valid is False
        assert "positive" in msg

    def test_negative_price(self):
        valid, msg = is_valid_price(-100)
        assert valid is False

    def test_price_unreasonably_high(self):
        valid, msg = is_valid_price(11_000_000)  # > 100k INR
        assert valid is False
        assert "unreasonably high" in msg

    def test_non_integer_price(self):
        valid, msg = is_valid_price(99.99)
        assert valid is False
        assert "integer" in msg


class TestMinimumOrder:
    """Tests for minimum order requirement."""

    def test_meets_minimum(self):
        # Minimum is 99 INR = 9900 paise
        meets, shortfall = meets_minimum_order(10000)  # 100 INR
        assert meets is True
        assert shortfall == 0

    def test_exact_minimum(self):
        meets, shortfall = meets_minimum_order(9900)  # Exactly 99 INR
        assert meets is True
        assert shortfall == 0

    def test_below_minimum(self):
        meets, shortfall = meets_minimum_order(5000)  # 50 INR
        assert meets is False
        assert shortfall > 0

    def test_shortfall_calculation(self):
        meets, shortfall = meets_minimum_order(5000)  # 50 INR
        assert shortfall == 4900  # Need 49 more INR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

