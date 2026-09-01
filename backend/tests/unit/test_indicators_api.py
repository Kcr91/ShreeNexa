"""Unit tests for technical indicator catalog discovery and formula validation API."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_list_indicators_endpoint() -> None:
    """GET /api/v1/indicators returns all registered indicators with metadata."""
    res = client.get("/api/v1/indicators")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 12

    names = [ind["name"] for ind in data]
    assert "sma" in names
    assert "rsi" in names
    assert "macd" in names
    assert "bollinger_bands" in names

    # Check SMA metadata schema
    sma_meta = next(ind for ind in data if ind["name"] == "sma")
    assert sma_meta["family"] == "trend"
    assert "period" in sma_meta["default_params"]
    assert "column" in sma_meta["default_params"]


def test_get_single_indicator_endpoint() -> None:
    """GET /api/v1/indicators/{name} returns metadata or 404."""
    res_ok = client.get("/api/v1/indicators/rsi")
    assert res_ok.status_code == 200
    rsi_meta = res_ok.json()
    assert rsi_meta["name"] == "rsi"
    assert rsi_meta["family"] == "momentum"

    res_404 = client.get("/api/v1/indicators/nonexistent_indicator")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()


def test_validate_formula_valid_expression() -> None:
    """POST /api/v1/indicators/validate-formula validates valid indicator signals."""
    payload = {"formula": "crossover(sma(close, 5), sma(close, 20))"}
    res = client.post("/api/v1/indicators/validate-formula", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert "close" in data["identifiers"]
    assert data["error"] is None


def test_validate_formula_adversarial_rejected() -> None:
    """POST /api/v1/indicators/validate-formula rejects sandbox attacks cleanly."""
    payload = {"formula": "__import__('os').system('echo pwned')"}
    res = client.post("/api/v1/indicators/validate-formula", json=payload)
    assert res.status_code == 200
    data = res.json()
    err_lower = data["error"].lower()
    assert "security" in err_lower or "forbidden" in err_lower or "disallowed" in err_lower


def test_validate_formula_lookahead_shift_rejected() -> None:
    """POST /api/v1/indicators/validate-formula rejects negative shift lookahead."""
    payload = {"formula": "shift(close, -1)"}
    res = client.post("/api/v1/indicators/validate-formula", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert "lookahead" in data["error"].lower()


def test_indicator_api_alias_routes() -> None:
    """Verify alias route prefix /api/indicators works interchangeably."""
    res = client.get("/api/indicators")
    assert res.status_code == 200
    assert len(res.json()) >= 12

    val_res = client.post(
        "/api/indicators/validate-formula", json={"formula": "close > sma(close, 10)"}
    )
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True
