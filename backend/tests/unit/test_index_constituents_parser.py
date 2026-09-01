"""Unit tests for index constituent fallback configuration and model parsing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from app.marketdata.universe import (
    ConstituentInput,
    _normalize_date,
    load_fallback_config,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "index_constituents_fallback.yaml"


def test_load_fallback_config_from_yaml() -> None:
    """Verify loading committed fallback index snapshots from YAML."""
    assert CONFIG_PATH.is_file()
    indices = load_fallback_config(CONFIG_PATH)

    assert len(indices) >= 3
    index_names = [idx["index_name"] for idx in indices]
    assert "NIFTY 50" in index_names
    assert "NIFTY BANK" in index_names
    assert "NIFTY IT" in index_names

    nifty50 = next(idx for idx in indices if idx["index_name"] == "NIFTY 50")
    assert len(nifty50["constituents"]) >= 15
    symbols = [c["symbol"] for c in nifty50["constituents"]]
    assert "HDFCBANK" in symbols
    assert "RELIANCE" in symbols


def test_constituent_input_validation() -> None:
    """Verify ConstituentInput decimal and string normalization."""
    input_item = ConstituentInput(symbol="reliance", weight=9.85, sector="Energy")
    assert input_item.symbol == "reliance"
    assert Decimal(str(input_item.weight)) == Decimal("9.85")


def test_normalize_date_formats() -> None:
    """Verify date normalization across strings and dates."""
    assert _normalize_date("2026-08-01") == date(2026, 8, 1)
    assert _normalize_date("2026-08-01 15:30:00") == date(2026, 8, 1)
    assert _normalize_date(date(2026, 8, 1)) == date(2026, 8, 1)


def test_load_fallback_config_missing_file() -> None:
    """Verify graceful handling when config file does not exist."""
    res = load_fallback_config(Path("non_existent_path.yaml"))
    assert res == []
