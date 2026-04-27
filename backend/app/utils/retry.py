"""
PetCircle Phase 1 - Retry Utilities (Module 17)

Provides retry wrappers for external API calls (Claude/Anthropic, WhatsApp).
Each wrapper has a specific retry policy tuned to the service's
failure characteristics.

Retry policies:
    - Claude/Anthropic: 3 attempts with 1s, 2s backoff (transient errors).
      429 rate-limit errors use longer 10s, 20s backoffs to allow TPM window
      recovery. A global semaphore (CLAUDE_API_CONCURRENCY) caps concurrent
      in-flight calls to prevent exhausting the token-per-minute quota.
      The semaphore is released during sleep so other callers can proceed
      while a rate-limited slot is waiting to retry.
    - WhatsApp: 2 attempts (1 retry). Log failure, continue.
    - Database: No retry - failures indicate constraint violations
      or connection issues that should not be silently retried.

Circuit breaker:
    - LLM calls are guarded by a per-service CircuitBreaker instance.
    - After CIRCUIT_BREAKER_FAILURE_THRESHOLD consecutive failures the
      circuit opens and subsequent calls fail immediately for
      CIRCUIT_BREAKER_RECOVERY_SECONDS, preventing retry storms.
    - A single probe attempt is allowed once the recovery window elapses.
      If the probe succeeds the circuit closes; if it fails the window
      resets and the circuit stays open.

These utilities ensure external API failures are isolated and
do not crash the main application flow.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.core.constants import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_RECOVERY_SECONDS,
    CLAUDE_API_CONCURRENCY,
    OPENAI_RATE_LIMIT_BACKOFFS,
    OPENAI_RETRY_BACKOFFS,
    WHATSAPP_MAX_RETRIES,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreakerOpen(Exception):
    """Raised when a call is rejected because the circuit is open."""


class CircuitBreaker:
    """
    Async-safe circuit breaker for external service calls.

    States:
        closed    - normal operation; failures are counted.
        open      - calls fail immediately; entered after
                    ``failure_threshold`` consecutive failures.
        half-open - one probe call is allowed after ``recovery_seconds``
                    to test whether the service has recovered.

    Thread/coroutine safety: all state mutations are protected by an
    asyncio.Lock so concurrent callers cannot race on state transitions.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_seconds: float = CIRCUIT_BREAKER_RECOVERY_SECONDS,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds

        self._failure_count: int = 0
        self._state: str = "closed"   # "closed" | "open" | "half-open"
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute *func* through the circuit breaker.

        Raises CircuitBreakerOpen if the circuit is open and the recovery
        window has not elapsed yet. Otherwise delegates to *func* and
        records success or failure accordingly.
        """
        async with self._lock:
            await self._maybe_transition_to_half_open()
            if self._state == "open":
                raise CircuitBreakerOpen(
                    f"Circuit '{self.name}' is open - service unavailable. "
                    f"Retry after {self._recovery_remaining():.0f}s."
                )

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            async with self._lock:
                self._on_failure()
            raise exc from exc

        async with self._lock:
            self._on_success()

        return result

    def reset(self) -> None:
        """Force-close the circuit (e.g. after manual intervention)."""
        self._state = "closed"
        self._failure_count = 0
        self._opened_at = 0.0
        logger.info("Circuit '%s' manually reset to closed", self.name)

    # ------------------------------------------------------------------
    # Internal helpers (must be called while holding _lock)
    # ------------------------------------------------------------------

    async def _maybe_transition_to_half_open(self) -> None:
        if self._state == "open" and self._recovery_remaining() <= 0:
            self._state = "half-open"
            logger.info(
                "Circuit '%s' -> half-open (probe allowed after %ss recovery)",
                self.name, self.recovery_seconds,
            )

    def _on_success(self) -> None:
        if self._state in ("half-open", "open"):
            logger.info("Circuit '%s' -> closed (probe succeeded)", self.name)
        self._state = "closed"
        self._failure_count = 0

    def _on_failure(self) -> None:
        self._failure_count += 1
        if self._state == "half-open":
            # Probe failed - reopen and reset recovery window.
            self._state = "open"
            self._opened_at = time.monotonic()
            logger.warning(
                "Circuit '%s' -> open (probe failed; next probe in %ss)",
                self.name, self.recovery_seconds,
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = "open"
            self._opened_at = time.monotonic()
            logger.error(
                "Circuit '%s' -> open after %d consecutive failures; "
                "fast-failing for %ss",
                self.name, self._failure_count, self.recovery_seconds,
            )

    def _recovery_remaining(self) -> float:
        return max(0.0, self.recovery_seconds - (time.monotonic() - self._opened_at))


# Process-wide circuit breaker instance for the LLM service.
# Shared across all coroutines so a storm of failures from any call site
# trips the breaker for the whole process, not just a single caller.
llm_circuit_breaker = CircuitBreaker(name="llm")


# ---------------------------------------------------------------------------
# Semaphore
# ---------------------------------------------------------------------------

# Global semaphore - limits concurrent in-flight Claude/Anthropic API calls
# across the whole process. Prevents TPM quota exhaustion under request bursts.
# Initialized eagerly at module load to avoid a lazy-init race where two coroutines
# both see None and create duplicate semaphores during cold-start.
_claude_semaphore = asyncio.Semaphore(CLAUDE_API_CONCURRENCY)


def _get_claude_semaphore() -> asyncio.Semaphore:
    """Return the process-wide Claude concurrency semaphore."""
    return _claude_semaphore


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True if *exc* is a 429 rate-limit error from Anthropic or OpenAI."""
    try:
        from anthropic import RateLimitError as AnthropicRateLimitError  # noqa: PLC0415
        if isinstance(exc, AnthropicRateLimitError):
            return True
    except ImportError:
        pass
    try:
        from openai import RateLimitError as OpenAIRateLimitError  # noqa: PLC0415
        if isinstance(exc, OpenAIRateLimitError):
            return True
    except ImportError:
        pass
    # Fallback: match status code or error type string.
    err_str = str(exc)
    return "rate_limit_error" in err_str or "429" in err_str


async def retry_openai_call(
    func: Callable[..., Any],
    *args: Any,
    call_timeout: float | None = None,
    max_retries: int | None = None,
    rate_limit_backoffs: list[float] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Retry wrapper for Claude/Anthropic API calls with circuit breaker protection.

    Default retry policy (background tasks):
        - Attempt 1: immediate (under semaphore)
        - Attempt 2: after 1s backoff  (10s for 429)
        - Attempt 3: after 2s backoff  (20s for 429)
        - If all 3 fail, raise the last exception

    Interactive policy (onboarding steps, set max_retries=1):
        - Attempt 1: immediate
        - Attempt 2: after 1s backoff  (3s for 429) - fails fast to fallback
        - Falls through to caller's fallback/default rather than hanging

    Circuit breaker:
        - If the circuit is open, CircuitBreakerOpen is raised immediately
          without attempting the call. After CIRCUIT_BREAKER_RECOVERY_SECONDS
          a single probe is allowed; on success the circuit closes.

    The semaphore is acquired per-attempt and released before sleeping so
    sleeping retriers do not starve other callers waiting for a slot.

    Args:
        func: The async callable that makes the Claude/Anthropic API call.
        *args: Positional arguments passed to func.
        call_timeout: Per-attempt timeout in seconds. Treats a timeout as a
            retryable failure. Set this on interactive paths to bound latency.
        max_retries: Override the number of retry attempts (not counting the
            first attempt). Defaults to len(OPENAI_RETRY_BACKOFFS). Set to 1
            for interactive onboarding calls so a 429 storm doesn't queue up
            users for 30+ seconds each.
        rate_limit_backoffs: Override the per-retry sleep durations used for
            429 errors. Defaults to OPENAI_RATE_LIMIT_BACKOFFS ([10, 20]).
            Interactive callers should pass [3] (matching max_retries=1) so
            a single 429 retries quickly rather than waiting 10s.
        **kwargs: Keyword arguments passed to func.

    Returns:
        The result of the successful API call.

    Raises:
        CircuitBreakerOpen: If the circuit is open and recovery has not elapsed.
        Exception: The last exception if all retry attempts fail.
    """
    backoffs = OPENAI_RETRY_BACKOFFS
    rl_backoffs = rate_limit_backoffs if rate_limit_backoffs is not None else OPENAI_RATE_LIMIT_BACKOFFS

    if max_retries is not None:
        # Trim backoff lists to match the requested retry count.
        backoffs = backoffs[:max_retries]
        rl_backoffs = rl_backoffs[:max_retries]

    last_exception = None
    total_attempts = 1 + len(backoffs)
    pending_backoff: float | None = None

    for attempt in range(total_attempts):
        # Sleep OUTSIDE the semaphore so the slot is free for other callers.
        if pending_backoff is not None:
            await asyncio.sleep(pending_backoff)
            pending_backoff = None

        async with _get_claude_semaphore():
            try:
                # Route through circuit breaker - raises CircuitBreakerOpen
                # immediately if the circuit is open and recovery hasn't elapsed.
                async def _invoke() -> Any:
                    if call_timeout is not None:
                        return await asyncio.wait_for(func(*args, **kwargs), timeout=call_timeout)
                    return await func(*args, **kwargs)

                return await llm_circuit_breaker.call(_invoke)
            except CircuitBreakerOpen:
                # Circuit is open - stop retrying immediately, surface to caller.
                raise
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(
                    "Claude/Anthropic call timed out after %ss (attempt %d/%d)",
                    call_timeout, attempt + 1, total_attempts,
                )
                if attempt < len(backoffs):
                    pending_backoff = backoffs[attempt]
                else:
                    logger.error(
                        "Claude/Anthropic call timed out after %d attempts",
                        total_attempts,
                    )
            except Exception as e:
                last_exception = e
                if attempt < len(backoffs):
                    # Use longer backoffs for rate-limit errors so the TPM
                    # window has time to reset before we retry.
                    if _is_rate_limit_error(e):
                        pending_backoff = rl_backoffs[attempt]
                    else:
                        pending_backoff = backoffs[attempt]
                    logger.warning(
                        "Claude/Anthropic call failed (attempt %d/%d), retrying in %ss: %s",
                        attempt + 1, total_attempts, pending_backoff, str(e)
                    )
                else:
                    # Final attempt failed - log and raise.
                    logger.error(
                        "Claude/Anthropic call failed after %d attempts: %s",
                        total_attempts, str(e)
                    )

    raise last_exception  # type: ignore[misc]


async def retry_whatsapp_call(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Retry wrapper for WhatsApp Cloud API calls.

    Retry policy:
        - Attempt 1: immediate
        - Attempt 2: immediate retry (no backoff)
        - If both fail, log the failure and return None
        - Never raises - WhatsApp failures must not crash the flow

    WhatsApp message delivery is best-effort. If a template message
    fails to send after 1 retry, the failure is logged but the
    application continues processing. This prevents WhatsApp outages
    from blocking the entire pipeline.

    Args:
        func: The async callable that makes the WhatsApp API call.
        *args: Positional arguments passed to func.
        **kwargs: Keyword arguments passed to func.

    Returns:
        The result of the successful API call, or None if all attempts fail.
    """
    total_attempts = 1 + WHATSAPP_MAX_RETRIES

    for attempt in range(total_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt < WHATSAPP_MAX_RETRIES:
                logger.warning(
                    "WhatsApp call failed (attempt %d/%d), retrying: %s",
                    attempt + 1, total_attempts, str(e)
                )
                # Brief pause before retry - prevents simultaneous burst failures
                # from all retrying at the same instant and colliding again.
                await asyncio.sleep(0.5)
            else:
                # Final attempt failed - log error but do not raise.
                # WhatsApp failures must never crash the processing flow.
                logger.error(
                    "WhatsApp call failed after %d attempts. "
                    "Continuing without sending message: %s",
                    total_attempts, str(e)
                )

    return None
