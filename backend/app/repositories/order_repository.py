"""
Order Repository â€” Order and order recommendation access.

Manages:
- Order CRUD
- Order status tracking
- Product recommendations for orders
"""

from uuid import UUID
from typing import List
from datetime import datetime

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.models.commerce.order import Order
from app.models.commerce.order_recommendation import OrderRecommendation


class OrderRepository:
    """Manages order data and order recommendations."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Order CRUD ----

    def find_by_id(self, order_id: UUID) -> Order | None:
        """Fetch an order by ID."""
        return self.db.query(Order).filter(Order.id == order_id).first()

    def find_by_id_with_recommendations(self, order_id: UUID) -> Order | None:
        """Fetch order with eager-loaded recommendations."""
        return (
            self.db.query(Order)
            .filter(Order.id == order_id)
            .options(selectinload(Order.recommendations))
            .first()
        )

    def find_by_pet_id(self, pet_id: UUID) -> List[Order]:
        """Fetch all orders for a pet."""
        return self.db.query(Order).filter(Order.pet_id == pet_id).all()

    def find_by_pet_id_paginated(
        self, pet_id: UUID, skip: int = 0, limit: int = 50
    ) -> tuple[List[Order], int]:
        """Fetch paginated orders for a pet with total count."""
        query = self.db.query(Order).filter(Order.pet_id == pet_id)
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def find_by_user_id(self, user_id: UUID) -> List[Order]:
        """Fetch all orders placed by a user (across all their pets)."""
        return (
            self.db.query(Order)
            .join(Order.pet)
            .filter(Order.pet.user_id == user_id)
            .all()
        )

    def find_by_status(self, status: str) -> List[Order]:
        """
        Find orders by status.

        Args:
            status: e.g. "pending", "confirmed", "completed", "cancelled"

        Returns:
            List of matching orders.
        """
        return self.db.query(Order).filter(Order.status == status).all()

    def find_pending(self) -> List[Order]:
        """Fetch all pending orders."""
        return self.db.query(Order).filter(Order.status == "pending").all()

    def find_by_status_and_pet(
        self, pet_id: UUID, status: str
    ) -> List[Order]:
        """Find orders for a pet with specific status."""
        return (
            self.db.query(Order)
            .filter(Order.pet_id == pet_id, Order.status == status)
            .all()
        )

    def create(self, order: Order) -> Order:
        """Create a new order."""
        self.db.add(order)
        self.db.flush()
        return order

    def update(self, order: Order) -> Order:
        """Update an existing order."""
        self.db.merge(order)
        self.db.flush()
        return order

    def update_status(
        self, order_id: UUID, status: str, admin_notes: str | None = None
    ) -> Order | None:
        """
        Update order status.

        Args:
            order_id: Order ID
            status: New status value
            admin_notes: Optional admin notes

        Returns:
            Updated Order or None if not found.
        """
        order = self.find_by_id(order_id)
        if order:
            order.status = status
            if admin_notes:
                order.admin_notes = admin_notes
            self.db.merge(order)
            self.db.flush()
            return order
        return None

    def delete(self, order_id: UUID) -> bool:
        """
        Delete an order.

        Args:
            order_id: Order ID

        Returns:
            True if found and deleted.
        """
        order = self.find_by_id(order_id)
        if order:
            self.db.delete(order)
            self.db.flush()
            return True
        return False

    def count_by_status(self, status: str) -> int:
        """Count orders with a specific status."""
        return (
            self.db.query(func.count(Order.id))
            .filter(Order.status == status)
            .scalar() or 0
        )

    def count_by_pet(self, pet_id: UUID) -> int:
        """Count total orders for a pet."""
        return (
            self.db.query(func.count(Order.id))
            .filter(Order.pet_id == pet_id)
            .scalar() or 0
        )

    # ---- Order Recommendations ----

    def find_recommendations(self, order_id: UUID) -> List[OrderRecommendation]:
        """Fetch all recommendations for an order."""
        return (
            self.db.query(OrderRecommendation)
            .filter(OrderRecommendation.order_id == order_id)
            .all()
        )

    def find_recommendation_by_id(
        self, recommendation_id: UUID
    ) -> OrderRecommendation | None:
        """Fetch a recommendation by ID."""
        return (
            self.db.query(OrderRecommendation)
            .filter(OrderRecommendation.id == recommendation_id)
            .first()
        )

    def add_recommendation(
        self, recommendation: OrderRecommendation
    ) -> OrderRecommendation:
        """Add a product recommendation to an order."""
        self.db.add(recommendation)
        self.db.flush()
        return recommendation

    def add_recommendations(
        self, recommendations: List[OrderRecommendation]
    ) -> List[OrderRecommendation]:
        """Add multiple recommendations to an order."""
        self.db.add_all(recommendations)
        self.db.flush()
        return recommendations

    def remove_recommendation(self, recommendation_id: UUID) -> bool:
        """
        Remove a recommendation from an order.

        Args:
            recommendation_id: OrderRecommendation ID

        Returns:
            True if found and deleted.
        """
        rec = self.find_recommendation_by_id(recommendation_id)
        if rec:
            self.db.delete(rec)
            self.db.flush()
            return True
        return False

    # ---- Date Filtering ----

    def find_recent_orders(self, pet_id: UUID, days: int = 30) -> List[Order]:
        """Find orders created in the last N days."""
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        return (
            self.db.query(Order)
            .filter(
                Order.pet_id == pet_id,
                Order.created_at >= cutoff,
            )
            .all()
        )

    def find_orders_by_date_range(
        self, pet_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[Order]:
        """Find orders within a date range."""
        return (
            self.db.query(Order)
            .filter(
                Order.pet_id == pet_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
            )
            .all()
        )

    def find_latest_qualifying_order(
        self, pet_id: UUID, product_label: str, qualifying_statuses: tuple[str, ...] = ("confirmed", "completed", "placed", "delivered")
    ) -> Order | None:
        """
        Find the latest order matching pet_id, product label, and status.
        Used by care_plan_engine._check_reorder_status for reorder CTA logic.

        Args:
            pet_id: Pet ID
            product_label: Product name / label to match (case-insensitive)
            qualifying_statuses: Tuple of allowed statuses

        Returns:
            Latest matching Order or None.
        """
        return (
            self.db.query(Order)
            .filter(
                Order.pet_id == pet_id,
                Order.status.in_(qualifying_statuses),
            )
            .filter(
                (Order.product_name.ilike(f"%{product_label}%")) |
                (Order.items_description.ilike(f"%{product_label}%"))
            )
            .order_by(Order.created_at.desc())
            .first()
        )

    def find_recommendation_by_profile(
        self, species: str, breed: str | None, age_range: str, category: str
    ) -> OrderRecommendation | None:
        """
        Find an OrderRecommendation matching species, breed, age_range, and category.
        Used by recommendation_service to check for existing recommendations.

        Args:
            species: Pet species
            breed: Pet breed (nullable)
            age_range: Age range bracket
            category: Recommendation category

        Returns:
            Matching OrderRecommendation or None.
        """
        from sqlalchemy import and_
        return (
            self.db.query(OrderRecommendation)
            .filter(
                and_(
                    OrderRecommendation.species == species,
                    OrderRecommendation.breed == breed,
                    OrderRecommendation.age_range == age_range,
                    OrderRecommendation.category == category,
                )
            )
            .first()
        )

