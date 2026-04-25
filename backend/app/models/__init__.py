"""
PetCircle — SQLAlchemy Models Package

All models are imported here to ensure they are registered with
SQLAlchemy's declarative base. This is required for relationship
resolution and for alembic/migration tooling to discover all tables.

Subpackages:
  app.models.lookup  — seed/config tables (never written at runtime)
  app.models.cache   — write-heavy ephemeral rows (logs, GPT caches)
"""

# ── Active domain models (organized by domain) ─────────────────────────────────
from app.models.auth import DashboardToken, Document
from app.models.commerce import AgentOrderSession, CartItem, Order, OrderRecommendation
from app.models.core import Contact, Pet, User
from app.models.health import (
    Condition,
    ConditionMedication,
    ConditionMonitoring,
    ConflictFlag,
    DiagnosticTestResult,
    WeightHistory,
)
from app.models.messaging import MessageLog, Nudge
from app.models.nutrition import DietItem, HygienePreference
from app.models.pet_profile import PetAiInsight, PetLifeStageTrait, PetPreference
from app.models.preventive import (
    CustomPreventiveItem,
    DeferredCarePlanPending,
    PreventiveRecord,
    Reminder,
)

# ── Lookup / seed tables (app/models/lookup/) ─────────────────────────────────
from app.models.lookup import (
    BreedConsequenceLibrary,
    NudgeConfig,
    NudgeMessageLibrary,
    PreventiveMaster,
    ProductFood,
    ProductMedicines,
    ProductSupplement,
    WhatsappTemplateConfig,
)

# ── Cache / log tables (app/models/cache/) ────────────────────────────────────
from app.models.cache import (
    DashboardVisit,
    FoodNutritionCache,
    HygieneTipCache,
    IdealWeightCache,
    NudgeDeliveryLog,
    NudgeEngagement,
    NutritionTargetCache,
)

__all__ = [
    # Domain models
    "AgentOrderSession",
    "CartItem",
    "Condition",
    "ConditionMedication",
    "ConditionMonitoring",
    "ConflictFlag",
    "Contact",
    "CustomPreventiveItem",
    "DashboardToken",
    "DeferredCarePlanPending",
    "DiagnosticTestResult",
    "DietItem",
    "Document",
    "HygienePreference",
    "MessageLog",
    "Nudge",
    "Order",
    "OrderRecommendation",
    "Pet",
    "PetAiInsight",
    "PetLifeStageTrait",
    "PetPreference",
    "PreventiveRecord",
    "Reminder",
    "User",
    "WeightHistory",
    # Lookup
    "BreedConsequenceLibrary",
    "NudgeConfig",
    "NudgeMessageLibrary",
    "PreventiveMaster",
    "ProductFood",
    "ProductMedicines",
    "ProductSupplement",
    "WhatsappTemplateConfig",
    # Cache
    "DashboardVisit",
    "FoodNutritionCache",
    "HygieneTipCache",
    "IdealWeightCache",
    "NudgeDeliveryLog",
    "NudgeEngagement",
    "NutritionTargetCache",
]
