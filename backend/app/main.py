# PetCircle Phase 1 - FastAPI Application Entry Point
#
# Initializes the FastAPI app, validates environment configuration at startup,
# registers routers, and configures security middleware.
# No business logic lives here - only app bootstrapping.

import logging
import logging.config
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# ---------------------------------------------------------------------------
# Structured logging - JSON in production, human-readable in development.
# All modules use logging.getLogger(__name__) - this config wires them up.
# ---------------------------------------------------------------------------
_LOG_LEVEL = "DEBUG" if settings.APP_ENV == "development" else "INFO"

if settings.APP_ENV == "production":
    _FORMATTER = "json"
    _FORMATTERS = {
        "json": {
            "()": "logging.Formatter",
            "fmt": (
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","message":"%(message)s"}'
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        }
    }
else:
    _FORMATTER = "text"
    _FORMATTERS = {
        "text": {
            "format": "%(asctime)s %(levelname)-8s %(name)s - %(message)s",
            "datefmt": "%H:%M:%S",
        }
    }

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": _FORMATTERS,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": _FORMATTER,
        }
    },
    "root": {
        "handlers": ["console"],
        "level": _LOG_LEVEL,
    },
    "loggers": {
        # Suppress noisy third-party logs in production.
        "uvicorn.access": {"level": "WARNING" if settings.APP_ENV == "production" else "INFO"},
        "sqlalchemy.engine": {"level": "WARNING"},
    },
})

from app.core.constants import APP_API_TITLE
from app.routers import admin, dashboard, internal, webhook
from app.services.whatsapp.message_router import (
    start_document_window_sweeper,
    stop_document_window_sweeper,
)
from app.services.admin import queue_service, document_consumer

# Application initialization.
# Settings are validated at import time (app/config.py).
# If any required env var is missing, the app crashes before reaching this point.
# Swagger/redoc disabled in production to avoid exposing full API schema.
app = FastAPI(
    title=APP_API_TITLE,
    description="WhatsApp-based preventive pet health system - Phase 1",
    version="1.0.0",
    docs_url=None if settings.APP_ENV == "production" else "/docs",
    redoc_url=None if settings.APP_ENV == "production" else "/redoc",
    openapi_url=None if settings.APP_ENV == "production" else "/openapi.json",
)

# --- CORS Middleware ---
# Restrict cross-origin requests to the frontend dashboard URL only.
# Local origins are only added in development/test to prevent accidental
# production exposure of the API through a local browser.
_cors_origins = [settings.FRONTEND_URL]
if settings.APP_ENV != "production":
    _cors_origins += ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-ADMIN-KEY"],
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next) -> Response:
    """
    Assign a unique X-Request-ID to every request and propagate it through
    the response. Uses the caller-supplied header if present (allows upstream
    load balancers / API gateways to set their own trace IDs), otherwise
    generates a new UUID4.

    The ID is stored in request.state so downstream handlers can include it
    in log records for correlated failure debugging.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Add security headers to all HTTP responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Prevent browser/CDN caching of API responses containing sensitive data.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


# --- Register Routers ---
# Webhook router: /webhook/whatsapp (GET verify, POST messages)
app.include_router(webhook.router)
# Admin login router: /admin/login (password-based, no X-ADMIN-KEY required)
app.include_router(admin.login_router)
# Admin router: /admin/* (all routes require X-ADMIN-KEY header)
app.include_router(admin.router)
# Internal router: /internal/* (cron jobs, requires X-ADMIN-KEY header)
app.include_router(internal.router)
# Dashboard router: /dashboard/{token} (token-based access, no auth header)
app.include_router(dashboard.router)


@app.on_event("startup")
async def _start_background_reconciliation() -> None:
    """Start background reconciliation loops and the RabbitMQ consumer."""
    start_document_window_sweeper()
    # Connect to CloudAMQP and declare queues (no-op if CLOUDAMQP_URL not set).
    await queue_service.connect()
    # Start the in-process consumer as a background asyncio task.
    # Consumes document.extract and dashboard.precompute queues.
    # Store the task reference so stop() can cancel it on shutdown.
    import asyncio
    document_consumer._consumer_task = asyncio.create_task(
        document_consumer.start_consuming()
    )


@app.on_event("shutdown")
async def _stop_background_reconciliation() -> None:
    """Stop the RabbitMQ consumer and background reconciliation loops cleanly."""
    document_consumer.stop()
    await queue_service.close()
    await stop_document_window_sweeper()


@app.get("/health")
async def health_check():
    """
    Dependency-probing health check.

    Probes:
      - database: executes SELECT 1 against the configured Supabase/Postgres.
      - llm:      checks the process-wide circuit breaker state (no API call).
      - storage:  checks whether GCP client initialized successfully.

    Returns 200 with per-dependency status even when some dependencies are
    degraded, so uptime monitors can distinguish "app is up but DB is down"
    from a total outage. Returns 503 only when the database is unreachable,
    since that is the hard dependency.
    """
    import asyncio
    from sqlalchemy import text
    from app.database import engine
    from app.utils.retry import llm_circuit_breaker

    checks: dict[str, str] = {}

    # --- Database probe ---
    def _db_ping() -> None:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    try:
        await asyncio.get_event_loop().run_in_executor(None, _db_ping)
        checks["database"] = "ok"
    except Exception as exc:
        logger.error("Health check — database unreachable: %s", exc)
        checks["database"] = "unreachable"

    # --- LLM circuit breaker probe (no network call) ---
    checks["llm_circuit"] = llm_circuit_breaker.state  # "closed" | "open" | "half-open"

    # --- Storage probe (cached flag — no network call) ---
    try:
        from app.services.shared.storage_service import is_gcp_available
        checks["storage_gcp"] = "ok" if is_gcp_available() else "degraded_using_supabase"
    except Exception:
        checks["storage_gcp"] = "unknown"

    overall = "healthy" if checks["database"] == "ok" else "degraded"
    status_code = 200 if overall == "healthy" else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "timezone": settings.TIMEZONE,
            "checks": checks,
        },
    )
