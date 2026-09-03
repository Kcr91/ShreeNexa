"""REST API endpoints for long-term holdings, tax lots, and Dhan reconciliation."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.investing.analytics import (
    compare_portfolio_to_benchmark,
    compute_account_xirr,
    generate_portfolio_allocation,
)
from app.investing.dividends import (
    DividendIncomeView,
    DividendMatchingResult,
    DividendPaymentImportItem,
    DividendRecord,
    DividendStatus,
    dividend_ledger,
)
from app.investing.ledger import holdings_ledger
from app.investing.models import (
    BenchmarkComparisonResult,
    CashFlowItem,
    CorporateAction,
    DhanHoldingItem,
    DisposalRecord,
    PortfolioAllocationReport,
    PortfolioHoldingsReport,
    ReconciliationReport,
    TaxLot,
    XIRRCalculationResponse,
)
from app.investing.rebalancing import (
    RebalanceProposal,
    SIPPlanResult,
    TWRCalculationResult,
    calculate_time_weighted_return,
    generate_rebalance_proposal,
    plan_sip_instalment,
)
from app.investing.reconciliation import (
    import_dhan_holdings_as_initial_lots,
    reconcile_dhan_holdings,
)
from app.investing.xirr import XIRRError, calculate_xirr

router = APIRouter(prefix="/api/v1/investing", tags=["investing"])


class AddLotRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = "default"
    security_id: str
    isin: str
    trading_symbol: str
    acquisition_date: date
    acquisition_price: float = Field(ge=0.0)
    quantity: int = Field(gt=0)
    lot_id: str | None = None


class RecordDisposalRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = "default"
    security_id: str
    disposal_date: date
    disposal_price: float = Field(gt=0.0)
    quantity: int = Field(gt=0)
    transaction_costs: float = Field(default=0.0, ge=0.0)
    disposal_id: str | None = None


class ReconcileDhanRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = "default"
    dhan_holdings: list[DhanHoldingItem]
    cost_tolerance: float = 0.01


class ImportDhanRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = "default"
    dhan_holdings: list[DhanHoldingItem]
    acquisition_date: date | None = None


@router.get("/holdings", response_model=PortfolioHoldingsReport)
def get_portfolio_holdings(account_id: str = "default") -> PortfolioHoldingsReport:
    """Retrieve full portfolio holdings statement with active tax lots and costs."""
    return holdings_ledger.generate_portfolio_report(account_id=account_id)


@router.post("/lots", response_model=TaxLot)
def add_tax_lot(request: AddLotRequest) -> TaxLot:
    """Add a purchase tax lot to the long-term holdings ledger."""
    try:
        return holdings_ledger.add_lot(
            account_id=request.account_id,
            security_id=request.security_id,
            isin=request.isin,
            trading_symbol=request.trading_symbol,
            acquisition_date=request.acquisition_date,
            acquisition_price=request.acquisition_price,
            quantity=request.quantity,
            lot_id=request.lot_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/disposals", response_model=DisposalRecord)
def record_disposal(request: RecordDisposalRequest) -> DisposalRecord:
    """Sell shares using FIFO lot depletion and calculate realized capital gains (STCG/LTCG)."""
    try:
        return holdings_ledger.record_disposal(
            account_id=request.account_id,
            security_id=request.security_id,
            disposal_date=request.disposal_date,
            disposal_price=request.disposal_price,
            quantity=request.quantity,
            transaction_costs=request.transaction_costs,
            disposal_id=request.disposal_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/corporate-actions", response_model=list[TaxLot])
def apply_corporate_action(
    action: CorporateAction,
    account_id: str = "default",
) -> list[TaxLot]:
    """Apply a corporate action (stock split, bonus issue, consolidation) to active lots."""
    return holdings_ledger.apply_corporate_action(account_id=account_id, action=action)


@router.post("/reconcile-dhan", response_model=ReconciliationReport)
def reconcile_with_dhan(request: ReconcileDhanRequest) -> ReconciliationReport:
    """Reconcile local holdings ledger against a Dhan broker holdings statement."""
    return reconcile_dhan_holdings(
        account_id=request.account_id,
        dhan_items=request.dhan_holdings,
        ledger=holdings_ledger,
        cost_tolerance=request.cost_tolerance,
    )


@router.post("/import-dhan", response_model=dict[str, int])
def import_dhan_holdings(request: ImportDhanRequest) -> dict[str, int]:
    """Import Dhan holdings as baseline purchase lots in the ledger."""
    count = import_dhan_holdings_as_initial_lots(
        account_id=request.account_id,
        dhan_items=request.dhan_holdings,
        acquisition_date=request.acquisition_date,
        ledger=holdings_ledger,
    )
    return {"imported_holdings": count}


# --- F10.2 Endpoints: XIRR, Allocation, Benchmark Comparison ---


class XIRRRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str | None = None
    cashflows: list[CashFlowItem] | None = None
    current_prices: dict[str, float] | None = None
    as_of_date: date | None = None


class BenchmarkComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = "default"
    benchmark_symbol: str = "NIFTY 50"
    benchmark_annual_return_pct: float = 14.5
    current_prices: dict[str, float] | None = None
    as_of_date: date | None = None


@router.post("/xirr", response_model=XIRRCalculationResponse)
def compute_xirr(request: XIRRRequest) -> XIRRCalculationResponse:
    """Calculate XIRR from explicit cashflows or for a portfolio account."""
    try:
        if request.cashflows:
            flows = [(cf.date, cf.amount) for cf in request.cashflows]
            xirr_val = calculate_xirr(flows)
            invested = sum(-f[1] for f in flows if f[1] < 0)
            terminal = sum(f[1] for f in flows if f[1] > 0)
            return XIRRCalculationResponse(
                account_id=request.account_id or "custom_flows",
                xirr=xirr_val,
                xirr_pct=round(xirr_val * 100.0, 2),
                total_invested=invested,
                current_value=terminal,
                cashflow_count=len(flows),
            )

        if not request.account_id:
            raise HTTPException(
                status_code=400, detail="Either 'cashflows' or 'account_id' must be provided."
            )

        return compute_account_xirr(
            account_id=request.account_id,
            ledger=holdings_ledger,
            current_prices=request.current_prices,
            as_of_date=request.as_of_date,
        )
    except XIRRError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/allocation", response_model=PortfolioAllocationReport)
def get_portfolio_allocation(account_id: str = "default") -> PortfolioAllocationReport:
    """Get portfolio sector and asset class allocation breakdown with concentration flags."""
    return generate_portfolio_allocation(account_id=account_id, ledger=holdings_ledger)


@router.post("/benchmark-comparison", response_model=BenchmarkComparisonResult)
def compare_with_benchmark(request: BenchmarkComparisonRequest) -> BenchmarkComparisonResult:
    """Compare portfolio XIRR against a market benchmark annual rate."""
    try:
        return compare_portfolio_to_benchmark(
            account_id=request.account_id,
            benchmark_symbol=request.benchmark_symbol,
            benchmark_annual_return_pct=request.benchmark_annual_return_pct,
            ledger=holdings_ledger,
            current_prices=request.current_prices,
            as_of_date=request.as_of_date,
        )
    except XIRRError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- F10.3 Endpoints: Dividend Ledger, Import/Matching, and Income View ---


class ImportDividendsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = "default"
    items: list[DividendPaymentImportItem]


@router.get("/dividends", response_model=list[DividendRecord])
def list_dividends(
    account_id: str = "default",
    from_date: date | None = None,
    to_date: date | None = None,
    status: DividendStatus | None = None,
) -> list[DividendRecord]:
    """List recorded dividends for an investing account with optional date/status filters."""
    return dividend_ledger.list_dividends(
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        status=status,
    )


@router.post("/dividends/import", response_model=DividendMatchingResult)
def import_dividends(request: ImportDividendsRequest) -> DividendMatchingResult:
    """Import dividend payments and match against active holdings on record date."""
    return dividend_ledger.match_dividend_payments(
        account_id=request.account_id,
        imports=request.items,
        ledger=holdings_ledger,
    )


@router.get("/dividends/income-view", response_model=DividendIncomeView)
def get_dividend_income_view(account_id: str = "default") -> DividendIncomeView:
    """Get dividend income statement, monthly calendar, and yield metrics."""
    return dividend_ledger.generate_income_view(
        account_id=account_id,
        ledger=holdings_ledger,
    )


# --- F10.4 Endpoints: SIP Planning, Rebalancing Proposals, and TWR ---


class SIPPlanRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    budget: float = Field(gt=0.0)
    target_weights: dict[str, float]
    current_prices: dict[str, float]


class RebalanceProposalRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = "default"
    target_weights: dict[str, float]
    current_prices: dict[str, float]
    available_cash: float = 0.0
    tolerance_band_pct: float = 5.0
    inflow_only: bool = False
    max_allocation_per_trade: float | None = None


class TWRSubPeriodItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_date: date
    end_date: date
    start_value: float
    end_value: float
    net_cash_flow: float = 0.0


class TWRCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = "default"
    sub_periods: list[TWRSubPeriodItem]


@router.post("/sip/plan", response_model=SIPPlanResult)
def create_sip_plan(request: SIPPlanRequest) -> SIPPlanResult:
    """Calculate whole-share SIP investment schedule from budget and target weights."""
    try:
        return plan_sip_instalment(
            budget=request.budget,
            target_weights=request.target_weights,
            current_prices=request.current_prices,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rebalance/proposal", response_model=RebalanceProposal)
def create_rebalance_proposal(request: RebalanceProposalRequest) -> RebalanceProposal:
    """Generate portfolio rebalancing proposal respecting cash limits and tolerance bands.

    Safety invariant: Only generates proposals; NEVER places automatic orders.
    """
    try:
        return generate_rebalance_proposal(
            account_id=request.account_id,
            target_weights=request.target_weights,
            current_prices=request.current_prices,
            available_cash=request.available_cash,
            tolerance_band_pct=request.tolerance_band_pct,
            inflow_only=request.inflow_only,
            max_allocation_per_trade=request.max_allocation_per_trade,
            ledger=holdings_ledger,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/performance/twr", response_model=TWRCalculationResult)
def compute_twr(request: TWRCalculationRequest) -> TWRCalculationResult:
    """Compute Time-Weighted Return (TWR) isolating performance from cashflow timing."""
    try:
        raw_periods = [
            (sp.start_date, sp.end_date, sp.start_value, sp.end_value, sp.net_cash_flow)
            for sp in request.sub_periods
        ]
        return calculate_time_weighted_return(
            account_id=request.account_id,
            sub_periods_data=raw_periods,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
