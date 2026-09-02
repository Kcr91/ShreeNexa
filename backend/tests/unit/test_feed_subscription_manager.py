"""Unit tests for feed subscription manager across the connection budget."""

from __future__ import annotations

import pytest
from app.feedd import (
    ConnectionBudgetConfig,
    ConnectionBudgetManager,
    InstrumentKey,
    PoolMode,
    SubscriptionCapacityExceededError,
    SubscriptionManager,
    SubscriptionMode,
    SubscriptionPriority,
)


def _make_manager(
    total_capacity: int = 5,
    feed_capacity: int = 3,
    max_per_socket: int = 5000,
    max_per_msg: int = 100,
) -> SubscriptionManager:
    config = ConnectionBudgetConfig(
        pool_mode=PoolMode.SHARED,
        total_capacity=total_capacity,
        feed_capacity=feed_capacity,
        depth_capacity=2,
    )
    budget = ConnectionBudgetManager(config)
    return SubscriptionManager(
        budget_manager=budget,
        max_instruments_per_socket=max_per_socket,
        max_instruments_per_message=max_per_msg,
    )


def test_message_batching_constraint_le_100() -> None:
    manager = _make_manager()

    # Subscribing 350 instruments
    instruments = [("NSE_EQ", f"{1000 + i}") for i in range(350)]
    messages = manager.subscribe(instruments, requester_id="widget_scanner")

    assert len(messages) == 4
    assert [m["InstrumentCount"] for m in messages] == [100, 100, 100, 50]
    for m in messages:
        assert m["InstrumentCount"] <= 100
        assert len(m["InstrumentList"]) == m["InstrumentCount"]
        assert m["RequestCode"] == int(SubscriptionMode.FULL)


def test_socket_capacity_spillover_to_next_socket() -> None:
    # Use smaller socket capacity of 5 instruments to test spillover
    manager = _make_manager(total_capacity=5, feed_capacity=3, max_per_socket=5)

    inst_batch1 = [("NSE_EQ", f"{100 + i}") for i in range(5)]
    inst_batch2 = [("NSE_EQ", f"{200 + i}") for i in range(3)]

    # 1. First 5 go to socket 1
    manager.subscribe(inst_batch1, requester_id="user_1")
    assert len(manager.sockets) == 1
    first_socket_id = next(iter(manager.sockets))
    assert manager.sockets[first_socket_id].subscribed_count == 5

    # 2. Next 3 spill over to socket 2
    manager.subscribe(inst_batch2, requester_id="user_1")
    assert len(manager.sockets) == 2
    second_socket_id = list(manager.sockets.keys())[1]
    assert manager.sockets[second_socket_id].subscribed_count == 3
    assert manager.sockets[first_socket_id].subscribed_count == 5


def test_budget_exhaustion_raises_capacity_error() -> None:
    # 2 sockets total capacity, each holds 2 instruments (max 4 instruments)
    manager = _make_manager(total_capacity=2, feed_capacity=2, max_per_socket=2)

    manager.subscribe([("NSE_EQ", "1"), ("NSE_EQ", "2")], requester_id="w1")
    manager.subscribe([("NSE_EQ", "3"), ("NSE_EQ", "4")], requester_id="w2")
    assert len(manager.sockets) == 2

    # Attempting to subscribe 5th instrument when both sockets and budget are full
    with pytest.raises(SubscriptionCapacityExceededError):
        manager.subscribe([("NSE_EQ", "5")], requester_id="w3")


def test_deduplication_and_multi_subscriber_ref_counting() -> None:
    manager = _make_manager()

    # Widget A subscribes to Reliance with LOW priority
    msg_a = manager.subscribe(
        [("NSE_EQ", "2885")],
        requester_id="widget_watchlist",
        priority=SubscriptionPriority.LOW,
    )
    key = InstrumentKey("NSE_EQ", "2885")
    assert len(msg_a) == 1
    item = manager.subscriptions[key]
    assert item.priority.value == SubscriptionPriority.LOW.value
    assert item.subscribers == {"widget_watchlist"}

    # Widget B subscribes to Reliance with HIGH priority
    msg_b = manager.subscribe(
        [("NSE_EQ", "2885")],
        requester_id="widget_chart",
        priority=SubscriptionPriority.HIGH,
    )
    # Already subscribed, no new wire payload required unless mode upgraded
    assert len(msg_b) == 0
    assert item.priority.value == SubscriptionPriority.HIGH.value
    assert item.subscribers == {"widget_watchlist", "widget_chart"}

    # Widget A unsubscribes -> instrument still needed by Widget B
    unsub_a = manager.unsubscribe([("NSE_EQ", "2885")], requester_id="widget_watchlist")
    assert len(unsub_a) == 0
    assert key in manager.subscriptions

    # Widget B unsubscribes -> instrument released and unsub message emitted
    unsub_b = manager.unsubscribe([("NSE_EQ", "2885")], requester_id="widget_chart")
    assert len(unsub_b) == 1
    assert unsub_b[0]["IsUnsubscribe"] is True
    assert unsub_b[0]["InstrumentCount"] == 1
    assert key not in manager.subscriptions


def test_reconnect_resubscribes_in_priority_order() -> None:
    manager = _make_manager(max_per_msg=2)

    # Subscribe 4 instruments with varying priority
    manager.subscribe([("NSE_EQ", "LOW_1")], "w", priority=SubscriptionPriority.LOW)
    manager.subscribe([("NSE_EQ", "CRIT_1")], "w", priority=SubscriptionPriority.CRITICAL)
    manager.subscribe([("NSE_EQ", "HIGH_1")], "w", priority=SubscriptionPriority.HIGH)
    manager.subscribe([("NSE_EQ", "MED_1")], "w", priority=SubscriptionPriority.MEDIUM)

    socket_id = next(iter(manager.sockets))

    # Disconnect
    manager.on_socket_disconnect(socket_id, reason="Network reset")
    assert manager.sockets[socket_id].is_connected is False
    assert manager.sockets[socket_id].reconnect_count == 1

    # Reconnect
    resub_msgs = manager.on_socket_reconnect(socket_id)
    assert manager.sockets[socket_id].is_connected is True

    # Check that batches are chunked by max_per_msg (2)
    assert len(resub_msgs) == 2
    # First batch must contain CRITICAL and HIGH
    first_batch_ids = [inst["SecurityId"] for inst in resub_msgs[0]["InstrumentList"]]
    assert first_batch_ids == ["CRIT_1", "HIGH_1"]
    # Second batch must contain MEDIUM and LOW
    second_batch_ids = [inst["SecurityId"] for inst in resub_msgs[1]["InstrumentList"]]
    assert second_batch_ids == ["MED_1", "LOW_1"]


def test_health_status_aggregation() -> None:
    manager = _make_manager()
    manager.subscribe([("NSE_EQ", "1333"), ("NSE_EQ", "2885")], requester_id="test")

    status = manager.get_health_status()
    assert status["total_subscribed"] == 2
    assert status["active_sockets"] == 1
    assert status["max_per_socket"] == 5000
    assert status["max_per_message"] == 100
    assert len(status["sockets"]) == 1
    assert status["sockets"][0]["subscribed_count"] == 2
    assert status["sockets"][0]["is_connected"] is True
