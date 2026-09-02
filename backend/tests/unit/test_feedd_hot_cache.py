"""Unit tests for feedd Redis quote, OI, depth hot cache, and freshness guarantees."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.dhan import (
    DepthLevel,
    FeedResponseCode,
    FullPacket,
    MarketDepth5,
    OIPacket,
    PacketHeader,
    QuotePacket,
)
from app.feedd import (
    CACHE_SCHEMA_VERSION,
    CachedFeedHealth,
    HotCache,
    InMemoryHotCache,
    RedisHotCache,
)


def _make_quote_packet(
    segment: int = 1,
    sec_id: int = 1333,
    ltp: float = 2450.5,
    volume: int = 50000,
) -> QuotePacket:
    header = PacketHeader(
        response_code=FeedResponseCode.QUOTE,
        msg_length=50,
        exchange_segment=segment,
        security_id=sec_id,
    )
    return QuotePacket(
        header=header,
        ltp=ltp,
        ltq=25,
        ltt=1772614500,
        avg_price=2448.0,
        volume=volume,
        total_buy_qty=10000.0,
        total_sell_qty=12000.0,
        open=2440.0,
        high=2465.0,
        low=2435.0,
        close=2442.0,
    )


def _make_oi_packet(segment: int = 2, sec_id: int = 45000, oi: int = 1250000) -> OIPacket:
    header = PacketHeader(
        response_code=FeedResponseCode.OI,
        msg_length=12,
        exchange_segment=segment,
        security_id=sec_id,
    )
    return OIPacket(header=header, open_interest=oi)


def _make_full_packet(segment: int = 2, sec_id: int = 45000) -> FullPacket:
    header = PacketHeader(
        response_code=FeedResponseCode.FULL,
        msg_length=154,
        exchange_segment=segment,
        security_id=sec_id,
    )
    depth = MarketDepth5(
        bids=[
            DepthLevel(price=150.20, quantity=100, orders=2),
            DepthLevel(price=150.15, quantity=300, orders=4),
            DepthLevel(price=150.10, quantity=500, orders=7),
            DepthLevel(price=150.05, quantity=800, orders=10),
            DepthLevel(price=150.00, quantity=1500, orders=15),
        ],
        asks=[
            DepthLevel(price=150.25, quantity=150, orders=3),
            DepthLevel(price=150.30, quantity=400, orders=5),
            DepthLevel(price=150.35, quantity=650, orders=8),
            DepthLevel(price=150.40, quantity=900, orders=12),
            DepthLevel(price=150.45, quantity=1800, orders=20),
        ],
    )
    return FullPacket(
        header=header,
        ltp=150.20,
        ltq=50,
        ltt=1772614502,
        avg_price=149.80,
        volume=250000,
        total_buy_qty=45000.0,
        total_sell_qty=52000.0,
        open=145.0,
        high=155.0,
        low=144.0,
        close=146.0,
        depth=depth,
        open_interest=3400000,
    )


@pytest.mark.parametrize("cache_type", ["in_memory", "redis_mock"])
def test_quote_packet_ingestion_and_schema(cache_type: str) -> None:
    t0 = 1000.0
    cache: HotCache

    if cache_type == "in_memory":
        cache = InMemoryHotCache(freshness_threshold_seconds=5.0)
    else:
        fake_storage: dict[str, str] = {}
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda k: fake_storage.get(k)

        pipe = MagicMock()

        def fake_set(k: str, v: str, ex: int | None = None) -> None:
            fake_storage[k] = v

        pipe.set.side_effect = fake_set
        mock_redis.pipeline.return_value = pipe
        cache = RedisHotCache(redis_client=mock_redis, freshness_threshold_seconds=5.0)

    pkt = _make_quote_packet(segment=1, sec_id=1333, ltp=2450.5)
    cache.update_from_packet(pkt, now=t0)

    # Read at t0 + 1.0s (fresh)
    quote = cache.get_quote("1", "1333", now=t0 + 1.0)
    assert quote is not None
    assert quote.schema_version == CACHE_SCHEMA_VERSION
    assert quote.segment == "1"
    assert quote.security_id == "1333"
    assert quote.ltp == 2450.5
    assert quote.volume == 50000
    assert quote.is_stale is False
    assert pytest.approx(quote.staleness_seconds, 0.01) == 1.0


@pytest.mark.parametrize("cache_type", ["in_memory", "redis_mock"])
def test_freshness_boundary_stale_data_marked(cache_type: str) -> None:
    t0 = 2000.0
    threshold = 5.0
    cache: HotCache

    if cache_type == "in_memory":
        cache = InMemoryHotCache(freshness_threshold_seconds=threshold)
    else:
        fake_storage: dict[str, str] = {}
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda k: fake_storage.get(k)
        pipe = MagicMock()
        pipe.set.side_effect = lambda k, v, ex=None: fake_storage.update({k: v})
        mock_redis.pipeline.return_value = pipe
        cache = RedisHotCache(redis_client=mock_redis, freshness_threshold_seconds=threshold)

    pkt = _make_oi_packet(segment=2, sec_id=45000, oi=1250000)
    cache.update_from_packet(pkt, now=t0)

    # 1. Fresh at t0 + 4.9s
    fresh_oi = cache.get_oi("2", "45000", now=t0 + 4.9)
    assert fresh_oi is not None
    assert fresh_oi.is_stale is False
    assert pytest.approx(fresh_oi.staleness_seconds, 0.01) == 4.9

    # 2. Stale at t0 + 5.1s
    stale_oi = cache.get_oi("2", "45000", now=t0 + 5.1)
    assert stale_oi is not None
    assert stale_oi.is_stale is True
    assert pytest.approx(stale_oi.staleness_seconds, 0.01) == 5.1

    # Invariant: expired data is never marked fresh
    assert not (stale_oi.is_stale is False and stale_oi.staleness_seconds > threshold)


def test_full_packet_atomic_composite_ingestion() -> None:
    cache = InMemoryHotCache()
    t0 = 3000.0
    full_pkt = _make_full_packet(segment=2, sec_id=45000)

    cache.update_from_packet(full_pkt, now=t0)

    # 1. Quote portion
    quote = cache.get_quote("2", "45000", now=t0)
    assert quote is not None
    assert quote.ltp == 150.20
    assert quote.open == 145.0
    assert quote.volume == 250000

    # 2. Open Interest portion
    oi = cache.get_oi("2", "45000", now=t0)
    assert oi is not None
    assert oi.open_interest == 3400000

    # 3. 5-Level Depth portion
    depth = cache.get_depth("2", "45000", now=t0)
    assert depth is not None
    assert len(depth.bids) == 5
    assert len(depth.asks) == 5
    assert depth.bids[0].price == 150.20
    assert depth.bids[0].quantity == 100
    assert depth.asks[0].price == 150.25
    assert depth.asks[0].quantity == 150


def test_multi_quote_batch_query() -> None:
    cache = InMemoryHotCache()
    t0 = 4000.0

    # Populate 3 quotes
    cache.update_from_packet(_make_quote_packet(1, 1001, 100.0), now=t0)
    cache.update_from_packet(_make_quote_packet(1, 1002, 200.0), now=t0)
    cache.update_from_packet(_make_quote_packet(1, 1003, 300.0), now=t0)

    # Query 4 symbols (including 1 missing symbol 9999)
    query = [("1", "1001"), ("1", "1002"), ("1", "9999")]
    results = cache.get_multi_quotes(query, now=t0 + 1.0)

    assert len(results) == 2
    assert ("1", "1001") in results
    assert results[("1", "1001")].ltp == 100.0
    assert ("1", "1002") in results
    assert results[("1", "1002")].ltp == 200.0
    assert ("1", "9999") not in results


def test_feed_health_tracking() -> None:
    cache = InMemoryHotCache(freshness_threshold_seconds=10.0)
    t0 = 5000.0

    health = CachedFeedHealth(
        socket_id="socket_feed_1",
        is_connected=True,
        subscribed_count=1500,
        reconnect_count=2,
        total_packets=50000,
        last_packet_time="2026-09-02T12:00:00Z",
        updated_at=t0,
    )
    cache.update_feed_health(health)

    # Query specific socket at t0 + 2.0s
    record = cache.get_feed_health("socket_feed_1", now=t0 + 2.0)
    assert record is not None
    assert record.is_connected is True
    assert record.subscribed_count == 1500
    assert record.is_stale is False
    assert pytest.approx(record.staleness_seconds, 0.01) == 2.0

    # Query all health records at t0 + 15.0s (stale)
    all_records = cache.get_all_feed_health(now=t0 + 15.0)
    assert len(all_records) == 1
    assert all_records[0].is_stale is True
    assert pytest.approx(all_records[0].staleness_seconds, 0.01) == 15.0
