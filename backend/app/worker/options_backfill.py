"""Dhan expired-option historical backfill worker in 30-day windows with ATM coverage validation."""

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
from app.warehouse.schema import OptionBarRecord, option_bars_to_arrow_table

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"
MAX_OPTIONS_WINDOW_DAYS = 30


class StrikeUnavailableError(ValueError):
    """Raised when a requested option strike falls outside allowed ATM coverage boundaries."""

    def __init__(
        self,
        symbol: str,
        spot_price: float,
        requested_strike: float,
        strike_step: float,
        max_strikes: int,
    ) -> None:
        self.symbol = symbol
        self.spot_price = spot_price
        self.requested_strike = requested_strike
        self.strike_step = strike_step
        self.max_strikes = max_strikes
        super().__init__(
            f"Strike {requested_strike} for {symbol} is outside ATM coverage "
            f"(spot={spot_price}, step={strike_step}, max_strikes={max_strikes}). "
            f"Silent substitution is forbidden (strike_unavailable)."
        )


def validate_strike_coverage(
    symbol: str,
    spot_price: float,
    requested_strike: float,
    strike_step: float,
    is_index: bool,
) -> None:
    """Validate that requested strike is within ATM±10 (index) or ATM±3 (stock) limits."""
    if strike_step <= 0:
        raise ValueError(f"strike_step must be positive, got {strike_step}")

    max_strikes = 10 if is_index else 3
    offset_strikes = round(abs(requested_strike - spot_price) / strike_step)

    if offset_strikes > max_strikes:
        raise StrikeUnavailableError(
            symbol=symbol,
            spot_price=spot_price,
            requested_strike=requested_strike,
            strike_step=strike_step,
            max_strikes=max_strikes,
        )


def generate_30_day_windows(
    start_date: date,
    end_date: date,
    max_days: int = MAX_OPTIONS_WINDOW_DAYS,
) -> list[tuple[date, date]]:
    """Split date range into discrete non-overlapping <= 30-day windows."""
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

    windows: list[tuple[date, date]] = []
    current_start = start_date

    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=max_days - 1), end_date)
        windows.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)

    return windows


class OptionsBackfillTask(BaseModel):
    """Specification for expired options historical backfill."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    security_id: str
    underlying_symbol: str
    expiry_date: str
    strike_price: float
    option_type: str  # "CALL" or "PUT"
    strike_step: float
    is_index: bool = True
    start_date: date
    end_date: date


def save_raw_option_ingest(
    data_root: Path,
    payload_bytes: bytes,
    params: dict[str, Any],
    ingest_id: str | None = None,
) -> tuple[str, Path]:
    """Persist immutable raw JSON response and metadata under data/raw/dhan/charts_options/."""
    now = datetime.now(UTC)
    i_id = ingest_id or f"ri-opt-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")

    dest_dir = data_root / "raw" / "dhan" / "charts_options" / year_str / month_str / i_id
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
        "dataset": "charts_options",
        "created_at": now.isoformat(),
        "sha256": sha256_digest,
        "byte_count": len(payload_bytes),
        "params": safe_params,
        "redactions": ["access_token", "client_id", "token", "authorization_headers", "cookies"],
    }
    meta_file = dest_dir / "metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    return i_id, dest_dir


def parse_dhan_rolling_option_candles(
    payload: dict[str, Any],
    symbol: str,
    security_id: str,
    underlying_symbol: str,
    expiry_date: str,
    strike_price: float,
    option_type: str,
) -> list[OptionBarRecord]:
    """Parse Dhan `/charts/rollingoption` response into typed OptionBarRecord models."""
    opens = payload.get("open", [])
    highs = payload.get("high", [])
    lows = payload.get("low", [])
    closes = payload.get("close", [])
    volumes = payload.get("volume", [])
    start_times = payload.get("timestamp", payload.get("start_Time", []))
    open_interests = payload.get("oi", payload.get("open_interest", []))
    ivs = payload.get("iv", [])
    spots = payload.get("spot", [])

    count = min(len(opens), len(highs), len(lows), len(closes), len(start_times))
    bars: list[OptionBarRecord] = []

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
        iv = float(ivs[i]) if i < len(ivs) and ivs[i] is not None else 0.0
        spot = float(spots[i]) if i < len(spots) and spots[i] is not None else 0.0

        bars.append(
            OptionBarRecord(
                timestamp=ts,
                exchange_segment="NSE_FNO",
                security_id=security_id,
                symbol=symbol,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                open=float(opens[i]),
                high=float(highs[i]),
                low=float(lows[i]),
                close=float(closes[i]),
                volume=vol,
                open_interest=oi,
                implied_volatility=iv,
                spot_price=spot,
            )
        )

    bars.sort(key=lambda b: b.timestamp)
    return bars


class OptionsBackfillManager:
    """Manages 30-day window expired option backfills with ATM limits and warehouse promotion."""

    def __init__(
        self,
        data_root: Path | str | None = None,
        publisher: WarehousePublisher | None = None,
    ) -> None:
        self.data_root = Path(data_root).resolve() if data_root else DEFAULT_DATA_ROOT.resolve()
        self.publisher = publisher or WarehousePublisher(data_root=self.data_root)

    def execute_options_backfill_from_payloads(
        self,
        task_window_payloads: list[
            tuple[OptionsBackfillTask, tuple[date, date], float, dict[str, Any]]
        ],
        warehouse_version: str | None = None,
        code_commit: str | None = None,
    ) -> tuple[CurrentPointer, list[str]]:
        """Execute options backfill with ATM boundary verification and atomic promotion."""
        now = datetime.now(UTC)
        suffix = uuid.uuid4().hex[:8]
        w_ver = warehouse_version or f"wv-opt-{now.strftime('%Y%m%dT%H%M%SZ')}-{suffix}"

        ingest_ids: list[str] = []
        staged_partitions: list[PartitionMetadata] = []

        for task, (w_from, w_to), spot_price, payload in task_window_payloads:
            # 1. Enforce ATM limits (raises StrikeUnavailableError if beyond threshold)
            validate_strike_coverage(
                symbol=task.symbol,
                spot_price=spot_price,
                requested_strike=task.strike_price,
                strike_step=task.strike_step,
                is_index=task.is_index,
            )

            # 2. Save raw ingest artifact
            payload_bytes = json.dumps(payload, indent=2).encode("utf-8")
            params = {
                "symbol": task.symbol,
                "security_id": task.security_id,
                "underlying_symbol": task.underlying_symbol,
                "expiry_date": task.expiry_date,
                "strike_price": task.strike_price,
                "option_type": task.option_type,
                "spot_price": spot_price,
                "from_date": w_from.isoformat(),
                "to_date": w_to.isoformat(),
            }
            i_id, _ = save_raw_option_ingest(self.data_root, payload_bytes, params)
            ingest_ids.append(i_id)

            # 3. Parse option bars
            bars = parse_dhan_rolling_option_candles(
                payload=payload,
                symbol=task.symbol,
                security_id=task.security_id,
                underlying_symbol=task.underlying_symbol,
                expiry_date=task.expiry_date,
                strike_price=task.strike_price,
                option_type=task.option_type,
            )

            if not bars:
                continue

            # 4. Stage Parquet partition
            start_year = task.start_date.strftime("%Y")
            start_month = task.start_date.strftime("%m")
            table = option_bars_to_arrow_table(bars)
            rel_path = (
                f"options/segment=NSE_FNO/year={start_year}/month={start_month}/"
                f"{task.underlying_symbol.lower()}_{task.expiry_date}_{int(task.strike_price)}_{task.option_type.lower()}.parquet"
            )
            part_meta = self.publisher.stage_partition(
                warehouse_version=w_ver,
                data=table,
                relative_path=rel_path,
            )
            staged_partitions.append(part_meta)

        # 5. Atomically promote and publish warehouse version
        pointer = self.publisher.publish_version(
            warehouse_version=w_ver,
            partitions=staged_partitions,
            source_ingest_ids=ingest_ids,
            code_commit=code_commit or "dev_local",
            reason="options_backfill",
        )
        return pointer, ingest_ids
