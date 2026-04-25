"""
AI-driven parsing functions for onboarding (pure functions, no DB, no state).

These parse GPT responses and user input into structured data.
All functions are async and use retry_openai_call for resilience.
"""

import json
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

_openai_parser_client = None


def _get_openai_parser_client():
    """Return a cached AI client for parsing."""
    global _openai_parser_client
    if _openai_parser_client is None:
        from app.utils.ai_client import get_ai_client
        _openai_parser_client = get_ai_client()
    return _openai_parser_client


def strip_json_fences(raw: str) -> str:
    """
    Strip markdown code fences from a model JSON response.

    Also handles preamble text before the JSON object. After fence-stripping,
    if result doesn't start with '{', we scan for the outermost { ... } pair
    and extract only that portion.

    Raises ValueError when no JSON object can be found.
    """
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    # If there is non-JSON preamble, extract the first complete JSON object.
    if raw and not raw.startswith("{"):
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            raw = raw[start : end + 1]
    if not raw:
        raise ValueError("Response returned an empty JSON body")
    return raw


async def parse_breed_age(text: str) -> dict:
    """
    Use GPT to extract breed and approximate age from combined input.

    Returns dict with keys:
        breed (str|None), species ("dog"|"cat"|None),
        age_years (float|None), age_text (str|None),
        dob (str|None â€” ISO date if explicitly given), confident (bool)
    """
    from app.core.constants import OPENAI_QUERY_MODEL
    from app.utils.retry import retry_openai_call

    client = _get_openai_parser_client()
    today_str = date.today().isoformat()
    prompt = (
        f"Today's date is {today_str}. "
        "Extract the pet breed and approximate age from this message. "
        "Also determine if this is a dog or cat breed. "
        'Return ONLY valid JSON, no markdown: '
        '{"breed": "...", "species": "dog"|"cat"|null, '
        '"age_years": number|null, "age_text": "original age text", '
        '"dob": "YYYY-MM-DD"|null, "confident": true|false}. '
        "If the breed is clearly identifiable, set confident=true. "
        "If the breed is ambiguous or unrecognizable, set confident=false. "
        "For age, accept years, months, or life stage words "
        '(puppy=0.5, kitten=0.5, junior=1.5, adult=4, senior=9). '
        "If the user provides a date of birth (like '11/11/2021', '11 Nov 21', etc.), "
        "convert it to ISO format (YYYY-MM-DD) in the 'dob' field AND compute age_years "
        "from today's date. Use the 2-digit year rule: 00-30 = 2000s, 31-99 = 1900s. "
        "If the user gives only an age in years or months (e.g. '2 years', '6 months') "
        "without an explicit birth date, set dob to null â€” do NOT compute a dob from the age. "
        "If no age is given, set age_years, age_text, and dob to null.\n\n"
        f"User message: {text}"
    )
    try:
        response = await retry_openai_call(
            client.messages.create,
            model=OPENAI_QUERY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
        )
        raw = strip_json_fences(response.content[0].text.strip())
        data = json.loads(raw)
        return {
            "breed": data.get("breed"),
            "species": data.get("species"),
            "age_years": data.get("age_years"),
            "age_text": data.get("age_text"),
            "dob": data.get("dob"),
            "confident": data.get("confident", False),
        }
    except Exception as e:
        logger.warning("Breed/age parse failed: %s", str(e))
        return {
            "breed": None,
            "species": None,
            "age_years": None,
            "age_text": None,
            "dob": None,
            "confident": False,
        }


async def parse_gender_weight(text: str) -> dict:
    """
    Use GPT to extract gender and weight (kg) from user input.

    Returns dict with keys:
        gender ("male"|"female"|None), weight_kg (float|None)
    """
    from app.core.constants import OPENAI_QUERY_MODEL
    from app.utils.retry import retry_openai_call

    client = _get_openai_parser_client()
    prompt = (
        "Extract the pet's gender and weight in kg from this message. "
        'Return ONLY valid JSON, no markdown: '
        '{"gender": "male"|"female"|null, "weight_kg": number|null}. '
        "Accept colloquial inputs: 'boy'/'he'/'him'='male', 'girl'/'she'/'her'='female'. "
        "If weight is given without units, assume kg.\n\n"
        f"User message: {text}"
    )
    try:
        response = await retry_openai_call(
            client.messages.create,
            model=OPENAI_QUERY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=80,
        )
        raw = strip_json_fences(response.content[0].text.strip())
        data = json.loads(raw)
        return {
            "gender": data.get("gender"),
            "weight_kg": data.get("weight_kg"),
        }
    except Exception as e:
        logger.warning("Gender/weight parse failed: %s", str(e))
        return {"gender": None, "weight_kg": None}


async def parse_gender_weight_neutered(text: str) -> dict:
    """
    Use GPT to extract gender, weight (kg), and neuter/spay status from input.

    Returns dict with keys:
        gender ("male"|"female"|None), weight_kg (float|None),
        neutered ("yes"|"no"|"unknown"|None)
    """
    from app.core.constants import OPENAI_QUERY_MODEL
    from app.utils.retry import retry_openai_call

    client = _get_openai_parser_client()
    prompt = (
        "Extract the pet's gender, weight in kg, and neuter/spay status from this message. "
        'Return ONLY valid JSON, no markdown: '
        '{"gender": "male"|"female"|null, "weight_kg": number|null, '
        '"neutered": "yes"|"no"|"unknown"|null}. '
        "For neuter status, accept: 'yes'/'neutered'/'spayed', 'no'/'not neutered', "
        "'unknown'/'not sure'. Colloquial gender inputs: 'boy'='male', 'girl'='female'.\n\n"
        f"User message: {text}"
    )
    try:
        response = await retry_openai_call(
            client.messages.create,
            model=OPENAI_QUERY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )
        raw = strip_json_fences(response.content[0].text.strip())
        data = json.loads(raw)
        return {
            "gender": data.get("gender"),
            "weight_kg": data.get("weight_kg"),
            "neutered": data.get("neutered"),
        }
    except Exception as e:
        logger.warning("Gender/weight/neutered parse failed: %s", str(e))
        return {"gender": None, "weight_kg": None, "neutered": None}


async def ai_decide_neuter_question(
    pet_name: str,
    gender: str | None,
    species: str | None,
    breed: str | None,
    age_text: str | None,
) -> dict:
    """
    AI agent that decides whether to ask about neutering/spaying.

    Uses the pet's gender, species, breed, and age to:
    - Ask "Is <name> neutered?" for males.
    - Ask "Is <name> spayed?" for females.
    - Ask "Is <name> neutered or spayed?" when gender is unknown.
    - Set should_ask=False only if the pet is clearly under ~3 months old.

    Returns dict: {"should_ask": bool, "question": str}
    """
    from app.core.constants import OPENAI_QUERY_MODEL
    from app.utils.retry import retry_openai_call

    client = _get_openai_parser_client()
    prompt = (
        "You are helping onboard a pet on a health tracking app. "
        "Decide whether to ask the owner about their pet's neutering or spaying status.\n\n"
        f"Pet name: {pet_name}\n"
        f"Gender: {gender or 'unknown'}\n"
        f"Species: {species or 'unknown'}\n"
        f"Breed: {breed or 'unknown'}\n"
        f"Age/DOB: {age_text or 'unknown'}\n\n"
        "Rules:\n"
        "- Use the word 'neutered' for males and 'spayed' for females.\n"
        "- If gender is unknown, use 'neutered or spayed'.\n"
        "- Set should_ask to false ONLY if the pet is clearly under 3 months old "
        "(too young for the procedure to be relevant). Otherwise always true.\n"
        "- Keep the question short and conversational.\n\n"
        'Return ONLY valid JSON, no markdown: {"should_ask": true|false, "question": "..."}'
    )
    try:
        response = await retry_openai_call(
            client.messages.create,
            model=OPENAI_QUERY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=120,
        )
        raw = strip_json_fences(response.content[0].text.strip())
        data = json.loads(raw)
        should_ask = bool(data.get("should_ask", True))
        question = data.get("question") or ""
        # Fallback question if AI returned empty.
        if should_ask and not question:
            if gender == "male":
                question = f"Is {pet_name} neutered?"
            elif gender == "female":
                question = f"Is {pet_name} spayed?"
            else:
                question = f"Is {pet_name} neutered or spayed?"
        return {"should_ask": should_ask, "question": question}
    except Exception as e:
        logger.warning("Neuter question decision failed: %s", str(e))
        # Safe fallback â€” always ask
        if gender == "male":
            question = f"Is {pet_name} neutered?"
        elif gender == "female":
            question = f"Is {pet_name} spayed?"
        else:
            question = f"Is {pet_name} neutered or spayed?"
        return {"should_ask": True, "question": question}

