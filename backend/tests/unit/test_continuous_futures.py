"""Unit tests for continuous synthetic futures series generator and roll policies."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from app.marketdata.continuous_futures import (
    AdjustmentMethod,
    ContinuousFuturesGenerator,
    ContractMetadata,
    RollTrigger,
)
from app.warehouse.schema import BarRecord

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_futures_contracts.json"


def load_fixture_contracts() -> list[ContractMetadata]:
    """Load sample NIFTY futures contracts from fixture file."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    contracts: list[ContractMetadata] = []
    for c in data["contracts"]:
        bars: list[BarRecord] = []
        for b in c["bars"]:
            d = date.fromisoformat(b["date"])
            bars.append(
                BarRecord(
                    timestamp=datetime(d.year, d.month, d.day, 10, 0, tzinfo=UTC),
                    exchange_segment="NSE_FNO",
                    security_id="9999",
                    symbol=c["symbol"],
                    open=b["open"],
                    high=b["high"],
                    low=b["low"],
                    close=b["close"],
                    volume=b["volume"],
                    open_interest=b["open_interest"],
                )
            )
        contracts.append(
            ContractMetadata(
                symbol=c["symbol"],
                expiry_date=date.fromisoformat(c["expiry_date"]),
                bars=bars,
            )
        )
    return contracts


def test_calendar_roll_trigger() -> None:
    """Verify calendar roll trigger switching contracts exactly on roll deadline."""
    contracts = load_fixture_contracts()

    # Roll 1 day prior to August expiry (2026-08-27 -> roll on 2026-08-26)
    gen = ContinuousFuturesGenerator(
        roll_trigger=RollTrigger.CALENDAR,
        days_before_expiry=1,
        adjustment_method=AdjustmentMethod.UNADJUSTED,
    )
    bars, events = gen.build_continuous_series(contracts, continuous_symbol="NIFTY_F1")

    assert len(events) == 1
    assert events[0].roll_date == date(2026, 8, 26)
    assert events[0].from_symbol == "NIFTY26AUGFUT"
    assert events[0].to_symbol == "NIFTY26SEPFUT"
    assert len(bars) == 3


def test_volume_roll_trigger() -> None:
    """Verify volume roll trigger switching contracts when next volume > current volume."""
    contracts = load_fixture_contracts()

    # On 2026-08-24: AUG vol 500k vs SEP vol 250k (no roll)
    # On 2026-08-25: AUG vol 400k vs SEP vol 600k (roll happens on 2026-08-25)
    gen = ContinuousFuturesGenerator(
        roll_trigger=RollTrigger.VOLUME,
        adjustment_method=AdjustmentMethod.UNADJUSTED,
    )
    _bars, events = gen.build_continuous_series(contracts, continuous_symbol="NIFTY_F1")

    assert len(events) == 1
    assert events[0].roll_date == date(2026, 8, 25)
    assert "Volume roll" in events[0].trigger_reason


def test_open_interest_roll_trigger() -> None:
    """Verify open interest roll trigger switching contracts when next OI > current OI."""
    contracts = load_fixture_contracts()

    # On 2026-08-24: AUG OI 1000k vs SEP OI 500k (no roll)
    # On 2026-08-25: AUG OI 700k vs SEP OI 850k (roll happens on 2026-08-25)
    gen = ContinuousFuturesGenerator(
        roll_trigger=RollTrigger.OPEN_INTEREST,
        adjustment_method=AdjustmentMethod.UNADJUSTED,
    )
    _bars, events = gen.build_continuous_series(contracts, continuous_symbol="NIFTY_F1")

    assert len(events) == 1
    assert events[0].roll_date == date(2026, 8, 25)
    assert "OI roll" in events[0].trigger_reason


def test_difference_panama_adjustment() -> None:
    """Verify difference (Panama) adjustment shifts historical bars by roll spread."""
    contracts = load_fixture_contracts()

    # On 2026-08-25 roll: AUG close was 24900, SEP close was 25000 -> spread = +100.0
    gen = ContinuousFuturesGenerator(
        roll_trigger=RollTrigger.VOLUME,
        adjustment_method=AdjustmentMethod.DIFFERENCE,
    )
    bars, events = gen.build_continuous_series(contracts, continuous_symbol="NIFTY_F1")

    assert len(events) == 1
    assert events[0].spread == 100.0

    # Bar on 2026-08-24 was unadjusted open 24800, close 24850 -> with +100 spread: 24900, 24950
    assert bars[0].open == 24900.0
    assert bars[0].close == 24950.0

    # Bar on 2026-08-25 (roll date and after) remains nominal SEP contract price
    assert bars[1].open == 24960.0
    assert bars[1].close == 25000.0


def test_ratio_adjustment_and_arrow_table() -> None:
    """Verify ratio multiplicative adjustment and PyArrow table export."""
    contracts = load_fixture_contracts()

    # On 2026-08-25 roll: ratio = 25000 / 24900 = 1.004016
    gen = ContinuousFuturesGenerator(
        roll_trigger=RollTrigger.VOLUME,
        adjustment_method=AdjustmentMethod.RATIO,
    )
    table, events = gen.build_continuous_table(contracts, continuous_symbol="NIFTY_F1")

    assert len(events) == 1
    assert round(events[0].ratio, 4) == 1.0040
    assert table.num_rows == 3

    # Prior bar (2026-08-24) open scaled by ratio: 24800 * (25000 / 24900) = 24899.5984
    open_0 = table.column("open").to_pylist()[0]
    assert round(open_0, 2) == 24899.60
