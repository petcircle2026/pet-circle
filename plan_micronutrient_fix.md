# Plan: Fix Raw Micronutrient Keys in Quick Fixes Section

## Context

The Quick Fixes ("add" bucket) shows supplement recommendations from nutrition analysis. Currently:
- Raw LLM keys like `omega_3`, `glucosamine` are naively capitalized → "Omega_3 Supplement" (underscore stays)
- `severity_score` is stripped in `get_diet_summary()` before reaching the recommendation injector, so low-severity deficiencies can't be filtered
- All top-3 gaps become supplement items regardless of relevance

The fix: use `SUPPLEMENT_TYPE_KEYWORDS` (signal_resolver.py) to map each micronutrient key → the canonical DB `type` string (e.g., `omega_3` → `fish_oil`), then humanize that type string by splitting on underscores and title-casing. This derives labels directly from the `product_supplement.type` values in the DB — no hardcoded display map.

---

## Label Derivation (DB-driven)

```
micronutrient key
    → longest-keyword match in SUPPLEMENT_TYPE_KEYWORDS
    → canonical DB type (e.g. "fish_oil", "joint_supplement")
    → " ".join(w.title() for w in type.split("_"))
    → "Fish Oil" / "Joint Supplement"
    → f"{label} Supplement"
```

| Micronutrient | Keyword → DB type | Final label |
|---|---|---|
| `omega_3` | `"omega"` → `fish_oil` | Fish Oil Supplement |
| `omega_6` | `"omega"` → `fish_oil` | Fish Oil Supplement |
| `glucosamine` | `"glucosamine"` → `joint_supplement` | Joint Supplement |
| `vitamin_d3` | `"vitamin"` → `multivitamin` | Multivitamin Supplement |
| `vitamin_e` | `"vitamin"` → `multivitamin` | Multivitamin Supplement |
| `calcium` | `"calcium"` → `bone_supplement` | Bone Supplement |
| `phosphorus` | `"phosphorus"` → `bone_supplement` | Bone Supplement |
| `probiotics` | `"probiotic"` → `probiotic` | Probiotic Supplement |
| `iron` | no match → fallback | Iron Supplement |
| `zinc` | no match → fallback | Zinc Supplement |
| `taurine` | no match → fallback | Taurine Supplement |

Fallback (no keyword match): humanize the raw micronutrient key itself using the same split/title logic.

---

## Changes

### 1. `nutrition_service.py` → `get_diet_summary()` (~line 1327)

Add `severity_score` to each `missing_micros` entry:

```python
# Before
missing_micros = [
    {"icon": _MICRO_ICONS.get(g["name"], "⚠️"), "name": g["name"], "reason": None, "supplement": None}
    for g in deficient[:3]
]

# After
missing_micros = [
    {
        "icon": _MICRO_ICONS.get(g["name"], "⚠️"),
        "name": g["name"],
        "reason": None,
        "supplement": None,
        "severity_score": g.get("severity_score", 0.0),
    }
    for g in deficient[:3]
]
```

---

### 2. `dashboard_service.py` → `_inject_supplement_recommendations()` (lines 315–363)

**a) Add import at top of file:**
```python
from app.services.dashboard.signal_resolver import SUPPLEMENT_TYPE_KEYWORDS
```

**b) Add module-level constants above the function:**
```python
_SUPPLEMENT_SEVERITY_THRESHOLD = 0.4  # exclude low-relevance deficiencies
_MAX_SUPPLEMENT_ITEMS = 2             # cap Quick Fixes supplement cards
```

**c) Add helper function above `_inject_supplement_recommendations`:**
```python
def _supplement_display_name(nutrient_name: str) -> str:
    """Derive a user-facing supplement label from a raw micronutrient key.

    Maps: nutrient key → canonical product_supplement.type (via SUPPLEMENT_TYPE_KEYWORDS)
    → humanized label (underscores → spaces, title-cased)
    → "<Label> Supplement"
    """
    if not nutrient_name:
        return "Supplement"
    lowered = nutrient_name.replace("_", " ").lower()
    # Longest-keyword match → canonical DB type
    matched_type: str | None = None
    best_len = 0
    for kw, ptype in SUPPLEMENT_TYPE_KEYWORDS.items():
        if kw in lowered and len(kw) > best_len:
            matched_type = ptype
            best_len = len(kw)
    base = matched_type or nutrient_name  # fallback: use raw key
    label = " ".join(w.title() for w in base.split("_"))
    # Avoid double "Supplement" if type already ends with it
    if label.lower().endswith("supplement"):
        return label
    return f"{label} Supplement"
```

**d) Updated loop in `_inject_supplement_recommendations` — severity filter + item cap + clean label:**
```python
supplement_items = []
for micro in missing_micros:
    if len(supplement_items) >= _MAX_SUPPLEMENT_ITEMS:
        break
    nutrient_name = micro.get("name", "")
    severity = micro.get("severity_score", 0.0)
    if severity < _SUPPLEMENT_SEVERITY_THRESHOLD:
        continue
    item_name = _supplement_display_name(nutrient_name)
    supplement_items.append({
        "name": item_name,
        "test_type": "supplement",
        "freq": "Daily",
        "next_due": None,
        "status_tag": "Recommended",
        "classification": "suggested",
        "reason": micro.get("reason") or None,
        "orderable": True,
        "cta_label": "Order Now",
        "micronutrient": nutrient_name,   # unchanged — product resolver uses this
    })
```

---

### 3. Frontend — no changes needed

- `CarePlanCard.tsx` (lines 165–171): only appends "Supplement" if name doesn't already end with it — clean backend names pass through correctly
- `micronutrient` field is unchanged → "Order Now" product resolution via `/products/resolve-by-micronutrient` works as before

---

## Critical Files

| File | Function | Change |
|---|---|---|
| `backend/app/services/dashboard/nutrition_service.py` | `get_diet_summary()` ~line 1327 | Add `severity_score` to `missing_micros` |
| `backend/app/services/dashboard/dashboard_service.py` | `_inject_supplement_recommendations()` lines 315–363 | Import, constants, helper, severity filter, item cap, clean label |

## Reused Utilities

- `SUPPLEMENT_TYPE_KEYWORDS` (signal_resolver.py line 802) — imported directly; maps keyword → canonical DB type
- `missing_micros` already sorted by severity desc in `get_diet_summary()` — severity threshold is a secondary quality gate

---

## Verification

1. Run backend: `make dev`
2. Open dashboard for a pet with diet items and micronutrient gaps
3. Quick Fixes shows at most 2 supplement cards
4. Labels are clean: "Fish Oil Supplement", "Joint Supplement", etc. — no raw keys or underscores
5. Gaps with severity < 0.4 are excluded
6. "Order Now" still resolves products correctly
7. Run tests: `cd backend && APP_ENV=test pytest tests/ -v`
