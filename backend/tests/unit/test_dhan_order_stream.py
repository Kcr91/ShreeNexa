"""Unit tests for Live Order Update WebSocket models, auth handshake, and stream handler."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from app.dhan.order_stream import (
    DhanOrderStreamClient,
    DhanOrderStreamHandler,
    DhanOrderUpdateData,
    DhanOrderUpdateEvent,
    DhanPostbackPayload,
    build_order_stream_auth_message,
)
from app.engine.core import create_engine_order_stream
from app.engine.order_reconciler import OrderReconciler
from websockets.asyncio.server import ServerConnection, serve


def test_build_order_stream_auth_message() -> None:
    auth = build_order_stream_auth_message(client_id="1100000000", access_token="JWT_SECRET_TOKEN")
    assert auth["UserType"] == "SELF"
    assert auth["LoginReq"]["MsgCode"] == 42
    assert auth["LoginReq"]["ClientId"] == "1100000000"
    assert auth["LoginReq"]["Token"] == "JWT_SECRET_TOKEN"


def test_parse_order_update_websocket_packet() -> None:
    raw_packet = json.dumps(
        {
            "Type": "order_alert",
            "Data": {
                "Exchange": "NSE",
                "Segment": "E",
                "SecurityId": "14366",
                "ClientId": "1100000000",
                "OrderNo": "1124091136546",
                "ExchOrderNo": "1400000000404591",
                "Product": "CNC",
                "TxnType": "BUY",
                "OrderType": "LIMIT",
                "Quantity": 100,
                "TradedQty": 40,
                "Price": 125.50,
                "TradedPrice": 125.50,
                "AvgTradedPrice": 125.50,
                "Status": "PART_TRADED",
                "CorrelationId": "NX-001",
                "LastUpdatedTime": "2026-09-04 10:15:30",
            },
        }
    )

    event = DhanOrderUpdateEvent.from_raw_json(raw_packet)
    assert event.event_type == "order_alert"
    assert event.data.order_no == "1124091136546"
    assert event.data.quantity == 100
    assert event.data.traded_qty == 40
    assert event.data.status == "PART_TRADED"
    assert event.data.price == 125.50


def test_postback_payload_to_unified_update() -> None:
    postback = DhanPostbackPayload(
        orderId="ORD_PB_123",
        correlationId="NX-PB-01",
        orderStatus="TRADED",
        transactionType="BUY",
        exchangeSegment="NSE_EQ",
        productType="CNC",
        orderType="LIMIT",
        securityId="1333",
        quantity=50,
        tradedQuantity=50,
        price=1450.0,
        averagePrice=1450.0,
        updateTime="2026-09-04 11:20:00",
    )

    update = postback.to_unified_update()
    assert update.order_no == "ORD_PB_123"
    assert update.correlation_id == "NX-PB-01"
    assert update.status == "TRADED"
    assert update.traded_qty == 50
    assert update.avg_traded_price == 1450.0


def test_order_stream_handler_dispatch() -> None:
    handler = DhanOrderStreamHandler()
    received_updates: list[DhanOrderUpdateData] = []
    handler.subscribe(lambda u: received_updates.append(u))

    # WebSocket packet
    raw_packet = json.dumps(
        {
            "Type": "order_alert",
            "Data": {
                "OrderNo": "ORD_HANDLER_01",
                "Status": "PENDING",
                "Quantity": 10,
                "TradedQty": 0,
            },
        }
    )
    handler.handle_raw_frame(raw_packet)
    assert len(received_updates) == 1
    assert received_updates[0].order_no == "ORD_HANDLER_01"

    # Postback packet
    postback = DhanPostbackPayload(
        orderId="ORD_HANDLER_02",
        orderStatus="TRADED",
        quantity=10,
        tradedQuantity=10,
    )
    handler.handle_postback(postback)
    assert len(received_updates) == 2
    assert received_updates[1].order_no == "ORD_HANDLER_02"


def test_order_stream_client_missing_credentials_raises() -> None:
    """Connecting without any resolved credentials raises ValueError."""
    client = DhanOrderStreamClient(
        ws_url="ws://127.0.0.1:12345",
        client_id="",
        access_token="",
    )

    with pytest.raises(ValueError, match="Dhan client_id and access_token are required"):
        asyncio.run(client._connect_and_listen())


@pytest.mark.anyio
async def test_order_stream_client_handshake_and_dispatch() -> None:
    """Mock WebSocket server receives MsgCode 42 handshake and dispatches to reconciler."""
    received_handshakes: list[dict[str, Any]] = []
    server_ready = asyncio.Event()

    sample_frame = json.dumps(
        {
            "Type": "order_alert",
            "Data": {
                "Exchange": "NSE",
                "Segment": "E",
                "SecurityId": "2885",
                "ClientId": "11001100",
                "OrderNo": "ORD_STREAM_999",
                "Status": "TRADED",
                "Quantity": 25,
                "TradedQty": 25,
                "Price": 3200.0,
                "AvgTradedPrice": 3200.0,
                "CorrelationId": "NX-STREAM-01",
            },
        }
    )

    async def ws_handler(websocket: ServerConnection) -> None:
        # First frame should be the MsgCode 42 handshake
        raw_auth = await websocket.recv()
        received_handshakes.append(json.loads(raw_auth))
        # Send confirmation / login response
        await websocket.send(json.dumps({"LoginRsp": {"Status": "SUCCESS"}, "MsgCode": 43}))
        # Send order alert
        await websocket.send(sample_frame)
        server_ready.set()
        # Keep connection open until client closes
        try:
            async for _ in websocket:
                pass
        except Exception:
            pass

    async with serve(ws_handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        reconciler = OrderReconciler()
        client = DhanOrderStreamClient(
            ws_url=f"ws://127.0.0.1:{port}",
            client_id="11001100",
            access_token="TEST_STREAM_SECRET_TOKEN",
            reconciler=reconciler,
            initial_reconnect_delay=0.05,
        )

        _ = client.start()
        # Wait until server sent the frame
        await asyncio.wait_for(server_ready.wait(), timeout=3.0)
        # Give brief time for client to process frame
        await asyncio.sleep(0.1)

        assert client.is_connected is True
        assert client.is_running is True
        assert client.processed_frames >= 1
        assert client.last_received_time is not None

        # Verify handshake payload
        assert len(received_handshakes) == 1
        handshake = received_handshakes[0]
        assert handshake["UserType"] == "SELF"
        login_req = handshake["LoginReq"]
        assert login_req["MsgCode"] == 42
        assert login_req["ClientId"] == "11001100"
        assert login_req["Token"] == "TEST_STREAM_SECRET_TOKEN"

        # Verify reconciler received and tracked the order
        state = reconciler.get_order_state("ORD_STREAM_999")
        assert state is not None
        assert state.order_id == "ORD_STREAM_999"
        assert state.status == "TRADED"
        assert state.cumulative_traded_qty == 25

        await client.stop()
        assert client.is_running is False
        assert client.is_connected is False


@pytest.mark.anyio
async def test_order_stream_client_reconnection_on_disconnect() -> None:
    """Client reconnects with backoff when connection is terminated and resumes streaming."""
    connection_count = 0

    async def disconnect_ws_handler(websocket: ServerConnection) -> None:
        nonlocal connection_count
        connection_count += 1
        _ = await websocket.recv()  # Auth handshake
        if connection_count == 1:
            # Abruptly close first connection
            await websocket.close()
        else:
            # Second connection sends an order alert and stays open
            await websocket.send(
                json.dumps(
                    {
                        "Type": "order_alert",
                        "Data": {
                            "OrderNo": "ORD_RECONNECT_01",
                            "Status": "PENDING",
                            "Quantity": 50,
                            "TradedQty": 0,
                        },
                    }
                )
            )
            try:
                async for _ in websocket:
                    pass
            except Exception:
                pass

    async with serve(disconnect_ws_handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        received_frames: list[str] = []

        client = DhanOrderStreamClient(
            ws_url=f"ws://127.0.0.1:{port}",
            client_id="11001100",
            access_token="RECON_TEST_TOKEN",
            on_update=lambda u: received_frames.append(u.order_no),
            initial_reconnect_delay=0.05,
            backoff_multiplier=1.2,
            max_reconnect_attempts=5,
        )

        _ = client.start()

        # Wait for reconnection and frame arrival
        for _ in range(50):
            if "ORD_RECONNECT_01" in received_frames:
                break
            await asyncio.sleep(0.05)

        assert "ORD_RECONNECT_01" in received_frames
        assert client.reconnect_count >= 1
        assert connection_count >= 2

        await client.stop()
        assert client.is_running is False


def test_create_engine_order_stream_factory() -> None:
    """Factory correctly wires DhanOrderStreamClient with OrderReconciler and AuditLedger."""
    client = create_engine_order_stream(ws_url="ws://127.0.0.1:8888")
    assert client.ws_url == "ws://127.0.0.1:8888"
    assert client.reconciler is not None
    assert client.reconciler.audit_ledger is not None
