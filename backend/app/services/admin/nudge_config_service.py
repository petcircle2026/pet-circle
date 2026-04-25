"""
PetCircle Phase 1 — Nudge Config Service

Reads nudge_config values from DB with in-memory caching (5 min TTL).
All nudge rate limits and intervals are DB-configurable via this service.
"""

import logging
import time

from sqlalchemy.orm import Session

from app.repositories.config_repository import ConfigRepository

logger = logging.getLogger(__name__)

# In-memory cache: {key: (value, timestamp)}
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def get_nudge_config(db: Session, key: str, default: str | None = None) -> str | None:
    """Get a nudge config value by key, with 5-min in-memory cache."""
    now = time.time()

    if key in _cache:
        cached_value, cached_at = _cache[key]
        if now - cached_at < _CACHE_TTL_SECONDS:
            return cached_value

    try:
        value = ConfigRepository(db).get_config(key)
        if value is not None:
            _cache[key] = (value, now)
            return value
    except Exception:
        logger.exception("Failed to read nudge_config key=%s", key)

    return default


def get_nudge_config_int(db: Session, key: str, default: int = 0) -> int:
    """Get a nudge config value as integer."""
    val = get_nudge_config(db, key)
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


