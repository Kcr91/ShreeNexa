"""Long-term investing portfolio management, lot accounting, and reconciliation."""

from __future__ import annotations

from app.investing.analytics import (
    compare_portfolio_to_benchmark,
    compute_account_xirr,
    generate_portfolio_allocation,
    generate_portfolio_cashflows,
    get_security_sector,
)
from app.investing.dividends import (
    DividendIncomeCalendarMonth,
    DividendIncomeView,
    DividendLedger,
    DividendMatchingResult,
    DividendPaymentImportItem,
    DividendRecord,
    DividendStatus,
    dividend_ledger,
)
from app.investing.ledger import HoldingsLedger, holdings_ledger
from app.investing.models import (
    AssetAllocationItem,
    BenchmarkComparisonResult,
    CapitalGainsCategory,
    CashFlowItem,
    CorporateAction,
    CorporateActionType,
    DhanHoldingItem,
    DisposalAllocation,
    DisposalRecord,
    HoldingReconciliationItem,
    HoldingSummary,
    PortfolioAllocationReport,
    PortfolioHoldingsReport,
    ReconciliationReport,
    SectorAllocationItem,
    TaxLot,
    XIRRCalculationResponse,
)
from app.investing.reconciliation import (
    import_dhan_holdings_as_initial_lots,
    parse_dhan_holdings_payload,
    reconcile_dhan_holdings,
)
from app.investing.xirr import (
    XIRRConvergenceError,
    XIRRError,
    XIRRInvalidCashflowsError,
    calculate_xirr,
)

__all__ = [
    "AssetAllocationItem",
    "BenchmarkComparisonResult",
    "CapitalGainsCategory",
    "CashFlowItem",
    "CorporateAction",
    "CorporateActionType",
    "DhanHoldingItem",
    "DisposalAllocation",
    "DisposalRecord",
    "DividendIncomeCalendarMonth",
    "DividendIncomeView",
    "DividendLedger",
    "DividendMatchingResult",
    "DividendPaymentImportItem",
    "DividendRecord",
    "DividendStatus",
    "HoldingReconciliationItem",
    "HoldingSummary",
    "HoldingsLedger",
    "PortfolioAllocationReport",
    "PortfolioHoldingsReport",
    "ReconciliationReport",
    "SectorAllocationItem",
    "TaxLot",
    "XIRRCalculationResponse",
    "XIRRConvergenceError",
    "XIRRError",
    "XIRRInvalidCashflowsError",
    "calculate_xirr",
    "compare_portfolio_to_benchmark",
    "compute_account_xirr",
    "dividend_ledger",
    "generate_portfolio_allocation",
    "generate_portfolio_cashflows",
    "get_security_sector",
    "holdings_ledger",
    "import_dhan_holdings_as_initial_lots",
    "parse_dhan_holdings_payload",
    "reconcile_dhan_holdings",
]
