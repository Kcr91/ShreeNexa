"""Integration tests for index constituent intervals, reconstitution, and overrides."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from app.contracts import heartbeat as hb
from app.marketdata.universe import (
    ConstituentInput,
    apply_manual_override,
    get_constituents_at_date,
    ingest_fallback_constituents,
    ingest_index_snapshot,
    is_member_at_date,
    list_available_indices,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine


@pytest.fixture
def db_engine() -> Generator[Engine]:
    """Provide database engine connected to local PostgreSQL."""
    try:
        engine = hb.make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()
    except Exception as exc:
        pytest.skip(f"Database not available for integration tests: {exc}")


@pytest.fixture(autouse=True)
def clean_constituents_table(db_engine: Engine) -> None:
    """Ensure clean table state before each test."""
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM index_constituent"))


def test_ingest_fallback_and_point_in_time_query(db_engine: Engine) -> None:
    """Verify committed fallback ingestion and date-aware membership queries."""
    count = ingest_fallback_constituents(db_engine)
    assert count >= 30

    indices = list_available_indices(db_engine)
    assert "NIFTY 50" in indices
    assert "NIFTY BANK" in indices
    assert "NIFTY IT" in indices

    # Point-in-time check on active date (2026-08-01)
    as_of = date(2026, 8, 1)
    constituents = get_constituents_at_date(db_engine, "NIFTY 50", as_of=as_of)
    assert len(constituents) >= 15

    # Check top constituent
    hdfc = constituents[0]
    assert hdfc.symbol == "HDFCBANK"
    assert hdfc.weight == Decimal("11.4500")
    assert hdfc.source == "fallback"
    assert hdfc.valid_from == date(2026, 8, 1)
    assert hdfc.valid_to is None

    # Membership query
    res = is_member_at_date(db_engine, "NIFTY 50", "RELIANCE", as_of=as_of)
    assert res.is_member is True
    assert res.symbol == "RELIANCE"
    assert res.weight == Decimal("9.8500")

    # Non-member query
    non_member = is_member_at_date(db_engine, "NIFTY 50", "UNKNOWN_STOCK", as_of=as_of)
    assert non_member.is_member is False

    # Historical query before index snapshot valid_from (2025-01-01)
    before_start = is_member_at_date(db_engine, "NIFTY 50", "RELIANCE", as_of=date(2025, 1, 1))
    assert before_start.is_member is False


def test_index_reconstitution_effective_intervals(db_engine: Engine) -> None:
    """Test updating index constituents across rebalancing dates with automatic interval closing."""
    # 1. Initial snapshot effective 2026-01-01
    initial_members = [
        ConstituentInput(symbol="STOCK_A", weight=50.0, sector="Tech"),
        ConstituentInput(symbol="STOCK_B", weight=50.0, sector="Finance"),
    ]
    ingest_index_snapshot(
        db_engine,
        index_name="TEST_INDEX",
        constituents=initial_members,
        source_date=date(2026, 1, 1),
        valid_from=date(2026, 1, 1),
    )

    # On 2026-03-01, both A and B are active
    assert (
        is_member_at_date(db_engine, "TEST_INDEX", "STOCK_A", as_of=date(2026, 3, 1)).is_member
        is True
    )
    assert (
        is_member_at_date(db_engine, "TEST_INDEX", "STOCK_B", as_of=date(2026, 3, 1)).is_member
        is True
    )

    # 2. Rebalancing on 2026-06-01: STOCK_B dropped, STOCK_C added
    rebalanced_members = [
        ConstituentInput(symbol="STOCK_A", weight=60.0, sector="Tech"),
        ConstituentInput(symbol="STOCK_C", weight=40.0, sector="Health"),
    ]
    ingest_index_snapshot(
        db_engine,
        index_name="TEST_INDEX",
        constituents=rebalanced_members,
        source_date=date(2026, 6, 1),
        valid_from=date(2026, 6, 1),
    )

    # Prior to rebalancing (2026-05-31): STOCK_B is active, STOCK_C is not
    assert (
        is_member_at_date(db_engine, "TEST_INDEX", "STOCK_B", as_of=date(2026, 5, 31)).is_member
        is True
    )
    assert (
        is_member_at_date(db_engine, "TEST_INDEX", "STOCK_C", as_of=date(2026, 5, 31)).is_member
        is False
    )

    # After rebalancing (2026-06-01): STOCK_B is dropped, STOCK_C is active
    b_after = is_member_at_date(db_engine, "TEST_INDEX", "STOCK_B", as_of=date(2026, 6, 1))
    assert b_after.is_member is False

    c_after = is_member_at_date(db_engine, "TEST_INDEX", "STOCK_C", as_of=date(2026, 6, 1))
    assert c_after.is_member is True
    assert c_after.weight == Decimal("40.0000")

    # Verify constituent list on 2026-06-01 contains STOCK_A and STOCK_C, but not STOCK_B
    constituents_june = get_constituents_at_date(db_engine, "TEST_INDEX", as_of=date(2026, 6, 1))
    symbols_june = {c.symbol for c in constituents_june}
    assert "STOCK_B" not in symbols_june
    assert "STOCK_A" in symbols_june
    assert "STOCK_C" in symbols_june


def test_manual_override_addition_and_removal(db_engine: Engine) -> None:
    """Test manual overrides recording explicit source='manual' provenance."""
    # Seed fallback
    ingest_fallback_constituents(db_engine)

    # 1. Manual addition on 2026-08-15
    apply_manual_override(
        db_engine,
        index_name="NIFTY 50",
        symbol="SPECIAL_STOCK",
        is_member=True,
        effective_date=date(2026, 8, 15),
        weight=1.5,
        sector="Specialty",
    )

    override_res = is_member_at_date(
        db_engine, "NIFTY 50", "SPECIAL_STOCK", as_of=date(2026, 8, 15)
    )
    assert override_res.is_member is True
    assert override_res.source == "manual"
    assert override_res.weight == Decimal("1.5000")

    # Before effective date: was not member
    assert (
        is_member_at_date(db_engine, "NIFTY 50", "SPECIAL_STOCK", as_of=date(2026, 8, 14)).is_member
        is False
    )

    # 2. Manual removal of RELIANCE on 2026-08-20
    apply_manual_override(
        db_engine,
        index_name="NIFTY 50",
        symbol="RELIANCE",
        is_member=False,
        effective_date=date(2026, 8, 20),
    )

    assert (
        is_member_at_date(db_engine, "NIFTY 50", "RELIANCE", as_of=date(2026, 8, 19)).is_member
        is True
    )
    assert (
        is_member_at_date(db_engine, "NIFTY 50", "RELIANCE", as_of=date(2026, 8, 20)).is_member
        is False
    )
