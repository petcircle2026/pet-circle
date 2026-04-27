"""
PetCircle — Breed Normalizer

Uses an LLM to identify pet breeds from user-supplied text (abbreviations,
misspellings, regional names). The LLM is the primary path; a title-case
fallback is used only when the LLM is unavailable.
"""

import logging

logger = logging.getLogger(__name__)

# In-process alias cache so repeated inputs skip API calls.
_LEARNED_ALIASES: dict[str, str] = {}


async def normalize_breed(breed: str, species: str | None = None) -> str:
    """
    Normalise a breed string using the LLM.

    Args:
        breed:   Raw breed text from the user.
        species: "dog", "cat", etc. for context.

    Returns:
        Standardised breed name, or title-cased original if LLM unavailable.
    """
    if not breed:
        return breed

    cache_key = f"{species or ''}:{breed.lower().strip()}"
    if cache_key in _LEARNED_ALIASES:
        return _LEARNED_ALIASES[cache_key]

    result = await normalize_breed_with_ai(breed, species)
    _LEARNED_ALIASES[cache_key] = result
    return result


async def normalize_breed_with_ai(breed: str, species: str | None = None) -> str:
    """
    Use the LLM to identify a breed.

    Args:
        breed:   Raw breed text from the user.
        species: "dog" or "cat" for context.

    Returns:
        Standardised breed name, or title-cased original if LLM fails.
    """
    from app.core.constants import OPENAI_QUERY_MODEL
    from app.utils.ai_client import get_ai_client

    animal = species or "pet"
    client = get_ai_client()

    try:
        response = await client.messages.create(
            model=OPENAI_QUERY_MODEL,
            temperature=0.0,
            max_tokens=30,
            system=(
                f"You are a {animal} breed identifier. The user will provide text "
                f"that may be a breed name, abbreviation, misspelling, or local name. "
                f"Identify the standardised {animal} breed name and return ONLY the "
                f"breed name. If it is clearly a mixed breed, return 'Mixed Breed'. "
                f"If you cannot identify any breed, return 'UNKNOWN'."
            ),
            messages=[{"role": "user", "content": breed}],
        )

        result = response.content[0].text.strip()
        if result == "UNKNOWN":
            return breed.strip().title()
        return result

    except Exception as e:
        logger.error("AI breed identification failed for '%s': %s", breed, str(e))
        return breed.strip().title()
