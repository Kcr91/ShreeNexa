"""Root test configuration and fixtures for ShreeNexa test suite.

Includes both infrastructure integration fixtures (Postgres/Redis connection checks)
and session/CSRF authentication dependency overrides for API endpoint suites.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
import redis
from app.api.deps import require_csrf, require_session
from app.auth.models import SessionInfo
from app.main import app
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://shreenexa:shreenexa_local_dev_only@127.0.0.1:5432/shreenexa",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CONNECT_TIMEOUT_S = 3


def psycopg_dsn(sqlalchemy_url: str) -> str:
    """Convert SQLAlchemy async/psycopg URL to standard psycopg DSN."""
    url = make_url(sqlalchemy_url)
    return url.render_as_string(hide_password=False).replace(
        "postgresql+psycopg://", "postgresql://"
    )


@pytest.fixture()
def postgres_or_skip() -> str:
    """Fixture ensuring PostgreSQL is running, skipping cleanly if unreachable."""
    dsn = psycopg_dsn(DATABASE_URL)
    try:
        with psycopg.connect(dsn, connect_timeout=CONNECT_TIMEOUT_S):
            pass
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres not reachable at {dsn!r} (start infra/docker-compose.yml): {exc}")
    return dsn


@pytest.fixture()
def redis_or_skip() -> redis.Redis:
    """Fixture ensuring Redis is running, skipping cleanly if unreachable."""
    client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=CONNECT_TIMEOUT_S)
    try:
        client.ping()
    except redis.exceptions.ConnectionError as exc:
        pytest.skip(
            f"Redis/Valkey not reachable at {REDIS_URL!r} (start infra/docker-compose.yml): {exc}"
        )
    return client


def create_test_session() -> SessionInfo:
    """Return a mock authenticated trader session for testing."""
    now = datetime.now(UTC)
    return SessionInfo(
        session_id="test_session_id_mock_autouse",
        username="trader",
        created_at=now,
        expires_at=now + timedelta(days=1),
        csrf_token="test_csrf_token_valid_mock",
    )


@pytest.fixture(autouse=True)
def default_auth_dependency_overrides(
    request: pytest.FixtureRequest,
) -> Generator[None]:
    """Globally mock session authentication and CSRF dependencies for test suites.

    Tests that specifically evaluate authentication enforcement can be marked with
    `@pytest.mark.no_auth_override` or can directly clear `app.dependency_overrides`.
    """
    if "no_auth_override" in request.keywords:
        yield
        return

    orig_session = app.dependency_overrides.get(require_session)
    orig_csrf = app.dependency_overrides.get(require_csrf)

    app.dependency_overrides[require_session] = create_test_session
    app.dependency_overrides[require_csrf] = lambda: None

    try:
        yield
    finally:
        if orig_session is not None:
            app.dependency_overrides[require_session] = orig_session
        else:
            app.dependency_overrides.pop(require_session, None)

        if orig_csrf is not None:
            app.dependency_overrides[require_csrf] = orig_csrf
        else:
            app.dependency_overrides.pop(require_csrf, None)


@pytest.fixture()
def backfill_engine(postgres_or_skip: str) -> Generator[Engine]:
    """Engine bound to a throwaway schema for backfill-queue integration tests.

    These tests need real Postgres semantics (SKIP LOCKED, ON CONFLICT, LEAST/GREATEST),
    so they create the queue tables for real. Creating them in `public` and dropping them
    afterwards would delete the tables Alembic owns in the developer's own database,
    leaving alembic_version claiming a migration that is no longer applied. Each test
    therefore gets its own schema, dropped wholesale at teardown.
    """
    from app.worker.backfill_queue import metadata as backfill_metadata

    schema = f"test_backfill_{uuid.uuid4().hex[:8]}"
    url = postgres_or_skip.replace("postgresql://", "postgresql+psycopg://")
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})

    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    backfill_metadata.create_all(engine)
    try:
        yield engine
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
