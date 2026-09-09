"""Integration tests for the backfill fetch driver.

Requires Postgres (skipped cleanly when unreachable). A stub transport stands in for
Dhan, so these prove the orchestration contract without touching the live API: what gets
fetched, what gets checkpointed, and - most importantly - what is *not* re-fetched after
a restart, a 401, or an exhausted budget.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.exceptions import DhanAuthenticationError, DhanRateLimitError
from app.worker.backfill_queue import (
    JobSpec,
    backfill_job_table,
    backfill_window_table,
    bar_coverage_table,
    enqueue_jobs,
)
from app.worker.backfill_runner import BackfillRunner, BudgetExhausted
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.engine import Engine


class StubTransport:
    """Returns canned bars, counts calls, and can be told to fail."""

    def __init__(self, bars_per_call: int = 3) -> None:
        self.bars_per_call = bars_per_call
        self.calls: list[dict[str, Any]] = []
        self.raise_next: Exception | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> tuple[int, dict[str, str], bytes]:
        self.calls.append({"path": path, "json": json_data})
        if self.raise_next is not None:
            err, self.raise_next = self.raise_next, None
            raise err

        # 2026-09-01 03:45 UTC is 09:15 IST, exactly NSE market open, so the
        # session guard accepts this fixture.
        base = 1788234300
        n = self.bars_per_call
        body = {
            "open": [100.0 + i for i in range(n)],
            "high": [101.0 + i for i in range(n)],
            "low": [99.0 + i for i in range(n)],
            "close": [100.5 + i for i in range(n)],
            "volume": [1000 + i for i in range(n)],
            "timestamp": [base + 60 * i for i in range(n)],
        }
        return 200, {"Content-Type": "application/json"}, json.dumps(body).encode()


class PermissiveLimiter:
    def __init__(self) -> None:
        self.acquisitions = 0

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        self.acquisitions += 1
        return 0.0

    def try_acquire(self, category: str, cost: float = 1.0) -> bool:
        return True

    def get_budget_usage(self, category: str) -> dict[str, Any]:
        return {}


class ExhaustedLimiter(PermissiveLimiter):
    """Stands in for a spent per-day budget."""

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        raise DhanRateLimitError("daily budget exhausted", status_code=429)


def build_runner(
    backfill_engine: Engine,
    tmp_path: Path,
    transport: StubTransport,
    limiter: Any | None = None,
) -> BackfillRunner:
    client = DhanRestClient(
        credentials=DhanCredentials(client_id="0000000000", access_token=SecretStr("t")),
        transport=transport,
        limiter=limiter or PermissiveLimiter(),
    )
    return BackfillRunner(
        backfill_engine, client=client, data_root=tmp_path, auto_renew_token=False
    )


def two_windows(spec: JobSpec) -> list[tuple[date, date]]:
    mid = spec.start_date + timedelta(days=44)
    return [(spec.start_date, mid), (mid + timedelta(days=1), spec.end_date)]


def equity_spec(**kw: Any) -> JobSpec:
    base: dict[str, Any] = {
        "tier": 4,
        "dataset": "intraday",
        "exchange_segment": "NSE_EQ",
        "security_id": "2885",
        "symbol": "RELIANCE",
        "interval": "1",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 3, 31),
    }
    base.update(kw)
    return JobSpec(**base)


class TestFetchAndCheckpoint:
    def test_run_once_fetches_and_completes_a_window(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        transport = StubTransport()
        runner = build_runner(backfill_engine, tmp_path, transport)

        assert runner.run_once() is True
        assert len(transport.calls) == 1
        assert transport.calls[0]["path"] == "charts/intraday"

        with backfill_engine.connect() as conn:
            states = sorted(r[0] for r in conn.execute(select(backfill_window_table.c.state)).all())
        assert states == ["done", "pending"]

    def test_run_once_returns_false_on_empty_queue(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        runner = build_runner(backfill_engine, tmp_path, StubTransport())
        assert runner.run_once() is False

    def test_daily_dataset_uses_the_separate_budget_endpoint(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        """charts/historical has its own 7,000/day; routing there is what makes the
        all-stock EOD tier free relative to the intraday grind."""
        enqueue_jobs(backfill_engine, [equity_spec(dataset="daily", interval="D")], two_windows)
        transport = StubTransport()
        runner = build_runner(backfill_engine, tmp_path, transport)

        runner.run_once()

        assert transport.calls[0]["path"] == "charts/historical"

    def test_drain_processes_every_window_exactly_once(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        transport = StubTransport()
        runner = build_runner(backfill_engine, tmp_path, transport)

        stats = runner.drain()

        assert stats.windows_attempted == 2
        assert stats.stopped_reason == "drained"
        assert len(transport.calls) == 2

    def test_coverage_is_recorded_after_a_successful_window(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        build_runner(backfill_engine, tmp_path, StubTransport()).run_once()

        with backfill_engine.connect() as conn:
            row = conn.execute(select(bar_coverage_table)).mappings().one()

        assert row["symbol"] == "RELIANCE"
        assert row["rows"] == 3
        assert row["min_ts"] is not None and row["max_ts"] is not None


class TestResumeAfterRestart:
    def test_completed_windows_are_never_re_fetched(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        """The property the whole multi-week download depends on."""
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)

        first = StubTransport()
        build_runner(backfill_engine, tmp_path, first).run_once()
        assert len(first.calls) == 1

        # A brand-new runner, as after a crash or reboot.
        second = StubTransport()
        stats = build_runner(backfill_engine, tmp_path, second).drain()

        assert stats.windows_attempted == 1, "only the outstanding window should remain"
        assert len(second.calls) == 1
        assert second.calls[0]["json"]["fromDate"] != first.calls[0]["json"]["fromDate"]


class TestBudgetExhaustion:
    def test_budget_exhaustion_stops_the_run_without_losing_the_window(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        runner = build_runner(
            backfill_engine, tmp_path, StubTransport(), limiter=ExhaustedLimiter()
        )

        stats = runner.drain()

        assert stats.stopped_reason == "budget_exhausted"
        with backfill_engine.connect() as conn:
            states = sorted(r[0] for r in conn.execute(select(backfill_window_table.c.state)).all())
        assert states == ["pending", "pending"], "leases must be returned, not lost"

    def test_budget_exhaustion_does_not_consume_an_attempt(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        build_runner(backfill_engine, tmp_path, StubTransport(), limiter=ExhaustedLimiter()).drain()

        with backfill_engine.connect() as conn:
            attempts = [r[0] for r in conn.execute(select(backfill_window_table.c.attempts)).all()]
        assert max(attempts) == 0, "an exhausted budget is not the window's fault"

    def test_run_once_raises_budget_exhausted(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        runner = build_runner(
            backfill_engine, tmp_path, StubTransport(), limiter=ExhaustedLimiter()
        )

        with pytest.raises(BudgetExhausted):
            runner.run_once()


class TestAuthFailure:
    def test_auth_failure_parks_jobs_and_keeps_progress(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)

        good = StubTransport()
        build_runner(backfill_engine, tmp_path, good).run_once()

        bad = StubTransport()
        bad.raise_next = DhanAuthenticationError("token expired", status_code=401)
        stats = build_runner(backfill_engine, tmp_path, bad).drain()

        assert stats.stopped_reason == "paused_auth"
        with backfill_engine.connect() as conn:
            job_state = conn.execute(select(backfill_job_table.c.state)).scalar_one()
            window_states = sorted(
                r[0] for r in conn.execute(select(backfill_window_table.c.state)).all()
            )

        assert job_state == "paused_auth"
        assert window_states == ["done", "pending"], "finished work must survive the pause"

    def test_auth_failure_does_not_consume_an_attempt(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        bad = StubTransport()
        bad.raise_next = DhanAuthenticationError("token expired", status_code=401)

        build_runner(backfill_engine, tmp_path, bad).drain()

        with backfill_engine.connect() as conn:
            attempts = [r[0] for r in conn.execute(select(backfill_window_table.c.attempts)).all()]
        assert max(attempts) == 0


class TestRawProvenance:
    def test_raw_payload_is_persisted_for_every_window(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        build_runner(backfill_engine, tmp_path, StubTransport()).run_once()

        raw_files = list((tmp_path / "raw").rglob("payload.json"))
        assert raw_files, "immutable raw ingest must be written before parsing"

        with backfill_engine.connect() as conn:
            ingest_id = conn.execute(
                select(backfill_window_table.c.raw_ingest_id).where(
                    backfill_window_table.c.state == "done"
                )
            ).scalar_one()
        assert ingest_id, "checkpoint must reference the raw ingest for provenance"


def test_empty_response_is_terminal_not_retried(backfill_engine: Engine, tmp_path: Path) -> None:
    enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
    runner = build_runner(backfill_engine, tmp_path, StubTransport(bars_per_call=0))

    runner.run_once()

    with backfill_engine.connect() as conn:
        states = sorted(r[0] for r in conn.execute(select(backfill_window_table.c.state)).all())
    assert "empty" in states


class TestAnomalyFlagging:
    """Nothing fetched is discarded. Exchange calendars are not ours to adjudicate:
    holidays differ per exchange, dates move, and special or shortened sessions exist.
    Unusual windows are stored and flagged for the Historic Data Report instead."""

    def odd_hours_transport(self) -> StubTransport:
        transport = StubTransport()
        # 2021-09-11 was a Saturday; 22:55 UTC is far outside any NSE session.
        base = 1631487300
        transport.request = lambda *a, **k: (  # type: ignore[method-assign]
            200,
            {},
            json.dumps(
                {
                    "open": [1.0] * 60,
                    "high": [2.0] * 60,
                    "low": [0.5] * 60,
                    "close": [1.5] * 60,
                    "volume": [10] * 60,
                    "timestamp": [base + 120 * i for i in range(60)],
                }
            ).encode(),
        )
        return transport

    def test_odd_window_is_still_stored(self, backfill_engine: Engine, tmp_path: Path) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        runner = build_runner(backfill_engine, tmp_path, self.odd_hours_transport())

        runner.run_once()

        with backfill_engine.connect() as conn:
            states = [r[0] for r in conn.execute(select(backfill_window_table.c.state)).all()]
            coverage = conn.execute(select(bar_coverage_table)).mappings().all()

        assert "done" in states, "whatever the API returned must be kept"
        assert coverage, "stored data must be reported as coverage"

    def test_odd_window_is_flagged_suspect_with_reasons(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        build_runner(backfill_engine, tmp_path, self.odd_hours_transport()).run_once()

        with backfill_engine.connect() as conn:
            row = (
                conn.execute(
                    select(
                        backfill_window_table.c.suspect,
                        backfill_window_table.c.quality,
                    ).where(backfill_window_table.c.state == "done")
                )
                .mappings()
                .one()
            )

        assert row["suspect"] is True
        reasons = row["quality"]["suspect_reasons"]
        assert reasons, "a flagged window must say why"
        assert any("market hours" in r for r in reasons)
        # These bars land at 04:25 IST - outside the session but on a weekday, so the
        # out-of-hours count is the signal here, not the weekend count.
        assert row["quality"]["out_of_hours"] == row["quality"]["bars"]
        assert row["quality"]["in_hours"] == 0

    def test_clean_window_is_not_flagged(self, backfill_engine: Engine, tmp_path: Path) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        build_runner(backfill_engine, tmp_path, StubTransport()).run_once()

        with backfill_engine.connect() as conn:
            row = (
                conn.execute(
                    select(
                        backfill_window_table.c.suspect,
                        backfill_window_table.c.quality,
                    ).where(backfill_window_table.c.state == "done")
                )
                .mappings()
                .one()
            )

        assert row["suspect"] is False
        assert row["quality"]["suspect_reasons"] == []
        assert row["quality"]["in_hours"] == row["quality"]["bars"]

    def test_quality_records_the_observed_span(
        self, backfill_engine: Engine, tmp_path: Path
    ) -> None:
        enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
        build_runner(backfill_engine, tmp_path, StubTransport()).run_once()

        with backfill_engine.connect() as conn:
            row = (
                conn.execute(
                    select(
                        backfill_window_table.c.min_ts,
                        backfill_window_table.c.max_ts,
                        backfill_window_table.c.distinct_days,
                    ).where(backfill_window_table.c.state == "done")
                )
                .mappings()
                .one()
            )

        assert row["min_ts"] is not None and row["max_ts"] is not None
        assert row["max_ts"] >= row["min_ts"]
        assert row["distinct_days"] >= 1


def test_drain_reports_real_totals(backfill_engine: Engine, tmp_path: Path) -> None:
    """Zeroed counters during a multi-week run would hide what is happening."""
    enqueue_jobs(backfill_engine, [equity_spec()], two_windows)
    runner = build_runner(backfill_engine, tmp_path, StubTransport(bars_per_call=3))

    stats = runner.drain()

    assert stats.windows_attempted == 2
    assert stats.windows_completed == 2
    assert stats.bars_written == 6
