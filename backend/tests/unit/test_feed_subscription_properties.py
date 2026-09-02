"""Property-based tests for feed subscription manager invariants using Hypothesis."""

from __future__ import annotations

from typing import cast

from app.feedd import (
    ConnectionBudgetConfig,
    ConnectionBudgetManager,
    PoolMode,
    SubscriptionCapacityExceededError,
    SubscriptionManager,
    SubscriptionMode,
    SubscriptionPriority,
)
from hypothesis import given, settings
from hypothesis import strategies as st


@st.composite
def subscription_action_strategy(draw: st.DrawFn) -> list[dict[str, object]]:
    """Generate a random sequence of subscribe and unsubscribe operations."""
    num_actions = draw(st.integers(min_value=5, max_value=25))
    actions: list[dict[str, object]] = []

    # Pool of 50 possible instruments
    universe = [(f"SEG_{i % 3}", f"SEC_{i}") for i in range(50)]
    requesters = ["widget_chart", "widget_depth", "widget_scanner", "strategy_alpha"]

    for _ in range(num_actions):
        action_type = draw(st.sampled_from(["subscribe", "unsubscribe", "reconnect"]))
        req = draw(st.sampled_from(requesters))

        if action_type in ("subscribe", "unsubscribe"):
            batch_size = draw(st.integers(min_value=1, max_value=20))
            chosen_instruments = draw(
                st.lists(st.sampled_from(universe), min_size=batch_size, max_size=batch_size)
            )
            prio = draw(
                st.sampled_from([
                    SubscriptionPriority.CRITICAL,
                    SubscriptionPriority.HIGH,
                    SubscriptionPriority.MEDIUM,
                    SubscriptionPriority.LOW,
                ])
            )
            actions.append({
                "type": action_type,
                "instruments": chosen_instruments,
                "requester": req,
                "priority": prio,
            })
        else:
            actions.append({"type": "reconnect"})

    return actions


@given(actions=subscription_action_strategy())
@settings(max_examples=50, deadline=None)
def test_subscription_invariants_under_arbitrary_operations(
    actions: list[dict[str, object]],
) -> None:
    # Small limits to force frequent socket allocations, message chunking, and boundary transitions
    max_socket_capacity = 15
    max_msg_capacity = 5

    budget_config = ConnectionBudgetConfig(
        pool_mode=PoolMode.SHARED,
        total_capacity=5,
        feed_capacity=4,
        depth_capacity=1,
    )
    budget = ConnectionBudgetManager(budget_config)
    manager = SubscriptionManager(
        budget_manager=budget,
        max_instruments_per_socket=max_socket_capacity,
        max_instruments_per_message=max_msg_capacity,
    )

    for action in actions:
        action_type = action["type"]

        if action_type == "subscribe":
            instruments = cast(list[tuple[str, str]], action["instruments"])
            requester = str(action["requester"])
            priority = cast(SubscriptionPriority, action["priority"])
            try:
                msgs = manager.subscribe(
                    instruments,
                    requester_id=requester,
                    priority=priority,
                    mode=SubscriptionMode.FULL,
                )
                # Invariant 1: Outbound message count <= max_instruments_per_message
                for m in msgs:
                    assert m["InstrumentCount"] <= max_msg_capacity
                    assert len(m["InstrumentList"]) <= max_msg_capacity
                    assert len(m["InstrumentList"]) == m["InstrumentCount"]
            except SubscriptionCapacityExceededError:
                # Capacity gracefully exhausted: state must remain intact
                pass

        elif action_type == "unsubscribe":
            instruments = cast(list[tuple[str, str]], action["instruments"])
            requester = str(action["requester"])
            unsub_msgs = manager.unsubscribe(instruments, requester_id=requester)
            for m in unsub_msgs:
                assert m["InstrumentCount"] <= max_msg_capacity
                assert len(m["InstrumentList"]) <= max_msg_capacity

        elif action_type == "reconnect":
            if manager.sockets:
                sock_id = next(iter(manager.sockets))
                manager.on_socket_disconnect(sock_id)
                resub_msgs = manager.on_socket_reconnect(sock_id)
                for m in resub_msgs:
                    assert m["InstrumentCount"] <= max_msg_capacity
                    assert len(m["InstrumentList"]) <= max_msg_capacity

        # Invariant 2: No socket ever exceeds max_instruments_per_socket
        for sock in manager.sockets.values():
            assert len(sock.instruments) <= max_socket_capacity

        # Invariant 3: No duplicate instruments across sockets
        seen_keys = set()
        for sock in manager.sockets.values():
            for k in sock.instruments:
                assert k not in seen_keys, f"Instrument {k} present in multiple sockets!"
                seen_keys.add(k)

        # Invariant 4: Subscriptions mapping matches exactly the sum of sockets' instruments
        assert seen_keys == set(manager.subscriptions.keys())
