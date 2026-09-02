"""Portfolio allocation, multi-strategy orchestration, and rebalancing package."""

from app.portfolio.allocation import (
    AllocationValidationError,
    compute_rebalance_transfers,
    split_initial_capital,
    validate_allocation_config,
)
from app.portfolio.analytics import (
    check_risk_caps,
    compute_drawdown_curve,
    compute_marginal_risk_return_attribution,
    generate_portfolio_analytics_report,
)
from app.portfolio.book import PositionEntry, StrategyBook
from app.portfolio.correlation import (
    align_pairwise_series,
    compute_correlation_matrix,
    compute_series_correlation,
    compute_signal_correlation_matrix,
)
from app.portfolio.models import (
    CorrelationMatrix,
    DrawdownPoint,
    MissingPeriodPolicy,
    PortfolioAllocationConfig,
    PortfolioAnalyticsReport,
    PortfolioDailySnapshot,
    PortfolioRiskCaps,
    PortfolioRunSummary,
    RebalanceFrequency,
    RebalanceTransferRecord,
    RebalanceTrigger,
    StrategyAllocationSpec,
    StrategyRiskAttribution,
)
from app.portfolio.orchestrator import PortfolioOrchestrator

__all__ = [
    "AllocationValidationError",
    "CorrelationMatrix",
    "DrawdownPoint",
    "MissingPeriodPolicy",
    "PortfolioAllocationConfig",
    "PortfolioAnalyticsReport",
    "PortfolioDailySnapshot",
    "PortfolioOrchestrator",
    "PortfolioRiskCaps",
    "PortfolioRunSummary",
    "PositionEntry",
    "RebalanceFrequency",
    "RebalanceTransferRecord",
    "RebalanceTrigger",
    "StrategyAllocationSpec",
    "StrategyBook",
    "StrategyRiskAttribution",
    "align_pairwise_series",
    "check_risk_caps",
    "compute_correlation_matrix",
    "compute_drawdown_curve",
    "compute_marginal_risk_return_attribution",
    "compute_rebalance_transfers",
    "compute_series_correlation",
    "compute_signal_correlation_matrix",
    "generate_portfolio_analytics_report",
    "split_initial_capital",
    "validate_allocation_config",
]
