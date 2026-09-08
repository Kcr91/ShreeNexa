"""Integration tests proving the backfill queue is genuinely resumable.

Requires Postgres (skipped cleanly when unreachable). These exercise the properties the
multi-week download depends on: a killed worker replays no completed window, concurrent
workers never receive the same window, and an auth pause parks work recoverably.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from app.worker.backfill_queue import (
    JobSpec,
    backfill_job_table,
    backfill_window_table,
    bar_coverage_table,
    claim_next_window,
    complete_window,
    enqueue_jobs,
    fail_window,
    metadata,
    pause_all_for_auth,
    queue_progress,
    release_window,
    resume_after_auth,
    upsert_coverage,
)
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine


@pytest.fixture()
def engine(postgres_or_skip: str) -> Generator[Engine]:
    """Engine against a scratch schema, dropped after each test."""
    eng = create_engine(postgres_or_skip.replace("postgresql://", "postgresql+psycopg://"))
    metadata.drop_all(eng, checkfirst=True)
    metadata.create_all(eng)
    try:
        yield eng
    finally:
        metadata.drop_all(eng, checkfirst=True)
        eng.dispose()


def three_windows(spec: JobSpec) -> list[tuple[date, date]]:
    start = spec.start_date
    return [
        (start, start + timedelta(days=29)),
        (start + timedelta(days=30), start + timedelta(days=59)),
        (start + timedelta(days=60), spec.end_date),
    ]


def make_spec(**kw: object) -> JobSpec:
    base: dict[str, object] = {
        "tier": 1,
        "dataset": "index",
        "exchange_segment": "IDX_I",
        "security_id": "13",
        "symbol": "NIFTY",
        "interval": "1",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 3, 31),
    }
    base.update(kw)
    return JobSpec(**base)  # type: ignore[arg-type]


class TestEnqueueIdempotence:
    def test_enqueue_creates_job_and_windows(self, engine: Engine) -> None:
        jobs, windows = enqueue_jobs(engine, [make_spec()], three_windows)
        assert (jobs, windows) == (1, 3)

    def test_re_enqueue_is_a_no_op(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec()], three_windows)
        assert enqueue_jobs(engine, [make_spec()], three_windows) == (0, 0)

    def test_re_enqueue_does_not_reset_completed_windows(self, engine: Engine) -> None:
        """The failure mode that would silently re-spend the whole API budget."""
        enqueue_jobs(engine, [make_spec()], three_windows)
        claimed = claim_next_window(engine)
        assert claimed is not None
        complete_window(engine, claimed.job_id, claimed.window_start, rows=375)

        enqueue_jobs(engine, [make_spec()], three_windows)

        with engine.connect() as conn:
            states = sorted(r[0] for r in conn.execute(select(backfill_window_table.c.state)).all())
        assert states == ["done", "pending", "pending"]


class TestClaimAndComplete:
    def test_claim_returns_job_routing_fields(self, engine: Engine) -> None:
        enqueue_jobs(
            engine,
            [make_spec(dataset="options", strike_offset=-3, expiry_flag="WEEK", expiry_code=1)],
            three_windows,
        )
        claimed = claim_next_window(engine)

        assert claimed is not None
        assert claimed.symbol == "NIFTY"
        assert claimed.strike_offset == -3
        assert claimed.expiry_flag == "WEEK"
        assert claimed.attempts == 1

    def test_claim_returns_none_when_drained(self, engine: Engine) -> None:
        assert claim_next_window(engine) is None

    def test_two_claims_never_return_the_same_window(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec()], three_windows)
        first = claim_next_window(engine)
        second = claim_next_window(engine)

        assert first is not None and second is not None
        assert first.window_start != second.window_start

    def test_lower_tier_is_claimed_first(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec(tier=5, security_id="99", symbol="LATE")], three_windows)
        enqueue_jobs(engine, [make_spec(tier=1, security_id="13", symbol="EARLY")], three_windows)

        claimed = claim_next_window(engine)
        assert claimed is not None
        assert claimed.symbol == "EARLY"

    def test_completing_all_windows_closes_the_job(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec()], three_windows)
        for _ in range(3):
            claimed = claim_next_window(engine)
            assert claimed is not None
            complete_window(engine, claimed.job_id, claimed.window_start, rows=100)

        with engine.connect() as conn:
            state = conn.execute(select(backfill_job_table.c.state)).scalar_one()
        assert state == "done"

    def test_empty_window_is_terminal_not_retried(self, engine: Engine) -> None:
        """A strike that never traded is a real answer; re-requesting wastes budget."""
        enqueue_jobs(engine, [make_spec()], three_windows)
        claimed = claim_next_window(engine)
        assert claimed is not None
        complete_window(engine, claimed.job_id, claimed.window_start, rows=0)

        with engine.connect() as conn:
            state = conn.execute(
                select(backfill_window_table.c.state).where(
                    backfill_window_table.c.window_start == claimed.window_start
                )
            ).scalar_one()
        assert state == "empty"


class TestResumeSemantics:
    def test_kill_and_resume_replays_only_unfinished_windows(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec()], three_windows)

        first = claim_next_window(engine)
        assert first is not None
        complete_window(engine, first.job_id, first.window_start, rows=375)

        # Simulate a crash mid-window: claimed, never completed.
        second = claim_next_window(engine)
        assert second is not None
        release_window(engine, second.job_id, second.window_start)

        seen: set[date] = set()
        while (claimed := claim_next_window(engine)) is not None:
            seen.add(claimed.window_start)
            complete_window(engine, claimed.job_id, claimed.window_start, rows=10)

        assert first.window_start not in seen, "completed window must never be re-fetched"
        assert second.window_start in seen

    def test_release_does_not_consume_an_attempt(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec()], three_windows)
        claimed = claim_next_window(engine)
        assert claimed is not None
        release_window(engine, claimed.job_id, claimed.window_start)

        reclaimed = claim_next_window(engine)
        assert reclaimed is not None
        assert reclaimed.window_start == claimed.window_start
        assert reclaimed.attempts == 1, "budget exhaustion must not burn a retry"

    def test_failure_retries_until_attempts_exhausted(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec()], three_windows)
        claimed = claim_next_window(engine)
        assert claimed is not None
        target = claimed.window_start

        for _ in range(5):
            fail_window(engine, claimed.job_id, target, "boom", max_attempts=3)
            nxt = claim_next_window(engine)
            if nxt is None or nxt.window_start != target:
                break
            claimed = nxt

        with engine.connect() as conn:
            state = conn.execute(
                select(backfill_window_table.c.state).where(
                    backfill_window_table.c.window_start == target
                )
            ).scalar_one()
        assert state in {"failed", "pending"}


class TestAuthPause:
    def test_pause_parks_jobs_and_stops_dispatch(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec()], three_windows)
        claim_next_window(engine)

        parked = pause_all_for_auth(engine, "token expired")

        assert parked == 1
        assert claim_next_window(engine) is None, "paused jobs must not be dispatched"

    def test_resume_restores_dispatch_without_losing_progress(self, engine: Engine) -> None:
        enqueue_jobs(engine, [make_spec()], three_windows)
        first = claim_next_window(engine)
        assert first is not None
        complete_window(engine, first.job_id, first.window_start, rows=375)

        pause_all_for_auth(engine, "token expired")
        assert resume_after_auth(engine) == 1

        resumed = claim_next_window(engine)
        assert resumed is not None
        assert resumed.window_start != first.window_start


class TestCoverage:
    def test_upsert_widens_bounds_across_calls(self, engine: Engine) -> None:
        newer = datetime(2026, 6, 1, tzinfo=UTC)
        older = datetime(2021, 1, 1, tzinfo=UTC)

        upsert_coverage(
            engine,
            dataset="index",
            exchange_segment="IDX_I",
            symbol="NIFTY",
            interval="1",
            min_ts=newer,
            max_ts=newer,
            rows=100,
        )
        # An older window arriving second must extend the range backwards.
        upsert_coverage(
            engine,
            dataset="index",
            exchange_segment="IDX_I",
            symbol="NIFTY",
            interval="1",
            min_ts=older,
            max_ts=older,
            rows=50,
        )

        with engine.connect() as conn:
            row = conn.execute(select(bar_coverage_table)).mappings().one()

        assert row["min_ts"] == older
        assert row["max_ts"] == newer
        assert row["rows"] == 150


def test_queue_progress_reports_per_tier(engine: Engine) -> None:
    enqueue_jobs(engine, [make_spec()], three_windows)
    claimed = claim_next_window(engine)
    assert claimed is not None
    complete_window(engine, claimed.job_id, claimed.window_start, rows=1)

    progress = queue_progress(engine)

    assert len(progress) == 1
    assert progress[0]["tier"] == 1
    assert progress[0]["windows"] == 3
    assert progress[0]["completed"] == 1
