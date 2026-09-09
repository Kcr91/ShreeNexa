"""Unit tests for the historical bar query, coverage, and CSV export API.

These previously asserted the synthetic-fallback behaviour: an empty warehouse returned
fabricated candles from a hardcoded price table, and the assertions demanded
`total_bars > 0`. That is now a defect rather than a feature, so the expectations are
inverted - an empty warehouse must produce a 404, never invented data.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from datetime import UTC, datetime

import pyarrow as pa
import pytest
from app.api import historical
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture()
def seeded_warehouse(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Stand in for a warehouse holding three 1-minute RELIANCE bars."""
    base = int(datetime(2026, 9, 1, 3, 45, tzinfo=UTC).timestamp() * 1000)
    table = pa.table(
        {
            "timestamp": [base, base + 60_000, base + 120_000],
            "symbol": ["RELIANCE"] * 3,
            "exchange_segment": ["NSE_EQ"] * 3,
            "open": [2980.0, 2982.0, 2984.0],
            "high": [2990.0, 2992.0, 2994.0],
            "low": [2975.0, 2977.0, 2979.0],
            "close": [2985.0, 2987.0, 2989.0],
            "volume": [1000, 1100, 1200],
            "open_interest": [0, 0, 0],
        }
    )
    monkeypatch.setattr(historical._reader, "query_bars", lambda **_: table)
    yield


@pytest.fixture()
def empty_warehouse(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Stand in for a warehouse that has never been published to."""

    def raise_missing(**_: object) -> pa.Table:
        raise FileNotFoundError("no current pointer")

    monkeypatch.setattr(historical._reader, "query_bars", raise_missing)
    monkeypatch.setattr(historical, "_coverage_rows", lambda **_: [])
    yield


def test_historical_info_endpoint() -> None:
    res = client.get("/api/v1/historical/info")
    assert res.status_code == 200
    data = res.json()
    assert "1d" in data["supported_timeframes"]
    assert "5m" in data["supported_timeframes"]
    assert "NSE_EQ" in data["supported_segments"]
    assert "options" in data["supported_datasets"]
    assert data["default_segment"] == "NSE_EQ"


class TestNoSyntheticData:
    """The regression that motivated this rewrite."""

    def test_synthetic_generator_is_gone(self) -> None:
        """A fallback that fabricates candles must not exist at all."""
        assert not hasattr(historical, "_generate_synthetic_bars")
        assert not hasattr(historical, "REFERENCE_PRICES")

    def test_empty_warehouse_returns_404_not_invented_bars(self, empty_warehouse: None) -> None:
        res = client.get("/api/v1/historical/bars", params={"symbol": "RELIANCE"})
        assert res.status_code == 404
        assert "backfill" in res.json()["detail"].lower()

    def test_empty_warehouse_export_returns_404(self, empty_warehouse: None) -> None:
        """A CSV of fabricated candles is the most dangerous form of this bug."""
        res = client.get("/api/v1/historical/export", params={"symbol": "RELIANCE"})
        assert res.status_code == 404

    def test_unknown_symbol_returns_404(self, empty_warehouse: None) -> None:
        res = client.get("/api/v1/historical/bars", params={"symbol": "NOTATICKER"})
        assert res.status_code == 404

    def test_served_bars_are_always_labelled_warehouse(self, seeded_warehouse: None) -> None:
        res = client.get(
            "/api/v1/historical/bars", params={"symbol": "RELIANCE", "timeframe": "1m"}
        )
        assert res.status_code == 200
        assert res.json()["data_source"] == "warehouse"


class TestBarsQuery:
    def test_returns_bars_and_summary(self, seeded_warehouse: None) -> None:
        res = client.get(
            "/api/v1/historical/bars", params={"symbol": "RELIANCE", "timeframe": "1m"}
        )
        assert res.status_code == 200
        data = res.json()

        assert data["symbol"] == "RELIANCE"
        assert data["summary"]["total_bars"] == 3
        assert data["summary"]["high"] == 2994.0
        assert data["summary"]["low"] == 2975.0
        assert data["summary"]["total_volume"] == 3300

    def test_bar_shape_includes_open_interest(self, seeded_warehouse: None) -> None:
        res = client.get(
            "/api/v1/historical/bars", params={"symbol": "RELIANCE", "timeframe": "1m"}
        )
        bar = res.json()["bars"][0]
        for field in ("timestamp", "symbol", "open", "high", "low", "close", "volume"):
            assert field in bar
        assert "open_interest" in bar

    def test_limit_is_honoured(self, seeded_warehouse: None) -> None:
        res = client.get(
            "/api/v1/historical/bars",
            params={"symbol": "RELIANCE", "timeframe": "1m", "limit": 2},
        )
        assert len(res.json()["bars"]) == 2

    def test_missing_symbol_rejected(self) -> None:
        assert client.get("/api/v1/historical/bars").status_code == 422

    def test_blank_symbol_rejected(self) -> None:
        res = client.get("/api/v1/historical/bars", params={"symbol": "   "})
        assert res.status_code == 400

    def test_invalid_timeframe_rejected(self) -> None:
        res = client.get(
            "/api/v1/historical/bars", params={"symbol": "RELIANCE", "timeframe": "7x"}
        )
        assert res.status_code == 400

    def test_unparseable_date_rejected(self) -> None:
        res = client.get(
            "/api/v1/historical/bars",
            params={"symbol": "RELIANCE", "start_time": "not-a-date"},
        )
        assert res.status_code == 400


class TestCoverage:
    def test_coverage_reports_recorded_series(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            historical,
            "_coverage_rows",
            lambda **_: [
                {
                    "dataset": "intraday",
                    "symbol": "RELIANCE",
                    "exchange_segment": "NSE_EQ",
                    "interval": "1",
                    "security_id": "2885",
                    "underlying_symbol": None,
                    "min_ts": datetime(2021, 1, 1, tzinfo=UTC),
                    "max_ts": datetime(2026, 9, 1, tzinfo=UTC),
                    "rows": 469000,
                    "last_verified_at": datetime(2026, 9, 8, tzinfo=UTC),
                }
            ],
        )
        res = client.get("/api/v1/historical/coverage", params={"symbol": "RELIANCE"})
        assert res.status_code == 200
        data = res.json()

        assert data["total_series"] == 1
        item = data["items"][0]
        assert item["first_date"] == "2021-01-01"
        assert item["last_date"] == "2026-09-01"
        assert item["rows"] == 469000

    def test_coverage_is_empty_before_any_backfill(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(historical, "_coverage_rows", lambda **_: [])
        res = client.get("/api/v1/historical/coverage")
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_max_range_without_coverage_is_404(self, empty_warehouse: None) -> None:
        """'Max available' cannot silently become 'the last 30 days'."""
        res = client.get(
            "/api/v1/historical/bars",
            params={"symbol": "RELIANCE", "range_mode": "max"},
        )
        assert res.status_code == 404
        assert "coverage" in res.json()["detail"].lower()


class TestCsvExport:
    def test_export_streams_valid_csv(self, seeded_warehouse: None) -> None:
        res = client.get(
            "/api/v1/historical/export", params={"symbol": "RELIANCE", "timeframe": "1m"}
        )
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert "attachment" in res.headers["content-disposition"]

        rows = list(csv.reader(io.StringIO(res.text)))
        assert rows[0] == historical.CSV_HEADER
        assert len(rows) == 4  # header plus three bars

    def test_export_declares_provenance_on_the_download(self, seeded_warehouse: None) -> None:
        """The old CSV carried no marker, so simulated data looked identical to real."""
        res = client.get(
            "/api/v1/historical/export", params={"symbol": "RELIANCE", "timeframe": "1m"}
        )
        assert res.headers["x-shreenexa-data-source"] == "warehouse"

    def test_export_filename_carries_symbol_and_range(self, seeded_warehouse: None) -> None:
        res = client.get(
            "/api/v1/historical/export",
            params={
                "symbol": "RELIANCE",
                "timeframe": "1m",
                "start_time": "2026-09-01",
                "end_time": "2026-09-02",
            },
        )
        disposition = res.headers["content-disposition"]
        assert "RELIANCE_1m_2026-09-01_2026-09-02.csv" in disposition

    def test_export_rejects_invalid_timeframe(self) -> None:
        res = client.get(
            "/api/v1/historical/export", params={"symbol": "RELIANCE", "timeframe": "9q"}
        )
        assert res.status_code == 400

    def test_csv_stream_chunks_large_exports(self) -> None:
        """A five-year 1-minute export is ~470k rows and must not be buffered whole."""
        bars = [
            historical.HistoricalBarResponseItem(
                timestamp="2026-09-01T03:45:00+00:00",
                symbol="X",
                exchange_segment="NSE_EQ",
                open=1.0,
                high=2.0,
                low=0.5,
                close=1.5,
                volume=10,
            )
            for _ in range(historical.CSV_CHUNK_ROWS * 2 + 7)
        ]
        chunks = list(historical._csv_stream(bars))

        assert len(chunks) >= 3, "output must arrive in multiple chunks, not one blob"
        total_rows = sum(chunk.decode().count("\n") for chunk in chunks)
        assert total_rows == len(bars) + 1


class TestCoverageOutage:
    """An unreachable catalogue must not masquerade as an empty one."""

    def test_coverage_endpoint_reports_503_on_db_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def unavailable(**_: object) -> list[dict[str, object]]:
            raise historical.CoverageUnavailableError("connection refused")

        monkeypatch.setattr(historical, "_coverage_rows", unavailable)
        res = client.get("/api/v1/historical/coverage")

        assert res.status_code == 503
        assert "unavailable" in res.json()["detail"].lower()

    def test_max_range_reports_503_rather_than_run_the_backfill(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Telling the user to run a backfill during an outage would be wrong."""

        def unavailable(**_: object) -> list[dict[str, object]]:
            raise historical.CoverageUnavailableError("connection refused")

        monkeypatch.setattr(historical, "_coverage_rows", unavailable)
        res = client.get(
            "/api/v1/historical/bars", params={"symbol": "RELIANCE", "range_mode": "max"}
        )

        assert res.status_code == 503
        assert "backfill" not in res.json()["detail"].lower()

    def test_bars_404_does_not_claim_to_know_coverage_during_an_outage(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def raise_missing(**_: object) -> pa.Table:
            raise FileNotFoundError("no current pointer")

        def unavailable(**_: object) -> list[dict[str, object]]:
            raise historical.CoverageUnavailableError("connection refused")

        monkeypatch.setattr(historical._reader, "query_bars", raise_missing)
        monkeypatch.setattr(historical, "_coverage_rows", unavailable)

        res = client.get("/api/v1/historical/bars", params={"symbol": "RELIANCE"})
        assert res.status_code == 404
        assert "could not be read" in res.json()["detail"]
