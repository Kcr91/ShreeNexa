"""Generate synthetic captured golden packets for Dhan Live Market Feed testing."""

from pathlib import Path

from app.dhan.packets import (
    DepthLevel,
    DhanFeedParser,
    ExchangeSegmentCode,
    MarketDepth5,
)

FIXTURES_DIR = Path(__file__).resolve().parent


def generate_all() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Index packet
    idx_bytes = DhanFeedParser.build_index_packet(
        exchange_segment=ExchangeSegmentCode.NSE_EQ,
        security_id=1333,
        ltp=2450.75,
        ltt=1772614500,
    )
    (FIXTURES_DIR / "golden_index.bin").write_bytes(idx_bytes)

    # 2. Ticker packet
    ticker_bytes = DhanFeedParser.build_ticker_packet(
        exchange_segment=ExchangeSegmentCode.NSE_EQ,
        security_id=2885,
        ltp=2950.50,
        ltt=1772614501,
    )
    (FIXTURES_DIR / "golden_ticker.bin").write_bytes(ticker_bytes)

    # 3. Quote packet
    quote_bytes = DhanFeedParser.build_quote_packet(
        exchange_segment=ExchangeSegmentCode.NSE_FNO,
        security_id=45000,
        ltp=155.20,
        ltq=50,
        ltt=1772614502,
        avg_price=154.80,
        volume=125000,
        total_buy_qty=35000.0,
        total_sell_qty=42000.0,
        day_open=150.00,
        day_high=162.50,
        day_low=148.00,
        day_close=152.00,
    )
    (FIXTURES_DIR / "golden_quote.bin").write_bytes(quote_bytes)

    # 4. OI packet
    oi_bytes = DhanFeedParser.build_oi_packet(
        exchange_segment=ExchangeSegmentCode.NSE_FNO,
        security_id=45000,
        open_interest=2450000,
    )
    (FIXTURES_DIR / "golden_oi.bin").write_bytes(oi_bytes)

    # 5. Full packet
    depth = MarketDepth5(
        bids=[
            DepthLevel(price=155.20, quantity=500, orders=5),
            DepthLevel(price=155.15, quantity=1200, orders=12),
            DepthLevel(price=155.10, quantity=2500, orders=18),
            DepthLevel(price=155.05, quantity=4000, orders=25),
            DepthLevel(price=155.00, quantity=8500, orders=40),
        ],
        asks=[
            DepthLevel(price=155.25, quantity=600, orders=6),
            DepthLevel(price=155.30, quantity=1400, orders=14),
            DepthLevel(price=155.35, quantity=2200, orders=19),
            DepthLevel(price=155.40, quantity=3800, orders=27),
            DepthLevel(price=155.45, quantity=7900, orders=38),
        ],
    )
    full_bytes = DhanFeedParser.build_full_packet(
        exchange_segment=ExchangeSegmentCode.NSE_FNO,
        security_id=45000,
        ltp=155.20,
        ltq=50,
        ltt=1772614502,
        avg_price=154.80,
        volume=125000,
        total_buy_qty=35000.0,
        total_sell_qty=42000.0,
        day_open=150.00,
        day_high=162.50,
        day_low=148.00,
        day_close=152.00,
        depth=depth,
        open_interest=2450000,
    )
    (FIXTURES_DIR / "golden_full.bin").write_bytes(full_bytes)

    # 6. Disconnect packet
    disc_bytes = DhanFeedParser.build_disconnect_packet(
        exchange_segment=ExchangeSegmentCode.NSE_EQ,
        security_id=0,
        disconnect_code=50,
    )
    (FIXTURES_DIR / "golden_disconnect.bin").write_bytes(disc_bytes)


if __name__ == "__main__":
    generate_all()
    print("All golden binary packet fixtures generated successfully.")
