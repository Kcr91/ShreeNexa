"""Unit tests for index and constituent heatmaps with breadth and weighting source."""

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


def test_index_level_heatmap_endpoint() -> None:
    resp = client.get("/api/v1/heatmap/indices")
    assert resp.status_code == 200
    cells = resp.json()
    assert len(cells) >= 6

    names = {c["index_name"] for c in cells}
    assert "NIFTY 50" in names
    assert "NIFTY BANK" in names
    assert "NIFTY IT" in names

    for c in cells:
        assert "futures_basis" in c
        assert "oi_change_pct" in c
        assert "weighting_source" in c
        assert c["weight"] > 0
        assert c["advances"] + c["declines"] + c["unchanged"] > 0


def test_constituent_level_heatmap_and_breadth(db_engine: Engine) -> None:
    app.dependency_overrides[get_db_engine] = lambda: db_engine
    try:
        # Ensure fallback seeds are ingested
        client.post("/api/v1/indices/seed-fallback")

        resp = client.get("/api/v1/heatmap/NIFTY 50/constituents")
        assert resp.status_code == 200
        data = resp.json()

        assert data["index_name"] == "NIFTY 50"
        constituents = data["constituents"]
        assert len(constituents) > 0

        # Invariant: cell totals match 100.0%
        total_weight = sum(c["weight"] for c in constituents)
        assert total_weight == pytest.approx(100.0, abs=0.1)
        assert data["cell_total_weight"] == pytest.approx(100.0, abs=0.1)

        # Invariant: Market breadth matches exact sum
        breadth = data["breadth"]
        assert breadth["total_count"] == len(constituents)
        assert breadth["advances"] + breadth["declines"] + breadth["unchanged"] == len(constituents)
        assert breadth["advance_decline_ratio"] >= 0.0
        assert 0.0 <= breadth["pct_above_prev_close"] <= 100.0
        assert breadth["sentiment_posture"] in {
            "Strong Bullish",
            "Moderate Bullish",
            "Neutral",
            "Moderate Bearish",
            "Strong Bearish",
        }

        # Invariant: transparent weighting source & fallback labelling
        for c in constituents:
            assert c["weighting_source"] in {
                "OFFICIAL_NSE",
                "FALLBACK_EQUAL_WEIGHT",
                "FREE_FLOAT_MCAP",
            }
            if c["is_weight_fallback"]:
                assert c["weighting_source"] == "FALLBACK_EQUAL_WEIGHT"
    finally:
        app.dependency_overrides.clear()
