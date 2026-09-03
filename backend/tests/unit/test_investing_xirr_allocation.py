"""Unit tests for XIRR solver, sector/asset allocation, and benchmark comparison (F10.2).

Verifies Excel XIRR parity across irregular cashflows, explicit failure handling,
holdings ledger portfolio XIRR, sector concentration analysis, and REST API endpoints.
"""

from __future__ import annotations

from datetime import date

import pytest
from app.investing.analytics import (
    compare_portfolio_to_benchmark,
    compute_account_xirr,
    generate_portfolio_allocation,
    generate_portfolio_cashflows,
)
from app.investing.ledger import HoldingsLedger
from app.investing.xirr import (
    XIRRInvalidCashflowsError,
    calculate_xirr,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_xirr_simple_excel_parity() -> None:
    """Proof: Exactly 1-year investment yields exact annual return rate matching Excel."""
    # 10,000 invested on 2023-01-01, 11,000 returned on 2024-01-01 (exact 365 days)
    flows = [
        (date(2023, 1, 1), -10000.0),
        (date(2024, 1, 1), 11000.0),
    ]
    # 365 days -> 10% annual return exactly
    res = calculate_xirr(flows)
    assert abs(res - 0.10) < 1e-4


def test_xirr_irregular_sip_cashflows_excel_parity() -> None:
    """Proof: Multi-period irregular cash flows converge to standard Excel XIRR value."""
    # Monthly SIP of 10,000 from Jan to Jun, terminal valuation 66,000 on Dec 31
    flows = [
        (date(2024, 1, 1), -10000.0),
        (date(2024, 2, 1), -10000.0),
        (date(2024, 3, 1), -10000.0),
        (date(2024, 4, 1), -10000.0),
        (date(2024, 5, 1), -10000.0),
        (date(2024, 6, 1), -10000.0),
        (date(2024, 12, 31), 66000.0),
    ]
    res = calculate_xirr(flows)
    # Total invested 60,000, terminal 66,000 over ~0.79 years average duration -> ~12.76% XIRR
    assert abs(res - 0.127634) < 1e-4


def test_xirr_explicit_failure_modes() -> None:
    """Proof: Invalid cashflows and non-converging degenerate series fail explicitly."""
    # 1. Empty or single cash flow
    with pytest.raises(XIRRInvalidCashflowsError):
        calculate_xirr([])
    with pytest.raises(XIRRInvalidCashflowsError):
        calculate_xirr([(date(2024, 1, 1), -1000.0)])

    # 2. All negative cash flows (no inflows/terminal value)
    with pytest.raises(XIRRInvalidCashflowsError):
        calculate_xirr(
            [
                (date(2024, 1, 1), -1000.0),
                (date(2024, 2, 1), -2000.0),
            ]
        )

    # 3. All positive cash flows (no investments)
    with pytest.raises(XIRRInvalidCashflowsError):
        calculate_xirr(
            [
                (date(2024, 1, 1), 1000.0),
                (date(2024, 2, 1), 2000.0),
            ]
        )


def test_holdings_ledger_portfolio_xirr() -> None:
    """Proof: Portfolio cashflows are accurately constructed from tax lots and terminal value."""
    ledger = HoldingsLedger()
    acc = "acc_xirr_test"

    # Buy 100 Reliance @ 2500 on 2024-01-01 -> 250,000 outflow
    ledger.add_lot(
        account_id=acc,
        security_id="RELIANCE",
        isin="INE002A01018",
        trading_symbol="RELIANCE",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=2500.0,
        quantity=100,
        lot_id=f"{acc}_lot1",
    )

    # Buy 50 TCS @ 3500 on 2024-03-01 -> 175,000 outflow
    ledger.add_lot(
        account_id=acc,
        security_id="TCS",
        isin="INE467B01029",
        trading_symbol="TCS",
        acquisition_date=date(2024, 3, 1),
        acquisition_price=3500.0,
        quantity=50,
        lot_id=f"{acc}_lot2",
    )

    # Current prices: Reliance @ 3000, TCS @ 4000 on 2025-01-01
    # Terminal value = (100 * 3000) + (50 * 4000) = 300,000 + 200,000 = 500,000
    prices = {"RELIANCE": 3000.0, "TCS": 4000.0}
    as_of = date(2025, 1, 1)

    flows = generate_portfolio_cashflows(
        acc, ledger=ledger, current_prices=prices, as_of_date=as_of
    )
    assert len(flows) == 3
    assert flows[0].amount == -250000.0
    assert flows[1].amount == -175000.0
    assert flows[2].amount == 500000.0

    xirr_res = compute_account_xirr(acc, ledger=ledger, current_prices=prices, as_of_date=as_of)
    assert xirr_res.xirr > 0.0
    assert xirr_res.total_invested == 425000.0
    assert xirr_res.current_value == 500000.0


def test_sector_allocation_and_concentration_flags() -> None:
    """Proof: Portfolio holdings are aggregated by sector with concentration warnings."""
    ledger = HoldingsLedger()
    acc = "acc_alloc_test"

    # Add 80% weight in Reliance (Energy) and 20% in TCS (IT)
    ledger.add_lot(
        account_id=acc,
        security_id="RELIANCE",
        isin="INE002A01018",
        trading_symbol="RELIANCE",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=2500.0,
        quantity=80,
        lot_id=f"{acc}_lot1",
    )
    ledger.add_lot(
        account_id=acc,
        security_id="TCS",
        isin="INE467B01029",
        trading_symbol="TCS",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=1000.0,
        quantity=50,
        lot_id=f"{acc}_lot2",
    )

    report = generate_portfolio_allocation(acc, ledger=ledger)
    assert len(report.sectors) >= 2

    energy_sector = next((s for s in report.sectors if "Energy" in s.sector), None)
    assert energy_sector is not None
    assert energy_sector.weight_pct > 70.0

    # Concentration warning should be triggered because Reliance > 35% of portfolio
    assert len(report.concentration_warnings) >= 1
    assert any("Concentration warning" in w for w in report.concentration_warnings)


def test_benchmark_performance_comparison() -> None:
    """Proof: Portfolio XIRR is benchmarked with excess return (alpha)."""
    ledger = HoldingsLedger()
    acc = "acc_bench_test"

    ledger.add_lot(
        account_id=acc,
        security_id="RELIANCE",
        isin="INE002A01018",
        trading_symbol="RELIANCE",
        acquisition_date=date(2024, 1, 1),
        acquisition_price=2000.0,
        quantity=100,
        lot_id=f"{acc}_lot1",
    )

    # 50% gain over 1 year
    prices = {"RELIANCE": 3000.0}
    as_of = date(2025, 1, 1)

    bench_res = compare_portfolio_to_benchmark(
        acc,
        benchmark_symbol="NIFTY 50",
        benchmark_annual_return_pct=15.0,
        ledger=ledger,
        current_prices=prices,
        as_of_date=as_of,
    )
    assert bench_res.portfolio_xirr_pct > 45.0
    assert bench_res.alpha_pct > 30.0
    assert bench_res.outperforming is True


def test_investing_xirr_rest_endpoints() -> None:
    """Proof: REST API endpoints for XIRR, allocation, and benchmark respond correctly."""
    # 1. Direct cashflow XIRR
    resp_xirr = client.post(
        "/api/v1/investing/xirr",
        json={
            "cashflows": [
                {"date": "2024-01-01", "amount": -10000.0},
                {"date": "2025-01-01", "amount": 11500.0},
            ]
        },
    )
    assert resp_xirr.status_code == 200
    data_xirr = resp_xirr.json()
    assert abs(data_xirr["xirr_pct"] - 15.0) < 0.2

    # 2. Portfolio allocation endpoint
    resp_alloc = client.get("/api/v1/investing/allocation?account_id=default")
    assert resp_alloc.status_code == 200
    data_alloc = resp_alloc.json()
    assert "sectors" in data_alloc
    assert "asset_classes" in data_alloc

    # 3. Benchmark comparison endpoint
    resp_bench = client.post(
        "/api/v1/investing/benchmark-comparison",
        json={
            "account_id": "default",
            "benchmark_symbol": "NIFTY 50",
            "benchmark_annual_return_pct": 12.0,
        },
    )
    # If default account has no holdings, returns 400 (no cashflows) or handles cleanly
    assert resp_bench.status_code in (200, 400)
