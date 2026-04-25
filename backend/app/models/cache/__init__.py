"""
PetCircle — Cache / Log Table Models

These tables are written heavily by app code (one row per event, per GPT
call, per visit). They are rarely read back except for cache-hit checks
and same-service queries.
"""

from app.models.cache.dashboard_visit import DashboardVisit
from app.models.cache.food_nutrition_cache import FoodNutritionCache
from app.models.cache.hygiene_tip_cache import HygieneTipCache
from app.models.cache.ideal_weight_cache import IdealWeightCache
from app.models.cache.nudge_delivery_log import NudgeDeliveryLog
from app.models.cache.nudge_engagement import NudgeEngagement
from app.models.cache.nutrition_target_cache import NutritionTargetCache

__all__ = [
    "DashboardVisit",
    "FoodNutritionCache",
    "HygieneTipCache",
    "IdealWeightCache",
    "NudgeDeliveryLog",
    "NudgeEngagement",
    "NutritionTargetCache",
]
