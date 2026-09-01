"""Unit and API tests for Dhan instrument master FastAPI endpoints."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from app.api.instruments import get_db_engine
from app.contracts import heartbeat as hb
from app.dhan.instruments import ingest_instruments
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_CSV_PATH = FIXTURES_DIR / "dhan_scrip_master_sample.csv"


@pytest.fixture
def db_engine() -> Generator[Engine]:
    try:
        engine = hb.make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()
    except Exception as exc:
        pytest.skip(f"Database not available for API test: {exc}")


@pytest.fixture
def client(db_engine: Engine) -> Generator[TestClient]:
    app.dependency_overrides[get_db_engine] = lambda: db_engine
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM instrument"))
    ingest_instruments(db_engine, SAMPLE_CSV_PATH)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_search_instruments(client: TestClient) -> None:
    response = client.get("/api/v1/instruments/search?query=RELIANCE")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    symbols = [item["symbol"] for item in data]
    assert "RELIANCE" in symbols


def test_api_search_with_filters(client: TestClient) -> None:
    response = client.get("/api/v1/instruments/search?query=RELIANCE&exchange_segment=NSE_EQ")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["security_id"] == "2885"
    assert data[0]["exchange_segment"] == "NSE_EQ"


def test_api_get_single_instrument_success(client: TestClient) -> None:
    response = client.get("/api/v1/instruments/NSE_EQ/2885")
    assert response.status_code == 200
    data = response.json()
    assert data["security_id"] == "2885"
    assert data["symbol"] == "RELIANCE"
    assert data["lot_size"] == 1


def test_api_get_single_instrument_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/instruments/NSE_EQ/999999999")
    assert response.status_code == 404
    assert "Instrument not found" in response.json()["detail"]


def test_api_list_segments(client: TestClient) -> None:
    response = client.get("/api/v1/instruments/segments")
    assert response.status_code == 200
    segments = response.json()
    assert "NSE_EQ" in segments
    assert "NSE_FNO" in segments
    assert "IDX_I" in segments


def test_api_option_chain(client: TestClient) -> None:
    response = client.get(
        "/api/v1/instruments/options/chain?underlying_id=13&expiry_date=2026-08-28"
    )
    assert response.status_code == 200
    chain = response.json()
    assert len(chain) == 4
    # Sorted by strike ascending
    strikes = [float(item["strike_price"]) for item in chain]
    assert strikes == [24500.0, 24500.0, 25000.0, 25000.0]


def test_api_option_expiries(client: TestClient) -> None:
    response = client.get("/api/v1/instruments/options/expiries?underlying_id=13")
    assert response.status_code == 200
    expiries = response.json()
    assert expiries == ["2026-08-28"]
