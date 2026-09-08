"""Resumable backfill job queue backed by Postgres.

The three backfill managers in this package parse and publish already-fetched payloads;
nothing tracked what had been fetched. A five-year, multi-week download has to survive a
crash, a reboot, and an expired token without replaying calls it already paid for, so
progress is checkpointed per *window* rather than per job:

    backfill_job     one addressable series (symbol / interval / option leg)
    backfill_window  one API call's worth of date range - the resume point
    bar_coverage     what the warehouse actually holds, for the export UI

Windows are claimed with ``FOR UPDATE SKIP LOCKED`` so several workers can drain the
queue without handing the same window to two of them.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    Integer,
    MetaData,
    Table,
    Text,
    and_,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger(__name__)

metadata = MetaData()

JobState = Literal["pending", "running", "done", "failed", "paused_auth", "unavailable"]
WindowState = Literal["pending", "running", "done", "failed", "empty"]

backfill_job_table = Table(
    "backfill_job",
    metadata,
    Column("job_id", Text, primary_key=True),
    Column("tier", Integer, nullable=False),
    Column("dataset", Text, nullable=False),
    Column("exchange_segment", Text, nullable=False),
    Column("security_id", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("underlying_symbol", Text, nullable=True),
    Column("instrument_type", Text, nullable=True),
    Column("expiry_flag", Text, nullable=True),
    Column("expiry_code", Integer, nullable=True),
    Column("strike_offset", Integer, nullable=True),
    Column("interval", Text, nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("priority", Integer, nullable=False),
    Column("state", Text, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("last_error", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False),
)

backfill_window_table = Table(
    "backfill_window",
    metadata,
    Column("job_id", Text, primary_key=True),
    Column("window_start", Date, primary_key=True),
    Column("window_end", Date, nullable=False),
    Column("state", Text, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("raw_ingest_id", Text, nullable=True),
    Column("rows", Integer, nullable=True),
    Column("sha256", Text, nullable=True),
    Column("last_error", Text, nullable=True),
    Column("claimed_at", TIMESTAMP(timezone=True), nullable=True),
    Column("completed_at", TIMESTAMP(timezone=True), nullable=True),
)

bar_coverage_table = Table(
    "bar_coverage",
    metadata,
    Column("dataset", Text, primary_key=True),
    Column("exchange_segment", Text, primary_key=True),
    Column("symbol", Text, primary_key=True),
    Column("interval", Text, primary_key=True),
    Column("security_id", Text, nullable=True),
    Column("underlying_symbol", Text, nullable=True),
    Column("min_ts", TIMESTAMP(timezone=True), nullable=True),
    Column("max_ts", TIMESTAMP(timezone=True), nullable=True),
    Column("rows", BigInteger, nullable=False),
    Column("last_verified_at", TIMESTAMP(timezone=True), nullable=False),
)


@dataclass(frozen=True)
class JobSpec:
    """One addressable series to back-fill."""

    tier: int
    dataset: str
    exchange_segment: str
    security_id: str
    symbol: str
    interval: str
    start_date: date
    end_date: date
    underlying_symbol: str | None = None
    instrument_type: str | None = None
    expiry_flag: str | None = None
    expiry_code: int | None = None
    strike_offset: int | None = None
    priority: int = 100

    def job_id(self) -> str:
        """Stable identity for this series, so re-enqueueing is idempotent."""
        parts = [
            self.dataset,
            self.exchange_segment,
            self.security_id,
            self.interval,
            self.expiry_flag or "",
            str(self.expiry_code if self.expiry_code is not None else -1),
            str(self.strike_offset if self.strike_offset is not None else -9999),
        ]
        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
        return f"bj-{self.dataset}-{digest}"


@dataclass(frozen=True)
class ClaimedWindow:
    """A window leased to this worker, with the parent job's routing fields."""

    job_id: str
    window_start: date
    window_end: date
    attempts: int
    tier: int
    dataset: str
    exchange_segment: str
    security_id: str
    symbol: str
    interval: str
    underlying_symbol: str | None
    instrument_type: str | None
    expiry_flag: str | None
    expiry_code: int | None
    strike_offset: int | None


def _now() -> datetime:
    return datetime.now(UTC)


def enqueue_jobs(
    engine: Engine,
    specs: Iterable[JobSpec],
    windows_for: Any,
) -> tuple[int, int]:
    """Insert jobs and their windows idempotently.

    ``windows_for(spec)`` yields ``(start, end)`` pairs sized for the relevant endpoint.
    Re-running against an existing queue inserts nothing and, critically, does not reset
    the state of windows already completed.

    Returns ``(jobs_inserted, windows_inserted)``.
    """
    jobs_inserted = 0
    windows_inserted = 0
    now = _now()

    with engine.begin() as conn:
        for spec in specs:
            job_id = spec.job_id()
            job_stmt = (
                pg_insert(backfill_job_table)
                .values(
                    job_id=job_id,
                    tier=spec.tier,
                    dataset=spec.dataset,
                    exchange_segment=spec.exchange_segment,
                    security_id=spec.security_id,
                    symbol=spec.symbol,
                    underlying_symbol=spec.underlying_symbol,
                    instrument_type=spec.instrument_type,
                    expiry_flag=spec.expiry_flag,
                    expiry_code=spec.expiry_code,
                    strike_offset=spec.strike_offset,
                    interval=spec.interval,
                    start_date=spec.start_date,
                    end_date=spec.end_date,
                    priority=spec.priority,
                    state="pending",
                    attempts=0,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(index_elements=["job_id"])
                .returning(backfill_job_table.c.job_id)
            )
            # RETURNING yields a row only for an actual insert; rowcount is unreliable
            # for ON CONFLICT DO NOTHING and is -1 for executemany under psycopg3.
            if conn.execute(job_stmt).first() is not None:
                jobs_inserted += 1

            rows = [
                {
                    "job_id": job_id,
                    "window_start": w_start,
                    "window_end": w_end,
                    "state": "pending",
                    "attempts": 0,
                }
                for w_start, w_end in windows_for(spec)
            ]
            if not rows:
                continue

            window_stmt = (
                pg_insert(backfill_window_table)
                .on_conflict_do_nothing(index_elements=["job_id", "window_start"])
                .returning(backfill_window_table.c.window_start)
            )
            for row in rows:
                if conn.execute(window_stmt.values(**row)).first() is not None:
                    windows_inserted += 1

    logger.info("Enqueued %d new job(s) and %d new window(s)", jobs_inserted, windows_inserted)
    return jobs_inserted, windows_inserted


def claim_next_window(
    engine: Engine,
    *,
    datasets: Sequence[str] | None = None,
    max_attempts: int = 5,
) -> ClaimedWindow | None:
    """Lease the highest-priority pending window, or None when the queue is drained.

    Uses ``FOR UPDATE SKIP LOCKED`` so concurrent workers never receive the same window.
    Windows whose parent job is not runnable (paused_auth, failed, unavailable) are not
    handed out, which is what makes a 401 pause recoverable rather than destructive.
    """
    j = backfill_job_table
    w = backfill_window_table

    conditions = [
        w.c.state == "pending",
        j.c.state.in_(["pending", "running"]),
        w.c.attempts < max_attempts,
    ]
    if datasets:
        conditions.append(j.c.dataset.in_(list(datasets)))

    select_stmt = (
        select(
            w.c.job_id,
            w.c.window_start,
            w.c.window_end,
            w.c.attempts,
            j.c.tier,
            j.c.dataset,
            j.c.exchange_segment,
            j.c.security_id,
            j.c.symbol,
            j.c.interval,
            j.c.underlying_symbol,
            j.c.instrument_type,
            j.c.expiry_flag,
            j.c.expiry_code,
            j.c.strike_offset,
        )
        .select_from(w.join(j, w.c.job_id == j.c.job_id))
        .where(and_(*conditions))
        .order_by(j.c.tier, j.c.priority, j.c.created_at, w.c.window_start)
        .limit(1)
        .with_for_update(skip_locked=True, of=w)
    )

    with engine.begin() as conn:
        row = conn.execute(select_stmt).mappings().first()
        if row is None:
            return None

        conn.execute(
            update(w)
            .where(
                and_(
                    w.c.job_id == row["job_id"],
                    w.c.window_start == row["window_start"],
                )
            )
            .values(state="running", attempts=w.c.attempts + 1, claimed_at=_now())
        )
        conn.execute(
            update(j)
            .where(and_(j.c.job_id == row["job_id"], j.c.state == "pending"))
            .values(state="running", updated_at=_now())
        )

        return ClaimedWindow(
            job_id=row["job_id"],
            window_start=row["window_start"],
            window_end=row["window_end"],
            attempts=row["attempts"] + 1,
            tier=row["tier"],
            dataset=row["dataset"],
            exchange_segment=row["exchange_segment"],
            security_id=row["security_id"],
            symbol=row["symbol"],
            interval=row["interval"],
            underlying_symbol=row["underlying_symbol"],
            instrument_type=row["instrument_type"],
            expiry_flag=row["expiry_flag"],
            expiry_code=row["expiry_code"],
            strike_offset=row["strike_offset"],
        )


def complete_window(
    engine: Engine,
    job_id: str,
    window_start: date,
    *,
    rows: int,
    raw_ingest_id: str | None = None,
    sha256: str | None = None,
) -> None:
    """Mark a window done. A window that returned no bars is recorded as ``empty``.

    ``empty`` is deliberately distinct from ``done``: an expired option strike that never
    traded is a real, terminal answer, and re-requesting it every run would waste budget.
    """
    w = backfill_window_table
    with engine.begin() as conn:
        conn.execute(
            update(w)
            .where(and_(w.c.job_id == job_id, w.c.window_start == window_start))
            .values(
                state="done" if rows > 0 else "empty",
                rows=rows,
                raw_ingest_id=raw_ingest_id,
                sha256=sha256,
                last_error=None,
                completed_at=_now(),
            )
        )
        _settle_job_if_finished(conn, job_id)


def fail_window(
    engine: Engine,
    job_id: str,
    window_start: date,
    error: str,
    *,
    max_attempts: int = 5,
) -> None:
    """Record a window failure, retiring it only once its attempts are exhausted."""
    w = backfill_window_table
    with engine.begin() as conn:
        attempts = conn.execute(
            select(w.c.attempts).where(and_(w.c.job_id == job_id, w.c.window_start == window_start))
        ).scalar_one_or_none()

        exhausted = attempts is not None and attempts >= max_attempts
        conn.execute(
            update(w)
            .where(and_(w.c.job_id == job_id, w.c.window_start == window_start))
            .values(
                state="failed" if exhausted else "pending",
                last_error=error[:2000],
            )
        )
        if exhausted:
            _settle_job_if_finished(conn, job_id)


def release_window(engine: Engine, job_id: str, window_start: date) -> None:
    """Return a leased window to the queue without consuming an attempt.

    Used when a run is interrupted for a reason that is not the window's fault, such as
    the daily API budget running out.
    """
    w = backfill_window_table
    with engine.begin() as conn:
        conn.execute(
            update(w)
            .where(
                and_(
                    w.c.job_id == job_id,
                    w.c.window_start == window_start,
                    w.c.state == "running",
                )
            )
            .values(state="pending", attempts=w.c.attempts - 1, claimed_at=None)
        )


def pause_all_for_auth(engine: Engine, reason: str) -> int:
    """Park every runnable job on an auth failure and return how many were parked.

    Nothing is lost: windows keep their completed state, so a refreshed token resumes
    from the exact point the token died.
    """
    j = backfill_job_table
    w = backfill_window_table
    with engine.begin() as conn:
        conn.execute(
            update(w).where(w.c.state == "running").values(state="pending", claimed_at=None)
        )
        result = conn.execute(
            update(j)
            .where(j.c.state.in_(["pending", "running"]))
            .values(state="paused_auth", last_error=reason[:2000], updated_at=_now())
        )
    count = result.rowcount or 0
    logger.warning("Paused %d backfill job(s) awaiting a valid token: %s", count, reason)
    return count


def resume_after_auth(engine: Engine) -> int:
    """Return parked jobs to the queue after credentials are restored."""
    j = backfill_job_table
    with engine.begin() as conn:
        result = conn.execute(
            update(j)
            .where(j.c.state == "paused_auth")
            .values(state="pending", last_error=None, updated_at=_now())
        )
    count = result.rowcount or 0
    logger.info("Resumed %d backfill job(s) after credential refresh", count)
    return count


def _settle_job_if_finished(conn: Connection, job_id: str) -> None:
    """Close a job once no window remains pending or running."""
    w = backfill_window_table
    j = backfill_job_table

    remaining = conn.execute(
        select(func.count())
        .select_from(w)
        .where(and_(w.c.job_id == job_id, w.c.state.in_(["pending", "running"])))
    ).scalar_one()
    if remaining:
        return

    failed = conn.execute(
        select(func.count()).select_from(w).where(and_(w.c.job_id == job_id, w.c.state == "failed"))
    ).scalar_one()

    conn.execute(
        update(j)
        .where(j.c.job_id == job_id)
        .values(state="failed" if failed else "done", updated_at=_now())
    )


def upsert_coverage(
    engine: Engine,
    *,
    dataset: str,
    exchange_segment: str,
    symbol: str,
    interval: str,
    min_ts: datetime,
    max_ts: datetime,
    rows: int,
    security_id: str | None = None,
    underlying_symbol: str | None = None,
) -> None:
    """Widen the recorded coverage window for a series and add to its row count.

    Bounds are widened with LEAST/GREATEST rather than overwritten, so back-filling an
    older window after a newer one cannot shrink the recorded range.
    """
    stmt = pg_insert(bar_coverage_table).values(
        dataset=dataset,
        exchange_segment=exchange_segment,
        symbol=symbol,
        interval=interval,
        security_id=security_id,
        underlying_symbol=underlying_symbol,
        min_ts=min_ts,
        max_ts=max_ts,
        rows=rows,
        last_verified_at=_now(),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["dataset", "exchange_segment", "symbol", "interval"],
        set_={
            "min_ts": func.least(bar_coverage_table.c.min_ts, stmt.excluded.min_ts),
            "max_ts": func.greatest(bar_coverage_table.c.max_ts, stmt.excluded.max_ts),
            "rows": bar_coverage_table.c.rows + stmt.excluded.rows,
            "last_verified_at": stmt.excluded.last_verified_at,
            "security_id": func.coalesce(
                stmt.excluded.security_id, bar_coverage_table.c.security_id
            ),
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)


def queue_progress(engine: Engine) -> list[dict[str, Any]]:
    """Per-tier progress, for the backfill status strip in the UI."""
    j = backfill_job_table
    w = backfill_window_table
    stmt = (
        select(
            j.c.tier,
            j.c.dataset,
            func.count().label("windows"),
            func.count(text("1")).filter(w.c.state.in_(["done", "empty"])).label("completed"),
            func.count(text("1")).filter(w.c.state == "failed").label("failed"),
        )
        .select_from(w.join(j, w.c.job_id == j.c.job_id))
        .group_by(j.c.tier, j.c.dataset)
        .order_by(j.c.tier, j.c.dataset)
    )
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(stmt).mappings()]
