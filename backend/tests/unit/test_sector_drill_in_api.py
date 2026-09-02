"""Unit tests for sector catalog, index constituent drill-in, and visible provenance."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from app.api.universe import get_db_engine
from app.contracts import heartbeat as hb
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

client = TestClient(app)


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


def test_get_sector_catalog() -> None:
    resp = client.get("/api/v1/indices/sectors/catalog")
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 8
    sectors = {c["sector"] for c in catalog}
    assert "Banking" in sectors
    assert "Information Technology" in sectors
    assert "Automotive" in sectors


def test_index_drill_in_with_visible_fallback_provenance(db_engine: Engine) -> None:
    app.dependency_overrides[get_db_engine] = lambda: db_engine
    try:
        # 1. Seed fallback constituents into database
        seed_resp = client.post("/api/v1/indices/seed-fallback")
        assert seed_resp.status_code == 200

        # 2. Query drill-in for NIFTY 50
        resp = client.get("/api/v1/indices/NIFTY 50/drill-in")
        assert resp.status_code == 200
        drill_in = resp.json()

        assert drill_in["index_name"] == "NIFTY 50"
        assert drill_in["total_constituents"] > 0
        # Invariant: transparent provenance is explicitly visible
        assert "provenance_sources" in drill_in
        assert len(drill_in["provenance_sources"]) > 0
        # Fallback seed is explicitly flagged as fallback
        assert drill_in["has_fallback"] is True
        assert any("FALLBACK" in s.upper() for s in drill_in["provenance_sources"])

        # Sector weights breakdown computed
        assert len(drill_in["sector_weights"]) > 0
        constituents = drill_in["constituents"]
        assert any(c["symbol"] == "RELIANCE" for c in constituents)
    finally:
        app.dependency_overrides.clear()


def test_historical_point_in_time_query(db_engine: Engine) -> None:
    app.dependency_overrides[get_db_engine] = lambda: db_engine
    try:
        # Query with a historical date in the past
        resp = client.get("/api/v1/indices/NIFTY 50/drill-in?as_of=2024-01-01")
        assert resp.status_code == 200
        data = resp.json()
        assert data["as_of"] == "2024-01-01"
    finally:
        app.dependency_overrides.clear()
