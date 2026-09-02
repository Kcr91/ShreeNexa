"""Unit tests for Paper Trading accounting reconciliation, live MTM, and cost parity."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app
from app.paper.broker import PaperBroker
from app.paper.models import (
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
)
from app.paper.reconciliation import reconcile_portfolio
from app.paper.repository import PaperRepository
from fastapi.testclient import TestClient

FIXTURES_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "paper_accounting_fixture.json"
client = TestClient(app)


def test_independent_accounting_fixture_reconciliation() -> None:
    """Proof: independent accounting fixture reconciles UI/API/order/fill/position totals."""
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        fixture = json.load(f)

    repo = PaperRepository()
    account_id = fixture["account_id"]
    initial_capital = fixture["initial_capital"]
    repo.get_or_create_account(account_id, initial_capital=initial_capital)
    broker = PaperBroker(repository=repo)

    # 1. Submit orders from fixture
    for o_data in fixture["orders"]:
        order = PaperOrder(
            order_id=o_data["order_id"],
            account_id=account_id,
            symbol=o_data["symbol"],
            security_id=o_data["security_id"],
            side=PaperOrderSide(o_data["side"]),
            order_type=PaperOrderType(o_data["order_type"]),
            quantity=o_data["quantity"],
            price=o_data["price"],
        )
        broker.submit_orders([order])

        if o_data["expected_status"] == "REJECTED":
            stored = repo.get_order(o_data["order_id"])
            assert stored is not None
            assert stored.status == PaperOrderStatus.REJECTED
            assert o_data["expected_reject_reason"] in (stored.reject_reason or "")
        else:
            # Match execution at order limit price
            broker.process_price_update(
                security_id=o_data["security_id"],
                current_price=o_data["price"],
                low_price=o_data["price"] if o_data["side"] == "BUY" else None,
                high_price=o_data["price"] if o_data["side"] == "SELL" else None,
            )
            stored = repo.get_order(o_data["order_id"])
            assert stored is not None
            assert stored.status == PaperOrderStatus.FILLED

    # 2. Update to current market prices for live MTM
    for sec_id, mkt_price in fixture["market_prices"].items():
        broker.process_price_update(security_id=sec_id, current_price=mkt_price)

    # 3. Verify positions match expected fixture
    for sec_id, exp_pos in fixture["expected_positions"].items():
        pos = repo.get_position(account_id, sec_id)
        assert pos is not None
        assert pos.symbol == exp_pos["symbol"]
        assert pos.quantity == exp_pos["quantity"]
        assert pos.avg_entry_price == exp_pos["avg_entry_price"]
        assert pos.current_price == exp_pos["current_price"]
        assert pos.unrealized_pnl == exp_pos["unrealized_pnl"]

    # 4. Run portfolio reconciliation
    summary = reconcile_portfolio(account_id, repository=repo)

    inv = fixture["invariants"]
    assert summary.total_orders == inv["total_orders"]
    assert summary.working_orders_count == inv["working_orders_count"]
    assert summary.filled_orders_count == inv["filled_orders_count"]
    assert summary.rejected_orders_count == inv["rejected_orders_count"]
    assert summary.total_fills == inv["total_fills"]
    assert summary.open_positions_count == inv["open_positions_count"]
    assert summary.is_reconciled is True
    assert summary.cash_discrepancy <= inv["max_cash_discrepancy"]

    # Invariant: Net equity = Cash + Blocked Margin + Unrealized P&L
    expected_equity = round(
        summary.cash_balance + summary.blocked_margin + summary.unrealized_pnl, 2
    )
    assert summary.total_equity == expected_equity

    # Transaction costs must be > 0 and accounted for
    assert summary.total_transaction_costs > 0.0

    # Rejected order details exposed
    assert len(summary.rejected_orders) == 1
    assert summary.rejected_orders[0].symbol == "RELIANCE"
    assert "Insufficient funds" in summary.rejected_orders[0].reject_reason


def test_portfolio_summary_and_reconciliation_api() -> None:
    """Verify GET /api/v1/paper/portfolio/summary and /reconcile endpoints."""
    # Create account
    client.post(
        "/api/v1/paper/accounts",
        json={"account_id": "api-recon-acc", "name": "Recon Test", "initial_capital": 300000.0},
    )

    # Place valid order
    client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": "api-recon-acc",
            "symbol": "TATASTEEL",
            "security_id": "3499",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 50,
        },
    )

    # Place invalid oversized order to trigger rejection
    client.post(
        "/api/v1/paper/orders",
        json={
            "account_id": "api-recon-acc",
            "symbol": "BAJFINANCE",
            "security_id": "317",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1000,
            "price": 7000.0,
        },
    )

    # Query summary endpoint
    resp_sum = client.get("/api/v1/paper/portfolio/summary?account_id=api-recon-acc")
    assert resp_sum.status_code == 200
    data = resp_sum.json()
    assert data["account_id"] == "api-recon-acc"
    assert data["total_orders"] >= 2
    assert data["rejected_orders_count"] >= 1
    assert len(data["rejected_orders"]) >= 1
    assert "Insufficient funds" in data["rejected_orders"][0]["reject_reason"]

    # Query reconcile endpoint
    resp_rec = client.get("/api/v1/paper/reconcile?account_id=api-recon-acc")
    assert resp_rec.status_code == 200
    rec_data = resp_rec.json()
    assert rec_data["is_reconciled"] is True
    assert rec_data["cash_discrepancy"] <= 0.05
