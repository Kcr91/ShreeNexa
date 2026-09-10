"""Tests for dynamic, direct-only Dhan quote ingestion in the feedd process."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from app.dhan.credentials import DhanCredentials
from app.dhan.live_feed_service import (
    DhanLiveFeedService,
    _market_state_for_trade_time,
    _quote_request_bodies,
    _wire_instruments,
    market_is_open,
)
from app.feedd import InMemoryHotCache
from pydantic import SecretStr

IST = ZoneInfo("Asia/Kolkata")


def test_market_open_uses_segment_session_windows() -> None:
    assert market_is_open(datetime(2026, 9, 8, 10, 0, tzinfo=IST)) is True
    assert market_is_open(datetime(2026, 9, 8, 8, 59, tzinfo=IST)) is False
    assert market_is_open(datetime(2026, 9, 6, 10, 0, tzinfo=IST)) is False
    assert market_is_open(datetime(2026, 9, 8, 16, 30, tzinfo=IST), "3") is True


def test_market_state_uses_dhan_trade_date_instead_of_guessed_holidays() -> None:
    now = datetime(2026, 9, 8, 10, 0, tzinfo=IST)
    assert _market_state_for_trade_time("08/09/2026 09:59:59", segment="1", now=now) == "LIVE"
    assert (
        _market_state_for_trade_time("07/09/2026 15:29:59", segment="1", now=now) == "MARKET_CLOSED"
    )
    assert _market_state_for_trade_time(None, segment="1", now=now) == "STALE"


def test_dhan_wire_mapping_and_quote_request_limits() -> None:
    wire = _wire_instruments({("1", "2885"), ("0", "13"), ("99", "1")})
    assert wire == [
        {"ExchangeSegment": "IDX_I", "SecurityId": "13"},
        {"ExchangeSegment": "NSE_EQ", "SecurityId": "2885"},
    ]

    instruments = {("1", str(security_id)) for security_id in range(1, 1002)}
    bodies = _quote_request_bodies(instruments)
    assert len(bodies) == 2
    assert sum(len(ids) for body in bodies for ids in body.values()) == 1001
    assert all(sum(len(ids) for ids in body.values()) <= 1000 for body in bodies)


def test_subscription_messages_use_official_quote_codes() -> None:
    class FakeWebSocket:
        def __init__(self) -> None:
            self.messages: list[str] = []

        async def send(self, message: str) -> None:
            self.messages.append(message)

    service = DhanLiveFeedService(hot_cache=InMemoryHotCache())
    websocket = FakeWebSocket()
    instruments = {("1", "2885")}

    asyncio.run(service._send_subscription_change(websocket, instruments))
    asyncio.run(service._send_subscription_change(websocket, instruments, unsubscribe=True))

    subscribe, unsubscribe = [json.loads(message) for message in websocket.messages]
    assert subscribe["RequestCode"] == 17
    assert unsubscribe["RequestCode"] == 18
    assert subscribe["InstrumentList"] == [{"ExchangeSegment": "NSE_EQ", "SecurityId": "2885"}]


def test_rest_bootstrap_caches_only_values_returned_by_dhan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDhanRestClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def get_quotes(self, _body: dict[str, list[int]]) -> dict[str, Any]:
            return {
                "NSE_EQ": {
                    "2885": {
                        "last_price": 1412.5,
                        "last_quantity": 20,
                        "last_trade_time": "07/09/2026 15:29:59",
                        "average_price": 1400.25,
                        "volume": 123456,
                        "buy_quantity": 4500,
                        "sell_quantity": 4700,
                        "net_change": 12.5,
                        "ohlc": {
                            "open": 1395.0,
                            "high": 1420.0,
                            "low": 1390.0,
                            "close": 1400.0,
                        },
                    }
                }
            }

    monkeypatch.setattr(
        "app.dhan.live_feed_service.resolve_dhan_credentials",
        lambda: DhanCredentials(client_id="masked-test-client", access_token=SecretStr("token")),
    )
    monkeypatch.setattr(
        "app.dhan.live_feed_service.DhanRestClient",
        FakeDhanRestClient,
    )
    cache = InMemoryHotCache()
    service = DhanLiveFeedService(hot_cache=cache)
    asyncio.run(service.sync_quotes({("1", "2885")}))

    quote = cache.get_quote("1", "2885")
    assert quote is not None
    assert quote.ltp == 1412.5
    assert quote.previous_close == 1400.0
    assert quote.volume == 123456
    assert quote.total_buy_qty == 4500.0
    assert quote.total_sell_qty == 4700.0
    assert quote.ltt == "07/09/2026 15:29:59"
    assert quote.source == "DHAN_REST"
    assert quote.market_state == "MARKET_CLOSED"
    assert quote.error is None
