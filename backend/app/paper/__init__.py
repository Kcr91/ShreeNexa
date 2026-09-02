"""Paper trading package."""

from app.paper.adapter import (
    calculate_paper_metrics,
    evaluate_paper_scorecard,
    paper_account_to_portfolio,
)
from app.paper.broker import PaperBroker, paper_broker
from app.paper.divergence import (
    DiscrepancyItem,
    DiscrepancyType,
    DivergenceSeverity,
    DivergenceTolerances,
    ExecutionComparisonItem,
    PnLComparisonSummary,
    SessionDivergenceReport,
    SignalComparisonItem,
    generate_account_divergence_report,
    generate_divergence_report,
)
from app.paper.fill_policy import PaperFillPolicy
from app.paper.lifecycle import (
    DeploymentAction,
    DeploymentAuditEvent,
    DeploymentState,
    DeploymentStore,
    PaperDeploymentManager,
    StrategyDeployment,
    deployment_store,
    paper_deployment_manager,
)
from app.paper.models import (
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
    PaperPosition,
)
from app.paper.multi_strategy import (
    MultiStrategyPaperCoordinator,
    MultiStrategyStatus,
    SharedAccountCaps,
    StrategyAllocationConfig,
    StrategyBookSummary,
)
from app.paper.reconciliation import (
    PortfolioSummary,
    PositionSummaryItem,
    RejectedOrderInfo,
    reconcile_portfolio,
)
from app.paper.repository import PaperRepository, paper_repository

__all__ = [
    "DeploymentAction",
    "DeploymentAuditEvent",
    "DeploymentState",
    "DeploymentStore",
    "DiscrepancyItem",
    "DiscrepancyType",
    "DivergenceSeverity",
    "DivergenceTolerances",
    "ExecutionComparisonItem",
    "MultiStrategyPaperCoordinator",
    "MultiStrategyStatus",
    "PaperAccount",
    "PaperBroker",
    "PaperDeploymentManager",
    "PaperFill",
    "PaperFillPolicy",
    "PaperOrder",
    "PaperOrderSide",
    "PaperOrderStatus",
    "PaperOrderType",
    "PaperPosition",
    "PaperRepository",
    "PnLComparisonSummary",
    "PortfolioSummary",
    "PositionSummaryItem",
    "RejectedOrderInfo",
    "SessionDivergenceReport",
    "SharedAccountCaps",
    "SignalComparisonItem",
    "StrategyAllocationConfig",
    "StrategyBookSummary",
    "StrategyDeployment",
    "calculate_paper_metrics",
    "deployment_store",
    "evaluate_paper_scorecard",
    "generate_account_divergence_report",
    "generate_divergence_report",
    "paper_account_to_portfolio",
    "paper_broker",
    "paper_deployment_manager",
    "paper_repository",
    "reconcile_portfolio",
]
