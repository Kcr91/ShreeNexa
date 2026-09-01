"""Integration tests for warehouse atomic publication, DuckDB reads, and rollback."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.warehouse.manifest import CorrectionMetadata
from app.warehouse.publisher import WarehousePublisher
from app.warehouse.reader import WarehouseReader
from app.warehouse.schema import BarRecord


@pytest.fixture
def temp_data_root() -> Generator[Path]:
    """Provide clean temporary data root directory."""
    with tempfile.TemporaryDirectory(prefix="shreenexa_test_warehouse_") as tmp_dir:
        root = Path(tmp_dir) / "data"
        yield root


def test_atomic_publication_and_duckdb_reads(temp_data_root: Path) -> None:
    """Test full cycle: stage partitions, publish atomically, query via DuckDB with pruning."""
    publisher = WarehousePublisher(data_root=temp_data_root)
    reader = WarehouseReader(data_root=temp_data_root)

    # Initial state: no pointer
    assert reader.get_current_pointer() is None

    # Create synthetic bars for two stocks in August 2026
    hdfc_bars = [
        BarRecord(
            timestamp=datetime(2026, 8, 1, 9, 15 + i, tzinfo=UTC),
            exchange_segment="NSE_EQ",
            security_id="1333",
            symbol="HDFCBANK",
            open=1650.0 + i,
            high=1655.0 + i,
            low=1648.0 + i,
            close=1652.0 + i,
            volume=5000,
            open_interest=0,
        )
        for i in range(10)
    ]

    rel_bars = [
        BarRecord(
            timestamp=datetime(2026, 8, 1, 9, 15 + i, tzinfo=UTC),
            exchange_segment="NSE_EQ",
            security_id="2885",
            symbol="RELIANCE",
            open=2950.0 + i,
            high=2960.0 + i,
            low=2945.0 + i,
            close=2955.0 + i,
            volume=8000,
            open_interest=0,
        )
        for i in range(10)
    ]

    # Stage two separate partitions
    v1 = "wv-20260901T210000Z-v1test"
    p1 = publisher.stage_partition(
        warehouse_version=v1,
        data=hdfc_bars,
        relative_path="bars/segment=NSE_EQ/year=2026/month=08/hdfc.parquet",
    )
    p2 = publisher.stage_partition(
        warehouse_version=v1,
        data=rel_bars,
        relative_path="bars/segment=NSE_EQ/year=2026/month=08/reliance.parquet",
    )

    # Publish version 1 atomically
    pointer1 = publisher.publish_version(
        warehouse_version=v1,
        partitions=[p1, p2],
        code_commit="commit1",
    )

    assert pointer1.warehouse_version == v1
    assert pointer1.pointer_generation == 1

    # Read back through DuckDB
    active_ptr = reader.get_current_pointer()
    assert active_ptr is not None
    assert active_ptr.warehouse_version == v1

    # Query all bars
    all_bars = reader.query_bars()
    assert all_bars.num_rows == 20

    # Query symbol-specific bars (partition pruned)
    hdfc_table = reader.query_bars(symbols=["HDFCBANK"])
    assert hdfc_table.num_rows == 10
    symbols = set(hdfc_table.column("symbol").to_pylist())
    assert symbols == {"HDFCBANK"}

    # Query with date filter
    date_filtered = reader.query_bars(
        symbols=["HDFCBANK"],
        start_time=datetime(2026, 8, 1, 9, 20, tzinfo=UTC),
    )
    assert date_filtered.num_rows == 5


def test_interrupted_write_safety(temp_data_root: Path) -> None:
    """Test that an aborted or failed staging write does not corrupt active pointer."""
    publisher = WarehousePublisher(data_root=temp_data_root)
    reader = WarehouseReader(data_root=temp_data_root)

    # 1. Publish baseline version 1
    v1 = "wv-20260901T210000Z-v1"
    p1 = publisher.stage_partition(
        warehouse_version=v1,
        data=[
            BarRecord(
                timestamp=datetime(2026, 8, 1, 9, 15, tzinfo=UTC),
                exchange_segment="NSE_EQ",
                security_id="1333",
                symbol="HDFCBANK",
                open=1650.0,
                high=1655.0,
                low=1648.0,
                close=1652.0,
                volume=1000,
                open_interest=0,
            )
        ],
        relative_path="bars/segment=NSE_EQ/year=2026/month=08/part-000.parquet",
    )
    publisher.publish_version(warehouse_version=v1, partitions=[p1])

    # Baseline verified
    ptr1 = reader.get_current_pointer()
    assert ptr1 is not None
    assert ptr1.warehouse_version == v1

    # 2. Start staging version 2 but fail before publication
    v2 = "wv-20260901T210500Z-v2"
    publisher.stage_partition(
        warehouse_version=v2,
        data=[
            BarRecord(
                timestamp=datetime(2026, 8, 2, 9, 15, tzinfo=UTC),
                exchange_segment="NSE_EQ",
                security_id="1333",
                symbol="HDFCBANK",
                open=1660.0,
                high=1665.0,
                low=1658.0,
                close=1662.0,
                volume=2000,
                open_interest=0,
            )
        ],
        relative_path="bars/segment=NSE_EQ/year=2026/month=08/part-001.parquet",
    )

    # Simulate process interruption before publish_version is called
    # Readers must still see version 1 cleanly
    active_ptr = reader.get_current_pointer()
    assert active_ptr is not None
    assert active_ptr.warehouse_version == v1
    bars = reader.query_bars()
    assert bars.num_rows == 1
    assert bars.column("close")[0].as_py() == 1652.0


def test_correction_publication_and_rollback(temp_data_root: Path) -> None:
    """Test publishing a corrected partition in version 2, and rolling back to version 1."""
    publisher = WarehousePublisher(data_root=temp_data_root)
    reader = WarehouseReader(data_root=temp_data_root)

    # Version 1 with unadjusted price (close = 1650)
    v1 = "wv-20260901T210000Z-v1"
    p1 = publisher.stage_partition(
        warehouse_version=v1,
        data=[
            BarRecord(
                timestamp=datetime(2026, 8, 1, 9, 15, tzinfo=UTC),
                exchange_segment="NSE_EQ",
                security_id="1333",
                symbol="HDFCBANK",
                open=1640.0,
                high=1655.0,
                low=1640.0,
                close=1650.0,
                volume=1000,
                open_interest=0,
            )
        ],
        relative_path="bars/segment=NSE_EQ/year=2026/month=08/part-000.parquet",
    )
    publisher.publish_version(warehouse_version=v1, partitions=[p1])

    # Version 2 with corrected price (close = 1655)
    v2 = "wv-20260901T211000Z-v2"
    p2 = publisher.stage_partition(
        warehouse_version=v2,
        data=[
            BarRecord(
                timestamp=datetime(2026, 8, 1, 9, 15, tzinfo=UTC),
                exchange_segment="NSE_EQ",
                security_id="1333",
                symbol="HDFCBANK",
                open=1640.0,
                high=1655.0,
                low=1640.0,
                close=1655.0,
                volume=1000,
                open_interest=0,
            )
        ],
        relative_path="bars/segment=NSE_EQ/year=2026/month=08/part-000.parquet",
    )
    correction = CorrectionMetadata(
        reason="Corporate action adjustment",
        replaces_partition_digest=p1.sha256,
    )
    pointer2 = publisher.publish_version(
        warehouse_version=v2,
        partitions=[p2],
        parent_version=v1,
        corrections=[correction],
        reason="correction",
    )
    assert pointer2.pointer_generation == 2
    assert reader.query_bars().column("close")[0].as_py() == 1655.0

    # Execute rollback to version 1
    pointer3 = publisher.rollback_to(target_version=v1, reason="rollback to v1")
    assert pointer3.warehouse_version == v1
    assert pointer3.pointer_generation == 3

    # Verification: query returns original close 1650.0
    assert reader.query_bars().column("close")[0].as_py() == 1650.0
