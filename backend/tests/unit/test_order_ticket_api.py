"""Unit tests for Order Ticket API.

Tests charges estimation, validation, mode gating, and status uncertainty.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from app.api.orders import _uncertain_orders
from app.engine.contracts import OrderSide
from app.engine.costs import ProductType as CostProductType
from app.engine.costs import cost_calculator
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_estimate_order_charges_equity_intraday(client: TestClient) -> None:
    payload = {
        "symbol": "INFY",
        "exchange_segment": "NSE_EQ",
        "transaction_type": "BUY",
        "product_type": "INTRADAY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": 1500.0,
        "broker_response_override": {"totalMargin": 30000.0},
    }
    resp = client.post("/api/v1/orders/ticket/estimate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # turnover = 150,000
    assert data["turnover"] == 150000.0
    # brokerage = min(20, 150000 * 0.0003) = 20.0
    assert data["brokerage"] == 20.0
    # STT on buy intraday = 0
    assert data["stt_ctt"] == 0.0
    assert data["exchange_turnover_charges"] > 0
    assert data["stamp_duty"] > 0
    assert data["gst"] > 0
    assert data["total_charges"] > 0
    # Margin evaluation delegated to F8.6 adapter with override
    assert data["is_margin_available"] is True
    assert data["required_margin"] == 30000.0


def test_estimate_order_charges_explicit_unavailable_margin(client: TestClient) -> None:
    """When broker/security_id is not provided, unavailable margin is explicit None, never 0.0."""
    payload = {
        "symbol": "INFY",
        "exchange_segment": "NSE_EQ",
        "transaction_type": "BUY",
        "product_type": "INTRADAY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": 1500.0,
    }
    resp = client.post("/api/v1/orders/ticket/estimate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_margin_available"] is False
    assert data["required_margin"] is None
    assert "Security ID required" in (data["margin_unavailable_reason"] or "")


def test_estimate_order_charges_equity_delivery(client: TestClient) -> None:
    payload = {
        "symbol": "TCS",
        "exchange_segment": "NSE_EQ",
        "transaction_type": "BUY",
        "product_type": "CNC",
        "order_type": "LIMIT",
        "quantity": 10,
        "price": 4000.0,
    }
    resp = client.post("/api/v1/orders/ticket/estimate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["turnover"] == 40000.0
    # Dhan ₹0 brokerage on delivery
    assert data["brokerage"] == 0.0
    # Delivery STT 0.1% = 40.0
    assert data["stt_ctt"] == 40.0


def test_estimate_order_charges_derivatives_flat_brokerage(client: TestClient) -> None:
    payload = {
        "symbol": "NIFTY",
        "exchange_segment": "NSE_FNO",
        "transaction_type": "BUY",
        "product_type": "MARGIN",
        "order_type": "LIMIT",
        "quantity": 50,
        "price": 120.0,
    }
    resp = client.post("/api/v1/orders/ticket/estimate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Flat ₹20 brokerage for F&O
    assert data["brokerage"] == 20.0


def test_estimate_order_charges_cost_model_parity(client: TestClient) -> None:
    """CRITICAL PARITY TEST (QA-21): Verify ticket estimate matches F3.3 cost_calculator exactly."""
    test_cases = [
        # (symbol, segment, side, txn_type, product_type, cost_prod, qty, price, inst_type)
        (
            "INFY",
            "NSE_EQ",
            OrderSide.BUY,
            "BUY",
            "INTRADAY",
            CostProductType.INTRADAY,
            100,
            1500.0,
            None,
        ),
        (
            "INFY",
            "NSE_EQ",
            OrderSide.SELL,
            "SELL",
            "INTRADAY",
            CostProductType.INTRADAY,
            100,
            1500.0,
            None,
        ),
        (
            "TCS",
            "NSE_EQ",
            OrderSide.BUY,
            "BUY",
            "CNC",
            CostProductType.DELIVERY,
            25,
            3800.0,
            None,
        ),
        (
            "TCS",
            "NSE_EQ",
            OrderSide.SELL,
            "SELL",
            "CNC",
            CostProductType.DELIVERY,
            25,
            3800.0,
            None,
        ),
        (
            "NIFTY-FUT",
            "NSE_FNO",
            OrderSide.BUY,
            "BUY",
            "MARGIN",
            CostProductType.FUTURES,
            50,
            24500.0,
            "FUTIDX",
        ),
        (
            "NIFTY-24500-CE",
            "NSE_FNO",
            OrderSide.BUY,
            "BUY",
            "MARGIN",
            CostProductType.OPTIONS,
            50,
            180.0,
            "OPTIDX",
        ),
        (
            "NIFTY-24500-CE",
            "NSE_FNO",
            OrderSide.SELL,
            "SELL",
            "MARGIN",
            CostProductType.OPTIONS,
            50,
            180.0,
            "OPTIDX",
        ),
    ]

    trade_d = date(2025, 2, 10)
    trade_ts = datetime.combine(trade_d, datetime.min.time(), tzinfo=UTC)

    for (
        sym,
        seg,
        side,
        txn_type,
        prod_type,
        cost_prod,
        qty,
        px,
        inst_type,
    ) in test_cases:
        expected = cost_calculator.calculate_cost(
            product_type=cost_prod,
            side=side,
            quantity=qty,
            price=px,
            timestamp=trade_ts,
        )

        req_body = {
            "symbol": sym,
            "exchange_segment": seg,
            "transaction_type": txn_type,
            "product_type": prod_type,
            "order_type": "LIMIT",
            "quantity": qty,
            "price": px,
            "trade_date": trade_d.isoformat(),
        }
        if inst_type:
            req_body["instrument_type"] = inst_type

        resp = client.post("/api/v1/orders/ticket/estimate", json=req_body)
        assert resp.status_code == 200, f"Failed for {sym} {txn_type}: {resp.text}"
        data = resp.json()

        # Assert exact line-item parity between endpoint and cost engine
        assert data["turnover"] == round(qty * px, 2)
        assert data["brokerage"] == round(expected.brokerage, 2)
        assert data["stt_ctt"] == round(expected.stt_ctt, 2)
        assert data["exchange_turnover_charges"] == round(expected.exchange_txn_charge, 2)
        assert data["sebi_charges"] == round(expected.sebi_fee, 2)
        assert data["stamp_duty"] == round(expected.stamp_duty, 2)
        assert data["gst"] == round(expected.gst, 2)
        assert data["total_charges"] == round(expected.total_cost, 2)
        assert data["cost_schedule_id"] == expected.schedule_id


def test_ticket_place_paper_order_success(client: TestClient) -> None:
    payload = {
        "mode": "PAPER",
        "symbol": "RELIANCE",
        "security_id": "2885",
        "exchange_segment": "NSE_EQ",
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "product_type": "INTRADAY",
        "quantity": 10,
        "price": 2900.0,
    }
    resp = client.post("/api/v1/orders/ticket/place", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["mode"] == "PAPER"
    assert data["order_id"].startswith("ORD-PAPER-")
    assert data["order_status"] == "PENDING"

    # QA-15 proof: Assert returned order ID is retrievable via GET /api/v1/paper/orders
    paper_orders_resp = client.get("/api/v1/paper/orders")
    assert paper_orders_resp.status_code == 200
    orders = paper_orders_resp.json()
    matching = [o for o in orders if o["order_id"] == data["order_id"]]
    assert len(matching) == 1
    assert matching[0]["symbol"] == "RELIANCE"
    assert matching[0]["quantity"] == 10


def test_ticket_place_live_order_blocked_without_confirmation(client: TestClient) -> None:
    payload = {
        "mode": "LIVE",
        "confirmation_acknowledged": False,  # Missing confirmation
        "symbol": "RELIANCE",
        "security_id": "2885",
        "exchange_segment": "NSE_EQ",
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "product_type": "INTRADAY",
        "quantity": 10,
        "price": 2900.0,
    }
    resp = client.post("/api/v1/orders/ticket/place", json=payload)
    assert resp.status_code == 400
    assert "confirmation_acknowledged" in resp.json()["detail"]


def test_ticket_place_live_order_blocked_by_live_gate(client: TestClient) -> None:
    payload = {
        "mode": "LIVE",
        "confirmation_acknowledged": True,
        "symbol": "RELIANCE",
        "security_id": "2885",
        "exchange_segment": "NSE_EQ",
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "product_type": "INTRADAY",
        "quantity": 10,
        "price": 2900.0,
    }
    resp = client.post("/api/v1/orders/ticket/place", json=payload)
    # Live trading is disabled by default invariant -> returns 403 Forbidden
    assert resp.status_code == 403
    assert "Live trading is disabled" in resp.json()["detail"]


def test_ticket_place_live_order_timeout_arms_uncertainty(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.dhan.exceptions import DhanTimeoutError
    from app.engine.risk import RiskFilteredBroker

    def mock_place_order(*args: object, **kwargs: object) -> None:
        raise DhanTimeoutError("Mock timeout contacting Dhan broker")

    monkeypatch.setattr(RiskFilteredBroker, "place_order", mock_place_order)

    corr_id = "CORR-TIMEOUT-TEST-001"
    payload = {
        "mode": "LIVE",
        "confirmation_acknowledged": True,
        "correlation_id": corr_id,
        "symbol": "RELIANCE",
        "security_id": "2885",
        "exchange_segment": "NSE_EQ",
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "product_type": "INTRADAY",
        "quantity": 10,
        "price": 2900.0,
    }

    try:
        # First attempt: raises 504 and arms _uncertain_orders
        resp = client.post("/api/v1/orders/ticket/place", json=payload)
        assert resp.status_code == 504
        assert "PENDING_BROKER_CONFIRMATION" in resp.json()["detail"]

        # Second attempt with same correlation_id: blocked with 409 Conflict
        resp2 = client.post("/api/v1/orders/ticket/place", json=payload)
        assert resp2.status_code == 409
        assert "Blind retry is blocked" in resp2.json()["detail"]
    finally:
        _uncertain_orders.pop(corr_id, None)


def test_ticket_blind_retry_blocked_on_uncertain_status(client: TestClient) -> None:
    corr_id = "CORR-UNCERTAIN-TEST"
    _uncertain_orders[corr_id] = "ORD-UNCERTAIN-123"

    payload = {
        "mode": "PAPER",
        "correlation_id": corr_id,
        "symbol": "RELIANCE",
        "security_id": "2885",
        "exchange_segment": "NSE_EQ",
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "product_type": "INTRADAY",
        "quantity": 10,
        "price": 2900.0,
    }
    try:
        resp = client.post("/api/v1/orders/ticket/place", json=payload)
        assert resp.status_code == 409
        assert "PENDING_BROKER_CONFIRMATION" in resp.json()["detail"]
        assert "Blind retry is blocked" in resp.json()["detail"]
    finally:
        _uncertain_orders.pop(corr_id, None)


def test_ticket_order_status_reporting(client: TestClient) -> None:
    resp = client.get("/api/v1/orders/ticket/status/ORD-NORMAL-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_id"] == "ORD-NORMAL-001"
    assert data["is_uncertain"] is False
    assert data["retry_allowed"] is True

    # When marked uncertain
    _uncertain_orders["CORR-TEST"] = "ORD-UNCERTAIN-999"
    try:
        resp_unc = client.get("/api/v1/orders/ticket/status/ORD-UNCERTAIN-999")
        assert resp_unc.status_code == 200
        data_unc = resp_unc.json()
        assert data_unc["is_uncertain"] is True
        assert data_unc["retry_allowed"] is False
        assert data_unc["status"] == "PENDING_BROKER_CONFIRMATION"
    finally:
        _uncertain_orders.pop("CORR-TEST", None)
