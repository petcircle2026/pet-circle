"""
PetCircle Phase 1 - Database Connection

Establishes SQLAlchemy engine and session factory using DATABASE_URL
from environment configuration. All database access flows through
the get_db() dependency to ensure proper session lifecycle management.

Connection strategy:
    - Supabase uses PgBouncer/Supavisor (port 6543) in transaction mode.
    - QueuePool with pool_pre_ping=True validates each connection before
      use, but cannot prevent the TOCTOU race where SSL drops after ping.
    - pool_recycle=120 refreshes connections aggressively - well under any
      idle-timeout Supabase/Supavisor might enforce server-side.
    - Pool (pool_size=20, max_overflow=20) supports burst webhook + background
      task concurrency while staying within Supabase connection limits.
    - keepalives settings prevent OS-level TCP idle drops on long queries.
    - Pool saturation is monitored via the checkin event: a warning is
      emitted whenever a connection was held longer than POOL_WAIT_WARN_SECONDS,
      giving early visibility of pool exhaustion before pool_timeout fires.

No business logic lives here - only connection infrastructure.
"""

import logging
import time
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import settings
from app.core.constants import (
    DB_KEEPALIVES_COUNT,
    DB_KEEPALIVES_IDLE,
    DB_KEEPALIVES_INTERVAL,
    DB_POOL_MAX_OVERFLOW,
    DB_POOL_RECYCLE_SECONDS,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT_SECONDS,
    DB_POOL_WAIT_WARN_SECONDS,
)

logger = logging.getLogger(__name__)

# Emit a WARNING when a connection was held longer than this threshold.
# DB_POOL_TIMEOUT_SECONDS is the hard limit; warn at DB_POOL_WAIT_WARN_SECONDS to flag saturation early.
POOL_WAIT_WARN_SECONDS: float = DB_POOL_WAIT_WARN_SECONDS


# Build connection args for SSL compatibility with Supabase.
connect_args = {}
if "supabase" in settings.DATABASE_URL:
    # Supabase requires SSL but psycopg2 needs keepalive settings
    # to prevent idle connection drops from PgBouncer.
    connect_args = {
        "keepalives": 1,
        "keepalives_idle": DB_KEEPALIVES_IDLE,
        "keepalives_interval": DB_KEEPALIVES_INTERVAL,
        "keepalives_count": DB_KEEPALIVES_COUNT,
    }

# SQLAlchemy engine - QueuePool with pre_ping to detect dead connections.
# pool_pre_ping re-enabled: SSL drop errors confirmed in production logs.
# The ~150ms cross-region ping cost is acceptable vs. 500 errors on stale
# connections. pool_recycle still limits how often the ping fires.
# Pool sizing constants live in app/core/constants.py alongside concurrency limits.
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_POOL_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE_SECONDS,
    pool_timeout=DB_POOL_TIMEOUT_SECONDS,
    connect_args=connect_args,
    # Disable SQL echo in production - only enable for debugging.
    echo=False,
)

# Per-checkout start time stored on the connection record so the checkin
# listener can compute actual hold duration without a thread-local.
_CHECKOUT_START_ATTR = "_petcircle_checkout_start"


@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_conn, connection_rec, connection_proxy):
    """Stamp checkout start time for saturation monitoring."""
    connection_rec.info[_CHECKOUT_START_ATTR] = time.monotonic()
    logger.debug("DB connection checked out from pool")


@event.listens_for(engine, "checkin")
def _on_checkin(dbapi_conn, connection_rec):
    """Warn when a connection was held longer than POOL_WAIT_WARN_SECONDS."""
    start = connection_rec.info.pop(_CHECKOUT_START_ATTR, None)
    if start is None:
        return
    held_for = time.monotonic() - start
    if held_for >= POOL_WAIT_WARN_SECONDS:
        pool = engine.pool
        logger.warning(
            "DB pool saturation - connection held for %.1fs "
            "(pool_size=%d, overflow=%d, checked_out=%d). "
            "Consider raising pool_size if this recurs.",
            held_for,
            pool.size(),
            pool.overflow(),
            pool.checkedout(),
        )


# Session factory - autocommit and autoflush disabled for explicit transaction control.
# Every DB write must be committed explicitly to prevent silent data loss.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative base for all SQLAlchemy models.
# Every model in app/models/ must inherit from this base.
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    Yields a session and ensures it is closed after the request completes,
    regardless of whether the request succeeded or raised an exception.
    Rolls back on errors to prevent dirty session state from poisoning
    subsequent requests.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_fresh_session() -> Session:
    """
    Create a fresh DB session for background tasks.

    Use this instead of raw SessionLocal() to ensure consistent
    configuration. Caller is responsible for closing the session.
    """
    return SessionLocal()


def safe_db_execute(db: Session, operation, max_retries: int = 1):
    """
    Execute a DB operation with retry on connection failure.

    If the connection has been dropped by PgBouncer/Supabase, this will
    rollback, close the dead session, create a new one, and retry once.

    Args:
        db: The current SQLAlchemy session.
        operation: A callable that takes a session and performs the DB work.
        max_retries: Number of retries on OperationalError (default 1).

    Returns:
        Tuple of (result, session) - session may be a new one if retry occurred.
    """
    try:
        result = operation(db)
        return result, db
    except OperationalError as e:
        logger.warning("DB operation failed (SSL/connection drop), retrying: %s", str(e))
        try:
            db.rollback()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass

        if max_retries > 0:
            new_db = SessionLocal()
            return safe_db_execute(new_db, operation, max_retries - 1)
        raise
