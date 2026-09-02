"""Binary packet definitions, serializers, and deserializers for DhanHQ Live Market Feed."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum


class FeedResponseCode(IntEnum):
    """Binary feed packet response codes from Dhan."""

    INDEX = 1
    TICKER = 2
    QUOTE = 4
    OI = 5
    FULL = 8
    DISCONNECT = 50


class ExchangeSegmentCode(IntEnum):
    """Numeric exchange segment identifier in Dhan binary headers."""

    NSE_EQ = 1
    NSE_FNO = 2
    NSE_CURRENCY = 3
    BSE_EQ = 4
    MCX_COMM = 5
    BSE_CURRENCY = 7
    BSE_FNO = 8


class CorruptPacketError(ValueError):
    """Raised when an incoming packet is truncated, malformed, or has an invalid structure."""


@dataclass(frozen=True, slots=True)
class PacketHeader:
    """Standard 8-byte header present in all Dhan live feed packets."""

    response_code: int
    msg_length: int
    exchange_segment: int
    security_id: int


@dataclass(frozen=True, slots=True)
class DepthLevel:
    """Single level of order book market depth."""

    price: float
    quantity: int
    orders: int


@dataclass(frozen=True, slots=True)
class MarketDepth5:
    """Standard 5-level bid/ask market depth ladder."""

    bids: list[DepthLevel]
    asks: list[DepthLevel]


@dataclass(frozen=True, slots=True)
class IndexPacket:
    """Index ticker packet containing current index level and timestamp."""

    header: PacketHeader
    ltp: float
    ltt: int


@dataclass(frozen=True, slots=True)
class TickerPacket:
    """Basic price ticker packet."""

    header: PacketHeader
    ltp: float
    ltt: int


@dataclass(frozen=True, slots=True)
class QuotePacket:
    """Detailed market quote packet."""

    header: PacketHeader
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


@dataclass(frozen=True, slots=True)
class OIPacket:
    """Open interest update packet."""

    header: PacketHeader
    open_interest: int


@dataclass(frozen=True, slots=True)
class FullPacket:
    """Full comprehensive market packet combining quote, 5-level depth, and open interest."""

    header: PacketHeader
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
    depth: MarketDepth5
    open_interest: int


@dataclass(frozen=True, slots=True)
class DisconnectPacket:
    """Server disconnect signal packet."""

    header: PacketHeader
    disconnect_code: int


FeedPacket = (
    IndexPacket
    | TickerPacket
    | QuotePacket
    | OIPacket
    | FullPacket
    | DisconnectPacket
)


class DhanFeedParser:
    """High-performance parser for Little-Endian DhanHQ binary live feed packets."""

    HEADER_SIZE = 8
    HEADER_FORMAT = "<BHBi"

    INDEX_PAYLOAD_FORMAT = "<fi"
    INDEX_PACKET_SIZE = 16

    TICKER_PAYLOAD_FORMAT = "<fi"
    TICKER_PACKET_SIZE = 16

    QUOTE_PAYLOAD_FORMAT = "<fHifIffffff"
    QUOTE_PACKET_SIZE = 50

    OI_PAYLOAD_FORMAT = "<I"
    OI_PACKET_SIZE = 12

    DEPTH_LEVEL_FORMAT = "<fih"
    DEPTH_LEVEL_SIZE = 10  # 4B price + 4B qty + 2B orders
    FULL_PACKET_SIZE = 154  # 8 (header) + 42 (quote fields) + 100 (5 bids + 5 asks) + 4 (OI)

    DISCONNECT_PAYLOAD_FORMAT = "<H"
    DISCONNECT_PACKET_SIZE = 10

    @classmethod
    def parse_header(cls, data: bytes) -> PacketHeader:
        """Parse the standard 8-byte header from raw packet bytes."""
        if len(data) < cls.HEADER_SIZE:
            raise CorruptPacketError(
                f"Packet truncated: expected at least {cls.HEADER_SIZE} bytes, got {len(data)}"
            )
        try:
            resp_code, msg_len, segment, sec_id = struct.unpack_from(cls.HEADER_FORMAT, data, 0)
        except struct.error as exc:
            raise CorruptPacketError(f"Malformed packet header: {exc}") from exc

        return PacketHeader(
            response_code=resp_code,
            msg_length=msg_len,
            exchange_segment=segment,
            security_id=sec_id,
        )

    @classmethod
    def parse_packet(cls, data: bytes) -> FeedPacket:
        """Parse raw binary data into a typed FeedPacket dataclass."""
        header = cls.parse_header(data)

        if header.response_code == FeedResponseCode.INDEX:
            return cls._parse_index(data, header)
        elif header.response_code == FeedResponseCode.TICKER:
            return cls._parse_ticker(data, header)
        elif header.response_code == FeedResponseCode.QUOTE:
            return cls._parse_quote(data, header)
        elif header.response_code == FeedResponseCode.OI:
            return cls._parse_oi(data, header)
        elif header.response_code == FeedResponseCode.FULL:
            return cls._parse_full(data, header)
        elif header.response_code == FeedResponseCode.DISCONNECT:
            return cls._parse_disconnect(data, header)
        else:
            raise CorruptPacketError(f"Unknown feed response code: {header.response_code}")

    @classmethod
    def _parse_index(cls, data: bytes, header: PacketHeader) -> IndexPacket:
        if len(data) < cls.INDEX_PACKET_SIZE:
            raise CorruptPacketError(
                f"Index packet truncated: expected {cls.INDEX_PACKET_SIZE} bytes, got {len(data)}"
            )
        ltp, ltt = struct.unpack_from(cls.INDEX_PAYLOAD_FORMAT, data, cls.HEADER_SIZE)
        return IndexPacket(header=header, ltp=round(ltp, 2), ltt=ltt)

    @classmethod
    def _parse_ticker(cls, data: bytes, header: PacketHeader) -> TickerPacket:
        if len(data) < cls.TICKER_PACKET_SIZE:
            raise CorruptPacketError(
                f"Ticker packet truncated: expected {cls.TICKER_PACKET_SIZE} bytes, got {len(data)}"
            )
        ltp, ltt = struct.unpack_from(cls.TICKER_PAYLOAD_FORMAT, data, cls.HEADER_SIZE)
        return TickerPacket(header=header, ltp=round(ltp, 2), ltt=ltt)

    @classmethod
    def _parse_quote(cls, data: bytes, header: PacketHeader) -> QuotePacket:
        if len(data) < cls.QUOTE_PACKET_SIZE:
            raise CorruptPacketError(
                f"Quote packet truncated: expected {cls.QUOTE_PACKET_SIZE} bytes, got {len(data)}"
            )
        (
            ltp,
            ltq,
            ltt,
            avg_price,
            volume,
            tot_buy,
            tot_sell,
            day_open,
            day_high,
            day_low,
            day_close,
        ) = struct.unpack_from(cls.QUOTE_PAYLOAD_FORMAT, data, cls.HEADER_SIZE)

        return QuotePacket(
            header=header,
            ltp=round(ltp, 2),
            ltq=ltq,
            ltt=ltt,
            avg_price=round(avg_price, 2),
            volume=volume,
            total_buy_qty=float(tot_buy),
            total_sell_qty=float(tot_sell),
            open=round(day_open, 2),
            high=round(day_high, 2),
            low=round(day_low, 2),
            close=round(day_close, 2),
        )

    @classmethod
    def _parse_oi(cls, data: bytes, header: PacketHeader) -> OIPacket:
        if len(data) < cls.OI_PACKET_SIZE:
            raise CorruptPacketError(
                f"OI packet truncated: expected {cls.OI_PACKET_SIZE} bytes, got {len(data)}"
            )
        (oi,) = struct.unpack_from(cls.OI_PAYLOAD_FORMAT, data, cls.HEADER_SIZE)
        return OIPacket(header=header, open_interest=oi)

    @classmethod
    def _parse_full(cls, data: bytes, header: PacketHeader) -> FullPacket:
        if len(data) < cls.FULL_PACKET_SIZE:
            raise CorruptPacketError(
                f"Full packet truncated: expected {cls.FULL_PACKET_SIZE} bytes, got {len(data)}"
            )

        # 1. Parse quote fields
        (
            ltp,
            ltq,
            ltt,
            avg_price,
            volume,
            tot_buy,
            tot_sell,
            day_open,
            day_high,
            day_low,
            day_close,
        ) = struct.unpack_from(cls.QUOTE_PAYLOAD_FORMAT, data, cls.HEADER_SIZE)

        # 2. Parse 5 bids + 5 asks
        offset = cls.QUOTE_PACKET_SIZE
        bids: list[DepthLevel] = []
        for _ in range(5):
            price, qty, orders = struct.unpack_from(cls.DEPTH_LEVEL_FORMAT, data, offset)
            bids.append(DepthLevel(price=round(price, 2), quantity=qty, orders=orders))
            offset += cls.DEPTH_LEVEL_SIZE

        asks: list[DepthLevel] = []
        for _ in range(5):
            price, qty, orders = struct.unpack_from(cls.DEPTH_LEVEL_FORMAT, data, offset)
            asks.append(DepthLevel(price=round(price, 2), quantity=qty, orders=orders))
            offset += cls.DEPTH_LEVEL_SIZE

        # 3. Parse open interest
        (oi,) = struct.unpack_from(cls.OI_PAYLOAD_FORMAT, data, offset)

        return FullPacket(
            header=header,
            ltp=round(ltp, 2),
            ltq=ltq,
            ltt=ltt,
            avg_price=round(avg_price, 2),
            volume=volume,
            total_buy_qty=float(tot_buy),
            total_sell_qty=float(tot_sell),
            open=round(day_open, 2),
            high=round(day_high, 2),
            low=round(day_low, 2),
            close=round(day_close, 2),
            depth=MarketDepth5(bids=bids, asks=asks),
            open_interest=oi,
        )

    @classmethod
    def _parse_disconnect(cls, data: bytes, header: PacketHeader) -> DisconnectPacket:
        if len(data) < cls.DISCONNECT_PACKET_SIZE:
            raise CorruptPacketError(
                f"Disconnect packet truncated: expected {cls.DISCONNECT_PACKET_SIZE} bytes, "
                f"got {len(data)}"
            )
        (disc_code,) = struct.unpack_from(cls.DISCONNECT_PAYLOAD_FORMAT, data, cls.HEADER_SIZE)
        return DisconnectPacket(header=header, disconnect_code=disc_code)

    # -------------------------------------------------------------------------
    # Builders / Serializers (for golden fixtures, testing, and mocking)
    # -------------------------------------------------------------------------

    @classmethod
    def build_header(
        cls, response_code: int, msg_length: int, exchange_segment: int, security_id: int
    ) -> bytes:
        return struct.pack(
            cls.HEADER_FORMAT, response_code, msg_length, exchange_segment, security_id
        )

    @classmethod
    def build_index_packet(
        cls, exchange_segment: int, security_id: int, ltp: float, ltt: int
    ) -> bytes:
        header = cls.build_header(
            FeedResponseCode.INDEX, cls.INDEX_PACKET_SIZE, exchange_segment, security_id
        )
        payload = struct.pack(cls.INDEX_PAYLOAD_FORMAT, ltp, ltt)
        return header + payload

    @classmethod
    def build_ticker_packet(
        cls, exchange_segment: int, security_id: int, ltp: float, ltt: int
    ) -> bytes:
        header = cls.build_header(
            FeedResponseCode.TICKER, cls.TICKER_PACKET_SIZE, exchange_segment, security_id
        )
        payload = struct.pack(cls.TICKER_PAYLOAD_FORMAT, ltp, ltt)
        return header + payload

    @classmethod
    def build_quote_packet(
        cls,
        exchange_segment: int,
        security_id: int,
        ltp: float,
        ltq: int,
        ltt: int,
        avg_price: float,
        volume: int,
        total_buy_qty: float,
        total_sell_qty: float,
        day_open: float,
        day_high: float,
        day_low: float,
        day_close: float,
    ) -> bytes:
        header = cls.build_header(
            FeedResponseCode.QUOTE, cls.QUOTE_PACKET_SIZE, exchange_segment, security_id
        )
        payload = struct.pack(
            cls.QUOTE_PAYLOAD_FORMAT,
            ltp,
            ltq,
            ltt,
            avg_price,
            volume,
            float(total_buy_qty),
            float(total_sell_qty),
            day_open,
            day_high,
            day_low,
            day_close,
        )
        return header + payload

    @classmethod
    def build_oi_packet(
        cls, exchange_segment: int, security_id: int, open_interest: int
    ) -> bytes:
        header = cls.build_header(
            FeedResponseCode.OI, cls.OI_PACKET_SIZE, exchange_segment, security_id
        )
        payload = struct.pack(cls.OI_PAYLOAD_FORMAT, open_interest)
        return header + payload

    @classmethod
    def build_full_packet(
        cls,
        exchange_segment: int,
        security_id: int,
        ltp: float,
        ltq: int,
        ltt: int,
        avg_price: float,
        volume: int,
        total_buy_qty: float,
        total_sell_qty: float,
        day_open: float,
        day_high: float,
        day_low: float,
        day_close: float,
        depth: MarketDepth5,
        open_interest: int,
    ) -> bytes:
        header = cls.build_header(
            FeedResponseCode.FULL, cls.FULL_PACKET_SIZE, exchange_segment, security_id
        )
        quote_part = struct.pack(
            cls.QUOTE_PAYLOAD_FORMAT,
            ltp,
            ltq,
            ltt,
            avg_price,
            volume,
            float(total_buy_qty),
            float(total_sell_qty),
            day_open,
            day_high,
            day_low,
            day_close,
        )
        depth_bids = b"".join(
            struct.pack(cls.DEPTH_LEVEL_FORMAT, b.price, b.quantity, b.orders)
            for b in depth.bids[:5]
        )
        depth_asks = b"".join(
            struct.pack(cls.DEPTH_LEVEL_FORMAT, a.price, a.quantity, a.orders)
            for a in depth.asks[:5]
        )
        oi_part = struct.pack(cls.OI_PAYLOAD_FORMAT, open_interest)
        return header + quote_part + depth_bids + depth_asks + oi_part

    @classmethod
    def build_disconnect_packet(
        cls, exchange_segment: int, security_id: int, disconnect_code: int = 50
    ) -> bytes:
        header = cls.build_header(
            FeedResponseCode.DISCONNECT, cls.DISCONNECT_PACKET_SIZE, exchange_segment, security_id
        )
        payload = struct.pack(cls.DISCONNECT_PAYLOAD_FORMAT, disconnect_code)
        return header + payload
