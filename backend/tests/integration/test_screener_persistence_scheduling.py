"""Integration tests for offline scheduled screener execution and reproducible snapshot auditing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.screener.models import ScreenerDefinition
from app.screener.runner import PointInTimeScreenerRunner
from app.screener.scheduler import ScreenerScheduler
from app.screener.store import ScreenerStore
from app.strategy.ir import IndicatorCompareNode, IndicatorDef, InstrumentRef, StaticUniverse
from app.warehouse.schema import BarRecord


def _make_synth_bars(security_id: str, as_of: datetime) -> list[BarRecord]:
    bars: list[BarRecord] = []
    p = 100.0
    for i in range(30):
        ts = as_of - timedelta(days=29 - i)
        if security_id == "WINNER":
            p += 2.0
        else:
            p -= 0.5
        bars.append(
            BarRecord(
                symbol=security_id,
                exchange_segment="NSE_EQ",
                security_id=security_id,
                timestamp=ts,
                open=p - 0.2,
                high=p + 0.5,
                low=p - 0.5,
                close=p,
                volume=1000 + i * 10,
                open_interest=0,
            )
        )
    return bars


def test_offline_scheduled_execution_reproducibility() -> None:
    """Offline scheduled-run test proving output snapshots are reproducible and auditable."""
    store = ScreenerStore()
    as_of = datetime(2026, 9, 1, 15, 30, tzinfo=UTC)

    def mock_provider(seg: str, sec_id: str, dt: datetime, lookback: int) -> list[BarRecord]:
        return _make_synth_bars(sec_id, dt)

    runner = PointInTimeScreenerRunner(bar_provider=mock_provider)
    scheduler = ScreenerScheduler(store=store, runner=runner)

    # 1. Register Screener with cron schedule
    screener_def = ScreenerDefinition(
        name="Scheduled Breakout Screener",
        universe=StaticUniverse(
            instruments=[
                InstrumentRef(segment="NSE_EQ", security_id="WINNER"),
                InstrumentRef(segment="NSE_EQ", security_id="LOSER"),
            ]
        ),
        as_of=as_of,
        indicators={"sma5": IndicatorDef(fn="SMA", params={"period": 5}, source="close")},
        filter=IndicatorCompareNode(left={"field": "close"}, op=">", right={"ref": "sma5"}),
    )

    record = store.create_screener(screener_def, schedule="30 15 * * 1-5")

    # 2. Execute Scheduled Job (Run 1)
    snapshot1 = scheduler.run_scheduled_job(record.id)
    assert snapshot1.result.total_universe_size == 2
    assert snapshot1.result.matched_count == 1
    assert snapshot1.result.matches[0].security_id == "WINNER"

    # 3. Re-run Scheduled Job on identical point-in-time state (Run 2)
    snapshot2 = scheduler.run_scheduled_job(record.id)

    # 4. Verify Reproducible and Auditable Snapshots
    assert snapshot1.result.matched_count == snapshot2.result.matched_count
    assert snapshot1.result.matches[0].security_id == snapshot2.result.matches[0].security_id
    assert (
        snapshot1.result.matches[0].indicator_values == snapshot2.result.matches[0].indicator_values
    )

    # Check store audit trail history
    history = store.list_runs_for_screener(record.id)
    assert len(history) == 2
    assert history[0].run_id == snapshot2.run_id
    assert history[1].run_id == snapshot1.run_id
