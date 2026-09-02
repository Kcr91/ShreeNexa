"""Unit tests for sector catalog, index constituent drill-in, and visible provenance."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_get_sector_catalog() -> None:
    resp = client.get("/api/v1/indices/sectors/catalog")
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 8
    sectors = {c["sector"] for c in catalog}
    assert "Banking" in sectors
    assert "Information Technology" in sectors
    assert "Automotive" in sectors


def test_index_drill_in_with_visible_fallback_provenance() -> None:
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


def test_historical_point_in_time_query() -> None:
    # Query with a historical date in the past
    resp = client.get("/api/v1/indices/NIFTY 50/drill-in?as_of=2024-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["as_of"] == "2024-01-01"
