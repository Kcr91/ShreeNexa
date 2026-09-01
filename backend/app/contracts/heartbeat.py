"""Durable process-liveness contract shared by api, engine, feedd, and worker.

Per ADR-0002 invariant 2 ("No process holds authoritative state only in
memory"), a process's liveness is proven by a row in Postgres, not by
whatever it happens to remember in memory. This is deliberately the only
thing F0.3's process skeletons do in their loop body -- see
docs/qa/acceptance/F0.3.md for why no real capability logic belongs here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

PROCESS_NAMES = ("api", "engine", "feedd", "worker")
STATUS_RUNNING = "running"
STATUS_STOPPED = "stopped"

metadata = MetaData()

process_heartbeat = Table(
    "process_heartbeat",
    metadata,
    Column("process_name", Text, primary_key=True),
    Column("pid", Integer, nullable=False),
    Column("status", Text, nullable=False),
    Column("started_at", TIMESTAMP(timezone=True), nullable=False),
    Column("last_heartbeat_at", TIMESTAMP(timezone=True), nullable=False),
)


@dataclass(frozen=True)
class HeartbeatRow:
    process_name: str
    pid: int
    status: str
    started_at: datetime
    last_heartbeat_at: datetime


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. See infra/docker-compose.yml for the local dev value."
        )
    return url


def make_engine() -> Engine:
    return create_engine(database_url())


def record_start(engine: Engine, process_name: str, pid: int) -> None:
    """Upsert this process's row as freshly started (new pid, running)."""
    if process_name not in PROCESS_NAMES:
        raise ValueError(f"unknown process_name {process_name!r}, expected one of {PROCESS_NAMES}")

    now = datetime.now(UTC)
    stmt = pg_insert(process_heartbeat).values(
        process_name=process_name,
        pid=pid,
        status=STATUS_RUNNING,
        started_at=now,
        last_heartbeat_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[process_heartbeat.c.process_name],
        set_={
            "pid": stmt.excluded.pid,
            "status": STATUS_RUNNING,
            "started_at": now,
            "last_heartbeat_at": now,
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)


def beat(engine: Engine, process_name: str) -> None:
    """Advance last_heartbeat_at for the current run; does not touch pid/started_at."""
    with engine.begin() as conn:
        conn.execute(
            process_heartbeat.update()
            .where(process_heartbeat.c.process_name == process_name)
            .values(last_heartbeat_at=datetime.now(UTC))
        )


def record_stop(engine: Engine, process_name: str) -> None:
    """Mark a graceful shutdown. A forceful kill never calls this, by design --
    that is exactly what A2/A3 exercise: the row simply stops advancing."""
    with engine.begin() as conn:
        conn.execute(
            process_heartbeat.update()
            .where(process_heartbeat.c.process_name == process_name)
            .values(status=STATUS_STOPPED, last_heartbeat_at=datetime.now(UTC))
        )


def read(engine: Engine, process_name: str) -> HeartbeatRow | None:
    with engine.connect() as conn:
        row = conn.execute(
            select(process_heartbeat).where(process_heartbeat.c.process_name == process_name)
        ).first()
    return HeartbeatRow(**row._mapping) if row is not None else None


def read_all(engine: Engine) -> list[HeartbeatRow]:
    with engine.connect() as conn:
        rows = conn.execute(select(process_heartbeat)).all()
    return [HeartbeatRow(**row._mapping) for row in rows]
