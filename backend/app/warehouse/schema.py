"""Typed schemas and data models for historical OHLCV bar store and expired options."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pyarrow as pa
from pydantic import BaseModel, ConfigDict


class BarRecord(BaseModel):
    """Pydantic model representing a single OHLCV bar with open interest."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    exchange_segment: str
    security_id: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    open_interest: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict with UTC-normalized timestamp."""
        ts = (
            self.timestamp
            if self.timestamp.tzinfo is not None
            else self.timestamp.replace(tzinfo=UTC)
        )
        return {
            "timestamp": ts,
            "exchange_segment": self.exchange_segment,
            "security_id": self.security_id,
            "symbol": self.symbol,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": int(self.volume),
            "open_interest": int(self.open_interest),
        }


BAR_SCHEMA_PYARROW = pa.schema(
    [
        ("timestamp", pa.timestamp("ms", tz="UTC")),
        ("exchange_segment", pa.string()),
        ("security_id", pa.string()),
        ("symbol", pa.string()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.int64()),
        ("open_interest", pa.int64()),
    ]
)


def bars_to_arrow_table(bars: list[BarRecord]) -> pa.Table:
    """Convert a sequence of BarRecord models into a standardized PyArrow Table."""
    if not bars:
        return pa.Table.from_arrays(
            [
                pa.array([], type=pa.timestamp("ms", tz="UTC")),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.int64()),
                pa.array([], type=pa.int64()),
            ],
            schema=BAR_SCHEMA_PYARROW,
        )

    timestamps = [
        b.timestamp if b.timestamp.tzinfo is not None else b.timestamp.replace(tzinfo=UTC)
        for b in bars
    ]
    segments = [b.exchange_segment for b in bars]
    security_ids = [b.security_id for b in bars]
    symbols = [b.symbol for b in bars]
    opens = [b.open for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    open_interests = [b.open_interest for b in bars]

    return pa.Table.from_arrays(
        [
            pa.array(timestamps, type=pa.timestamp("ms", tz="UTC")),
            pa.array(segments, type=pa.string()),
            pa.array(security_ids, type=pa.string()),
            pa.array(symbols, type=pa.string()),
            pa.array(opens, type=pa.float64()),
            pa.array(highs, type=pa.float64()),
            pa.array(lows, type=pa.float64()),
            pa.array(closes, type=pa.float64()),
            pa.array(volumes, type=pa.int64()),
            pa.array(open_interests, type=pa.int64()),
        ],
        schema=BAR_SCHEMA_PYARROW,
    )


class OptionBarRecord(BaseModel):
    """Pydantic model representing an option contract bar with Greeks/OI/Spot."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    exchange_segment: str = "NSE_FNO"
    security_id: str
    symbol: str
    underlying_symbol: str
    expiry_date: str
    strike_price: float
    option_type: str  # "CALL" or "PUT"
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    open_interest: int = 0
    implied_volatility: float = 0.0
    spot_price: float = 0.0


OPTION_BAR_SCHEMA_PYARROW = pa.schema(
    [
        ("timestamp", pa.timestamp("ms", tz="UTC")),
        ("exchange_segment", pa.string()),
        ("security_id", pa.string()),
        ("symbol", pa.string()),
        ("underlying_symbol", pa.string()),
        ("expiry_date", pa.string()),
        ("strike_price", pa.float64()),
        ("option_type", pa.string()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.int64()),
        ("open_interest", pa.int64()),
        ("implied_volatility", pa.float64()),
        ("spot_price", pa.float64()),
    ]
)


def option_bars_to_arrow_table(bars: list[OptionBarRecord]) -> pa.Table:
    """Convert a sequence of OptionBarRecord models into a standardized PyArrow Table."""
    if not bars:
        return pa.Table.from_arrays(
            [
                pa.array([], type=pa.timestamp("ms", tz="UTC")),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.int64()),
                pa.array([], type=pa.int64()),
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.float64()),
            ],
            schema=OPTION_BAR_SCHEMA_PYARROW,
        )

    timestamps = [
        b.timestamp if b.timestamp.tzinfo is not None else b.timestamp.replace(tzinfo=UTC)
        for b in bars
    ]

    return pa.Table.from_arrays(
        [
            pa.array(timestamps, type=pa.timestamp("ms", tz="UTC")),
            pa.array([b.exchange_segment for b in bars], type=pa.string()),
            pa.array([b.security_id for b in bars], type=pa.string()),
            pa.array([b.symbol for b in bars], type=pa.string()),
            pa.array([b.underlying_symbol for b in bars], type=pa.string()),
            pa.array([b.expiry_date for b in bars], type=pa.string()),
            pa.array([b.strike_price for b in bars], type=pa.float64()),
            pa.array([b.option_type for b in bars], type=pa.string()),
            pa.array([b.open for b in bars], type=pa.float64()),
            pa.array([b.high for b in bars], type=pa.float64()),
            pa.array([b.low for b in bars], type=pa.float64()),
            pa.array([b.close for b in bars], type=pa.float64()),
            pa.array([b.volume for b in bars], type=pa.int64()),
            pa.array([b.open_interest for b in bars], type=pa.int64()),
            pa.array([b.implied_volatility for b in bars], type=pa.float64()),
            pa.array([b.spot_price for b in bars], type=pa.float64()),
        ],
        schema=OPTION_BAR_SCHEMA_PYARROW,
    )
