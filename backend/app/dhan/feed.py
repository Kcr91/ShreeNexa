"""Dhan Live Market Feed WebSocket client, heartbeat, and reconnect state machine."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.dhan.packets import CorruptPacketError, DhanFeedParser, FeedPacket

logger = logging.getLogger(__name__)

MAX_INSTRUMENTS_PER_SUBSCRIBE_MESSAGE = 100


class FeedConnectionState(StrEnum):
    """Lifecycle states for Dhan WebSocket live feed connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ReconnectPolicy:
    """Parameters governing exponential backoff reconnect behavior."""

    initial_delay_seconds: float = 0.5
    max_delay_seconds: float = 10.0
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1
    max_reconnect_attempts: int = 10


class FeedConnectionStateMachine:
    """Manages the connection state lifecycle and computes exponential backoff delays."""

    def __init__(self, policy: ReconnectPolicy | None = None) -> None:
        self.policy = policy or ReconnectPolicy()
        self.state: FeedConnectionState = FeedConnectionState.DISCONNECTED
        self.attempts: int = 0
        self.last_disconnect_reason: str | None = None
        self.state_history: list[tuple[float, FeedConnectionState]] = []
        self._set_state(FeedConnectionState.DISCONNECTED)

    def _set_state(self, new_state: FeedConnectionState) -> None:
        self.state = new_state
        self.state_history.append((time.monotonic(), new_state))
        logger.debug("Feed state transition: %s", new_state)

    @property
    def current_state(self) -> FeedConnectionState:
        """Dynamic property returning current connection state."""
        return self.state

    def get_state(self) -> FeedConnectionState:
        """Return current state as an un-narrowed method call."""
        return self.state

    def on_connect_start(self) -> None:
        """Transition from DISCONNECTED or RECONNECTING to CONNECTING."""
        self._set_state(FeedConnectionState.CONNECTING)

    def on_connected(self) -> None:
        """Transition to CONNECTED and reset retry counters."""
        self.attempts = 0
        self.last_disconnect_reason = None
        self._set_state(FeedConnectionState.CONNECTED)

    def on_disconnect(self, reason: str = "Connection closed") -> float:
        """Record a disconnect and return backoff delay before next reconnect attempt."""
        self.last_disconnect_reason = reason
        self.attempts += 1

        if self.attempts > self.policy.max_reconnect_attempts:
            self._set_state(FeedConnectionState.FAILED)
            return -1.0  # Max attempts exceeded

        self._set_state(FeedConnectionState.RECONNECTING)
        # Calculate exponential backoff
        base_delay = self.policy.initial_delay_seconds * (
            self.policy.backoff_multiplier ** (self.attempts - 1)
        )
        clamped_delay = min(base_delay, self.policy.max_delay_seconds)
        # Apply jitter
        jitter = clamped_delay * self.policy.jitter_factor * (random.random() * 2 - 1)
        delay = max(0.1, clamped_delay + jitter)
        return delay

    def on_failed(self) -> None:
        """Explicitly transition to terminal FAILED state."""
        self._set_state(FeedConnectionState.FAILED)

    def reset(self) -> None:
        """Reset state machine back to clean DISCONNECTED state."""
        self.attempts = 0
        self.last_disconnect_reason = None
        self._set_state(FeedConnectionState.DISCONNECTED)


@dataclass
class FeedHeartbeatMonitor:
    """Tracks socket ping/pong health and detects silent connection stall."""

    ping_interval_seconds: float = 10.0
    pong_timeout_seconds: float = 30.0

    last_ping_sent: float = field(default_factory=time.monotonic)
    last_pong_received: float = field(default_factory=time.monotonic)
    last_packet_received: float = field(default_factory=time.monotonic)

    def record_packet(self) -> None:
        now = time.monotonic()
        self.last_packet_received = now
        self.last_pong_received = now

    def record_ping(self) -> None:
        self.last_ping_sent = time.monotonic()

    def record_pong(self) -> None:
        self.last_pong_received = time.monotonic()

    def should_send_ping(self, now: float | None = None) -> bool:
        t = now if now is not None else time.monotonic()
        return (t - self.last_ping_sent) >= self.ping_interval_seconds

    def is_stale(self, now: float | None = None) -> bool:
        t = now if now is not None else time.monotonic()
        last_activity = max(self.last_pong_received, self.last_packet_received)
        return (t - last_activity) > self.pong_timeout_seconds


class DhanLiveFeedClient:
    """Manages Dhan Live Market Feed binary WebSocket stream, packet parsing, and subscriptions."""

    DEFAULT_FEED_URL = "wss://api-feed.dhan.co"

    def __init__(
        self,
        client_id: str,
        access_token: str,
        feed_url: str = DEFAULT_FEED_URL,
        reconnect_policy: ReconnectPolicy | None = None,
        on_packet: Callable[[FeedPacket], None] | None = None,
    ) -> None:
        self._client_id = client_id
        self._access_token = access_token
        self.feed_url = feed_url
        self.state_machine = FeedConnectionStateMachine(reconnect_policy)
        self.heartbeat = FeedHeartbeatMonitor()
        self.on_packet = on_packet
        self.total_packets_received: int = 0
        self.corrupt_packets_count: int = 0

    def __repr__(self) -> str:
        # Redact credentials from logs/representations
        return (
            f"<DhanLiveFeedClient url={self.feed_url} "
            f"state={self.state_machine.state} "
            f"packets={self.total_packets_received}>"
        )

    def process_incoming_frame(self, data: bytes) -> list[FeedPacket]:
        """Decode incoming binary frame into typed packets and dispatch callbacks."""
        packets: list[FeedPacket] = []
        if not data:
            return packets

        offset = 0
        total_len = len(data)

        while offset < total_len:
            remaining = data[offset:]
            if len(remaining) < DhanFeedParser.HEADER_SIZE:
                self.corrupt_packets_count += 1
                logger.warning("Truncated trailing bytes in feed frame: %d bytes", len(remaining))
                break

            try:
                header = DhanFeedParser.parse_header(remaining)
                msg_len = header.msg_length

                if msg_len <= 0 or len(remaining) < msg_len:
                    # Truncated or malformed message length
                    self.corrupt_packets_count += 1
                    logger.warning(
                        "Truncated packet payload: declared %d bytes, available %d",
                        msg_len,
                        len(remaining),
                    )
                    break

                packet_bytes = remaining[:msg_len]
                packet = DhanFeedParser.parse_packet(packet_bytes)
                packets.append(packet)
                self.total_packets_received += 1
                self.heartbeat.record_packet()

                if self.on_packet:
                    try:
                        self.on_packet(packet)
                    except Exception as cb_exc:
                        logger.error("Error in on_packet callback: %s", cb_exc)

                offset += msg_len

            except CorruptPacketError as err:
                self.corrupt_packets_count += 1
                logger.warning("Corrupt packet encountered: %s", err)
                break
            except Exception as unk_err:
                self.corrupt_packets_count += 1
                logger.error("Unexpected error decoding packet: %s", unk_err)
                break

        return packets

    @classmethod
    def build_subscription_message(
        cls,
        instruments: Sequence[tuple[int | str, int | str]],
        request_code: int = 17,  # Default: Full Mode (15=Ticker, 16=Quote, 17=Full)
    ) -> dict[str, Any]:
        """Construct subscription JSON request adhering to <=100 instruments batch limit."""
        if len(instruments) > MAX_INSTRUMENTS_PER_SUBSCRIBE_MESSAGE:
            raise ValueError(
                f"Subscription batch cannot exceed {MAX_INSTRUMENTS_PER_SUBSCRIBE_MESSAGE} "
                f"instruments (got {len(instruments)})"
            )

        inst_list = [
            {"ExchangeSegment": str(seg), "SecurityId": str(sec_id)}
            for seg, sec_id in instruments
        ]
        return {
            "RequestCode": request_code,
            "InstrumentCount": len(inst_list),
            "InstrumentList": inst_list,
        }
