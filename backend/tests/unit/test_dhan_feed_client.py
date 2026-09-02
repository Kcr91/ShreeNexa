"""Unit tests for Dhan live feed client and reconnect state machine."""

from __future__ import annotations

import pytest
from app.dhan import (
    DhanLiveFeedClient,
    FeedConnectionState,
    FeedConnectionStateMachine,
    FeedHeartbeatMonitor,
    ReconnectPolicy,
)


def test_client_repr_redacts_credentials() -> None:
    secret_token = "dhan_secret_access_token_xyz123"
    secret_client_id = "dhan_client_id_9999"

    client = DhanLiveFeedClient(client_id=secret_client_id, access_token=secret_token)
    repr_str = repr(client)

    assert secret_token not in repr_str
    assert secret_client_id not in repr_str
    assert "DhanLiveFeedClient" in repr_str


def test_subscription_message_respects_batch_limit() -> None:
    # 1. Valid batch of 50 instruments
    valid_instruments = [("NSE_EQ", f"{1000 + i}") for i in range(50)]
    msg = DhanLiveFeedClient.build_subscription_message(valid_instruments, request_code=17)

    assert msg["RequestCode"] == 17
    assert msg["InstrumentCount"] == 50
    assert len(msg["InstrumentList"]) == 50
    assert msg["InstrumentList"][0] == {"ExchangeSegment": "NSE_EQ", "SecurityId": "1000"}

    # 2. Valid batch of exactly 100 instruments
    max_batch = [("NSE_EQ", f"{1000 + i}") for i in range(100)]
    msg_100 = DhanLiveFeedClient.build_subscription_message(max_batch, request_code=17)
    assert msg_100["InstrumentCount"] == 100

    # 3. Invalid batch of 101 instruments must raise ValueError
    over_limit = [("NSE_EQ", f"{1000 + i}") for i in range(101)]
    with pytest.raises(ValueError) as exc_info:
        DhanLiveFeedClient.build_subscription_message(over_limit, request_code=17)
    assert "cannot exceed 100 instruments" in str(exc_info.value)


def test_reconnect_state_machine_exponential_backoff() -> None:
    policy = ReconnectPolicy(
        initial_delay_seconds=1.0,
        max_delay_seconds=8.0,
        backoff_multiplier=2.0,
        jitter_factor=0.0,  # Zero jitter for exact mathematical assertion
        max_reconnect_attempts=4,
    )
    sm = FeedConnectionStateMachine(policy)

    assert sm.get_state() == FeedConnectionState.DISCONNECTED

    sm.on_connect_start()
    assert sm.get_state() == FeedConnectionState.CONNECTING

    sm.on_connected()
    assert sm.get_state() == FeedConnectionState.CONNECTED
    assert sm.attempts == 0

    # 1st disconnect -> attempt 1 -> delay = 1.0 * 2^0 = 1.0s
    d1 = sm.on_disconnect("Socket drop 1")
    assert sm.get_state() == FeedConnectionState.RECONNECTING
    assert sm.attempts == 1
    assert pytest.approx(d1, 0.01) == 1.0

    # 2nd disconnect -> attempt 2 -> delay = 1.0 * 2^1 = 2.0s
    d2 = sm.on_disconnect("Socket drop 2")
    assert sm.get_state() == FeedConnectionState.RECONNECTING
    assert sm.attempts == 2
    assert pytest.approx(d2, 0.01) == 2.0

    # 3rd disconnect -> attempt 3 -> delay = 1.0 * 2^2 = 4.0s
    d3 = sm.on_disconnect("Socket drop 3")
    assert sm.attempts == 3
    assert pytest.approx(d3, 0.01) == 4.0

    # 4th disconnect -> attempt 4 -> delay = 1.0 * 2^3 = 8.0s
    d4 = sm.on_disconnect("Socket drop 4")
    assert sm.attempts == 4
    assert pytest.approx(d4, 0.01) == 8.0

    # 5th disconnect -> exceeds max_reconnect_attempts (4) -> FAILED
    d5 = sm.on_disconnect("Socket drop 5")
    assert sm.get_state() == FeedConnectionState.FAILED
    assert d5 == -1.0

    # Reset recovers to DISCONNECTED
    sm.reset()
    assert sm.get_state() == FeedConnectionState.DISCONNECTED
    assert sm.attempts == 0


def test_feed_heartbeat_monitor() -> None:
    hb = FeedHeartbeatMonitor(ping_interval_seconds=10.0, pong_timeout_seconds=30.0)

    # Initial time t0
    t0 = 1000.0
    hb.last_ping_sent = t0
    hb.last_pong_received = t0
    hb.last_packet_received = t0

    # At t0 + 5s: should not ping, not stale
    assert not hb.should_send_ping(now=t0 + 5.0)
    assert not hb.is_stale(now=t0 + 5.0)

    # At t0 + 10s: should ping
    assert hb.should_send_ping(now=t0 + 10.0)

    # Record ping sent
    hb.record_ping()

    # At t0 + 25s: not stale yet (< 30s)
    assert not hb.is_stale(now=t0 + 25.0)

    # At t0 + 35s: stale (> 30s without packet or pong)
    assert hb.is_stale(now=t0 + 35.0)

    # Receiving packet resets stall condition
    hb.record_packet()
    assert not hb.is_stale(now=hb.last_packet_received + 5.0)
