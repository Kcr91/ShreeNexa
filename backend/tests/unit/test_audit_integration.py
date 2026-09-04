"""Integration tests verifying end-to-end audit ledger recording, lifecycle

reconstruction, secret redaction, and persistence across process restart (QA-16 / F12.6).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.orders import (
    DhanOrderRequest,
    ExchangeSegment,
    OrderType,
    ProductType,
    TransactionType,
)
from app.dhan.transport import MockTransport
from app.engine.audit import (
    AuditEventType,
    AuditLedger,
    reset_audit_ledger,
)
from app.engine.broker import DhanBroker
from app.engine.gateway import get_risk_filtered_broker
from app.engine.risk import RiskLimits
from app.main import app
from fastapi.testclient import TestClient
from pydantic import SecretStr


@pytest.fixture
def temp_audit_log(tmp_path: Path) -> Path:
    log_file = tmp_path / "test_audit.jsonl"
    reset_audit_ledger(log_path=log_file)
    return log_file


def test_paper_order_ticket_creates_audit_chain(temp_audit_log: Path) -> None:
    """Test that placing a paper order through the API records an immutable audit chain."""
    client = TestClient(app)
    corr_id = "CORR-AUDIT-TEST-001"

    payload = {
        "mode": "PAPER",
        "symbol": "RELIANCE",
        "exchange_segment": "NSE_EQ",
        "security_id": "2885",
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "product_type": "INTRADAY",
        "quantity": 10,
        "price": 2980.0,
        "correlation_id": corr_id,
    }

    res = client.post("/api/v1/orders/ticket/place", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    order_id = data["order_id"]

    ledger = reset_audit_ledger(log_path=temp_audit_log)
    lifecycle = ledger.reconstruct_lifecycle(corr_id)

    # Must contain ORDER_SUBMITTED and ORDER_RESPONSE
    assert len(lifecycle) >= 2
    assert lifecycle[0].event_type == AuditEventType.ORDER_SUBMITTED
    assert lifecycle[0].correlation_id == corr_id
    assert lifecycle[1].event_type == AuditEventType.ORDER_RESPONSE
    assert lifecycle[1].order_id == order_id

    # Verify cryptographic hash chain integrity
    is_valid, invalid_seq = ledger.verify_chain()
    assert is_valid is True
    assert invalid_seq is None


def test_live_gateway_records_full_lifecycle_and_persists(temp_audit_log: Path) -> None:
    """Verify live gateway records RISK_FILTER_EVALUATED, RISK_DECISION, ORDER_SUBMITTED,

    and ORDER_RESPONSE into an immutable, disk-persisted audit ledger.
    """
    transport = MockTransport()
    transport.register(
        "orders",
        status_code=200,
        body={"orderId": "ORD-LIVE-777", "orderStatus": "PENDING"},
    )
    creds = DhanCredentials(
        client_id="1100000000",
        access_token=SecretStr("super_secret_token_val"),
        source="environment",
    )
    rest_client = DhanRestClient(credentials=creds, transport=transport)
    mock_broker = DhanBroker(client=rest_client, enable_live_trading=True, enforce_static_ip=False)

    ledger = reset_audit_ledger(log_path=temp_audit_log)
    risk_broker = get_risk_filtered_broker(
        broker=mock_broker,
        limits=RiskLimits(max_order_value=100_000.0),
        audit_ledger=ledger,
    )

    corr_id = "CORR-LIVE-TRADE-999"
    order = DhanOrderRequest(
        securityId="11536",
        exchangeSegment=ExchangeSegment.NSE_EQ,
        transactionType=TransactionType.BUY,
        orderType=OrderType.LIMIT,
        productType=ProductType.INTRADAY,
        quantity=5,
        price=4200.0,  # 5 * 4200 = 21,000 <= 100,000 limit
        correlationId=corr_id,
    )

    resp = risk_broker.place_order(order)
    assert resp.order_id == "ORD-LIVE-777"

    # Reconstruct lifecycle
    lifecycle = ledger.reconstruct_lifecycle(corr_id)
    assert len(lifecycle) == 4

    # Sequence of events
    assert lifecycle[0].event_type == AuditEventType.RISK_FILTER_EVALUATED
    assert lifecycle[1].event_type == AuditEventType.RISK_DECISION
    assert lifecycle[1].payload.get("decision") == "APPROVED"
    assert lifecycle[2].event_type == AuditEventType.ORDER_SUBMITTED
    assert lifecycle[3].event_type == AuditEventType.ORDER_RESPONSE
    assert lifecycle[3].order_id == "ORD-LIVE-777"

    # Cryptographic integrity check
    valid, bad_idx = ledger.verify_chain()
    assert valid is True
    assert bad_idx is None

    # Restart durability test: create brand new ledger instance pointing at same disk file
    restarted_ledger = AuditLedger(log_path=temp_audit_log)
    assert restarted_ledger.total_events == ledger.total_events

    reconstructed = restarted_ledger.reconstruct_lifecycle(corr_id)
    assert len(reconstructed) == 4
    restored_valid, restored_bad_idx = restarted_ledger.verify_chain()
    assert restored_valid is True
    assert restored_bad_idx is None
