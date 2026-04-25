import os

os.environ.setdefault("APP_ENV", "test")

from app.services.dashboard.health_trends_service import _classify_preventive_item
from app.services.admin.nudge_engine import _classify_item as classify_nudge_item
from app.services.admin.reminder_engine import _classify_item as classify_reminder_item


def test_kennel_cough_is_classified_as_vaccine_everywhere() -> None:
    item_name = "Kennel Cough (Nobivac KC)"

    assert classify_nudge_item(item_name) == "vaccine"
    assert classify_reminder_item(item_name) == "vaccine"
    assert _classify_preventive_item(item_name) == "vaccine"


def test_ccov_is_classified_as_vaccine_everywhere() -> None:
    item_name = "Canine Coronavirus (CCoV)"

    assert classify_nudge_item(item_name) == "vaccine"
    assert classify_reminder_item(item_name) == "vaccine"
    assert _classify_preventive_item(item_name) == "vaccine"
