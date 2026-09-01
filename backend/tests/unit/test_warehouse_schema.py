"""Unit tests for warehouse bar schemas and PyArrow conversions."""

from __future__ import annotations

from datetime import UTC, datetime

import pyarrow as pa
from app.warehouse.schema import (
    BAR_SCHEMA_PYARROW,
    BarRecord,
    bars_to_arrow_table,
)


def test_bar_record_validation_and_conversion() -> None:
    """Verify BarRecord model and dictionary conversion."""
    bar = BarRecord(
        timestamp=datetime(2026, 8, 1, 9, 15, tzinfo=UTC),
        exchange_segment="NSE_EQ",
        security_id="1333",
        symbol="HDFCBANK",
        open=1650.0,
        high=1660.0,
        low=1645.0,
        close=1655.0,
        volume=10000,
        open_interest=0,
    )
    d = bar.to_dict()
    assert d["symbol"] == "HDFCBANK"
    assert d["open"] == 1650.0
    assert d["timestamp"].tzinfo == UTC


def test_bars_to_arrow_table() -> None:
    """Verify converting sequence of BarRecords to typed PyArrow Table."""
    bars = [
        BarRecord(
            timestamp=datetime(2026, 8, 1, 9, 15 + i, tzinfo=UTC),
            exchange_segment="NSE_EQ",
            security_id="1333",
            symbol="HDFCBANK",
            open=1650.0 + i,
            high=1655.0 + i,
            low=1648.0 + i,
            close=1652.0 + i,
            volume=5000 * (i + 1),
            open_interest=0,
        )
        for i in range(5)
    ]

    table = bars_to_arrow_table(bars)
    assert table.num_rows == 5
    assert table.num_columns == 10
    assert table.schema.equals(BAR_SCHEMA_PYARROW)

    # Check field types
    assert table.schema.field("timestamp").type == pa.timestamp("ms", tz="UTC")
    assert table.schema.field("volume").type == pa.int64()
    assert table.schema.field("open").type == pa.float64()


def test_empty_bars_to_arrow_table() -> None:
    """Verify converting empty list produces an empty table with correct schema."""
    table = bars_to_arrow_table([])
    assert table.num_rows == 0
    assert table.schema.equals(BAR_SCHEMA_PYARROW)
