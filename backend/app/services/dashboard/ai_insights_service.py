"""
PetCircle Phase 1 — AI Insights Service

Generates and caches GPT-driven insights shown on the Conditions dashboard tab:

    1. health_summary  — 3-4 sentence rich health narrative displayed at the
                         top of the Conditions tab alongside the health score ring.
    2. vet_questions   — Prioritised list of questions the pet owner should raise
                         at the next vet visit, shown in the "Ask the Vet" section.

Caching rules:
    - Insights are stored in pet_ai_insights (one row per pet per insight_type).
    - An insight older than AI_INSIGHT_CACHE_DAYS (7 days) is considered stale
      and re-generated on the next request.
    - force=True bypasses the cache regardless of age (used by the regenerate
      endpoint triggered from the dashboard).

Model: OPENAI_QUERY_MODEL (gpt-4.1) — used for structured text generation.

Failure behaviour: If GPT or the DB call fails, the error is logged and a
sensible default payload is returned so the dashboard never crashes.
"""
from app.models.lookup.preventive_master import PreventiveMaster

import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import List, Any, TypedDict
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.constants import OPENAI_QUERY_MODEL
from app.models.health.condition import Condition
from app.models.preventive.custom_preventive_item import CustomPreventiveItem
from app.models.nutrition.diet_item import DietItem
from app.models.core.pet import Pet
from app.models.pet_profile.pet_ai_insight import PetAiInsight
from app.models.preventive.preventive_record import PreventiveRecord
from app.repositories.pet_repository import PetRepository
from app.repositories.pet_ai_insight_repository import PetAiInsightRepository
from app.repositories.condition_repository import ConditionRepository
from app.repositories.diet_repository import DietRepository
from app.services.shared.care_plan_engine import _get_breed_size, _get_life_stage, _get_pet_age_months
from app.services.dashboard.condition_aggregation_service import _compute_condition_status
from app.utils.retry import retry_openai_call

logger = logging.getLogger(__name__)

# Re-generate if the cached insight is older than this many days.
AI_INSIGHT_CACHE_DAYS = 7

# Keywords used to classify a PreventiveMaster.item_name as a vaccine for the
# "What We Found" bullet. Case-insensitive substring match. Must include every
# canonical vaccine item_name shipped in preventive_master so none get misfiled
# as "other preventive items". See Bug 2.
_VACCINE_BULLET_TERMS: list[str] = [
    "vaccine", "rabies", "dhpp", "bordetella", "feline core",
    "kennel cough", "nobivac",
    "coronavirus", "ccov",
]

# Nutrition importance note is stable — re-generate only when pet ages significantly.
NUTRITION_IMPORTANCE_CACHE_DAYS = 30

# --------------------------------------------------------------------------- #
#  Lazy OpenAI client                                                           #
# --------------------------------------------------------------------------- #

_openai_client = None  # Anthropic AsyncAnthropic client (lazy-initialised)


class Bullet(TypedDict):
    """Single recognition bullet used by the What We Found card."""

    icon: str
    label: str


_DIET_SPLIT_RE = re.compile(r"\s*[·,;|]\s*", re.IGNORECASE)
_NOISE_CHUNK_RE = re.compile(
    r"(times?\s+a\s+day|x\s*\d+\s*/\s*day|\d+\s*/\s*day|per\s+day|"
    r"/\s*day|\bday\b|morning|afternoon|evening|night|treat|snack)",
    re.IGNORECASE,
)
_FREQUENCY_FRAGMENT_RE = re.compile(
    r"("
    r"\bx\s*\d+(?:\.\d+)?\s*/\s*(?:day|week|month)\b|"
    r"\b\d+(?:\.\d+)?\s*x\s*/\s*(?:day|week|month)\b|"
    r"\b(?:once|twice|thrice|\d+\s*times?)\s*(?:a|per)\s*(?:day|week|month)\b|"
    r"/\s*(?:day|week|month)\b"
    r")",
    re.IGNORECASE,
)
_FREQUENCY_QUALIFIER_RE = re.compile(
    r"^\s*(?:occasional(?:ly)?|sometimes|rarely|infrequently)\s+",
    re.IGNORECASE,
)
_STANDALONE_FREQUENCY_QUALIFIER_RE = re.compile(
    r"^\s*(?:occasional(?:ly)?|sometimes|rarely|infrequently)\s*$",
    re.IGNORECASE,
)
_MEASURE_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:g|kg|ml|l|cups?|tbsp|tsp|x)\b", re.IGNORECASE)


def _sentence_case(text: str) -> str:
    """Return text with first letter uppercased and trailing punctuation removed."""
    cleaned = text.strip().strip(". ")
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _canonical_diet_item_text(text: str) -> str:
    """Return a canonical representation for cross-list diet item matching."""
    canonical = (text or "").lower().strip()
    canonical = re.sub(r"[^a-z0-9]+", " ", canonical)
    return re.sub(r"\s+", " ", canonical).strip()


def _is_food_item_covered_by_supplements(food_item: str, supplement_items: list[str]) -> bool:
    """Return True if a food item semantically overlaps with any supplement label."""
    food_canonical = _canonical_diet_item_text(food_item)
    if not food_canonical:
        return False

    food_tokens = set(food_canonical.split())
    if not food_tokens:
        return False

    for supplement in supplement_items:
        supplement_canonical = _canonical_diet_item_text(supplement)
        if not supplement_canonical:
            continue
        if food_canonical == supplement_canonical:
            return True

        supplement_tokens = set(supplement_canonical.split())
        if not supplement_tokens:
            continue
        # Keep only one-way subset matching to avoid suppressing legitimate foods
        # that merely contain a generic supplement token.
        if food_tokens.issubset(supplement_tokens):
            return True

    return False


def _extract_main_food_items(*texts: str, apply_noise_filter: bool = True) -> list[str]:
    """Extract main food labels while removing quantity/frequency/noise fragments."""
    items: list[str] = []

    for raw_text in texts:
        if not raw_text:
            continue

        normalized = raw_text.replace("×", "x")
        chunks = _DIET_SPLIT_RE.split(normalized)
        for chunk in chunks:
            # Strip frequency snippets so labels stay as clean food names.
            chunk = _FREQUENCY_FRAGMENT_RE.sub("", chunk)
            chunk = _FREQUENCY_QUALIFIER_RE.sub("", chunk)
            standalone_probe = re.sub(r"\s+", " ", chunk).strip(" .,!?:;-")
            if _STANDALONE_FREQUENCY_QUALIFIER_RE.match(standalone_probe):
                continue
            chunk = _MEASURE_TOKEN_RE.sub("", chunk)
            chunk = re.sub(r"\b\d+\b", "", chunk)
            chunk = re.sub(r"\s+", " ", chunk).strip(" .,-")
            if not chunk:
                continue
            if apply_noise_filter and _NOISE_CHUNK_RE.search(chunk):
                continue

            main_item = _sentence_case(chunk)
            if not main_item:
                continue
            if main_item.lower() not in {i.lower() for i in items}:
                items.append(main_item)

    return items


def _format_found_diet_summary(food_items: list[DietItem], supplement_items: list[DietItem]) -> str:
    """Format the What We Found diet line as a natural sentence with quantities.

    Example output: "Royal Canin hypoallergenic (280g x 2/day) and Fur+ along
    with Vitamin D3 and Glucosamine supplements"
    """
    # Build food descriptions using label + detail (for quantity/portion info).
    seen_foods: set[str] = set()
    food_descriptions: list[str] = []
    for food in food_items:
        label = (food.label or "").strip()
        if not label:
            continue
        key = label.lower()
        if key in seen_foods:
            continue
        seen_foods.add(key)
        # Use only the label — the detail field may contain prescription metadata
        # (e.g. "5 days · Vet prescribed (VetPrescription_Apr26)") that should not
        # be shown in the What We Found summary card.
        food_descriptions.append(label)

    # Build supplement descriptions.
    seen_supps: set[str] = set()
    supp_descriptions: list[str] = []
    for supp in supplement_items:
        label = (supp.label or "").strip()
        if not label:
            continue
        key = label.lower()
        if key in seen_supps:
            continue
        seen_supps.add(key)
        # Skip supplements that are already covered by food item names.
        supp_names_for_check = [s for s in supp_descriptions]
        if _is_food_item_covered_by_supplements(label, supp_names_for_check):
            continue
        supp_descriptions.append(label)

    # Join foods into a natural sentence.
    if len(food_descriptions) == 0:
        food_str = "No food items recorded"
    elif len(food_descriptions) == 1:
        food_str = food_descriptions[0]
    elif len(food_descriptions) == 2:
        food_str = f"{food_descriptions[0]} and {food_descriptions[1]}"
    else:
        food_str = ", ".join(food_descriptions[:-1]) + f" and {food_descriptions[-1]}"

    # Append supplements.
    if supp_descriptions:
        if len(supp_descriptions) == 1:
            supp_str = supp_descriptions[0]
        elif len(supp_descriptions) == 2:
            supp_str = f"{supp_descriptions[0]} and {supp_descriptions[1]}"
        else:
            supp_str = ", ".join(supp_descriptions[:-1]) + f" and {supp_descriptions[-1]}"
        suffix = "supplement" if len(supp_descriptions) == 1 else "supplements"
        # Avoid doubling "supplement" when the label already ends with that word.
        supp_str_clean = supp_str.rstrip()
        if supp_str_clean.lower().endswith("supplements") or supp_str_clean.lower().endswith("supplement"):
            return f"{food_str} along with {supp_str_clean}"
        return f"{food_str} along with {supp_str_clean} {suffix}"

    return food_str


def _get_openai_client():
    """Lazy-initialise AI client (provider-agnostic, avoids import-time errors)."""
    global _openai_client
    if _openai_client is None:
        from app.utils.ai_client import get_ai_client  # noqa: PLC0415
        _openai_client = get_ai_client()
    return _openai_client


# --------------------------------------------------------------------------- #
#  GPT generation helpers                                                       #
# --------------------------------------------------------------------------- #



async def _generate_health_summary_gpt(pet_context: str) -> dict:
    """
    Call GPT to produce a rich 3-4 sentence health narrative for the pet.

    Args:
        pet_context: Structured text description of the pet's health status.

    Returns:
        {"summary": "<rich 3-4 sentence narrative>"}
    """
    client = _get_openai_client()

    system_prompt = (
        "You are a veterinary health assistant writing for a pet owner's dashboard. "
        "Given a pet's profile, active health conditions, and health score, write a "
        "rich 3-4 sentence health narrative. Structure it as follows:\n"
        "1. Overall health standing — reference the score and label naturally.\n"
        "2. Key active conditions and what they mean for the pet's daily life.\n"
        "3. What is going well (e.g. vaccines up to date, medications being managed).\n"
        "4. What the owner should focus on next (e.g. overdue monitoring, refill due, "
        "missing record to add).\n"
        "Tone: warm, factual, parent-friendly. Never alarming. "
        "Respond with ONLY valid JSON: {\"summary\": \"<text>\"}. "
        "Do not include any explanation outside the JSON object."
    )

    user_prompt = f"Pet health context:\n{pet_context}"

    async def _call() -> str:
        response = await client.messages.create(
            model=OPENAI_QUERY_MODEL,
            temperature=0,
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.content[0].text or "{}"

    raw = await retry_openai_call(_call)
    try:
        parsed = json.loads(raw)
        if "summary" not in parsed:
            raise ValueError("Missing 'summary' key")
        return parsed
    except Exception as exc:
        logger.warning("health_summary JSON parse failed: %s | raw=%s", exc, raw)
        return {"summary": "Health summary is being updated."}


async def _generate_vet_questions_gpt(pet_context: str) -> list:
    """
    Call GPT to produce a prioritised list of vet consultation questions.

    Args:
        pet_context: Structured text description of the pet's health status.

    Returns:
        List of {"priority", "icon", "q", "context"} dicts.
    """
    client = _get_openai_client()

    system_prompt = (
        "You are a veterinary health assistant. "
        "Given a pet's active conditions, medications, and overdue monitoring checks, "
        "generate a list of 2-5 prioritised questions the owner should raise at the "
        "next vet visit. "
        "Rules:\n"
        "- priority must be one of: 'urgent', 'high', 'medium'\n"
        "- icon must be a single relevant emoji\n"
        "- q is the question (≤15 words)\n"
        "- context is a 1-3 sentence explanation (factual, no alarming language)\n"
        "Respond with ONLY valid JSON array: "
        "[{\"priority\":\"...\",\"icon\":\"...\",\"q\":\"...\",\"context\":\"...\"}]"
    )

    user_prompt = f"Pet health context:\n{pet_context}"

    async def _call() -> str:
        response = await client.messages.create(
            model=OPENAI_QUERY_MODEL,
            temperature=0,
            max_tokens=800,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.content[0].text or "[]"

    raw = await retry_openai_call(_call)
    try:
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            raise ValueError("Expected a JSON array")
        # Validate each item
        valid_priorities = {"urgent", "high", "medium"}
        questions = []
        for item in parsed:
            if isinstance(item, dict) and "q" in item and "context" in item:
                questions.append({
                    "priority": item.get("priority", "medium") if item.get("priority") in valid_priorities else "medium",
                    "icon": item.get("icon", "🩺"),
                    "q": str(item["q"])[:200],
                    "context": str(item["context"])[:800],
                })
        return questions
    except Exception as exc:
        logger.warning("vet_questions JSON parse failed: %s | raw=%s", exc, raw)
        return []


def _build_pet_context(pet, conditions: list) -> str:
    """
    Build a compact plain-text context string for GPT prompts.

    Includes: species, breed, age, active conditions, medications,
    and overdue monitoring items.
    """
    from datetime import date

    today = date.today()
    lines = []

    # Pet basics
    age_str = ""
    if pet.get("dob"):
        try:
            dob = datetime.strptime(pet["dob"], "%Y-%m-%d").date()
            age_years = (today - dob).days // 365
            age_str = f", {age_years} years old"
        except ValueError:
            pass

    neutered = "neutered" if pet.get("neutered") else "intact"
    lines.append(
        f"Pet: {pet.get('name', 'Unknown')}, {pet.get('species', '')} ({pet.get('breed', '')})"
        f"{age_str}, {pet.get('gender', '')}, {neutered}"
    )

    # Active conditions
    if not conditions:
        lines.append("Active conditions: None")
    else:
        lines.append(f"Active conditions ({len(conditions)}):")
        for cond in conditions:
            lines.append(f"  - {cond.get('name', '?')} ({cond.get('condition_type', '')})"
                         f" diagnosed {cond.get('diagnosed_at', 'unknown date')}")

            # Medications
            meds = cond.get("medications", [])
            active_meds = [m for m in meds if m.get("status") == "active"]
            if active_meds:
                med_names = ", ".join(m.get("name", "?") for m in active_meds)
                lines.append(f"    Medications (active): {med_names}")
            elif not meds:
                lines.append("    Medications: none recorded")

            # Overdue monitoring
            monitoring = cond.get("monitoring", [])
            for mon in monitoring:
                next_due = mon.get("next_due_date")
                if next_due:
                    try:
                        due_date = datetime.strptime(next_due, "%Y-%m-%d").date()
                        if due_date < today:
                            days_overdue = (today - due_date).days
                            lines.append(
                                f"    OVERDUE monitoring: {mon.get('name', '?')} "
                                f"({days_overdue} days overdue)"
                            )
                    except ValueError:
                        pass
                elif not mon.get("last_done_date"):
                    lines.append(f"    Monitoring: {mon.get('name', '?')} — never done")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  Health Prompt 5 — GPT-driven condition classification and status             #
# --------------------------------------------------------------------------- #

_HEALTH_CONDITIONS_V2_SYSTEM_PROMPT = """
You are PetCircle's health insight engine writing for a pet owner's dashboard.
═══════════════════════════════════════════════════════
INPUT FIELDS — TRUST THESE, DO NOT RECLASSIFY
═══════════════════════════════════════════════════════
Per condition you receive:
  condition_type : chronic | recurrent | episodic  — pre-classified
  condition_status : active | monitoring | resolved  — pre-computed
  soft_resolution  : true/false — resolved by elapsed time, not vet-confirmed
  recurrence_watch : true/false — one episode seen, watching for second
  inferred_from_medication : true/false — name inferred from drug, not written by vet
  episode_dates[], diagnosed_at, last_record_date
  medications[]  : name, dose, frequency, end_date
  monitoring[]   : name, recheck_due_date

You also receive:
  active_medications[] : currently active drugs across all conditions
  abnormal_labs[]      : abnormal lab results from last 10 reports
  current_diet[]       : active diet items
  pet                  : name, species, breed, age_years, life_stage, gender, neutered
  today                : current date — use for all date comparisons
═══════════════════════════════════════════════════════
CONDITION NAME RULE
═══════════════════════════════════════════════════════
  inferred_from_medication = false
    → use condition name freely in all output fields

  inferred_from_medication = true
    → never use the condition name anywhere in output
    → refer only to observable facts: symptoms, lab findings, medication names
    WRONG: "UTI — 2nd episode, on antibiotics until Apr 30"
    RIGHT: "Recurring urinary symptoms — on antibiotics until Apr 30"
═══════════════════════════════════════════════════════
CARD LAYOUT
═══════════════════════════════════════════════════════
Everything renders on one card in this order:

  [headline_state]        ← bold heading, leads the card
  [summary_body]          ← prose paragraph below heading
  ──────────────────────────────────────────────────────
  ● [insight]  [trend_label] ← one bullet per active/monitoring condition
  ──────────────────────────────────────────────────────
  [Book a Consult button]

Rules across the entire card:
  - headline_state must be distinct from all insight lines
  - No field may repeat content verbatim from any other field
  - Never use alarming language. Use: suggest, note, watch, advise
  - Never mention vaccines, grooming, or health score
  - Never use clinical marker names (creatinine, ALT, MCH etc.) in summary_body
    unless no plain language equivalent exists
    Use: "kidney markers" not "creatinine", "liver values" not "ALT"
═══════════════════════════════════════════════════════
PART 1 — PATTERN INSIGHT (leads the card)
═══════════════════════════════════════════════════════
Two fields: headline_state and summary_body.

Written AFTER reading all conditions and data.
Appears ABOVE the condition bullets on the card.

── CONDITIONAL MERGE RULE ──────────────────────────────
If ONLY ONE active/monitoring condition exists AND the sharpest
pattern observation is directly about that same condition:
  → MERGE: open summary_body with a plain-language condition
    status fact, then surface the pattern observation.
    Do not repeat the insight line verbatim — paraphrase the status.
    Example (single GI recurrence):
      headline_state: "Two stomach episodes a year apart — trigger worth investigating"
      summary_body opens: "June has had two stomach upsets in April, a year apart..."

If MULTIPLE active/monitoring conditions exist OR the pattern
observation is about a different condition than the active one:
  → KEEP SEPARATE: summary_body covers the pattern observation only.
    Condition status facts stay in the insight bullet lines below.
    Do not restate condition status in summary_body.
────────────────────────────────────────────────────────

headline_state (max 10 words)
  One sharp observation heading that leads the entire card.
  Must be distinct from all insight bullet lines.
  Names the observation specifically — not vague.
  Examples:
    "Two stomach episodes a year apart — trigger worth investigating"
    "Kidney strain and GI episodes may be connected"
    "Recurring skin infections — diet may be a factor"
    "Lab finding worth following up before next episode"
    "No records yet — here is what to prioritise"
  Never use: urgent, critical, alert, warning, needs attention

summary_body (max 60 words, flowing prose, no bullet points inside)
  Surfaces ONE sharp observation the owner may not have connected.
  Must NOT repeat what insight bullet lines already state.

  Write for the pet parent, not the vet:
   - Use plain language throughout
     Not "creatinine is elevated" → "kidney markers are slightly above normal"
     Not "hepatotoxicity risk" → "this can put extra strain on the liver"
   - Always end with one or two specific named actions or named questions
     for the vet — not vague suggestions
     WRONG: "worth discussing kidney health with your vet"
     RIGHT: "worth asking whether a kidney recheck after the treatment
            course ends would be a good idea"

  Pick the sharpest observation from:
  a) Recurrence pattern
     Frequency tightening, narrowing gaps, same timing, same trigger.
     Name the pattern specifically — same month, every winter, etc.

  b) Lab correlation
     An abnormal finding that aligns with and adds meaning to
     an active or recurrent condition.
     Explain the connection in plain language.
     Name the specific action: recheck timing, hydration support, etc.

  c) Treatment gap
     A recurrent condition treated only symptomatically each time
     with no root cause investigation on record.
     Name what investigation could help and why.

  d) Breed or life-stage risk
     A known predisposition at this breed and age that aligns
     with what has been seen, or a proactive screen worth considering.
     Name the specific screen or check, not a general suggestion.

  e) Diet-condition link
     ONLY surface if you can name all three:
       (i)   the specific food item from current_diet input
       (ii)  the specific condition from conditions input
       (iii) a reasoned mechanism linking them
     If all three cannot be named, skip nutrition entirely.
     The mechanism may be indirect but must be reasoned, not speculative.

  Combining rule:
    If two observations point to the same condition — for example
    a recurrence pattern substantiated by a lab finding — combine
    them into one narrative. Do not list as separate sentences.

  Actionable rule:
    End with ONE specific next step. Before suggesting any test,
    check abnormal_labs input. If that test already appears there,
    do not suggest it. Only suggest something not already in the input.
    If nothing concrete adds value, end without a next step.

  soft_resolution rule:
    If soft_resolution = true for the latest active condition,
    end summary_body with one gentle sentence asking for an update.
    Example: "Let us know how June is doing once the course ends."
═══════════════════════════════════════════════════════
PART 2 — CONDITION BULLETS (conditions[])
═══════════════════════════════════════════════════════
Include ONLY conditions with status: active or monitoring.
Exclude resolved conditions from conditions[] entirely.
Resolved conditions may inform summary_body but never appear as bullets.
If zero active/monitoring conditions: return conditions: []

Per condition produce three fields:

insight (max 12 words)
  Factual one-line status. No narrative. No medication names.
  Format by type + status:

  chronic + active:
    "[Condition] since [year] — [one-line management status]"
    Example: "Hypothyroidism since 2021 — on daily medication"
    Example: "Chronic kidney disease since 2024 — stable, markers monitored"

  chronic + monitoring:
    "[Condition] — [what is being watched]"
    Example: "Kidney markers — mildly elevated Oct 2025, no treatment yet"

  recurrent + active:
    "[N] episodes of [condition] since [year] — last episode [Mon YYYY]"
    Example: "2 episodes of GI upset since Apr 2025 — last episode Apr 2026"

  recurrent + monitoring:
    "[N] episodes of [condition] since [year] — last episode [Mon YYYY]"
    Example: "3 episodes of ear infection since Jan 2024 — last episode Feb 2026"

  episodic + active:
    "[Condition] — treatment ongoing since [Mon YYYY]"
    Example: "Skin infection — treatment ongoing since Apr 2026"

  episodic + monitoring:
    "[Condition] — treatment ended [Mon YYYY], watching recovery"
    Example: "GI upset — treatment ended Mar 2026, watching recovery"

trend_label (max 4 words)
  Small tag shown alongside bullet.
  chronic:               "Since [year]"
  recurrent + active:    "Episode [N] ongoing"
  recurrent + monitoring: "Last episode [Mon YYYY]"
  episodic + active:     "Started [Mon YYYY]"
  episodic + monitoring:  "Monitoring recovery"

severity
  Always "yellow". No red. No green.

Order: active before monitoring.
Most recent episode_date or diagnosed_at first within each group.
═══════════════════════════════════════════════════════
CORNER CASES
═══════════════════════════════════════════════════════
CASE 1 — No documents uploaded
  (conditions[], abnormal_labs[], current_diet[] all empty)

  conditions: []
  headline_state: breed and age specific
    Example: "Senior Labrador — joint and weight check worth scheduling"
  summary_body:
    Open with "No health records have been shared for [name] yet."
    Surface the single most clinically relevant proactive watch for
    this breed at this age. Name a specific screen or check.
    If no strong breed predisposition exists, give a life-stage
    appropriate baseline: senior blood panel, first wellness check etc.

CASE 2 — Records exist, all conditions resolved
  conditions: []
  headline_state: sharpest pattern or forward watch from records
    Example: "Recurring stomach episodes — root cause not yet investigated"
  summary_body:
    Open with "[Name]'s health is currently on track."
    Surface sharpest observation from a-e above.
    Apply combining rule and actionable rule as normal.
    Do not use "keep up the great preventive care" as the sole response.
    Always surface a specific observation or named forward watch.

CASE 3 — Only abnormal labs, no conditions
  conditions: []
  headline_state: name the specific finding in plain language
    Example: "One liver value worth following up"
  summary_body:
    Surface the finding in plain language, what it may indicate,
    and one specific suggested follow-up.
    Do not suggest repeating a test already in abnormal_labs input.
═══════════════════════════════════════════════════════
OUTPUT — valid JSON only, no prose outside the block
═══════════════════════════════════════════════════════
{
  "headline_state": "string",
  "summary_body": "string",
  "conditions": [
    {
      "id": "string",
      "name": "string",
      "type": "chronic | recurrent | episodic",
      "status": "active | monitoring",
      "severity": "yellow",
      "trend_label": "string",
      "insight": "string"
    }
  ],
  "meta": {
    "total_conditions": 0,
    "displayed_count": 0,
    "resolved_count": 0
  }
}
"""

_HEALTH_CONDITIONS_V2_FALLBACK: dict = {
    "headline_state": "No active conditions on record",
    "summary_body": (
        "No active conditions detected. Uploading a recent blood panel or "
        "prescription will help us surface personalised health insights."
    ),
    "conditions": [],
    "meta": {"total_conditions": 0, "displayed_count": 0, "resolved_count": 0},
}


async def _generate_health_conditions_v2_gpt(user_payload: dict) -> dict:
    """
    Call GPT with the Health Conditions V2 prompt to build the structured
    conditions dashboard payload.

    Args:
        user_payload: Full input dict with today, pet, conditions, active_medications,
                      abnormal_labs, and current_diet.

    Returns:
        Structured dict: {headline_state, summary_body, conditions[], meta}.
    """
    client = _get_openai_client()

    async def _call() -> str:
        response = await client.messages.create(
            model=OPENAI_QUERY_MODEL,
            temperature=0,
            max_tokens=1200,
            system=_HEALTH_CONDITIONS_V2_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(user_payload)}],
        )
        return response.content[0].text or "{}"

    raw = await retry_openai_call(_call)

    # Strip markdown fences if model wraps JSON.
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw.strip())

    try:
        parsed = json.loads(raw)
        if "headline_state" not in parsed or "conditions" not in parsed:
            raise ValueError("Missing required keys in health_conditions_v2 response")
        if "meta" not in parsed:
            total_input = len(user_payload.get("conditions", []))
            displayed = len(parsed.get("conditions") or [])
            parsed["meta"] = {
                "total_conditions": total_input,
                "displayed_count": displayed,
                "resolved_count": max(total_input - displayed, 0),
            }
        return parsed
    except Exception as exc:
        logger.warning(
            "health_conditions_v2 JSON parse failed: %s | raw=%s", exc, raw[:500]
        )
        return {
            "headline_state": "Health summary updating",
            "summary_body": "We are updating the health summary. Check back shortly.",
            "conditions": [],
            "meta": {"total_conditions": 0, "displayed_count": 0, "resolved_count": 0},
        }


# --------------------------------------------------------------------------- #
#  Public API                                                                   #
# --------------------------------------------------------------------------- #

async def get_or_generate_insight(
    db: Session,
    pet_id: UUID,
    insight_type: str,
    pet: dict,
    conditions: list,
    force: bool = False,
) -> dict:
    """
    Return a cached AI insight or generate a fresh one.

    If a cached insight exists and is less than AI_INSIGHT_CACHE_DAYS old
    (and force is False), return it immediately without calling GPT.
    Otherwise call GPT, persist the result, and return it.

    Args:
        db:           SQLAlchemy session.
        pet_id:       Pet UUID.
        insight_type: 'health_summary' or 'vet_questions'.
        pet:          Pet dict (from dashboard data).
        conditions:   List of condition dicts (from dashboard data).
        force:        If True, bypass cache and re-generate.

    Returns:
        content_json dict (structure depends on insight_type).
    """
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=AI_INSIGHT_CACHE_DAYS)
    insight_repo = PetAiInsightRepository(db)

    # Check cache
    if not force:
        existing = insight_repo.find_non_stale_by_pet_and_type(pet_id, insight_type, stale_cutoff)
        if existing:
            return existing.content_json

    # Generate fresh content
    pet_context = _build_pet_context(pet, conditions)
    try:
        normalized_insight_type = insight_type
        if insight_type.startswith("vet_questions"):
            # Allow per-condition cache keys like "vet_questions:<condition_id>".
            normalized_insight_type = "vet_questions"

        if normalized_insight_type == "health_conditions_v2":
            from app.models.nutrition.diet_item import DietItem
            from app.repositories.condition_repository import ConditionRepository
            from app.repositories.health_repository import HealthRepository
            from datetime import date as _date
            _today = _date.today()
            _condition_repo = ConditionRepository(db)
            _health_repo = HealthRepository(db)

            age_months = _get_pet_age_months(pet) if not isinstance(pet, dict) else None
            age_years = round(age_months / 12, 1) if age_months else None
            life_stage = _get_life_stage(pet) if not isinstance(pet, dict) else None

            pet_name = pet.get("name", "") if isinstance(pet, dict) else getattr(pet, "name", "")
            pet_profile = {
                "name": pet_name,
                "species": pet.get("species") if isinstance(pet, dict) else getattr(pet, "species", None),
                "breed": pet.get("breed") if isinstance(pet, dict) else getattr(pet, "breed", None),
                "age_years": age_years,
                "life_stage": str(life_stage) if life_stage else None,
                "gender": pet.get("gender") if isinstance(pet, dict) else getattr(pet, "gender", None),
                "neutered": pet.get("neutered") if isinstance(pet, dict) else getattr(pet, "neutered", None),
            }

            _NON_CONDITION_NAMES = {
                "prescription medications", "prescription medication",
                "medications", "medication", "supplements", "supplement", "rx medications",
            }

            agg_rows = _condition_repo.get_aggregated_conditions_for_insights(pet_id)

            def _compute_status(row):
                if row.vet_resolved:
                    return "resolved"
                return _compute_condition_status(
                    row.condition_type,
                    row.medication_end_date,
                    row.episode_dates or [],
                    recurrence_watch=bool(row.recurrence_watch),
                )

            if agg_rows:
                conditions_payload = [
                    {
                        "id": str(row.condition_family_id),
                        "name": row.name,
                        "condition_type": row.condition_type,
                        "condition_status": _compute_status(row),
                        "soft_resolution": bool(row.soft_resolution) if row.soft_resolution is not None else False,
                        "recurrence_watch": bool(row.recurrence_watch) if row.recurrence_watch is not None else False,
                        "inferred_from_medication": (row.source or "").lower() == "inferred",
                        "episode_dates": row.episode_dates or [],
                        "diagnosed_at": str(row.diagnosed_at) if row.diagnosed_at else None,
                        "last_record_date": str(row.last_record_date) if row.last_record_date else None,
                        "medications": row.medications or [],
                        "monitoring": row.monitoring or [],
                    }
                    for row in agg_rows
                    if row.name.lower().strip() not in _NON_CONDITION_NAMES
                ]
            else:
                # aggregated_conditions table not yet populated — fall back to raw conditions
                conditions_payload = [
                    {
                        "id": c.get("id", ""),
                        "name": c.get("name", ""),
                        "condition_type": c.get("condition_type", "episodic"),
                        "condition_status": "active" if c.get("is_active") else "resolved",
                        "soft_resolution": False,
                        "recurrence_watch": False,
                        "inferred_from_medication": False,
                        "episode_dates": [],
                        "diagnosed_at": c.get("diagnosed_at"),
                        "last_record_date": c.get("created_at"),
                        "medications": [m.get("name", "") for m in c.get("medications", [])],
                        "monitoring": [m.get("name", "") for m in c.get("monitoring", [])],
                    }
                    for c in (conditions or [])
                    if c.get("name", "").lower().strip() not in _NON_CONDITION_NAMES
                ]

            active_meds_raw = _health_repo.get_active_medications_deduped(pet_id, _today)

            def _null_end_date_active(row) -> bool:
                episode_dates = row.episode_dates or []
                if not episode_dates:
                    return False
                try:
                    from app.utils.date_utils import parse_date
                    latest = parse_date(max(episode_dates))
                    return (_today - latest).days <= 30
                except Exception:
                    return False

            active_meds = [
                m for m in active_meds_raw
                if m.end_date is not None or _null_end_date_active(m)
            ]

            medications_payload = [
                {
                    "name": m.med_name,
                    "dose": m.dose,
                    "frequency": m.frequency,
                    "end_date": str(m.end_date) if m.end_date else "lifelong",
                    "for_condition": m.condition_name,
                }
                for m in active_meds
            ]

            abnormal_results = _health_repo.get_abnormal_diagnostics(pet_id)
            labs_payload = [
                {
                    "test_name": r.parameter_name,
                    "value": str(r.value_numeric) if r.value_numeric is not None else r.value_text,
                    "unit": r.unit,
                    "status_flag": r.status_flag,
                    "report_date": str(r.observed_at),
                }
                for r in abnormal_results
            ]

            diet_rows = db.query(DietItem).filter(DietItem.pet_id == pet_id, DietItem.is_active == True).all()
            diet_payload = [
                {
                    "item_name": d.label,
                    "item_type": d.type,
                    "daily_portion_g": d.daily_portion_g,
                    "pack_size_g": d.pack_size_g,
                    "doses_per_day": d.doses_per_day,
                }
                for d in diet_rows
            ]

            user_payload = {
                "today": _today.isoformat(),
                "pet": pet_profile,
                "conditions": conditions_payload,
                "active_medications": medications_payload,
                "abnormal_labs": labs_payload,
                "current_diet": diet_payload,
            }
            content = await _generate_health_conditions_v2_gpt(user_payload)
        elif normalized_insight_type == "health_summary":
            content = await _generate_health_summary_gpt(pet_context)
        elif normalized_insight_type == "vet_questions":
            content = await _generate_vet_questions_gpt(pet_context)
        else:
            logger.error("Unknown insight_type: %s", insight_type)
            return {}
    except Exception as exc:
        logger.error("GPT insight generation failed for %s/%s: %s", pet_id, insight_type, exc, exc_info=True)
        if insight_type == "health_conditions_v2":
            return dict(_HEALTH_CONDITIONS_V2_FALLBACK)
        if insight_type == "health_summary":
            return {"summary": "Summary is currently unavailable."}
        return []

    # Upsert to DB (INSERT … ON CONFLICT DO UPDATE)
    try:
        insight_repo.upsert_insight(pet_id, insight_type, content)
        db.commit()
    except Exception as exc:
        logger.error("Failed to upsert AI insight to DB: %s", exc)
        db.rollback()

    return content


# --------------------------------------------------------------------------- #
#  Nutrition Importance — separate cache with longer TTL                        #
# --------------------------------------------------------------------------- #

_NUTRITION_IMPORTANCE_FALLBACK = (
    "Good nutrition is the foundation of your pet's health at every life stage. "
    "The right balance of proteins, fats, vitamins, and minerals supports their "
    "energy levels, immune system, coat condition, and long-term organ health. "
    "Every meal is an opportunity to invest in a longer, healthier life for your pet."
)


async def _generate_nutrition_importance_gpt(pet: Pet) -> dict:
    """
    Generate a warm 3-4 sentence note on why nutrition matters for this specific pet.

    Personalised to species, breed, and age so the note feels relevant rather than generic.

    Returns:
        {"note": "<3-4 sentence plain-text note>"}
    """
    age_years: float = (date.today() - pet.dob).days / 365.25 if pet.dob else 2.0
    breed_str = pet.breed or pet.species

    system_prompt = (
        "You are a friendly pet nutritionist writing a short note for a pet owner's health dashboard. "
        "Write a warm, practical 3-4 sentence note explaining why good nutrition is especially important "
        f"for a {age_years:.1f}-year-old {pet.species} of the {breed_str} breed. "
        "Cover their life stage, species-specific dietary needs, and the long-term health benefits. "
        "Be encouraging and parent-friendly. Plain text only — no bullets, headers, or markdown."
    )

    client = _get_openai_client()

    async def _call() -> str:
        response = await client.messages.create(
            model=OPENAI_QUERY_MODEL,
            temperature=0.6,
            max_tokens=200,
            system=system_prompt,
            messages=[{"role": "user", "content": "Generate the nutrition importance note."}],
        )
        return response.content[0].text or ""

    try:
        note = await retry_openai_call(_call)
        note = note.strip()
        if not note:
            raise ValueError("Empty response")
        return {"note": note}
    except Exception as exc:
        logger.warning("nutrition_importance GPT failed: %s", exc)
        return {"note": _NUTRITION_IMPORTANCE_FALLBACK}


async def get_or_generate_nutrition_importance(db: Session, pet_id: UUID) -> dict:
    """
    Return a cached 'why nutrition matters' note for this pet, or generate a fresh one.

    Cached for NUTRITION_IMPORTANCE_CACHE_DAYS (30 days). Stored in pet_ai_insights
    with insight_type='nutrition_importance'.

    Args:
        db:     SQLAlchemy session.
        pet_id: Pet UUID.

    Returns:
        {"note": "<plain-text nutrition importance note>"}
    """
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=NUTRITION_IMPORTANCE_CACHE_DAYS)
    insight_repo = PetAiInsightRepository(db)
    pet_repo = PetRepository(db)

    existing = insight_repo.find_non_stale_by_pet_and_type(pet_id, "nutrition_importance", stale_cutoff)
    if existing:
        return existing.content_json

    # Load pet for personalisation
    pet = pet_repo.get_by_id(pet_id)
    if not pet:
        return {"note": _NUTRITION_IMPORTANCE_FALLBACK}

    content = await _generate_nutrition_importance_gpt(pet)

    try:
        insight_repo.upsert_insight(pet_id, "nutrition_importance", content)
        db.commit()
    except Exception as exc:
        logger.error("Failed to upsert nutrition_importance insight: %s", exc)
        db.rollback()

    return content


async def generate_recognition_bullets(db: Session, pet: Pet) -> list[Bullet]:
    """
    Build deterministic recognition bullets for the dashboard's What We Found card.

    Bullets are observational and traceable to DB records only (no GPT).
    Output order is fixed: conditions first, preventive second, diet last.

    Args:
        db: SQLAlchemy session.
        pet: Pet model instance.

    Returns:
        Up to three bullets of shape {icon, label}.
    """
    if not pet:
        return []

    condition_repo = ConditionRepository(db)
    active_conditions = condition_repo.find_displayable_active(pet.id)
    active_condition_count = len(active_conditions)

    from app.repositories.preventive_repository import PreventiveRepository
    preventive_repo = PreventiveRepository(db)
    vaccine_count, other_preventive_count = preventive_repo.count_core_split_by_vaccine(
        pet.id, _VACCINE_BULLET_TERMS
    )
    on_schedule_preventive_count = vaccine_count + other_preventive_count

    diet_repo = DietRepository(db)
    diet_items = diet_repo.find_by_pet_id(pet.id)

    bullets: list[Bullet] = []

    # 1. Conditions — always present
    if active_condition_count > 0:
        bullets.append(
            {
                "icon": "🩺",
                "label": (
                    f"{active_condition_count} active condition"
                    f"{'s' if active_condition_count != 1 else ''} being managed"
                ),
            }
        )
    else:
        bullets.append(
            {"icon": "🩺", "label": "No health conditions found"}
        )

    # 2. Preventive care — split into vaccines vs other preventive items
    if on_schedule_preventive_count > 0:
        if vaccine_count > 0 and other_preventive_count > 0:
            label = (
                f"{vaccine_count} vaccine{'s' if vaccine_count != 1 else ''} and "
                f"{other_preventive_count} preventive care item"
                f"{'s' if other_preventive_count != 1 else ''} tracked"
            )
        elif vaccine_count > 0:
            label = f"{vaccine_count} vaccine{'s' if vaccine_count != 1 else ''} tracked"
        else:
            label = (
                f"{other_preventive_count} preventive care item"
                f"{'s' if other_preventive_count != 1 else ''} tracked"
            )
        bullets.append({"icon": "💉", "label": label})
    else:
        bullets.append(
            {"icon": "💉", "label": "0 preventive care items tracked"}
        )

    # 3. Diet — chat/manual entries only (packaged + homemade not from documents, manual supplements).
    # Document-extracted items (vet-prescribed food, avoid instructions, supplements) go to bullet 4.
    food_items = [
        d for d in diet_items
        if d.type in ("packaged", "homemade")
        and (d.source or "").lower() != "document_extracted"
    ]
    supplement_items = [d for d in diet_items if d.type == "supplement" and (d.source or "").lower() == "manual"]

    if food_items or supplement_items:
        bullets.append(
            {"icon": "🍽️", "label": _format_found_diet_summary(food_items, supplement_items)}
        )
    else:
        bullets.append({"icon": "🍽️", "label": "No diet entries recorded"})

    # 4. Prescribed diet — document-extracted diet items (food or supplement from documents)
    doc_diet_items = [
        d for d in diet_items
        if (d.source or "").lower() == "document_extracted"
        and d.type in ("packaged", "homemade", "supplement")
    ]
    if doc_diet_items:
        seen_labels: set[str] = set()
        unique_labels: list[str] = []
        for d in doc_diet_items:
            lbl = (d.label or "").strip()
            if lbl and lbl.lower() not in seen_labels:
                seen_labels.add(lbl.lower())
                unique_labels.append(lbl)
        if unique_labels:
            if len(unique_labels) == 1:
                prescribed_str = unique_labels[0]
            elif len(unique_labels) == 2:
                prescribed_str = f"{unique_labels[0]} and {unique_labels[1]}"
            else:
                prescribed_str = ", ".join(unique_labels[:-1]) + f" and {unique_labels[-1]}"
            bullets.append({"icon": "📋", "label": f"Prescribed diet: {prescribed_str}"})

    return bullets[:4]


def _extract_orderable_item_key_and_name(item: dict[str, Any]) -> tuple[str, str] | None:
    """Extract a stable id and display name from an orderable item payload."""
    if not isinstance(item, dict):
        return None
    item_id = item.get("item_id") or item.get("id") or item.get("name")
    item_name = item.get("name") or item.get("label") or item_id
    if not item_id or not item_name:
        return None
    return str(item_id), str(item_name)


async def generate_care_plan_reasons(
    db: Session,
    pet: Pet,
    orderable_items: list[dict[str, Any]],
    diet_summary: dict | None = None,
) -> dict[str, str]:
    """
    Generate one-sentence reasons for orderable care plan items.

    Results are cached in pet_ai_insights with a 1-hour TTL.  Using a short
    TTL (rather than the 7-day insight TTL) ensures reasons stay current when
    care-plan items change, while preventing every dashboard load from hitting
    the Claude API concurrently.

    Args:
        db: SQLAlchemy session.
        pet: Pet model instance.
        orderable_items: List of orderable item payloads with id/name fields.
        diet_summary: Pre-computed diet summary dict; if provided, skips the
            get_diet_summary() OpenAI call to avoid a redundant round-trip.

    Returns:
        Mapping of item_id -> reason sentence.
    """
    if not pet or not orderable_items:
        return {}

    _CARE_PLAN_REASONS_CACHE_HOURS = 1
    _CARE_PLAN_REASONS_INSIGHT_TYPE = "care_plan_reasons"

    # --- Cache check (1-hour TTL) ---
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=_CARE_PLAN_REASONS_CACHE_HOURS)
    insight_repo = PetAiInsightRepository(db)
    try:
        cached = insight_repo.find_non_stale_by_pet_and_type(pet.id, _CARE_PLAN_REASONS_INSIGHT_TYPE, stale_cutoff)
        if cached and isinstance(cached.content_json, dict):
            return cached.content_json.get("reasons", {})
    except Exception as exc:
        logger.warning("care_plan_reasons cache read failed for pet %s: %s", pet.id, exc)

    try:
        item_map: dict[str, str] = {}
        for item in orderable_items:
            extracted = _extract_orderable_item_key_and_name(item)
            if extracted:
                item_id, item_name = extracted
                item_map[item_id] = item_name

        if not item_map:
            return {}

        condition_repo = ConditionRepository(db)
        active_conditions = condition_repo.find_by_pet_and_active(pet.id)
        condition_names = [c.name for c in active_conditions if c and c.name]

        age_months = _get_pet_age_months(pet)
        try:
            weight_kg = float(pet.weight) if pet.weight is not None else None
        except (TypeError, ValueError):
            weight_kg = None

        breed_size = _get_breed_size(weight_kg, pet.breed)
        life_stage = _get_life_stage(age_months, breed_size).value

        # Use caller-supplied diet_summary to avoid a redundant OpenAI call when
        # the dashboard has already fetched it in the parallel enrichment phase.
        nutrition_summary = diet_summary or {"macros": [], "missing_micros": []}
        missing_micros = nutrition_summary.get("missing_micros", [])
        nutrition_gap_names = [
            str(gap.get("name"))
            for gap in missing_micros
            if isinstance(gap, dict) and gap.get("name")
        ]
    except Exception as exc:
        logger.warning("care_plan_reasons context build failed for pet %s: %s", pet.id, exc)
        return {}

    conditions_text = ", ".join(condition_names) if condition_names else "none"
    nutrition_gaps_text = ", ".join(nutrition_gap_names) if nutrition_gap_names else "none identified"
    items_text = "\n".join([f"- {item_id}: {name}" for item_id, name in item_map.items()])

    system_prompt = (
        "You are a veterinary care-plan assistant. "
        "For each orderable item id, write exactly one sentence that explains why the item is relevant "
        "based on life stage, active health context, and nutrition context. "
        "Return ONLY a valid JSON object where each key is item id and each value is the reason string. "
        "No markdown, no extra keys, no recommendations beyond context, and no alarming language."
    )

    user_prompt = (
        f"Pet: {pet.name} ({pet.species}, breed={pet.breed or 'unknown'})\n"
        f"Life stage: {life_stage}\n"
        f"Active conditions: {conditions_text}\n"
        f"Nutrition gaps: {nutrition_gaps_text}\n"
        "Orderable items:\n"
        f"{items_text}"
    )

    client = _get_openai_client()

    async def _call() -> str:
        response = await client.messages.create(
            model=OPENAI_QUERY_MODEL,
            temperature=0,
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.content[0].text or "{}"

    try:
        raw = await retry_openai_call(_call)
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object for care plan reasons")

        reasons: dict[str, str] = {}
        for item_id in item_map:
            reason = parsed.get(item_id)
            if not isinstance(reason, str):
                continue
            one_line_reason = " ".join(reason.strip().split())
            if not one_line_reason:
                continue
            if not one_line_reason.endswith((".", "!", "?")):
                one_line_reason = f"{one_line_reason}."
            reasons[item_id] = one_line_reason

        # --- Persist to cache (only if GPT returned usable reasons) ---
        if reasons:
            try:
                insight_repo.upsert_insight(pet.id, _CARE_PLAN_REASONS_INSIGHT_TYPE, {"reasons": reasons})
                db.commit()
            except Exception as cache_exc:
                logger.warning("care_plan_reasons cache write failed for pet %s: %s", pet.id, cache_exc)
                db.rollback()

        return reasons
    except Exception as exc:
        logger.warning("care_plan_reasons generation failed for pet %s: %s", pet.id, exc)
        return {}
