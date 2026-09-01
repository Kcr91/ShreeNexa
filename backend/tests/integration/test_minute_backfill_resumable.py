"""Integration tests for 90-day window 1m backfills, deduplication, and warehouse reads."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest
from app.warehouse.reader import WarehouseReader
from app.worker.minute_backfill import (
    MinuteBackfillManager,
    MinuteBackfillTask,
    generate_90_day_windows,
)


@pytest.fixture
def temp_data_root() -> Generator[Path]:
    """Provide clean temporary data directory."""
    with tempfile.TemporaryDirectory(prefix="shreenexa_1m_test_") as tmp_dir:
        root = Path(tmp_dir) / "data"
        yield root


def test_minute_backfill_kill_resume_deduplication(temp_data_root: Path) -> None:
    """Test kill/resume idempotency: repeated windows produce zero duplicates in warehouse."""
    manager = MinuteBackfillManager(data_root=temp_data_root)
    reader = WarehouseReader(data_root=temp_data_root)

    task = MinuteBackfillTask(
        symbol="HDFCBANK",
        security_id="1333",
        exchange_segment="NSE_EQ",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 29),
    )

    windows = generate_90_day_windows(task.start_date, task.end_date, max_days=90)
    assert len(windows) == 2

    # Window 1 payload (3 bars)
    w1_payload = {
        "open": [1650.0, 1651.0, 1652.0],
        "high": [1655.0, 1656.0, 1657.0],
        "low": [1648.0, 1649.0, 1650.0],
        "close": [1651.0, 1652.0, 1653.0],
        "volume": [1000, 1200, 1100],
        "start_Time": [1767258900, 1767258960, 1767259020],  # 2026-01-01
        "open_interest": [0, 0, 0],
    }

    # Window 2 payload (3 bars, including 1 bar overlapping from window 1)
    w2_payload = {
        "open": [1652.0, 1660.0, 1665.0],
        "high": [1657.0, 1665.0, 1670.0],
        "low": [1650.0, 1658.0, 1662.0],
        "close": [1653.0, 1662.0, 1668.0],
        "volume": [1100, 2000, 2500],
        "start_Time": [1767259020, 1775034900, 1775034960],  # 1st timestamp overlaps with w1 bar 3
        "open_interest": [0, 0, 0],
    }

    # 1. Run only window 1 (simulate partial run before kill)
    pointer1, reports1, _ = manager.execute_minute_backfill_from_payloads(
        window_payloads=[(task, windows[0], w1_payload)],
        warehouse_version="wv-1m-run1",
    )
    assert pointer1.pointer_generation == 1
    assert reports1[0].total_bars == 3
    assert reports1[0].duplicate_count == 0

    # 2. Resume / re-run with both window 1 and window 2 (with overlapping bar)
    pointer2, reports2, _ = manager.execute_minute_backfill_from_payloads(
        window_payloads=[
            (task, windows[0], w1_payload),
            (task, windows[1], w2_payload),
        ],
        warehouse_version="wv-1m-run2",
    )
    assert pointer2.pointer_generation == 2
    # Total unique bars must be 5 (3 from w1 + 2 new from w2)
    assert reports2[0].total_bars == 5
    assert reports2[0].duplicate_count == 0

    # 3. Verify DuckDB queries return exactly 5 bars with zero duplicates
    bars_table = reader.query_bars(symbols=["HDFCBANK"])
    assert bars_table.num_rows == 5
    timestamps = bars_table.column("timestamp").to_pylist()
    assert len(timestamps) == len(set(timestamps))  # strictly unique
