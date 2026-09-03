"""REST API endpoints for long-term holdings, tax lots, and Dhan reconciliation."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.investing.ledger import holdings_ledger
from app.investing.models import (
    CorporateAction,
    DhanHoldingItem,
    DisposalRecord,
    PortfolioHoldingsReport,
    ReconciliationReport,
    TaxLot,
)
from app.investing.reconciliation import (
    import_dhan_holdings_as_initial_lots,
    reconcile_dhan_holdings,
)

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
