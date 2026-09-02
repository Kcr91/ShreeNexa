"""Unit tests for StockStrategyBacktestRunner, manual reconciliation, and REST endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.backtest.models import BacktestConfig
from app.backtest.runner import StockStrategyBacktestRunner
from app.backtest.store import backtest_store
from app.engine.contracts import FillEvent
from app.engine.costs import ProductType
from app.engine.sim_broker import FillTiming
from app.main import app
from app.strategy.ir import StrategyIR
from app.warehouse.schema import BarRecord
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    backtest_store.clear()


def _make_daily_bars(
    sec_id: str,
    start_dt: datetime,
    n_bars: int,
    start_p: float = 100.0,
    trend: float = 1.0,
) -> list[BarRecord]:
    bars: list[BarRecord] = []
    p = start_p
    for i in range(n_bars):
        ts = start_dt + timedelta(days=i)
        p += trend
        bars.append(
            BarRecord(
                symbol=sec_id,
                exchange_segment="NSE_EQ",
                security_id=sec_id,
                timestamp=ts,
                open=p - 0.5,
                high=p + 1.0,
                low=p - 1.0,
                close=p,
                volume=10000,
                open_interest=0,
            )
        )
    return bars


def _trade_key(t: FillEvent) -> tuple[str, str, int, float, datetime, float, float, float]:
    return (
        t.security_id,
        t.side.value,
        t.quantity,
        t.price,
        t.timestamp,
        t.brokerage,
        t.taxes,
        t.slippage,
    )


def test_buy_and_hold_manual_reconciliation() -> None:
    """Manual reconciliation of Buy-and-Hold strategy against spreadsheet expectations."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    bars = _make_daily_bars("RELIANCE", t0, 30, start_p=100.0, trend=1.0)
    dataset = {"RELIANCE": bars}

    # Strategy: Buy on first bar (close > 0)
    strategy = StrategyIR.model_validate(
        {
            "name": "Buy and Hold Reliance",
            "kind": "stock",
            "horizon": "positional",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "RELIANCE"}],
            },
            "timeframe": "1d",
            "sizing": {"type": "fixed_qty", "qty": 100},
            "entries": [
                {
                    "id": "entry_1",
                    "side": "BUY",
                    "when": {
                        "node": "IndicatorCompare",
                        "left": {"field": "close"},
                        "op": ">",
                        "right": 0.0,
                    },
                }
            ],
            "exits": [],
        }
    )

    config = BacktestConfig(
        strategy=strategy,
        start_date=t0,
        end_date=t0 + timedelta(days=30),
        initial_cash=100_000.0,
        fill_timing=FillTiming.NEXT_BAR_OPEN,
        product_type=ProductType.DELIVERY,
    )

    runner = StockStrategyBacktestRunner()
    result = runner.run(config, bars_dataset=dataset)

    # 1. Entry happens at Bar 1's Open:
    # Bar 0 close = 101.0 (signal generated).
    # Bar 1 open = 101.5. Buy 100 @ 101.5 = 10,150.0.
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.price == 101.5
    assert trade.quantity == 100

    # 2. Final bar (Bar 29) close = 130.0.
    # Cost basis = 10,150.0. Final position value = 100 * 130.0 = 13,000.0.
    # Unrealized PnL = 13,000 - 10,150 = 2,850.0.
    pos_pnl = 2850.0
    expected_final_equity = 100_000.0 + pos_pnl - trade.total_cost

    assert result.metrics.final_equity == pytest.approx(expected_final_equity, abs=1e-2)
    assert result.metrics.unrealized_pnl == pytest.approx(pos_pnl, abs=1e-2)
    assert result.metrics.total_trades == 1
    assert result.metrics.total_return_pct == pytest.approx(
        ((expected_final_equity - 100_000.0) / 100_000.0) * 100.0, abs=1e-2
    )


def test_sma_crossover_strategy_reconciliation() -> None:
    """Manual reconciliation of SMA(3) / SMA(7) crossover strategy."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    # Sine/oscillating price series to generate crossover entries and exits
    bars: list[BarRecord] = []
    prices = [
        100.0, 101.0, 102.0, 104.0, 106.0, 108.0, 107.0, 105.0, 103.0, 101.0,
        102.0, 105.0, 109.0, 112.0, 110.0, 106.0, 103.0, 100.0, 102.0, 105.0,
    ]
    for i, p in enumerate(prices):
        bars.append(
            BarRecord(
                symbol="TCS",
                exchange_segment="NSE_EQ",
                security_id="TCS",
                timestamp=t0 + timedelta(days=i),
                open=p - 0.5,
                high=p + 1.0,
                low=p - 1.0,
                close=p,
                volume=5000,
                open_interest=0,
            )
        )
    dataset = {"TCS": bars}

    strategy = StrategyIR.model_validate(
        {
            "name": "SMA Crossover TCS",
            "kind": "stock",
            "horizon": "positional",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "TCS"}],
            },
            "timeframe": "1d",
            "sizing": {"type": "fixed_qty", "qty": 50},
            "indicators": {
                "fast_sma": {"fn": "SMA", "params": {"period": 3}, "source": "close"},
                "slow_sma": {"fn": "SMA", "params": {"period": 7}, "source": "close"},
            },
            "entries": [
                {
                    "id": "entry_cross",
                    "side": "BUY",
                    "when": {
                        "node": "CrossOver",
                        "left": {"ref": "fast_sma"},
                        "right": {"ref": "slow_sma"},
                    },
                }
            ],
            "exits": [
                {
                    "id": "exit_cross",
                    "type": "signal",
                    "when": {
                        "node": "CrossUnder",
                        "left": {"ref": "fast_sma"},
                        "right": {"ref": "slow_sma"},
                    },
                }
            ],
        }
    )

    config = BacktestConfig(
        strategy=strategy,
        start_date=t0,
        end_date=t0 + timedelta(days=20),
        initial_cash=500_000.0,
        fill_timing=FillTiming.NEXT_BAR_OPEN,
        product_type=ProductType.DELIVERY,
    )

    runner = StockStrategyBacktestRunner()
    result = runner.run(config, bars_dataset=dataset)

    assert len(result.trades) >= 2
    # Verify trade alternating sides
    assert result.trades[0].side.value == "BUY"
    assert result.trades[1].side.value == "SELL"
    assert result.metrics.total_trades == len(result.trades)
    assert result.metrics.final_equity > 0


def test_backtest_determinism_and_byte_identical_reproducibility() -> None:
    """Determinism proof: running identical config/data produces byte-identical results."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    bars = _make_daily_bars("INFY", t0, 20, start_p=1500.0, trend=2.5)
    dataset = {"INFY": bars}

    strategy = StrategyIR.model_validate(
        {
            "name": "Deterministic Strategy",
            "kind": "stock",
            "horizon": "positional",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "INFY"}],
            },
            "timeframe": "1d",
            "sizing": {"type": "fixed_qty", "qty": 20},
            "entries": [
                {
                    "id": "entry_high",
                    "side": "BUY",
                    "when": {
                        "node": "IndicatorCompare",
                        "left": {"field": "close"},
                        "op": ">",
                        "right": 1500.0,
                    },
                }
            ],
            "exits": [],
        }
    )

    config = BacktestConfig(
        strategy=strategy,
        start_date=t0,
        end_date=t0 + timedelta(days=20),
        initial_cash=200_000.0,
        fill_timing=FillTiming.NEXT_BAR_OPEN,
        seed=42,
    )

    runner = StockStrategyBacktestRunner()
    res1 = runner.run(config, bars_dataset=dataset)
    res2 = runner.run(config, bars_dataset=dataset)

    assert res1.metrics.model_dump() == res2.metrics.model_dump()
    assert len(res1.trades) == len(res2.trades)
    assert [_trade_key(t) for t in res1.trades] == [_trade_key(t) for t in res2.trades]
    assert [e.model_dump() for e in res1.equity_curve] == [
        e.model_dump() for e in res2.equity_curve
    ]


def test_backtest_api_endpoints() -> None:
    """Test FastAPI /api/v1/backtests/run, list, and detail endpoints."""
    payload: dict[str, Any] = {
        "strategy": {
            "name": "API Backtest",
            "kind": "stock",
            "horizon": "positional",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "RELIANCE"}],
            },
            "timeframe": "1d",
            "sizing": {"type": "fixed_qty", "qty": 10},
            "entries": [
                {
                    "id": "entry_all",
                    "side": "BUY",
                    "when": {
                        "node": "IndicatorCompare",
                        "left": {"field": "close"},
                        "op": ">",
                        "right": 0.0,
                    },
                }
            ],
            "exits": [],
        },
        "start_date": "2026-09-01T09:15:00Z",
        "end_date": "2026-09-30T15:30:00Z",
        "initial_cash": 100000.0,
        "fill_timing": "NEXT_BAR_OPEN",
        "product_type": "DELIVERY",
    }

    # 1. Run Backtest
    resp = client.post("/api/v1/backtests/run", json=payload)
    assert resp.status_code == 201
    res_data = resp.json()
    bt_id = res_data["backtest_id"]
    assert res_data["strategy_name"] == "API Backtest"
    assert "metrics" in res_data

    # 2. List Backtests
    resp = client.get("/api/v1/backtests")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. Get Backtest Detail
    resp = client.get(f"/api/v1/backtests/{bt_id}")
    assert resp.status_code == 200
    assert resp.json()["backtest_id"] == bt_id

    # 4. Unknown Backtest 404
    resp = client.get("/api/v1/backtests/unknown-id")
    assert resp.status_code == 404
