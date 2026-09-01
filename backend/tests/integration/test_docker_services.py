"""Connectivity smoke tests for the F0.2 Docker Compose stack.

Each test skips (never silently passes) when its service isn't reachable
within a short timeout, so `pytest` stays green with the stack down (A4)
while still genuinely exercising the stack when it's up (A2).

Start the stack first: docker compose -f infra/docker-compose.yml up -d
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg
import redis
from conftest import CONNECT_TIMEOUT_S, DATABASE_URL
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = REPO_ROOT / "backend" / "alembic.ini"


def test_postgres_connectivity(postgres_or_skip: str) -> None:
    with psycopg.connect(postgres_or_skip, connect_timeout=CONNECT_TIMEOUT_S) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone() == (1,)


def test_alembic_upgrade_head_creates_version_table(postgres_or_skip: str) -> None:
    env = {**os.environ, "DATABASE_URL": DATABASE_URL}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}"

    with psycopg.connect(postgres_or_skip, connect_timeout=CONNECT_TIMEOUT_S) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version")
            row = cur.fetchone()
            assert row is not None and row[0]

    # Idempotent: running it again must not error.
    result_again = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result_again.returncode == 0, f"second upgrade head failed:\n{result_again.stdout}"


def test_redis_connectivity(redis_or_skip: redis.Redis) -> None:
    key = "shreenexa:f0.2:smoke-test"
    redis_or_skip.set(key, "ok", ex=30)
    assert redis_or_skip.get(key) == b"ok"
    redis_or_skip.delete(key)


def test_sqlalchemy_engine_connects(postgres_or_skip: str) -> None:
    """Prove the SQLAlchemy engine URL (not just raw psycopg) also works,
    since that's what application code and future models will use."""
    from sqlalchemy import create_engine

    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar() == 1
    finally:
        engine.dispose()
