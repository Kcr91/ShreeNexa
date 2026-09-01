"""Unit and API tests for index constituent universe FastAPI endpoints."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from app.api.universe import get_db_engine
from app.contracts import heartbeat as hb
from app.main import app
from app.marketdata.universe import ingest_fallback_constituents
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine


@pytest.fixture
def db_engine() -> Generator[Engine]:
    try:
        engine = hb.make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()
    except Exception as exc:
        pytest.skip(f"Database not available for API tests: {exc}")


@pytest.fixture
def client(db_engine: Engine) -> Generator[TestClient]:
    app.dependency_overrides[get_db_engine] = lambda: db_engine
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM index_constituent"))
    ingest_fallback_constituents(db_engine)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_list_indices(client: TestClient) -> None:
    response = client.get("/api/v1/indices")
    assert response.status_code == 200
    indices = response.json()
    assert "NIFTY 50" in indices
    assert "NIFTY BANK" in indices
    assert "NIFTY IT" in indices


def test_api_get_constituents(client: TestClient) -> None:
    response = client.get("/api/v1/indices/NIFTY%2050/constituents?as_of=2026-08-01")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 15
    symbols = [item["symbol"] for item in data]
    assert "HDFCBANK" in symbols
    assert "RELIANCE" in symbols


def test_api_membership_check_member(client: TestClient) -> None:
    response = client.get("/api/v1/indices/NIFTY%2050/membership?symbol=RELIANCE&as_of=2026-08-01")
    assert response.status_code == 200
    data = response.json()
    assert data["is_member"] is True
    assert data["symbol"] == "RELIANCE"
    assert data["source"] == "fallback"


def test_api_membership_check_non_member(client: TestClient) -> None:
    response = client.get(
        "/api/v1/indices/NIFTY%2050/membership?symbol=NON_EXISTENT_STOCK&as_of=2026-08-01"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_member"] is False


def test_api_manual_override(client: TestClient) -> None:
    payload = {
        "index_name": "NIFTY 50",
        "symbol": "CUSTOM_STOCK",
        "is_member": True,
        "effective_date": "2026-08-10",
        "weight": 2.5,
        "sector": "Custom Sector",
    }
    response = client.post("/api/v1/indices/NIFTY%2050/override", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify membership after override
    check_resp = client.get(
        "/api/v1/indices/NIFTY%2050/membership?symbol=CUSTOM_STOCK&as_of=2026-08-10"
    )
    assert check_resp.status_code == 200
    assert check_resp.json()["is_member"] is True
    assert check_resp.json()["source"] == "manual"


def test_api_seed_fallback(client: TestClient) -> None:
    response = client.post("/api/v1/indices/seed-fallback")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["records_ingested"] >= 30
