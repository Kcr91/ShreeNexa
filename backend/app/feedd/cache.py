"""Redis quote, OI, and market depth hot cache with freshness and feed-health tracking."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field
from redis import Redis

from app.config import get_settings
from app.dhan.packets import (
    FeedPacket,
    FullPacket,
    IndexPacket,
    OIPacket,
    PrevClosePacket,
    QuotePacket,
    TickerPacket,
)

logger = logging.getLogger(__name__)

CACHE_SCHEMA_VERSION = 2
DEFAULT_FRESHNESS_THRESHOLD_SECONDS = 5.0
DEFAULT_CACHE_TTL_SECONDS = 604800  # Retain the last verified close across weekends.
REQUESTED_INSTRUMENTS_KEY = "shreenexa:feed:v2:requested-instruments"

MarketDataState = Literal["LIVE", "MARKET_CLOSED", "STALE", "UNAVAILABLE", "ERROR"]


class CachedQuote(BaseModel):
    """Normalized real-time quote cached in hot storage."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = CACHE_SCHEMA_VERSION
    segment: str
    security_id: str
    ltp: float | None = None
    ltq: int | None = None
    ltt: int | str | None = None
    avg_price: float | None = None
    volume: int | None = None
    total_buy_qty: float | None = None
    total_sell_qty: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    previous_close: float | None = None
    received_at: float
    source: Literal["DHAN_WEBSOCKET", "DHAN_REST"] = "DHAN_WEBSOCKET"
    market_state: MarketDataState = "LIVE"
    error: str | None = None
    is_stale: bool = False
    staleness_seconds: float = 0.0


class CachedOI(BaseModel):
    """Normalized open interest record cached in hot storage."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = CACHE_SCHEMA_VERSION
    segment: str
    security_id: str
    open_interest: int
    received_at: float
    is_stale: bool = False
    staleness_seconds: float = 0.0


class CachedDepthLevel(BaseModel):
    """Single level of order book market depth."""

    model_config = ConfigDict(frozen=True)

    price: float
    quantity: int
    orders: int


class CachedDepth(BaseModel):
    """5-level bid/ask order book depth cached in hot storage."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = CACHE_SCHEMA_VERSION
    segment: str
    security_id: str
    bids: list[CachedDepthLevel] = Field(default_factory=list)
    asks: list[CachedDepthLevel] = Field(default_factory=list)
    received_at: float
    is_stale: bool = False
    staleness_seconds: float = 0.0


class CachedFeedHealth(BaseModel):
    """Health record for an active feed socket connection."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = CACHE_SCHEMA_VERSION
    socket_id: str
    is_connected: bool
    subscribed_count: int
    reconnect_count: int
    total_packets: int
    last_packet_time: str | None = None
    updated_at: float
    is_stale: bool = False
    staleness_seconds: float = 0.0


def quote_key(segment: str, security_id: str) -> str:
    return f"shreenexa:feed:v2:quote:{segment}:{security_id}"


def oi_key(segment: str, security_id: str) -> str:
    return f"shreenexa:feed:v2:oi:{segment}:{security_id}"


def depth_key(segment: str, security_id: str) -> str:
    return f"shreenexa:feed:v2:depth:{segment}:{security_id}"


def health_key(socket_id: str) -> str:
    return f"shreenexa:feed:v2:health:{socket_id}"


class HotCache(Protocol):
    """Interface defining operations on the hot market data cache."""

    def update_from_packet(self, packet: FeedPacket, now: float | None = None) -> None: ...

    def batch_update_packets(
        self, packets: Sequence[FeedPacket], now: float | None = None
    ) -> None: ...

    def set_quote(self, quote: CachedQuote) -> None: ...

    def get_quote(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedQuote | None: ...

    def get_oi(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedOI | None: ...

    def get_depth(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedDepth | None: ...

    def get_multi_quotes(
        self, instruments: Sequence[tuple[str, str]], now: float | None = None
    ) -> dict[tuple[str, str], CachedQuote]: ...

    def update_feed_health(self, health: CachedFeedHealth) -> None: ...

    def get_feed_health(
        self, socket_id: str, now: float | None = None
    ) -> CachedFeedHealth | None: ...

    def get_all_feed_health(self, now: float | None = None) -> list[CachedFeedHealth]: ...

    def request_subscriptions(self, instruments: Sequence[tuple[str, str]]) -> None: ...

    def release_subscriptions(self, instruments: Sequence[tuple[str, str]]) -> None: ...

    def get_requested_subscriptions(self) -> set[tuple[str, str]]: ...


def _apply_freshness_quote(quote: CachedQuote, now: float, threshold: float) -> CachedQuote:
    elapsed = max(0.0, now - quote.received_at)
    is_stale = elapsed > threshold
    return CachedQuote(
        schema_version=quote.schema_version,
        segment=quote.segment,
        security_id=quote.security_id,
        ltp=quote.ltp,
        ltq=quote.ltq,
        ltt=quote.ltt,
        avg_price=quote.avg_price,
        volume=quote.volume,
        total_buy_qty=quote.total_buy_qty,
        total_sell_qty=quote.total_sell_qty,
        open=quote.open,
        high=quote.high,
        low=quote.low,
        close=quote.close,
        previous_close=quote.previous_close,
        received_at=quote.received_at,
        source=quote.source,
        market_state="STALE" if is_stale and quote.market_state == "LIVE" else quote.market_state,
        error=quote.error,
        is_stale=is_stale,
        staleness_seconds=round(elapsed, 3),
    )


def _apply_freshness_oi(oi: CachedOI, now: float, threshold: float) -> CachedOI:
    elapsed = max(0.0, now - oi.received_at)
    is_stale = elapsed > threshold
    return CachedOI(
        schema_version=oi.schema_version,
        segment=oi.segment,
        security_id=oi.security_id,
        open_interest=oi.open_interest,
        received_at=oi.received_at,
        is_stale=is_stale,
        staleness_seconds=round(elapsed, 3),
    )


def _apply_freshness_depth(depth: CachedDepth, now: float, threshold: float) -> CachedDepth:
    elapsed = max(0.0, now - depth.received_at)
    is_stale = elapsed > threshold
    return CachedDepth(
        schema_version=depth.schema_version,
        segment=depth.segment,
        security_id=depth.security_id,
        bids=depth.bids,
        asks=depth.asks,
        received_at=depth.received_at,
        is_stale=is_stale,
        staleness_seconds=round(elapsed, 3),
    )


def _apply_freshness_health(
    health: CachedFeedHealth, now: float, threshold: float
) -> CachedFeedHealth:
    elapsed = max(0.0, now - health.updated_at)
    is_stale = elapsed > threshold
    return CachedFeedHealth(
        schema_version=health.schema_version,
        socket_id=health.socket_id,
        is_connected=health.is_connected,
        subscribed_count=health.subscribed_count,
        reconnect_count=health.reconnect_count,
        total_packets=health.total_packets,
        last_packet_time=health.last_packet_time,
        updated_at=health.updated_at,
        is_stale=is_stale,
        staleness_seconds=round(elapsed, 3),
    )


class InMemoryHotCache:
    """Thread-safe in-memory implementation of HotCache for fast unit testing."""

    def __init__(
        self, freshness_threshold_seconds: float = DEFAULT_FRESHNESS_THRESHOLD_SECONDS
    ) -> None:
        self.freshness_threshold = freshness_threshold_seconds
        self._quotes: dict[tuple[str, str], CachedQuote] = {}
        self._oi: dict[tuple[str, str], CachedOI] = {}
        self._depth: dict[tuple[str, str], CachedDepth] = {}
        self._health: dict[str, CachedFeedHealth] = {}
        self._requested: set[tuple[str, str]] = set()

    def update_from_packet(self, packet: FeedPacket, now: float | None = None) -> None:
        t = now if now is not None else time.time()
        seg = str(packet.header.exchange_segment)
        sec_id = str(packet.header.security_id)

        if isinstance(packet, (QuotePacket, FullPacket)):
            existing_quote = self._quotes.get((seg, sec_id))
            self._quotes[(seg, sec_id)] = CachedQuote(
                segment=seg,
                security_id=sec_id,
                ltp=packet.ltp,
                ltq=packet.ltq,
                ltt=packet.ltt,
                avg_price=packet.avg_price,
                volume=packet.volume,
                total_buy_qty=packet.total_buy_qty,
                total_sell_qty=packet.total_sell_qty,
                open=packet.open,
                high=packet.high,
                low=packet.low,
                close=packet.close,
                previous_close=(
                    existing_quote.previous_close if existing_quote is not None else None
                ),
                received_at=t,
            )

        if isinstance(packet, (OIPacket, FullPacket)):
            self._oi[(seg, sec_id)] = CachedOI(
                segment=seg,
                security_id=sec_id,
                open_interest=packet.open_interest,
                received_at=t,
            )

        if isinstance(packet, FullPacket):
            bids = [
                CachedDepthLevel(price=b.price, quantity=b.quantity, orders=b.orders)
                for b in packet.depth.bids
            ]
            asks = [
                CachedDepthLevel(price=a.price, quantity=a.quantity, orders=a.orders)
                for a in packet.depth.asks
            ]
            self._depth[(seg, sec_id)] = CachedDepth(
                segment=seg,
                security_id=sec_id,
                bids=bids,
                asks=asks,
                received_at=t,
            )

        elif isinstance(packet, (IndexPacket, TickerPacket)):
            # Update only LTP and LTT if quote exists, or initialize minimal quote
            existing = self._quotes.get((seg, sec_id))
            if existing:
                self._quotes[(seg, sec_id)] = CachedQuote(
                    segment=seg,
                    security_id=sec_id,
                    ltp=packet.ltp,
                    ltq=existing.ltq,
                    ltt=packet.ltt,
                    avg_price=existing.avg_price,
                    volume=existing.volume,
                    total_buy_qty=existing.total_buy_qty,
                    total_sell_qty=existing.total_sell_qty,
                    open=existing.open,
                    high=max(existing.high, packet.ltp) if existing.high is not None else None,
                    low=min(existing.low, packet.ltp) if existing.low is not None else None,
                    close=existing.close,
                    previous_close=existing.previous_close,
                    received_at=t,
                )
            else:
                self._quotes[(seg, sec_id)] = CachedQuote(
                    segment=seg,
                    security_id=sec_id,
                    ltp=packet.ltp,
                    ltt=packet.ltt,
                    received_at=t,
                )

        elif isinstance(packet, PrevClosePacket):
            existing = self._quotes.get((seg, sec_id))
            if existing:
                self._quotes[(seg, sec_id)] = CachedQuote(
                    segment=seg,
                    security_id=sec_id,
                    ltp=existing.ltp,
                    ltq=existing.ltq,
                    ltt=existing.ltt,
                    avg_price=existing.avg_price,
                    volume=existing.volume,
                    total_buy_qty=existing.total_buy_qty,
                    total_sell_qty=existing.total_sell_qty,
                    open=existing.open,
                    high=existing.high,
                    low=existing.low,
                    close=existing.close,
                    previous_close=packet.prev_close,
                    received_at=t,
                )
            else:
                self._quotes[(seg, sec_id)] = CachedQuote(
                    segment=seg,
                    security_id=sec_id,
                    previous_close=packet.prev_close,
                    received_at=t,
                )

    def batch_update_packets(self, packets: Sequence[FeedPacket], now: float | None = None) -> None:
        t = now if now is not None else time.time()
        for p in packets:
            self.update_from_packet(p, now=t)

    def set_quote(self, quote: CachedQuote) -> None:
        self._quotes[(quote.segment, quote.security_id)] = quote

    def get_quote(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedQuote | None:
        t = now if now is not None else time.time()
        item = self._quotes.get((segment, security_id))
        if not item:
            return None
        return _apply_freshness_quote(item, t, self.freshness_threshold)

    def get_oi(self, segment: str, security_id: str, now: float | None = None) -> CachedOI | None:
        t = now if now is not None else time.time()
        item = self._oi.get((segment, security_id))
        if not item:
            return None
        return _apply_freshness_oi(item, t, self.freshness_threshold)

    def get_depth(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedDepth | None:
        t = now if now is not None else time.time()
        item = self._depth.get((segment, security_id))
        if not item:
            return None
        return _apply_freshness_depth(item, t, self.freshness_threshold)

    def get_multi_quotes(
        self, instruments: Sequence[tuple[str, str]], now: float | None = None
    ) -> dict[tuple[str, str], CachedQuote]:
        t = now if now is not None else time.time()
        res: dict[tuple[str, str], CachedQuote] = {}
        for seg, sec_id in instruments:
            q = self.get_quote(seg, sec_id, now=t)
            if q:
                res[(seg, sec_id)] = q
        return res

    def update_feed_health(self, health: CachedFeedHealth) -> None:
        self._health[health.socket_id] = health

    def get_feed_health(self, socket_id: str, now: float | None = None) -> CachedFeedHealth | None:
        t = now if now is not None else time.time()
        item = self._health.get(socket_id)
        if not item:
            return None
        return _apply_freshness_health(item, t, self.freshness_threshold)

    def get_all_feed_health(self, now: float | None = None) -> list[CachedFeedHealth]:
        t = now if now is not None else time.time()
        return [
            _apply_freshness_health(item, t, self.freshness_threshold)
            for item in self._health.values()
        ]

    def request_subscriptions(self, instruments: Sequence[tuple[str, str]]) -> None:
        self._requested.update((str(seg), str(sec_id)) for seg, sec_id in instruments)

    def release_subscriptions(self, instruments: Sequence[tuple[str, str]]) -> None:
        self._requested.difference_update((str(seg), str(sec_id)) for seg, sec_id in instruments)

    def get_requested_subscriptions(self) -> set[tuple[str, str]]:
        return set(self._requested)


class RedisHotCache:
    """Production Redis-backed implementation of HotCache supporting atomic pipeline writes."""

    def __init__(
        self,
        redis_client: Redis | None = None,
        freshness_threshold_seconds: float = DEFAULT_FRESHNESS_THRESHOLD_SECONDS,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        if redis_client is not None:
            self._client = redis_client
        else:
            settings = get_settings()
            self._client = Redis.from_url(
                settings.redis_url.get_secret_value(), decode_responses=True
            )

        self.freshness_threshold = freshness_threshold_seconds
        self.ttl = ttl_seconds

    def update_from_packet(self, packet: FeedPacket, now: float | None = None) -> None:
        self.batch_update_packets([packet], now=now)

    def batch_update_packets(self, packets: Sequence[FeedPacket], now: float | None = None) -> None:
        if not packets:
            return

        t = now if now is not None else time.time()
        # Packet types must merge with the existing quote; writing only quote/full
        # packets loses ticker/index updates and can corrupt LTP on previous-close.
        passthrough: list[IndexPacket | TickerPacket | PrevClosePacket] = []
        pipe = self._client.pipeline(transaction=True)

        for packet in packets:
            seg = str(packet.header.exchange_segment)
            sec_id = str(packet.header.security_id)

            if isinstance(packet, (QuotePacket, FullPacket)):
                q_key = quote_key(seg, sec_id)
                existing_quote = self.get_quote(seg, sec_id, now=t)
                data = {
                    "schema_version": CACHE_SCHEMA_VERSION,
                    "segment": seg,
                    "security_id": sec_id,
                    "ltp": packet.ltp,
                    "ltq": packet.ltq,
                    "ltt": packet.ltt,
                    "avg_price": packet.avg_price,
                    "volume": packet.volume,
                    "total_buy_qty": packet.total_buy_qty,
                    "total_sell_qty": packet.total_sell_qty,
                    "open": packet.open,
                    "high": packet.high,
                    "low": packet.low,
                    "close": packet.close,
                    "previous_close": (
                        existing_quote.previous_close if existing_quote is not None else None
                    ),
                    "received_at": t,
                    "source": "DHAN_WEBSOCKET",
                    "market_state": "LIVE",
                }
                pipe.set(q_key, json.dumps(data), ex=self.ttl)
            elif isinstance(packet, (TickerPacket, IndexPacket, PrevClosePacket)):
                passthrough.append(packet)

            if isinstance(packet, (OIPacket, FullPacket)):
                o_key = oi_key(seg, sec_id)
                oi_data = {
                    "schema_version": CACHE_SCHEMA_VERSION,
                    "segment": seg,
                    "security_id": sec_id,
                    "open_interest": packet.open_interest,
                    "received_at": t,
                }
                pipe.set(o_key, json.dumps(oi_data), ex=self.ttl)

            if isinstance(packet, FullPacket):
                d_key = depth_key(seg, sec_id)
                bids = [
                    {"price": b.price, "quantity": b.quantity, "orders": b.orders}
                    for b in packet.depth.bids
                ]
                asks = [
                    {"price": a.price, "quantity": a.quantity, "orders": a.orders}
                    for a in packet.depth.asks
                ]
                depth_data = {
                    "schema_version": CACHE_SCHEMA_VERSION,
                    "segment": seg,
                    "security_id": sec_id,
                    "bids": bids,
                    "asks": asks,
                    "received_at": t,
                }
                pipe.set(d_key, json.dumps(depth_data), ex=self.ttl)

        pipe.execute()

        # These updates depend on the previous cache value and are deliberately
        # merged after the atomic independent writes above.
        for packet in passthrough:
            seg = str(packet.header.exchange_segment)
            sec_id = str(packet.header.security_id)
            existing = self.get_quote(seg, sec_id, now=t)
            if isinstance(packet, PrevClosePacket):
                quote = (
                    existing.model_copy(
                        update={
                            "previous_close": packet.prev_close,
                            "received_at": t,
                            "is_stale": False,
                            "staleness_seconds": 0.0,
                        }
                    )
                    if existing
                    else CachedQuote(
                        segment=seg,
                        security_id=sec_id,
                        previous_close=packet.prev_close,
                        received_at=t,
                    )
                )
            else:
                quote = (
                    existing.model_copy(
                        update={
                            "ltp": packet.ltp,
                            "ltt": packet.ltt,
                            "received_at": t,
                            "source": "DHAN_WEBSOCKET",
                            "market_state": "LIVE",
                            "is_stale": False,
                            "staleness_seconds": 0.0,
                        }
                    )
                    if existing
                    else CachedQuote(
                        segment=seg,
                        security_id=sec_id,
                        ltp=packet.ltp,
                        ltt=packet.ltt,
                        received_at=t,
                    )
                )
            self.set_quote(quote)

    def set_quote(self, quote: CachedQuote) -> None:
        q_key = quote_key(quote.segment, quote.security_id)
        self._client.set(q_key, quote.model_dump_json(), ex=self.ttl)

    def get_quote(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedQuote | None:
        t = now if now is not None else time.time()
        val = self._client.get(quote_key(segment, security_id))
        if not val:
            return None
        data = json.loads(val)  # type: ignore[arg-type]
        quote = CachedQuote.model_validate(data)
        return _apply_freshness_quote(quote, t, self.freshness_threshold)

    def get_oi(self, segment: str, security_id: str, now: float | None = None) -> CachedOI | None:
        t = now if now is not None else time.time()
        val = self._client.get(oi_key(segment, security_id))
        if not val:
            return None
        data = json.loads(val)  # type: ignore[arg-type]
        oi = CachedOI.model_validate(data)
        return _apply_freshness_oi(oi, t, self.freshness_threshold)

    def get_depth(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedDepth | None:
        t = now if now is not None else time.time()
        val = self._client.get(depth_key(segment, security_id))
        if not val:
            return None
        data = json.loads(val)  # type: ignore[arg-type]
        depth = CachedDepth.model_validate(data)
        return _apply_freshness_depth(depth, t, self.freshness_threshold)

    def get_multi_quotes(
        self, instruments: Sequence[tuple[str, str]], now: float | None = None
    ) -> dict[tuple[str, str], CachedQuote]:
        if not instruments:
            return {}

        t = now if now is not None else time.time()
        keys = [quote_key(seg, sec_id) for seg, sec_id in instruments]
        raw_vals = cast(list[Any], self._client.mget(keys))

        results: dict[tuple[str, str], CachedQuote] = {}
        for (seg, sec_id), raw in zip(instruments, raw_vals, strict=True):
            if raw:
                data = json.loads(raw)
                q = CachedQuote.model_validate(data)
                results[(seg, sec_id)] = _apply_freshness_quote(q, t, self.freshness_threshold)

        return results

    def update_feed_health(self, health: CachedFeedHealth) -> None:
        h_key = health_key(health.socket_id)
        data = health.model_dump()
        self._client.set(h_key, json.dumps(data), ex=self.ttl)
        # Add to set of known socket IDs
        self._client.sadd("shreenexa:feed:v2:sockets", health.socket_id)

    def get_feed_health(self, socket_id: str, now: float | None = None) -> CachedFeedHealth | None:
        t = now if now is not None else time.time()
        h_key = health_key(socket_id)
        val = self._client.get(h_key)
        if not val:
            return None
        data = json.loads(val)  # type: ignore[arg-type]
        health = CachedFeedHealth.model_validate(data)
        return _apply_freshness_health(health, t, self.freshness_threshold)

    def get_all_feed_health(self, now: float | None = None) -> list[CachedFeedHealth]:
        t = now if now is not None else time.time()
        socket_ids = cast(set[Any], self._client.smembers("shreenexa:feed:v2:sockets"))
        if not socket_ids:
            return []

        health_records: list[CachedFeedHealth] = []
        for s_id in socket_ids:
            h = self.get_feed_health(str(s_id), now=t)
            if h:
                health_records.append(h)

        return health_records

    def request_subscriptions(self, instruments: Sequence[tuple[str, str]]) -> None:
        values = [f"{seg}|{sec_id}" for seg, sec_id in instruments if seg and sec_id]
        if values:
            self._client.sadd(REQUESTED_INSTRUMENTS_KEY, *values)

    def release_subscriptions(self, instruments: Sequence[tuple[str, str]]) -> None:
        values = [f"{seg}|{sec_id}" for seg, sec_id in instruments if seg and sec_id]
        if values:
            self._client.srem(REQUESTED_INSTRUMENTS_KEY, *values)

    def get_requested_subscriptions(self) -> set[tuple[str, str]]:
        values = cast(set[Any], self._client.smembers(REQUESTED_INSTRUMENTS_KEY))
        requested: set[tuple[str, str]] = set()
        for value in values:
            segment, separator, security_id = str(value).partition("|")
            if separator and segment and security_id:
                requested.add((segment, security_id))
        return requested
