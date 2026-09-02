"""Backtest execution, performance analytics, and strategy simulation engine."""

from __future__ import annotations

from app.backtest.metrics import calculate_backtest_metrics
from app.backtest.models import (
    BacktestConfig,
    BacktestPerformanceMetrics,
    BacktestResult,
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
    "StockStrategyBacktestRunner",
    "backtest_store",
    "calculate_backtest_metrics",
]
