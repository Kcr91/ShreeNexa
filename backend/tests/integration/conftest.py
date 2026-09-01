"""Shared fixtures for backend/tests/integration/.

Every integration test here needs the same "skip cleanly, name the reason"
behavior when infra/docker-compose.yml's stack isn't running -- see
docs/qa/acceptance/F0.2.md's A4 and F0.3's reuse of the same pattern.
"""

from __future__ import annotations

import os

import psycopg
import pytest
import redis
from sqlalchemy.engine import make_url

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://shreenexa:shreenexa_local_dev_only@127.0.0.1:5432/shreenexa",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

CONNECT_TIMEOUT_S = 3


def psycopg_dsn(sqlalchemy_url: str) -> str:
    url = make_url(sqlalchemy_url)
    return url.render_as_string(hide_password=False).replace(
        "postgresql+psycopg://", "postgresql://"
    )


@pytest.fixture()
def postgres_or_skip() -> str:
    dsn = psycopg_dsn(DATABASE_URL)
    try:
        with psycopg.connect(dsn, connect_timeout=CONNECT_TIMEOUT_S):
            pass
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres not reachable at {dsn!r} (start infra/docker-compose.yml): {exc}")
    return dsn


@pytest.fixture()
def redis_or_skip() -> redis.Redis:
    client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=CONNECT_TIMEOUT_S)
    try:
        client.ping()
    except redis.exceptions.ConnectionError as exc:
        pytest.skip(
            f"Redis/Valkey not reachable at {REDIS_URL!r} (start infra/docker-compose.yml): {exc}"
        )
    return client
