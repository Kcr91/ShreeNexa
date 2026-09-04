"""REST and WebSocket API endpoints for Dhan feed monitoring and browser market data fan-out."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.ws import get_market_data_fanout_manager
from app.feedd.budget import (
    BudgetStatus,
    ConnectionBudgetManager,
    get_connection_budget_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feed", tags=["feed"])


def get_budget_manager() -> ConnectionBudgetManager:
    """Dependency providing the central connection budget manager."""
    return get_connection_budget_manager()


BudgetManagerDep = Annotated[ConnectionBudgetManager, Depends(get_budget_manager)]


@router.get("/budget", response_model=BudgetStatus)
def get_budget_status(manager: BudgetManagerDep) -> BudgetStatus:
    """Retrieve current Dhan WebSocket connection budget capacity and active leases."""
    return manager.get_status()


@router.get("/metrics")
def get_fanout_metrics() -> dict[str, Any]:
    """Retrieve browser WebSocket fan-out telemetry, session counts, and backpressure metrics."""
    manager = get_market_data_fanout_manager()
    return manager.get_metrics()
