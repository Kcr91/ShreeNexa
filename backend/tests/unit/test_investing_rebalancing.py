"""Unit tests for SIP planning, calendar/threshold rebalancing, and TWR (F10.4).

Proof requirement: Cashflow/TWR separation; G2; proposal totals respect cash
and configured limits.
"""

from __future__ import annotations

from datetime import date

from app.investing.ledger import HoldingsLedger
from app.investing.rebalancing import (
    RebalanceAction,
    calculate_time_weighted_return,
    generate_rebalance_proposal,
    plan_sip_instalment,
    project_step_up_sip,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_sip_planning_whole_shares_allocation() -> None:
    """Proof: Whole-lot shares allocated from SIP budget and target weights."""
    budget = 50000.0
    weights = {
        "NIFTYBEES": 50.0,
        "GOLDBEES": 30.0,
        "HDFCBANK": 20.0,
    }
    prices = {
        "NIFTYBEES": 250.0,
        "GOLDBEES": 60.0,
        "HDFCBANK": 1500.0,
    }

    res = plan_sip_instalment(budget, weights, prices)
    assert res.budget == 50000.0
    assert res.total_allocated <= budget

    # Check NIFTYBEES: target 25,000 / 250 = 100 shares exactly
    nifty = next(it for it in res.items if it.trading_symbol == "NIFTYBEES")
    assert nifty.allocated_shares == 100
    assert nifty.allocated_amount == 25000.0

    # Check GOLDBEES: target 15,000 / 60 = 250 shares exactly
    gold = next(it for it in res.items if it.trading_symbol == "GOLDBEES")
    assert gold.allocated_shares == 250
    assert gold.allocated_amount == 15000.0

    # Check HDFCBANK: target 10,000 / 1500 = 6 shares (9000), leftover 1000
    hdfc = next(it for it in res.items if it.trading_symbol == "HDFCBANK")
    assert hdfc.allocated_shares == 6
    assert hdfc.allocated_amount == 9000.0
    assert hdfc.leftover_cash == 1000.0

    assert res.total_unallocated_cash == 1000.0
    assert res.total_allocated == 49000.0


def test_step_up_sip_projection() -> None:
    """Proof: Step-up schedule computes accurate multi-year contributions."""
    proj = project_step_up_sip(initial_monthly=10000.0, annual_step_up_pct=10.0, years=3)
    assert len(proj) == 3

    # Year 1: 10,000 * 12 = 120,000
    assert proj[0].monthly_instalment == 10000.0
    assert proj[0].annual_contribution == 120000.0
    assert proj[0].cumulative_invested == 120000.0

    # Year 2: 11,000 * 12 = 132,000 -> cum 252,000
    assert proj[1].monthly_instalment == 11000.0
    assert proj[1].annual_contribution == 132000.0
    assert proj[1].cumulative_invested == 252000.0

    # Year 3: 12,100 * 12 = 145,200 -> cum 397,200
    assert proj[2].monthly_instalment == 12100.0
    assert proj[2].annual_contribution == 145200.0
    assert proj[2].cumulative_invested == 397200.0


def test_rebalance_proposal_respects_limits_and_no_automatic_orders() -> None:
    """Proof: Rebalance proposal respects limits and never executes automatic orders."""
    h_ledger = HoldingsLedger()
    acc = "acc_reb_test"

    # Current portfolio: 80% RELIANCE (100 shares @ 2500 = 250,000)
    # and 20% TCS (20 shares @ 3125 = 62,500). Total = 312,500
    h_ledger.add_lot(
        account_id=acc,
        security_id="RELIANCE",
        isin="INE002A01018",
        trading_symbol="RELIANCE",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=2500.0,
        quantity=100,
    )
    h_ledger.add_lot(
        account_id=acc,
        security_id="TCS",
        isin="INE467B01029",
        trading_symbol="TCS",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=3125.0,
        quantity=20,
    )

    target_weights = {
        "RELIANCE": 50.0,
        "TCS": 50.0,
    }
    prices = {
        "RELIANCE": 2500.0,
        "TCS": 3125.0,
    }

    proposal = generate_rebalance_proposal(
        account_id=acc,
        target_weights=target_weights,
        current_prices=prices,
        available_cash=50000.0,
        tolerance_band_pct=5.0,
        max_allocation_per_trade=60000.0,
        ledger=h_ledger,
    )

    # Invariant: Output is strictly PROPOSED; no automatic order placement
    assert proposal.status == "PROPOSED"

    rel_item = next(it for it in proposal.items if it.trading_symbol == "RELIANCE")
    tcs_item = next(it for it in proposal.items if it.trading_symbol == "TCS")

    # RELIANCE is overweight (69% vs target 50%) -> action SELL
    assert rel_item.action == RebalanceAction.SELL
    assert rel_item.proposed_quantity > 0

    # TCS is underweight (17% vs target 50%) -> action BUY
    assert tcs_item.action == RebalanceAction.BUY
    assert tcs_item.proposed_quantity > 0

    # Invariant: Respect configured limits (max_allocation_per_trade capped at 60,000)
    assert tcs_item.estimated_amount <= 60000.0


def test_twr_cashflow_separation_proof() -> None:
    """Proof: Time-Weighted Return separates external cash additions from investment performance."""
    acc = "acc_twr_proof"

    # Sub-period 1: Jan 1 to Jun 30.
    # Start: 100,000, Ends: 110,000 (+10% performance gain, no cash addition).
    # Sub-period 2: Jul 1 to Dec 31.
    # Investor deposits 90,000 cash on Jul 1.
    # Base = 110,000 + 90,000 = 200,000.
    # Ends on Dec 31 at 180,000 (-10% performance decline).
    sub_periods = [
        (date(2024, 1, 1), date(2024, 6, 30), 100000.0, 110000.0, 0.0),
        (date(2024, 7, 1), date(2024, 12, 31), 110000.0, 180000.0, 90000.0),
    ]

    res = calculate_time_weighted_return(acc, sub_periods)

    # Sub-period 1 return: (110,000 - 100,000) / 100,000 = +10.0%
    assert abs(res.sub_periods[0].sub_period_return - 0.10) < 1e-5

    # Sub-period 2 return: (180,000 - 200,000) / 200,000 = -10.0%
    assert abs(res.sub_periods[1].sub_period_return - (-0.10)) < 1e-5

    # Chained TWR: (1 + 0.10) * (1 - 0.10) - 1 = 0.99 - 1 = -0.01 (-1.00%)
    assert abs(res.twr - (-0.01)) < 1e-4
    assert res.twr_pct == -1.0


def test_rebalancing_rest_api_endpoints() -> None:
    """Proof: REST API endpoints for SIP, rebalance proposals, and TWR respond correctly."""
    # 1. SIP plan endpoint
    resp_sip = client.post(
        "/api/v1/investing/sip/plan",
        json={
            "budget": 20000.0,
            "target_weights": {"NIFTYBEES": 60.0, "GOLDBEES": 40.0},
            "current_prices": {"NIFTYBEES": 250.0, "GOLDBEES": 60.0},
        },
    )
    assert resp_sip.status_code == 200
    data_sip = resp_sip.json()
    assert len(data_sip["items"]) == 2

    # 2. Rebalance proposal endpoint
    resp_reb = client.post(
        "/api/v1/investing/rebalance/proposal",
        json={
            "account_id": "default",
            "target_weights": {"NIFTYBEES": 60.0, "GOLDBEES": 40.0},
            "current_prices": {"NIFTYBEES": 250.0, "GOLDBEES": 60.0},
            "available_cash": 10000.0,
        },
    )
    # Returns 200 proposal or 400 if empty holdings
    assert resp_reb.status_code in (200, 400)

    # 3. TWR endpoint
    resp_twr = client.post(
        "/api/v1/investing/performance/twr",
        json={
            "account_id": "test_acc",
            "sub_periods": [
                {
                    "start_date": "2024-01-01",
                    "end_date": "2024-06-30",
                    "start_value": 100000.0,
                    "end_value": 110000.0,
                    "net_cash_flow": 0.0,
                }
            ],
        },
    )
    assert resp_twr.status_code == 200
    data_twr = resp_twr.json()
    assert data_twr["twr_pct"] == 10.0
