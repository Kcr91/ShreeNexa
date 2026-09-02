"""Backtest execution, performance analytics, strategy simulation, and options modeling."""

from __future__ import annotations

from app.backtest.metrics import calculate_backtest_metrics
from app.backtest.models import (
    BacktestConfig,
    BacktestPerformanceMetrics,
    BacktestResult,
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
from app.backtest.runner import StockStrategyBacktestRunner
from app.backtest.store import (
    BacktestStore,
    backtest_store,
)

__all__ = [
    "BacktestConfig",
    "BacktestPerformanceMetrics",
    "BacktestResult",
    "BacktestStore",
    "OptionBacktestConfig",
    "OptionBacktestResult",
    "OptionLegConfig",
    "OptionStrategyBacktestRunner",
    "OptionStrategyConfig",
    "PortfolioGreeks",
    "StockStrategyBacktestRunner",
    "backtest_store",
    "calculate_backtest_metrics",
    "calculate_option_margin",
]
