"""Unit tests for tier expansion, window sizing, and the worker backfill scheduler."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from itertools import pairwise

import pytest
from app.dhan.exceptions import DhanAuthenticationError
from app.warehouse.paths import DataRootCapacityError
from app.worker.backfill_queue import JobSpec
from app.worker.backfill_runner import BudgetExhausted, RunStats
from app.worker.core import (
    AUTH_BACKOFF,
    BUDGET_BACKOFF,
    ENABLE_ENV_VAR,
    BackfillScheduler,
    backfill_enabled,
)
from app.worker.minute_backfill import MAX_INTRADAY_WINDOW_DAYS
from app.worker.options_backfill import MAX_OPTIONS_WINDOW_DAYS
from app.worker.universe_builder import (
    HISTORY_YEARS,
    INDEX_OPTION_UNDERLYINGS,
    daily_windows,
    default_history_start,
    intraday_windows,
    option_windows,
    strike_offsets,
    windows_for,
)


def spec(dataset: str, start: date, end: date) -> JobSpec:
    return JobSpec(
        tier=1,
        dataset=dataset,
        exchange_segment="NSE_EQ",
        security_id="1",
        symbol="X",
        interval="1",
        start_date=start,
        end_date=end,
    )


class TestWindowSizing:
    def test_intraday_uses_the_90_day_api_maximum(self) -> None:
        windows = intraday_windows(spec("intraday", date(2026, 1, 1), date(2026, 12, 31)))
        spans = {(w[1] - w[0]).days + 1 for w in windows}
        assert max(spans) == MAX_INTRADAY_WINDOW_DAYS

    def test_options_use_the_45_day_api_maximum(self) -> None:
        windows = option_windows(spec("options", date(2026, 1, 1), date(2026, 12, 31)))
        spans = {(w[1] - w[0]).days + 1 for w in windows}
        assert max(spans) == MAX_OPTIONS_WINDOW_DAYS

    def test_daily_is_a_single_unwindowed_call(self) -> None:
        """charts/historical serves since inception, so splitting it wastes calls."""
        windows = daily_windows(spec("daily", date(2005, 1, 1), date(2026, 1, 1)))
        assert len(windows) == 1

    def test_windows_are_contiguous_and_non_overlapping(self) -> None:
        windows = intraday_windows(spec("intraday", date(2026, 1, 1), date(2026, 12, 31)))
        for earlier, later in pairwise(windows):
            assert later[0] == earlier[1] + timedelta(days=1)

    def test_windows_cover_the_whole_range_exactly(self) -> None:
        start, end = date(2026, 1, 1), date(2026, 12, 31)
        windows = intraday_windows(spec("intraday", start, end))
        assert windows[0][0] == start
        assert windows[-1][1] == end

    def test_single_day_range_yields_one_window(self) -> None:
        day = date(2026, 3, 3)
        assert intraday_windows(spec("intraday", day, day)) == [(day, day)]

    def test_inverted_range_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="cannot be after"):
            intraday_windows(spec("intraday", date(2026, 5, 1), date(2026, 1, 1)))

    def test_windows_for_dispatches_on_dataset(self) -> None:
        start, end = date(2026, 1, 1), date(2026, 12, 31)
        assert len(windows_for(spec("daily", start, end))) == 1
        assert len(windows_for(spec("options", start, end))) > len(
            windows_for(spec("intraday", start, end))
        ), "45-day option windows must be more numerous than 90-day intraday ones"


class TestStrikeCoverage:
    def test_index_covers_atm_plus_minus_10(self) -> None:
        offsets = strike_offsets(is_index=True)
        assert min(offsets) == -10
        assert max(offsets) == 10
        assert len(offsets) == 21

    def test_stock_covers_atm_plus_minus_5(self) -> None:
        """Widened from the original ATM+/-3 by the authorised F1.4 amendment."""
        offsets = strike_offsets(is_index=False)
        assert min(offsets) == -5
        assert max(offsets) == 5
        assert len(offsets) == 11

    def test_atm_itself_is_always_collected(self) -> None:
        assert 0 in strike_offsets(is_index=True)
        assert 0 in strike_offsets(is_index=False)


class TestHistoryHorizon:
    def test_default_start_is_five_years_back(self) -> None:
        today = date(2026, 9, 8)
        start = default_history_start(today)
        assert (today - start).days == 365 * HISTORY_YEARS

    def test_index_underlyings_include_both_exchanges(self) -> None:
        segments = {segment for _, segment in INDEX_OPTION_UNDERLYINGS}
        assert segments == {"NSE_FNO", "BSE_FNO"}

    def test_sensex_and_banknifty_are_covered(self) -> None:
        symbols = {symbol for symbol, _ in INDEX_OPTION_UNDERLYINGS}
        assert {"NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"} <= symbols


class StubRunner:
    """Stands in for BackfillRunner, scripted to raise or return."""

    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls = 0

    def drain(self, max_windows: int | None = None, **_: object) -> RunStats:
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        assert isinstance(self.outcome, RunStats)
        return self.outcome


class TestScheduler:
    def test_beat_reports_the_drain_outcome(self) -> None:
        runner = StubRunner(RunStats(windows_attempted=3, stopped_reason="drained"))
        scheduler = BackfillScheduler(runner)  # type: ignore[arg-type]

        assert scheduler.beat() == "drained"
        assert runner.calls == 1

    def test_budget_exhaustion_pauses_further_beats(self) -> None:
        """Hammering a spent budget every second would achieve nothing."""
        runner = StubRunner(BudgetExhausted("spent"))
        scheduler = BackfillScheduler(runner)  # type: ignore[arg-type]
        now = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)

        assert scheduler.beat(now) == "budget_exhausted"
        assert scheduler.beat(now + timedelta(seconds=1)) == "paused"
        assert runner.calls == 1, "no further calls while paused"

    def test_pause_expires_and_work_resumes(self) -> None:
        runner = StubRunner(BudgetExhausted("spent"))
        scheduler = BackfillScheduler(runner)  # type: ignore[arg-type]
        now = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
        scheduler.beat(now)

        scheduler.runner = StubRunner(RunStats(stopped_reason="drained"))  # type: ignore[assignment]
        assert scheduler.beat(now + BUDGET_BACKOFF + timedelta(seconds=1)) == "drained"

    def test_auth_failure_pauses_with_its_own_backoff(self) -> None:
        runner = StubRunner(DhanAuthenticationError("expired", status_code=401))
        scheduler = BackfillScheduler(runner)  # type: ignore[arg-type]
        now = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)

        assert scheduler.beat(now) == "paused_auth"
        assert scheduler.paused_until == now + AUTH_BACKOFF

    def test_disk_full_pauses(self) -> None:
        from pathlib import Path

        runner = StubRunner(DataRootCapacityError(Path("/data"), 1, 2))
        scheduler = BackfillScheduler(runner)  # type: ignore[arg-type]

        assert scheduler.beat() == "disk_full"

    def test_stop_reason_from_stats_also_pauses(self) -> None:
        """drain() reports these as a stats field rather than raising."""
        runner = StubRunner(RunStats(stopped_reason="budget_exhausted"))
        scheduler = BackfillScheduler(runner)  # type: ignore[arg-type]

        assert scheduler.beat() == "budget_exhausted"
        assert scheduler.paused_until is not None

    def test_beat_is_bounded_so_stop_signals_are_honoured(self) -> None:
        captured: dict[str, object] = {}

        class Recording(StubRunner):
            def drain(self, max_windows: int | None = None, **_: object) -> RunStats:
                captured["max_windows"] = max_windows
                return RunStats(stopped_reason="max_windows")

        BackfillScheduler(Recording(None), windows_per_beat=7).beat()  # type: ignore[arg-type]
        assert captured["max_windows"] == 7


class TestEnableFlag:
    def test_enabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ENABLE_ENV_VAR, raising=False)
        assert backfill_enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "FALSE"])
    def test_can_be_disabled(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv(ENABLE_ENV_VAR, value)
        assert backfill_enabled() is False
