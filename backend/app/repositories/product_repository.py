"""
Product Repository — Product catalog access (food and supplements).

Manages access to ProductFood and ProductSupplement catalog tables.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from app.models.lookup.product_food import ProductFood
from app.models.lookup.product_supplement import ProductSupplement


class ProductRepository:
    """Access to product catalogs (food and supplements)."""

    def __init__(self, db: Session):
        self.db = db

    # ---- ProductFood ----

    def find_food_by_sku(self, sku_id: str) -> ProductFood | None:
        """Find a food product by SKU ID."""
        return (
            self.db.query(ProductFood)
            .filter(ProductFood.sku_id == sku_id)
            .first()
        )

    def find_foods_by_type(self, product_type: str) -> List[ProductFood]:
        """Find food products by type."""
        return (
            self.db.query(ProductFood)
            .filter(ProductFood.product_type == product_type)
            .all()
        )

    def find_all_foods(self) -> List[ProductFood]:
        """Find all food products."""
        return self.db.query(ProductFood).all()

    # ---- ProductSupplement ----

    def find_supplement_by_sku(self, sku_id: str) -> ProductSupplement | None:
        """Find a supplement product by SKU ID."""
        return (
            self.db.query(ProductSupplement)
            .filter(ProductSupplement.sku_id == sku_id)
            .first()
        )

    def find_supplements_by_type(self, supplement_type: str) -> List[ProductSupplement]:
        """Find supplement products by type."""
        return (
            self.db.query(ProductSupplement)
            .filter(ProductSupplement.type == supplement_type)
            .all()
        )

    def find_all_supplements(self) -> List[ProductSupplement]:
        """Find all supplement products."""
        return self.db.query(ProductSupplement).all()

    def find_active_supplements(self) -> List[ProductSupplement]:
        """Find all active and in-stock supplement products, ordered by popularity."""
        return (
            self.db.query(ProductSupplement)
            .filter(ProductSupplement.active.is_(True), ProductSupplement.in_stock.is_(True))
            .order_by(ProductSupplement.popularity_rank.asc())
            .all()
        )

    def find_active_foods(self) -> List[ProductFood]:
        """Find all active and in-stock food products, ordered by popularity."""
        return (
            self.db.query(ProductFood)
            .filter(ProductFood.active.is_(True), ProductFood.in_stock.is_(True))
            .order_by(ProductFood.popularity_rank.asc())
            .all()
        )

    def find_foods_query(self):
        """Return a query builder for active and in-stock foods."""
        return (
            self.db.query(ProductFood)
            .filter(ProductFood.active.is_(True), ProductFood.in_stock.is_(True))
        )
