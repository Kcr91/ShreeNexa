"""Dhan market-data ingestion owned exclusively by the ``feedd`` process."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import time as clock_time
from typing import Any
from zoneinfo import ZoneInfo

import websockets

from app.config import mask_client_id
from app.dhan.client import DhanRestClient
from app.dhan.credentials import resolve_dhan_credentials
from app.dhan.feed import DhanLiveFeedClient
from app.dhan.packets import DisconnectPacket
from app.feedd.cache import (
    CachedFeedHealth,
    CachedQuote,
    HotCache,
    MarketDataState,
    RedisHotCache,
)

logger = logging.getLogger("shreenexa.dhan.live_feed")

MAX_INSTRUMENTS_PER_MESSAGE = 100
MAX_INSTRUMENTS_PER_SOCKET = 5000
MAX_INSTRUMENTS_PER_QUOTE_REQUEST = 1000
QUOTE_REQUEST_CODE = 17
UNSUBSCRIBE_REQUEST_CODE = 18
IST = ZoneInfo("Asia/Kolkata")

# Reconnect pacing. Dhan blocks a client ID/IP that reconnects too aggressively
# (HTTP 429 "client id is blocked"), and it accepts the handshake before rejecting
# a bad token, so a successful handshake alone must never reset the backoff.
INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 120.0
STABLE_CONNECTION_SECONDS = 60.0
RATE_LIMITED_BACKOFF_SECONDS = 300.0
CREDENTIAL_POLL_SECONDS = 30.0
CONNECTION_LIMIT_DISCONNECT_CODE = 805
# 806 data APIs not subscribed, 807 token expired, 808 auth failed,
# 809 token invalid, 810 client ID invalid: retrying the same token cannot succeed.
CREDENTIAL_DISCONNECT_CODES = frozenset({806, 807, 808, 809, 810})

SEGMENT_TO_DHAN = {
    "0": "IDX_I",
    "1": "NSE_EQ",
    "2": "NSE_FNO",
    "3": "NSE_CURRENCY",
    "4": "BSE_EQ",
    "5": "MCX_COMM",
    "7": "BSE_CURRENCY",
    "8": "BSE_FNO",
    "IDX_I": "IDX_I",
    "NSE_EQ": "NSE_EQ",
    "NSE_FNO": "NSE_FNO",
    "NSE_CURRENCY": "NSE_CURRENCY",
    "BSE_EQ": "BSE_EQ",
    "MCX_COMM": "MCX_COMM",
    "BSE_CURRENCY": "BSE_CURRENCY",
    "BSE_FNO": "BSE_FNO",
}
DHAN_TO_SEGMENT = {
    "IDX_I": "0",
    "NSE_EQ": "1",
    "NSE_FNO": "2",
    "NSE_CURRENCY": "3",
    "BSE_EQ": "4",
    "MCX_COMM": "5",
    "BSE_CURRENCY": "7",
    "BSE_FNO": "8",
}

_SEGMENT_INSTRUMENT_TYPE: dict[str, tuple[str, str]] = {
    "0": ("IDX_I", "INDEX"),
    "1": ("NSE_EQ", "EQUITY"),
    "2": ("NSE_FNO", "FUTIDX"),
    "3": ("NSE_CURRENCY", "FUTCUR"),
    "4": ("BSE_EQ", "EQUITY"),
    "5": ("MCX_COMM", "COMMODITY"),
    "7": ("BSE_CURRENCY", "FUTCUR"),
    "8": ("BSE_FNO", "FUTIDX"),
    "IDX_I": ("IDX_I", "INDEX"),
    "NSE_EQ": ("NSE_EQ", "EQUITY"),
    "NSE_FNO": ("NSE_FNO", "FUTIDX"),
    "NSE_CURRENCY": ("NSE_CURRENCY", "FUTCUR"),
    "BSE_EQ": ("BSE_EQ", "EQUITY"),
    "MCX_COMM": ("MCX_COMM", "COMMODITY"),
    "BSE_CURRENCY": ("BSE_CURRENCY", "FUTCUR"),
    "BSE_FNO": ("BSE_FNO", "FUTIDX"),
}


def market_is_open(now: datetime | None = None, segment: str = "0") -> bool:
    """Return the regular segment session window without guessing holiday truth."""
    current = (now or datetime.now(tz=IST)).astimezone(IST)
    if current.weekday() >= 5:
        return False
    session_bounds = {
        "3": (clock_time(9, 0), clock_time(17, 0)),
        "5": (clock_time(9, 0), clock_time(23, 30)),
        "7": (clock_time(9, 0), clock_time(17, 0)),
    }
    start, end = session_bounds.get(segment, (clock_time(9, 15), clock_time(15, 30)))
    return start <= current.time().replace(tzinfo=None) <= end


def _market_state_for_trade_time(
    trade_time: int | str | None,
    *,
    segment: str,
    now: datetime | None = None,
) -> MarketDataState:
    """Classify a Dhan quote from its direct LTT plus the regular session window."""
    current = (now or datetime.now(tz=IST)).astimezone(IST)
    traded_at: datetime | None = None
    if isinstance(trade_time, int) and trade_time > 0:
        try:
            traded_at = datetime.fromtimestamp(trade_time, tz=UTC).astimezone(IST)
        except OSError, OverflowError, ValueError:
            traded_at = None
    elif isinstance(trade_time, str):
        try:
            traded_at = datetime.strptime(trade_time, "%d/%m/%Y %H:%M:%S").replace(tzinfo=IST)
        except ValueError:
            traded_at = None

    if traded_at is None:
        return "STALE" if market_is_open(current, segment) else "MARKET_CLOSED"
    if traded_at.date() != current.date():
        return "MARKET_CLOSED"
    if abs((current - traded_at).total_seconds()) <= 300:
        return "LIVE"
    return "LIVE" if market_is_open(current, segment) else "MARKET_CLOSED"


def _wire_instruments(instruments: set[tuple[str, str]]) -> list[dict[str, str]]:
    wire: list[dict[str, str]] = []
    for segment, security_id in sorted(instruments):
        dhan_segment = SEGMENT_TO_DHAN.get(segment)
        if dhan_segment == "BSE_EQ" or segment in ("4", "BSE_EQ", "BSE"):
            dhan_segment = "NSE_EQ"
        if dhan_segment:
            wire.append({"ExchangeSegment": dhan_segment, "SecurityId": security_id})
    return wire


def _chunks(items: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    return [
        items[index : index + MAX_INSTRUMENTS_PER_MESSAGE]
        for index in range(0, len(items), MAX_INSTRUMENTS_PER_MESSAGE)
    ]


def _quote_request_bodies(
    instruments: set[tuple[str, str]],
) -> list[dict[str, list[int]]]:
    """Build direct-quote request bodies within Dhan's 1000-instrument limit."""
    normalized: list[tuple[str, int]] = []
    for segment, security_id in sorted(instruments):
        dhan_segment = SEGMENT_TO_DHAN.get(segment)
        if dhan_segment == "BSE_EQ" or segment in ("4", "BSE_EQ", "BSE"):
            dhan_segment = "NSE_EQ"
        if dhan_segment is None:
            continue
        try:
            normalized.append((dhan_segment, int(security_id)))
        except ValueError:
            continue

    bodies: list[dict[str, list[int]]] = []
    for offset in range(0, len(normalized), MAX_INSTRUMENTS_PER_QUOTE_REQUEST):
        body: dict[str, list[int]] = {}
        for dhan_segment, numeric_id in normalized[
            offset : offset + MAX_INSTRUMENTS_PER_QUOTE_REQUEST
        ]:
            body.setdefault(dhan_segment, []).append(numeric_id)
        if body:
            bodies.append(body)
    return bodies


class DhanFeedRejectedError(Exception):
    """Dhan ended the feed with a documented disconnect reason code."""

    def __init__(self, code: int) -> None:
        super().__init__(f"Dhan disconnected the feed with code {code}")
        self.code = code


def _failure_policy(exc: BaseException) -> tuple[str, float, bool]:
    """Classify a feed failure as (reason, minimum retry delay, credentials rejected).

    The reason never includes the exception text: the feed URL carries the token.
    """
    if isinstance(exc, DhanFeedRejectedError):
        if exc.code in CREDENTIAL_DISCONNECT_CODES:
            return f"Dhan rejected the access token (disconnect code {exc.code})", 0.0, True
        if exc.code == CONNECTION_LIMIT_DISCONNECT_CODE:
            return (
                "Dhan connection limit exceeded (disconnect code 805)",
                RATE_LIMITED_BACKOFF_SECONDS,
                False,
            )
        return f"Dhan disconnected the feed (code {exc.code})", 0.0, False

    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    if status_code == 429:
        return (
            "Dhan is rate-limiting this client ID/IP (HTTP 429)",
            RATE_LIMITED_BACKOFF_SECONDS,
            False,
        )
    if status_code in (401, 403):
        return f"Dhan rejected the access token (HTTP {status_code})", 0.0, True
    if status_code is not None:
        return f"Dhan feed handshake failed (HTTP {status_code})", 0.0, False

    close = getattr(exc, "rcvd", None)
    if close is not None:
        return f"Dhan closed the feed (close code {close.code})", 0.0, False
    return f"Dhan feed disconnected ({type(exc).__name__})", 0.0, False


@dataclass(frozen=True)
class HistoricalMetrics:
    previous_close: float
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    volume: int | None = None


class DhanLiveFeedService:
    """Maintains dynamic Dhan subscriptions and publishes normalized Redis state."""

    def __init__(self, hot_cache: HotCache | None = None) -> None:
        self.hot_cache = hot_cache or RedisHotCache()
        self.is_running = False
        self.total_packets = 0
        self._stop_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._active: set[tuple[str, str]] = set()
        self._reconnect_count = 0
        self._last_packet_time: str | None = None
        self._last_rest_sync = 0.0
        self._last_error: str | None = None
        self._rejected_token: str | None = None

    async def _wait(self, seconds: float) -> bool:
        """Sleep unless stopped; return True when the service should exit."""
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except TimeoutError:
            return False
        return True

    def _set_idle_error(self, reason: str) -> None:
        """Publish why the feed is not connecting, logging each distinct reason once."""
        if reason != self._last_error:
            logger.error(reason)
            self._last_error = reason
        self._health(connected=False)

    def _health(self, *, connected: bool) -> None:
        self.hot_cache.update_feed_health(
            CachedFeedHealth(
                socket_id="dhan-market-feed-1",
                is_connected=connected,
                subscribed_count=len(self._active),
                reconnect_count=self._reconnect_count,
                total_packets=self.total_packets,
                last_packet_time=self._last_packet_time,
                last_error=self._last_error,
                updated_at=time.time(),
            )
        )

    async def _send_subscription_change(
        self,
        ws: Any,
        instruments: set[tuple[str, str]],
        *,
        unsubscribe: bool = False,
    ) -> None:
        for chunk in _chunks(_wire_instruments(instruments)):
            if not chunk:
                continue
            await ws.send(
                json.dumps(
                    {
                        "RequestCode": UNSUBSCRIBE_REQUEST_CODE
                        if unsubscribe
                        else QUOTE_REQUEST_CODE,
                        "InstrumentCount": len(chunk),
                        "InstrumentList": chunk,
                    }
                )
            )

    async def _resolve_historical_metrics(
        self, client: DhanRestClient, segment: str, security_id: str
    ) -> HistoricalMetrics | None:
        """Fetch exact previous daily close, 52w high/low, and volume from Dhan daily bars."""
        norm_seg = "1" if str(segment) in ("4", "BSE_EQ", "BSE") else str(segment)
        exch_seg, inst_type = _SEGMENT_INSTRUMENT_TYPE.get(norm_seg, ("NSE_EQ", "EQUITY"))
        today = datetime.now(IST).date()
        from_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
        try:
            data = await asyncio.to_thread(
                client.get_historical_daily,
                str(security_id),
                exch_seg,
                inst_type,
                from_date,
                to_date,
            )
            bars = data.to_bars()
            if not bars:
                return None
            last_bar = bars[-1]
            last_bar_date = datetime.fromtimestamp(last_bar.timestamp, IST).date()
            if last_bar_date == today and len(bars) > 1:
                prev_close = bars[-2].close
            else:
                prev_close = last_bar.close

            valid_highs = [b.high for b in bars if b.high > 0]
            valid_lows = [b.low for b in bars if b.low > 0]
            high_52 = round(max(valid_highs), 2) if valid_highs else None
            low_52 = round(min(valid_lows), 2) if valid_lows else None
            vol = (
                last_bar.volume
                if last_bar.volume > 0
                else (bars[-2].volume if len(bars) > 1 and bars[-2].volume > 0 else None)
            )

            return HistoricalMetrics(
                previous_close=prev_close,
                fifty_two_week_high=high_52,
                fifty_two_week_low=low_52,
                volume=vol,
            )
        except Exception as exc:
            logger.debug(
                "Failed to fetch historical daily bars for %s:%s: %s", segment, security_id, exc
            )
            return None

    async def sync_quotes(self, instruments: set[tuple[str, str]]) -> None:
        """Bootstrap requested instruments from Dhan's direct quote endpoint."""
        if not instruments:
            return
        creds = resolve_dhan_credentials()
        if not creds or not creds.access_token or not creds.client_id:
            return

        request_bodies = _quote_request_bodies(instruments)
        if not request_bodies:
            return

        payload: dict[str, Any] = {}
        try:
            client = DhanRestClient(credentials=creds)
            for index, body in enumerate(request_bodies):
                if index > 0:
                    await asyncio.sleep(0.25)
                response_data = await asyncio.to_thread(client.get_quotes, body)
                for segment, quotes in response_data.items():
                    if isinstance(quotes, dict):
                        payload.setdefault(segment, {}).update(quotes)
        except Exception as exc:
            logger.warning("Dhan quote bootstrap failed: %s", type(exc).__name__)
            return

        received_at = time.time()
        redis_client = getattr(self.hot_cache, "_client", None)

        # 1. Parse payload and compute previous_close directly from net_change if non-zero
        parsed_items: list[tuple[str, str, dict[str, Any], float | None]] = []
        needed_metrics: list[tuple[str, str]] = []

        for dhan_segment, segment_quotes in payload.items():
            segment_code = DHAN_TO_SEGMENT.get(str(dhan_segment))
            if segment_code is None or not isinstance(segment_quotes, dict):
                continue
            for security_id, raw in segment_quotes.items():
                if not isinstance(raw, dict):
                    continue
                ltp = _number(raw.get("last_price"))
                net_change = _number(raw.get("net_change"))
                high_52_raw = _number(raw.get("52_week_high"))
                vol_raw = _integer(raw.get("volume"))
                prev_close: float | None = None
                if net_change is not None and net_change != 0.0 and ltp is not None:
                    prev_close = round(ltp - net_change, 2)
                    if redis_client:
                        try:
                            redis_client.set(
                                f"shreenexa:feed:v2:prev_close:{segment_code}:{security_id}",
                                str(prev_close),
                                ex=86400,
                            )
                        except Exception:
                            pass
                parsed_items.append((segment_code, str(security_id), raw, prev_close))
                if (
                    prev_close is None
                    or high_52_raw is None
                    or high_52_raw <= 0
                    or vol_raw is None
                    or vol_raw <= 0
                ):
                    needed_metrics.append((segment_code, str(security_id)))

        # 2. Check Redis cache for instruments where metrics were 0 or missing
        resolved_metrics: dict[tuple[str, str], HistoricalMetrics] = {}
        if needed_metrics and redis_client:
            try:
                pc_keys = [f"shreenexa:feed:v2:prev_close:{s}:{i}" for s, i in needed_metrics]
                h52_keys = [f"shreenexa:feed:v2:52w_high:{s}:{i}" for s, i in needed_metrics]
                l52_keys = [f"shreenexa:feed:v2:52w_low:{s}:{i}" for s, i in needed_metrics]
                vol_keys = [f"shreenexa:feed:v2:vol:{s}:{i}" for s, i in needed_metrics]

                pc_vals = redis_client.mget(pc_keys)
                h52_vals = redis_client.mget(h52_keys)
                l52_vals = redis_client.mget(l52_keys)
                vol_vals = redis_client.mget(vol_keys)

                for idx, (s, i) in enumerate(needed_metrics):
                    pc = pc_vals[idx]
                    h52_v = h52_vals[idx]
                    l52_v = l52_vals[idx]
                    vol_v = vol_vals[idx]
                    if (
                        pc is not None
                        and h52_v is not None
                        and l52_v is not None
                        and vol_v is not None
                    ):
                        try:
                            pc_f = float(pc.decode("utf-8") if isinstance(pc, bytes) else pc)
                            h52_f = float(h52_v)
                            l52_f = float(l52_v)
                            vol_i = int(vol_v)
                            resolved_metrics[(s, i)] = HistoricalMetrics(
                                previous_close=pc_f,
                                fifty_two_week_high=h52_f,
                                fifty_two_week_low=l52_f,
                                volume=vol_i,
                            )
                        except (ValueError, TypeError):
                            pass
            except Exception as exc:
                logger.debug("Redis mget for historical metrics failed: %s", exc)

        # 3. For any still missing, check hot cache or fetch historical bars from API
        still_missing = [(s, i) for s, i in needed_metrics if (s, i) not in resolved_metrics]
        if still_missing:
            fetch_from_api: list[tuple[str, str]] = []
            for s, i in still_missing:
                existing = self.hot_cache.get_quote(s, i)
                if (
                    existing
                    and existing.previous_close is not None
                    and existing.previous_close > 0
                    and (existing.open is None or existing.previous_close != existing.open)
                    and existing.fifty_two_week_high is not None
                    and existing.fifty_two_week_high > 0
                    and existing.volume is not None
                    and existing.volume > 0
                ):
                    resolved_metrics[(s, i)] = HistoricalMetrics(
                        previous_close=existing.previous_close,
                        fifty_two_week_high=existing.fifty_two_week_high,
                        fifty_two_week_low=existing.fifty_two_week_low,
                        volume=existing.volume,
                    )
                else:
                    fetch_from_api.append((s, i))

            if fetch_from_api:
                for s, i in fetch_from_api:
                    metrics = await self._resolve_historical_metrics(client, s, i)
                    if metrics is not None:
                        resolved_metrics[(s, i)] = metrics
                        if redis_client:
                            try:
                                redis_client.set(
                                    f"shreenexa:feed:v2:prev_close:{s}:{i}",
                                    str(metrics.previous_close),
                                    ex=86400,
                                )
                                if metrics.fifty_two_week_high is not None:
                                    redis_client.set(
                                        f"shreenexa:feed:v2:52w_high:{s}:{i}",
                                        str(metrics.fifty_two_week_high),
                                        ex=86400,
                                    )
                                if metrics.fifty_two_week_low is not None:
                                    redis_client.set(
                                        f"shreenexa:feed:v2:52w_low:{s}:{i}",
                                        str(metrics.fifty_two_week_low),
                                        ex=86400,
                                    )
                                if metrics.volume is not None:
                                    redis_client.set(
                                        f"shreenexa:feed:v2:vol:{s}:{i}",
                                        str(metrics.volume),
                                        ex=86400,
                                    )
                            except Exception:
                                pass
                    await asyncio.sleep(0.15)

        # 4. Construct and save CachedQuotes
        for segment_code, security_id, raw, prev_close in parsed_items:
            ltp = _number(raw.get("last_price"))
            raw_ohlc = raw.get("ohlc")
            ohlc: dict[str, Any] = raw_ohlc if isinstance(raw_ohlc, dict) else {}
            open_price = _number(ohlc.get("open"))
            inst_key = (segment_code, security_id)
            metrics = resolved_metrics.get(inst_key)

            final_prev_close = (
                prev_close
                if (prev_close is not None and prev_close > 0)
                else (metrics.previous_close if metrics else None)
            )
            if final_prev_close is None:
                final_prev_close = open_price if open_price is not None and open_price > 0 else ltp

            fifty_two_week_high = _number(raw.get("52_week_high"))
            if (fifty_two_week_high is None or fifty_two_week_high <= 0) and metrics:
                fifty_two_week_high = metrics.fifty_two_week_high

            fifty_two_week_low = _number(raw.get("52_week_low"))
            if (fifty_two_week_low is None or fifty_two_week_low <= 0) and metrics:
                fifty_two_week_low = metrics.fifty_two_week_low

            vol_val = _integer(raw.get("volume"))
            if (vol_val is None or vol_val <= 0) and metrics and metrics.volume:
                vol_val = metrics.volume

            trade_time = _trade_time(raw.get("last_trade_time"))

            self.hot_cache.set_quote(
                CachedQuote(
                    segment=segment_code,
                    security_id=security_id,
                    ltp=ltp,
                    ltq=_integer(raw.get("last_quantity")),
                    ltt=trade_time,
                    avg_price=_number(raw.get("average_price")),
                    volume=vol_val,
                    total_buy_qty=_number(raw.get("buy_quantity")),
                    total_sell_qty=_number(raw.get("sell_quantity")),
                    open=open_price,
                    high=_number(ohlc.get("high")),
                    low=_number(ohlc.get("low")),
                    close=_number(ohlc.get("close")),
                    previous_close=final_prev_close,
                    fifty_two_week_high=fifty_two_week_high,
                    fifty_two_week_low=fifty_two_week_low,
                    received_at=received_at,
                    source="DHAN_REST",
                    market_state=_market_state_for_trade_time(trade_time, segment=segment_code),
                )
            )
        self._last_rest_sync = received_at

    async def _reconcile_subscriptions(self, ws: Any) -> None:
        desired = self.hot_cache.get_requested_subscriptions()
        if len(desired) > MAX_INSTRUMENTS_PER_SOCKET:
            logger.error("Requested Dhan subscriptions exceed the 5000-instrument socket limit")
            desired = set(sorted(desired)[:MAX_INSTRUMENTS_PER_SOCKET])
        additions = desired - self._active
        removals = self._active - desired
        if additions:
            await self.sync_quotes(additions)
            await self._send_subscription_change(ws, additions)
        if removals:
            await self._send_subscription_change(ws, removals, unsubscribe=True)
        self._active = desired
        if desired and not market_is_open() and time.time() - self._last_rest_sync > 300.0:
            await self.sync_quotes(desired)
        self._health(connected=True)

    async def run(self) -> None:
        """Connect, reconcile demand, decode packets, and update Redis."""
        self._loop = asyncio.get_running_loop()
        self.is_running = True
        self._stop_event.clear()
        backoff = INITIAL_BACKOFF_SECONDS
        try:
            while not self._stop_event.is_set():
                creds = resolve_dhan_credentials()
                if not creds or not creds.access_token or not creds.client_id:
                    self._set_idle_error("Dhan credentials are not configured")
                    if await self._wait(CREDENTIAL_POLL_SECONDS):
                        break
                    continue

                token = creds.access_token.get_secret_value()
                fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()
                if creds.expires_at is not None and creds.expires_at <= datetime.now(tz=UTC):
                    # Connecting with an expired token is rejected after the handshake;
                    # repeating that gets the client ID/IP blocked by Dhan.
                    self._set_idle_error(
                        f"Dhan access token expired at {creds.expires_at.isoformat()}; "
                        "store a new token with 'python -m app.dhan.token set'"
                    )
                    if await self._wait(CREDENTIAL_POLL_SECONDS):
                        break
                    continue
                if fingerprint == self._rejected_token:
                    self._health(connected=False)
                    if await self._wait(CREDENTIAL_POLL_SECONDS):
                        break
                    continue

                url = (
                    "wss://api-feed.dhan.co?version=2"
                    f"&token={token}&clientId={creds.client_id}&authType=2"
                )
                logger.info("Connecting Dhan feed for client %s", mask_client_id(creds.client_id))
                client = DhanLiveFeedClient(client_id=creds.client_id, access_token=token)
                self._active.clear()
                connected_at: float | None = None
                try:
                    async with websockets.connect(
                        url, ping_interval=10, ping_timeout=20, close_timeout=5
                    ) as ws:
                        connected_at = time.monotonic()
                        self._last_error = None
                        await self._reconcile_subscriptions(ws)
                        while not self._stop_event.is_set():
                            await self._reconcile_subscriptions(ws)
                            try:
                                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            except TimeoutError:
                                continue
                            if not isinstance(message, bytes):
                                continue
                            packets = client.process_incoming_frame(message)
                            for packet in packets:
                                if isinstance(packet, DisconnectPacket):
                                    raise DhanFeedRejectedError(packet.disconnect_code)
                            self.hot_cache.batch_update_packets(packets)
                            for packet in packets:
                                quote = self.hot_cache.get_quote(
                                    str(packet.header.exchange_segment),
                                    str(packet.header.security_id),
                                )
                                state = (
                                    _market_state_for_trade_time(
                                        quote.ltt,
                                        segment=str(packet.header.exchange_segment),
                                    )
                                    if quote is not None
                                    else "UNAVAILABLE"
                                )
                                if quote is not None and quote.market_state != state:
                                    self.hot_cache.set_quote(
                                        quote.model_copy(update={"market_state": state})
                                    )
                            self.total_packets += len(packets)
                            if packets:
                                self._last_packet_time = datetime.now(tz=IST).isoformat()
                                self._health(connected=True)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    reason, minimum_delay, credentials_rejected = _failure_policy(exc)
                    if (
                        connected_at is not None
                        and time.monotonic() - connected_at >= STABLE_CONNECTION_SECONDS
                    ):
                        backoff = INITIAL_BACKOFF_SECONDS
                    self._reconnect_count += 1
                    self._last_error = reason
                    self._health(connected=False)
                    if credentials_rejected:
                        self._rejected_token = fingerprint
                        logger.error("%s; waiting for a new token before reconnecting", reason)
                        continue
                    delay = max(backoff, minimum_delay)
                    logger.warning("%s; retrying in %.0fs", reason, delay)
                    if await self._wait(delay):
                        break
                    backoff = min(backoff * 2.0, MAX_BACKOFF_SECONDS)
        finally:
            self.is_running = False
            self._health(connected=False)

    def stop(self) -> None:
        """Signal the feed loop from the feedd process's main thread."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._stop_event.set)
        else:
            self._stop_event.set()


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _trade_time(value: Any) -> int | str | None:
    if isinstance(value, str):
        return value.strip() or None
    return _integer(value)


_GLOBAL_FEED_SERVICE: DhanLiveFeedService | None = None


def get_dhan_live_feed_service() -> DhanLiveFeedService:
    global _GLOBAL_FEED_SERVICE
    if _GLOBAL_FEED_SERVICE is None:
        _GLOBAL_FEED_SERVICE = DhanLiveFeedService()
    return _GLOBAL_FEED_SERVICE
