"""Unit and integration tests for browser WebSocket fan-out, backpressure, snapshots, and resync."""

from __future__ import annotations

import time
from typing import Any

import pytest
from app.api.ws import (
    ClientSession,
    MarketDataFanoutManager,
)
from app.dhan import (
    DepthLevel,
    FeedResponseCode,
    FullPacket,
    MarketDepth5,
    PacketHeader,
    QuotePacket,
)
from app.feedd.cache import InMemoryHotCache
from app.main import app
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def _make_quote_packet(segment: int, sec_id: int, ltp: float, vol: int = 1000) -> QuotePacket:
    header = PacketHeader(
        response_code=FeedResponseCode.QUOTE,
        msg_length=50,
        exchange_segment=segment,
        security_id=sec_id,
    )
    return QuotePacket(
        header=header,
        ltp=ltp,
        ltq=10,
        ltt=1772615000,
        avg_price=ltp,
        volume=vol,
        total_buy_qty=5000.0,
        total_sell_qty=5000.0,
        open=ltp,
        high=ltp + 5.0,
        low=ltp - 5.0,
        close=ltp,
    )


def test_three_client_consistency_and_slow_client_backpressure() -> None:
    """Three-client consistency test proving slow client backpressure cannot block feed ingestion.

    Invariant from F7.4:
    - 2 fast clients receive all streaming updates synchronously and consistently.
    - 1 slow client with a small, full buffer drops updates without delaying broadcast.
    - Feed ingestion completes instantaneously (< 0.2s for 100 packets).
    """
    cache = InMemoryHotCache()
    manager = MarketDataFanoutManager(hot_cache=cache)

    # Client 1: Fast client subscribed to (1, 1001) and (1, 1002)
    s1 = ClientSession(session_id="client_1_fast", max_queue_size=200)
    # Client 2: Fast client subscribed to (1, 1001) and (1, 1003)
    s2 = ClientSession(session_id="client_2_fast", max_queue_size=200)
    # Client 3: Slow client subscribed to (1, 1001) with bounded queue of 5
    s3 = ClientSession(session_id="client_3_slow", max_queue_size=5)

    manager.register_session(s1)
    manager.register_session(s2)
    manager.register_session(s3)

    manager.subscribe("client_1_fast", [("1", "1001"), ("1", "1002")])
    manager.subscribe("client_2_fast", [("1", "1001"), ("1", "1003")])
    manager.subscribe("client_3_slow", [("1", "1001")])

    # Fill s3's queue to capacity to simulate a stalled browser
    for i in range(5):
        s3.queue.put_nowait({"type": "dummy", "index": i})
    assert s3.queue.full()

    # Now ingest 50 rapid packets on (1, 1001)
    t_start = time.perf_counter()
    for i in range(50):
        pkt = _make_quote_packet(1, 1001, ltp=100.0 + i, vol=1000 + i)
        manager.broadcast_packet(pkt)
    t_elapsed = time.perf_counter() - t_start

    # Ingestion was non-blocking and ultra-fast
    assert t_elapsed < 0.2, f"Feed ingestion took {t_elapsed:.4f}s, expected < 0.2s"

    # Fast clients received their expected messages
    # Client 1 had (1, 1001) -> 50 messages
    received_s1: list[dict[str, Any]] = []
    while not s1.queue.empty():
        received_s1.append(s1.queue.get_nowait())
    assert len(received_s1) == 50
    assert received_s1[0]["data"]["ltp"] == 100.0
    assert received_s1[-1]["data"]["ltp"] == 149.0

    # Client 2 had (1, 1001) -> 50 messages
    received_s2: list[dict[str, Any]] = []
    while not s2.queue.empty():
        received_s2.append(s2.queue.get_nowait())
    assert len(received_s2) == 50
    assert received_s2[-1]["data"]["ltp"] == 149.0

    # Client 3: slow client dropped messages
    assert s3.is_slow is True
    assert s3.dropped_messages_count == 50

    metrics = manager.get_metrics()
    assert metrics["active_sessions"] == 3
    assert metrics["total_dropped_messages"] == 50
    assert metrics["slow_sessions_count"] == 1
    assert "client_3_slow" in metrics["slow_session_ids"]


def test_snapshot_delivery_on_subscribe_and_resync() -> None:
    cache = InMemoryHotCache()
    manager = MarketDataFanoutManager(hot_cache=cache)

    # Pre-populate hot cache with a composite packet (Quote, Depth, OI)
    header = PacketHeader(
        response_code=FeedResponseCode.FULL,
        msg_length=154,
        exchange_segment=1,
        security_id=2885,
    )
    full_pkt = FullPacket(
        header=header,
        ltp=2850.0,
        ltq=25,
        ltt=1772615005,
        avg_price=2845.0,
        volume=500000,
        total_buy_qty=15000.0,
        total_sell_qty=18000.0,
        open=2830.0,
        high=2860.0,
        low=2825.0,
        close=2840.0,
        depth=MarketDepth5(
            bids=[DepthLevel(price=2850.0, quantity=100, orders=1)],
            asks=[DepthLevel(price=2850.5, quantity=150, orders=2)],
        ),
        open_interest=9800000,
    )
    cache.update_from_packet(full_pkt)

    session = ClientSession(session_id="browser_tab_1")
    manager.register_session(session)

    # Subscribe to (1, 2885)
    snapshots = manager.subscribe("browser_tab_1", [("1", "2885")])
    assert len(snapshots) == 3  # quote, depth, oi
    channels = {s["channel"] for s in snapshots}
    assert channels == {"quotes", "depth", "oi"}

    # Resync
    resync_snapshots = manager.resync("browser_tab_1")
    assert len(resync_snapshots) == 3


def test_unsubscribe_cleans_routing() -> None:
    cache = InMemoryHotCache()
    manager = MarketDataFanoutManager(hot_cache=cache)

    session = ClientSession(session_id="tab_unsub")
    manager.register_session(session)
    manager.subscribe("tab_unsub", [("1", "1001")])

    # Ingest 1 packet -> received
    manager.broadcast_packet(_make_quote_packet(1, 1001, 100.0))
    assert not session.queue.empty()
    session.queue.get_nowait()

    # Unsubscribe
    manager.unsubscribe("tab_unsub", [("1", "1001")])

    # Ingest another packet -> not received
    manager.broadcast_packet(_make_quote_packet(1, 1001, 101.0))
    assert session.queue.empty()


def test_unauthenticated_websocket_rejected() -> None:
    """QA-05: Opening WebSocket without valid session cookie is rejected before accept with 4401."""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/feed/ws"):
            pass
    assert exc_info.value.code == 4401


def test_fastapi_websocket_endpoint_integration() -> None:
    """QA-05: Authenticated browser WebSocket connects and exchanges frames."""
    from app.auth.service import auth_service

    session = auth_service._create_session("ws_test_trader")
    client = TestClient(app)

    with client.websocket_connect(
        "/api/v1/feed/ws",
        cookies={"shreenexa_session": session.session_id},
    ) as ws:
        # 1. Ping / Pong
        ws.send_json({"action": "ping", "timestamp": 999888})
        pong = ws.receive_json()
        assert pong["type"] == "pong"
        assert pong["timestamp"] == 999888

        # 2. Subscribe with dictionary-based instrument specification
        ws.send_json(
            {
                "action": "subscribe",
                "instruments": [{"segment": "1", "security_id": "9999"}],
                "channels": ["quotes"],
            }
        )

        # 3. Unsubscribe
        ws.send_json(
            {
                "action": "unsubscribe",
                "instruments": [{"segment": "1", "security_id": "9999"}],
            }
        )
