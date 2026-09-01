"""REST API endpoints for monitoring Dhan WebSocket connection budget and active leases."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.feedd.budget import (
    BudgetStatus,
    ConnectionBudgetManager,
    get_connection_budget_manager,
)

router = APIRouter(prefix="/api/v1/feed", tags=["feed"])


def get_budget_manager() -> ConnectionBudgetManager:
    """Dependency providing the central connection budget manager."""
    return get_connection_budget_manager()


BudgetManagerDep = Annotated[ConnectionBudgetManager, Depends(get_budget_manager)]


@router.get("/budget", response_model=BudgetStatus)
def get_budget_status(manager: BudgetManagerDep) -> BudgetStatus:
    """Retrieve current Dhan WebSocket connection budget capacity and active leases."""
    return manager.get_status()
