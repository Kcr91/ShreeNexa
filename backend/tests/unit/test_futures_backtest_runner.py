"""Unit tests for FuturesStrategyBacktestRunner, contract rollovers, MTM, and margin tracking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.backtest.futures_models import (
    FuturesBacktestConfig,
    FuturesContractSpec,
    FuturesStrategyConfig,
)
from app.backtest.futures_runner import FuturesStrategyBacktestRunner
from app.engine.contracts import OrderSide
from app.warehouse.schema import BarRecord


def _make_futures_bars(
    symbol: str,
    start_dt: datetime,
    prices: list[float],
) -> list[BarRecord]:
    bars: list[BarRecord] = []
    for i, p in enumerate(prices):
        ts = start_dt + timedelta(days=i)
        bars.append(
            BarRecord(
                symbol=symbol,
                exchange_segment="NSE_FNO",
                security_id=symbol,
                timestamp=ts,
                open=p - 5.0,
                high=p + 10.0,
                low=p - 10.0,
                close=p,
                volume=50000,
                open_interest=25000,
            )
        )
    return bars


def test_futures_contract_rollover_execution_and_spread_reconciliation() -> None:
    """Reconcile 2-month futures rollover, roll spread, trade ledger, and total MTM."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    expiry1 = t0 + timedelta(days=10)
    expiry2 = t0 + timedelta(days=40)

    c1 = FuturesContractSpec(
        symbol="NIFTY26SEPFUT",
        underlying_symbol="NIFTY",
        expiry_date=expiry1,
        lot_size=50,
    )
    c2 = FuturesContractSpec(
        symbol="NIFTY26OCTFUT",
        underlying_symbol="NIFTY",
        expiry_date=expiry2,
        lot_size=50,
    )

    # 15 days of data covering the roll on Day 9 (1 day before Day 10 expiry)
    p1 = [25000.0 + 10.0 * i for i in range(15)]
    p2 = [25050.0 + 10.0 * i for i in range(15)]  # Trading at 50 pts premium (contango)

    bars_c1 = _make_futures_bars(c1.symbol, t0, p1)
    bars_c2 = _make_futures_bars(c2.symbol, t0, p2)

    strategy = FuturesStrategyConfig(
        name="NIFTY Trend Follower with Roll",
        underlying_symbol="NIFTY",
        lot_size=50,
        lots=1,
        days_before_expiry_roll=1,
        side=OrderSide.BUY,
    )

    config = FuturesBacktestConfig(
        strategy=strategy,
        start_date=t0,
        end_date=t0 + timedelta(days=14),
        initial_cash=1_000_000.0,
    )

    runner = FuturesStrategyBacktestRunner()
    result = runner.run(
        config=config,
        contracts=[c1, c2],
        bars_by_contract={c1.symbol: bars_c1, c2.symbol: bars_c2},
    )

    # 1. Trade Ledger: 3 trades (Initial Entry c1, Roll Exit c1, Roll Entry c2)
    assert len(result.trades) == 3
    assert (
        result.trades[0].security_id == "NIFTY26SEPFUT"
        and result.trades[0].side == OrderSide.BUY
    )
    assert (
        result.trades[1].security_id == "NIFTY26SEPFUT"
        and result.trades[1].side == OrderSide.SELL
    )
    assert (
        result.trades[2].security_id == "NIFTY26OCTFUT"
        and result.trades[2].side == OrderSide.BUY
    )

    # 2. Roll Record Verification
    assert len(result.rolls) == 1
    roll = result.rolls[0]
    assert roll.from_contract == "NIFTY26SEPFUT"
    assert roll.to_contract == "NIFTY26OCTFUT"
    assert roll.roll_spread == pytest.approx(50.0)  # Contango spread difference

    # 3. Final Equity Reconciled against Realized & Unrealized PnL:
    # Entry c1 @ Day 0 Open (25000 - 5 = 24995.0)
    # Roll Exit c1 @ Day 9 Close (25000 + 90 = 25090.0) -> (25090 - 24995) * 50 = 4750.0
    # Roll Entry c2 @ Day 9 Close (25050 + 90 = 25140.0)
    # Final c2 @ Day 14 Close (25050 + 140 = 25190.0) -> (25190 - 25140) * 50 = 2500.0
    # Gross Profit = 4750 + 2500 = 7250.0
    gross_pnl = 7250.0
    expected_final_equity = 1_000_000.0 + gross_pnl - result.metrics.total_costs
    assert result.metrics.final_equity == pytest.approx(expected_final_equity, abs=1.0)


def test_futures_mark_to_market_and_margin_tracking() -> None:
    """Test daily mark-to-market accounting and exchange margin requirement tracking."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    expiry = t0 + timedelta(days=20)

    c = FuturesContractSpec(
        symbol="NIFTY26SEPFUT",
        underlying_symbol="NIFTY",
        expiry_date=expiry,
        lot_size=50,
    )

    prices = [25000.0, 25100.0, 24900.0, 25200.0, 25300.0]
    bars = _make_futures_bars(c.symbol, t0, prices)

    strategy = FuturesStrategyConfig(
        name="NIFTY Positional MTM",
        underlying_symbol="NIFTY",
        lot_size=50,
        lots=1,
        margin_pct=0.12,
        side=OrderSide.BUY,
    )

    config = FuturesBacktestConfig(
        strategy=strategy,
        start_date=t0,
        end_date=t0 + timedelta(days=4),
        initial_cash=500_000.0,
    )

    runner = FuturesStrategyBacktestRunner()
    result = runner.run(
        config=config,
        contracts=[c],
        bars_by_contract={c.symbol: bars},
    )

    # Margin is tracked at every bar: 50 * Price * 0.12
    assert len(result.margin_history) == len(prices)
    for i, p in enumerate(prices):
        expected_margin = 50 * p * 0.12
        assert result.margin_history[i]["required_margin"] == pytest.approx(expected_margin)

    # Initial cash 500,000, entry @ 24995.0, final close @ 25300.0
    pnl = (25300.0 - 24995.0) * 50
    assert result.metrics.unrealized_pnl == pytest.approx(pnl)


def test_effective_dated_futures_taxation_boundary() -> None:
    """Verify STT difference between pre-Oct 2024 (0.0125%) and post-Oct 2024 (0.020%)."""
    # 1. Pre Oct 2024
    t_pre = datetime(2024, 9, 15, 9, 15, tzinfo=UTC)
    c_pre = FuturesContractSpec(
        symbol="NIFTY24SEPFUT",
        underlying_symbol="NIFTY",
        expiry_date=t_pre + timedelta(days=10),
        lot_size=25,
    )
    bars_pre = _make_futures_bars(c_pre.symbol, t_pre, [25000.0, 25100.0])

    strat = FuturesStrategyConfig(
        name="Tax Test", underlying_symbol="NIFTY", lot_size=25, side=OrderSide.SELL
    )
    cfg_pre = FuturesBacktestConfig(
        strategy=strat,
        start_date=t_pre,
        end_date=t_pre + timedelta(days=1),
        initial_cash=100000.0,
    )

    runner = FuturesStrategyBacktestRunner()
    res_pre = runner.run(cfg_pre, [c_pre], {c_pre.symbol: bars_pre})

    # 2. Post Oct 2024
    t_post = datetime(2024, 10, 15, 9, 15, tzinfo=UTC)
    c_post = FuturesContractSpec(
        symbol="NIFTY24OCTFUT",
        underlying_symbol="NIFTY",
        expiry_date=t_post + timedelta(days=10),
        lot_size=25,
    )
    bars_post = _make_futures_bars(c_post.symbol, t_post, [25000.0, 25100.0])
    cfg_post = FuturesBacktestConfig(
        strategy=strat,
        start_date=t_post,
        end_date=t_post + timedelta(days=1),
        initial_cash=100000.0,
    )

    res_post = runner.run(cfg_post, [c_post], {c_post.symbol: bars_post})

    # Sell trade STT comparison (25 * 24995 = 624,875 turnover):
    # Pre: 624,875 * 0.000125 = 78.109
    # Post: 624,875 * 0.00020 = 124.975
    assert res_post.trades[0].taxes > res_pre.trades[0].taxes
