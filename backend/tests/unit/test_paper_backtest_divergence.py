"""Unit tests for same-session paper-vs-backtest divergence report (F9.5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.engine.contracts import FillEvent, OrderSide
from app.main import app
from app.paper.divergence import (
    DiscrepancyType,
    DivergenceSeverity,
    DivergenceTolerances,
    generate_divergence_report,
)
from app.paper.models import PaperFill, PaperOrderSide
from app.paper.repository import paper_repository
from fastapi.testclient import TestClient

client = TestClient(app)


def test_identical_inputs_perfect_match() -> None:
    """Proof: Identical inputs reconcile cleanly with verdict PERFECT_MATCH."""
    t0 = datetime(2026, 3, 1, 9, 30, 0, tzinfo=UTC)

    p_fills = [
        PaperFill(
            fill_id="f-1",
            order_id="ord-1",
            account_id="acc-1",
            symbol="TCS",
            security_id="11536",
            side=PaperOrderSide.BUY,
            quantity=100,
            price=3500.0,
            slippage=0.0,
            transaction_cost=40.0,
            timestamp=t0,
        ),
        PaperFill(
            fill_id="f-2",
            order_id="ord-2",
            account_id="acc-1",
            symbol="TCS",
            security_id="11536",
            side=PaperOrderSide.SELL,
            quantity=100,
            price=3550.0,
            slippage=0.0,
            transaction_cost=40.0,
            timestamp=t0 + timedelta(minutes=30),
        ),
    ]

    bt_fills = [
        FillEvent(
            order_id="ord-1",
            security_id="11536",
            exchange_segment="NSE_EQ",
            side=OrderSide.BUY,
            quantity=100,
            price=3500.0,
            timestamp=t0,
            brokerage=0.0,
            taxes=40.0,
            slippage=0.0,
        ),
        FillEvent(
            order_id="ord-2",
            security_id="11536",
            exchange_segment="NSE_EQ",
            side=OrderSide.SELL,
            quantity=100,
            price=3550.0,
            timestamp=t0 + timedelta(minutes=30),
            brokerage=0.0,
            taxes=40.0,
            slippage=0.0,
        ),
    ]

    signals = [
        {"signal_id": "sig-1", "symbol": "TCS", "side": "BUY", "timestamp": t0},
        {
            "signal_id": "sig-2",
            "symbol": "TCS",
            "side": "SELL",
            "timestamp": t0 + timedelta(minutes=30),
        },
    ]

    report = generate_divergence_report(
        session_id="sess-match",
        strategy_name="MomentumAlpha",
        paper_fills=p_fills,
        backtest_fills=bt_fills,
        paper_signals=signals,
        backtest_signals=signals,
    )

    assert report.verdict == DivergenceSeverity.PERFECT_MATCH
    assert report.is_deployable is True
    assert len(report.discrepancies) == 0
    assert report.executions_summary["matched"] == 2
    assert report.signals_summary["matched"] == 2
    assert report.pnl_summary.pnl_delta == 0.0


def test_acceptable_drift_within_tolerances() -> None:
    """Proof: Minor execution drift within declared tolerances results in ACCEPTABLE_DRIFT."""
    t0 = datetime(2026, 3, 1, 9, 30, 0, tzinfo=UTC)

    # Paper fill has 0.05% slippage (3501.75 vs 3500.00) and 0.8s latency
    p_fills = [
        PaperFill(
            fill_id="f-1",
            order_id="ord-1",
            account_id="acc-1",
            symbol="TCS",
            security_id="11536",
            side=PaperOrderSide.BUY,
            quantity=100,
            price=3501.75,
            slippage=1.75,
            transaction_cost=40.0,
            timestamp=t0 + timedelta(milliseconds=800),
        )
    ]

    bt_fills = [
        FillEvent(
            order_id="ord-1",
            security_id="11536",
            exchange_segment="NSE_EQ",
            side=OrderSide.BUY,
            quantity=100,
            price=3500.0,
            timestamp=t0,
            brokerage=0.0,
            taxes=40.0,
            slippage=0.0,
        )
    ]

    report = generate_divergence_report(
        session_id="sess-drift",
        strategy_name="MomentumAlpha",
        paper_fills=p_fills,
        backtest_fills=bt_fills,
        tolerances=DivergenceTolerances(max_price_drift_pct=0.1, max_latency_seconds=2.0),
    )

    assert report.verdict == DivergenceSeverity.ACCEPTABLE_DRIFT
    assert report.is_deployable is True
    assert len(report.discrepancies) == 0


def test_injected_slippage_divergence_localized_and_explained() -> None:
    """Proof: Injected slippage beyond tolerance is localized, explained, and flagged."""
    t0 = datetime(2026, 3, 1, 9, 30, 0, tzinfo=UTC)

    # Injected massive slippage: 3550 vs 3500 (+1.43% drift)
    p_fills = [
        PaperFill(
            fill_id="f-slip",
            order_id="ord-slip-101",
            account_id="acc-1",
            symbol="TCS",
            security_id="11536",
            side=PaperOrderSide.BUY,
            quantity=100,
            price=3550.0,
            slippage=50.0,
            transaction_cost=40.0,
            timestamp=t0,
        )
    ]

    bt_fills = [
        FillEvent(
            order_id="ord-slip-101",
            security_id="11536",
            exchange_segment="NSE_EQ",
            side=OrderSide.BUY,
            quantity=100,
            price=3500.0,
            timestamp=t0,
            brokerage=0.0,
            taxes=40.0,
            slippage=0.0,
        )
    ]

    report = generate_divergence_report(
        session_id="sess-slip",
        strategy_name="MomentumAlpha",
        paper_fills=p_fills,
        backtest_fills=bt_fills,
        tolerances=DivergenceTolerances(max_price_drift_pct=0.1),
    )

    assert report.verdict == DivergenceSeverity.DIVERGENCE_DETECTED
    assert report.is_deployable is False

    # Verify localized discrepancy
    slip_items = [
        d
        for d in report.discrepancies
        if d.discrepancy_type == DiscrepancyType.SLIPPAGE_DISCREPANCY
    ]
    assert len(slip_items) == 1
    item = slip_items[0]
    assert item.entity_id == "ord-slip-101"
    assert item.symbol == "TCS"
    assert item.paper_value == 3550.0
    assert item.backtest_value == 3500.0
    assert item.delta == 50.0
    assert "1.43%" in item.explanation


def test_injected_latency_delay_localized_and_explained() -> None:
    """Proof: Injected execution latency delay is localized and explained."""
    t0 = datetime(2026, 3, 1, 9, 30, 0, tzinfo=UTC)

    # Injected 6.0 seconds latency (exceeding 2.0s limit)
    p_fills = [
        PaperFill(
            fill_id="f-lat",
            order_id="ord-lat-202",
            account_id="acc-1",
            symbol="INFY",
            security_id="1594",
            side=PaperOrderSide.BUY,
            quantity=50,
            price=1500.0,
            slippage=0.0,
            transaction_cost=20.0,
            timestamp=t0 + timedelta(seconds=6.0),
        )
    ]

    bt_fills = [
        FillEvent(
            order_id="ord-lat-202",
            security_id="1594",
            exchange_segment="NSE_EQ",
            side=OrderSide.BUY,
            quantity=50,
            price=1500.0,
            timestamp=t0,
            brokerage=0.0,
            taxes=20.0,
            slippage=0.0,
        )
    ]

    report = generate_divergence_report(
        session_id="sess-lat",
        strategy_name="LatencyTest",
        paper_fills=p_fills,
        backtest_fills=bt_fills,
        tolerances=DivergenceTolerances(max_latency_seconds=2.0),
    )

    assert report.verdict == DivergenceSeverity.DIVERGENCE_DETECTED
    assert report.is_deployable is False

    lat_items = [
        d for d in report.discrepancies if d.discrepancy_type == DiscrepancyType.LATENCY_DELAY
    ]
    assert len(lat_items) == 1
    assert lat_items[0].entity_id == "ord-lat-202"
    assert "6.00s" in lat_items[0].explanation


def test_injected_dropped_fill_critical_mismatch() -> None:
    """Proof: Injected dropped fill in paper trading triggers CRITICAL_MISMATCH."""
    t0 = datetime(2026, 3, 1, 9, 30, 0, tzinfo=UTC)

    # Backtest has 2 fills, but paper only executed 1 (second was dropped)
    p_fills = [
        PaperFill(
            fill_id="f-1",
            order_id="ord-1",
            account_id="acc-1",
            symbol="RELIANCE",
            security_id="2885",
            side=PaperOrderSide.BUY,
            quantity=30,
            price=2900.0,
            slippage=0.0,
            transaction_cost=30.0,
            timestamp=t0,
        )
    ]

    bt_fills = [
        FillEvent(
            order_id="ord-1",
            security_id="2885",
            exchange_segment="NSE_EQ",
            side=OrderSide.BUY,
            quantity=30,
            price=2900.0,
            timestamp=t0,
            brokerage=0.0,
            taxes=30.0,
            slippage=0.0,
        ),
        FillEvent(
            order_id="ord-2-dropped",
            security_id="2885",
            exchange_segment="NSE_EQ",
            side=OrderSide.SELL,
            quantity=30,
            price=2950.0,
            timestamp=t0 + timedelta(minutes=15),
            brokerage=0.0,
            taxes=30.0,
            slippage=0.0,
        ),
    ]

    report = generate_divergence_report(
        session_id="sess-drop",
        strategy_name="DropTest",
        paper_fills=p_fills,
        backtest_fills=bt_fills,
    )

    assert report.verdict == DivergenceSeverity.CRITICAL_MISMATCH
    assert report.is_deployable is False
    assert report.executions_summary["dropped"] == 1

    dropped = [
        d for d in report.discrepancies if d.discrepancy_type == DiscrepancyType.DROPPED_FILL
    ]
    assert len(dropped) == 1
    assert dropped[0].entity_id == "ord-2-dropped"
    assert "dropped in paper trading" in dropped[0].explanation


def test_injected_signal_discrepancy_localized() -> None:
    """Proof: Injected missed signal is localized and attributed."""
    t0 = datetime(2026, 3, 1, 9, 30, 0, tzinfo=UTC)

    p_signals = [
        {"signal_id": "sig-1", "symbol": "TCS", "side": "BUY", "timestamp": t0},
    ]
    bt_signals = [
        {"signal_id": "sig-1", "symbol": "TCS", "side": "BUY", "timestamp": t0},
        {
            "signal_id": "sig-2-missed",
            "symbol": "INFY",
            "side": "BUY",
            "timestamp": t0 + timedelta(minutes=5),
        },
    ]

    report = generate_divergence_report(
        session_id="sess-sig",
        strategy_name="SignalTest",
        paper_fills=[],
        backtest_fills=[],
        paper_signals=p_signals,
        backtest_signals=bt_signals,
    )

    assert report.verdict == DivergenceSeverity.CRITICAL_MISMATCH
    assert report.signals_summary["missed"] == 1

    missed = [
        d for d in report.discrepancies if d.discrepancy_type == DiscrepancyType.MISSED_SIGNAL
    ]
    assert len(missed) == 1
    assert missed[0].entity_id == "sig-2-missed"
    assert missed[0].symbol == "INFY"


def test_divergence_report_api_endpoint() -> None:
    """Verify REST API /api/v1/paper/divergence-report endpoint."""
    paper_repository.clear()
    paper_repository.get_or_create_account("api-div-acc", initial_capital=1000000.0)

    t0 = datetime.now(UTC)
    p_fill = PaperFill(
        fill_id="f-api",
        order_id="ord-api-1",
        account_id="api-div-acc",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        quantity=50,
        price=3500.0,
        slippage=0.0,
        transaction_cost=25.0,
        timestamp=t0,
    )
    paper_repository.save_fill(p_fill)

    req_payload = {
        "account_id": "api-div-acc",
        "strategy_name": "APITestStrategy",
        "backtest_fills": [
            {
                "order_id": "ord-api-1",
                "security_id": "11536",
                "exchange_segment": "NSE_EQ",
                "side": "BUY",
                "quantity": 50,
                "price": 3500.0,
                "timestamp": t0.isoformat(),
                "brokerage": 0.0,
                "taxes": 25.0,
                "slippage": 0.0,
            }
        ],
        "paper_signals": [],
        "backtest_signals": [],
    }

    response = client.post("/api/v1/paper/divergence-report", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["strategy_name"] == "APITestStrategy"
    assert data["verdict"] in ("PERFECT_MATCH", "ACCEPTABLE_DRIFT")
    assert data["is_deployable"] is True
    assert data["executions_summary"]["matched"] == 1
