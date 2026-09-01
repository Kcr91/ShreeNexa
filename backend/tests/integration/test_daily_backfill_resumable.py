"""Integration tests for daily backfill execution, raw ingest, and warehouse publishing."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest
from app.warehouse.reader import WarehouseReader
from app.worker.daily_backfill import (
    AdjustmentStatus,
    DailyBackfillManager,
    DailyBackfillTask,
)


@pytest.fixture
def temp_data_root() -> Generator[Path]:
    """Provide temporary clean data directory."""
    with tempfile.TemporaryDirectory(prefix="shreenexa_backfill_") as tmp_dir:
        root = Path(tmp_dir) / "data"
        yield root


def test_daily_backfill_execution_and_warehouse_query(temp_data_root: Path) -> None:
    """Test full cycle: backfill tasks, raw provenance saving, and warehouse querying."""
    manager = DailyBackfillManager(data_root=temp_data_root)
    reader = WarehouseReader(data_root=temp_data_root)

    task_nifty = DailyBackfillTask(
        symbol="NIFTY 50",
        security_id="13",
        exchange_segment="IDX_I",
        instrument_type="INDEX",
        from_date=date(2026, 8, 1),
        to_date=date(2026, 8, 31),
        adjustment_status=AdjustmentStatus.UNADJUSTED,
    )

    nifty_payload = {
        "open": [24800.0, 24900.0],
        "high": [24950.0, 25000.0],
        "low": [24750.0, 24850.0],
        "close": [24920.0, 24980.0],
        "volume": [0, 0],
        "start_Time": [1785642300, 1785728700],
        "open_interest": [0, 0],
    }

    pointer, ingest_ids = manager.execute_backfill_from_payloads(
        tasks_and_payloads=[(task_nifty, nifty_payload)],
        code_commit="commit_f1_2",
    )

    assert pointer.pointer_generation == 1
    assert len(ingest_ids) == 1

    # Verify raw ingest file exists
    raw_files = list((temp_data_root / "raw" / "dhan" / "charts_daily").glob("**/payload.json"))
    assert len(raw_files) == 1

    # Verify warehouse manifest records ingest ID
    manifest = reader.get_manifest()
    assert manifest.source_ingest_ids == ingest_ids

    # Query daily bars through WarehouseReader
    bars_table = reader.query_bars(symbols=["NIFTY 50"])
    assert bars_table.num_rows == 2
    assert bars_table.column("close").to_pylist() == [24920.0, 24980.0]
