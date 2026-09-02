"""Data models for Option multi-leg strategies, Greeks tracking, and backtest results."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.backtest.models import BacktestPerformanceMetrics
from app.engine.contracts import EquityPoint, FillEvent, OrderSide
from app.marketdata.options_analytics import OptionType


class OptionLegConfig(BaseModel):
    """Definition of a single option leg within a multi-leg options strategy."""

    model_config = ConfigDict(extra="forbid")

    leg_id: str
    option_type: OptionType
    side: OrderSide
    strike: float = Field(gt=0.0)
    expiry_date: datetime
    ratio: int = Field(default=1, ge=1)
    lot_size: int = Field(default=50, ge=1)


class OptionStrategyConfig(BaseModel):
    """Multi-leg option strategy specification."""

    model_config = ConfigDict(extra="forbid")

    name: str
    underlying_symbol: str
    exchange_segment: str = "NSE_FNO"
    legs: list[OptionLegConfig]
    lots: int = Field(default=1, ge=1)
    volatility: float = Field(default=0.15, gt=0.0)
    risk_free_rate: float = Field(default=0.07, ge=0.0)


class OptionBacktestConfig(BaseModel):
    """Execution configuration for options strategy simulation."""

    model_config = ConfigDict(extra="forbid")

    strategy: OptionStrategyConfig
    start_date: datetime
    end_date: datetime
    initial_cash: float = Field(default=1_000_000.0, gt=0.0)
    slippage_model: str = Field(default="none")
    slippage_param: float = Field(default=0.0)


class PortfolioGreeks(BaseModel):
    """Aggregated portfolio-level Greeks snapshot at a given timestamp."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    net_delta: float
    net_gamma: float
    net_theta: float
    net_vega: float
    net_rho: float


class OptionBacktestResult(BaseModel):
    """Complete option strategy backtest result with Greeks and margin history."""

    model_config = ConfigDict(extra="forbid")

    backtest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_name: str
    config: OptionBacktestConfig
    metrics: BacktestPerformanceMetrics
    greeks_history: list[PortfolioGreeks]
    margin_history: list[dict[str, float]]
    trades: list[FillEvent]
    equity_curve: list[EquityPoint]
    engine_commit: str = Field(default="unknown")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
