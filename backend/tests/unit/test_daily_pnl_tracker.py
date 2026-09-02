"""Unit tests for shared Daily P&L and Time-Weighted Return (TWR) ledger."""

from __future__ import annotations

from datetime import date

import pytest
from app.engine.daily_pnl import (
    DailyPnLTracker,
    ExecutionMode,
)


def test_fundamental_accounting_identity() -> None:
    """Verify ending equity identically satisfies E_end = E_start + C + P_real + delta_U - K."""
    tracker = DailyPnLTracker(initial_capital=1_000_000.0, mode=ExecutionMode.BACKTEST)

    # Day 1: Realized +5k, Unrealized 12k, Costs 350, No cashflow
    r1 = tracker.record_day(
        record_date=date(2026, 1, 5),
        realized_pnl=5_000.0,
        unrealized_pnl=12_000.0,
        transaction_costs=350.0,
        cashflow=0.0,
    )
    assert r1.starting_equity == 1_000_000.0
    assert r1.mtm_change == 12_000.0
    assert r1.gross_pnl == 17_000.0
    assert r1.net_pnl == 16_650.0
    assert r1.ending_equity == 1_016_650.0
    assert tracker.current_equity == 1_016_650.0

    # Day 2: Realized -3k, Unrealized drops from 12k to 10k (delta = -2k), Costs 200, Deposit +50k
    r2 = tracker.record_day(
        record_date=date(2026, 1, 6),
        realized_pnl=-3_000.0,
        unrealized_pnl=10_000.0,
        transaction_costs=200.0,
        cashflow=50_000.0,
    )
    assert r2.starting_equity == 1_016_650.0
    assert r2.mtm_change == -2_000.0
    assert r2.gross_pnl == -5_000.0
    assert r2.net_pnl == -5_200.0
    # E_end = 1,016,650 + 50,000 - 5,200 = 1,061,450
    assert r2.ending_equity == 1_061_450.0
    assert tracker.current_equity == 1_061_450.0


def test_pure_cashflow_zero_return_invariance() -> None:
    """Verify deposits and withdrawals without trading P&L produce exactly 0% return."""
    tracker = DailyPnLTracker(initial_capital=500_000.0)

    # Day 1: Deposit 500,000, 0 PnL
    r1 = tracker.record_day(
        record_date=date(2026, 2, 2),
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        transaction_costs=0.0,
        cashflow=500_000.0,
    )
    assert r1.ending_equity == 1_000_000.0
    assert r1.daily_return == 0.0
    assert tracker.cumulative_twr == pytest.approx(0.0)

    # Day 2: Withdrawal -300,000, 0 PnL
    r2 = tracker.record_day(
        record_date=date(2026, 2, 3),
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        transaction_costs=0.0,
        cashflow=-300_000.0,
    )
    assert r2.ending_equity == 700_000.0
    assert r2.daily_return == 0.0
    assert tracker.cumulative_twr == pytest.approx(0.0)


def test_twr_subperiod_compounding() -> None:
    """Verify Time-Weighted Return (TWR) correctly chains returns independent of cashflow."""
    tracker = DailyPnLTracker(initial_capital=100_000.0)

    # Day 1: +10% return (Net PnL = +10,000 on 100k)
    r1 = tracker.record_day(
        record_date=date(2026, 3, 2),
        realized_pnl=10_000.0,
    )
    assert r1.daily_return == pytest.approx(0.10)
    assert tracker.cumulative_twr == pytest.approx(0.10)
    assert r1.ending_equity == 110_000.0

    # Day 2: Deposit +90k (Base = 200k), Net PnL = +20k (+10% on 200k)
    r2 = tracker.record_day(
        record_date=date(2026, 3, 3),
        realized_pnl=20_000.0,
        cashflow=90_000.0,
    )
    assert r2.daily_return == pytest.approx(0.10)
    # Compounded TWR: (1 + 0.10) * (1 + 0.10) - 1 = 0.21 (21%)
    assert tracker.cumulative_twr == pytest.approx(0.21)
    assert tracker.cumulative_twr_pct == pytest.approx(21.0)
    assert r2.ending_equity == 220_000.0


def test_monthly_and_yearly_summaries() -> None:
    """Verify ledger correctly aggregates monthly and yearly performance metrics."""
    tracker = DailyPnLTracker(initial_capital=100_000.0)

    # January 2026: 2 days of +5% and +5%
    tracker.record_day(date(2026, 1, 15), realized_pnl=5_000.0)
    tracker.record_day(date(2026, 1, 16), realized_pnl=5_250.0)

    # February 2026: 1 day of -2%
    tracker.record_day(date(2026, 2, 10), realized_pnl=-2_205.0)

    months = tracker.get_monthly_summaries()
    assert len(months) == 2

    # Jan summary
    assert months[0].year == 2026
    assert months[0].month == 1
    assert months[0].trading_days == 2
    assert months[0].win_days == 2
    assert months[0].loss_days == 0
    assert months[0].net_pnl == 10_250.0
    assert months[0].twr_return_pct == pytest.approx(10.25)

    # Feb summary
    assert months[1].year == 2026
    assert months[1].month == 2
    assert months[1].trading_days == 1
    assert months[1].loss_days == 1
    assert months[1].net_pnl == -2_205.0

    years = tracker.get_yearly_summaries()
    assert len(years) == 1
    assert years[0].year == 2026
    assert years[0].trading_days == 3
    assert years[0].win_days == 2
    assert years[0].loss_days == 1
    assert years[0].net_pnl == 10_250.0 - 2_205.0
