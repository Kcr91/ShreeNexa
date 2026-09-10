"""Unit tests for index and constituent heatmaps with breadth and weighting source."""

from __future__ import annotations

import time
from collections.abc import Generator

import pytest
from app.api.heatmap import load_official_records_for_index
from app.api.universe import get_db_engine
from app.api.ws import configure_market_data_hot_cache, get_market_data_fanout_manager
from app.contracts import heartbeat as hb
from app.feedd import CachedQuote
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
    configure_market_data_hot_cache(use_redis=False)
    get_market_data_fanout_manager().hot_cache.set_quote(
        CachedQuote(
            segment="0",
            security_id="13",
            ltp=22550.0,
            previous_close=22000.0,
            received_at=time.time(),
            source="DHAN_REST",
            market_state="MARKET_CLOSED",
        )
    )
    resp = client.get("/api/v1/heatmap/indices")
    assert resp.status_code == 200
    cells = resp.json()
    assert len(cells) >= 6

    names = {c["index_name"] for c in cells}
    assert "NIFTY 50" in names
    assert "NIFTY BANK" in names
    assert "NIFTY IT" in names

    nifty = next(c for c in cells if c["index_name"] == "NIFTY 50")
    assert nifty["ltp"] == 22550.0
    assert nifty["change_pct"] == 2.5
    assert nifty["source"] == "DHAN_REST"
    assert nifty["market_state"] == "MARKET_CLOSED"

    unavailable = next(c for c in cells if c["index_name"] == "NIFTY BANK")
    assert unavailable["ltp"] is None
    assert unavailable["change_pct"] is None
    assert unavailable["market_state"] == "UNAVAILABLE"
    assert unavailable["error"]


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

        # No quote cache was populated for constituents: breadth and values must
        # remain explicitly unavailable rather than becoming seeded market data.
        breadth = data["breadth"]
        assert breadth["total_count"] == 0
        assert breadth["advances"] == 0
        assert breadth["declines"] == 0
        assert breadth["unchanged"] == 0
        assert data["market_state"] == "UNAVAILABLE"
        assert data["error"]
        assert all(c["ltp"] is None for c in constituents)
        assert all(c["change_pct"] is None for c in constituents)

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


def test_official_nse_constituents_fallback() -> None:
    # Test that NIFTY AUTO constituents come from official NSE scraped catalog
    records_auto = load_official_records_for_index("NIFTY AUTO")
    assert len(records_auto) == 15
    auto_symbols = {r.symbol for r in records_auto}
    assert "MARUTI" in auto_symbols
    assert "BAJAJ-AUTO" in auto_symbols
    assert "M&M" in auto_symbols
    assert "HEROMOTOCO" in auto_symbols
    assert "EICHERMOT" in auto_symbols
    for r in records_auto:
        assert r.source == "OFFICIAL_NSE"

    # Test NIFTY BANK
    records_bank = load_official_records_for_index("NIFTY BANK")
    assert len(records_bank) == 14
    bank_symbols = {r.symbol for r in records_bank}
    assert "HDFCBANK" in bank_symbols
    assert "ICICIBANK" in bank_symbols
    assert "SBIN" in bank_symbols

    # Test NIFTY PHARMA
    records_pharma = load_official_records_for_index("NIFTY PHARMA")
    assert len(records_pharma) == 20
    pharma_symbols = {r.symbol for r in records_pharma}
    assert "SUNPHARMA" in pharma_symbols
    assert "CIPLA" in pharma_symbols
