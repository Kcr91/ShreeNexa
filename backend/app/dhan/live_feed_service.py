"""Live Dhan WebSocket market feed ingestion service for ShreeNexa."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx
import websockets

from app.api.ws import get_market_data_fanout_manager
from app.config import mask_client_id
from app.dhan.credentials import resolve_dhan_credentials
from app.dhan.feed import DhanLiveFeedClient
from app.feedd.cache import CachedQuote

logger = logging.getLogger("shreenexa.dhan.live_feed")

# Default liquid instruments to stream
DEFAULT_SUBSCRIPTIONS = [
    # Top NIFTY 50 Stocks (NSE_EQ)
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1333"},  # HDFCBANK
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "2885"},  # RELIANCE
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "11536"},  # TCS
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1594"},  # INFY
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "4963"},  # ICICIBANK
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "3045"},  # SBIN
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "10604"},  # BHARTIARTL
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "3456"},  # TATAMOTORS
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1232"},  # GRASIM
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1922"},  # KOTAKBANK
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "5900"},  # AXISBANK
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "236"},  # ASIANPAINT
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "11483"},  # LT
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "526"},  # BPCL
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1363"},  # HINDUNILVR
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "1660"},  # ITC
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "317"},  # BAJFINANCE
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "10999"},  # MARUTI
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "3499"},  # TATASTEEL
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "3351"},  # SUNPHARMA
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "3787"},  # WIPRO
    {"ExchangeSegment": "NSE_EQ", "SecurityId": "7229"},  # HCLTECH
    # Indices (IDX_I)
    {"ExchangeSegment": "IDX_I", "SecurityId": "13"},  # NIFTY 50
    {"ExchangeSegment": "IDX_I", "SecurityId": "25"},  # NIFTY BANK
]

SECURITY_ID_TO_SYMBOL: dict[str, str] = {
    "1333": "HDFCBANK",
    "2885": "RELIANCE",
    "11536": "TCS",
    "1594": "INFY",
    "4963": "ICICIBANK",
    "3045": "SBIN",
    "10604": "BHARTIARTL",
    "3456": "TATAMOTORS",
    "1232": "GRASIM",
    "1922": "KOTAKBANK",
    "5900": "AXISBANK",
    "236": "ASIANPAINT",
    "11483": "LT",
    "526": "BPCL",
    "1363": "HINDUNILVR",
    "1660": "ITC",
    "317": "BAJFINANCE",
    "10999": "MARUTI",
    "3499": "TATASTEEL",
    "3351": "SUNPHARMA",
    "3787": "WIPRO",
    "7229": "HCLTECH",
    "2142": "POWERGRID",
    "3103": "NESTLEIND",
    "10794": "NTPC",
    "13538": "TECHM",
    "14977": "ONGC",
    "3506": "TITAN",
    "14418": "NIFTYBEES",
    "14419": "BANKBEES",
    "13": "NIFTY 50",
    "25": "NIFTY BANK",
    "27": "NIFTY FIN SERVICE",
    "28": "NIFTY MID SELECT",
    "29": "NIFTY IT",
    "30": "NIFTY AUTO",
}


class DhanLiveFeedService:
    """Manages active connection to DhanHQ Live Market Feed WebSocket and packet fan-out."""

    def __init__(self, subscriptions: list[dict[str, str]] | None = None) -> None:
        self.subscriptions = subscriptions or list(DEFAULT_SUBSCRIPTIONS)
        self.is_running = False
        self.total_packets = 0
        self.cached_quotes: dict[str, Any] = {}
        self.last_quote_sync_time: float = 0.0
        self._stop_event = asyncio.Event()

    def get_latest_quotes(self) -> dict[str, Any]:
        """Return latest authentic Dhan OHLC and closing quotes."""
        return self.cached_quotes

    async def sync_ohlc_quotes(self) -> None:
        """Fetch authentic closing/OHLC quotes from Dhan REST API and update hot cache."""
        creds = resolve_dhan_credentials()
        if not creds or not creds.access_token or not creds.client_id:
            return

        client_id = creds.client_id
        token = creds.access_token.get_secret_value()
        url = "https://api.dhan.co/v2/marketfeed/ohlc"
        headers = {
            "access-token": token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        eq_ids = [
            1333,
            2885,
            11536,
            1594,
            4963,
            3045,
            10604,
            1660,
            1922,
            317,
            10999,
            3456,
            1232,
            5900,
            236,
            11483,
            526,
            1363,
            3499,
            3351,
            3787,
            7229,
            2142,
            3103,
            10794,
            13538,
            14977,
            3506,
            14418,
            14419,
        ]
        body = {"NSE_EQ": eq_ids, "IDX_I": [13, 25, 27, 28, 29, 30]}

        try:
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                resp = await http_client.post(url, headers=headers, json=body)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    t = time.time()
                    fanout_mgr = get_market_data_fanout_manager()

                    # 1. Equities
                    for sec_id_str, q in data.get("NSE_EQ", {}).items():
                        ltp = float(q.get("last_price", 0.0))
                        ohlc = q.get("ohlc", {})
                        open_p = float(ohlc.get("open", ltp))
                        close_p = float(ohlc.get("close", ltp))
                        high_p = float(ohlc.get("high", ltp))
                        low_p = float(ohlc.get("low", ltp))

                        quote_item = {
                            "segment": "NSE_EQ",
                            "security_id": sec_id_str,
                            "ltp": ltp,
                            "open": open_p,
                            "high": high_p,
                            "low": low_p,
                            "close": close_p,
                            "received_at": t,
                        }
                        self.cached_quotes[f"NSE_EQ:{sec_id_str}"] = quote_item
                        self.cached_quotes[sec_id_str] = quote_item
                        sym = SECURITY_ID_TO_SYMBOL.get(sec_id_str)
                        if sym:
                            self.cached_quotes[sym] = quote_item

                        cached_q = CachedQuote(
                            segment="1",
                            security_id=sec_id_str,
                            ltp=ltp,
                            ltq=1,
                            ltt=int(t),
                            avg_price=ltp,
                            volume=1000,
                            total_buy_qty=1000.0,
                            total_sell_qty=1000.0,
                            open=open_p,
                            high=high_p,
                            low=low_p,
                            close=close_p,
                            received_at=t,
                        )
                        fanout_mgr.hot_cache.set_quote(cached_q)
                        fanout_mgr.hot_cache.set_quote(
                            cached_q.model_copy(update={"segment": "NSE_EQ"})
                        )

                    # 2. Indices
                    for sec_id_str, q in data.get("IDX_I", {}).items():
                        ltp = float(q.get("last_price", 0.0))
                        ohlc = q.get("ohlc", {})
                        open_p = float(ohlc.get("open", ltp))
                        close_p = float(ohlc.get("close", ltp))
                        high_p = float(ohlc.get("high", ltp))
                        low_p = float(ohlc.get("low", ltp))

                        quote_item = {
                            "segment": "IDX_I",
                            "security_id": sec_id_str,
                            "ltp": ltp,
                            "open": open_p,
                            "high": high_p,
                            "low": low_p,
                            "close": close_p,
                            "received_at": t,
                        }
                        self.cached_quotes[f"IDX_I:{sec_id_str}"] = quote_item
                        self.cached_quotes[sec_id_str] = quote_item
                        sym = SECURITY_ID_TO_SYMBOL.get(sec_id_str)
                        if sym:
                            self.cached_quotes[sym] = quote_item
                            if sym == "NIFTY 50":
                                self.cached_quotes["NIFTY"] = quote_item
                                self.cached_quotes["NIFTY50"] = quote_item
                            elif sym == "NIFTY BANK":
                                self.cached_quotes["BANKNIFTY"] = quote_item
                                self.cached_quotes["BANK NIFTY"] = quote_item
                            elif sym == "NIFTY FIN SERVICE":
                                self.cached_quotes["FINNIFTY"] = quote_item
                            elif sym == "NIFTY MID SELECT":
                                self.cached_quotes["MIDCPNIFTY"] = quote_item
                            elif sym == "NIFTY IT":
                                self.cached_quotes["NIFTYIT"] = quote_item
                            elif sym == "NIFTY AUTO":
                                self.cached_quotes["NIFTYAUTO"] = quote_item

                        cached_q = CachedQuote(
                            segment="0",
                            security_id=sec_id_str,
                            ltp=ltp,
                            ltq=1,
                            ltt=int(t),
                            avg_price=ltp,
                            volume=1000,
                            total_buy_qty=1000.0,
                            total_sell_qty=1000.0,
                            open=open_p,
                            high=high_p,
                            low=low_p,
                            close=close_p,
                            received_at=t,
                        )
                        fanout_mgr.hot_cache.set_quote(cached_q)
                        fanout_mgr.hot_cache.set_quote(
                            cached_q.model_copy(update={"segment": "1"})
                        )
                        fanout_mgr.hot_cache.set_quote(
                            cached_q.model_copy(update={"segment": "IDX_I"})
                        )

                    self.last_quote_sync_time = t
                    eq_cnt = len(data.get("NSE_EQ", {}))
                    idx_cnt = len(data.get("IDX_I", {}))
                    print(
                        f"[DhanFeed] Successfully synced {eq_cnt} equities and "
                        f"{idx_cnt} indices real quotes from Dhan REST API",
                        flush=True,
                    )
        except Exception as err:
            logger.warning(f"[DhanFeed] Failed to sync OHLC quotes from REST API: {err}")

    async def run(self) -> None:
        """Connect to Dhan WebSocket, subscribe to instruments, and pump decoded packets."""
        self.is_running = True
        self._stop_event.clear()
        backoff = 1.0

        # Initial synchronization of authentic Dhan OHLC and closing quotes
        await self.sync_ohlc_quotes()

        while not self._stop_event.is_set():
            creds = resolve_dhan_credentials()
            if not creds or not creds.access_token or not creds.client_id:
                logger.warning(
                    "[DhanFeed] No valid Dhan credentials found in environment or .env; "
                    "waiting 10s..."
                )
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=10.0)
                except TimeoutError:
                    continue
                break

            client_id = creds.client_id
            token = creds.access_token.get_secret_value()
            masked_id = mask_client_id(client_id)
            feed_url = (
                f"wss://api-feed.dhan.co?version=2&token={token}&clientId={client_id}&authType=2"
            )

            print(
                f"[DhanFeed] Connecting to Dhan live market feed (client={masked_id})...",
                flush=True,
            )
            fanout_mgr = get_market_data_fanout_manager()
            client = DhanLiveFeedClient(client_id=client_id, access_token=token)

            try:
                async with websockets.connect(
                    feed_url,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    print(
                        "[DhanFeed] Connected to Dhan live feed WebSocket successfully!",
                        flush=True,
                    )
                    backoff = 1.0

                    # 1. Equities subscription (Ticker = 15 or Quote = 16)
                    eq_list = [s for s in self.subscriptions if s["ExchangeSegment"] != "IDX_I"]
                    if eq_list:
                        await ws.send(
                            json.dumps(
                                {
                                    "RequestCode": 15,  # Ticker mode ensures high throughput
                                    "InstrumentCount": len(eq_list),
                                    "InstrumentList": eq_list,
                                }
                            )
                        )
                        print(
                            f"[DhanFeed] Subscribed to {len(eq_list)} equity instruments",
                            flush=True,
                        )

                    # 2. Index subscription (IDX_I)
                    idx_list = [s for s in self.subscriptions if s["ExchangeSegment"] == "IDX_I"]
                    if idx_list:
                        await ws.send(
                            json.dumps(
                                {
                                    "RequestCode": 15,
                                    "InstrumentCount": len(idx_list),
                                    "InstrumentList": idx_list,
                                }
                            )
                        )
                        print(
                            f"[DhanFeed] Subscribed to {len(idx_list)} index instruments",
                            flush=True,
                        )

                    last_log_time = asyncio.get_event_loop().time()
                    packets_since_log = 0

                    while not self._stop_event.is_set():
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                        except TimeoutError:
                            continue

                        if isinstance(msg, bytes):
                            packets = client.process_incoming_frame(msg)
                            for pkt in packets:
                                self.total_packets += 1
                                packets_since_log += 1
                                fanout_mgr.broadcast_packet(pkt)

                            now = asyncio.get_event_loop().time()
                            if now - last_log_time >= 10.0:
                                print(
                                    f"[DhanFeed] Feed active: {packets_since_log} packets "
                                    f"in last 10s (total={self.total_packets})",
                                    flush=True,
                                )
                                last_log_time = now
                                packets_since_log = 0
                        elif isinstance(msg, str):
                            print(f"[DhanFeed] Received text message: {msg}", flush=True)

            except asyncio.CancelledError:
                print("[DhanFeed] Feed task cancelled, closing connection cleanly", flush=True)
                break
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                print(
                    f"[DhanFeed] Connection dropped ({type(exc).__name__}: {exc}). "
                    f"Reconnecting in {backoff:.1f}s...",
                    flush=True,
                )
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
                except TimeoutError:
                    pass
                backoff = min(backoff * 2.0, 15.0)

        self.is_running = False
        logger.info("[DhanFeed] Service stopped")

    def stop(self) -> None:
        """Signal background runner to stop."""
        self._stop_event.set()


_GLOBAL_FEED_SERVICE: DhanLiveFeedService | None = None


def get_dhan_live_feed_service() -> DhanLiveFeedService:
    """Retrieve global singleton feed service instance."""
    global _GLOBAL_FEED_SERVICE
    if _GLOBAL_FEED_SERVICE is None:
        _GLOBAL_FEED_SERVICE = DhanLiveFeedService()
    return _GLOBAL_FEED_SERVICE
