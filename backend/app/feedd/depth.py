"""Market depth engine supporting 5, 20, and 200-level order books."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DepthLevelType(StrEnum):
    """Supported market depth resolution levels."""

    LEVEL_5 = "LEVEL_5"
    LEVEL_20 = "LEVEL_20"
    LEVEL_200 = "LEVEL_200"


class DepthLevel(BaseModel):
    """Single level in the bid or ask market depth ladder."""

    price: float
    quantity: int
    orders: int
    cumulative_qty: int = 0


class MarketDepthBook(BaseModel):
    """Comprehensive market depth order book with monotonic cumulative quantities and metadata."""

    security_id: int
    symbol: str
    segment: str
    depth_level_type: DepthLevelType
    is_fallback: bool = False
    fallback_reason: str | None = None
    connection_cost: str
    bids: list[DepthLevel] = Field(default_factory=list)
    asks: list[DepthLevel] = Field(default_factory=list)
    total_bid_qty: int = 0
    total_ask_qty: int = 0
    spread: float = 0.0
    spread_pct: float = 0.0
    imbalance_ratio: float = 0.0


class DepthWatchlistItem(BaseModel):
    """Compact depth summary for multi-script depth watchlist strip."""

    symbol: str
    segment: str
    best_bid: float
    best_ask: float
    spread: float
    top5_imbalance: float
    total_bid_qty: int
    total_ask_qty: int
    depth_level_type: DepthLevelType
    is_fallback: bool


FULL_DEPTH_SUPPORTED_SEGMENTS = {"NSE_EQ", "NSE_FNO"}


def calculate_cumulative_depth(levels: list[DepthLevel]) -> list[DepthLevel]:
    """Calculate strictly monotonic cumulative quantities for depth levels."""
    cum = 0
    result: list[DepthLevel] = []
    for level in levels:
        cum += level.quantity
        result.append(
            DepthLevel(
                price=level.price,
                quantity=level.quantity,
                orders=level.orders,
                cumulative_qty=cum,
            )
        )
    return result


def build_depth_book(
    security_id: int,
    symbol: str,
    segment: str,
    requested_level: DepthLevelType = DepthLevelType.LEVEL_20,
    raw_bids: list[DepthLevel] | None = None,
    raw_asks: list[DepthLevel] | None = None,
    base_price: float = 1000.0,
) -> MarketDepthBook:
    """Build and validate a MarketDepthBook enforcing segment capabilities."""
    is_fallback = False
    fallback_reason = None
    actual_level = requested_level

    # Segment limitation check (Spec §3.3.2 & §12.5)
    if segment not in FULL_DEPTH_SUPPORTED_SEGMENTS and requested_level in {
        DepthLevelType.LEVEL_20,
        DepthLevelType.LEVEL_200,
    }:
        actual_level = DepthLevelType.LEVEL_5
        is_fallback = True
        fallback_reason = (
            f"Exchange limitation: Full Market Depth ({requested_level.value}) is supported "
            f"only on NSE_EQ and NSE_FNO. 5-level regular feed active for {segment}."
        )

    # Connection cost metadata
    if actual_level == DepthLevelType.LEVEL_200:
        connection_cost = "Dedicated (1 full socket per instrument)"
    elif actual_level == DepthLevelType.LEVEL_20:
        connection_cost = "Shared (up to 50 instruments per depth socket)"
    else:
        connection_cost = "Regular feed packet (no dedicated depth socket consumed)"

    if actual_level == DepthLevelType.LEVEL_5:
        target_count = 5
    elif actual_level == DepthLevelType.LEVEL_20:
        target_count = 20
    else:
        target_count = 200

    # Generate synthetic depth levels if not provided
    if raw_bids is None or raw_asks is None:
        raw_bids = []
        raw_asks = []
        tick_size = 0.05
        sym_seed = sum(ord(c) for c in symbol)

        for i in range(target_count):
            bid_p = round(base_price - (i + 1) * tick_size, 2)
            bid_q = 50 + ((sym_seed * (i + 1) * 37) % 500)
            bid_o = 1 + ((sym_seed * (i + 1)) % 15)
            raw_bids.append(DepthLevel(price=bid_p, quantity=bid_q, orders=bid_o))

            ask_p = round(base_price + (i + 1) * tick_size, 2)
            ask_q = 40 + ((sym_seed * (i + 1) * 43) % 480)
            ask_o = 1 + ((sym_seed * (i + 1) * 3) % 12)
            raw_asks.append(DepthLevel(price=ask_p, quantity=ask_q, orders=ask_o))

    # Slice to actual target level count
    bids_slice = raw_bids[:target_count]
    asks_slice = raw_asks[:target_count]

    # Calculate strictly monotonic cumulative quantities
    bids = calculate_cumulative_depth(bids_slice)
    asks = calculate_cumulative_depth(asks_slice)

    total_bid_qty = bids[-1].cumulative_qty if bids else 0
    total_ask_qty = asks[-1].cumulative_qty if asks else 0

    best_bid = bids[0].price if bids else base_price
    best_ask = asks[0].price if asks else base_price
    spread = round(max(0.0, best_ask - best_bid), 2)
    spread_pct = round((spread / max(best_bid, 0.01)) * 100.0, 4)

    total_combined = total_bid_qty + total_ask_qty
    imbalance = (
        round((total_bid_qty - total_ask_qty) / total_combined, 4)
        if total_combined > 0
        else 0.0
    )

    return MarketDepthBook(
        security_id=security_id,
        symbol=symbol,
        segment=segment,
        depth_level_type=actual_level,
        is_fallback=is_fallback,
        fallback_reason=fallback_reason,
        connection_cost=connection_cost,
        bids=bids,
        asks=asks,
        total_bid_qty=total_bid_qty,
        total_ask_qty=total_ask_qty,
        spread=spread,
        spread_pct=spread_pct,
        imbalance_ratio=imbalance,
    )
