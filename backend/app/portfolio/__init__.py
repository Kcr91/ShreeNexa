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
from app.portfolio.models import (
    DrawdownPoint,
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
    "DrawdownPoint",
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
    "check_risk_caps",
    "compute_drawdown_curve",
    "compute_marginal_risk_return_attribution",
    "compute_rebalance_transfers",
    "generate_portfolio_analytics_report",
    "split_initial_capital",
    "validate_allocation_config",
]
