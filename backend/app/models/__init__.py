"""
PetCircle — SQLAlchemy Models Package

All models are imported here to ensure they are registered with
SQLAlchemy's declarative base. This is required for relationship
resolution and for alembic/migration tooling to discover all tables.

Subpackages:
  app.models.lookup  — seed/config tables (never written at runtime)
  app.models.cache   — write-heavy ephemeral rows (logs, GPT caches)
"""

# ── Active domain models (stay in app/models/) ───────────────────────────────
from app.models.agent_order_session import AgentOrderSession
from app.models.cart_item import CartItem
from app.models.condition import Condition
from app.models.condition_medication import ConditionMedication
from app.models.condition_monitoring import ConditionMonitoring
from app.models.conflict_flag import ConflictFlag
from app.models.contact import Contact
from app.models.custom_preventive_item import CustomPreventiveItem
from app.models.dashboard_token import DashboardToken
from app.models.deferred_care_plan_pending import DeferredCarePlanPending
from app.models.diagnostic_test_result import DiagnosticTestResult
from app.models.diet_item import DietItem
from app.models.document import Document
from app.models.hygiene_preference import HygienePreference
from app.models.message_log import MessageLog
from app.models.nudge import Nudge
from app.models.order import Order
from app.models.order_recommendation import OrderRecommendation
from app.models.pet import Pet
from app.models.pet_ai_insight import PetAiInsight
from app.models.pet_life_stage_trait import PetLifeStageTrait
from app.models.pet_preference import PetPreference
from app.models.preventive_record import PreventiveRecord
from app.models.reminder import Reminder
from app.models.user import User
from app.models.weight_history import WeightHistory

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
