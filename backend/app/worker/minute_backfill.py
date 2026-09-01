"""Dhan 1-minute historical backfill worker in 90-day windows with deduplication."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.warehouse.manifest import CurrentPointer, PartitionMetadata
from app.warehouse.publisher import WarehousePublisher
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"
MAX_INTRADAY_WINDOW_DAYS = 90


def generate_90_day_windows(
    start_date: date,
    end_date: date,
    max_days: int = MAX_INTRADAY_WINDOW_DAYS,
) -> list[tuple[date, date]]:
    """Split a broad date range into discrete non-overlapping <= 90-day windows."""
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

    windows: list[tuple[date, date]] = []
    current_start = start_date

    while current_start <= end_date:
        # Window end is current_start + max_days - 1 day, capped at end_date
        current_end = min(current_start + timedelta(days=max_days - 1), end_date)
        windows.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)

    return windows


class MinuteBackfillTask(BaseModel):
    """Specification for 1-minute historical bar backfill."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    security_id: str
    exchange_segment: str
    instrument_type: str = "EQUITY"
    start_date: date
    end_date: date


class MinuteCoverageReport(BaseModel):
    """Data quality and coverage report for backfilled 1-minute bars."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    security_id: str
    exchange_segment: str
    total_bars: int
    start_time: str | None = None
    end_time: str | None = None
    duplicate_count: int = 0
    gaps_detected: int = 0
    sha256: str = ""


def save_raw_minute_ingest(
    data_root: Path,
    payload_bytes: bytes,
    params: dict[str, Any],
    ingest_id: str | None = None,
) -> tuple[str, Path]:
    """Persist immutable raw JSON response and metadata under data/raw/dhan/charts_intraday/."""
    now = datetime.now(UTC)
    i_id = ingest_id or f"ri-1m-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")

    dest_dir = data_root / "raw" / "dhan" / "charts_intraday" / year_str / month_str / i_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    payload_file = dest_dir / "payload.json"
    payload_file.write_bytes(payload_bytes)

    sha256_digest = hashlib.sha256(payload_bytes).hexdigest()

    sensitive_keys = {"access_token", "client_id", "token"}
    safe_params = {k: v for k, v in params.items() if k not in sensitive_keys}

    metadata = {
        "format_version": 1,
        "ingest_id": i_id,
        "provider": "dhan",
        "dataset": "charts_intraday",
        "interval": "1m",
        "created_at": now.isoformat(),
        "sha256": sha256_digest,
        "byte_count": len(payload_bytes),
        "params": safe_params,
        "redactions": ["access_token", "client_id", "token", "authorization_headers", "cookies"],
    }
    meta_file = dest_dir / "metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    return i_id, dest_dir


def parse_dhan_intraday_candles(
    payload: dict[str, Any],
    symbol: str,
    security_id: str,
    exchange_segment: str,
) -> list[BarRecord]:
    """Parse Dhan `/charts/intraday` JSON response arrays into typed BarRecord models."""
    opens = payload.get("open", [])
    highs = payload.get("high", [])
    lows = payload.get("low", [])
    closes = payload.get("close", [])
    volumes = payload.get("volume", [])
    start_times = payload.get("start_Time", [])
    open_interests = payload.get("open_interest", [])

    count = min(len(opens), len(highs), len(lows), len(closes), len(start_times))
    bars: list[BarRecord] = []

    for i in range(count):
        raw_ts = start_times[i]
        if isinstance(raw_ts, (int, float)):
            if raw_ts > 10_000_000_000:
                ts = datetime.fromtimestamp(raw_ts / 1000.0, tz=UTC)
            else:
                ts = datetime.fromtimestamp(float(raw_ts), tz=UTC)
        elif isinstance(raw_ts, str):
            try:
                ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
            except Exception:
                ts = datetime.now(UTC)
        else:
            ts = datetime.now(UTC)

        vol = int(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0
        oi = (
            int(open_interests[i])
            if i < len(open_interests) and open_interests[i] is not None
            else 0
        )

        bars.append(
            BarRecord(
                timestamp=ts,
                exchange_segment=exchange_segment,
                security_id=security_id,
                symbol=symbol,
                open=float(opens[i]),
                high=float(highs[i]),
                low=float(lows[i]),
                close=float(closes[i]),
                volume=vol,
                open_interest=oi,
            )
        )

    # Sort bars by timestamp ascending
    bars.sort(key=lambda b: b.timestamp)
    return bars


def analyze_minute_bars(
    bars: list[BarRecord],
    symbol: str,
    security_id: str,
    exchange_segment: str,
) -> MinuteCoverageReport:
    """Analyze bar collection for duplicates, gaps, coverage span, and SHA-256 fingerprint."""
    if not bars:
        return MinuteCoverageReport(
            symbol=symbol,
            security_id=security_id,
            exchange_segment=exchange_segment,
            total_bars=0,
            duplicate_count=0,
            gaps_detected=0,
            sha256=hashlib.sha256(b"").hexdigest(),
        )

    seen_timestamps: set[datetime] = set()
    duplicate_count = 0
    gaps_detected = 0

    sorted_bars = sorted(bars, key=lambda b: b.timestamp)
    for i, b in enumerate(sorted_bars):
        if b.timestamp in seen_timestamps:
            duplicate_count += 1
        seen_timestamps.add(b.timestamp)

        if i > 0:
            delta = sorted_bars[i].timestamp - sorted_bars[i - 1].timestamp
            # In Indian market, inter-day gap is normal; gap > 1 day counts as session boundary
            if delta > timedelta(days=4):
                gaps_detected += 1

    # Fingerprint all bars
    canonical_repr = "".join(
        f"{b.timestamp.isoformat()}:{b.open}:{b.high}:{b.low}:{b.close}:{b.volume};"
        for b in sorted_bars
    ).encode("utf-8")
    digest = hashlib.sha256(canonical_repr).hexdigest()

    return MinuteCoverageReport(
        symbol=symbol,
        security_id=security_id,
        exchange_segment=exchange_segment,
        total_bars=len(sorted_bars),
        start_time=sorted_bars[0].timestamp.isoformat(),
        end_time=sorted_bars[-1].timestamp.isoformat(),
        duplicate_count=duplicate_count,
        gaps_detected=gaps_detected,
        sha256=digest,
    )


class MinuteBackfillManager:
    """Manages resumable 90-day window 1m backfills, deduplication, and warehouse publication."""

    def __init__(
        self,
        data_root: Path | str | None = None,
        publisher: WarehousePublisher | None = None,
    ) -> None:
        self.data_root = Path(data_root).resolve() if data_root else DEFAULT_DATA_ROOT.resolve()
        self.publisher = publisher or WarehousePublisher(data_root=self.data_root)

    def execute_minute_backfill_from_payloads(
        self,
        window_payloads: list[tuple[MinuteBackfillTask, tuple[date, date], dict[str, Any]]],
        warehouse_version: str | None = None,
        code_commit: str | None = None,
    ) -> tuple[CurrentPointer, list[MinuteCoverageReport], list[str]]:
        """Execute multi-window backfill with deduplication and quality reporting."""
        now = datetime.now(UTC)
        suffix = uuid.uuid4().hex[:8]
        w_ver = warehouse_version or f"wv-1m-{now.strftime('%Y%m%dT%H%M%SZ')}-{suffix}"

        ingest_ids: list[str] = []
        symbol_bars_map: dict[str, tuple[MinuteBackfillTask, dict[datetime, BarRecord]]] = {}

        for task, (w_from, w_to), payload in window_payloads:
            # 1. Save raw payload artifact
            payload_bytes = json.dumps(payload, indent=2).encode("utf-8")
            params = {
                "symbol": task.symbol,
                "security_id": task.security_id,
                "exchange_segment": task.exchange_segment,
                "from_date": w_from.isoformat(),
                "to_date": w_to.isoformat(),
                "interval": "1m",
            }
            i_id, _ = save_raw_minute_ingest(self.data_root, payload_bytes, params)
            ingest_ids.append(i_id)

            # 2. Parse into BarRecords
            bars = parse_dhan_intraday_candles(
                payload=payload,
                symbol=task.symbol,
                security_id=task.security_id,
                exchange_segment=task.exchange_segment,
            )

            # 3. Deduplicate across windows using timestamp map
            if task.symbol not in symbol_bars_map:
                symbol_bars_map[task.symbol] = (task, {})
            _, ts_map = symbol_bars_map[task.symbol]
            for bar in bars:
                ts_map[bar.timestamp] = bar

        reports: list[MinuteCoverageReport] = []
        staged_partitions: list[PartitionMetadata] = []

        for _symbol, (task, ts_map) in symbol_bars_map.items():
            deduped_bars = sorted(ts_map.values(), key=lambda b: b.timestamp)
            report = analyze_minute_bars(
                bars=deduped_bars,
                symbol=task.symbol,
                security_id=task.security_id,
                exchange_segment=task.exchange_segment,
            )
            reports.append(report)

            if not deduped_bars:
                continue

            # Stage partition into warehouse
            start_year = task.start_date.strftime("%Y")
            start_month = task.start_date.strftime("%m")
            rel_path = (
                f"bars/segment={task.exchange_segment}/year={start_year}/"
                f"month={start_month}/{task.symbol.lower()}_1m.parquet"
            )
            part_meta = self.publisher.stage_partition(
                warehouse_version=w_ver,
                data=deduped_bars,
                relative_path=rel_path,
            )
            staged_partitions.append(part_meta)

        # Publish version atomically
        pointer = self.publisher.publish_version(
            warehouse_version=w_ver,
            partitions=staged_partitions,
            source_ingest_ids=ingest_ids,
            code_commit=code_commit or "dev_local",
            reason="minute_backfill",
        )

        return pointer, reports, ingest_ids
