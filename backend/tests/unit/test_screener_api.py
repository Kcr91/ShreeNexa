"""Unit tests for Screener FastAPI endpoints, export formats, and routing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.main import app
from app.screener.models import ScreenerMatch, ScreenerResult
from app.screener.store import screener_store
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    screener_store.clear()


def test_screener_crud_and_run_flow() -> None:
    """Test complete Screener REST lifecycle: Create, Read, List, Run, Export, Route, Delete."""
    payload: dict[str, Any] = {
        "definition": {
            "name": "API Screener",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "RELIANCE"}],
            },
            "timeframe": "1d",
            "as_of": "2026-09-01T15:30:00Z",
            "lookback_bars": 50,
            "indicators": {
                "sma5": {"fn": "SMA", "params": {"period": 5}, "source": "close"},
            },
            "filter": {
                "node": "IndicatorCompare",
                "left": {"field": "close"},
                "op": ">",
                "right": {"ref": "sma5"},
            },
        },
        "schedule": "0 16 * * 1-5",
    }

    # 1. Create
    resp = client.post("/api/v1/screeners", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    screener_id = created["id"]
    assert created["name"] == "API Screener"
    assert created["schedule"] == "0 16 * * 1-5"

    # 2. Get
    resp = client.get(f"/api/v1/screeners/{screener_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == screener_id

    # 3. List
    resp = client.get("/api/v1/screeners")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 4. Run
    resp = client.post(f"/api/v1/screeners/{screener_id}/run")
    assert resp.status_code == 200
    run_snap = resp.json()
    run_id = run_snap["run_id"]
    assert run_snap["screener_id"] == screener_id

    # 5. List Runs
    resp = client.get(f"/api/v1/screeners/{screener_id}/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 6. Get Run Snapshot
    resp = client.get(f"/api/v1/screeners/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == run_id

    # 7. Export CSV
    resp = client.post(f"/api/v1/screeners/runs/{run_id}/export?format=csv")
    assert resp.status_code == 200
    assert "security_id,symbol,exchange_segment" in resp.text

    # 8. Export JSON
    resp = client.post(f"/api/v1/screeners/runs/{run_id}/export?format=json")
    assert resp.status_code == 200
    assert "matches" in resp.json()

    # 9. Route to Watchlist
    resp = client.post(
        f"/api/v1/screeners/runs/{run_id}/route-watchlist",
        json={"watchlist_name": "Breakout_Watchlist"},
    )
    assert resp.status_code == 200
    assert resp.json()["watchlist_name"] == "Breakout_Watchlist"

    # 10. Route to Strategy Universe (empty matches returns 400)
    resp = client.post(f"/api/v1/screeners/runs/{run_id}/route-universe")
    assert resp.status_code == 400

    # 11. Delete
    resp = client.delete(f"/api/v1/screeners/{screener_id}")
    assert resp.status_code == 204

    # Verify not found after delete
    resp = client.get(f"/api/v1/screeners/{screener_id}")
    assert resp.status_code == 404


def test_screener_export_and_routing_with_matches() -> None:
    """Test CSV/JSON export formatting and routing with populated matches."""
    sample_match = ScreenerMatch(
        security_id="1333",
        symbol="HDFCBANK",
        exchange_segment="NSE_EQ",
        as_of=datetime(2026, 9, 1, 15, 30, tzinfo=UTC),
        indicator_values={"rsi": 65.4, "sma5": 1650.0},
        rank_value=65.4,
    )
    result = ScreenerResult(
        as_of=datetime(2026, 9, 1, 15, 30, tzinfo=UTC),
        matches=[sample_match],
        total_universe_size=1,
        evaluated_count=1,
        matched_count=1,
    )

    snap = screener_store.save_run_snapshot("test-s1", "Test Screener", result)

    # Test CSV export endpoint
    resp = client.post(f"/api/v1/screeners/runs/{snap.run_id}/export?format=csv")
    assert resp.status_code == 200
    lines = resp.text.strip().split("\n")
    assert len(lines) == 2
    assert "HDFCBANK" in lines[1]
    assert "65.4" in lines[1]

    # Test JSON export endpoint
    resp = client.post(f"/api/v1/screeners/runs/{snap.run_id}/export?format=json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_count"] == 1
    assert data["matches"][0]["symbol"] == "HDFCBANK"

    # Test Route to Strategy Universe with populated matches
    resp = client.post(f"/api/v1/screeners/runs/{snap.run_id}/route-universe")
    assert resp.status_code == 200
    univ_data = resp.json()
    assert univ_data["type"] == "static"
    assert len(univ_data["instruments"]) == 1
    assert univ_data["instruments"][0]["security_id"] == "1333"
