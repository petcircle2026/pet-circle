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

    def find_distinct_food_brands(self) -> List[str]:
        """Find all distinct active food brands."""
        rows = (
            self.db.query(ProductFood.brand_name)
            .filter(ProductFood.active.is_(True))
            .distinct()
            .all()
        )
        return [brand for (brand,) in rows if brand]

    def find_product_lines_by_brand(self, brand_name: str) -> List[str]:
        """Find all distinct product lines for a food brand."""
        rows = (
            self.db.query(ProductFood.product_line)
            .filter(ProductFood.brand_name == brand_name, ProductFood.active.is_(True))
            .distinct()
            .all()
        )
        return [line for (line,) in rows if line]

    def find_active_foods_by_brand(self, brand_name: str) -> List[ProductFood]:
        """Find all active foods for a brand."""
        return (
            self.db.query(ProductFood)
            .filter(ProductFood.brand_name == brand_name, ProductFood.active.is_(True))
            .all()
        )

    def find_active_foods_by_brand_and_line(
        self, brand_name: str, product_line: str
    ) -> List[ProductFood]:
        """Find all active foods for a brand and product line."""
        return (
            self.db.query(ProductFood)
            .filter(
                ProductFood.brand_name == brand_name,
                ProductFood.product_line == product_line,
                ProductFood.active.is_(True),
            )
            .all()
        )

    def find_distinct_supplement_brands(self) -> List[str]:
        """Find all distinct active supplement brands."""
        rows = (
            self.db.query(ProductSupplement.brand_name)
            .filter(ProductSupplement.active.is_(True))
            .distinct()
            .all()
        )
        return [brand for (brand,) in rows if brand]

    def find_active_supplements_by_brand(self, brand_name: str) -> List[ProductSupplement]:
        """Find all active supplements for a brand."""
        return (
            self.db.query(ProductSupplement)
            .filter(ProductSupplement.brand_name == brand_name, ProductSupplement.active.is_(True))
            .all()
        )

    def find_supplement_types_by_brand(self, brand_name: str) -> List[str]:
        """Find all distinct supplement types for a brand."""
        rows = (
            self.db.query(ProductSupplement.type)
            .filter(ProductSupplement.brand_name == brand_name, ProductSupplement.active.is_(True))
            .distinct()
            .all()
        )
        return [stype for (stype,) in rows if stype]

    def find_active_supplements_by_brand_and_type(
        self, brand_name: str, supplement_type: str
    ) -> List[ProductSupplement]:
        """Find all active supplements for a brand and type."""
        return (
            self.db.query(ProductSupplement)
            .filter(
                ProductSupplement.brand_name == brand_name,
                ProductSupplement.type == supplement_type,
                ProductSupplement.active.is_(True),
            )
            .all()
        )

    def find_active_foods_raw(self) -> List[ProductFood]:
        """Find all active foods without in_stock filter (for internal filtering)."""
        return (
            self.db.query(ProductFood)
            .filter(ProductFood.active.is_(True))
            .all()
        )

    def find_active_supplements_raw(self) -> List[ProductSupplement]:
        """Find all active supplements without in_stock filter (for internal filtering)."""
        return (
            self.db.query(ProductSupplement)
            .filter(ProductSupplement.active.is_(True))
            .all()
        )

    def find_medicine_by_name(self, medicine_name: str):
        """Find an active medicine by name (case-insensitive partial match)."""
        from app.models.lookup.product_medicines import ProductMedicines
        return (
            self.db.query(ProductMedicines)
            .filter(
                ProductMedicines.active == True,
                ProductMedicines.product_name.ilike(f"%{medicine_name}%"),
            )
            .first()
        )
