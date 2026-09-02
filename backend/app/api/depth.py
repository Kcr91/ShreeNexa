"""REST API endpoints for market depth ladder and depth watchlist strip."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.feedd.depth import (
    DepthLevelType,
    DepthWatchlistItem,
    MarketDepthBook,
    build_depth_book,
)

router = APIRouter(prefix="/api/v1/depth", tags=["depth"])


@router.get("/watchlist", response_model=list[DepthWatchlistItem])
def get_depth_watchlist() -> list[DepthWatchlistItem]:
    """Retrieve multi-script depth watchlist strip summary for up to 50 pinned instruments."""
    pinned = [
        ("RELIANCE", "NSE_EQ", 2980.0, 1333),
        ("HDFCBANK", "NSE_EQ", 1640.0, 1334),
        ("ICICIBANK", "NSE_EQ", 1215.0, 4963),
        ("INFY", "NSE_EQ", 1890.0, 1594),
        ("TCS", "NSE_EQ", 4210.0, 11536),
        ("SBIN", "NSE_EQ", 815.0, 3045),
        ("BSE_SENSEX", "BSE_EQ", 82500.0, 9999),
        ("MCX_GOLD", "MCX_COMM", 74200.0, 8888),
    ]

    items: list[DepthWatchlistItem] = []
    for sym, seg, base_p, sec_id in pinned:
        book = build_depth_book(
            security_id=sec_id,
            symbol=sym,
            segment=seg,
            requested_level=DepthLevelType.LEVEL_20,
            base_price=base_p,
        )
        best_b = book.bids[0].price if book.bids else base_p
        best_a = book.asks[0].price if book.asks else base_p
        top5_b = sum(b.quantity for b in book.bids[:5])
        top5_a = sum(a.quantity for a in book.asks[:5])
        top5_imbalance = (
            round((top5_b - top5_a) / (top5_b + top5_a), 4)
            if (top5_b + top5_a) > 0
            else 0.0
        )

        items.append(
            DepthWatchlistItem(
                symbol=sym,
                segment=seg,
                best_bid=best_b,
                best_ask=best_a,
                spread=book.spread,
                top5_imbalance=top5_imbalance,
                total_bid_qty=book.total_bid_qty,
                total_ask_qty=book.total_ask_qty,
                depth_level_type=book.depth_level_type,
                is_fallback=book.is_fallback,
            )
        )
    return items


@router.get("/{symbol}", response_model=MarketDepthBook)
def get_market_depth(
    symbol: str,
    segment: Annotated[
        str, Query(description="Exchange segment, e.g. NSE_EQ, BSE_EQ, MCX_COMM")
    ] = "NSE_EQ",
    level: Annotated[
        DepthLevelType,
        Query(description="Requested depth level: LEVEL_5, LEVEL_20, LEVEL_200"),
    ] = DepthLevelType.LEVEL_20,
    security_id: Annotated[int, Query(description="Dhan security ID")] = 1333,
    base_price: Annotated[
        float, Query(description="Base price anchor for depth generation")
    ] = 1000.0,
) -> MarketDepthBook:
    """Retrieve full market depth book for a focused instrument with fallback handling."""
    return build_depth_book(
        security_id=security_id,
        symbol=symbol,
        segment=segment,
        requested_level=level,
        base_price=base_price,
    )
