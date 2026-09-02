"""Backtest execution, metrics grading, scorecard, and Overfitting controls."""

from __future__ import annotations

from app.backtest.futures_models import (
    FuturesBacktestConfig,
    FuturesBacktestResult,
    FuturesContractSpec,
    FuturesRollRecord,
    FuturesStrategyConfig,
)
from app.backtest.futures_runner import FuturesStrategyBacktestRunner
from app.backtest.grading import (
    DeploymentGateResult,
    GradingConfig,
    MetricGrade,
    MetricScore,
    StrategyHorizon,
    StrategyScorecard,
    Verdict,
    evaluate_strategy_scorecard,
)
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
from app.backtest.overfitting import (
    DeflatedSharpeResult,
    OverfittingReport,
    PBOResult,
    WhiteRealityCheckResult,
    calculate_deflated_sharpe_ratio,
    calculate_pbo,
    calculate_whites_reality_check,
    generate_overfitting_report,
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
    "DeflatedSharpeResult",
    "DeploymentGateResult",
    "FuturesBacktestConfig",
    "FuturesBacktestResult",
    "FuturesContractSpec",
    "FuturesRollRecord",
    "FuturesStrategyBacktestRunner",
    "FuturesStrategyConfig",
    "GradingConfig",
    "MetricGrade",
    "MetricScore",
    "MonteCarloConfig",
    "MonteCarloPercentileSummary",
    "MonteCarloResult",
    "OptionBacktestConfig",
    "OptionBacktestResult",
    "OptionLegConfig",
    "OptionStrategyBacktestRunner",
    "OptionStrategyConfig",
    "OverfittingReport",
    "PBOResult",
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
    "StrategyHorizon",
    "StrategyScorecard",
    "Verdict",
    "WalkForwardConfig",
    "WalkForwardResult",
    "WalkForwardSplit",
    "WalkForwardWindowResult",
    "WhiteRealityCheckResult",
    "backtest_store",
    "calculate_backtest_metrics",
    "calculate_deflated_sharpe_ratio",
    "calculate_option_margin",
    "calculate_pbo",
    "calculate_whites_reality_check",
    "evaluate_strategy_scorecard",
    "generate_overfitting_report",
    "generate_walk_forward_splits",
    "run_monte_carlo",
    "run_walk_forward_analysis",
]
