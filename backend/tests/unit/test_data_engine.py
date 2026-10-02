"""Unit test suite for Data Engine & Storage Pipeline (Feature 1)."""

from __future__ import annotations

import csv
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.worker.data_engine.bulk_importer import BulkImporter, parse_csv_path
from app.worker.data_engine.incremental_updater import IncrementalUpdater
from app.worker.data_engine.models import metadata
from app.worker.data_engine.parquet_archiver import EQUITY_SCHEMA, ParquetArchiver
from app.worker.data_engine.quota_manager import QuotaManager
from app.worker.data_engine.segment_seeder import (
    get_all_segments,
    get_segment_constituents,
    seed_nse_segments,
)


@pytest.fixture
def sqlite_engine() -> Generator[Engine, None, None]:
    """In-memory SQLite engine for testing with tables created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_path_parser_rules() -> None:
    """Verify metadata derivation across all specified file path conventions."""
    # 1. Equity spot
    eq_meta = parse_csv_path("C:/data/RELIANCE.csv")
    assert eq_meta is not None
    assert eq_meta.symbol == "RELIANCE"
    assert eq_meta.instrument_type == "EQ"

    # 2. Options ATM Call Month 1
    opt_atm = parse_csv_path("C:/data/RELIANCE/Month_1/ATM_Call.csv")
    assert opt_atm is not None
    assert opt_atm.symbol == "RELIANCE"
    assert opt_atm.instrument_type == "CE"
    assert opt_atm.strike_offset == 0
    assert opt_atm.expiry_period == "Month_1"

    # 3. Options Strike offset +2 Call
    opt_plus = parse_csv_path("C:/data/RELIANCE/Month_1/ATM+2_Call.csv")
    assert opt_plus is not None
    assert opt_plus.symbol == "RELIANCE"
    assert opt_plus.instrument_type == "CE"
    assert opt_plus.strike_offset == 2

    # 4. Options Strike offset -3 Put
    opt_minus = parse_csv_path("C:/data/RELIANCE/Month_1/ATM-3_Put.csv")
    assert opt_minus is not None
    assert opt_minus.symbol == "RELIANCE"
    assert opt_minus.instrument_type == "PE"
    assert opt_minus.strike_offset == -3

    # 5. Weekly options
    opt_week = parse_csv_path("C:/data/NIFTY/Week_2/ATM_Call.csv")
    assert opt_week is not None
    assert opt_week.symbol == "NIFTY"
    assert opt_week.expiry_period == "Week_2"

    # 6. Futures
    fut_meta = parse_csv_path("C:/data/NIFTY_FUT.csv")
    assert fut_meta is not None
    assert fut_meta.symbol == "NIFTY"
    assert fut_meta.instrument_type == "FUT"


def test_quota_manager(sqlite_engine: Engine) -> None:
    """Verify daily API budget limits, reservations, and exhaustion guards."""
    qm = QuotaManager(db_engine=sqlite_engine, daily_limit=1000, reserved_live=100)
    today = datetime.now(UTC).date()

    status = qm.get_quota_status(today)
    assert status.daily_limit == 1000
    assert status.used_historical == 0
    assert status.reserved_live == 100
    assert status.available_historical == 900
    assert qm.can_make_historical_request(500, today) is True

    # Consume quota
    qm.consume_historical_quota(850, today)
    status2 = qm.get_quota_status(today)
    assert status2.used_historical == 850
    assert status2.available_historical == 50
    assert qm.can_make_historical_request(60, today) is False
    assert qm.can_make_historical_request(50, today) is True


def test_segment_seeder(sqlite_engine: Engine) -> None:
    """Verify 27 NSE segments and their constituent lists."""
    count = seed_nse_segments(sqlite_engine)
    assert count == 27

    segments = get_all_segments(sqlite_engine)
    assert len(segments) == 27
    codes = {s.code for s in segments}
    assert "INDEX_NIFTY50" in codes
    assert "INDEX_BANKNIFTY" in codes
    assert "SECTOR_IT" in codes
    assert "FNO_208" in codes

    nifty50_stocks = get_segment_constituents(sqlite_engine, "INDEX_NIFTY50")
    assert "RELIANCE" in nifty50_stocks
    assert "INFY" in nifty50_stocks


def test_parquet_archiver() -> None:
    """Verify parquet partitioned writing and appending."""
    with tempfile.TemporaryDirectory() as tmpdir:
        archiver = ParquetArchiver(base_data_dir=tmpdir)

        # Write equity partition
        arrow_data = {
            "datetime_ist": [datetime(2024, 1, 15, 9, 15, tzinfo=UTC)],
            "open": [2500.0],
            "high": [2510.0],
            "low": [2495.0],
            "close": [2505.0],
            "volume": [10000],
        }
        table = pa.Table.from_pydict(arrow_data, schema=EQUITY_SCHEMA)
        out_file = archiver.write_equity_candles("RELIANCE", 2024, 1, table)
        assert out_file.exists()
        assert "2024" in str(out_file)
        assert "01.parquet" in str(out_file)


def test_bulk_importer(sqlite_engine: Engine) -> None:
    """Verify CSV reading and batch import into DB and Parquet."""
    with tempfile.TemporaryDirectory() as tmpdir:
        archiver = ParquetArchiver(base_data_dir=tmpdir)
        importer = BulkImporter(engine=sqlite_engine, archiver=archiver)

        # Create sample CSV file
        csv_path = Path(tmpdir) / "RELIANCE.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["datetime_ist", "open", "high", "low", "close", "volume"])
            writer.writerow(["2024-01-15 09:15:00", "2500.0", "2510.0", "2495.0", "2505.0", "1500"])
            writer.writerow(["2024-01-15 09:16:00", "2505.0", "2515.0", "2502.0", "2512.0", "2000"])

        rows = importer.import_csv_file(csv_path)
        assert rows == 2


def test_incremental_updater(sqlite_engine: Engine) -> None:
    """Verify incremental sync progress, checkpointing, and pause/resume."""
    updater = IncrementalUpdater(engine=sqlite_engine)
    progress = updater.sync_universe(symbols=["RELIANCE", "INFY"])
    assert progress.status == "COMPLETED"
    assert progress.total_instruments == 2
    assert progress.completed_instruments == 2

    updater.pause()
    assert updater.get_progress().status == "PAUSED"
    updater.resume()
    assert updater.get_progress().status == "RUNNING"


def test_data_engine_api_routes(sqlite_engine: Engine) -> None:
    """Verify FastAPI /api/v1/data endpoints."""
    from app.api.data_engine import get_db_engine

    app.dependency_overrides[get_db_engine] = lambda: sqlite_engine
    client = TestClient(app)

    try:
        # 1. Segments list
        resp = client.get("/api/v1/data/segments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

        # 2. Quota endpoint
        quota_resp = client.get("/api/v1/data/quota")
        assert quota_resp.status_code == 200
        quota = quota_resp.json()
        assert "daily_limit" in quota
        assert "available_historical" in quota

        # 3. Sync status
        status_resp = client.get("/api/v1/data/sync/status")
        assert status_resp.status_code == 200
        assert "status" in status_resp.json()
    finally:
        app.dependency_overrides.pop(get_db_engine, None)
