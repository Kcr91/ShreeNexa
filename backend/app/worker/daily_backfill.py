"""Dhan daily backfill worker with resumability, raw provenance, and adjustment tracking."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.warehouse.manifest import CurrentPointer, PartitionMetadata
from app.warehouse.publisher import WarehousePublisher
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"


class AdjustmentStatus(StrEnum):
    """Corporate action adjustment classification for historical bars."""

    UNADJUSTED = "unadjusted"
    ADJUSTED = "adjusted"
    INVESTIGATION_PENDING = "investigation_pending"


class DailyBackfillTask(BaseModel):
    """Task specification for backfilling historical daily bars."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    security_id: str
    exchange_segment: str
    instrument_type: str = "EQUITY"
    from_date: date
    to_date: date
    adjustment_status: AdjustmentStatus = AdjustmentStatus.INVESTIGATION_PENDING


def save_raw_ingest(
    data_root: Path,
    payload_bytes: bytes,
    params: dict[str, Any],
    ingest_id: str | None = None,
) -> tuple[str, Path]:
    """Persist immutable raw JSON response and provenance metadata under data/raw/."""
    now = datetime.now(UTC)
    i_id = ingest_id or f"ri-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")

    dest_dir = data_root / "raw" / "dhan" / "charts_daily" / year_str / month_str / i_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    payload_file = dest_dir / "payload.json"
    payload_file.write_bytes(payload_bytes)

    sha256_digest = hashlib.sha256(payload_bytes).hexdigest()

    # Redact sensitive parameters
    sensitive_keys = {"access_token", "client_id", "token"}
    safe_params = {k: v for k, v in params.items() if k not in sensitive_keys}

    metadata = {
        "format_version": 1,
        "ingest_id": i_id,
        "provider": "dhan",
        "dataset": "charts_daily",
        "created_at": now.isoformat(),
        "sha256": sha256_digest,
        "byte_count": len(payload_bytes),
        "params": safe_params,
        "redactions": ["access_token", "client_id", "token", "authorization_headers", "cookies"],
    }
    meta_file = dest_dir / "metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    return i_id, dest_dir


def parse_dhan_daily_candles(
    payload: dict[str, Any],
    symbol: str,
    security_id: str,
    exchange_segment: str,
) -> list[BarRecord]:
    """Parse Dhan `/charts/historical` JSON response arrays into typed BarRecord models."""
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
            # Epoch seconds or milliseconds
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


class DailyBackfillManager:
    """Manages resumable backfill execution, raw ingest preservation, and warehouse promotion."""

    def __init__(
        self,
        data_root: Path | str | None = None,
        publisher: WarehousePublisher | None = None,
    ) -> None:
        self.data_root = Path(data_root).resolve() if data_root else DEFAULT_DATA_ROOT.resolve()
        self.publisher = publisher or WarehousePublisher(data_root=self.data_root)

    def execute_backfill_from_payloads(
        self,
        tasks_and_payloads: list[tuple[DailyBackfillTask, dict[str, Any]]],
        warehouse_version: str | None = None,
        code_commit: str | None = None,
    ) -> tuple[CurrentPointer, list[str]]:
        """Execute daily backfill given tasks and raw payloads (supports offline testing)."""
        now = datetime.now(UTC)
        w_ver = warehouse_version or f"wv-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"

        staged_partitions: list[PartitionMetadata] = []
        ingest_ids: list[str] = []

        for task, payload in tasks_and_payloads:
            # 1. Save raw payload artifact
            payload_bytes = json.dumps(payload, indent=2).encode("utf-8")
            params = {
                "symbol": task.symbol,
                "security_id": task.security_id,
                "exchange_segment": task.exchange_segment,
                "instrument_type": task.instrument_type,
                "from_date": task.from_date.isoformat(),
                "to_date": task.to_date.isoformat(),
                "adjustment_status": task.adjustment_status.value,
            }
            i_id, _ = save_raw_ingest(self.data_root, payload_bytes, params)
            ingest_ids.append(i_id)

            # 2. Parse into BarRecords
            bars = parse_dhan_daily_candles(
                payload=payload,
                symbol=task.symbol,
                security_id=task.security_id,
                exchange_segment=task.exchange_segment,
            )

            if not bars:
                logger.warning("No bars parsed for task %s (%s)", task.symbol, task.security_id)
                continue

            # 3. Stage partition
            start_year = task.from_date.strftime("%Y")
            start_month = task.from_date.strftime("%m")
            rel_path = (
                f"bars/segment={task.exchange_segment}/year={start_year}/"
                f"month={start_month}/{task.symbol.lower()}_daily.parquet"
            )
            part_meta = self.publisher.stage_partition(
                warehouse_version=w_ver,
                data=bars,
                relative_path=rel_path,
            )
            staged_partitions.append(part_meta)

        # 4. Promote and publish warehouse version
        pointer = self.publisher.publish_version(
            warehouse_version=w_ver,
            partitions=staged_partitions,
            source_ingest_ids=ingest_ids,
            code_commit=code_commit or "dev_local",
            reason="daily_backfill",
        )
        return pointer, ingest_ids
