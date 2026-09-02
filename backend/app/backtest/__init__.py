"""Backtest execution, performance analytics, strategy simulation, options, and futures modeling."""

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
    "FuturesBacktestConfig",
    "FuturesBacktestResult",
    "FuturesContractSpec",
    "FuturesRollRecord",
    "FuturesStrategyBacktestRunner",
    "FuturesStrategyConfig",
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
