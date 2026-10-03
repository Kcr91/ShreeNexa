"""SQLAlchemy and Pydantic data models for Feature 6: Live Trading & Safety Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.engine.variant_models import live_tradebook_table
from app.strategy.models import metadata

__all__ = [
    "LiveKillSwitchRequest",
    "LiveKillSwitchResponse",
    "LivePositionRecord",
    "LivePositionsResponse",
    "LiveReconcileResponse",
    "LiveRiskSettingsRead",
    "LiveRiskSettingsUpdate",
    "LiveSquareOffResponse",
    "LiveSystemStatusResponse",
    "LiveTradebookItem",
    "LiveTradebookResponse",
    "live_risk_settings_table",
    "live_safety_events_table",
    "live_tradebook_table",
]

# 1. Live Risk Settings Table
live_risk_settings_table = Table(
    "live_risk_settings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("max_daily_loss_pct", Numeric(5, 2), nullable=False, default=3.00),
    Column("max_trade_exposure_pct", Numeric(5, 2), nullable=False, default=10.00),
    Column("max_concurrent_trades", Integer, nullable=False, default=5),
    Column("circuit_buffer_pct", Numeric(5, 2), nullable=False, default=0.50),
    Column("kill_switch_active", Boolean, nullable=False, default=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# 3. Live Safety Audit Events Table
live_safety_events_table = Table(
    "live_safety_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_type", String(50), nullable=False),
    Column("description", Text, nullable=False),
    Column(
        "metadata_json",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------


class LiveRiskSettingsRead(BaseModel):
    id: int = 1
    max_daily_loss_pct: float = Field(default=3.0, description="Max daily loss % before auto-kill")
    max_trade_exposure_pct: float = Field(
        default=10.0, description="Max single trade capital allocation %"
    )
    max_concurrent_trades: int = Field(
        default=5, description="Max active concurrent open positions"
    )
    circuit_buffer_pct: float = Field(
        default=0.5, description="Upper/lower circuit filter buffer %"
    )
    kill_switch_active: bool = Field(default=False, description="Emergency kill switch state")
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LiveRiskSettingsUpdate(BaseModel):
    max_daily_loss_pct: float | None = Field(default=None, ge=0.5, le=50.0)
    max_trade_exposure_pct: float | None = Field(default=None, ge=1.0, le=100.0)
    max_concurrent_trades: int | None = Field(default=None, ge=1, le=50)
    circuit_buffer_pct: float | None = Field(default=None, ge=0.1, le=5.0)
    kill_switch_active: bool | None = None


class LiveSystemStatusResponse(BaseModel):
    status: Literal["ACTIVE", "HALTED_BY_KILL_SWITCH", "MARKET_CLOSED"]
    dhan_api_connected: bool
    dhan_client_id: str
    daily_realized_pnl: float
    daily_unrealized_pnl: float
    total_daily_pnl: float
    max_daily_loss_limit_inr: float
    open_positions_count: int
    max_concurrent_trades: int
    kill_switch_active: bool
    timestamp: datetime


class LivePositionRecord(BaseModel):
    position_id: str
    symbol: str
    quantity: int
    buy_price: float
    current_ltp: float
    unrealized_pnl: float
    entry_time: datetime
    stoploss: float | None = None
    target: float | None = None
    dhan_security_id: str | None = None


class LivePositionsResponse(BaseModel):
    total_positions: int
    positions: list[LivePositionRecord]
    total_unrealized_pnl: float


class LiveTradebookItem(BaseModel):
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
    brokerage_charges: float | None = None
    stt_taxes: float | None = None
    slippage_amount: float | None = None
    net_pnl: float | None = None

    model_config = ConfigDict(from_attributes=True)


class LiveTradebookResponse(BaseModel):
    trades: list[LiveTradebookItem]
    total_trades: int
    total_realized_pnl: float
    total_charges: float
    net_realized_pnl: float


class LiveKillSwitchRequest(BaseModel):
    reason: str = Field(
        default="Manual Emergency Trigger", description="Reason for kill-switch halt"
    )


class LiveKillSwitchResponse(BaseModel):
    kill_switch_active: bool
    orders_cancelled_count: int
    positions_squared_off_count: int
    halt_timestamp: datetime
    status: str
    message: str


class LiveSquareOffResponse(BaseModel):
    trade_id: int | str
    dhan_order_id: str
    symbol: str
    exit_price: float
    realized_pnl: float
    status: str
    message: str


class LiveReconcileResponse(BaseModel):
    reconciled_at: datetime
    broker_positions_count: int
    local_positions_count: int
    mismatch_detected: bool
    drift_details: list[dict[str, Any]]
    status: Literal["SYNCHRONIZED", "DRIFT_RESOLVED", "WARNING_MISMATCH"]
    message: str


LiveSystemStatusResponse.model_rebuild()
LivePositionsResponse.model_rebuild()
LiveTradebookResponse.model_rebuild()
LiveReconcileResponse.model_rebuild()
