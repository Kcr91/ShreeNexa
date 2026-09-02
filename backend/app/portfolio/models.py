"""Data models for multi-strategy portfolio allocation, rebalancing, and execution."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RebalanceFrequency(StrEnum):
    """Frequency of portfolio capital rebalancing."""

    NEVER = "NEVER"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    DRIFT_ONLY = "DRIFT_ONLY"


class RebalanceTrigger(StrEnum):
    """Reason triggering a portfolio rebalance."""

    CALENDAR = "CALENDAR"
    DRIFT_THRESHOLD = "DRIFT_THRESHOLD"
    MANUAL = "MANUAL"


class StrategyAllocationSpec(BaseModel):
    """Specification of an individual strategy's capital allocation within a portfolio."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    weight: float = Field(gt=0.0, le=1.0)
    strategy_type: str = Field(description="'stock', 'option', or 'futures'")
    config_payload: dict[str, Any] = Field(default_factory=dict)


class PortfolioAllocationConfig(BaseModel):
    """Configuration for multi-strategy capital allocation and rebalancing policies."""

    model_config = ConfigDict(extra="forbid")

    portfolio_name: str = Field(min_length=1)
    total_initial_capital: float = Field(gt=0.0)
    allocations: list[StrategyAllocationSpec] = Field(min_length=1)
    rebalance_freq: RebalanceFrequency = Field(default=RebalanceFrequency.NEVER)
    rebalance_threshold_pct: float = Field(
        default=0.05,
        ge=0.0,
        description="Drift threshold (e.g. 0.05 = 5% drift from target weight)",
    )


class RebalanceTransferRecord(BaseModel):
    """Audit record capturing an individual strategy's cash adjustment during rebalancing."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    trigger: RebalanceTrigger
    strategy_id: str
    pre_rebalance_capital: float
    target_capital: float
    delta_cash: float = Field(description="Net cash transferred (+ = infused, - = harvested)")


class PortfolioDailySnapshot(BaseModel):
    """Aggregated daily equity and cash balance for the portfolio."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    total_cash: float
    total_equity: float
    strategy_equities: dict[str, float]
    strategy_weights: dict[str, float]


class PortfolioRunSummary(BaseModel):
    """Portfolio run outcome including allocations, rebalances, and snapshots."""

    model_config = ConfigDict(extra="forbid")

    portfolio_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_name: str
    initial_capital: float
    final_capital: float
    total_pnl: float
    total_return_pct: float
    rebalance_events: list[RebalanceTransferRecord]
    daily_snapshots: list[PortfolioDailySnapshot]
    executed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class DrawdownPoint(BaseModel):
    """High-water mark and drawdown point in portfolio equity time series."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    equity: float
    high_water_mark: float
    drawdown_abs: float = Field(le=0.0)
    drawdown_pct: float = Field(le=0.0)


class PortfolioRiskCaps(BaseModel):
    """Risk constraints and guardrail caps applied to multi-strategy portfolios."""

    model_config = ConfigDict(extra="forbid")

    max_drawdown_pct_cap: float = Field(default=0.20, gt=0.0, le=1.0)
    max_strategy_concentration_pct: float = Field(default=0.70, gt=0.0, le=1.0)
    max_leverage_cap: float = Field(default=2.0, gt=0.0)


class StrategyRiskAttribution(BaseModel):
    """Marginal risk and return contribution metrics for an individual sub-strategy."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    strategy_name: str
    target_weight: float
    actual_weight: float
    total_return_pct: float
    return_contribution_pct: float
    volatility: float
    marginal_contribution_to_risk: float
    percentage_risk_contribution: float


class PortfolioAnalyticsReport(BaseModel):
    """Comprehensive portfolio analytics, drawdown profile, caps compliance, and attribution."""

    model_config = ConfigDict(extra="forbid")

    portfolio_name: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    annualized_return_pct: float
    portfolio_volatility: float
    portfolio_sharpe: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    drawdown_curve: list[DrawdownPoint]
    attributions: list[StrategyRiskAttribution]
    caps_breaches: list[str]


class MissingPeriodPolicy(StrEnum):
    """Policy for handling misaligned or missing periods between strategies."""

    DROP_COMMON = "DROP_COMMON"
    FILL_ZERO = "FILL_ZERO"
    FORWARD_FILL = "FORWARD_FILL"


class CorrelationMatrix(BaseModel):
    """Pairwise correlation matrix with metadata, sample counts, and diagnostics."""

    model_config = ConfigDict(extra="forbid")

    labels: list[str]
    matrix: list[list[float]]
    sample_counts: list[list[int]]
    policy: MissingPeriodPolicy
    warnings: list[str] = Field(default_factory=list)
