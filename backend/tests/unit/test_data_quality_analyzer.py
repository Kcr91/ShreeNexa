"""Unit tests for data-quality reporting, seeded defect detection, and origin attribution."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.warehouse.quality import (
    DataQualityAnalyzer,
    DefectType,
    OriginCategory,
)
from app.warehouse.schema import BarRecord

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_quality_seeded_bars.json"


def test_seeded_defect_detection_100_percent() -> None:
    """Verify DataQualityAnalyzer detects all seeded defects in sample_quality_seeded_bars.json."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    bars = [
        BarRecord(
            timestamp=datetime.fromisoformat(b["timestamp"]),
            exchange_segment=data["exchange_segment"],
            security_id="11536",
            symbol=data["symbol"],
            open=b["open"],
            high=b["high"],
            low=b["low"],
            close=b["close"],
            volume=b["volume"],
            open_interest=b["open_interest"],
        )
        for b in data["bars"]
    ]

    analyzer = DataQualityAnalyzer(outlier_threshold_pct=0.20)
    summary, defects = analyzer.analyze_bars(symbol="TCS", bars=bars, segment="NSE_EQ")

    assert summary.total_bars == 6
    assert summary.duplicate_count == 1
    assert summary.outlier_count >= 1
    assert summary.zero_volume_count == 1
    assert summary.unexpected_date_count == 1
    assert summary.gap_count >= 1

    defect_types = {d.defect_type for d in defects}
    assert DefectType.DUPLICATE_TIMESTAMP in defect_types
    assert DefectType.PRICE_OUTLIER in defect_types
    assert DefectType.ZERO_VOLUME_ACTIVE in defect_types
    assert DefectType.UNEXPECTED_SESSION_DATE in defect_types
    assert DefectType.TIMESTAMP_GAP in defect_types


def test_origin_classification_upstream_vs_warehouse() -> None:
    """Verify proper attribution between UPSTREAM_SOURCE and WAREHOUSE_INTEGRITY."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    bars = [
        BarRecord(
            timestamp=datetime.fromisoformat(b["timestamp"]),
            exchange_segment=data["exchange_segment"],
            security_id="11536",
            symbol=data["symbol"],
            open=b["open"],
            high=b["high"],
            low=b["low"],
            close=b["close"],
            volume=b["volume"],
            open_interest=b["open_interest"],
        )
        for b in data["bars"]
    ]

    analyzer = DataQualityAnalyzer()
    _, defects = analyzer.analyze_bars(symbol="TCS", bars=bars, is_raw_ingest=True)

    # Duplicates are always marked as WAREHOUSE_INTEGRITY
    dup_defects = [d for d in defects if d.defect_type == DefectType.DUPLICATE_TIMESTAMP]
    assert len(dup_defects) > 0
    assert all(d.origin == OriginCategory.WAREHOUSE_INTEGRITY for d in dup_defects)

    # Outliers and gaps are marked as UPSTREAM_SOURCE
    outliers = [d for d in defects if d.defect_type == DefectType.PRICE_OUTLIER]
    assert len(outliers) > 0
    assert all(d.origin == OriginCategory.UPSTREAM_SOURCE for d in outliers)


def test_generate_multi_symbol_report() -> None:
    """Verify aggregate DataQualityReport generation across multiple symbols."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    bars = [
        BarRecord(
            timestamp=datetime.fromisoformat(b["timestamp"]),
            exchange_segment=data["exchange_segment"],
            security_id="11536",
            symbol=data["symbol"],
            open=b["open"],
            high=b["high"],
            low=b["low"],
            close=b["close"],
            volume=b["volume"],
            open_interest=b["open_interest"],
        )
        for b in data["bars"]
    ]

    analyzer = DataQualityAnalyzer()
    report = analyzer.generate_report(
        symbol_bars_map={"TCS": bars, "INFY": bars[:2]},
        segment="NSE_EQ",
    )

    assert report.total_symbols_analyzed == 2
    assert "TCS" in report.coverage_by_symbol
    assert "INFY" in report.coverage_by_symbol
    assert report.total_defects_found > 0
    assert report.report_id.startswith("dqr-")
