"""SQLAlchemy tables and Pydantic schemas for the Strategy Builder Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BOOLEAN,
    INTEGER,
    JSON,
    TEXT,
    TIMESTAMP,
    Column,
    ForeignKey,
    MetaData,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

# 1. Master Strategy Configurations Table
strategy_configs_table = Table(
    "strategy_configs",
    metadata,
    Column("id", INTEGER, primary_key=True, autoincrement=True),
    Column("name", TEXT, nullable=False),
    Column("description", TEXT, nullable=True),
    Column("strategy_type", TEXT, nullable=False),
    Column("current_version", INTEGER, nullable=False, default=1),
    Column("is_active", BOOLEAN, nullable=False, default=True),
    Column("config_json", JSON().with_variant(JSONB, "postgresql"), nullable=False),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
)

# 2. Strategy Versions History Table
strategy_versions_table = Table(
    "strategy_versions",
    metadata,
    Column("id", INTEGER, primary_key=True, autoincrement=True),
    Column(
        "strategy_id",
        INTEGER,
        ForeignKey("strategy_configs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("version", INTEGER, nullable=False),
    Column("change_summary", TEXT, nullable=True),
    Column("config_json", JSON().with_variant(JSONB, "postgresql"), nullable=False),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    UniqueConstraint("strategy_id", "version", name="uq_strategy_version"),
)


# --- 4-Part Modular Pydantic Schemas ---


class TradingSession(BaseModel):
    """Trading session timings in HH:MM:SS format."""

    start_time: str = "09:16:00"
    no_new_entries_after: str = "14:30:00"
    force_square_off: str = "15:15:00"


class StrikeSelection(BaseModel):
    """Options strike selection rules."""

    mode: Literal["ATM_OFFSET", "DELTA", "PREMIUM_RANGE"] = "ATM_OFFSET"
    offset: int = 0  # 0 for ATM, +1 for OTM/ITM offset, -1 etc.
    target_delta: float | None = None
    min_premium: float | None = None
    max_premium: float | None = None


class Part1Scope(BaseModel):
    """Part 1: Instrument Scope & Strike Selection."""

    source_type: Literal["SCREENER", "WATCHLIST", "INDEX_OPTION", "STOCK_OPTION", "MCX"] = (
        "INDEX_OPTION"
    )
    screener_config_id: int | None = None
    fallback_watchlist: list[str] = Field(default_factory=list)
    underlying_symbol: str | None = None
    option_right: Literal["CE", "PE", "BOTH"] | None = None
    expiry_type: Literal["CURRENT_WEEK", "NEXT_WEEK", "MONTHLY"] = "CURRENT_WEEK"
    strike_selection: StrikeSelection = Field(default_factory=StrikeSelection)
    trading_session: TradingSession = Field(default_factory=TradingSession)


class StrategyCondition(BaseModel):
    """Individual entry trigger condition in Part 2."""

    price_reference: Literal["SPOT", "OPTION_PREMIUM"] = "SPOT"
    timeframe: str = "15min"
    indicator: str | None = None  # RSI, EMA, SMA, MACD, BB, VWAP, VOLUME_RATIO, ATR, Supertrend
    pattern: str | None = None  # OPEN_EQ_HIGH, OPEN_EQ_LOW, INSIDE_BAR, BULLISH_ENGULFING, etc.
    period: int | None = None
    fast: int | None = None
    slow: int | None = None
    signal: int | None = None
    std_dev: float | None = None
    multiplier: float | None = None
    avg_period: int | None = None
    operator: str | None = None  # >, <, >=, <=, =, close_above, crosses_above, etc.
    value: float | int | list[float] | list[int] | str | None = None


class Part2Entry(BaseModel):
    """Part 2: Entry Rules & Trigger Conditions."""

    direction: Literal["LONG", "SHORT"] = "LONG"
    trigger_timeframe: str = "15min"
    logic: Literal["AND", "OR"] = "AND"
    conditions: list[StrategyCondition] = Field(default_factory=list)


class Part3Stoploss(BaseModel):
    """Part 3: Stop-Loss Rules."""

    sl_reference: Literal["SPOT", "OPTION_PREMIUM"] = "SPOT"
    sl_type: Literal["PERCENTAGE", "POINTS", "CANDLE_LOW", "CANDLE_HIGH", "INDICATOR"] = (
        "PERCENTAGE"
    )
    percentage_val: float | None = None
    points_val: float | None = None
    candle_lookback: int = 1
    buffer_percentage: float = 0.0
    indicator: str | None = None
    indicator_period: int | None = None


class TargetRule(BaseModel):
    """Multi-stage exit target rule."""

    target_number: int = 1
    reward_risk_ratio: float | None = None
    percentage_gain: float | None = None
    points_gain: float | None = None
    exit_lots_percentage: float = 50.0  # Percentage of remaining position to exit


class TrailingSLRule(BaseModel):
    """Trailing stop-loss configuration."""

    enabled: bool = False
    mode: Literal["SPOT_POINTS", "SPOT_PERCENTAGE", "OPTION_POINTS", "OPTION_PERCENTAGE"] = (
        "SPOT_POINTS"
    )
    trail_after_target: int = 1
    step_points: float | None = None
    step_percentage: float | None = None


class Part4Exit(BaseModel):
    """Part 4: Exit Targets & Trailing Stop-Loss Sizing."""

    exit_reference: Literal["SPOT", "OPTION_PREMIUM"] = "SPOT"
    targets: list[TargetRule] = Field(default_factory=list)
    trailing_sl: TrailingSLRule = Field(default_factory=TrailingSLRule)


class StrategyDefinition(BaseModel):
    """Complete 4-Part Strategy Definition Schema."""

    strategy_type: Literal["STOCK", "OPTION", "MCX_FUTURES", "MCX_OPTION"] = "STOCK"
    name: str = Field(min_length=1)
    version: int = 1
    description: str | None = None
    part_1_scope: Part1Scope = Field(default_factory=Part1Scope)
    part_2_entry: Part2Entry = Field(default_factory=Part2Entry)
    part_3_stoploss: Part3Stoploss = Field(default_factory=Part3Stoploss)
    part_4_exit: Part4Exit = Field(default_factory=Part4Exit)


# --- API Request & Response Schemas ---


class StrategyConfigCreate(BaseModel):
    """Payload to create a new strategy."""

    name: str = Field(min_length=1)
    description: str | None = None
    strategy_type: Literal["STOCK", "OPTION", "MCX_FUTURES", "MCX_OPTION"] = "STOCK"
    config_json: dict[str, Any]
    is_active: bool = True


class StrategyConfigUpdate(BaseModel):
    """Payload to update an existing strategy."""

    name: str | None = None
    description: str | None = None
    strategy_type: Literal["STOCK", "OPTION", "MCX_FUTURES", "MCX_OPTION"] | None = None
    config_json: dict[str, Any] | None = None
    is_active: bool | None = None
    change_summary: str | None = None


class StrategyConfigRecord(BaseModel):
    """Pydantic representation of a saved strategy config."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    strategy_type: str
    current_version: int
    is_active: bool
    config_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class StrategyVersionRecord(BaseModel):
    """Pydantic representation of a strategy version snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    version: int
    change_summary: str | None = None
    config_json: dict[str, Any]
    created_at: datetime


class PythonExportResponse(BaseModel):
    """Response payload containing generated standalone Python script."""

    strategy_id: int
    strategy_name: str
    version: int
    filename: str
    code_content: str
