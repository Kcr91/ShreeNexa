"""SQLAlchemy models and table schemas for the Data Engine & Market Storage Pipeline."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BIGINT,
    DATE,
    INTEGER,
    NUMERIC,
    TEXT,
    TIMESTAMP,
    Column,
    MetaData,
    PrimaryKeyConstraint,
    Table,
)

metadata = MetaData()

# 1. Equity & Index OHLCV Table (Partitioned by datetime_ist range)
mkt_ohlcv_equity_table = Table(
    "mkt_ohlcv_equity",
    metadata,
    Column("security_id", TEXT, nullable=False),
    Column("exchange_segment", TEXT, nullable=False, default="NSE_EQ"),
    Column("symbol", TEXT, nullable=False),
    Column("datetime_ist", TIMESTAMP(timezone=True), nullable=False),
    Column("open", NUMERIC(12, 4), nullable=False),
    Column("high", NUMERIC(12, 4), nullable=False),
    Column("low", NUMERIC(12, 4), nullable=False),
    Column("close", NUMERIC(12, 4), nullable=False),
    Column("volume", BIGINT, nullable=False, default=0),
    PrimaryKeyConstraint(
        "exchange_segment", "security_id", "datetime_ist", name="pk_mkt_ohlcv_equity"
    ),
)

# 2. Futures OHLCV Table
mkt_ohlcv_futures_table = Table(
    "mkt_ohlcv_futures",
    metadata,
    Column("security_id", TEXT, nullable=False),
    Column("exchange_segment", TEXT, nullable=False, default="NSE_FNO"),
    Column("symbol", TEXT, nullable=False),
    Column("datetime_ist", TIMESTAMP(timezone=True), nullable=False),
    Column("open", NUMERIC(12, 4), nullable=False),
    Column("high", NUMERIC(12, 4), nullable=False),
    Column("low", NUMERIC(12, 4), nullable=False),
    Column("close", NUMERIC(12, 4), nullable=False),
    Column("volume", BIGINT, nullable=False, default=0),
    Column("oi", BIGINT, nullable=False, default=0),
    Column("underlying_spot", NUMERIC(12, 4), nullable=True),
    PrimaryKeyConstraint(
        "exchange_segment", "security_id", "datetime_ist", name="pk_mkt_ohlcv_futures"
    ),
)

# 3. Options OHLCV Table
mkt_ohlcv_options_table = Table(
    "mkt_ohlcv_options",
    metadata,
    Column("security_id", TEXT, nullable=False),
    Column("exchange_segment", TEXT, nullable=False, default="NSE_FNO"),
    Column("symbol", TEXT, nullable=False),
    Column("datetime_ist", TIMESTAMP(timezone=True), nullable=False),
    Column("open", NUMERIC(12, 4), nullable=False),
    Column("high", NUMERIC(12, 4), nullable=False),
    Column("low", NUMERIC(12, 4), nullable=False),
    Column("close", NUMERIC(12, 4), nullable=False),
    Column("volume", BIGINT, nullable=False, default=0),
    Column("oi", BIGINT, nullable=False, default=0),
    Column("iv", NUMERIC(8, 4), nullable=True),
    Column("underlying_spot", NUMERIC(12, 4), nullable=True),
    PrimaryKeyConstraint(
        "exchange_segment", "security_id", "datetime_ist", name="pk_mkt_ohlcv_options"
    ),
)

# 4. Download / Sync State Tracker Table
mkt_download_state_table = Table(
    "mkt_download_state",
    metadata,
    Column("security_id", TEXT, nullable=False),
    Column("exchange_segment", TEXT, nullable=False),
    Column("symbol", TEXT, nullable=False),
    Column("instrument_type", TEXT, nullable=False),
    Column("last_candle_ts", TIMESTAMP(timezone=True), nullable=True),
    Column("last_sync_at", TIMESTAMP(timezone=True), nullable=True),
    Column("sync_status", TEXT, nullable=False, default="PENDING"),
    Column("error_message", TEXT, nullable=True),
    Column("total_candles", BIGINT, nullable=False, default=0),
    Column("api_requests_used", INTEGER, nullable=False, default=0),
    PrimaryKeyConstraint("exchange_segment", "security_id", name="pk_mkt_download_state"),
)

# 5. API Daily Quota Ledger Table
mkt_api_quota_table = Table(
    "mkt_api_quota",
    metadata,
    Column("date", DATE, primary_key=True, default=lambda: datetime.now(UTC).date()),
    Column("daily_limit", INTEGER, nullable=False, default=100000),
    Column("used_historical", INTEGER, nullable=False, default=0),
    Column("used_live", INTEGER, nullable=False, default=0),
    Column("reserved_live", INTEGER, nullable=False, default=5000),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
)

# 6. Segment Catalog Table
mkt_segment_table = Table(
    "mkt_segment",
    metadata,
    Column("code", TEXT, primary_key=True),
    Column("name", TEXT, nullable=False),
    Column("category", TEXT, nullable=False),  # INDEX, SECTOR, EQUITY, COMMODITY
    Column("description", TEXT, nullable=True),
)

mkt_segment_constituent_table = Table(
    "mkt_segment_constituent",
    metadata,
    Column("segment_code", TEXT, nullable=False),
    Column("symbol", TEXT, nullable=False),
    Column("weight", NUMERIC(8, 4), nullable=True),
    PrimaryKeyConstraint("segment_code", "symbol", name="pk_mkt_segment_constituent"),
)


# Pydantic Schemas
class OHLCVRecord(BaseModel):
    """Pydantic representation of an OHLCV candle."""

    model_config = ConfigDict(from_attributes=True)

    security_id: str
    exchange_segment: str
    symbol: str
    datetime_ist: datetime
    open: Decimal | float
    high: Decimal | float
    low: Decimal | float
    close: Decimal | float
    volume: int = 0
    oi: int | None = None
    iv: Decimal | float | None = None
    underlying_spot: Decimal | float | None = None


class DownloadStateRecord(BaseModel):
    """Pydantic model for download/sync state tracking."""

    model_config = ConfigDict(from_attributes=True)

    security_id: str
    exchange_segment: str
    symbol: str
    instrument_type: str
    last_candle_ts: datetime | None = None
    last_sync_at: datetime | None = None
    sync_status: str = "PENDING"
    error_message: str | None = None
    total_candles: int = 0
    api_requests_used: int = 0


class ApiQuotaRecord(BaseModel):
    """Pydantic model for daily API quota budget."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    daily_limit: int = 100000
    used_historical: int = 0
    used_live: int = 0
    reserved_live: int = 5000
    available_historical: int = 95000
    updated_at: datetime | None = None


class SegmentSummary(BaseModel):
    """Pydantic model for segment summary with constituent count."""

    code: str
    name: str
    category: str
    description: str | None = None
    constituent_count: int = 0
