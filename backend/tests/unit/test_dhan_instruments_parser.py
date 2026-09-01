"""Unit tests for Dhan detailed scrip master parser, segment resolution, and schema drift."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from app.dhan.instruments import (
    parse_scrip_master_csv,
    resolve_exchange_segment,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_CSV_PATH = FIXTURES_DIR / "dhan_scrip_master_sample.csv"


def test_resolve_exchange_segment_standard_and_numeric() -> None:
    """Test dynamic segment resolution across all known exchanges and numeric IDs."""
    assert resolve_exchange_segment("NSE", "E") == "NSE_EQ"
    assert resolve_exchange_segment("NSE", "D") == "NSE_FNO"
    assert resolve_exchange_segment("NSE", "I") == "IDX_I"
    assert resolve_exchange_segment("NSE", "C") == "NSE_CURRENCY"
    assert resolve_exchange_segment("BSE", "E") == "BSE_EQ"
    assert resolve_exchange_segment("MCX", "M") == "MCX_COMM"
    assert resolve_exchange_segment("BSE", "C") == "BSE_CURRENCY"
    assert resolve_exchange_segment("BSE", "D") == "BSE_FNO"

    # Numeric codes
    assert resolve_exchange_segment("0", "") == "IDX_I"
    assert resolve_exchange_segment("1", "") == "NSE_EQ"
    assert resolve_exchange_segment("2", "") == "NSE_FNO"
    assert resolve_exchange_segment("3", "") == "NSE_CURRENCY"
    assert resolve_exchange_segment("4", "") == "BSE_EQ"
    assert resolve_exchange_segment("5", "") == "MCX_COMM"
    assert resolve_exchange_segment("7", "") == "BSE_CURRENCY"
    assert resolve_exchange_segment("8", "") == "BSE_FNO"


def test_resolve_exchange_segment_unannounced_fallback() -> None:
    """Do not crash on unannounced exchange segments; preserve dynamic format."""
    assert resolve_exchange_segment("NCDEX", "AGRI") == "NCDEX_AGRI"
    assert resolve_exchange_segment("GIFT", "FNO") == "GIFT_FNO"
    assert resolve_exchange_segment("NEWEXCH", "") == "NEWEXCH"


def test_parse_sample_csv_fixture() -> None:
    """Parse synthetic Dhan detailed master CSV and verify all record fields."""
    assert SAMPLE_CSV_PATH.is_file()
    records, errors = parse_scrip_master_csv(SAMPLE_CSV_PATH)

    assert len(errors) == 0
    assert len(records) == 19

    # Check Reliance Equity
    reliance = next(
        r for r in records if r["security_id"] == "2885" and r["exchange_segment"] == "NSE_EQ"
    )
    assert reliance["symbol"] == "RELIANCE"
    assert reliance["trading_symbol"] == "RELIANCE-EQ"
    assert reliance["instrument_type"] == "EQUITY"
    assert reliance["lot_size"] == 1
    assert reliance["tick_size"] == Decimal("0.05")
    assert reliance["isin"] == "INE002A01018"
    assert reliance["is_active"] is True
    assert reliance["expiry_date"] is None
    assert reliance["strike_price"] is None

    # Check Nifty 50 Index
    nifty_idx = next(
        r for r in records if r["security_id"] == "13" and r["exchange_segment"] == "IDX_I"
    )
    assert nifty_idx["symbol"] == "NIFTY"
    assert nifty_idx["instrument_type"] == "INDEX"
    assert nifty_idx["trading_symbol"] == "NIFTY 50"

    # Check Nifty Option Call
    nifty_ce = next(r for r in records if r["security_id"] == "49231")
    assert nifty_ce["exchange_segment"] == "NSE_FNO"
    assert nifty_ce["instrument_type"] == "OPTIDX"
    assert nifty_ce["option_type"] == "CE"
    assert nifty_ce["strike_price"] == Decimal("24500.0000")
    assert nifty_ce["expiry_date"] == date(2026, 8, 28)
    assert nifty_ce["lot_size"] == 25
    assert nifty_ce["underlying_id"] == "13"

    # Check Delisted Inactive Equity
    delisted = next(r for r in records if r["security_id"] == "99999")
    assert delisted["is_active"] is False


def test_parse_csv_with_header_drift_and_simplified_columns() -> None:
    """Tolerate alternate column names and casing variations in CSV headers."""
    csv_data = (
        "security_id,exchange_segment,instrument_type,symbol,trading_symbol,"
        "lot_size,tick_size,expiry_date,strike_price,option_type,underlying_id,is_active\n"
        "101,NSE_EQ,EQUITY,INFY,INFY-EQ,1,0.05,NA,NA,NA,NA,Y\n"
        "102,NSE_FNO,OPTSTK,INFY 28AUG26 1900 CE,INFY-28Aug2026-1900-CE,"
        "400,0.05,2026-08-28,1900.00,CE,101,1\n"
    )
    records, errors = parse_scrip_master_csv(csv_data)
    assert len(errors) == 0
    assert len(records) == 2

    assert records[0]["security_id"] == "101"
    assert records[0]["exchange_segment"] == "NSE_EQ"
    assert records[0]["symbol"] == "INFY"

    assert records[1]["security_id"] == "102"
    assert records[1]["exchange_segment"] == "NSE_FNO"
    assert records[1]["strike_price"] == Decimal("1900.00")
    assert records[1]["option_type"] == "CE"
    assert records[1]["underlying_id"] == "101"
    assert records[1]["is_active"] is True


def test_parse_csv_error_recovery_on_corrupted_rows() -> None:
    """Rows missing critical security_id or malformed are logged as errors without crashing."""
    csv_data = """SEM_SMST_SECURITY_ID,SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_CUSTOM_SYMBOL
2885,NSE,E,RELIANCE
,NSE,E,MISSING_SEC_ID
NA,NSE,E,EMPTY_SEC_ID
1333,NSE,E,HDFCBANK
"""
    records, errors = parse_scrip_master_csv(csv_data)
    assert len(records) == 2
    assert len(errors) == 2
    assert {r["security_id"] for r in records} == {"2885", "1333"}


def test_parse_csv_date_formats() -> None:
    """Test date parsing across various formats."""
    csv_data = """security_id,exchange_segment,instrument_type,symbol,trading_symbol,expiry_date
1,NSE_FNO,OPTIDX,NIFTY,NIFTY-CE,28-Aug-2026
2,NSE_FNO,OPTIDX,NIFTY,NIFTY-PE,2026-08-28 15:30:00
3,NSE_FNO,OPTIDX,NIFTY,NIFTY-FUT,28/08/2026
"""
    records, _ = parse_scrip_master_csv(csv_data)
    assert len(records) == 3
    assert records[0]["expiry_date"] == date(2026, 8, 28)
    assert records[1]["expiry_date"] == date(2026, 8, 28)
