"""Domain models for long-term investing, tax lots, corporate actions, and reconciliation."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CapitalGainsCategory(StrEnum):
    """Classification of capital gains under Indian tax rules."""

    STCG = "STCG"  # Short-Term Capital Gains (< 365 calendar days for equity)
    LTCG = "LTCG"  # Long-Term Capital Gains (>= 365 calendar days for equity)


class CorporateActionType(StrEnum):
    """Types of corporate actions that affect holdings or cash."""

    STOCK_SPLIT = "STOCK_SPLIT"
    BONUS_ISSUE = "BONUS_ISSUE"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    CONSOLIDATION = "CONSOLIDATION"


class TaxLot(BaseModel):
    """Individual tax lot representing a discrete purchase tranche."""

    model_config = ConfigDict(frozen=True)

    lot_id: str
    security_id: str
    isin: str
    trading_symbol: str
    acquisition_date: date
    acquisition_price: float = Field(ge=0.0)
    quantity: int = Field(gt=0)
    remaining_quantity: int = Field(ge=0)

    @property
    def is_exhausted(self) -> bool:
        return self.remaining_quantity == 0

    @property
    def invested_capital(self) -> float:
        return round(self.remaining_quantity * self.acquisition_price, 2)


class DisposalAllocation(BaseModel):
    """Specific tax lot depletion allocation during a disposal."""

    model_config = ConfigDict(frozen=True)

    lot_id: str
    depleted_quantity: int = Field(gt=0)
    acquisition_price: float
    acquisition_date: date
    disposal_price: float
    disposal_date: date
    holding_period_days: int
    gains_category: CapitalGainsCategory
    gross_pnl: float


class DisposalRecord(BaseModel):
    """Audit record of a sold tranche with FIFO lot depletion and tax breakdown."""

    model_config = ConfigDict(frozen=True)

    disposal_id: str
    security_id: str
    isin: str
    trading_symbol: str
    disposal_date: date
    disposal_price: float = Field(gt=0.0)
    quantity: int = Field(gt=0)
    transaction_costs: float = Field(default=0.0, ge=0.0)
    gross_realized_pnl: float
    net_realized_pnl: float
    stcg_pnl: float
    ltcg_pnl: float
    allocations: list[DisposalAllocation] = Field(default_factory=list)


class CorporateAction(BaseModel):
    """Corporate action specification (splits, bonuses, dividends)."""

    model_config = ConfigDict(frozen=True)

    action_id: str
    action_type: CorporateActionType
    security_id: str
    isin: str
    effective_date: date
    ratio_numerator: int = Field(default=1, gt=0)
    ratio_denominator: int = Field(default=1, gt=0)
    cash_amount_per_share: float = Field(default=0.0, ge=0.0)
    description: str = ""


class HoldingSummary(BaseModel):
    """Consolidated summary of a security holding."""

    model_config = ConfigDict(frozen=True)

    security_id: str
    isin: str
    trading_symbol: str
    total_quantity: int = Field(ge=0)
    available_quantity: int = Field(ge=0)
    dp_quantity: int = Field(ge=0)
    t1_quantity: int = Field(default=0, ge=0)
    weighted_average_cost: float = Field(ge=0.0)
    total_invested_capital: float = Field(ge=0.0)
    current_market_price: float = Field(default=0.0, ge=0.0)
    current_value: float = Field(default=0.0, ge=0.0)
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    active_lots: list[TaxLot] = Field(default_factory=list)


class PortfolioHoldingsReport(BaseModel):
    """Complete portfolio statement with active holdings, capital, and tax gains."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    as_of_date: date
    holdings: list[HoldingSummary] = Field(default_factory=list)
    total_invested: float = 0.0
    total_current_value: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_stcg: float = 0.0
    total_ltcg: float = 0.0


class DhanHoldingItem(BaseModel):
    """Raw holding entry as returned by Dhan /holdings endpoint."""

    model_config = ConfigDict(extra="ignore")

    exchange: str = "NSE"
    tradingSymbol: str
    securityId: str
    isin: str
    totalQty: int
    dpQty: int
    t1Qty: int = 0
    availableQty: int
    collateralQty: int = 0
    avgCostPrice: float


class HoldingReconciliationItem(BaseModel):
    """Comparison item between local ledger and broker holdings."""

    model_config = ConfigDict(frozen=True)

    security_id: str
    isin: str
    trading_symbol: str
    local_quantity: int
    broker_quantity: int
    quantity_matched: bool
    local_average_cost: float
    broker_average_cost: float
    cost_matched: bool
    cost_diff: float
    status: str  # "MATCHED", "QUANTITY_MISMATCH", "COST_DRIFT", "MISSING_LOCAL", "MISSING_BROKER"
    notes: str = ""


class ReconciliationReport(BaseModel):
    """Result of reconciling local ledger against broker holdings statement."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    reconciled_at: datetime
    all_matched: bool
    total_items: int
    matched_items: int
    discrepancy_count: int
    items: list[HoldingReconciliationItem] = Field(default_factory=list)
