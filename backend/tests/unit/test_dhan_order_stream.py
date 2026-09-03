"""Unit tests for Live Order Update WebSocket models, auth handshake, and stream handler."""

from __future__ import annotations

import json

from app.dhan.order_stream import (
    DhanOrderStreamHandler,
    DhanOrderUpdateData,
    DhanOrderUpdateEvent,
    DhanPostbackPayload,
    build_order_stream_auth_message,
)


def test_build_order_stream_auth_message() -> None:
    auth = build_order_stream_auth_message(client_id="1100000000", access_token="JWT_SECRET_TOKEN")
    assert auth["UserType"] == "SELF"
    assert auth["LoginReq"]["MsgCode"] == 42
    assert auth["LoginReq"]["ClientId"] == "1100000000"
    assert auth["LoginReq"]["Token"] == "JWT_SECRET_TOKEN"


def test_parse_order_update_websocket_packet() -> None:
    raw_packet = json.dumps({
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
    })

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
    raw_packet = json.dumps({
        "Type": "order_alert",
        "Data": {
            "OrderNo": "ORD_HANDLER_01",
            "Status": "PENDING",
            "Quantity": 10,
            "TradedQty": 0,
        },
    })
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
