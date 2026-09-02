"""Unit tests for the watchlists REST API endpoints."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_list_watchlists_returns_defaults() -> None:
    resp = client.get("/api/v1/watchlists")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    names = {w["name"] for w in data}
    assert "NIFTY 50" in names
    assert "BANK NIFTY F&O" in names


def test_create_and_delete_custom_watchlist() -> None:
    # 1. Create
    payload = {
        "name": "Breakout Strategy Watchlist",
        "description": "Momentum breakouts",
        "columns": ["symbol", "ltp", "changePct", "volume"],
        "items": [
            {"symbol": "TATASTEEL", "segment": "NSE_EQ", "security_id": "3499"},
            {"symbol": "SBIN", "segment": "NSE_EQ", "security_id": "3045"},
        ],
    }
    create_resp = client.post("/api/v1/watchlists", json=payload)
    assert create_resp.status_code == 201
    wl = create_resp.json()
    wl_id = wl["id"]
    assert wl["name"] == "Breakout Strategy Watchlist"
    assert len(wl["items"]) == 2
    assert wl["items"][0]["order"] == 0
    assert wl["items"][1]["order"] == 1

    # 2. Retrieve
    get_resp = client.get(f"/api/v1/watchlists/{wl_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == wl_id

    # 3. Delete
    del_resp = client.delete(f"/api/v1/watchlists/{wl_id}")
    assert del_resp.status_code == 204

    # 4. Verify gone
    get_gone = client.get(f"/api/v1/watchlists/{wl_id}")
    assert get_gone.status_code == 404


def test_cannot_delete_default_watchlist() -> None:
    resp = client.delete("/api/v1/watchlists/wl-nifty50")
    assert resp.status_code == 400
    assert "Default built-in watchlists cannot be deleted" in resp.json()["detail"]


def test_add_remove_and_reorder_symbols() -> None:
    # Create test watchlist
    create_resp = client.post(
        "/api/v1/watchlists",
        json={
            "name": "Reorder Test Watchlist",
            "items": [
                {"symbol": "AAA", "segment": "NSE_EQ", "security_id": "1"},
                {"symbol": "BBB", "segment": "NSE_EQ", "security_id": "2"},
                {"symbol": "CCC", "segment": "NSE_EQ", "security_id": "3"},
            ],
        },
    )
    wl_id = create_resp.json()["id"]

    # 1. Add symbol
    add_resp = client.post(
        f"/api/v1/watchlists/{wl_id}/symbols",
        json={"symbol": "DDD", "segment": "NSE_EQ", "security_id": "4"},
    )
    assert add_resp.status_code == 200
    items = add_resp.json()["items"]
    assert len(items) == 4
    assert items[-1]["symbol"] == "DDD"
    assert items[-1]["order"] == 3

    # 2. Reorder symbols stably: ["CCC", "AAA", "DDD", "BBB"]
    reorder_resp = client.post(
        f"/api/v1/watchlists/{wl_id}/reorder",
        json={"ordered_symbols": ["CCC", "AAA", "DDD", "BBB"]},
    )
    assert reorder_resp.status_code == 200
    reordered_items = reorder_resp.json()["items"]
    symbols_order = [item["symbol"] for item in reordered_items]
    assert symbols_order == ["CCC", "AAA", "DDD", "BBB"]
    for idx, item in enumerate(reordered_items):
        assert item["order"] == idx

    # 3. Remove symbol "AAA"
    del_sym_resp = client.delete(f"/api/v1/watchlists/{wl_id}/symbols/AAA")
    assert del_sym_resp.status_code == 200
    remaining_symbols = [item["symbol"] for item in del_sym_resp.json()["items"]]
    assert remaining_symbols == ["CCC", "DDD", "BBB"]
    for idx, item in enumerate(del_sym_resp.json()["items"]):
        assert item["order"] == idx

    # Cleanup
    client.delete(f"/api/v1/watchlists/{wl_id}")
