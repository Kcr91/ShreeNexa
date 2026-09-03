"""Unit tests for OrderReconciler deduplication, fill idempotency, and gap reconciliation."""

from __future__ import annotations

from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.order_stream import DhanOrderUpdateData
from app.dhan.transport import MockTransport
from app.engine.order_reconciler import OrderReconciler
from pydantic import SecretStr


def create_sample_update(
    order_no: str = "ORD_RECON_001",
    status: str = "PENDING",
    quantity: int = 100,
    traded_qty: int = 0,
    traded_price: float = 0.0,
    last_updated_time: str = "2026-09-04 10:00:00",
) -> DhanOrderUpdateData:
    return DhanOrderUpdateData(
        OrderNo=order_no,
        Status=status,
        Quantity=quantity,
        TradedQty=traded_qty,
        TradedPrice=traded_price,
        AvgTradedPrice=traded_price,
        LastUpdatedTime=last_updated_time,
    )


def test_order_reconciler_deduplication() -> None:
    reconciler = OrderReconciler()
    update1 = create_sample_update(traded_qty=0, status="PENDING")
    update_dup = create_sample_update(traded_qty=0, status="PENDING")

    is_dup1, fill1 = reconciler.process_update(update1)
    assert is_dup1 is False
    assert fill1 is None

    # Exact same update received again (e.g. from Postback + WebSocket)
    is_dup2, fill2 = reconciler.process_update(update_dup)
    assert is_dup2 is True
    assert fill2 is None


def test_order_reconciler_incremental_fills_idempotency() -> None:
    reconciler = OrderReconciler()

    # Initial order pending
    reconciler.process_update(create_sample_update(traded_qty=0, status="PENDING"))

    # First partial fill: 30 shares
    u1 = create_sample_update(
        traded_qty=30,
        traded_price=100.0,
        status="PART_TRADED",
        last_updated_time="2026-09-04 10:01:00",
    )
    is_dup, fill1 = reconciler.process_update(u1)
    assert is_dup is False
    assert fill1 is not None
    assert fill1.incremental_qty == 30
    assert fill1.cumulative_traded_qty == 30
    assert fill1.fill_price == 100.0

    # Repeated identical packet (no duplicate fill emitted)
    is_dup_repeat, fill_repeat = reconciler.process_update(u1)
    assert is_dup_repeat is True
    assert fill_repeat is None

    # Second partial fill: total 70 shares (incremental 40)
    u2 = create_sample_update(
        traded_qty=70,
        traded_price=101.0,
        status="PART_TRADED",
        last_updated_time="2026-09-04 10:02:00",
    )
    _, fill2 = reconciler.process_update(u2)
    assert fill2 is not None
    assert fill2.incremental_qty == 40
    assert fill2.cumulative_traded_qty == 70

    # Final fill: total 100 shares (incremental 30)
    u3 = create_sample_update(
        traded_qty=100,
        traded_price=100.5,
        status="TRADED",
        last_updated_time="2026-09-04 10:03:00",
    )
    _, fill3 = reconciler.process_update(u3)
    assert fill3 is not None
    assert fill3.incremental_qty == 30
    assert fill3.cumulative_traded_qty == 100

    state = reconciler.get_order_state("ORD_RECON_001")
    assert state is not None
    assert state.status == "TRADED"
    assert state.cumulative_traded_qty == 100


def test_order_reconciler_out_of_order_gap_triggers_broker_reconciliation() -> None:
    mock_transport = MockTransport()
    mock_transport.register(
        "orders/ORD_GAP_001",
        status_code=200,
        body={
            "orderId": "ORD_GAP_001",
            "orderStatus": "TRADED",
            "transactionType": "BUY",
            "exchangeSegment": "NSE_EQ",
            "productType": "CNC",
            "orderType": "LIMIT",
            "securityId": "1333",
            "quantity": 50,
            "tradedQuantity": 50,
            "averageTradedPrice": 250.0,
            "updateTime": "2026-09-04 10:10:00",
        },
    )
    creds = DhanCredentials(
        client_id="1100000000",
        access_token=SecretStr("test_token"),
        source="environment",
    )
    client = DhanRestClient(credentials=creds, transport=mock_transport)
    reconciler = OrderReconciler(client=client)

    # Initial state: 40 shares traded
    reconciler.process_update(
        create_sample_update(
            order_no="ORD_GAP_001",
            traded_qty=40,
            status="PART_TRADED",
            last_updated_time="2026-09-04 10:05:00",
        )
    )

    # Out-of-order corrupted update arrives with traded_qty = 10 (< 40)
    bad_update = create_sample_update(
        order_no="ORD_GAP_001",
        traded_qty=10,
        status="PART_TRADED",
        last_updated_time="2026-09-04 10:04:00",
    )

    is_dup, fill = reconciler.process_update(bad_update)
    assert is_dup is False
    assert fill is None

    # State was converged to broker truth (50/50 traded)
    state = reconciler.get_order_state("ORD_GAP_001")
    assert state is not None
    assert state.status == "TRADED"
    assert state.cumulative_traded_qty == 50
    assert state.avg_traded_price == 250.0
