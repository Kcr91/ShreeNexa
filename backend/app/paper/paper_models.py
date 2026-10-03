"""SQLAlchemy tables and Pydantic schemas for Feature 5: Paper Trading Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    INTEGER,
    NUMERIC,
    TEXT,
    TIMESTAMP,
    Column,
    ForeignKey,
    Table,
)

from app.strategy.models import metadata

# 1. Active Paper Trading Sessions Table
paper_sessions_table = Table(
    "paper_sessions",
    metadata,
    Column("session_id", INTEGER, primary_key=True, autoincrement=True),
    Column(
        "strategy_id",
        INTEGER,
        ForeignKey("strategy_configs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("session_name", TEXT, nullable=False),
    Column("status", TEXT, nullable=False, default="RUNNING"),
    Column("initial_capital", NUMERIC(12, 2), nullable=False, default=500000.00),
    Column("current_capital", NUMERIC(12, 2), nullable=False, default=500000.00),
    Column(
        "start_time", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column("end_time", TIMESTAMP(timezone=True), nullable=True),
    Column("readiness_score", NUMERIC(5, 2), nullable=False, default=0.00),
)

# 2. Open Paper Positions Table
paper_positions_table = Table(
    "paper_positions",
    metadata,
    Column("position_id", INTEGER, primary_key=True, autoincrement=True),
    Column(
        "session_id",
        INTEGER,
        ForeignKey("paper_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("symbol", TEXT, nullable=False),
    Column("signal_type", TEXT, nullable=False),
    Column("entry_time", TIMESTAMP(timezone=True), nullable=False),
    Column("entry_price", NUMERIC(12, 4), nullable=False),
    Column("current_price", NUMERIC(12, 4), nullable=True),
    Column("quantity", INTEGER, nullable=False),
    Column("unrealized_pnl", NUMERIC(12, 2), nullable=False, default=0.00),
    Column("active_sl", NUMERIC(12, 4), nullable=True),
    Column("active_target", NUMERIC(12, 4), nullable=True),
    Column(
        "updated_at", TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
)

# 3. Paper Trade History Table
paper_tradebook_table = Table(
    "paper_tradebook",
    metadata,
    Column("trade_id", INTEGER, primary_key=True, autoincrement=True),
    Column(
        "session_id",
        INTEGER,
        ForeignKey("paper_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("symbol", TEXT, nullable=False),
    Column("signal_type", TEXT, nullable=False),
    Column("entry_time", TIMESTAMP(timezone=True), nullable=False),
    Column("exit_time", TIMESTAMP(timezone=True), nullable=True),
    Column("entry_price", NUMERIC(12, 4), nullable=False),
    Column("exit_price", NUMERIC(12, 4), nullable=True),
    Column("quantity", INTEGER, nullable=False),
    Column("realized_pnl", NUMERIC(12, 2), nullable=False, default=0.00),
    Column("exit_reason", TEXT, nullable=True),
    Column("entry_vix", NUMERIC(6, 2), nullable=True),
    Column("exit_vix", NUMERIC(6, 2), nullable=True),
    Column("entry_iv", NUMERIC(6, 2), nullable=True),
    Column("exit_iv", NUMERIC(6, 2), nullable=True),
    Column("simulated_slippage", NUMERIC(10, 2), nullable=False, default=0.00),
    Column("simulated_brokerage", NUMERIC(10, 2), nullable=False, default=0.00),
)


# --- Pydantic Schemas ---


class PaperSessionCreate(BaseModel):
    """Payload to launch a new paper trading session."""

    strategy_id: int
    session_name: str = Field(min_length=1)
    initial_capital: float = 500000.00


class PaperPositionRecord(BaseModel):
    """Pydantic representation of an open paper position."""

    model_config = ConfigDict(from_attributes=True)

    position_id: int
    session_id: int
    symbol: str
    signal_type: str
    entry_time: datetime
    entry_price: float
    current_price: float | None = None
    quantity: int
    unrealized_pnl: float
    active_sl: float | None = None
    active_target: float | None = None
    updated_at: datetime


class PaperTradeRecord(BaseModel):
    """Pydantic representation of a closed paper trade."""

    model_config = ConfigDict(from_attributes=True)

    trade_id: int
    session_id: int
    symbol: str
    signal_type: str
    entry_time: datetime
    exit_time: datetime | None = None
    entry_price: float
    exit_price: float | None = None
    quantity: int
    realized_pnl: float
    exit_reason: str | None = None
    entry_vix: float | None = None
    exit_vix: float | None = None
    entry_iv: float | None = None
    exit_iv: float | None = None
    simulated_slippage: float
    simulated_brokerage: float


class PaperSessionRecord(BaseModel):
    """Pydantic model of a paper trading session with summary stats."""

    model_config = ConfigDict(from_attributes=True)

    session_id: int
    strategy_id: int
    session_name: str
    status: Literal["RUNNING", "PAUSED", "COMPLETED", "SWITCHED_TO_LIVE"]
    initial_capital: float
    current_capital: float
    start_time: datetime
    end_time: datetime | None = None
    readiness_score: float
    total_trades_count: int = 0
    open_positions_count: int = 0
    total_realized_pnl: float = 0.00
    total_unrealized_pnl: float = 0.00


class QuickCompareMetricItem(BaseModel):
    """Row in the Quick Live Paper vs Backtest Expected comparison card."""

    metric: str
    live_paper_val: str
    backtest_expected_val: str
    status: Literal["ON_TRACK", "STABLE", "SAFE", "MATCH", "WARNING", "DIVERGENT"]
    badge_label: str


class QuickCompareResponse(BaseModel):
    """Quick comparison card response for strategy inspection."""

    strategy_id: int
    strategy_name: str
    session_id: int
    execution_mode: str
    metrics: list[QuickCompareMetricItem]
    open_positions: list[PaperPositionRecord]
    shadow_leaderboard: list[dict[str, Any]]


class ReadinessScoreBreakdown(BaseModel):
    """Detailed breakdown of the 0-100% Go/No-Go Readiness Score."""

    pnl_match_score: float  # Weight 40%
    win_rate_stability_score: float  # Weight 30%
    drawdown_safety_score: float  # Weight 20%
    sample_size_weight_score: float  # Weight 10%
    total_readiness_score: float
    verdict: Literal["READY_FOR_LIVE", "NEEDS_FURTHER_VALIDATION"]
    verdict_message: str


class DriftAnalysisResponse(BaseModel):
    """Deep-dive drift analytics and readiness score response."""

    session_id: int
    strategy_name: str
    paper_win_rate: float
    backtest_win_rate: float
    win_rate_drift_pct: float
    paper_max_drawdown_pct: float
    backtest_max_drawdown_pct: float
    slippage_latency_cost_total: float
    total_paper_trades: int
    readiness: ReadinessScoreBreakdown


class SwitchToLiveResponse(BaseModel):
    """Response returned when a strategy is switched to real-money Live Trading."""

    strategy_id: int
    strategy_name: str
    previous_mode: str = "PAPER"
    current_mode: str = "LIVE"
    switched_at: datetime
    status: str
    message: str


# Rebuild forward-referenced Pydantic models
QuickCompareResponse.model_rebuild()
DriftAnalysisResponse.model_rebuild()
PaperSessionRecord.model_rebuild()
