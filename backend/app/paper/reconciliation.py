"""Portfolio accounting, MTM calculation, and reconciliation engine for Paper Trading."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.paper.models import (
    PaperOrderSide,
    PaperOrderStatus,
)
from app.paper.repository import PaperRepository, paper_repository


class RejectedOrderInfo(BaseModel):
    """Details of a rejected order."""

    model_config = ConfigDict(extra="ignore")

    order_id: str
    symbol: str
    security_id: str
    side: PaperOrderSide
    quantity: int
    reject_reason: str


class PositionSummaryItem(BaseModel):
    """Summary of an open or closed paper position."""

    model_config = ConfigDict(extra="ignore")

    symbol: str
    security_id: str
    segment: str
    quantity: int
    avg_entry_price: float
    current_price: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float


class PortfolioSummary(BaseModel):
    """Aggregated portfolio status and accounting summary."""

    model_config = ConfigDict(extra="ignore")

    account_id: str
    name: str
    initial_capital: float
    cash_balance: float
    blocked_margin: float
    realized_pnl: float
    unrealized_pnl: float
    total_equity: float
    total_transaction_costs: float
    total_orders: int
    working_orders_count: int
    filled_orders_count: int
    rejected_orders_count: int
    total_fills: int
    open_positions_count: int
    rejected_orders: list[RejectedOrderInfo] = Field(default_factory=list)
    positions: list[PositionSummaryItem] = Field(default_factory=list)
    is_reconciled: bool = True
    cash_discrepancy: float = 0.0


def reconcile_portfolio(
    account_id: str,
    repository: PaperRepository | None = None,
) -> PortfolioSummary:
    """Reconcile orders, fills, positions, cash balance, and costs for an account."""
    repo = repository or paper_repository
    account = repo.get_or_create_account(account_id)
    orders = repo.list_orders(account_id)
    fills = repo.list_fills(account_id)
    positions = repo.list_positions(account_id)

    total_costs = 0.0
    computed_cash = account.initial_capital

    for fill in fills:
        total_costs += fill.transaction_cost
        if fill.side == PaperOrderSide.BUY:
            computed_cash -= (fill.quantity * fill.price) + fill.transaction_cost
        else:  # SELL
            computed_cash += (fill.quantity * fill.price) - fill.transaction_cost

    cash_discrepancy = round(abs(computed_cash - account.cash_balance), 2)
    is_reconciled = cash_discrepancy < 0.05

    active_statuses = (PaperOrderStatus.ACCEPTED, PaperOrderStatus.PARTIALLY_FILLED)
    working_orders = [o for o in orders if o.status in active_statuses]
    filled_orders = [o for o in orders if o.status == PaperOrderStatus.FILLED]
    rejected_orders_list: list[RejectedOrderInfo] = []
    for o in orders:
        if o.status == PaperOrderStatus.REJECTED:
            rejected_orders_list.append(
                RejectedOrderInfo(
                    order_id=o.order_id,
                    symbol=o.symbol,
                    security_id=o.security_id,
                    side=o.side,
                    quantity=o.quantity,
                    reject_reason=o.reject_reason or "Order rejected by broker risk filter",
                )
            )

    pos_items: list[PositionSummaryItem] = []
    total_unrealized = 0.0
    for p in positions:
        pos_items.append(
            PositionSummaryItem(
                symbol=p.symbol,
                security_id=p.security_id,
                segment=p.segment,
                quantity=p.quantity,
                avg_entry_price=p.avg_entry_price,
                current_price=p.current_price,
                realized_pnl=round(p.realized_pnl, 2),
                unrealized_pnl=round(p.unrealized_pnl, 2),
                total_pnl=round(p.realized_pnl + p.unrealized_pnl, 2),
            )
        )
        total_unrealized += p.unrealized_pnl

    return PortfolioSummary(
        account_id=account.account_id,
        name=account.name,
        initial_capital=round(account.initial_capital, 2),
        cash_balance=round(account.cash_balance, 2),
        blocked_margin=round(account.blocked_margin, 2),
        realized_pnl=round(account.realized_pnl, 2),
        unrealized_pnl=round(total_unrealized, 2),
        total_equity=round(account.cash_balance + account.blocked_margin + total_unrealized, 2),
        total_transaction_costs=round(total_costs, 2),
        total_orders=len(orders),
        working_orders_count=len(working_orders),
        filled_orders_count=len(filled_orders),
        rejected_orders_count=len(rejected_orders_list),
        total_fills=len(fills),
        open_positions_count=len([p for p in pos_items if p.quantity != 0]),
        rejected_orders=rejected_orders_list,
        positions=pos_items,
        is_reconciled=is_reconciled,
        cash_discrepancy=cash_discrepancy,
    )
