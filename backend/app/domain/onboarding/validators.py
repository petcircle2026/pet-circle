"""
Pure input validation functions for onboarding (no DB, no I/O).

Intent detection (yes/no/skip/doc-skip) uses the LLM for flexibility.
Structural validators (name, weight, phone) remain purely deterministic.
Returns (bool, str) tuples: (is_valid, error_message).
"""

import logging
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)

# Minimal universal yes/no signals that need no LLM (single chars / unambiguous abbrevs)
_DEFINITE_YES = frozenset({"yes", "y", "yep", "yup", "yeah", "ok", "okay", "haan"})
_DEFINITE_NO = frozenset({"no", "n", "nope", "nahi", "na"})
_DEFINITE_SKIP = frozenset({"skip", "s", "later", "n/a"})

_GENERIC_VAX_LABELS = frozenset({
    "vaccines", "shots", "vaccine", "shot",
    "vaccinated", "vaccinations", "vaccine shots",
    "rabies", "general", "booster", "boosters",
    "primary vaccines", "routine vaccines",
})

_PENDING_VACCINE_PHRASES = (
    "should be given", "need to give", "needs to give", "not yet given",
    "not yet", "pending", "to be given", "yet to give", "yet to be given",
    "supposed to", "have to give", "has to be given", "will give", "will be given",
)

_SPECIES_INTENT_PATTERNS: dict[str, tuple[str, ...]] = {
    "dog": (r"\bdog\b", r"\bdogs\b", r"\bpuppy\b", r"\bcanine\b"),
    "cat": (r"\bcat\b", r"\bcats\b", r"\bkitten\b", r"\bfeline\b"),
    "rabbit": (r"\brabbit\b", r"\brabbits\b", r"\bbunny\b", r"\bbunnies\b", r"\bholland\s+lop\b"),
    "bird": (r"\bbird\b", r"\bbirds\b", r"\bparrot\b", r"\bparakeet\b", r"\bcockatiel\b"),
    "fish": (r"\bfish\b", r"\bfishes\b", r"\bgoldfish\b", r"\bbetta\b"),
    "hamster": (r"\bhamster\b", r"\bhamsters\b"),
    "guinea pig": (r"\bguinea\s+pig\b", r"\bguinea\s+pigs\b"),
    "turtle": (r"\bturtle\b", r"\btortoise\b"),
}


async def _llm_intent(text: str, question: str) -> bool:
    """Ask the LLM whether text expresses a given intent. Returns True/False."""
    from app.core.constants import OPENAI_QUERY_MODEL
    from app.utils.ai_client import get_ai_client

    client = get_ai_client()
    try:
        response = await client.messages.create(
            model=OPENAI_QUERY_MODEL,
            temperature=0.0,
            max_tokens=5,
            system=(
                f"Answer only YES or NO. {question}"
            ),
            messages=[{"role": "user", "content": text}],
        )
        answer = response.content[0].text.strip().upper()
        return answer.startswith("Y")
    except Exception as e:
        logger.warning("LLM intent check failed, defaulting False: %s", e)
        return False


def is_yes_intent(text: str | None) -> bool:
    """Return True if text is a yes-like response (sync, uses minimal signal set)."""
    if not text:
        return False
    return str(text).strip().lower() in _DEFINITE_YES


def is_no_intent(text: str | None) -> bool:
    """Return True if text is a no-like response (sync, uses minimal signal set)."""
    if not text:
        return False
    return str(text).strip().lower() in _DEFINITE_NO


def is_skip_intent(text: str | None) -> bool:
    """Return True if user wants to skip this field."""
    if not text:
        return False
    return str(text).strip().lower() in _DEFINITE_SKIP


async def is_doc_skip_intent_async(text: str | None) -> bool:
    """Return True when user indicates they are skipping document upload (LLM-backed)."""
    if not text:
        return False
    normalized = text.strip().lower()

    # Fast path for unambiguous signals.
    if normalized in _DEFINITE_SKIP or normalized in _DEFINITE_NO:
        return True
    # Upload intent words are a hard negative.
    if any(w in normalized for w in ("upload", "sending", "send", "attach", "attached")):
        return False

    return await _llm_intent(
        text,
        "Does the user's message mean they want to skip uploading a document right now "
        "(e.g. 'no records', 'maybe later', 'move on', 'continue without uploading')? "
        "Answer YES or NO.",
    )


# Keep a sync shim so existing callers that haven't been migrated yet still work.
def is_doc_skip_intent(text_lower: str) -> bool:
    """Sync fallback — checks only the definite-skip signals."""
    normalized = (text_lower or "").strip()
    if normalized in _DEFINITE_SKIP or normalized in _DEFINITE_NO:
        return True
    return False


def is_generic_vaccine_mention(parsed: dict) -> bool:
    """
    Return True if parsed data contains a generic vaccine mention with no
    specific vaccine name.
    """
    generic = parsed.get("vaccines")
    vaccine_specifics = parsed.get("vaccine_specifics") or []

    if generic and generic != "none":
        real_specifics = [
            s for s in vaccine_specifics
            if isinstance(s, dict)
            and str(s.get("name") or "").strip().lower() not in _GENERIC_VAX_LABELS
            and str(s.get("date") or "").strip()
        ]
        return len(real_specifics) == 0

    generic_entries = [
        s for s in vaccine_specifics
        if isinstance(s, dict)
        and str(s.get("name") or "").strip().lower() in _GENERIC_VAX_LABELS
        and str(s.get("date") or "").strip()
    ]
    real_entries = [
        s for s in vaccine_specifics
        if isinstance(s, dict)
        and str(s.get("name") or "").strip().lower() not in _GENERIC_VAX_LABELS
        and str(s.get("date") or "").strip()
    ]
    return bool(generic_entries) and not real_entries


def is_flea_without_brand(parsed: dict) -> bool:
    """Return True if GPT detected flea/tick date but no medicine/brand name."""
    flea_tick = parsed.get("flea_tick")
    if not flea_tick or flea_tick == "none":
        return False
    if isinstance(flea_tick, dict):
        date_val = (flea_tick.get("date") or "").strip()
        medicine = (flea_tick.get("medicine") or "").strip()
        return bool(date_val) and not medicine
    return bool(str(flea_tick).strip())


def is_pending_vaccine_intent(raw: str | None) -> bool:
    """True if user expressed 'vaccines not yet given' intent rather than a date."""
    if not raw:
        return False
    n = str(raw).strip().lower()
    return any(phrase in n for phrase in _PENDING_VACCINE_PHRASES)


def looks_like_vaccine_selection(text: str) -> bool:
    """Return True if text is a deliberate vaccine type selection (options 1-4 or keywords)."""
    t = text.strip().lower()
    t = re.sub(r"[.!?,]+$", "", t)

    never_keywords = {
        "never", "never done", "not vaccinated", "no vaccine", "no vaccines",
        "none", "nope", "n/a", "na", "skip", "not done", "not sure",
    }
    vaccine_phrases = {
        "mandatory", "mandatory only", "only mandatory",
        "rabies and dhppi", "rabies + dhppi", "dhppi and rabies",
        "mandatory + corona", "corona", "mandatory + coronavirus",
        "mandatory + kennel cough", "kennel cough", "mandatory + kennel",
        "all", "all four", "all 4", "all vaccines", "all four vaccines",
    }
    vaccine_keywords = any(kw in t for kw in ("kennel", "corona", "rabies", "dhppi", "bordetella"))

    return (
        t in {"1", "2", "3", "4"}
        or t in never_keywords
        or t in _DEFINITE_YES
        or is_pending_vaccine_intent(t)
        or t in vaccine_phrases
        or vaccine_keywords
    )


def is_valid_pet_name(name: str | None) -> tuple[bool, str]:
    """Validate pet name: non-empty, no special chars, reasonable length."""
    if not name or not str(name).strip():
        return False, "Pet name cannot be empty"

    name = str(name).strip()
    if len(name) > 50:
        return False, "Pet name too long (max 50 chars)"
    if len(name) < 2:
        return False, "Pet name too short (min 2 chars)"
    if not re.match(r"^[a-zA-Z0-9\s\-']+$", name):
        return False, "Pet name contains invalid characters"

    return True, ""


def is_valid_breed(breed: str | None) -> tuple[bool, str]:
    """Validate breed name: non-empty, reasonable length."""
    if not breed or not str(breed).strip():
        return False, "Breed cannot be empty"

    breed = str(breed).strip()
    if len(breed) > 100:
        return False, "Breed name too long (max 100 chars)"
    if len(breed) < 2:
        return False, "Breed name too short (min 2 chars)"

    return True, ""


def is_valid_weight_kg(weight: float | None, max_weight: float = 150.0) -> tuple[bool, str]:
    """Validate weight in kg: positive, reasonable range."""
    if weight is None:
        return False, "Weight cannot be empty"

    try:
        w = float(weight)
    except (ValueError, TypeError):
        return False, "Weight must be a number"

    if w <= 0:
        return False, "Weight must be positive"
    if w > max_weight:
        return False, f"Weight too high (max {max_weight}kg)"

    return True, ""


def is_valid_age(age: float | None) -> tuple[bool, str]:
    """Validate age in years: positive, reasonable range."""
    if age is None:
        return False, "Age cannot be empty"

    try:
        a = float(age)
    except (ValueError, TypeError):
        return False, "Age must be a number"

    if a < 0:
        return False, "Age cannot be negative"
    if a > 30:
        return False, "Age seems unreasonable (max 30 years)"

    return True, ""


def is_valid_gender(gender: str | None) -> tuple[bool, str]:
    """Validate gender: must be Male, Female, or Other."""
    if not gender:
        return False, "Gender cannot be empty"

    gender = str(gender).strip().lower()
    if gender not in {"male", "female", "other", "m", "f"}:
        return False, "Gender must be Male, Female, or Other"

    return True, ""


def is_valid_neuter_spay_status(status: str | None) -> tuple[bool, str]:
    """Validate neuter/spay status: yes, no, or unknown."""
    if not status:
        return False, "Neuter/spay status cannot be empty"

    status = str(status).strip().lower()
    if status not in {"yes", "no", "unknown", "not sure", "y", "n"}:
        return False, "Must answer yes, no, or unknown"

    return True, ""


def is_valid_phone(phone: str | None) -> tuple[bool, str]:
    """Validate phone number: must be 10 digits (India format)."""
    if not phone:
        return False, "Phone cannot be empty"

    phone = re.sub(r"\D", "", str(phone).strip())
    if len(phone) != 10:
        return False, "Phone must be 10 digits"

    return True, ""
