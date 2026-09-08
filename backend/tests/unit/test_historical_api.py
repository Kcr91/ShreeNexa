"""Unit tests for historical OHLCV bar query, preview, and CSV export API."""

from __future__ import annotations

import csv
import io

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_historical_info_endpoint() -> None:
    """GET /api/v1/historical/info returns warehouse status and supported timeframes."""
    res = client.get("/api/v1/historical/info")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "supported_timeframes" in data
    assert "1d" in data["supported_timeframes"]
    assert "5m" in data["supported_timeframes"]
    assert "supported_segments" in data
    assert "NSE_EQ" in data["supported_segments"]
    assert data["default_segment"] == "NSE_EQ"


def test_historical_bars_default() -> None:
    """GET /api/v1/historical/bars returns OHLCV bars with summary metrics."""
    res = client.get("/api/v1/historical/bars", params={"symbol": "RELIANCE"})
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "RELIANCE"
    assert data["exchange_segment"] == "NSE_EQ"
    assert data["timeframe"] == "1d"
    assert data["summary"]["total_bars"] > 0
    assert len(data["bars"]) > 0

    first_bar = data["bars"][0]
    assert "timestamp" in first_bar
    assert first_bar["symbol"] == "RELIANCE"
    assert first_bar["open"] > 0
    assert first_bar["high"] >= first_bar["low"]
    assert first_bar["volume"] >= 0


def test_historical_bars_intraday_timeframe() -> None:
    """GET /api/v1/historical/bars works with intraday timeframes (e.g. 15m)."""
    res = client.get(
        "/api/v1/historical/bars",
        params={
            "symbol": "TCS",
            "exchange_segment": "NSE_EQ",
            "timeframe": "15m",
            "start_time": "2026-01-01",
            "end_time": "2026-01-05",
            "limit": 100,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "TCS"
    assert data["timeframe"] == "15m"
    assert data["summary"]["total_bars"] > 0
    assert len(data["bars"]) <= 100


def test_historical_bars_missing_symbol_rejected() -> None:
    """GET /api/v1/historical/bars rejects blank symbol."""
    res = client.get("/api/v1/historical/bars", params={"symbol": "  "})
    assert res.status_code == 400
    assert "Symbol parameter is required" in res.json()["detail"]


def test_historical_bars_invalid_timeframe_rejected() -> None:
    """GET /api/v1/historical/bars rejects unsupported timeframe."""
    res = client.get(
        "/api/v1/historical/bars",
        params={"symbol": "INFY", "timeframe": "42xyz"},
    )
    assert res.status_code == 400
    assert "Unsupported timeframe" in res.json()["detail"]


def test_historical_export_csv_download() -> None:
    """GET /api/v1/historical/export returns streaming CSV with proper headers and data."""
    res = client.get(
        "/api/v1/historical/export",
        params={
            "symbol": "HDFCBANK",
            "exchange_segment": "NSE_EQ",
            "timeframe": "1d",
            "start_time": "2026-01-01",
            "end_time": "2026-01-15",
        },
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=" in res.headers["content-disposition"]
    assert "HDFCBANK" in res.headers["content-disposition"]
    assert ".csv" in res.headers["content-disposition"]

    csv_text = res.text
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    assert len(rows) > 1
    expected_header = [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "open_interest",
    ]
    assert rows[0] == expected_header

    first_row = rows[1]
    assert first_row[1] == "HDFCBANK"
    assert float(first_row[2]) > 0
    assert float(first_row[3]) >= float(first_row[4])


def test_historical_export_csv_invalid_timeframe() -> None:
    """GET /api/v1/historical/export returns 400 on invalid timeframe."""
    res = client.get(
        "/api/v1/historical/export",
        params={"symbol": "HDFCBANK", "timeframe": "invalid_tf"},
    )
    assert res.status_code == 400
