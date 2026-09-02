"""Data models for Futures strategy configuration, contract specs, rolls, and backtest results."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.backtest.models import BacktestPerformanceMetrics
from app.engine.contracts import EquityPoint, FillEvent, OrderSide


class FuturesContractSpec(BaseModel):
    """Specification of an individual exchange-traded futures contract."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    underlying_symbol: str
    exchange_segment: str = "NSE_FNO"
    expiry_date: datetime
    lot_size: int = Field(default=50, ge=1)
    tick_size: float = Field(default=0.05, gt=0.0)


class FuturesStrategyConfig(BaseModel):
    """Futures trading strategy specification including roll policies and margin rules."""

    model_config = ConfigDict(extra="forbid")

    name: str
    underlying_symbol: str
    exchange_segment: str = "NSE_FNO"
    lot_size: int = Field(default=50, ge=1)
    lots: int = Field(default=1, ge=1)
    margin_pct: float = Field(default=0.12, gt=0.0, le=1.0)
    days_before_expiry_roll: int = Field(default=1, ge=0)
    side: OrderSide = Field(default=OrderSide.BUY)


class FuturesBacktestConfig(BaseModel):
    """Execution configuration for futures backtesting."""

    model_config = ConfigDict(extra="forbid")

    strategy: FuturesStrategyConfig
    start_date: datetime
    end_date: datetime
    initial_cash: float = Field(default=1_000_000.0, gt=0.0)
    slippage_model: str = Field(default="none")
    slippage_param: float = Field(default=0.0)


class FuturesRollRecord(BaseModel):
    """Audit record capturing an automated contract rollover event."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    from_contract: str
    to_contract: str
    old_price: float
    new_price: float
    roll_spread: float
    roll_cost: float


class FuturesBacktestResult(BaseModel):
    """Complete futures strategy simulation result with roll history and margin analytics."""

    model_config = ConfigDict(extra="forbid")

    backtest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_name: str
    config: FuturesBacktestConfig
    metrics: BacktestPerformanceMetrics
    rolls: list[FuturesRollRecord]
    margin_history: list[dict[str, float]]
    trades: list[FillEvent]
    equity_curve: list[EquityPoint]
    engine_commit: str = Field(default="unknown")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
