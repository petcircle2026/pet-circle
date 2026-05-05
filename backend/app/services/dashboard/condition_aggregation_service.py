"""
PetCircle — Condition Aggregation Service

Groups document-level Condition rows for a pet into complaint families using
the 5-step similarity algorithm (body system + symptom sub-pattern), then
merges them into AggregatedCondition rows.

Entry point:
    await aggregate_conditions_for_pet(db, pet_id)

Also exports:
    is_medication_active(med, condition) — Sheet 6 Fix B: computed from end_date
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import List, Any
from uuid import UUID, uuid4

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ─── Recurrence thresholds (Sheet 2) ─────────────────────────────────────────
_RECURRENCE_2_IN_MONTHS = 15   # ≥2 episodes within 15 months → recurrent
_RECURRENCE_3_IN_MONTHS = 24   # ≥3 episodes within 24 months → recurrent

# ─── Condition type rank (highest wins on merge) ──────────────────────────────
_TYPE_RANK: dict[str, int] = {"chronic": 3, "recurrent": 2, "episodic": 1, "resolved": 0}

# ─── Chronic trigger lists (Sheet 1) ─────────────────────────────────────────
_CHRONIC_CONDITION_NAMES: frozenset[str] = frozenset({
    "hypothyroidism", "hyperthyroidism", "diabetes", "diabetes mellitus",
    "ckd", "chronic kidney disease", "renal failure", "cardiac disease",
    "heart disease", "epilepsy", "addison", "addison's disease", "cushing",
    "cushing's disease", "incontinence", "ibd", "inflammatory bowel disease",
    "liver disease", "megaoesophagus",
})
_CHRONIC_DRUG_NAMES: frozenset[str] = frozenset({
    "thyroxine", "levothyroxine", "insulin", "enalapril", "furosemide",
    "phenobarbitone", "phenobarbital", "potassium bromide", "trilostane",
    "fludrocortisone", "benazepril", "pimobendan",
})

# ─── Body system keyword maps (Sheet 2 Step 2) ───────────────────────────────
_BODY_SYSTEM_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("gastrointestinal", ("vomit", "loose stool", "diarrh", "colitis", "gi upset",
                          "gastroenteritis", "gastrointestinal", "gastro", "hge", "ibd",
                          "gastritis", "constipat", "flatulen", "malabsorpt", "pancreatit",
                          "liver disease", "hepatitis", "bile", "enteritis", "nausea",
                          "regurgitat", "inappeten", "anorexia", "haematemesis", "melaena")),
    ("urinary", ("uti", "urinary tract", "cystitis", "strain", "haematuria", "hematuria",
                 "incontinence", "stones", "crystal", "kidney", "ckd", "renal",
                 "nephritis", "proteinuria", "ecoli", "e.coli")),
    ("skin", ("pyoderma", "fungal", "dermatitis", "allergy", "hot spot", "mange",
              "ringworm", "alopecia", "itch", "pruritus", "seborrhoea", "ear mite",
              "otitis", "ear discharge", "ear infection")),
    ("respiratory", ("cough", "kennel cough", "pharyngitis", "tonsillitis",
                     "bronchitis", "pneumonia", "upper respiratory", "nasal discharge",
                     "sneez", "reverse sneeze", "tracheal")),
    ("musculoskeletal", ("lame", "arthritis", "joint pain", "ligament", "cruciate",
                         "hip dysplasia", "fracture", "sprain", "muscle pain",
                         "ivdd", "spondylosis")),
    ("endocrine", ("hypothyroid", "hyperthyroid", "diabetes", "cushing", "addison",
                   "thyroid", "insulin", "adrenal")),
    ("cardiac", ("heart disease", "cardiac", "murmur", "cardiomyopathy", "chf",
                 "arrhythmia", "pericardial")),
    ("neurological", ("seizure", "epilepsy", "tremor", "ataxia", "vestibular",
                      "paralysis", "disc disease", "cognitive dysfunction")),
    ("haematological", ("anaemia", "anemia", "thrombocytopenia", "tick fever",
                        "ehrlichia", "anaplasma", "babesia", "platelet",
                        "haemoparasite")),
    ("ophthalmological", ("eye infection", "conjunctivit", "uveitis", "cataract",
                          "corneal ulcer", "eye discharge", "cherry eye")),
    ("reproductive", ("pyometra", "prostatic", "mammary", "testicular", "ovarian",
                      "whelping")),
    ("nutritional", ("weight loss", "obesity", "malnutrition", "vitamin deficiency",
                     "hypoalbuminaemia")),
    ("dental", ("dental", "periodontal", "tooth resorpt", "gingivitis", "stomatitis")),
    ("oncological", ("tumour", "tumor", "cancer", "mass", "lymphoma", "mast cell",
                     "lipoma", "carcinoma", "sarcoma")),
]

# ─── Symptom sub-patterns within systems (Sheet 2 Step 3) ────────────────────
_SUB_PATTERNS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "gastrointestinal": [
        ("upper_gi", ("vomit",)),
        ("lower_gi", ("diarrh", "loose stool", "colitis")),
        ("hepatic", ("liver", "bile", "pancreatit", "hepatitis")),
    ],
    "urinary": [
        ("lower_urinary", ("uti", "cystitis", "crystal", "strain", "haematuria",
                           "hematuria", "ecoli", "e.coli")),
        ("upper_urinary", ("kidney", "ckd", "renal", "nephritis", "proteinuria")),
        ("incontinence", ("incontinence",)),
    ],
    "skin": [
        ("infection", ("pyoderma", "fungal", "ringworm")),
        ("allergic", ("dermatitis", "pruritus", "itch", "hot spot", "allergy")),
        ("ear", ("otitis", "ear mite", "ear discharge", "ear infection")),
        ("parasitic", ("mange",)),
    ],
    "respiratory": [
        ("upper", ("pharyngitis", "nasal", "sneez", "tonsillitis")),
        ("lower", ("cough", "bronchitis", "pneumonia")),
    ],
    "musculoskeletal": [
        ("joint", ("arthritis", "hip dysplasia", "cruciate", "joint pain")),
        ("spinal", ("ivdd", "spondylosis", "disc")),
        ("soft_tissue", ("sprain", "muscle", "lame", "fracture")),
    ],
}

# ─── Dosage/route words to strip during name normalization ────────────────────
_STRIP_WORDS: frozenset[str] = frozenset({
    "mg", "ml", "tablet", "tablets", "tab", "tabs", "capsule", "capsules",
    "cap", "caps", "injection", "inj", "oral", "topical", "cream", "drop",
    "drops", "solution", "suspension", "syrup", "powder", "spray",
    "per", "day", "daily", "twice", "once", "bid", "tid", "sid",
    "week", "weekly", "month", "monthly",
})


# ─────────────────────────────────────────────────────────────────────────────
# Public helper: medication active status (Sheet 6 Fix B)
# ─────────────────────────────────────────────────────────────────────────────

def is_medication_active(med: Any, condition: Any) -> bool:
    """
    Compute whether a medication is currently active.

    Rules (Sheet 6):
      - end_date is NOT null AND end_date >= today → active
      - end_date is NOT null AND end_date < today  → inactive
      - end_date is null AND (today - latest_episode_date) <= 30 days → active
      - end_date is null AND (today - latest_episode_date) > 30 days  → inactive
    """
    today = date.today()
    if med.end_date is not None:
        return med.end_date >= today

    episode_dates: list[str] = getattr(condition, "episode_dates", None) or []
    if episode_dates:
        try:
            from app.utils.date_utils import parse_date
            latest_date = parse_date(max(episode_dates))
            return (today - latest_date).days <= 30
        except Exception:
            pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Condition status computation (Sheet 1)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_condition_status(
    condition_type: str,
    medication_end_date: date | None,
    episode_dates: list[str],
    recurrence_watch: bool = False,
) -> str:
    """Compute condition_status from type, medication end_date, and episode_dates."""
    today = date.today()

    if condition_type == "chronic":
        return "active"

    # recurrence_watch = one episode seen, watching for second → always monitoring
    if recurrence_watch:
        return "monitoring"

    if medication_end_date is not None:
        if medication_end_date >= today:
            return "active"
        days_since_end = (today - medication_end_date).days
        if days_since_end <= 30:
            return "monitoring"
        # Recurrent conditions with multiple episodes stay monitoring longer
        # so the insight engine can surface the pattern.
        if condition_type == "recurrent" and len(episode_dates) > 1 and days_since_end <= 90:
            return "monitoring"
        return "resolved"

    # No medication ever recorded — condition was never formally treated or
    # vet-confirmed resolved. Keep as monitoring with a long window so untreated
    # conditions remain visible to the insight engine.
    if episode_dates:
        try:
            from app.utils.date_utils import parse_date
            latest = parse_date(max(episode_dates))
            days_ago = (today - latest).days
            window = 365 if condition_type in ("episodic", "recurrent") else 30
            if days_ago <= window:
                return "monitoring"
        except Exception:
            pass

    return "resolved"


# ─────────────────────────────────────────────────────────────────────────────
# Name normalization (Sheet 2 Step 1)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Strip dosage/route words and lowercase."""
    parts = name.lower().strip().split()
    kept = [p for p in parts if p not in _STRIP_WORDS and not p.replace(".", "").isdigit()]
    return " ".join(kept).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Body system detection (Sheet 2 Step 2)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_body_system(normalized_name: str) -> str:
    """Return body system string for a normalized condition name."""
    for system, keywords in _BODY_SYSTEM_KEYWORDS:
        if any(kw in normalized_name for kw in keywords):
            return system
    return "other"


# ─────────────────────────────────────────────────────────────────────────────
# Sub-pattern detection (Sheet 2 Step 3)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_sub_pattern(system: str, normalized_name: str) -> str | None:
    """Return sub-pattern within the body system, or None if no sub-grouping."""
    patterns = _SUB_PATTERNS.get(system)
    if not patterns:
        return None
    for sub_name, keywords in patterns:
        if any(kw in normalized_name for kw in keywords):
            return sub_name
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Similarity decision (Sheet 2 Step 4)
# ─────────────────────────────────────────────────────────────────────────────

def _same_family(norm_a: str, sys_a: str, sub_a: str | None,
                 norm_b: str, sys_b: str, sub_b: str | None) -> bool:
    """Return True if two conditions belong to the same complaint family."""
    if norm_a == norm_b:
        return True
    if sys_a != sys_b:
        return False
    # "other" conditions only group if their names are identical — otherwise every
    # unclassified condition would collapse into one family incorrectly.
    if sys_a == "other":
        return False
    # Same system — check sub-pattern
    if sub_a is None or sub_b is None:
        # No sub-grouping defined for this system → same system = same family
        return True
    return sub_a == sub_b


# ─────────────────────────────────────────────────────────────────────────────
# Recurrence threshold check (Sheet 2 Step 5)
# ─────────────────────────────────────────────────────────────────────────────

def _apply_recurrence_threshold(episode_dates: list[str]) -> tuple[str, bool]:
    """
    Return (condition_type, recurrence_watch) based on merged episode_dates.

    condition_type is only upgraded to "recurrent" here for episodic/recurrent
    families. Chronic families are always "chronic".
    """
    if len(episode_dates) < 2:
        return "episodic", True  # 1 episode: watch for recurrence

    try:
        from app.utils.date_utils import parse_date
        parsed = sorted(parse_date(d) for d in episode_dates)
    except Exception:
        return "episodic", False

    today = date.today()
    cutoff_15m = today - timedelta(days=_RECURRENCE_2_IN_MONTHS * 30)
    cutoff_24m = today - timedelta(days=_RECURRENCE_3_IN_MONTHS * 30)

    recent_2 = [d for d in parsed if d >= cutoff_15m]
    recent_3 = [d for d in parsed if d >= cutoff_24m]

    if len(recent_2) >= 2 or len(recent_3) >= 3:
        return "recurrent", False

    return "episodic", False


# ─────────────────────────────────────────────────────────────────────────────
# Chronic override (Sheet 1)
# ─────────────────────────────────────────────────────────────────────────────

def _is_chronic_by_name_or_drug(name: str, medications: list[dict]) -> bool:
    """Return True if name or any medication matches the chronic trigger lists."""
    norm = name.lower()
    if any(trigger in norm for trigger in _CHRONIC_CONDITION_NAMES):
        return True
    for med in medications:
        med_name = (med.get("name") or "").lower()
        if any(drug in med_name for drug in _CHRONIC_DRUG_NAMES):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Group conditions into families (Sheet 2 Steps 1–4)
# ─────────────────────────────────────────────────────────────────────────────

def _group_into_families(conditions: list[Any]) -> list[list[Any]]:
    """
    Group document-level Condition rows into complaint families.

    Returns a list of families; each family is a list of Condition rows.
    """
    entries: list[tuple[Any, str, str, str | None]] = []
    for cond in conditions:
        norm = _normalize_name(cond.name or "")
        sys_ = _detect_body_system(norm)
        sub_ = _detect_sub_pattern(sys_, norm)
        entries.append((cond, norm, sys_, sub_))

    families: list[list[Any]] = []
    used: list[bool] = [False] * len(entries)

    for i, (cond_i, norm_i, sys_i, sub_i) in enumerate(entries):
        if used[i]:
            continue
        family = [cond_i]
        used[i] = True
        for j, (cond_j, norm_j, sys_j, sub_j) in enumerate(entries):
            if used[j] or i == j:
                continue
            if _same_family(norm_i, sys_i, sub_i, norm_j, sys_j, sub_j):
                family.append(cond_j)
                used[j] = True
        families.append(family)

    return families


# ─────────────────────────────────────────────────────────────────────────────
# Merge a family into a single AggregatedCondition dict (Sheet 3)
# ─────────────────────────────────────────────────────────────────────────────

def _getf(obj: Any, field: str, default: Any = None) -> Any:
    """Get a field from either a dict or an ORM object."""
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def _merge_family(family: list[Any]) -> dict[str, Any]:
    """
    Merge all Condition rows in a family according to Sheet 3 merge rules.
    Returns a dict ready to upsert into aggregated_conditions.
    Works with both ORM Condition objects and plain dicts/dataclass objects.
    """
    # ── condition_type: highest rank wins ────────────────────────────────────
    merged_type = max(
        (c.condition_type or "episodic" for c in family),
        key=lambda t: _TYPE_RANK.get(t, 0),
    )
    if merged_type == "resolved":
        merged_type = "episodic"

    # ── episode_dates: union, normalised to ISO, deduplicated, sorted ───────────
    all_episodes: set[str] = set()
    for c in family:
        for _ed in (c.episode_dates or []):
            try:
                from app.utils.date_utils import parse_date as _pd
                all_episodes.add(str(_pd(str(_ed))))  # normalise to YYYY-MM-DD
            except Exception:
                all_episodes.add(str(_ed))  # keep raw if unparseable
    merged_episodes = sorted(all_episodes)

    # ── Promote to chronic if name/drugs match trigger list ───────────────────
    all_meds_raw: list[dict] = []
    for c in family:
        for med in (c.medications or []):
            all_meds_raw.append({"name": _getf(med, "name")})
    family_name_for_chronic = (family[0].name or "")
    if merged_type != "chronic" and _is_chronic_by_name_or_drug(family_name_for_chronic, all_meds_raw):
        merged_type = "chronic"

    # ── Recurrence threshold for non-chronic families ─────────────────────────
    # Build a runtime-only episode list for the threshold check: conditions with
    # no episode_dates get a synthetic recent date (today minus a small per-condition
    # offset) so each undated episode counts distinctly. These synthetic dates are
    # never stored — merged_episodes above (used for DB storage, last_record_date,
    # medication activity, etc.) contains only real extracted dates.
    recurrence_watch = False
    if merged_type != "chronic":
        _threshold_episodes: list[str] = list(merged_episodes)
        _undated_idx = 0
        for c in family:
            if not (c.episode_dates or []):
                # Use diagnosed_at or created_at as the episode proxy so the 15/24-month
                # window is anchored to the real diagnosis date, not always "today".
                # Fall back to a synthetic recent date only when no real date exists.
                proxy_date = (
                    str(c.diagnosed_at) if c.diagnosed_at
                    else str(c.created_at.date()) if getattr(c, "created_at", None)
                    else str(date.today() - timedelta(days=_undated_idx))
                )
                _threshold_episodes.append(proxy_date)
                _undated_idx += 1
        type_from_threshold, recurrence_watch = _apply_recurrence_threshold(_threshold_episodes)
        if _TYPE_RANK.get(type_from_threshold, 0) > _TYPE_RANK.get(merged_type, 0):
            merged_type = type_from_threshold

    # ── diagnosed_at: MIN across family ──────────────────────────────────────
    diagnosed_dates = [c.diagnosed_at for c in family if c.diagnosed_at]
    diagnosed_at = min(diagnosed_dates) if diagnosed_dates else None

    # ── last_record_date: MAX of merged episode_dates ─────────────────────────
    last_record_date: date | None = None
    if merged_episodes:
        try:
            from app.utils.date_utils import parse_date
            last_record_date = parse_date(max(merged_episodes))
        except Exception:
            pass

    # ── medications: union by name, MAX end_date per drug ─────────────────────
    med_map: dict[str, dict] = {}  # lower(name) → {name, end_date, dose, frequency}
    for c in family:
        for med in (c.medications or []):
            med_name = _getf(med, "name")
            key = (med_name or "").lower().strip()
            if not key:
                continue
            med_end = _getf(med, "end_date")
            med_dose = _getf(med, "dose")
            med_freq = _getf(med, "frequency")
            # Normalise end_date to a string for comparison
            if isinstance(med_end, date):
                med_end_str = med_end.isoformat()
            elif isinstance(med_end, str):
                med_end_str = med_end
            else:
                med_end_str = None
            existing = med_map.get(key)
            if existing is None:
                med_map[key] = {
                    "name": med_name,
                    "end_date": med_end_str,
                    "dose": med_dose,
                    "frequency": med_freq,
                }
            else:
                # MAX end_date
                if med_end_str:
                    existing_end_str = existing.get("end_date")
                    if existing_end_str is None or med_end_str > existing_end_str:
                        existing["end_date"] = med_end_str
                if not existing.get("dose") and med_dose:
                    existing["dose"] = med_dose
                if not existing.get("frequency") and med_freq:
                    existing["frequency"] = med_freq
    merged_medications = list(med_map.values())

    # ── medication_end_date: MAX across all rows in family ────────────────────
    all_med_end_dates = [
        v["end_date"] for v in med_map.values() if v.get("end_date")
    ]
    medication_end_date: date | None = None
    if all_med_end_dates:
        try:
            from app.utils.date_utils import parse_date
            medication_end_date = parse_date(max(all_med_end_dates))
        except Exception:
            pass

    # ── monitoring: union by name, MAX recheck_due_date per item ─────────────
    mon_map: dict[str, dict] = {}
    for c in family:
        for mon in (c.monitoring or []):
            mon_name = _getf(mon, "name")
            key = (mon_name or "").lower().strip()
            if not key:
                continue
            mon_recheck = _getf(mon, "recheck_due_date")
            if isinstance(mon_recheck, date):
                mon_recheck_str = mon_recheck.isoformat()
            elif isinstance(mon_recheck, str):
                mon_recheck_str = mon_recheck
            else:
                mon_recheck_str = None
            existing_mon = mon_map.get(key)
            if existing_mon is None:
                mon_map[key] = {
                    "name": mon_name,
                    "recheck_due_date": mon_recheck_str,
                }
            else:
                if mon_recheck_str:
                    existing_recheck = existing_mon.get("recheck_due_date")
                    if existing_recheck is None or mon_recheck_str > existing_recheck:
                        existing_mon["recheck_due_date"] = mon_recheck_str
    merged_monitoring = list(mon_map.values())

    # ── condition_status: computed from merged data ───────────────────────────
    condition_status = _compute_condition_status(merged_type, medication_end_date, merged_episodes)

    # ── soft_resolution: True if latest-episode row has resolved status ───────
    soft_resolution = False
    if merged_episodes:
        latest_ep = max(merged_episodes)
        for c in family:
            if latest_ep in (c.episode_dates or []) and c.condition_status == "resolved":
                soft_resolution = True
                break

    # ── name: most frequent; tiebreak = latest document's name ───────────────
    name_counts: dict[str, int] = defaultdict(int)
    for c in family:
        name_counts[c.name or ""] += 1
    most_freq_count = max(name_counts.values())
    candidates = [n for n, cnt in name_counts.items() if cnt == most_freq_count]
    if len(candidates) == 1:
        merged_name = candidates[0]
    else:
        # tiebreak: name from latest document (by created_at, if available)
        latest_cond = max(family, key=lambda c: getattr(c, "created_at", None) or date.min)
        merged_name = latest_cond.name or candidates[0]

    # ── canonical_condition_id: row with MIN diagnosed_at ────────────────────
    with_diag = [c for c in family if c.diagnosed_at]
    canonical = min(with_diag, key=lambda c: c.diagnosed_at) if with_diag else family[0]

    # ── latest_episode_condition_id: row whose max(episode_dates[]) is most recent ──
    # Used by precompute JOIN to pull treatment_route + vet_resolved for status computation.
    def _latest_ep_date(c: Any) -> str:
        eps = c.episode_dates or []
        return max(eps) if eps else ""

    latest_episode_row = max(family, key=_latest_ep_date)

    return {
        "name": merged_name[:200],
        "condition_type": merged_type,
        "condition_status": condition_status,
        "episode_dates": merged_episodes,
        "diagnosed_at": diagnosed_at,
        "last_record_date": last_record_date,
        "medication_end_date": medication_end_date,
        "medications": merged_medications,
        "monitoring": merged_monitoring,
        "soft_resolution": soft_resolution,
        "recurrence_watch": recurrence_watch,
        "canonical_condition_id": canonical.id,
        "latest_episode_condition_id": latest_episode_row.id,
        "_family_members": family,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

async def aggregate_conditions_for_pet(db: Session, pet_id: UUID) -> None:
    """
    Rebuild aggregated_conditions for a pet.

    1. Load all active document-level conditions.
    2. Group into complaint families (body system + sub-pattern).
    3. Merge each family and upsert into aggregated_conditions.
    4. Write condition_family_id + recurrence_watch back to each member row.
    """
    from app.models.health.condition import Condition
    from app.models.health.aggregated_condition import AggregatedCondition
    from sqlalchemy.orm import selectinload

    conditions: list[Condition] = (
        db.query(Condition)
        .options(selectinload(Condition.medications), selectinload(Condition.monitoring))
        .filter(Condition.pet_id == pet_id, Condition.is_active.is_(True))
        .all()
    )

    if not conditions:
        return

    families = _group_into_families(conditions)

    for family_rows in families:
        merged = _merge_family(family_rows)
        members: list[Condition] = merged.pop("_family_members")

        # Find existing AggregatedCondition row for this family.
        # Match by condition_family_id already written on any member.
        existing_agg: AggregatedCondition | None = None
        for member in members:
            if member.condition_family_id:
                existing_agg = db.query(AggregatedCondition).get(member.condition_family_id)
                if existing_agg:
                    break

        if existing_agg is None:
            # Create new aggregated row
            existing_agg = AggregatedCondition(
                id=uuid4(),
                pet_id=pet_id,
                **{k: v for k, v in merged.items()},
            )
            db.add(existing_agg)
            db.flush()
        else:
            # Update existing
            for key, value in merged.items():
                setattr(existing_agg, key, value)
            db.flush()

        # Write condition_family_id + recurrence_watch back to member rows
        for member in members:
            member.condition_family_id = existing_agg.id
            member.recurrence_watch = merged.get("recurrence_watch", False)

        # Write merged recheck_due_date back as next_due_date on ConditionMonitoring rows
        # so condition_service.py has a single reliable source of truth.
        merged_mon_map: dict[str, date | None] = {}
        for mon_dict in (merged.get("monitoring") or []):
            raw = mon_dict.get("recheck_due_date")
            if raw:
                try:
                    from app.utils.date_utils import parse_date
                    merged_mon_map[(mon_dict.get("name") or "").lower().strip()] = parse_date(raw)
                except Exception:
                    pass
        if merged_mon_map:
            for member in members:
                for mon in (member.monitoring or []):
                    key = (mon.name or "").lower().strip()
                    merged_date = merged_mon_map.get(key)
                    if merged_date and (mon.next_due_date is None or merged_date > mon.next_due_date):
                        mon.next_due_date = merged_date

    try:
        db.flush()
    except Exception as exc:
        logger.warning("aggregate_conditions_for_pet flush failed for pet=%s: %s", pet_id, exc)
        db.rollback()
        raise

    db.execute(
        sa_text(
            "DELETE FROM pet_ai_insights "
            "WHERE pet_id = :pet_id AND insight_type = 'health_conditions_v2'"
        ),
        {"pet_id": str(pet_id)},
    )
