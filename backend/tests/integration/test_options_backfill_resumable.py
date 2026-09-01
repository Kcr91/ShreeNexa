"""Integration tests for expired options 30-day backfill and warehouse publishing."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from datetime import date
from pathlib import Path

import duckdb
import pytest
from app.warehouse.reader import WarehouseReader
from app.worker.options_backfill import (
    OptionsBackfillManager,
    OptionsBackfillTask,
    generate_30_day_windows,
)


@pytest.fixture
def temp_data_root() -> Generator[Path]:
    """Provide clean temporary data directory."""
    with tempfile.TemporaryDirectory(prefix="shreenexa_opt_test_") as tmp_dir:
        root = Path(tmp_dir) / "data"
        yield root


def test_options_backfill_execution_and_warehouse_read(temp_data_root: Path) -> None:
    """Test full cycle: validate ATM limit, save raw ingest, stage option parquet, promote."""
    manager = OptionsBackfillManager(data_root=temp_data_root)
    reader = WarehouseReader(data_root=temp_data_root)

    task = OptionsBackfillTask(
        symbol="NIFTY26AUG25000CE",
        security_id="45000",
        underlying_symbol="NIFTY",
        expiry_date="2026-08-27",
        strike_price=25000.0,
        option_type="CALL",
        strike_step=50.0,
        is_index=True,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 27),
    )

    windows = generate_30_day_windows(task.start_date, task.end_date, max_days=30)
    assert len(windows) == 1

    payload = {
        "open": [120.0, 125.0],
        "high": [130.0, 128.0],
        "low": [118.0, 122.0],
        "close": [126.0, 124.0],
        "volume": [1500, 2200],
        "timestamp": [1785642300, 1785642360],
        "oi": [50000, 52000],
        "iv": [14.5, 14.8],
        "spot": [24980.0, 24995.0],
    }

    # Spot is 24980 -> strike 25000 is within ATM±10 (distance is 20 points, < 1 strike step)
    pointer, ingest_ids = manager.execute_options_backfill_from_payloads(
        task_window_payloads=[(task, windows[0], 24980.0, payload)],
        warehouse_version="wv-opt-test1",
    )

    assert pointer.pointer_generation == 1
    assert len(ingest_ids) == 1

    # Verify raw ingest file exists
    raw_files = list((temp_data_root / "raw" / "dhan" / "charts_options").glob("**/payload.json"))
    assert len(raw_files) == 1

    # Verify manifest exists and records ingest ID
    manifest = reader.get_manifest()
    assert manifest.source_ingest_ids == ingest_ids
    assert len(manifest.partitions) == 1
    rel_p = manifest.partitions[0].relative_path
    part_path = temp_data_root / "warehouse" / "versions" / "wv-opt-test1" / rel_p
    assert part_path.is_file()

    # Query option Parquet partition directly using DuckDB
    con = duckdb.connect(":memory:")
    try:
        clean_path = str(part_path).replace("\\", "/")
        opt_table = con.execute("SELECT * FROM read_parquet(?)", [clean_path]).to_arrow_table()
        assert opt_table.num_rows == 2
        assert opt_table.column("strike_price").to_pylist() == [25000.0, 25000.0]
        assert opt_table.column("implied_volatility").to_pylist() == [14.5, 14.8]
    finally:
        con.close()
