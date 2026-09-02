"""Data models for multi-strategy portfolio backtesting, capital allocation, and rebalancing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.backtest.futures_models import FuturesBacktestConfig
from app.backtest.models import BacktestConfig, BacktestPerformanceMetrics
from app.backtest.options_models import OptionBacktestConfig
from app.engine.contracts import EquityPoint


class RebalanceFrequency(StrEnum):
    """Rebalancing schedule policy."""

    NEVER = "NEVER"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class StrategyAllocation(BaseModel):
    """Allocation specification for an individual sub-strategy within a portfolio."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    strategy_name: str
    strategy_type: str = Field(description="'stock', 'option', or 'futures'")
    weight: float = Field(gt=0.0, le=1.0)
    stock_config: BacktestConfig | None = None
    option_config: OptionBacktestConfig | None = None
    futures_config: FuturesBacktestConfig | None = None


class PortfolioBacktestConfig(BaseModel):
    """Execution configuration for multi-strategy portfolio simulation."""

    model_config = ConfigDict(extra="forbid")

    name: str
    allocations: list[StrategyAllocation]
    initial_cash: float = Field(default=2_000_000.0, gt=0.0)
    start_date: datetime
    end_date: datetime
    rebalance_freq: RebalanceFrequency = Field(default=RebalanceFrequency.NEVER)
    rebalance_threshold_pct: float = Field(default=0.05, ge=0.0)


class StrategyContribution(BaseModel):
    """Performance and attribution breakdown for an individual sub-strategy."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    strategy_name: str
    allocated_capital: float
    final_equity: float
    total_pnl: float
    return_pct: float
    initial_weight: float
    final_weight: float
    metrics: BacktestPerformanceMetrics


class PortfolioRebalanceEvent(BaseModel):
    """Audit record capturing a portfolio capital rebalancing transaction."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    strategy_id: str
    old_capital: float
    new_capital: float
    delta_cash: float


class PortfolioBacktestResult(BaseModel):
    """Complete portfolio-level backtesting output with aggregated metrics and attribution."""

    model_config = ConfigDict(extra="forbid")

    portfolio_backtest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    config: PortfolioBacktestConfig
    combined_metrics: BacktestPerformanceMetrics
    contributions: list[StrategyContribution]
    rebalance_events: list[PortfolioRebalanceEvent]
    combined_equity_curve: list[EquityPoint]
    engine_commit: str = Field(default="unknown")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
