"""Subscription manager for Dhan live feed across the central connection budget."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any

from app.feedd.budget import (
    ConnectionBudgetExhaustedError,
    ConnectionBudgetManager,
    ConnectionLease,
    SocketType,
    get_connection_budget_manager,
)

logger = logging.getLogger(__name__)

MAX_INSTRUMENTS_PER_SOCKET = 5000
MAX_INSTRUMENTS_PER_MESSAGE = 100


class SubscriptionPriority(IntEnum):
    """Priority level for market feed subscriptions."""

    CRITICAL = 0  # Working orders, open positions, hard risk monitors
    HIGH = 1  # Active chart focus, visible option chain, order tickets
    MEDIUM = 2  # Active watchlists, scanner focus
    LOW = 3  # Inactive tabs, broad background universe


class SubscriptionMode(IntEnum):
    """Dhan subscription mode codes."""

    TICKER = 15
    QUOTE = 16
    FULL = 17


class SubscriptionCapacityExceededError(RuntimeError):
    """Raised when the subscription pool is saturated across all permitted sockets."""


@dataclass(frozen=True, slots=True)
class InstrumentKey:
    """Canonical instrument identifier tuple."""

    segment: str
    security_id: str

    @classmethod
    def from_tuple(cls, item: tuple[int | str, int | str]) -> InstrumentKey:
        return cls(segment=str(item[0]), security_id=str(item[1]))

    def to_wire_dict(self) -> dict[str, str]:
        return {"ExchangeSegment": self.segment, "SecurityId": self.security_id}


@dataclass
class SubscriptionItem:
    """Tracks state and multiple subscriber references for a single instrument."""

    key: InstrumentKey
    mode: SubscriptionMode = SubscriptionMode.FULL
    priority: SubscriptionPriority = SubscriptionPriority.MEDIUM
    subscribers: set[str] = field(default_factory=set)
    socket_id: str | None = None
    is_active: bool = False


@dataclass
class FeedSocketRecord:
    """Tracks instruments and telemetry assigned to a single WebSocket lease."""

    socket_id: str
    lease: ConnectionLease
    instruments: dict[InstrumentKey, SubscriptionItem] = field(default_factory=dict)
    is_connected: bool = True
    reconnect_count: int = 0
    last_packet_time: datetime | None = None
    total_packets: int = 0

    @property
    def subscribed_count(self) -> int:
        return len(self.instruments)

    def available_capacity(self, max_per_socket: int = MAX_INSTRUMENTS_PER_SOCKET) -> int:
        return max(0, max_per_socket - len(self.instruments))

    def can_accept(self, count: int = 1, max_per_socket: int = MAX_INSTRUMENTS_PER_SOCKET) -> bool:
        return (len(self.instruments) + count) <= max_per_socket


class SubscriptionManager:
    """Central manager allocating subscriptions across feed sockets adhering to budget & limits."""

    def __init__(
        self,
        budget_manager: ConnectionBudgetManager | None = None,
        max_instruments_per_socket: int = MAX_INSTRUMENTS_PER_SOCKET,
        max_instruments_per_message: int = MAX_INSTRUMENTS_PER_MESSAGE,
    ) -> None:
        self.budget_manager = budget_manager or get_connection_budget_manager()
        self.max_instruments_per_socket = max_instruments_per_socket
        self.max_instruments_per_message = max_instruments_per_message

        self.sockets: dict[str, FeedSocketRecord] = {}
        self.subscriptions: dict[InstrumentKey, SubscriptionItem] = {}

    def _ensure_socket_with_capacity(self, needed: int = 1) -> FeedSocketRecord:
        """Find an existing socket with capacity or allocate a new lease from budget manager."""
        # 1. Search existing sockets with available room
        for s in self.sockets.values():
            if s.can_accept(needed, self.max_instruments_per_socket):
                return s

        # 2. Try acquiring a new feed socket lease
        try:
            lease = self.budget_manager.acquire(
                SocketType.FEED,
                metadata={"purpose": "market_feed_subscription_pool"},
            )
        except ConnectionBudgetExhaustedError as exc:
            raise SubscriptionCapacityExceededError(
                f"Cannot acquire additional WebSocket connection: {exc}"
            ) from exc

        record = FeedSocketRecord(socket_id=lease.lease_id, lease=lease)
        self.sockets[lease.lease_id] = record
        logger.info("Allocated new feed socket %s for subscription pool", lease.lease_id)
        return record

    def subscribe(
        self,
        instruments: Sequence[tuple[int | str, int | str]],
        requester_id: str,
        priority: SubscriptionPriority = SubscriptionPriority.MEDIUM,
        mode: SubscriptionMode = SubscriptionMode.FULL,
    ) -> list[dict[str, Any]]:
        """Subscribe to a collection of instruments.

        Batches wire messages at <= 100 instruments per payload.
        """
        if not instruments:
            return []

        new_assignments: list[tuple[InstrumentKey, SubscriptionMode]] = []

        for item in instruments:
            key = InstrumentKey.from_tuple(item)

            if key in self.subscriptions:
                sub = self.subscriptions[key]
                sub.subscribers.add(requester_id)
                if priority < sub.priority:
                    sub.priority = priority
                if mode > sub.mode:
                    sub.mode = mode
                    # Need to resubscribe with higher mode
                    new_assignments.append((key, sub.mode))
            else:
                # New instrument subscription
                target_socket = self._ensure_socket_with_capacity(1)
                sub = SubscriptionItem(
                    key=key,
                    mode=mode,
                    priority=priority,
                    subscribers={requester_id},
                    socket_id=target_socket.socket_id,
                    is_active=True,
                )
                target_socket.instruments[key] = sub
                self.subscriptions[key] = sub
                new_assignments.append((key, mode))

        # Generate batched wire messages
        return self._batch_subscription_messages(new_assignments)

    def unsubscribe(
        self,
        instruments: Sequence[tuple[int | str, int | str]],
        requester_id: str,
    ) -> list[dict[str, Any]]:
        """Unsubscribe requester from instruments.

        Releases wire subscription if no subscribers remain.
        """
        if not instruments:
            return []

        to_remove: list[tuple[InstrumentKey, SubscriptionMode]] = []

        for item in instruments:
            key = InstrumentKey.from_tuple(item)
            if key not in self.subscriptions:
                continue

            sub = self.subscriptions[key]
            sub.subscribers.discard(requester_id)

            if not sub.subscribers:
                # No more requesters for this instrument: clean up
                if sub.socket_id and sub.socket_id in self.sockets:
                    self.sockets[sub.socket_id].instruments.pop(key, None)
                to_remove.append((key, sub.mode))
                self.subscriptions.pop(key, None)

        # Generate unsubscribe batches (Dhan uses RequestCode for unsub or payload chunks)
        return self._batch_subscription_messages(to_remove, is_unsubscribe=True)

    def on_socket_disconnect(self, socket_id: str, reason: str = "") -> None:
        """Mark socket as disconnected and increment reconnect count."""
        if socket_id in self.sockets:
            sock = self.sockets[socket_id]
            sock.is_connected = False
            sock.reconnect_count += 1
            logger.warning("Socket %s disconnected: %s", socket_id, reason)

    def on_socket_reconnect(self, socket_id: str) -> list[dict[str, Any]]:
        """Mark socket reconnected and generate priority-ordered resubscription batches."""
        if socket_id not in self.sockets:
            return []

        sock = self.sockets[socket_id]
        sock.is_connected = True

        # Sort registered instruments by priority: CRITICAL first, then HIGH, MEDIUM, LOW
        sorted_items = sorted(
            sock.instruments.values(),
            key=lambda item: (item.priority, item.key.security_id),
        )

        assignments = [(item.key, item.mode) for item in sorted_items]
        return self._batch_subscription_messages(assignments)

    def _batch_subscription_messages(
        self,
        items: list[tuple[InstrumentKey, SubscriptionMode]],
        is_unsubscribe: bool = False,
    ) -> list[dict[str, Any]]:
        """Chunk instruments into wire payloads strictly <= max_instruments_per_message (100)."""
        if not items:
            return []

        # Group by subscription mode so each message has a consistent RequestCode
        grouped: dict[SubscriptionMode, list[InstrumentKey]] = defaultdict(list)
        for key, mode in items:
            grouped[mode].append(key)

        messages: list[dict[str, Any]] = []

        for mode, keys in grouped.items():
            # Chunk keys into slices of max_instruments_per_message (100)
            for i in range(0, len(keys), self.max_instruments_per_message):
                chunk = keys[i : i + self.max_instruments_per_message]
                inst_list = [k.to_wire_dict() for k in chunk]

                msg: dict[str, Any] = {
                    "RequestCode": int(mode),
                    "InstrumentCount": len(inst_list),
                    "InstrumentList": inst_list,
                }
                if is_unsubscribe:
                    msg["IsUnsubscribe"] = True

                messages.append(msg)

        return messages

    def get_socket_for_instrument(self, item: tuple[int | str, int | str]) -> str | None:
        """Return socket ID hosting the given instrument, or None if not subscribed."""
        key = InstrumentKey.from_tuple(item)
        sub = self.subscriptions.get(key)
        return sub.socket_id if sub else None

    def get_health_status(self) -> dict[str, Any]:
        """Aggregate health metrics across all active sockets and subscriptions."""
        total_subscribed = len(self.subscriptions)
        socket_stats = []

        for s_id, s in self.sockets.items():
            socket_stats.append(
                {
                    "socket_id": s_id,
                    "is_connected": s.is_connected,
                    "subscribed_count": s.subscribed_count,
                    "available_capacity": s.available_capacity(self.max_instruments_per_socket),
                    "reconnect_count": s.reconnect_count,
                    "last_packet_time": s.last_packet_time.isoformat()
                    if s.last_packet_time
                    else None,
                    "total_packets": s.total_packets,
                }
            )

        return {
            "total_subscribed": total_subscribed,
            "active_sockets": len(self.sockets),
            "max_per_socket": self.max_instruments_per_socket,
            "max_per_message": self.max_instruments_per_message,
            "sockets": socket_stats,
        }
