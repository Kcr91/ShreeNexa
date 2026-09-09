"""Fetch driver connecting the Dhan REST client to the resumable backfill queue.

This is the layer that was missing. ``DhanRestClient.get_historical_daily`` and its
siblings were never called from ``app/``, and the three backfill managers only accept
already-fetched payloads, so nothing walked a universe, spent the API budget, or recorded
what it had already collected.

One pass is deliberately small: claim a window, fetch it, publish it, checkpoint it. That
granularity is what makes a multi-week download survivable - the process can die at any
instant and lose at most one window's work.

Budget discipline is inherited rather than reimplemented: every call goes through
``DhanRestClient``, which acquires a rate-limiter token per attempt (including retries).
When a per-day budget is exhausted the limiter raises, the lease is released without
consuming an attempt, and the run stops cleanly until the budget window rolls over.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine

from app.dhan.client import DhanRestClient
from app.dhan.exceptions import (
    DhanAuthenticationError,
    DhanClientError,
    DhanError,
    DhanRateLimitError,
)
from app.dhan.models import DhanHistoricalData
from app.marketdata.calendar import TradingCalendar, to_ist
from app.warehouse import paths
from app.warehouse.paths import DataRootCapacityError, check_write_admission
from app.warehouse.publisher import WarehousePublisher
from app.worker.backfill_queue import (
    ClaimedWindow,
    claim_next_window,
    complete_window,
    fail_window,
    pause_all_for_auth,
    reclaim_stale_leases,
    release_window,
    upsert_coverage,
)
from app.worker.daily_backfill import DailyBackfillManager, DailyBackfillTask, save_raw_ingest
from app.worker.minute_backfill import (
    MinuteBackfillManager,
    MinuteBackfillTask,
    save_raw_minute_ingest,
)
from app.worker.options_backfill import (
    INDEX_MAX_STRIKES,
    STOCK_MAX_STRIKES,
    OptionsBackfillManager,
    OptionsBackfillTask,
    StrikeUnavailableError,
    save_raw_option_ingest,
)

logger = logging.getLogger(__name__)

# Datasets fetched with charts/intraday or charts/rollingoption share one daily budget;
# "daily" uses charts/historical, which has its own. See config/dhan_limits.yaml.
DAILY_DATASETS = frozenset({"daily"})
OPTION_DATASETS = frozenset({"options"})

# Below this share of bars inside regular market hours a window is flagged as suspect
# in the Historic Data Report. It is NOT rejected: exchange calendars are not something
# this system can adjudicate. Holidays differ per exchange, holiday dates move, Muhurat
# and other special sessions exist, and sessions are sometimes shortened or run outside
# the usual window. An earlier version of this guard discarded a whole month of NIFTY
# because nse_calendar.yaml wrongly lists 2026-05-27 as a holiday. Everything fetched is
# now stored; anomalies are recorded for a later, separate cleaning task.
SUSPECT_IN_HOURS_RATIO = 0.95

# Windows published together as one warehouse version. Publishing per window rewrites
# the whole manifest each time, which is quadratic in partition count: measured on the
# real run at 475 bytes per entry, 137,423 partitions would mean a 65 MB manifest
# rewritten 137,423 times - roughly 4.5 TB of writes - with throughput already down to
# 0.30 windows/sec and still falling. Nothing in a batch is checkpointed until the
# batch is published, so a crash re-fetches at most one batch.
PUBLISH_BATCH_SIZE = 250

# Rough upper bound on the disk one window can add, used for write admission.
WINDOW_WRITE_HEADROOM_BYTES = 256 * 1024 * 1024


class BudgetExhausted(RuntimeError):
    """Raised when the per-day API budget is spent and the run should stop cleanly."""


@dataclass
class RunStats:
    """Outcome of a single drain pass."""

    windows_attempted: int = 0
    windows_completed: int = 0
    windows_empty: int = 0
    windows_failed: int = 0
    bars_written: int = 0
    stopped_reason: str = "drained"

    def as_dict(self) -> dict[str, Any]:
        return {
            "windows_attempted": self.windows_attempted,
            "windows_completed": self.windows_completed,
            "windows_empty": self.windows_empty,
            "windows_failed": self.windows_failed,
            "bars_written": self.bars_written,
            "stopped_reason": self.stopped_reason,
        }


class BackfillRunner:
    """Drains the backfill queue, one window per iteration."""

    def __init__(
        self,
        engine: Engine,
        client: DhanRestClient | None = None,
        data_root: Path | str | None = None,
        *,
        max_attempts: int = 5,
        auto_renew_token: bool = True,
        calendar: TradingCalendar | None = None,
        publish_batch_size: int = PUBLISH_BATCH_SIZE,
    ) -> None:
        self.engine = engine
        self.client = client or DhanRestClient()
        self.data_root = paths.resolve_data_root(data_root)
        self.max_attempts = max_attempts
        self.auto_renew_token = auto_renew_token
        self.calendar = calendar or TradingCalendar()
        self.publish_batch_size = publish_batch_size
        # Windows fetched and staged but not yet published, and therefore not yet
        # checkpointed. Losing these to a crash costs a re-fetch, never wrong data.
        self._pending: list[tuple[ClaimedWindow, int, Any, str | None, dict[str, Any]]] = []
        self._batch_version: str | None = None
        # Outcome of the most recent run_once, so drain() can report real totals.
        self.last_outcome: str = "none"
        self.last_rows: int = 0
        self.last_quality: dict[str, Any] = {}
        # One publisher shared with every manager, so an open batch captures their
        # publishes instead of each one rewriting the manifest.
        self.publisher = WarehousePublisher(self.data_root)
        self.publisher.ensure_data_root()

    # ---------------------------------------------------------------- driving

    def run_once(self, datasets: list[str] | None = None, flush_after: bool = True) -> bool:
        """Process exactly one window. Returns False when there is nothing to do.

        Publishes and checkpoints before returning unless ``flush_after`` is False,
        which drain() uses to batch many windows into one warehouse version. A single
        call is durable on return, so callers do not have to know about batching.
        """
        window = claim_next_window(self.engine, datasets=datasets, max_attempts=self.max_attempts)
        if window is None:
            return False

        self._open_batch_if_needed()

        try:
            check_write_admission(self.data_root, WINDOW_WRITE_HEADROOM_BYTES)
        except DataRootCapacityError:
            release_window(self.engine, window.job_id, window.window_start)
            raise

        try:
            payload, rows, span = self._fetch_and_publish(window)
        except DhanAuthenticationError as err:
            # Do not consume an attempt: the window is fine, the credentials are not.
            release_window(self.engine, window.job_id, window.window_start)
            self._handle_auth_failure(err)
            raise
        except DhanRateLimitError as err:
            release_window(self.engine, window.job_id, window.window_start)
            raise BudgetExhausted(str(err)) from err
        except DhanClientError as err:
            # A malformed request will fail identically forever; retiring it immediately
            # keeps the queue moving instead of burning five attempts on it.
            self.last_outcome = "failed"
            logger.warning(
                "Window %s %s is not retryable: %s", window.job_id, window.window_start, err
            )
            fail_window(
                self.engine,
                window.job_id,
                window.window_start,
                str(err),
                max_attempts=0,
            )
            return True
        except (DhanError, OSError, ValueError) as err:
            self.last_outcome = "failed"
            logger.warning("Window %s %s failed: %s", window.job_id, window.window_start, err)
            fail_window(
                self.engine,
                window.job_id,
                window.window_start,
                str(err),
                max_attempts=self.max_attempts,
            )
            return True

        self.last_outcome = "completed" if rows else "empty"
        self.last_rows = rows
        self._pending.append((window, rows, span, payload, self.last_quality))
        if flush_after or len(self._pending) >= self.publish_batch_size:
            self.flush()
        return True

    def flush(self) -> None:
        """Publish the open batch, then checkpoint every window it contained.

        Ordering matters: the data has to be durably published before its windows are
        marked done, otherwise a crash between the two would leave the ledger claiming
        months that are not in the warehouse.
        """
        if not self._pending:
            self._close_batch()
            return

        try:
            self.publisher.flush_batch(reason="backfill_batch")
        except OSError, RuntimeError, ValueError:
            # Nothing was checkpointed, so every window in the batch stays claimable.
            logger.exception("Batch publish failed; releasing %d window(s)", len(self._pending))
            for window, _rows, _span, _ingest, _quality in self._pending:
                release_window(self.engine, window.job_id, window.window_start)
            self._pending = []
            self._batch_version = None
            return

        for window, rows, span, ingest_id, quality in self._pending:
            complete_window(
                self.engine,
                window.job_id,
                window.window_start,
                rows=rows,
                raw_ingest_id=ingest_id,
                quality=quality,
                span=span,
            )
            if rows and span is not None:
                upsert_coverage(
                    self.engine,
                    dataset=window.dataset,
                    exchange_segment=window.exchange_segment,
                    symbol=window.symbol,
                    interval=window.interval,
                    security_id=window.security_id,
                    underlying_symbol=window.underlying_symbol,
                    min_ts=span[0],
                    max_ts=span[1],
                    rows=rows,
                )
        logger.info("Published batch of %d window(s)", len(self._pending))
        self._pending = []
        self._batch_version = None

    def _open_batch_if_needed(self) -> None:
        """Start a warehouse version for the batch about to be accumulated."""
        if self._batch_version is None:
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            self._batch_version = f"wv-batch-{stamp}-{uuid.uuid4().hex[:8]}"
            self.publisher.begin_batch(self._batch_version)

    def _close_batch(self) -> None:
        self.publisher.abandon_batch()
        self._batch_version = None

    def drain(
        self,
        max_windows: int | None = None,
        datasets: list[str] | None = None,
        should_continue: Callable[[], bool] | None = None,
    ) -> RunStats:
        """Process windows until the queue empties, a limit is hit, or budget runs out."""
        stats = RunStats()
        reclaim_stale_leases(self.engine)

        while max_windows is None or stats.windows_attempted < max_windows:
            if should_continue is not None and not should_continue():
                stats.stopped_reason = "cancelled"
                self.flush()
                return stats

            try:
                progressed = self.run_once(datasets=datasets, flush_after=False)
            except BudgetExhausted:
                stats.stopped_reason = "budget_exhausted"
                self.flush()
                return stats
            except DhanAuthenticationError:
                stats.stopped_reason = "paused_auth"
                self.flush()
                return stats
            except DataRootCapacityError:
                stats.stopped_reason = "disk_full"
                self.flush()
                return stats

            if not progressed:
                stats.stopped_reason = "drained"
                self.flush()
                return stats

            stats.windows_attempted += 1
            if self.last_outcome == "completed":
                stats.windows_completed += 1
                stats.bars_written += self.last_rows
            elif self.last_outcome == "empty":
                stats.windows_empty += 1
            elif self.last_outcome == "failed":
                stats.windows_failed += 1

        stats.stopped_reason = "max_windows"
        self.flush()
        return stats

    # ---------------------------------------------------------------- fetching

    def _fetch_and_publish(
        self, window: ClaimedWindow
    ) -> tuple[str | None, int, tuple[datetime, datetime] | None]:
        """Fetch one window, persist the raw payload, and publish parsed bars."""
        if window.dataset in OPTION_DATASETS:
            return self._fetch_options(window)
        if window.dataset in DAILY_DATASETS:
            return self._fetch_daily(window)
        return self._fetch_intraday(window)

    def _fetch_daily(
        self, window: ClaimedWindow
    ) -> tuple[str | None, int, tuple[datetime, datetime] | None]:
        instrument = window.instrument_type or "EQUITY"
        data = self.client.get_historical_daily(
            security_id=window.security_id,
            exchange_segment=window.exchange_segment,
            instrument_type=instrument,
            from_date=window.window_start.isoformat(),
            to_date=window.window_end.isoformat(),
            include_open_interest=_wants_open_interest(window.exchange_segment),
        )
        payload = _canonical_bar_payload(data)
        ingest_id, _ = save_raw_ingest(
            self.data_root,
            json.dumps(payload).encode("utf-8"),
            self._raw_params(window),
        )

        bars = data.to_bars()
        if not bars:
            return ingest_id, 0, None
        self.last_quality = self.assess_window(window, bars)

        task = DailyBackfillTask(
            symbol=window.symbol,
            security_id=window.security_id,
            exchange_segment=window.exchange_segment,
            instrument_type=instrument,
            from_date=window.window_start,
            to_date=window.window_end,
        )
        DailyBackfillManager(
            self.data_root, publisher=self.publisher
        ).execute_backfill_from_payloads([(task, payload)], warehouse_version=self._batch_version)
        return ingest_id, len(bars), _span(bars)

    def _fetch_intraday(
        self, window: ClaimedWindow
    ) -> tuple[str | None, int, tuple[datetime, datetime] | None]:
        instrument = window.instrument_type or "EQUITY"
        data = self.client.get_historical_intraday(
            security_id=window.security_id,
            exchange_segment=window.exchange_segment,
            instrument_type=instrument,
            from_date=window.window_start.isoformat(),
            to_date=window.window_end.isoformat(),
            interval=int(window.interval) if window.interval.isdigit() else 1,
            include_open_interest=_wants_open_interest(window.exchange_segment),
        )
        payload = _canonical_bar_payload(data)
        ingest_id, _ = save_raw_minute_ingest(
            self.data_root,
            json.dumps(payload).encode("utf-8"),
            self._raw_params(window),
        )

        bars = data.to_bars()
        if not bars:
            return ingest_id, 0, None
        self.last_quality = self.assess_window(window, bars)

        task = MinuteBackfillTask(
            symbol=window.symbol,
            security_id=window.security_id,
            exchange_segment=window.exchange_segment,
            instrument_type=instrument,
            start_date=window.window_start,
            end_date=window.window_end,
        )
        MinuteBackfillManager(
            self.data_root, publisher=self.publisher
        ).execute_minute_backfill_from_payloads(
            [(task, (window.window_start, window.window_end), payload)],
            warehouse_version=self._batch_version,
        )
        return ingest_id, len(bars), _span(bars)

    def _fetch_options(
        self, window: ClaimedWindow
    ) -> tuple[str | None, int, tuple[datetime, datetime] | None]:
        """Fetch one ATM-relative strike for one expiry and publish both legs."""
        offset = window.strike_offset or 0
        is_index = (window.instrument_type or "OPTIDX").upper() == "OPTIDX"
        self._guard_strike_offset(window.symbol, offset, is_index=is_index)

        # One leg per call: drvOptionType is required and only that leg is returned.
        option_type = (window.option_type or "CALL").upper()
        strike_label = "ATM" if offset == 0 else f"ATM{offset:+d}"
        data = self.client.get_rolling_option_history(
            window.security_id,
            from_date=window.window_start.isoformat(),
            to_date=window.window_end.isoformat(),
            exchange_segment=window.exchange_segment,
            instrument=window.instrument_type or "OPTIDX",
            expiry_flag=window.expiry_flag or "WEEK",
            expiry_code=window.expiry_code or 1,
            strike=strike_label,
            option_type=option_type,
            interval=int(window.interval) if window.interval.isdigit() else 1,
        )

        payload = data.model_dump(by_alias=True)
        ingest_id, _ = save_raw_option_ingest(
            self.data_root,
            json.dumps(payload).encode("utf-8"),
            self._raw_params(window) | {"strike": strike_label, "option_type": option_type},
        )

        leg = data.ce if option_type == "CALL" else data.pe
        total = leg.bar_count()
        if not total:
            # A strike that never traded in this window is a terminal, valid answer.
            return ingest_id, 0, None

        # rollingoption is rolling, so the response carries no expiry date; label the
        # series by the rolling descriptor that actually addressed it.
        expiry_label = f"{(window.expiry_flag or 'WEEK').upper()}-{window.expiry_code or 1}"

        # Exactly the leg that was requested. Iterating both would rebind option_type
        # and could publish one leg's bars under the other leg's identity; it only ever
        # appeared to work because the unrequested leg comes back null.
        strike_price = leg.strike[0] if leg.strike else 0.0
        spot_price = leg.spot[0] if leg.spot else strike_price
        task = OptionsBackfillTask(
            symbol=f"{window.symbol}{expiry_label}{strike_price:g}{option_type[0]}E",
            security_id=window.security_id,
            underlying_symbol=window.underlying_symbol or window.symbol,
            expiry_date=expiry_label,
            strike_price=strike_price,
            option_type=option_type,
            strike_step=_infer_strike_step(strike_price, spot_price, offset),
            is_index=is_index,
            start_date=window.window_start,
            end_date=window.window_end,
        )
        leg_payload = leg.model_dump(by_alias=True)
        leg_payload["oi"] = leg.open_interest
        leg_payload["iv"] = leg.implied_volatility
        OptionsBackfillManager(
            self.data_root, publisher=self.publisher
        ).execute_options_backfill_from_payloads(
            [(task, (window.window_start, window.window_end), spot_price, leg_payload)],
            warehouse_version=self._batch_version,
        )

        timestamps = list(leg.timestamp)
        span = (
            datetime.fromtimestamp(min(timestamps), tz=UTC),
            datetime.fromtimestamp(max(timestamps), tz=UTC),
        )
        return ingest_id, total, span

    def _guard_strike_offset(self, symbol: str, offset: int, *, is_index: bool) -> None:
        """Reject an offset outside the F1.4 coverage band before spending a call.

        With charts/rollingoption the strike is addressed relative to spot, so the
        meaningful check is on the offset we are about to request. Validating the
        returned strike against a step inferred from the same response would be
        circular and would prove nothing.
        """
        limit = INDEX_MAX_STRIKES if is_index else STOCK_MAX_STRIKES
        if abs(offset) > limit:
            raise StrikeUnavailableError(
                symbol=symbol,
                spot_price=0.0,
                requested_strike=float(offset),
                strike_step=1.0,
                max_strikes=limit,
            )

    # ---------------------------------------------------------------- helpers

    def assess_window(self, window: ClaimedWindow, bars: list[Any]) -> dict[str, Any]:
        """Describe what was fetched, without judging whether to keep it.

        Returns metrics the Historic Data Report highlights: how many bars fell inside
        regular market hours, which dates are absent from our calendar, how many bars
        landed on each day, and the observed span. A window can be unusual for entirely
        legitimate reasons - a special session, a shortened day, a moved holiday - so
        this only ever flags, never discards.
        """
        metrics: dict[str, Any] = {
            "bars": len(bars),
            "in_hours": 0,
            "out_of_hours": 0,
            "unexpected_dates": [],
            "distinct_days": 0,
            "max_bars_in_a_day": 0,
            "weekend_days": 0,
            "suspect_reasons": [],
        }
        if window.dataset == "daily" or not bars:
            return metrics

        segment = window.exchange_segment.upper()
        bounds = self.calendar.default_sessions.get(segment) or self.calendar.default_sessions.get(
            "NSE_EQ"
        )

        per_day: Counter[date] = Counter()
        unexpected: set[date] = set()
        weekend: set[date] = set()
        in_hours = 0

        for bar in bars:
            stamp_ist = to_ist(datetime.fromtimestamp(bar.timestamp, tz=UTC))
            day = stamp_ist.date()
            per_day[day] += 1
            if bounds is not None and bounds.start <= stamp_ist.time() <= bounds.end:
                in_hours += 1
            if stamp_ist.weekday() >= 5:
                weekend.add(day)
            if not self.calendar.is_trading_day(day, segment=segment):
                unexpected.add(day)

        metrics["in_hours"] = in_hours
        metrics["out_of_hours"] = len(bars) - in_hours
        metrics["unexpected_dates"] = [d.isoformat() for d in sorted(unexpected)]
        metrics["weekend_days"] = len(weekend)
        metrics["distinct_days"] = len(per_day)
        metrics["max_bars_in_a_day"] = max(per_day.values()) if per_day else 0

        reasons: list[str] = []
        if in_hours < len(bars) * SUSPECT_IN_HOURS_RATIO:
            share = in_hours / len(bars) if bars else 0.0
            reasons.append(f"only {share:.0%} of bars inside regular market hours")
        if weekend:
            reasons.append(f"{len(weekend)} weekend day(s) present")
        if unexpected:
            reasons.append(f"{len(unexpected)} date(s) not in the {segment} calendar")
        metrics["suspect_reasons"] = reasons

        if reasons:
            logger.info(
                "%s %s stored with anomalies: %s",
                window.symbol,
                window.window_start,
                "; ".join(reasons),
            )
        return metrics

    def _raw_params(self, window: ClaimedWindow) -> dict[str, Any]:
        return {
            "symbol": window.symbol,
            "security_id": window.security_id,
            "exchange_segment": window.exchange_segment,
            "from_date": window.window_start.isoformat(),
            "to_date": window.window_end.isoformat(),
            "interval": window.interval,
            "dataset": window.dataset,
        }

    def _handle_auth_failure(self, err: DhanAuthenticationError) -> None:
        """Try to renew the token; park every job if that fails.

        Parking is not a loss. Completed windows keep their state, so a refreshed
        token resumes from the exact point the old one died.
        """
        if self.auto_renew_token:
            try:
                self.client.renew_token()
            except DhanError as renew_err:
                logger.error("Dhan token renewal failed: %s", renew_err)
            else:
                logger.info("Dhan token renewed; backfill jobs remain runnable")
                return

        pause_all_for_auth(self.engine, f"authentication failed: {err}")


def _canonical_bar_payload(data: DhanHistoricalData) -> dict[str, Any]:
    """Render a typed chart response into the dict shape the parsers consume.

    Serialising the model directly would emit the Python field name (start_time), which
    none of the parsers look for, so every bar would be silently dropped. Building the
    payload explicitly keeps that contract visible instead of implicit in alias config.
    """
    return {
        "open": list(data.open),
        "high": list(data.high),
        "low": list(data.low),
        "close": list(data.close),
        "volume": list(data.volume),
        "open_interest": list(data.open_interest),
        "start_Time": list(data.start_time),
    }


def _infer_strike_step(strike_price: float, spot_price: float, offset: int) -> float:
    """Derive the chain's strike step from an addressed offset.

    Only used to populate provenance on the published partition. It is never the
    coverage guard - that runs on the requested offset in _guard_strike_offset.
    """
    if offset == 0:
        return 1.0
    step = abs(strike_price - spot_price) / abs(offset)
    return step if step > 0 else 1.0


def _wants_open_interest(exchange_segment: str) -> bool:
    """Open interest exists only for derivatives segments."""
    return exchange_segment.upper().endswith("_FNO") or exchange_segment.upper() == "MCX_COMM"


def _span(bars: list[Any]) -> tuple[datetime, datetime]:
    """Return the (min, max) UTC timestamps covered by a list of parsed bars."""
    stamps = [datetime.fromtimestamp(b.timestamp, tz=UTC) for b in bars]
    return min(stamps), max(stamps)
