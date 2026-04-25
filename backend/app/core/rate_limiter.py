"""
PetCircle Phase 1 â€” In-Memory Rate Limiter

Enforces per-key rate limiting using a sliding window algorithm.
Used for WhatsApp messages (per phone number), dashboard (per IP),
and admin endpoints (per IP).

Implementation:
    - Tracks timestamps of recent requests per key in a deque.
    - On each check, expired timestamps are evicted.
    - If the count exceeds the limit, the request is rejected.

Limitations:
    - In-memory only â€” resets on server restart.
    - Not shared across multiple worker processes.
    - Sufficient for Phase 1 single-process deployment on Render.
"""

import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.constants import MAX_MESSAGES_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter keyed by arbitrary string.

    Tracks request timestamps in a deque per key. Expired entries
    are pruned on each check to keep memory bounded.
    """

    def __init__(
        self,
        max_requests: int = MAX_MESSAGES_PER_MINUTE,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
    ):
        """
        Initialize the rate limiter.

        Args:
            max_requests: Maximum allowed requests within the window.
            window_seconds: Rolling window duration in seconds.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque] = defaultdict(deque)

    def check_rate_limit(self, key: str) -> bool:
        """
        Check whether a request from the given key is allowed.

        Evicts expired timestamps, then checks if the count is under the limit.
        If allowed, records the current timestamp. Cleans up empty keys to
        prevent unbounded memory growth from inactive users.

        Args:
            key: The rate limit key (phone number, IP address, etc.).

        Returns:
            True if the request is allowed, False if rate-limited.
        """
        now = time.monotonic()
        window_start = now - self.window_seconds

        # Evict expired timestamps
        timestamps = self._requests[key]
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        # Remove the key entirely if no timestamps remain â€” prevents memory leak
        # from accumulating keys for users who are no longer active.
        if not timestamps:
            del self._requests[key]
            # Re-create for the current request below.
            timestamps = self._requests[key]

        if len(timestamps) >= self.max_requests:
            return False

        timestamps.append(now)
        return True


# --- Singleton instances ---

# WhatsApp message rate limiter â€” 20 requests/min per phone number.
rate_limiter = RateLimiter()

# Dashboard endpoint rate limiter â€” 120 requests/min per IP.
# Raised from 30: Vercel edge nodes share IPs across users, so the lower
# limit caused legitimate users to hit 429s during normal tab browsing.
dashboard_rate_limiter = RateLimiter(max_requests=120, window_seconds=60)

# Admin endpoint rate limiter â€” 10 requests/min per IP.
# Stricter limit to protect admin key brute-force attempts.
admin_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


def _get_client_ip(request: Request) -> str:
    """
    Extract the client IP from a FastAPI request.

    Uses X-Forwarded-For header if present (behind reverse proxy),
    otherwise falls back to the direct client host.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs; the first is the client.
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_dashboard_token(request: Request) -> str | None:
    """
    Extract the dashboard token from the request path.

    Dashboard paths have the form /dashboard/{token}/... so the token
    is always at path index 1 (after stripping the leading slash).
    Returns None if the path doesn't match the expected shape.
    """
    parts = request.url.path.strip("/").split("/")
    # parts[0] == "dashboard", parts[1] == token
    if len(parts) >= 2 and parts[0] == "dashboard" and len(parts[1]) >= 16:
        return parts[1]
    return None


async def check_dashboard_rate_limit(request: Request) -> None:
    """
    FastAPI dependency that enforces per-token rate limiting on dashboard routes.

    Uses the dashboard token from the URL path as the rate-limit key so that
    each user gets an independent 120 req/min budget. Falls back to client IP
    if the token cannot be extracted (e.g. health-check or malformed path).

    Raises HTTPException 429 if the key exceeds 120 requests/minute.
    """
    token = _get_dashboard_token(request)
    key = token if token else _get_client_ip(request)
    if not dashboard_rate_limiter.check_rate_limit(key):
        logger.warning(
            "Dashboard rate limit exceeded for %s=%s",
            "token" if token else "IP",
            key[:8] + "â€¦" if token else key,
        )
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        )


async def check_admin_rate_limit(request: Request) -> None:
    """
    FastAPI dependency that enforces IP-based rate limiting on admin routes.

    Raises HTTPException 429 if the client IP exceeds 10 requests/minute.
    """
    client_ip = _get_client_ip(request)
    if not admin_rate_limiter.check_rate_limit(client_ip):
        logger.warning("Admin rate limit exceeded for IP=%s", client_ip)
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        )

