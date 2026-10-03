"""SQLAlchemy tables and Pydantic schemas for the Dynamic Screener Engine."""

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
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

# 1. Saved Screener Configurations Table
screener_configs_table = Table(
    "screener_configs",
    metadata,
    Column("id", INTEGER, primary_key=True, autoincrement=True),
    Column("name", TEXT, nullable=False),
    Column("description", TEXT, nullable=True),
    Column("universe_filter", TEXT, nullable=False, default="FNO_208"),
    Column("condition_tree", JSON().with_variant(JSONB, "postgresql"), nullable=False),
    Column("is_strategy_mode", BOOLEAN, nullable=False, default=False),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
)

# 2. Screener Run History Table
screener_results_table = Table(
    "screener_results",
    metadata,
    Column("id", INTEGER, primary_key=True, autoincrement=True),
    Column(
        "config_id", INTEGER, ForeignKey("screener_configs.id", ondelete="SET NULL"), nullable=True
    ),
    Column("run_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)),
    Column("matched_symbols", JSON().with_variant(JSONB, "postgresql"), nullable=False),
    Column("total_scanned", INTEGER, nullable=False, default=0),
    Column("total_matched", INTEGER, nullable=False, default=0),
    Column("run_duration_ms", INTEGER, nullable=False, default=0),
    Column("result_snapshot", JSON().with_variant(JSONB, "postgresql"), nullable=False),
)


# Pydantic Schemas for Condition Tree & API
class ConditionLeaf(BaseModel):
    """Leaf node in the condition tree evaluating one technical rule."""

    indicator: str  # RSI, EMA, SMA, MACD, BB, VWAP, ATR, Supertrend, etc.
    timeframe: str = "daily"  # 1min, 5min, 15min, 1h, 4h, daily, weekly, monthly
    operator: str  # >, <, >=, <=, =, between, close_above, crosses_above, etc.
    value: float | int | list[float] | list[int] | str | None = None
    period: int | None = None
    fast: int | None = None
    slow: int | None = None
    signal: int | None = None
    std_dev: float | None = None
    multiplier: float | None = None
    avg_period: int | None = None


class ConditionGroup(BaseModel):
    """Group node representing AND / OR logical branches."""

    logic: Literal["AND", "OR"] = "AND"
    conditions: list[ConditionGroup | ConditionLeaf] = Field(default_factory=list)


class ScreenerConfigCreate(BaseModel):
    """Payload to create a new screener configuration."""

    name: str = Field(min_length=1, description="Unique screener name")
    description: str | None = None
    universe_filter: str = Field(
        default="FNO_208", description="Target segment or index universe code"
    )
    condition_tree: dict[str, Any] = Field(description="Nested AND/OR condition tree")
    is_strategy_mode: bool = False


class ScreenerConfigUpdate(BaseModel):
    """Payload to update an existing screener configuration."""

    name: str | None = None
    description: str | None = None
    universe_filter: str | None = None
    condition_tree: dict[str, Any] | None = None
    is_strategy_mode: bool | None = None


class ScreenerConfigRecord(BaseModel):
    """Pydantic representation of a saved screener config."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    universe_filter: str
    condition_tree: dict[str, Any]
    is_strategy_mode: bool
    created_at: datetime
    updated_at: datetime


class MatchedStockDetail(BaseModel):
    """Detailed screener match result for a single stock."""

    symbol: str
    display_name: str | None = None
    segments: list[str] = Field(default_factory=list)
    last_close: float
    change_pct: float = 0.0
    volume: int = 0
    indicator_values: dict[str, Any] = Field(default_factory=dict)
    conditions_met: list[str] = Field(default_factory=list)


class DynamicScreenerRunResponse(BaseModel):
    """Response payload returned when a screener is executed."""

    run_id: int | None = None
    config_id: int | None = None
    config_name: str
    universe: str
    total_scanned: int
    total_matched: int
    duration_ms: int
    run_at: datetime
    results: list[MatchedStockDetail]
