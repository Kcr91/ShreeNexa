"""Unit and API tests for Dhan WebSocket connection budget FastAPI endpoint."""

from __future__ import annotations

from app.feedd.budget import (
    ConnectionBudgetConfig,
    ConnectionBudgetManager,
    PoolMode,
    SocketType,
)
from app.main import app
from fastapi.testclient import TestClient


def test_api_get_budget_status() -> None:
    """Verify GET /api/v1/feed/budget endpoint returns real budget status and active leases."""
    cfg = ConnectionBudgetConfig(
        pool_mode=PoolMode.SHARED,
        total_capacity=5,
        feed_capacity=3,
        depth_capacity=2,
    )
    mgr = ConnectionBudgetManager(config=cfg)

    from app.api.feed import get_budget_manager

    app.dependency_overrides[get_budget_manager] = lambda: mgr

    # Acquire 1 feed socket
    lease = mgr.acquire(SocketType.FEED, metadata={"purpose": "market_watch"})

    with TestClient(app) as client:
        response = client.get("/api/v1/feed/budget")
        assert response.status_code == 200
        data = response.json()

        assert data["pool_mode"] == "shared"
        assert data["total_capacity"] == 5
        assert data["feed_capacity"] == 3
        assert data["depth_capacity"] == 2
        assert data["active_feed"] == 1
        assert data["active_depth"] == 0
        assert data["total_active"] == 1
        assert data["available_feed"] == 2
        assert data["available_depth"] == 2
        assert len(data["active_leases"]) == 1
        assert data["active_leases"][0]["lease_id"] == lease.lease_id

    mgr.release(lease)
    app.dependency_overrides.clear()
