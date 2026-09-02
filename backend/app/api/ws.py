"""Browser WebSocket fan-out, snapshots, streaming deltas, and backpressure management."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.dhan.packets import (
    FeedPacket,
    FullPacket,
    OIPacket,
    QuotePacket,
    TickerPacket,
)
from app.feedd.cache import (
    HotCache,
    InMemoryHotCache,
)

logger = logging.getLogger(__name__)

DEFAULT_CLIENT_QUEUE_SIZE = 100


class ClientSession:
    """Represents a connected browser client session with bounded outbound queue."""

    def __init__(
        self,
        session_id: str | None = None,
        websocket: WebSocket | None = None,
        max_queue_size: int = DEFAULT_CLIENT_QUEUE_SIZE,
        is_authenticated: bool = True,
    ) -> None:
        self.session_id = session_id or str(uuid4())
        self.websocket = websocket
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max_queue_size)
        self.subscribed_instruments: set[tuple[str, str]] = set()
        self.subscribed_channels: set[str] = {"quotes", "depth", "oi"}
        self.is_authenticated = is_authenticated
        self.is_slow = False
        self.dropped_messages_count = 0
        self.connected_at = time.time()

    def send_nowait(self, message: dict[str, Any]) -> bool:
        """Enqueue an outbound message non-blockingly.

        If the queue is full, the message is dropped and backpressure state is recorded,
        preventing any blocking of the fan-out dispatcher or feed ingestion.
        """
        try:
            self.queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            self.is_slow = True
            self.dropped_messages_count += 1
            logger.warning(
                "Client session %s buffer full; dropped message on channel %s",
                self.session_id,
                message.get("channel"),
            )
            return False


class MarketDataFanoutManager:
    """Manages browser WebSocket sessions, state snapshots, streaming deltas, and backpressure."""

    def __init__(
        self,
        hot_cache: HotCache | None = None,
        max_client_queue_size: int = DEFAULT_CLIENT_QUEUE_SIZE,
    ) -> None:
        self.hot_cache: HotCache = hot_cache or InMemoryHotCache()
        self.max_client_queue_size = max_client_queue_size
        self._sessions: dict[str, ClientSession] = {}
        self._instrument_subscribers: dict[tuple[str, str], set[str]] = {}

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    def register_session(self, session: ClientSession) -> None:
        self._sessions[session.session_id] = session

    def unregister_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            for inst in session.subscribed_instruments:
                subscribers = self._instrument_subscribers.get(inst)
                if subscribers:
                    subscribers.discard(session_id)
                    if not subscribers:
                        self._instrument_subscribers.pop(inst, None)

    def get_session(self, session_id: str) -> ClientSession | None:
        return self._sessions.get(session_id)

    def subscribe(
        self,
        session_id: str,
        instruments: Sequence[tuple[str, str]],
        channels: Sequence[str] | None = None,
        now: float | None = None,
    ) -> list[dict[str, Any]]:
        """Subscribe session to instruments and return initial state snapshots."""
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")

        if channels:
            session.subscribed_channels.update(channels)

        snapshots: list[dict[str, Any]] = []
        t = now if now is not None else time.time()

        for seg, sec_id in instruments:
            inst_key = (str(seg), str(sec_id))
            session.subscribed_instruments.add(inst_key)

            if inst_key not in self._instrument_subscribers:
                self._instrument_subscribers[inst_key] = set()
            self._instrument_subscribers[inst_key].add(session_id)

            # Generate snapshots from hot cache
            if "quotes" in session.subscribed_channels:
                quote = self.hot_cache.get_quote(inst_key[0], inst_key[1], now=t)
                if quote:
                    snap = {
                        "type": "snapshot",
                        "channel": "quotes",
                        "segment": inst_key[0],
                        "security_id": inst_key[1],
                        "data": quote.model_dump(),
                    }
                    snapshots.append(snap)
                    session.send_nowait(snap)

            if "depth" in session.subscribed_channels:
                depth = self.hot_cache.get_depth(inst_key[0], inst_key[1], now=t)
                if depth:
                    snap = {
                        "type": "snapshot",
                        "channel": "depth",
                        "segment": inst_key[0],
                        "security_id": inst_key[1],
                        "data": depth.model_dump(),
                    }
                    snapshots.append(snap)
                    session.send_nowait(snap)

            if "oi" in session.subscribed_channels:
                oi = self.hot_cache.get_oi(inst_key[0], inst_key[1], now=t)
                if oi:
                    snap = {
                        "type": "snapshot",
                        "channel": "oi",
                        "segment": inst_key[0],
                        "security_id": inst_key[1],
                        "data": oi.model_dump(),
                    }
                    snapshots.append(snap)
                    session.send_nowait(snap)

        return snapshots

    def unsubscribe(
        self, session_id: str, instruments: Sequence[tuple[str, str]]
    ) -> None:
        """Unsubscribe session from specified instruments."""
        session = self._sessions.get(session_id)
        if not session:
            return

        for seg, sec_id in instruments:
            inst_key = (str(seg), str(sec_id))
            session.subscribed_instruments.discard(inst_key)
            subscribers = self._instrument_subscribers.get(inst_key)
            if subscribers:
                subscribers.discard(session_id)
                if not subscribers:
                    self._instrument_subscribers.pop(inst_key, None)

    def resync(self, session_id: str, now: float | None = None) -> list[dict[str, Any]]:
        """Deliver fresh state snapshots for all currently subscribed instruments."""
        session = self._sessions.get(session_id)
        if not session:
            return []

        active_instruments = list(session.subscribed_instruments)
        return self.subscribe(session_id, active_instruments, now=now)

    def broadcast_packet(
        self, packet: FeedPacket, now: float | None = None
    ) -> int:
        """Ingest feed packet into hot cache and dispatch deltas to subscribed sessions.

        Guaranteed non-blocking: slow clients with full queues have messages dropped
        without delaying this method or blocking feed ingestion.
        """
        t = now if now is not None else time.time()
        self.hot_cache.update_from_packet(packet, now=t)

        seg = str(packet.header.exchange_segment)
        sec_id = str(packet.header.security_id)
        inst_key = (seg, sec_id)

        subscribers = self._instrument_subscribers.get(inst_key)
        if not subscribers:
            return 0

        messages_to_dispatch: list[dict[str, Any]] = []

        if isinstance(packet, (QuotePacket, FullPacket, TickerPacket)):
            q_data: dict[str, Any] = {
                "segment": seg,
                "security_id": sec_id,
                "ltp": packet.ltp,
                "ltt": packet.ltt,
                "received_at": t,
            }
            if isinstance(packet, (QuotePacket, FullPacket)):
                q_data.update(
                    {
                        "ltq": packet.ltq,
                        "avg_price": packet.avg_price,
                        "volume": packet.volume,
                        "total_buy_qty": packet.total_buy_qty,
                        "total_sell_qty": packet.total_sell_qty,
                        "open": packet.open,
                        "high": packet.high,
                        "low": packet.low,
                        "close": packet.close,
                    }
                )
            messages_to_dispatch.append(
                {
                    "type": "delta",
                    "channel": "quotes",
                    "segment": seg,
                    "security_id": sec_id,
                    "data": q_data,
                }
            )

        if isinstance(packet, (OIPacket, FullPacket)):
            messages_to_dispatch.append(
                {
                    "type": "delta",
                    "channel": "oi",
                    "segment": seg,
                    "security_id": sec_id,
                    "data": {
                        "segment": seg,
                        "security_id": sec_id,
                        "open_interest": packet.open_interest,
                        "received_at": t,
                    },
                }
            )

        if isinstance(packet, FullPacket):
            messages_to_dispatch.append(
                {
                    "type": "delta",
                    "channel": "depth",
                    "segment": seg,
                    "security_id": sec_id,
                    "data": {
                        "segment": seg,
                        "security_id": sec_id,
                        "bids": [
                            {"price": b.price, "quantity": b.quantity, "orders": b.orders}
                            for b in packet.depth.bids
                        ],
                        "asks": [
                            {"price": a.price, "quantity": a.quantity, "orders": a.orders}
                            for a in packet.depth.asks
                        ],
                        "received_at": t,
                    },
                }
            )

        successful_enqueues = 0
        for s_id in list(subscribers):
            session = self._sessions.get(s_id)
            if not session:
                continue

            for msg in messages_to_dispatch:
                channel = msg["channel"]
                if channel in session.subscribed_channels:
                    if session.send_nowait(msg):
                        successful_enqueues += 1

        return successful_enqueues

    def get_metrics(self) -> dict[str, Any]:
        """Aggregate metrics for fan-out performance and backpressure."""
        total_dropped = sum(s.dropped_messages_count for s in self._sessions.values())
        slow_sessions = [s.session_id for s in self._sessions.values() if s.is_slow]
        return {
            "active_sessions": len(self._sessions),
            "subscribed_instruments_count": len(self._instrument_subscribers),
            "total_dropped_messages": total_dropped,
            "slow_sessions_count": len(slow_sessions),
            "slow_session_ids": slow_sessions,
        }


# Global fanout manager singleton for API process
_GLOBAL_FANOUT_MANAGER: MarketDataFanoutManager | None = None


def get_market_data_fanout_manager() -> MarketDataFanoutManager:
    global _GLOBAL_FANOUT_MANAGER
    if _GLOBAL_FANOUT_MANAGER is None:
        _GLOBAL_FANOUT_MANAGER = MarketDataFanoutManager()
    return _GLOBAL_FANOUT_MANAGER
