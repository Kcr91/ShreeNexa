"""REST API endpoints for Paper Trading portfolio, orders, positions, and trades."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.backtest.grading import StrategyHorizon, StrategyScorecard
from app.backtest.models import BacktestPerformanceMetrics
from app.engine.contracts import FillEvent, OrderSide
from app.paper.adapter import calculate_paper_metrics, evaluate_paper_scorecard
from app.paper.broker import paper_broker
from app.paper.divergence import (
    DivergenceTolerances,
    SessionDivergenceReport,
    generate_account_divergence_report,
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
)
from app.paper.reconciliation import PortfolioSummary, reconcile_portfolio
from app.paper.repository import paper_repository

router = APIRouter(prefix="/api/v1/paper", tags=["Paper Trading"])

_coordinators: dict[str, MultiStrategyPaperCoordinator] = {}


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


class InitMultiStrategyRequest(BaseModel):
    """Payload to initialize a multi-strategy paper trading portfolio."""

    account_id: str = "default"
    total_capital: float = Field(default=1000000.0, ge=1000.0)
    allocations: list[StrategyAllocationConfig]
    shared_caps: SharedAccountCaps | None = None


class SubmitStrategyOrderPayload(BaseModel):
    """Payload to route an order to an isolated strategy book."""

    account_id: str = "default"
    strategy_id: str
    symbol: str
    security_id: str
    side: PaperOrderSide
    order_type: PaperOrderType
    quantity: int = Field(gt=0)
    price: float | None = None
    trigger_price: float | None = None


class KillSwitchRequest(BaseModel):
    """Payload to activate or deactivate the global kill switch."""

    account_id: str = "default"
    action: str = Field(pattern="^(trigger|reset)$")
    reason: str = "Manual emergency halt"


@router.post("/multi-strategy/init", response_model=MultiStrategyStatus)
def init_multi_strategy(payload: InitMultiStrategyRequest) -> MultiStrategyStatus:
    """Initialize a multi-strategy paper trading portfolio with isolated capital pools."""
    coord = MultiStrategyPaperCoordinator(
        account_id=payload.account_id,
        total_capital=payload.total_capital,
        allocations=payload.allocations,
        shared_caps=payload.shared_caps,
        repository=paper_repository,
    )
    _coordinators[payload.account_id] = coord
    return coord.get_status()


@router.post("/multi-strategy/orders", response_model=PaperOrder)
def submit_strategy_order(payload: SubmitStrategyOrderPayload) -> PaperOrder:
    """Submit an order to an isolated strategy under shared account caps."""
    coord = _coordinators.get(payload.account_id)
    if not coord:
        raise HTTPException(
            status_code=404,
            detail=(
                "Multi-strategy paper coordinator not initialized for account "
                f"'{payload.account_id}'"
            ),
        )

    order_id = f"ord-strat-{uuid.uuid4().hex[:8]}"
    order = PaperOrder(
        order_id=order_id,
        account_id=f"{payload.account_id}:{payload.strategy_id}",
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        security_id=payload.security_id,
        side=payload.side,
        order_type=payload.order_type,
        quantity=payload.quantity,
        price=payload.price,
        trigger_price=payload.trigger_price,
    )
    return coord.submit_strategy_order(payload.strategy_id, order)


@router.get("/multi-strategy/status", response_model=MultiStrategyStatus)
def get_multi_strategy_status(account_id: str = "default") -> MultiStrategyStatus:
    """Get real-time status of all strategy books and shared risk caps."""
    coord = _coordinators.get(account_id)
    if not coord:
        raise HTTPException(
            status_code=404,
            detail=f"Multi-strategy paper coordinator not found for account '{account_id}'",
        )
    return coord.get_status()


@router.post("/multi-strategy/kill-switch")
def handle_kill_switch(payload: KillSwitchRequest) -> dict[str, Any]:
    """Trigger or reset global emergency kill switch across all strategies."""
    coord = _coordinators.get(payload.account_id)
    if not coord:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Multi-strategy paper coordinator not found for account '{payload.account_id}'"
            ),
        )
    if payload.action == "trigger":
        coord.trigger_kill_switch(reason=payload.reason)
        return {
            "account_id": payload.account_id,
            "kill_switch_active": True,
            "action": "triggered",
        }
    coord.reset_kill_switch()
    return {
        "account_id": payload.account_id,
        "kill_switch_active": False,
        "action": "reset",
    }


@router.get("/metrics", response_model=BacktestPerformanceMetrics)
def get_paper_metrics(
    account_id: str = "default",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> BacktestPerformanceMetrics:
    """Calculate Epic 3 performance metrics for a paper portfolio without calculation forks."""
    return calculate_paper_metrics(
        account_id=account_id,
        repository=paper_repository,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/scorecard", response_model=StrategyScorecard)
def get_paper_scorecard(
    account_id: str = "default",
    strategy_name: str = "Paper Forward Test",
    horizon: StrategyHorizon = StrategyHorizon.POSITIONAL,
) -> StrategyScorecard:
    """Evaluate Epic 3 scorecard and deployment gates for a forward-tested paper strategy."""
    return evaluate_paper_scorecard(
        account_id=account_id,
        strategy_name=strategy_name,
        horizon=horizon,
        repository=paper_repository,
    )


class DivergenceReportRequest(BaseModel):
    account_id: str
    strategy_name: str = "Live Forward Test Strategy"
    backtest_fills: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Serialized FillEvent items from replay backtest",
    )
    paper_signals: list[dict[str, Any]] = Field(default_factory=list)
    backtest_signals: list[dict[str, Any]] = Field(default_factory=list)
    tolerances: DivergenceTolerances | None = None


@router.post("/divergence-report", response_model=SessionDivergenceReport)
def create_divergence_report(payload: DivergenceReportRequest) -> SessionDivergenceReport:
    """Generate same-session paper-vs-backtest divergence report."""
    parsed_bt_fills: list[FillEvent] = []
    for f in payload.backtest_fills:
        side_val = OrderSide.BUY if str(f.get("side", "")).upper() == "BUY" else OrderSide.SELL
        ts = f.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif not isinstance(ts, datetime):
            ts = datetime.now(UTC)
        parsed_bt_fills.append(
            FillEvent(
                order_id=str(f.get("order_id", "")),
                security_id=str(f.get("security_id", "")),
                exchange_segment=str(f.get("exchange_segment", "NSE_EQ")),
                side=side_val,
                quantity=int(f.get("quantity", 0)),
                price=float(f.get("price", 0.0)),
                timestamp=ts,
                brokerage=float(f.get("brokerage", 0.0)),
                taxes=float(f.get("taxes", 0.0)),
                slippage=float(f.get("slippage", 0.0)),
            )
        )

    return generate_account_divergence_report(
        account_id=payload.account_id,
        strategy_name=payload.strategy_name,
        backtest_fills=parsed_bt_fills,
        paper_signals=payload.paper_signals,
        backtest_signals=payload.backtest_signals,
        tolerances=payload.tolerances,
        repository=paper_repository,
    )
