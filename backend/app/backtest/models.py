"""Data models for Backtest configuration, performance metrics, and execution results."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.engine.contracts import EquityPoint, FillEvent
from app.engine.costs import ProductType
from app.engine.sim_broker import FillTiming
from app.strategy.ir import StrategyIR


class AIGenerationMetadata(BaseModel):
    """Provenance metadata recorded when a backtest originates from an AI-generated draft."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    provider_name: str
    model_version: str = "1.0.0"
    ir_version: int
    ir_hash: str
    generated_at: datetime
    approved_at: datetime
    draft_status: str = "APPROVED_DRAFT"


class BacktestConfig(BaseModel):
    """Backtest execution parameter configuration."""

    model_config = ConfigDict(extra="forbid")

    strategy: StrategyIR
    start_date: datetime
    end_date: datetime
    initial_cash: float = Field(default=1_000_000.0, gt=0.0)
    fill_timing: FillTiming = Field(default=FillTiming.NEXT_BAR_OPEN)
    slippage_model: str = Field(
        default="none", description="Slippage model: 'none', 'tick', or 'percent'"
    )
    slippage_param: float = Field(
        default=0.0, description="Slippage value (ticks or percentage fraction)"
    )
    product_type: ProductType = Field(default=ProductType.DELIVERY)
    seed: int | None = Field(default=None, description="Random seed for reproducible execution")
    ai_metadata: AIGenerationMetadata | None = Field(
        default=None, description="Optional AI generation provenance metadata"
    )


class BacktestPerformanceMetrics(BaseModel):
    """Key performance metrics calculated from portfolio equity and trade history."""

    model_config = ConfigDict(extra="forbid")

    initial_capital: float
    final_equity: float
    total_return_pct: float
    cagr_pct: float
    total_pnl: float
    total_costs: float
    realized_pnl: float
    unrealized_pnl: float
    max_drawdown_pct: float
    max_drawdown_value: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float


class BacktestResult(BaseModel):
    """Complete immutable backtest run snapshot with audit provenance."""

    model_config = ConfigDict(extra="forbid")

    backtest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_name: str
    config: BacktestConfig
    metrics: BacktestPerformanceMetrics
    trades: list[FillEvent]
    equity_curve: list[EquityPoint]
    engine_commit: str = Field(default="unknown")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    ai_metadata: AIGenerationMetadata | None = Field(
        default=None, description="Optional AI generation provenance metadata"
    )
