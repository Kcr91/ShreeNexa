"""Integration tests for Dhan instrument master PostgreSQL ingestion and search."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from app.contracts import heartbeat as hb
from app.dhan.instruments import (
    InstrumentSearchQuery,
    get_distinct_segments,
    get_expiries_for_underlying,
    get_instrument,
    get_option_chain_instruments,
    ingest_instruments,
    search_instruments,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_CSV_PATH = FIXTURES_DIR / "dhan_scrip_master_sample.csv"


@pytest.fixture
def db_engine() -> Generator[Engine]:
    """Provide a database engine connected to test Postgres."""
    try:
        engine = hb.make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()
    except Exception as exc:
        pytest.skip(f"Postgres database not available: {exc}")


@pytest.fixture(autouse=True)
def clean_instruments_table(db_engine: Engine) -> None:
    """Ensure clean table state before each test."""
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM instrument"))


def test_ingest_and_query_instruments_in_postgres(db_engine: Engine) -> None:
    """Ingest sample CSV fixture and verify database contents and queries."""
    summary = ingest_instruments(db_engine, SAMPLE_CSV_PATH)

    assert summary.total_rows == 19
    assert summary.inserted_or_updated == 19
    assert "NSE_EQ" in summary.distinct_segments
    assert "NSE_FNO" in summary.distinct_segments
    assert "IDX_I" in summary.distinct_segments
    assert "BSE_EQ" in summary.distinct_segments
    assert "MCX_COMM" in summary.distinct_segments

    # Query distinct segments
    segments = get_distinct_segments(db_engine)
    assert len(segments) >= 5
    assert "NSE_EQ" in segments
    assert "NSE_FNO" in segments

    # Exact lookup
    reliance_eq = get_instrument(db_engine, "NSE_EQ", "2885")
    assert reliance_eq is not None
    assert reliance_eq.symbol == "RELIANCE"
    assert reliance_eq.trading_symbol == "RELIANCE-EQ"
    assert reliance_eq.is_active is True

    # Search by symbol substring
    results = search_instruments(db_engine, InstrumentSearchQuery(query="RELIANCE"))
    assert len(results) >= 4  # NSE_EQ, BSE_EQ, OPTSTK CE, OPTSTK PE
    symbols = {r.symbol for r in results}
    assert "RELIANCE" in symbols

    # Search filtered by segment
    nse_eq_only = search_instruments(
        db_engine, InstrumentSearchQuery(query="RELIANCE", exchange_segment="NSE_EQ")
    )
    assert len(nse_eq_only) == 1
    assert nse_eq_only[0].security_id == "2885"

    # Search filtered by instrument type
    options_only = search_instruments(
        db_engine, InstrumentSearchQuery(query="NIFTY", instrument_type="OPTIDX")
    )
    assert len(options_only) == 4  # 24500 CE, 24500 PE, 25000 CE, 25000 PE
    for opt in options_only:
        assert opt.instrument_type == "OPTIDX"
        assert opt.expiry_date == date(2026, 8, 28)

    # Inactive filter
    active_search = search_instruments(db_engine, InstrumentSearchQuery(query="DELISTED"))
    assert len(active_search) == 0  # Inactive by default

    inactive_included = search_instruments(
        db_engine, InstrumentSearchQuery(query="DELISTED", is_active_only=False)
    )
    assert len(inactive_included) == 1
    assert inactive_included[0].is_active is False


def test_option_chain_retrieval_and_sorting(db_engine: Engine) -> None:
    """Verify option chain retrieves all strikes sorted by strike and option type."""
    ingest_instruments(db_engine, SAMPLE_CSV_PATH)

    chain = get_option_chain_instruments(
        db_engine, underlying_id="13", expiry_date=date(2026, 8, 28), exchange_segment="NSE_FNO"
    )

    assert len(chain) == 4
    # Strikes: 24500 CE, 24500 PE, 25000 CE, 25000 PE
    strikes_and_types = [(c.strike_price, c.option_type) for c in chain]
    assert strikes_and_types == [
        (Decimal("24500.0000"), "CE"),
        (Decimal("24500.0000"), "PE"),
        (Decimal("25000.0000"), "CE"),
        (Decimal("25000.0000"), "PE"),
    ]

    # Expiries query
    expiries = get_expiries_for_underlying(db_engine, underlying_id="13")
    assert expiries == [date(2026, 8, 28)]


def test_idempotent_reingest(db_engine: Engine) -> None:
    """Repeated ingestion of the same master updates timestamps and does not duplicate rows."""
    summary1 = ingest_instruments(db_engine, SAMPLE_CSV_PATH)
    assert summary1.inserted_or_updated == 19

    # Re-ingest
    summary2 = ingest_instruments(db_engine, SAMPLE_CSV_PATH)
    assert summary2.inserted_or_updated == 19

    # Total rows in DB should still be 19
    all_rows = search_instruments(
        db_engine, InstrumentSearchQuery(limit=100, is_active_only=False)
    )
    assert len(all_rows) == 19
