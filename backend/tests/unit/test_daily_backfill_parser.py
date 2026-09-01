"""Unit tests for Dhan daily chart response parser, raw provenance, and NIFTY reconciliation."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC
from pathlib import Path

from app.worker.daily_backfill import (
    parse_dhan_daily_candles,
    save_raw_ingest,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_dhan_daily_candles_epoch_and_iso() -> None:
    """Verify parsing Dhan daily candles with epoch timestamps and values."""
    payload = {
        "open": [24800.5, 24930.0],
        "high": [24950.25, 25010.8],
        "low": [24780.0, 24890.1],
        "close": [24920.75, 24995.5],
        "volume": [1000, 2000],
        "start_Time": [1785642300, 1785728700],
        "open_interest": [0, 0],
    }
    bars = parse_dhan_daily_candles(
        payload=payload,
        symbol="NIFTY",
        security_id="13",
        exchange_segment="IDX_I",
    )
    assert len(bars) == 2
    assert bars[0].symbol == "NIFTY"
    assert bars[0].open == 24800.5
    assert bars[0].close == 24920.75
    assert bars[0].timestamp.tzinfo == UTC


def test_save_raw_ingest_redacts_secrets() -> None:
    """Verify raw JSON persistence and secret redaction."""
    with tempfile.TemporaryDirectory(prefix="shreenexa_raw_") as tmp_dir:
        data_root = Path(tmp_dir) / "data"
        raw_payload = b'{"open": [100.0], "close": [105.0], "start_Time": [1785642300]}'
        params = {
            "symbol": "RELIANCE",
            "security_id": "2885",
            "access_token": "secret-jwt-token-must-not-leak",
            "client_id": "1000000001",
        }

        ingest_id, dest_dir = save_raw_ingest(data_root, raw_payload, params)

        assert (dest_dir / "payload.json").is_file()
        assert (dest_dir / "metadata.json").is_file()

        meta = json.loads((dest_dir / "metadata.json").read_text(encoding="utf-8"))
        assert meta["ingest_id"] == ingest_id
        assert "access_token" not in meta["params"]
        assert "client_id" not in meta["params"]
        assert meta["params"]["symbol"] == "RELIANCE"


def test_nifty_daily_sample_reconciliation() -> None:
    """Verify NIFTY daily fixture parses and reconciles against reference sample."""
    fixture_path = FIXTURES_DIR / "nifty_daily_sample.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    candles = data["candles"]
    payload = {
        "open": [c["open"] for c in candles],
        "high": [c["high"] for c in candles],
        "low": [c["low"] for c in candles],
        "close": [c["close"] for c in candles],
        "volume": [c["volume"] for c in candles],
        "start_Time": [c["timestamp"] for c in candles],
        "open_interest": [c["open_interest"] for c in candles],
    }

    bars = parse_dhan_daily_candles(
        payload=payload,
        symbol=data["symbol"],
        security_id=data["security_id"],
        exchange_segment=data["exchange_segment"],
    )

    assert len(bars) == 3
    assert bars[0].close == 24920.75
    assert bars[1].close == 24995.50
    assert bars[2].close == 25050.20
