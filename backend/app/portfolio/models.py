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
    delta_cash: float = Field(
        description="Net cash transferred (+ = infused, - = harvested)"
    )


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
