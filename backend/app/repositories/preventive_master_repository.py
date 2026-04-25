"""
PreventiveMaster Repository â€” Read-only reference data access.

Provides access to preventive care standards, product catalogs,
and breed/species lookup tables.
"""

from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from app.models.lookup.preventive_master import PreventiveMaster
from app.models.lookup.product_medicines import ProductMedicines
from app.models.lookup.product_food import ProductFood
from app.models.lookup.product_supplement import ProductSupplement
from app.models.lookup.breed_consequence_library import BreedConsequenceLibrary
from app.models.lookup.nudge_message_library import NudgeMessageLibrary
from app.models.lookup.whatsapp_template_config import WhatsAppTemplateConfig


class PreventiveMasterRepository:
    """Read-only access to preventive care reference data."""

    def __init__(self, db: Session):
        self.db = db

    # ---- PreventiveMaster ----

    def find_by_id(self, master_id: UUID) -> PreventiveMaster | None:
        """Fetch a preventive care standard by ID."""
        return (
            self.db.query(PreventiveMaster)
            .filter(PreventiveMaster.id == master_id)
            .first()
        )

    def find_all(self) -> List[PreventiveMaster]:
        """Fetch all preventive care standards."""
        return self.db.query(PreventiveMaster).all()

    def find_by_species(self, species: str) -> List[PreventiveMaster]:
        """
        Find preventive care standards for a specific species.

        Args:
            species: "dog" or "cat"

        Returns:
            List of applicable preventive standards.
        """
        return (
            self.db.query(PreventiveMaster)
            .filter(PreventiveMaster.species.in_([species, "both"]))
            .all()
        )

    def find_by_category(self, category: str) -> List[PreventiveMaster]:
        """
        Find preventive standards by category.

        Args:
            category: e.g. "vaccine", "deworming", "flea_tick", "checkup"
        """
        return (
            self.db.query(PreventiveMaster)
            .filter(PreventiveMaster.category == category)
            .all()
        )

    def find_by_species_and_category(
        self, species: str, category: str
    ) -> List[PreventiveMaster]:
        """Find preventive standards matching species and category."""
        return (
            self.db.query(PreventiveMaster)
            .filter(
                PreventiveMaster.species.in_([species, "both"]),
                PreventiveMaster.category == category,
            )
            .all()
        )

    # ---- ProductMedicines ----

    def find_medicine_by_id(self, medicine_id: UUID) -> ProductMedicines | None:
        """Fetch a medicine/vaccine by ID."""
        return (
            self.db.query(ProductMedicines)
            .filter(ProductMedicines.id == medicine_id)
            .first()
        )

    def find_medicines_by_type(self, medicine_type: str) -> List[ProductMedicines]:
        """
        Find medicines/vaccines by type.

        Args:
            medicine_type: e.g. "vaccine", "dewormer", "supplement"
        """
        return (
            self.db.query(ProductMedicines)
            .filter(ProductMedicines.type == medicine_type)
            .all()
        )

    def find_medicine_by_name(self, name: str) -> ProductMedicines | None:
        """Find a medicine by exact name match."""
        return (
            self.db.query(ProductMedicines)
            .filter(ProductMedicines.name == name)
            .first()
        )

    # ---- ProductFood ----

    def find_food_by_id(self, food_id: UUID) -> ProductFood | None:
        """Fetch a food product by ID."""
        return self.db.query(ProductFood).filter(ProductFood.id == food_id).first()

    def find_foods_by_species(self, species: str) -> List[ProductFood]:
        """Find foods suitable for a specific species."""
        return (
            self.db.query(ProductFood)
            .filter(ProductFood.suitable_for.in_([species, "both"]))
            .all()
        )

    def find_food_by_name(self, name: str) -> ProductFood | None:
        """Find a food product by exact name match."""
        return self.db.query(ProductFood).filter(ProductFood.name == name).first()

    # ---- ProductSupplement ----

    def find_supplement_by_id(self, supplement_id: UUID) -> ProductSupplement | None:
        """Fetch a supplement by ID."""
        return (
            self.db.query(ProductSupplement)
            .filter(ProductSupplement.id == supplement_id)
            .first()
        )

    def find_supplements_by_type(
        self, supplement_type: str
    ) -> List[ProductSupplement]:
        """
        Find supplements by type.

        Args:
            supplement_type: e.g. "joint_health", "coat_care", "digestion"
        """
        return (
            self.db.query(ProductSupplement)
            .filter(ProductSupplement.type == supplement_type)
            .all()
        )

    def find_supplement_by_name(self, name: str) -> ProductSupplement | None:
        """Find a supplement by exact name match."""
        return (
            self.db.query(ProductSupplement)
            .filter(ProductSupplement.name == name)
            .first()
        )

    # ---- BreedConsequenceLibrary ----

    def find_breed_consequence(
        self, breed: str, category: str
    ) -> BreedConsequenceLibrary | None:
        """Find the breed-specific consequence row for a given breed and category."""
        return (
            self.db.query(BreedConsequenceLibrary)
            .filter(
                BreedConsequenceLibrary.breed == breed,
                BreedConsequenceLibrary.category == category,
            )
            .first()
        )

    def find_generic_consequence(self, category: str) -> BreedConsequenceLibrary | None:
        """Find the generic (breed='Other') consequence row for a category."""
        return (
            self.db.query(BreedConsequenceLibrary)
            .filter(
                BreedConsequenceLibrary.breed == "Other",
                BreedConsequenceLibrary.category == category,
            )
            .first()
        )

    def find_breed_consequences(self, breed: str) -> List[BreedConsequenceLibrary]:
        """
        Find breed-specific health consequences and predispositions.

        Args:
            breed: The pet breed name

        Returns:
            List of health conditions this breed is prone to.
        """
        return (
            self.db.query(BreedConsequenceLibrary)
            .filter(BreedConsequenceLibrary.breed == breed)
            .all()
        )

    # ---- NudgeMessageLibrary ----

    def find_nudge_messages(
        self, level: int | None = None, breed: str | None = None
    ) -> List[NudgeMessageLibrary]:
        """
        Find nudge messages by level and/or breed.

        Args:
            level: Nudge engagement level (0-5) or None for all
            breed: Breed filter or None for all (including "All")

        Returns:
            List of applicable nudge messages.
        """
        query = self.db.query(NudgeMessageLibrary)

        if level is not None:
            query = query.filter(NudgeMessageLibrary.level == level)

        if breed is not None:
            query = query.filter(NudgeMessageLibrary.breed.in_([breed, "All"]))

        return query.all()

    def find_nudge_message_by_category(
        self, category: str, level: int
    ) -> NudgeMessageLibrary | None:
        """Find nudge message for a specific category and level."""
        return (
            self.db.query(NudgeMessageLibrary)
            .filter(
                NudgeMessageLibrary.category == category,
                NudgeMessageLibrary.level == level,
            )
            .first()
        )

    # ---- WhatsAppTemplateConfig ----

    def find_template_by_name(
        self, template_name: str
    ) -> WhatsAppTemplateConfig | None:
        """
        Fetch WhatsApp message template by name.

        Args:
            template_name: e.g. "reminder_vaccine", "nudge_diet"

        Returns:
            Template config or None if not found.
        """
        return (
            self.db.query(WhatsAppTemplateConfig)
            .filter(WhatsAppTemplateConfig.template_name == template_name)
            .first()
        )

    def find_all_templates(self) -> List[WhatsAppTemplateConfig]:
        """Fetch all WhatsApp message templates."""
        return self.db.query(WhatsAppTemplateConfig).all()

    def find_nudge_message_by_type(
        self, level: int, message_type: str, breed: str
    ) -> NudgeMessageLibrary | None:
        """Find the first nudge message matching level, type, and breed."""
        return (
            self.db.query(NudgeMessageLibrary)
            .filter(
                NudgeMessageLibrary.level == level,
                NudgeMessageLibrary.message_type == message_type,
                NudgeMessageLibrary.breed == breed,
            )
            .order_by(NudgeMessageLibrary.seq.asc())
            .first()
        )

    def find_nudge_message_by_type_and_category(
        self, level: int, message_type: str, breed: str, category: str
    ) -> NudgeMessageLibrary | None:
        """Find a nudge message matching level, type, breed, and category."""
        return (
            self.db.query(NudgeMessageLibrary)
            .filter(
                NudgeMessageLibrary.level == level,
                NudgeMessageLibrary.message_type == message_type,
                NudgeMessageLibrary.breed == breed,
                NudgeMessageLibrary.category == category,
            )
            .first()
        )

    def find_nudge_message_by_offset(
        self, level: int, breed: str, offset: int
    ) -> NudgeMessageLibrary | None:
        """Find a nudge message at a specific offset (for slot cycling)."""
        return (
            self.db.query(NudgeMessageLibrary)
            .filter(
                NudgeMessageLibrary.level == level,
                NudgeMessageLibrary.breed == breed,
            )
            .order_by(NudgeMessageLibrary.seq.asc())
            .offset(offset)
            .first()
        )

    def count_nudge_messages(self, level: int, breed: str) -> int:
        """Count nudge messages for a level and breed."""
        from sqlalchemy import func
        return (
            self.db.query(func.count(NudgeMessageLibrary.id))
            .filter(
                NudgeMessageLibrary.level == level,
                NudgeMessageLibrary.breed == breed,
            )
            .scalar() or 0
        )

    def find_medicines_by_life_stage(self, species: str) -> List[ProductMedicines]:
        """Find medicines/products with life_stage_tags matching a species."""
        return (
            self.db.query(ProductMedicines)
            .filter(
                ProductMedicines.active == True,
                ProductMedicines.life_stage_tags.ilike(f"%{species}%"),
            )
            .all()
        )

    def find_medicine_by_name_ilike(self, name: str) -> ProductMedicines | None:
        """Find active medicine by partial name match (for warning lookup)."""
        from app.models.lookup.product_medicines import ProductMedicines
        return (
            self.db.query(ProductMedicines)
            .filter(
                ProductMedicines.active == True,
                ProductMedicines.product_name.ilike(f"%{name}%"),
            )
            .first()
        )

    def find_mandatory_by_species(self, species: str) -> List[PreventiveMaster]:
        """
        Find mandatory preventive items for a species.
        Used by care_plan_engine to inject phantom entries for Quick Fixes.

        Args:
            species: "dog", "cat", or species to filter (includes "both")

        Returns:
            List of mandatory PreventiveMaster items.
        """
        return (
            self.db.query(PreventiveMaster)
            .filter(
                PreventiveMaster.is_mandatory == True,
                PreventiveMaster.species.in_([species, "both"]),
            )
            .all()
        )

    def find_product_medicines_with_repeat_frequency(self) -> List[tuple]:
        """
        Fetch (product_name, repeat_frequency) pairs for all medicines.
        Used by care_plan_engine to map medicines to human-readable frequencies.

        Returns:
            List of (product_name, repeat_frequency) tuples.
        """
        return (
            self.db.query(ProductMedicines.product_name, ProductMedicines.repeat_frequency)
            .filter(ProductMedicines.repeat_frequency.isnot(None))
            .all()
        )

    def find_all_active_medicines(self) -> List[ProductMedicines]:
        """
        Fetch all active product medicines.
        Used by gpt_extraction to build medicine mapping cache.

        Returns:
            List of active ProductMedicines.
        """
        return (
            self.db.query(ProductMedicines)
            .filter(ProductMedicines.active == True)
            .all()
        )

    def find_preventive_master_by_name_ilike(self, name: str) -> PreventiveMaster | None:
        """
        Find preventive master item by partial name match (case-insensitive).
        Used by gpt_extraction for duplicate detection.

        Args:
            name: Product name to search (partial match)

        Returns:
            First matching PreventiveMaster or None.
        """
        return (
            self.db.query(PreventiveMaster)
            .filter(PreventiveMaster.item_name.ilike(f"%{name}%"))
            .first()
        )

