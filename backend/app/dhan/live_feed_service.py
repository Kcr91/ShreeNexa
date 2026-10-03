"""Dhan market-data ingestion owned exclusively by the ``feedd`` process."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import UTC, datetime
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
}
DHAN_TO_SEGMENT = {value: key for key, value in SEGMENT_TO_DHAN.items()}


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
            for body in request_bodies:
                response_data = await asyncio.to_thread(client.get_quotes, body)
                for segment, quotes in response_data.items():
                    if isinstance(quotes, dict):
                        payload.setdefault(segment, {}).update(quotes)
        except Exception as exc:
            logger.warning("Dhan quote bootstrap failed: %s", type(exc).__name__)
            return

        received_at = time.time()
        for dhan_segment, segment_quotes in payload.items():
            segment_code = DHAN_TO_SEGMENT.get(str(dhan_segment))
            if segment_code is None or not isinstance(segment_quotes, dict):
                continue
            for security_id, raw in segment_quotes.items():
                if not isinstance(raw, dict):
                    continue
                ltp = _number(raw.get("last_price"))
                net_change = _number(raw.get("net_change"))
                raw_ohlc = raw.get("ohlc")
                ohlc: dict[str, Any] = raw_ohlc if isinstance(raw_ohlc, dict) else {}
                previous_close = (
                    ltp - net_change if ltp is not None and net_change is not None else None
                )
                trade_time = _trade_time(raw.get("last_trade_time"))
                self.hot_cache.set_quote(
                    CachedQuote(
                        segment=segment_code,
                        security_id=str(security_id),
                        ltp=ltp,
                        ltq=_integer(raw.get("last_quantity")),
                        ltt=trade_time,
                        avg_price=_number(raw.get("average_price")),
                        volume=_integer(raw.get("volume")),
                        total_buy_qty=_number(raw.get("buy_quantity")),
                        total_sell_qty=_number(raw.get("sell_quantity")),
                        open=_number(ohlc.get("open")),
                        high=_number(ohlc.get("high")),
                        low=_number(ohlc.get("low")),
                        close=_number(ohlc.get("close")),
                        previous_close=previous_close,
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
