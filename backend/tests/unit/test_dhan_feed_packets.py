"""Unit tests for Dhan live feed binary packet parser and golden packets."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.dhan import (
    CorruptPacketError,
    DhanFeedParser,
    DhanLiveFeedClient,
    DisconnectPacket,
    ExchangeSegmentCode,
    FeedResponseCode,
    FullPacket,
    IndexPacket,
    OIPacket,
    QuotePacket,
    TickerPacket,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "golden_packets"


def test_independent_golden_index_packet_decode() -> None:
    data = (FIXTURES_DIR / "golden_index.bin").read_bytes()
    packet = DhanFeedParser.parse_packet(data)

    assert isinstance(packet, IndexPacket)
    assert packet.header.response_code == FeedResponseCode.INDEX
    assert packet.header.exchange_segment == ExchangeSegmentCode.NSE_EQ
    assert packet.header.security_id == 1333
    assert packet.ltp == 2450.75
    assert packet.ltt == 1772614500


def test_independent_golden_ticker_packet_decode() -> None:
    data = (FIXTURES_DIR / "golden_ticker.bin").read_bytes()
    packet = DhanFeedParser.parse_packet(data)

    assert isinstance(packet, TickerPacket)
    assert packet.header.response_code == FeedResponseCode.TICKER
    assert packet.header.exchange_segment == ExchangeSegmentCode.NSE_EQ
    assert packet.header.security_id == 2885
    assert packet.ltp == 2950.50
    assert packet.ltt == 1772614501


def test_independent_golden_quote_packet_decode() -> None:
    data = (FIXTURES_DIR / "golden_quote.bin").read_bytes()
    packet = DhanFeedParser.parse_packet(data)

    assert isinstance(packet, QuotePacket)
    assert packet.header.response_code == FeedResponseCode.QUOTE
    assert packet.header.exchange_segment == ExchangeSegmentCode.NSE_FNO
    assert packet.header.security_id == 45000
    assert packet.ltp == 155.20
    assert packet.ltq == 50
    assert packet.ltt == 1772614502
    assert packet.avg_price == 154.80
    assert packet.volume == 125000
    assert packet.total_buy_qty == 35000.0
    assert packet.total_sell_qty == 42000.0
    assert packet.open == 150.00
    assert packet.high == 162.50
    assert packet.low == 148.00
    assert packet.close == 152.00


def test_independent_golden_oi_packet_decode() -> None:
    data = (FIXTURES_DIR / "golden_oi.bin").read_bytes()
    packet = DhanFeedParser.parse_packet(data)

    assert isinstance(packet, OIPacket)
    assert packet.header.response_code == FeedResponseCode.OI
    assert packet.header.exchange_segment == ExchangeSegmentCode.NSE_FNO
    assert packet.header.security_id == 45000
    assert packet.open_interest == 2450000


def test_independent_golden_full_packet_decode() -> None:
    data = (FIXTURES_DIR / "golden_full.bin").read_bytes()
    packet = DhanFeedParser.parse_packet(data)

    assert isinstance(packet, FullPacket)
    assert packet.header.response_code == FeedResponseCode.FULL
    assert packet.header.exchange_segment == ExchangeSegmentCode.NSE_FNO
    assert packet.header.security_id == 45000
    assert packet.ltp == 155.20
    assert packet.open_interest == 2450000

    # Verify 5-level depth levels
    assert len(packet.depth.bids) == 5
    assert len(packet.depth.asks) == 5
    assert packet.depth.bids[0].price == 155.20
    assert packet.depth.bids[0].quantity == 500
    assert packet.depth.bids[0].orders == 5
    assert packet.depth.asks[0].price == 155.25
    assert packet.depth.asks[0].quantity == 600
    assert packet.depth.asks[0].orders == 6


def test_independent_golden_disconnect_packet_decode() -> None:
    data = (FIXTURES_DIR / "golden_disconnect.bin").read_bytes()
    packet = DhanFeedParser.parse_packet(data)

    assert isinstance(packet, DisconnectPacket)
    assert packet.header.response_code == FeedResponseCode.DISCONNECT
    assert packet.disconnect_code == 50


def test_truncated_header_raises_clean_error() -> None:
    for length in [0, 1, 4, 7]:
        with pytest.raises(CorruptPacketError):
            DhanFeedParser.parse_header(b"X" * length)


def test_truncated_payload_raises_clean_error() -> None:
    # Build a valid 8-byte header for Quote packet (expects 50 bytes total)
    header = DhanFeedParser.build_header(
        response_code=FeedResponseCode.QUOTE,
        msg_length=50,
        exchange_segment=1,
        security_id=1333,
    )
    # Give only 20 bytes total (12 bytes of payload instead of 42)
    truncated = header + b"\x00" * 12
    with pytest.raises(CorruptPacketError):
        DhanFeedParser.parse_packet(truncated)


def test_unknown_response_code_raises() -> None:
    header = DhanFeedParser.build_header(
        response_code=99,
        msg_length=16,
        exchange_segment=1,
        security_id=1333,
    )
    with pytest.raises(CorruptPacketError) as exc_info:
        DhanFeedParser.parse_packet(header + b"\x00" * 8)
    assert "Unknown feed response code" in str(exc_info.value)


def test_stream_framing_multiple_packets_in_single_payload() -> None:
    client = DhanLiveFeedClient(client_id="test_client", access_token="test_token")

    ticker_bytes = (FIXTURES_DIR / "golden_ticker.bin").read_bytes()
    oi_bytes = (FIXTURES_DIR / "golden_oi.bin").read_bytes()
    full_bytes = (FIXTURES_DIR / "golden_full.bin").read_bytes()

    # Concatenate 3 distinct packets into a single TCP frame
    combined_frame = ticker_bytes + oi_bytes + full_bytes
    parsed = client.process_incoming_frame(combined_frame)

    assert len(parsed) == 3
    assert isinstance(parsed[0], TickerPacket)
    assert isinstance(parsed[1], OIPacket)
    assert isinstance(parsed[2], FullPacket)
    assert client.total_packets_received == 3
    assert client.corrupt_packets_count == 0


def test_corrupted_frame_does_not_crash_client_state() -> None:
    client = DhanLiveFeedClient(client_id="test_client", access_token="test_token")
    garbage_frame = b"\x01\x02\x03\x04\x05"  # < 8 bytes
    parsed = client.process_incoming_frame(garbage_frame)

    assert parsed == []
    assert client.corrupt_packets_count == 1
    assert client.total_packets_received == 0
