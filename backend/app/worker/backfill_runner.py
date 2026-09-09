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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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
from app.marketdata.calendar import TradingCalendar
from app.warehouse import paths
from app.warehouse.paths import DataRootCapacityError, check_write_admission
from app.warehouse.publisher import WarehousePublisher
from app.worker.backfill_queue import (
    ClaimedWindow,
    claim_next_window,
    complete_window,
    fail_window,
    pause_all_for_auth,
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

# Share of a window's bars that must land inside a real trading session for the
# window to be trusted. Dhan's archive for some thinly-followed indices returns bars
# on Saturdays and across a ten-hour span; storing those would silently corrupt any
# back-test that used them. Set below 1.0 because a handful of boundary bars around
# special sessions are normal.
MIN_IN_SESSION_RATIO = 0.95

# Rough upper bound on the disk one window can add, used for write admission.
WINDOW_WRITE_HEADROOM_BYTES = 256 * 1024 * 1024


class OutOfSessionData(ValueError):
    """Raised when a fetched window is mostly outside any real trading session."""

    def __init__(self, symbol: str, in_session: int, total: int) -> None:
        self.symbol = symbol
        self.in_session = in_session
        self.total = total
        ratio = in_session / total if total else 0.0
        super().__init__(
            f"{symbol}: only {in_session}/{total} bars ({ratio:.1%}) fall inside a "
            f"trading session; refusing to publish likely-corrupt upstream history"
        )


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
    ) -> None:
        self.engine = engine
        self.client = client or DhanRestClient()
        self.data_root = paths.resolve_data_root(data_root)
        self.max_attempts = max_attempts
        self.auto_renew_token = auto_renew_token
        self.calendar = calendar or TradingCalendar()
        # Outcome of the most recent run_once, so drain() can report real totals.
        self.last_outcome: str = "none"
        self.last_rows: int = 0
        # The managers stage into staging/ and warehouse/; a first run against a fresh
        # data root would otherwise fail with a missing staging directory.
        WarehousePublisher(self.data_root).ensure_data_root()

    # ---------------------------------------------------------------- driving

    def run_once(self, datasets: list[str] | None = None) -> bool:
        """Process exactly one window. Returns False when there is nothing to do."""
        window = claim_next_window(self.engine, datasets=datasets, max_attempts=self.max_attempts)
        if window is None:
            return False

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
        except OutOfSessionData as err:
            self.last_outcome = "failed"
            logger.warning("Quarantining window: %s", err)
            fail_window(
                self.engine,
                window.job_id,
                window.window_start,
                str(err),
                max_attempts=0,
            )
            return True
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
        complete_window(
            self.engine,
            window.job_id,
            window.window_start,
            rows=rows,
            raw_ingest_id=payload,
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
        return True

    def drain(
        self,
        max_windows: int | None = None,
        datasets: list[str] | None = None,
        should_continue: Callable[[], bool] | None = None,
    ) -> RunStats:
        """Process windows until the queue empties, a limit is hit, or budget runs out."""
        stats = RunStats()

        while max_windows is None or stats.windows_attempted < max_windows:
            if should_continue is not None and not should_continue():
                stats.stopped_reason = "cancelled"
                return stats

            try:
                progressed = self.run_once(datasets=datasets)
            except BudgetExhausted:
                stats.stopped_reason = "budget_exhausted"
                return stats
            except DhanAuthenticationError:
                stats.stopped_reason = "paused_auth"
                return stats
            except DataRootCapacityError:
                stats.stopped_reason = "disk_full"
                return stats

            if not progressed:
                stats.stopped_reason = "drained"
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
        self._assert_in_session(window, bars)

        task = DailyBackfillTask(
            symbol=window.symbol,
            security_id=window.security_id,
            exchange_segment=window.exchange_segment,
            instrument_type=instrument,
            from_date=window.window_start,
            to_date=window.window_end,
        )
        DailyBackfillManager(self.data_root).execute_backfill_from_payloads([(task, payload)])
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
        self._assert_in_session(window, bars)

        task = MinuteBackfillTask(
            symbol=window.symbol,
            security_id=window.security_id,
            exchange_segment=window.exchange_segment,
            instrument_type=instrument,
            start_date=window.window_start,
            end_date=window.window_end,
        )
        MinuteBackfillManager(self.data_root).execute_minute_backfill_from_payloads(
            [(task, (window.window_start, window.window_end), payload)]
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

        batch = []
        for option_type, leg in (("CALL", data.ce), ("PUT", data.pe)):
            if leg.bar_count() == 0:
                continue
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
            batch.append((task, (window.window_start, window.window_end), spot_price, leg_payload))

        if batch:
            OptionsBackfillManager(self.data_root).execute_options_backfill_from_payloads(batch)

        timestamps = [*data.ce.timestamp, *data.pe.timestamp]
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

    def _assert_in_session(self, window: ClaimedWindow, bars: list[Any]) -> None:
        """Refuse a window whose bars mostly sit outside a real trading session.

        Daily bars are stamped at IST midnight rather than inside the session, so the
        check applies to intraday series only.
        """
        if window.dataset == "daily" or not bars:
            return

        segment = window.exchange_segment.upper()
        in_session = 0
        for bar in bars:
            stamp = datetime.fromtimestamp(bar.timestamp, tz=UTC)
            if self.calendar.validate_bar_session(stamp, segment=segment):
                in_session += 1

        if in_session < len(bars) * MIN_IN_SESSION_RATIO:
            raise OutOfSessionData(window.symbol, in_session, len(bars))

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
