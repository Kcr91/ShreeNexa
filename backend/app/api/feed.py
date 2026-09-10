"""REST and WebSocket API endpoints for Dhan feed monitoring and browser market data fan-out."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

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


@router.get("/status")
def get_feed_status() -> dict[str, Any]:
    """Retrieve measured feedd health from shared hot state."""
    records = get_market_data_fanout_manager().hot_cache.get_all_feed_health()
    connected = any(record.is_connected and not record.is_stale for record in records)
    return {
        "status": "LIVE" if connected else "UNAVAILABLE",
        "is_connected": connected,
        "total_packets": sum(record.total_packets for record in records),
        "subscriptions_count": sum(record.subscribed_count for record in records),
        "sockets": [record.model_dump() for record in records],
    }


@router.get("/quotes")
def get_feed_quotes() -> dict[str, Any]:
    """Retrieve only requested, verified Dhan quote records."""
    cache = get_market_data_fanout_manager().hot_cache
    requested = sorted(cache.get_requested_subscriptions())
    quotes = cache.get_multi_quotes(requested)
    return {
        "status": "success" if quotes else "unavailable",
        "quotes": {
            f"{segment}:{security_id}": quote.model_dump()
            for (segment, security_id), quote in quotes.items()
        },
    }


@router.post("/quotes/sync")
async def trigger_quotes_sync() -> dict[str, Any]:
    """Reject API-owned broker synchronization; feedd owns all Dhan calls."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Quote synchronization is owned by feedd and follows active subscriptions",
    )
