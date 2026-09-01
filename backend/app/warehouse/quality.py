"""Data-quality reporting engine for gaps, duplicates, outliers, zero volume, and coverage."""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.marketdata.calendar import TradingCalendar, to_utc
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


class DefectType(StrEnum):
    """Categorized data anomaly types."""

    TIMESTAMP_GAP = "TIMESTAMP_GAP"
    DUPLICATE_TIMESTAMP = "DUPLICATE_TIMESTAMP"
    PRICE_OUTLIER = "PRICE_OUTLIER"
    ZERO_VOLUME_ACTIVE = "ZERO_VOLUME_ACTIVE"
    UNEXPECTED_SESSION_DATE = "UNEXPECTED_SESSION_DATE"
    STALE_PARTITION = "STALE_PARTITION"


class OriginCategory(StrEnum):
    """Origin attributing whether defect is an upstream broker omission or warehouse error."""

    UPSTREAM_SOURCE = "UPSTREAM_SOURCE"
    WAREHOUSE_INTEGRITY = "WAREHOUSE_INTEGRITY"


class DefectRecord(BaseModel):
    """Detailed audit record for a single detected quality anomaly."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    timestamp: datetime | None = None
    defect_type: DefectType
    origin: OriginCategory
    details: str


class CoverageSummary(BaseModel):
    """Summary of data coverage and defect counts for an individual symbol."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    total_bars: int
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    gap_count: int = 0
    duplicate_count: int = 0
    outlier_count: int = 0
    zero_volume_count: int = 0
    unexpected_date_count: int = 0


class DataQualityReport(BaseModel):
    """Overall dataset audit report across symbols and warehouse partitions."""

    model_config = ConfigDict(frozen=True)

    report_id: str
    generated_at: datetime
    total_symbols_analyzed: int
    total_defects_found: int
    defects: list[DefectRecord]
    coverage_by_symbol: dict[str, CoverageSummary]


class DataQualityAnalyzer:
    """Evaluates OHLCV bar datasets for gaps, duplicates, outliers, and session integrity."""

    def __init__(
        self,
        calendar: TradingCalendar | None = None,
        outlier_threshold_pct: float = 0.20,
    ) -> None:
        self.calendar = calendar or TradingCalendar()
        self.outlier_threshold_pct = outlier_threshold_pct

    def analyze_bars(
        self,
        symbol: str,
        bars: list[BarRecord],
        segment: str = "NSE_EQ",
        is_raw_ingest: bool = False,
    ) -> tuple[CoverageSummary, list[DefectRecord]]:
        """Analyze a sequence of BarRecord models for quality defects."""
        if not bars:
            summary = CoverageSummary(symbol=symbol, total_bars=0)
            return summary, []

        defects: list[DefectRecord] = []
        default_origin = (
            OriginCategory.UPSTREAM_SOURCE if is_raw_ingest else OriginCategory.WAREHOUSE_INTEGRITY
        )

        # 1. Duplicate detection
        timestamps = [to_utc(b.timestamp) for b in bars]
        ts_counts = Counter(timestamps)
        dup_count = 0
        for ts, count in ts_counts.items():
            if count > 1:
                dup_count += count - 1
                defects.append(
                    DefectRecord(
                        symbol=symbol,
                        timestamp=ts,
                        defect_type=DefectType.DUPLICATE_TIMESTAMP,
                        origin=OriginCategory.WAREHOUSE_INTEGRITY,
                        details=f"Found {count} duplicate bars sharing timestamp {ts.isoformat()}",
                    )
                )

        # 2. Sort unique bars chronologically
        unique_bars = sorted(
            {to_utc(b.timestamp): b for b in bars}.values(), key=lambda b: b.timestamp
        )

        # 3. Session boundaries, Zero Volume, Outliers, and Gaps
        unexpected_count = 0
        zero_vol_count = 0
        outlier_count = 0
        gap_count = 0

        for i, bar in enumerate(unique_bars):
            ts = to_utc(bar.timestamp)

            # Check session validity
            is_valid_session = self.calendar.validate_bar_session(ts, segment=segment)
            if not is_valid_session:
                unexpected_count += 1
                defects.append(
                    DefectRecord(
                        symbol=symbol,
                        timestamp=ts,
                        defect_type=DefectType.UNEXPECTED_SESSION_DATE,
                        origin=default_origin,
                        details=f"Outside valid trading session/holiday: {ts.isoformat()}",
                    )
                )

            # Check zero volume during active session
            if is_valid_session and bar.volume == 0:
                zero_vol_count += 1
                defects.append(
                    DefectRecord(
                        symbol=symbol,
                        timestamp=ts,
                        defect_type=DefectType.ZERO_VOLUME_ACTIVE,
                        origin=OriginCategory.UPSTREAM_SOURCE,
                        details=f"Zero volume in active session at {ts.isoformat()}",
                    )
                )

            # Check price outlier w.r.t previous bar
            if i > 0:
                prev_bar = unique_bars[i - 1]
                prev_close = prev_bar.close
                if prev_close > 0:
                    pct_change = abs(bar.close - prev_close) / prev_close
                    if pct_change >= self.outlier_threshold_pct:
                        outlier_count += 1
                        defects.append(
                            DefectRecord(
                                symbol=symbol,
                                timestamp=ts,
                                defect_type=DefectType.PRICE_OUTLIER,
                                origin=OriginCategory.UPSTREAM_SOURCE,
                                details=(
                                    f"Price jump of {pct_change * 100:.1f}% "
                                    f"from {prev_close} to {bar.close} exceeds threshold"
                                ),
                            )
                        )

                # Check intraday gap between consecutive bars during same session
                prev_ts = to_utc(prev_bar.timestamp)
                prev_valid = self.calendar.validate_bar_session(prev_ts, segment=segment)
                if is_valid_session and prev_valid:
                    # If same day and difference > 1 minute (e.g. >= 2 minutes)
                    if prev_ts.date() == ts.date() and (ts - prev_ts) >= timedelta(minutes=2):
                        missing_mins = int((ts - prev_ts).total_seconds() // 60) - 1
                        gap_count += 1
                        defects.append(
                            DefectRecord(
                                symbol=symbol,
                                timestamp=prev_ts,
                                defect_type=DefectType.TIMESTAMP_GAP,
                                origin=OriginCategory.UPSTREAM_SOURCE,
                                details=f"Gap of {missing_mins}m: {prev_ts} to {ts}",
                            )
                        )

        summary = CoverageSummary(
            symbol=symbol,
            total_bars=len(bars),
            first_timestamp=unique_bars[0].timestamp if unique_bars else None,
            last_timestamp=unique_bars[-1].timestamp if unique_bars else None,
            gap_count=gap_count,
            duplicate_count=dup_count,
            outlier_count=outlier_count,
            zero_volume_count=zero_vol_count,
            unexpected_date_count=unexpected_count,
        )
        return summary, defects

    def generate_report(
        self,
        symbol_bars_map: dict[str, list[BarRecord]],
        segment: str = "NSE_EQ",
        is_raw_ingest: bool = False,
    ) -> DataQualityReport:
        """Generate comprehensive data quality report across multiple symbols."""
        now = datetime.now(UTC)
        rep_id = f"dqr-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"

        all_defects: list[DefectRecord] = []
        coverage_map: dict[str, CoverageSummary] = {}

        for sym, bars in symbol_bars_map.items():
            summary, defects = self.analyze_bars(
                symbol=sym,
                bars=bars,
                segment=segment,
                is_raw_ingest=is_raw_ingest,
            )
            coverage_map[sym] = summary
            all_defects.extend(defects)

        return DataQualityReport(
            report_id=rep_id,
            generated_at=now,
            total_symbols_analyzed=len(symbol_bars_map),
            total_defects_found=len(all_defects),
            defects=all_defects,
            coverage_by_symbol=coverage_map,
        )
