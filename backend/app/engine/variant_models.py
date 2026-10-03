"""SQLAlchemy tables and Pydantic schemas for Feature 4: Multi-Variant Engine & Live Tradebook."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BOOLEAN,
    INTEGER,
    JSON,
    NUMERIC,
    TEXT,
    TIMESTAMP,
    Column,
    ForeignKey,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.strategy.models import metadata

# 1. Reusable Tracking Condition Library Table
variant_library_table = Table(
    "variant_library_conditions",
    metadata,
    Column("id", INTEGER, primary_key=True, autoincrement=True),
    Column("name", TEXT, nullable=False),
    Column("description", TEXT, nullable=True),
    Column("category", TEXT, nullable=False),
    Column("condition_config", JSON().with_variant(JSONB, "postgresql"), nullable=False),
    Column("is_built_in", BOOLEAN, nullable=False, default=False),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
)

# 2. Master Multi-Variant Execution Runs Table
variant_runs_table = Table(
    "variant_runs",
    metadata,
    Column("run_id", INTEGER, primary_key=True, autoincrement=True),
    Column(
        "strategy_id", INTEGER, ForeignKey("strategy_configs.id", ondelete="CASCADE"), nullable=True
    ),
    Column("run_name", TEXT, nullable=False, default="Multi-Variant Run"),
    Column("run_type", TEXT, nullable=False, default="BACKTEST"),
    Column("start_time", TIMESTAMP(timezone=True), nullable=False),
    Column("end_time", TIMESTAMP(timezone=True), nullable=False),
    Column("total_signals", INTEGER, nullable=False, default=0),
    Column("total_variants_run", INTEGER, nullable=False, default=1),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
)

# 3. Detailed Variant Trade Logs Table
variant_trades_table = Table(
    "variant_trades",
    metadata,
    Column("id", INTEGER, primary_key=True, autoincrement=True),
    Column(
        "run_id", INTEGER, ForeignKey("variant_runs.run_id", ondelete="CASCADE"), nullable=False
    ),
    Column("variant_name", TEXT, nullable=False),
    Column("symbol", TEXT, nullable=False),
    Column("signal_type", TEXT, nullable=False),
    Column("entry_time", TIMESTAMP(timezone=True), nullable=False),
    Column("entry_spot_price", NUMERIC(12, 4), nullable=True),
    Column("entry_option_price", NUMERIC(12, 4), nullable=True),
    Column("entry_india_vix", NUMERIC(6, 2), nullable=True),
    Column("entry_option_iv", NUMERIC(6, 2), nullable=True),
    Column("entry_delta", NUMERIC(6, 3), nullable=True),
    Column("entry_gamma", NUMERIC(6, 4), nullable=True),
    Column("entry_theta", NUMERIC(8, 2), nullable=True),
    Column("entry_vega", NUMERIC(8, 2), nullable=True),
    Column("exit_time", TIMESTAMP(timezone=True), nullable=True),
    Column("exit_spot_price", NUMERIC(12, 4), nullable=True),
    Column("exit_option_price", NUMERIC(12, 4), nullable=True),
    Column("exit_india_vix", NUMERIC(6, 2), nullable=True),
    Column("exit_option_iv", NUMERIC(6, 2), nullable=True),
    Column("vix_change", NUMERIC(6, 2), nullable=True),
    Column("iv_change", NUMERIC(6, 2), nullable=True),
    Column("exit_reason", TEXT, nullable=False),
    Column("quantity", INTEGER, nullable=False, default=1),
    Column("realized_pnl", NUMERIC(12, 2), nullable=False, default=0.00),
    Column("max_favorable_excursion", NUMERIC(12, 4), nullable=True),
    Column("max_adverse_excursion", NUMERIC(12, 4), nullable=True),
)

# 4. Real-Money Live Tradebook Table
live_tradebook_table = Table(
    "live_tradebook",
    metadata,
    Column("trade_id", INTEGER, primary_key=True, autoincrement=True),
    Column("dhan_order_id", TEXT, unique=True, nullable=False),
    Column(
        "strategy_id",
        INTEGER,
        ForeignKey("strategy_configs.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("symbol", TEXT, nullable=False),
    Column("signal_type", TEXT, nullable=False),
    Column("fill_time", TIMESTAMP(timezone=True), nullable=False),
    Column("buy_price", NUMERIC(12, 4), nullable=False),
    Column("sell_price", NUMERIC(12, 4), nullable=True),
    Column("quantity", INTEGER, nullable=False),
    Column("entry_vix", NUMERIC(6, 2), nullable=True),
    Column("exit_vix", NUMERIC(6, 2), nullable=True),
    Column("entry_iv", NUMERIC(6, 2), nullable=True),
    Column("exit_iv", NUMERIC(6, 2), nullable=True),
    Column("exit_reason", TEXT, nullable=True),
    Column("realized_pnl", NUMERIC(12, 2), nullable=True),
    Column("brokerage_charges", NUMERIC(10, 2), nullable=False, default=0.00),
    Column("stt_taxes", NUMERIC(10, 2), nullable=False, default=0.00),
    Column("slippage_amount", NUMERIC(10, 2), nullable=False, default=0.00),
    Column(
        "created_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
)


# --- Pydantic Schemas ---


class LibraryConditionCreate(BaseModel):
    """Payload to create a reusable tracking condition in the library."""

    name: str = Field(min_length=1)
    description: str | None = None
    category: Literal[
        "SL_VARIANT",
        "TARGET_VARIANT",
        "PARTIAL_EXIT",
        "TRAILING_SL",
        "TIME_EXIT",
        "INDICATOR_EXIT",
    ] = "SL_VARIANT"
    condition_config: dict[str, Any]
    is_built_in: bool = False


class LibraryConditionUpdate(BaseModel):
    """Payload to update an existing library condition."""

    name: str | None = None
    description: str | None = None
    category: (
        Literal[
            "SL_VARIANT",
            "TARGET_VARIANT",
            "PARTIAL_EXIT",
            "TRAILING_SL",
            "TIME_EXIT",
            "INDICATOR_EXIT",
        ]
        | None
    ) = None
    condition_config: dict[str, Any] | None = None


class LibraryConditionRecord(BaseModel):
    """Pydantic representation of a library condition."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    category: str
    condition_config: dict[str, Any]
    is_built_in: bool
    created_at: datetime
    updated_at: datetime


class SelectedVariantOverride(BaseModel):
    """Specification of an active tracking variation attached to a run."""

    condition_id: int | None = None
    name: str
    override_params: dict[str, Any] = Field(default_factory=dict)


class MultiVariantRunRequest(BaseModel):
    """Payload to trigger a multi-variant backtest or paper run."""

    strategy_id: int
    run_name: str = "Multi-Variant Backtest Run"
    start_date: str = "2026-09-01"
    end_date: str = "2026-09-30"
    capital: float = 500000.0
    selected_variations: list[SelectedVariantOverride] = Field(default_factory=list)


class VariantTradeRecord(BaseModel):
    """Representation of an individual variant trade outcome."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    variant_name: str
    symbol: str
    signal_type: str
    entry_time: datetime
    entry_spot_price: float | None = None
    entry_option_price: float | None = None
    entry_india_vix: float | None = None
    entry_option_iv: float | None = None
    entry_delta: float | None = None
    entry_gamma: float | None = None
    entry_theta: float | None = None
    entry_vega: float | None = None
    exit_time: datetime | None = None
    exit_spot_price: float | None = None
    exit_option_price: float | None = None
    exit_india_vix: float | None = None
    exit_option_iv: float | None = None
    vix_change: float | None = None
    iv_change: float | None = None
    exit_reason: str
    quantity: int
    realized_pnl: float
    max_favorable_excursion: float | None = None
    max_adverse_excursion: float | None = None


class VariantRankingItem(BaseModel):
    """Summary metrics for a specific variant in a multi-variant run."""

    variant_name: str
    is_baseline: bool
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_realized_pnl: float
    net_pnl_after_costs: float
    profit_factor: float
    max_drawdown_pct: float
    avg_trade_pnl: float
    avg_vix_at_entry: float
    avg_iv_expansion: float


class MultiVariantRunResponse(BaseModel):
    """Response returned when a multi-variant execution completes."""

    run_id: int
    strategy_id: int
    strategy_name: str
    total_signals: int
    total_variants_run: int
    rankings: list[VariantRankingItem]
    trades: list[VariantTradeRecord]


class LiveTradebookCreate(BaseModel):
    """Payload to log a live order trade in the tradebook."""

    dhan_order_id: str
    strategy_id: int | None = None
    symbol: str
    signal_type: str
    fill_time: datetime
    buy_price: float
    sell_price: float | None = None
    quantity: int
    entry_vix: float | None = None
    exit_vix: float | None = None
    entry_iv: float | None = None
    exit_iv: float | None = None
    exit_reason: str | None = None
    realized_pnl: float | None = None
    brokerage_charges: float = 20.0
    stt_taxes: float = 0.0
    slippage_amount: float = 0.0


class LiveTradebookRecord(BaseModel):
    """Pydantic model of a live tradebook entry."""

    model_config = ConfigDict(from_attributes=True)

    trade_id: int
    dhan_order_id: str
    strategy_id: int | None = None
    symbol: str
    signal_type: str
    fill_time: datetime
    buy_price: float
    sell_price: float | None = None
    quantity: int
    entry_vix: float | None = None
    exit_vix: float | None = None
    entry_iv: float | None = None
    exit_iv: float | None = None
    exit_reason: str | None = None
    realized_pnl: float | None = None
    brokerage_charges: float
    stt_taxes: float
    slippage_amount: float
    created_at: datetime


class VixHeatmapCell(BaseModel):
    """One cell in the VIX vs IV performance heatmap."""

    vix_bucket: str  # "<12", "12-15", "15-18", "18-22", ">22"
    iv_bucket: str  # "<20%", "20-30%", "30-40%", ">40%"
    trade_count: int
    win_rate_pct: float
    total_pnl: float
    avg_pnl: float


class VixHeatmapResponse(BaseModel):
    """Heatmap matrix response."""

    profitable_vix_range: str
    profitable_iv_zone: str
    cells: list[VixHeatmapCell]
