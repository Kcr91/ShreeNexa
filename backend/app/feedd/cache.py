"""Redis quote, OI, and market depth hot cache with freshness and feed-health tracking."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from typing import Any, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field
from redis import Redis

from app.config import get_settings
from app.dhan.packets import (
    FeedPacket,
    FullPacket,
    IndexPacket,
    OIPacket,
    QuotePacket,
    TickerPacket,
)

logger = logging.getLogger(__name__)

CACHE_SCHEMA_VERSION = 1
DEFAULT_FRESHNESS_THRESHOLD_SECONDS = 5.0
DEFAULT_CACHE_TTL_SECONDS = 86400  # 24 hours TTL for hot keys


class CachedQuote(BaseModel):
    """Normalized real-time quote cached in hot storage."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = CACHE_SCHEMA_VERSION
    segment: str
    security_id: str
    ltp: float
    ltq: int
    ltt: int
    avg_price: float
    volume: int
    total_buy_qty: float
    total_sell_qty: float
    open: float
    high: float
    low: float
    close: float
    received_at: float
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
    return f"shreenexa:feed:v1:quote:{segment}:{security_id}"


def oi_key(segment: str, security_id: str) -> str:
    return f"shreenexa:feed:v1:oi:{segment}:{security_id}"


def depth_key(segment: str, security_id: str) -> str:
    return f"shreenexa:feed:v1:depth:{segment}:{security_id}"


def health_key(socket_id: str) -> str:
    return f"shreenexa:feed:v1:health:{socket_id}"


class HotCache(Protocol):
    """Interface defining operations on the hot market data cache."""

    def update_from_packet(self, packet: FeedPacket, now: float | None = None) -> None: ...

    def batch_update_packets(
        self, packets: Sequence[FeedPacket], now: float | None = None
    ) -> None: ...

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


def _apply_freshness_quote(
    quote: CachedQuote, now: float, threshold: float
) -> CachedQuote:
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
        received_at=quote.received_at,
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


def _apply_freshness_depth(
    depth: CachedDepth, now: float, threshold: float
) -> CachedDepth:
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

    def update_from_packet(self, packet: FeedPacket, now: float | None = None) -> None:
        t = now if now is not None else time.time()
        seg = str(packet.header.exchange_segment)
        sec_id = str(packet.header.security_id)

        if isinstance(packet, (QuotePacket, FullPacket)):
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
                    high=max(existing.high, packet.ltp),
                    low=min(existing.low, packet.ltp),
                    close=existing.close,
                    received_at=t,
                )
            else:
                self._quotes[(seg, sec_id)] = CachedQuote(
                    segment=seg,
                    security_id=sec_id,
                    ltp=packet.ltp,
                    ltq=0,
                    ltt=packet.ltt,
                    avg_price=packet.ltp,
                    volume=0,
                    total_buy_qty=0.0,
                    total_sell_qty=0.0,
                    open=packet.ltp,
                    high=packet.ltp,
                    low=packet.ltp,
                    close=packet.ltp,
                    received_at=t,
                )

    def batch_update_packets(
        self, packets: Sequence[FeedPacket], now: float | None = None
    ) -> None:
        t = now if now is not None else time.time()
        for p in packets:
            self.update_from_packet(p, now=t)

    def get_quote(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedQuote | None:
        t = now if now is not None else time.time()
        item = self._quotes.get((segment, security_id))
        if not item:
            return None
        return _apply_freshness_quote(item, t, self.freshness_threshold)

    def get_oi(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedOI | None:
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

    def get_feed_health(
        self, socket_id: str, now: float | None = None
    ) -> CachedFeedHealth | None:
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

    def batch_update_packets(
        self, packets: Sequence[FeedPacket], now: float | None = None
    ) -> None:
        if not packets:
            return

        t = now if now is not None else time.time()
        pipe = self._client.pipeline(transaction=True)

        for packet in packets:
            seg = str(packet.header.exchange_segment)
            sec_id = str(packet.header.security_id)

            if isinstance(packet, (QuotePacket, FullPacket)):
                q_key = quote_key(seg, sec_id)
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
                    "received_at": t,
                }
                pipe.set(q_key, json.dumps(data), ex=self.ttl)

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

    def get_oi(
        self, segment: str, security_id: str, now: float | None = None
    ) -> CachedOI | None:
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
                results[(seg, sec_id)] = _apply_freshness_quote(
                    q, t, self.freshness_threshold
                )

        return results

    def update_feed_health(self, health: CachedFeedHealth) -> None:
        h_key = health_key(health.socket_id)
        data = health.model_dump()
        self._client.set(h_key, json.dumps(data), ex=self.ttl)
        # Add to set of known socket IDs
        self._client.sadd("shreenexa:feed:v1:sockets", health.socket_id)

    def get_feed_health(
        self, socket_id: str, now: float | None = None
    ) -> CachedFeedHealth | None:
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
        socket_ids = cast(set[Any], self._client.smembers("shreenexa:feed:v1:sockets"))
        if not socket_ids:
            return []

        health_records: list[CachedFeedHealth] = []
        for s_id in socket_ids:
            h = self.get_feed_health(str(s_id), now=t)
            if h:
                health_records.append(h)

        return health_records
