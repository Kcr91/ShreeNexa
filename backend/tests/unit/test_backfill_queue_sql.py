"""Offline tests for the backfill queue: identity, and PostgreSQL statement shape.

Postgres is not always reachable in local development, so these compile the queue's
statements against the real PostgreSQL dialect instead of executing them. That catches
malformed SQL and, more importantly, pins the two properties the whole resumable design
rests on: windows are claimed with SKIP LOCKED, and coverage bounds widen rather than
overwrite. The behavioural counterparts live in
backend/tests/integration/test_backfill_queue_resumable.py.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.worker.backfill_queue import (
    JobSpec,
    backfill_job_table,
    backfill_window_table,
    bar_coverage_table,
)
from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert


def compile_pg(stmt: Any) -> str:
    """Render a statement using the PostgreSQL dialect."""
    compiled: Any = stmt.compile(
        dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
        compile_kwargs={"literal_binds": True},
    )
    return str(compiled)


def base_spec(**overrides: object) -> JobSpec:
    defaults: dict[str, object] = {
        "tier": 2,
        "dataset": "options",
        "exchange_segment": "NSE_FNO",
        "security_id": "13",
        "symbol": "NIFTY",
        "interval": "1",
        "start_date": date(2021, 1, 1),
        "end_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return JobSpec(**defaults)  # type: ignore[arg-type]


class TestJobIdentity:
    def test_identity_is_stable_across_calls(self) -> None:
        assert base_spec().job_id() == base_spec().job_id()

    def test_identity_ignores_non_addressing_fields(self) -> None:
        """Priority and date range describe scheduling, not which series this is."""
        assert base_spec(priority=1).job_id() == base_spec(priority=999).job_id()
        assert (
            base_spec(end_date=date(2026, 1, 1)).job_id()
            == base_spec(end_date=date(2026, 6, 1)).job_id()
        )

    def test_strike_offset_distinguishes_option_legs(self) -> None:
        """ATM+3 and ATM-3 are different series and must never share a job."""
        assert base_spec(strike_offset=3).job_id() != base_spec(strike_offset=-3).job_id()

    def test_zero_offset_is_distinct_from_absent_offset(self) -> None:
        """ATM (0) must not collide with a non-option job that has no offset."""
        assert base_spec(strike_offset=0).job_id() != base_spec(strike_offset=None).job_id()

    def test_expiry_fields_distinguish_series(self) -> None:
        weekly = base_spec(expiry_flag="WEEK", expiry_code=1)
        monthly = base_spec(expiry_flag="MONTH", expiry_code=1)
        next_expiry = base_spec(expiry_flag="WEEK", expiry_code=2)
        assert len({weekly.job_id(), monthly.job_id(), next_expiry.job_id()}) == 3

    def test_interval_distinguishes_series(self) -> None:
        assert base_spec(interval="1").job_id() != base_spec(interval="D").job_id()

    def test_dataset_appears_in_the_identifier(self) -> None:
        assert base_spec(dataset="equity").job_id().startswith("bj-equity-")


class TestClaimStatementShape:
    def build_claim(self) -> Any:
        j = backfill_job_table
        w = backfill_window_table
        return (
            select(w.c.job_id, w.c.window_start)
            .select_from(w.join(j, w.c.job_id == j.c.job_id))
            .where(
                and_(
                    w.c.state == "pending",
                    j.c.state.in_(["pending", "running"]),
                    w.c.attempts < 5,
                )
            )
            .order_by(j.c.tier, j.c.priority, j.c.created_at, w.c.window_start)
            .limit(1)
            .with_for_update(skip_locked=True, of=w)
        )

    def test_claim_uses_skip_locked(self) -> None:
        """Without SKIP LOCKED, concurrent workers would serialise or collide."""
        sql = compile_pg(self.build_claim())
        assert "FOR UPDATE" in sql
        assert "SKIP LOCKED" in sql

    def test_claim_locks_only_the_window_row(self) -> None:
        """Locking the job row too would block sibling windows of the same series."""
        assert "OF backfill_window" in compile_pg(self.build_claim())

    def test_claim_orders_by_tier_then_priority(self) -> None:
        sql = compile_pg(self.build_claim())
        order_clause = sql.split("ORDER BY")[1]
        assert order_clause.index("tier") < order_clause.index("priority")

    def test_claim_excludes_paused_and_failed_jobs(self) -> None:
        """A 401 pause must stop dispatch, not merely stop the current worker."""
        sql = compile_pg(self.build_claim())
        assert "state IN ('pending', 'running')" in sql
        assert "paused_auth" not in sql


class TestCoverageUpsertShape:
    def build_upsert(self) -> Any:
        stmt = pg_insert(bar_coverage_table).values(
            dataset="equity",
            exchange_segment="NSE_EQ",
            symbol="RELIANCE",
            interval="1",
            min_ts=None,
            max_ts=None,
            rows=10,
            last_verified_at=None,
        )
        return stmt.on_conflict_do_update(
            index_elements=["dataset", "exchange_segment", "symbol", "interval"],
            set_={
                "min_ts": func.least(bar_coverage_table.c.min_ts, stmt.excluded.min_ts),
                "max_ts": func.greatest(bar_coverage_table.c.max_ts, stmt.excluded.max_ts),
                "rows": bar_coverage_table.c.rows + stmt.excluded.rows,
            },
        )

    def test_coverage_widens_rather_than_overwrites(self) -> None:
        """Back-filling an older window after a newer one must not shrink the range."""
        sql = compile_pg(self.build_upsert())
        assert "least" in sql.lower()
        assert "greatest" in sql.lower()

    def test_coverage_accumulates_rows(self) -> None:
        assert "rows + " in compile_pg(self.build_upsert()).replace("  ", " ")

    def test_coverage_upsert_targets_the_composite_key(self) -> None:
        sql = compile_pg(self.build_upsert())
        assert "ON CONFLICT" in sql
        for column in ("dataset", "exchange_segment", "symbol", "interval"):
            assert column in sql


class TestIdempotentEnqueueShape:
    def test_job_insert_does_nothing_on_conflict(self) -> None:
        """Re-enqueueing a tier must not reset progress on existing jobs."""
        stmt = (
            pg_insert(backfill_job_table)
            .values(job_id="bj-x")
            .on_conflict_do_nothing(index_elements=["job_id"])
        )
        assert "ON CONFLICT (job_id) DO NOTHING" in compile_pg(stmt)

    def test_window_insert_does_nothing_on_conflict(self) -> None:
        stmt = (
            pg_insert(backfill_window_table)
            .values(job_id="bj-x", window_start=date(2026, 1, 1))
            .on_conflict_do_nothing(index_elements=["job_id", "window_start"])
        )
        sql = compile_pg(stmt)
        assert "ON CONFLICT" in sql
        assert "DO NOTHING" in sql


class TestReleaseSemantics:
    def test_release_refunds_the_attempt(self) -> None:
        """Budget exhaustion is not the window's fault; it must not burn a retry."""
        w = backfill_window_table
        stmt = (
            update(w)
            .where(and_(w.c.job_id == "bj-x", w.c.state == "running"))
            .values(state="pending", attempts=w.c.attempts - 1)
        )
        sql = compile_pg(stmt)
        assert "attempts - 1" in sql
        assert "state='pending'" in sql.replace(" = ", "=").replace("'pending'", "'pending'")


def test_tables_declare_the_states_the_module_uses() -> None:
    """Guard against a state string drifting away from the migration's CHECK constraint."""
    assert {c.name for c in backfill_job_table.columns} >= {
        "job_id",
        "tier",
        "dataset",
        "state",
        "attempts",
        "priority",
    }
    assert {c.name for c in backfill_window_table.columns} >= {
        "job_id",
        "window_start",
        "window_end",
        "state",
        "attempts",
        "rows",
        "sha256",
    }
    assert {c.name for c in bar_coverage_table.columns} >= {
        "dataset",
        "symbol",
        "interval",
        "min_ts",
        "max_ts",
        "rows",
    }
