"""REST API endpoints for Paper Trading portfolio, orders, positions, and trades."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.paper.broker import paper_broker
from app.paper.models import (
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
    PaperPosition,
)
from app.paper.reconciliation import PortfolioSummary, reconcile_portfolio
from app.paper.repository import paper_repository

router = APIRouter(prefix="/api/v1/paper", tags=["Paper Trading"])


class CreateAccountRequest(BaseModel):
    """Payload to initialize or reset paper trading account."""

    account_id: str = "default"
    name: str = "Paper Trading Account"
    initial_capital: float = Field(default=1_000_000.0, gt=0)


class SubmitPaperOrderRequest(BaseModel):
    """Payload to place a new paper order."""

    account_id: str = "default"
    strategy_id: str | None = None
    symbol: str
    segment: str = "NSE_EQ"
    security_id: str
    side: PaperOrderSide
    order_type: PaperOrderType
    quantity: int = Field(gt=0)
    price: float | None = None
    trigger_price: float | None = None


@router.post("/accounts", response_model=PaperAccount)
def create_or_reset_account(req: CreateAccountRequest) -> PaperAccount:
    """Create or reset a virtual paper trading account."""
    acc = PaperAccount(
        account_id=req.account_id,
        name=req.name,
        initial_capital=req.initial_capital,
        cash_balance=req.initial_capital,
    )
    paper_repository.save_account(acc)
    return acc


@router.get("/accounts/{account_id}", response_model=PaperAccount)
def get_account(account_id: str) -> PaperAccount:
    """Retrieve virtual paper trading account details."""
    acc = paper_repository.get_account(account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found")
    return acc


@router.post("/orders", response_model=PaperOrder)
def submit_order(req: SubmitPaperOrderRequest) -> PaperOrder:
    """Submit a paper order into execution queue."""
    order = PaperOrder(
        order_id=f"porder-{req.security_id}-{req.side}-{int(1000 * req.quantity)}",
        account_id=req.account_id,
        strategy_id=req.strategy_id,
        symbol=req.symbol,
        segment=req.segment,
        security_id=req.security_id,
        side=req.side,
        order_type=req.order_type,
        quantity=req.quantity,
        price=req.price,
        trigger_price=req.trigger_price,
    )
    paper_broker.submit_orders([order])
    return order


@router.delete("/orders/{order_id}")
def cancel_order(order_id: str) -> dict[str, Any]:
    """Cancel an active pending paper order."""
    success = paper_broker.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not cancel order '{order_id}'")
    return {"order_id": order_id, "status": "CANCELLED"}


@router.get("/orders", response_model=list[PaperOrder])
def list_orders(
    account_id: str = "default", status: PaperOrderStatus | None = None
) -> list[PaperOrder]:
    """List paper orders for an account."""
    return paper_repository.list_orders(account_id=account_id, status=status)


@router.get("/positions", response_model=list[PaperPosition])
def list_positions(account_id: str = "default") -> list[PaperPosition]:
    """List active open positions."""
    return paper_repository.list_positions(account_id=account_id)


@router.get("/fills", response_model=list[PaperFill])
def list_fills(account_id: str = "default") -> list[PaperFill]:
    """List trade fills for an account."""
    return paper_repository.list_fills(account_id=account_id)


@router.get("/portfolio/summary", response_model=PortfolioSummary)
def get_portfolio_summary(account_id: str = "default") -> PortfolioSummary:
    """Get aggregated portfolio status and MTM summary."""
    return reconcile_portfolio(account_id=account_id, repository=paper_repository)


@router.get("/reconcile", response_model=PortfolioSummary)
def get_reconciliation_report(account_id: str = "default") -> PortfolioSummary:
    """Run mathematical accounting reconciliation across orders, fills, and cash balance."""
    return reconcile_portfolio(account_id=account_id, repository=paper_repository)
