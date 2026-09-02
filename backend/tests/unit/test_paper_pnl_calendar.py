"""Unit tests for paper P&L calendar and returns timeline (F9.7).

Verifies source_kind='paper' totals reconcile, proves zero duplicated calendar
or return calculation paths, and verifies REST API endpoints.
"""

from __future__ import annotations

from datetime import date

from app.engine.daily_pnl import DailyPnLTracker, ExecutionMode
from app.main import app
from app.paper.calendar import (
    generate_paper_calendar_report,
    generate_paper_returns_slice,
    record_paper_day,
    reset_paper_trackers,
)
from app.paper.repository import paper_repository
from fastapi.testclient import TestClient

client = TestClient(app)


def test_paper_fundamental_accounting_identity() -> None:
    """Proof: Paper trading daily PnL satisfies E_end = E_start + C + P_real + delta_MTM - K."""
    tracker = DailyPnLTracker(initial_capital=1_000_000.0, mode=ExecutionMode.PAPER)
    assert tracker._mode == ExecutionMode.PAPER

    # Day 1: Realized 6,000, Unrealized 15,000, Costs 420, No cashflow
    r1 = tracker.record_day(
        record_date=date(2026, 2, 2),
        realized_pnl=6_000.0,
        unrealized_pnl=15_000.0,
        transaction_costs=420.0,
        cashflow=0.0,
    )
    assert r1.starting_equity == 1_000_000.0
    assert r1.mtm_change == 15_000.0
    assert r1.gross_pnl == 21_000.0
    assert r1.net_pnl == 20_580.0
    assert r1.ending_equity == 1_020_580.0
    assert tracker.current_equity == 1_020_580.0
    assert r1.mode == ExecutionMode.PAPER

    # Day 2: Realized -2,500, Unrealized drops 4k, Costs 250, Cashflow +25,000
    r2 = tracker.record_day(
        record_date=date(2026, 2, 3),
        realized_pnl=-2_500.0,
        unrealized_pnl=11_000.0,
        transaction_costs=250.0,
        cashflow=25_000.0,
    )
    assert r2.starting_equity == 1_020_580.0
    assert r2.mtm_change == -4_000.0
    assert r2.gross_pnl == -6_500.0
    assert r2.net_pnl == -6_750.0
    assert r2.ending_equity == 1_020_580.0 + 25_000.0 - 6_750.0
    assert tracker.current_equity == r2.ending_equity


def test_zero_duplicated_calculation_path_parity() -> None:
    """Proof: Identical inputs produce bit-for-bit identical results in backtest and paper modes."""
    cap = 500_000.0
    bt_tracker = DailyPnLTracker(initial_capital=cap, mode=ExecutionMode.BACKTEST)
    paper_tracker = DailyPnLTracker(initial_capital=cap, mode=ExecutionMode.PAPER)

    test_days = [
        (date(2026, 1, 5), 4500.0, 8000.0, 320.0, 0.0),
        (date(2026, 1, 6), -1200.0, 6500.0, 150.0, 0.0),
        (date(2026, 1, 7), 8000.0, 14000.0, 480.0, 50000.0),
        (date(2026, 2, 2), 3200.0, 16000.0, 210.0, 0.0),
        (date(2026, 2, 3), -500.0, 15000.0, 180.0, -10000.0),
    ]

    for d, real, unrl, costs, cf in test_days:
        r_bt = bt_tracker.record_day(d, real, unrl, costs, cf)
        r_p = paper_tracker.record_day(d, real, unrl, costs, cf)

        # Exact parity checks
        assert r_bt.net_pnl == r_p.net_pnl
        assert r_bt.ending_equity == r_p.ending_equity
        assert r_bt.daily_return == r_p.daily_return
        assert r_bt.cumulative_twr == r_p.cumulative_twr

    # Monthly and yearly parity checks
    m_bt = bt_tracker.get_monthly_summaries()
    m_p = paper_tracker.get_monthly_summaries()
    assert len(m_bt) == len(m_p)
    for b_item, p_item in zip(m_bt, m_p, strict=True):
        assert b_item.net_pnl == p_item.net_pnl
        assert b_item.twr_return_pct == p_item.twr_return_pct
        assert b_item.win_days == p_item.win_days
        assert b_item.loss_days == p_item.loss_days

    y_bt = bt_tracker.get_yearly_summaries()
    y_p = paper_tracker.get_yearly_summaries()
    assert len(y_bt) == len(y_p)
    for yb, yp in zip(y_bt, y_p, strict=True):
        assert yb.net_pnl == yp.net_pnl
        assert yb.twr_return_pct == yp.twr_return_pct


def test_generate_paper_calendar_report_reconciliation() -> None:
    """Proof: generate_paper_calendar_report reconciles totals with source_kind='paper'."""
    reset_paper_trackers()
    paper_repository.clear()
    paper_repository.get_or_create_account("acc-cal-test", initial_capital=800_000.0)

    record_paper_day(
        account_id="acc-cal-test",
        record_date=date(2026, 3, 2),
        realized_pnl=5000.0,
        unrealized_pnl=8000.0,
        transaction_costs=300.0,
    )
    record_paper_day(
        account_id="acc-cal-test",
        record_date=date(2026, 3, 3),
        realized_pnl=-1500.0,
        unrealized_pnl=9500.0,
        transaction_costs=200.0,
    )

    report = generate_paper_calendar_report(account_id="acc-cal-test")
    assert report.source_kind == "paper"
    assert report.account_id == "acc-cal-test"
    assert report.initial_capital == 800_000.0
    assert len(report.daily_records) == 2
    assert len(report.monthly_summaries) == 1
    assert len(report.yearly_summaries) == 1

    # Check totals reconcile
    m = report.monthly_summaries[0]
    assert m.trading_days == 2
    tot_net = sum(d.net_pnl for d in report.daily_records)
    assert m.net_pnl == tot_net


def test_generate_paper_returns_slice_contract() -> None:
    """Proof: generate_paper_returns_slice returns compliant slice with phase='PAPER'."""
    reset_paper_trackers()
    paper_repository.clear()
    paper_repository.get_or_create_account("acc-returns-test", initial_capital=1_000_000.0)

    # Empty history fallback
    empty_slice = generate_paper_returns_slice(account_id="acc-returns-test")
    assert empty_slice.phase == "PAPER"
    assert empty_slice.source_kind == "paper"
    assert empty_slice.start_equity == 1_000_000.0
    assert empty_slice.end_equity == 1_000_000.0
    assert empty_slice.total_return == 0.0
    assert len(empty_slice.daily_points) == 0

    # Record 3 days
    record_paper_day(
        account_id="acc-returns-test",
        record_date=date(2026, 3, 2),
        realized_pnl=10000.0,
        unrealized_pnl=5000.0,
        transaction_costs=500.0,
    )
    record_paper_day(
        account_id="acc-returns-test",
        record_date=date(2026, 3, 3),
        realized_pnl=-3000.0,
        unrealized_pnl=8000.0,
        transaction_costs=200.0,
    )
    record_paper_day(
        account_id="acc-returns-test",
        record_date=date(2026, 3, 4),
        realized_pnl=8000.0,
        unrealized_pnl=12000.0,
        transaction_costs=400.0,
    )

    ret_slice = generate_paper_returns_slice(account_id="acc-returns-test")
    assert ret_slice.phase == "PAPER"
    assert ret_slice.source_kind == "paper"
    assert ret_slice.start_date == "2026-03-02"
    assert ret_slice.end_date == "2026-03-04"
    assert len(ret_slice.daily_points) == 3
    assert ret_slice.total_return > 0


def test_paper_calendar_and_returns_api_endpoints() -> None:
    """Proof: REST endpoints /api/v1/paper/calendar and /returns work end-to-end."""
    reset_paper_trackers()
    paper_repository.clear()
    paper_repository.get_or_create_account("acc-api-cal", initial_capital=600_000.0)

    record_paper_day(
        account_id="acc-api-cal",
        record_date=date(2026, 3, 2),
        realized_pnl=4000.0,
        unrealized_pnl=3000.0,
        transaction_costs=250.0,
    )

    # 1. GET /api/v1/paper/calendar
    cal_resp = client.get("/api/v1/paper/calendar?account_id=acc-api-cal")
    assert cal_resp.status_code == 200
    cal_data = cal_resp.json()
    assert cal_data["source_kind"] == "paper"
    assert cal_data["account_id"] == "acc-api-cal"
    assert len(cal_data["daily_records"]) == 1
    assert cal_data["current_equity"] > 600_000.0

    # 2. GET /api/v1/paper/returns
    ret_resp = client.get("/api/v1/paper/returns?account_id=acc-api-cal")
    assert ret_resp.status_code == 200
    ret_data = ret_resp.json()
    assert ret_data["phase"] == "PAPER"
    assert ret_data["source_kind"] == "paper"
    assert len(ret_data["daily_points"]) == 1
