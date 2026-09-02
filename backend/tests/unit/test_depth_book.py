"""Unit tests for 5, 20, and 200-level market depth book and segment fallback."""

from __future__ import annotations

from app.feedd.depth import (
    DepthLevel,
    DepthLevelType,
    build_depth_book,
    calculate_cumulative_depth,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_20_level_depth_book_monotonic_cumulative_sums() -> None:
    book = build_depth_book(
        security_id=1333,
        symbol="RELIANCE",
        segment="NSE_EQ",
        requested_level=DepthLevelType.LEVEL_20,
        base_price=2980.0,
    )

    assert book.depth_level_type == DepthLevelType.LEVEL_20
    assert not book.is_fallback
    assert book.fallback_reason is None
    assert "Shared (up to 50" in book.connection_cost
    assert len(book.bids) == 20
    assert len(book.asks) == 20

    # Invariant: cumulative quantities strictly monotonically increasing
    for i in range(1, len(book.bids)):
        assert book.bids[i].cumulative_qty > book.bids[i - 1].cumulative_qty
    for i in range(1, len(book.asks)):
        assert book.asks[i].cumulative_qty > book.asks[i - 1].cumulative_qty

    assert book.total_bid_qty == book.bids[-1].cumulative_qty
    assert book.total_ask_qty == book.asks[-1].cumulative_qty
    assert -1.0 <= book.imbalance_ratio <= 1.0
    assert book.spread >= 0.0


def test_200_level_on_demand_depth_book() -> None:
    book = build_depth_book(
        security_id=4963,
        symbol="NIFTY_FUT",
        segment="NSE_FNO",
        requested_level=DepthLevelType.LEVEL_200,
        base_price=25200.0,
    )

    assert book.depth_level_type == DepthLevelType.LEVEL_200
    assert not book.is_fallback
    assert "Dedicated" in book.connection_cost
    assert len(book.bids) == 200
    assert len(book.asks) == 200

    # Invariant: monotonic cumulative sums
    for i in range(1, len(book.bids)):
        assert book.bids[i].cumulative_qty > book.bids[i - 1].cumulative_qty
    for i in range(1, len(book.asks)):
        assert book.asks[i].cumulative_qty > book.asks[i - 1].cumulative_qty

    assert book.total_bid_qty == book.bids[-1].cumulative_qty
    assert book.total_ask_qty == book.asks[-1].cumulative_qty


def test_5_level_fallback_on_unsupported_segments() -> None:
    # Request 20-level on BSE_EQ (not supported by exchange)
    bse_book = build_depth_book(
        security_id=9999,
        symbol="BSE_SENSEX",
        segment="BSE_EQ",
        requested_level=DepthLevelType.LEVEL_20,
        base_price=82500.0,
    )

    assert bse_book.depth_level_type == DepthLevelType.LEVEL_5
    assert bse_book.is_fallback
    assert "Exchange limitation" in (bse_book.fallback_reason or "")
    assert len(bse_book.bids) == 5
    assert len(bse_book.asks) == 5

    # Request 200-level on MCX_COMM
    mcx_book = build_depth_book(
        security_id=8888,
        symbol="MCX_GOLD",
        segment="MCX_COMM",
        requested_level=DepthLevelType.LEVEL_200,
        base_price=74200.0,
    )

    assert mcx_book.depth_level_type == DepthLevelType.LEVEL_5
    assert mcx_book.is_fallback
    assert len(mcx_book.bids) == 5
    assert len(mcx_book.asks) == 5


def test_calculate_cumulative_depth_helper() -> None:
    raw = [
        DepthLevel(price=100.0, quantity=50, orders=2),
        DepthLevel(price=99.5, quantity=100, orders=4),
        DepthLevel(price=99.0, quantity=150, orders=6),
    ]
    res = calculate_cumulative_depth(raw)
    assert len(res) == 3
    assert res[0].cumulative_qty == 50
    assert res[1].cumulative_qty == 150
    assert res[2].cumulative_qty == 300


def test_depth_rest_api_endpoints() -> None:
    # 1. Symbol depth endpoint
    resp = client.get("/api/v1/depth/RELIANCE?segment=NSE_EQ&level=LEVEL_20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "RELIANCE"
    assert data["depth_level_type"] == "LEVEL_20"
    assert len(data["bids"]) == 20
    assert len(data["asks"]) == 20

    # 2. Watchlist strip endpoint
    resp_wl = client.get("/api/v1/depth/watchlist")
    assert resp_wl.status_code == 200
    wl = resp_wl.json()
    assert len(wl) >= 6
    symbols = {item["symbol"] for item in wl}
    assert "RELIANCE" in symbols
    assert "BSE_SENSEX" in symbols

    bse_item = next(item for item in wl if item["symbol"] == "BSE_SENSEX")
    assert bse_item["is_fallback"]
    assert bse_item["depth_level_type"] == "LEVEL_5"
