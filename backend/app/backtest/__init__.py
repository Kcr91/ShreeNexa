"""Backtest execution, performance analytics, Monte Carlo, and Walk-Forward modeling."""

from __future__ import annotations

from app.backtest.futures_models import (
    FuturesBacktestConfig,
    FuturesBacktestResult,
    FuturesContractSpec,
    FuturesRollRecord,
    FuturesStrategyConfig,
)
from app.backtest.futures_runner import FuturesStrategyBacktestRunner
from app.backtest.metrics import calculate_backtest_metrics
from app.backtest.models import (
    BacktestConfig,
    BacktestPerformanceMetrics,
    BacktestResult,
)
from app.backtest.monte_carlo import (
    MonteCarloConfig,
    MonteCarloPercentileSummary,
    MonteCarloResult,
    ResampleMethod,
    run_monte_carlo,
)
from app.backtest.options_models import (
    OptionBacktestConfig,
    OptionBacktestResult,
    OptionLegConfig,
    OptionStrategyConfig,
    PortfolioGreeks,
)
from app.backtest.options_runner import (
    OptionStrategyBacktestRunner,
    calculate_option_margin,
)
from app.backtest.portfolio_models import (
    PortfolioBacktestConfig,
    PortfolioBacktestResult,
    PortfolioRebalanceEvent,
    RebalanceFrequency,
    StrategyAllocation,
    StrategyContribution,
)
from app.backtest.portfolio_runner import PortfolioBacktestRunner
from app.backtest.runner import StockStrategyBacktestRunner
from app.backtest.store import (
    BacktestStore,
    backtest_store,
)
from app.backtest.walk_forward import (
    WalkForwardConfig,
    WalkForwardResult,
    WalkForwardSplit,
    WalkForwardWindowResult,
    generate_walk_forward_splits,
    run_walk_forward_analysis,
)

__all__ = [
    "BacktestConfig",
    "BacktestPerformanceMetrics",
    "BacktestResult",
    "BacktestStore",
    "FuturesBacktestConfig",
    "FuturesBacktestResult",
    "FuturesContractSpec",
    "FuturesRollRecord",
    "FuturesStrategyBacktestRunner",
    "FuturesStrategyConfig",
    "MonteCarloConfig",
    "MonteCarloPercentileSummary",
    "MonteCarloResult",
    "OptionBacktestConfig",
    "OptionBacktestResult",
    "OptionLegConfig",
    "OptionStrategyBacktestRunner",
    "OptionStrategyConfig",
    "PortfolioBacktestConfig",
    "PortfolioBacktestResult",
    "PortfolioBacktestRunner",
    "PortfolioGreeks",
    "PortfolioRebalanceEvent",
    "RebalanceFrequency",
    "ResampleMethod",
    "StockStrategyBacktestRunner",
    "StrategyAllocation",
    "StrategyContribution",
    "WalkForwardConfig",
    "WalkForwardResult",
    "WalkForwardSplit",
    "WalkForwardWindowResult",
    "backtest_store",
    "calculate_backtest_metrics",
    "calculate_option_margin",
    "generate_walk_forward_splits",
    "run_monte_carlo",
    "run_walk_forward_analysis",
]
