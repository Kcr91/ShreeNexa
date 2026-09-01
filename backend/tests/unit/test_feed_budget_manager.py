"""Unit and property tests for ConnectionBudgetManager ceiling enforcement and lease lifecycle."""

from __future__ import annotations

import threading
import time

import hypothesis.strategies as st
import pytest
from app.feedd.budget import (
    ConnectionBudgetConfig,
    ConnectionBudgetExhaustedError,
    ConnectionBudgetManager,
    ConnectionLease,
    PoolMode,
    SocketType,
)
from hypothesis import given, settings


def test_shared_pool_ceiling_enforcement() -> None:
    """Verify shared pool hard ceiling of 5 sockets (3 feed / 2 depth)."""
    cfg = ConnectionBudgetConfig(
        pool_mode=PoolMode.SHARED,
        total_capacity=5,
        feed_capacity=3,
        depth_capacity=2,
        acquire_timeout_seconds=0.01,
    )
    mgr = ConnectionBudgetManager(config=cfg)

    # Acquire 3 feed sockets
    f1 = mgr.acquire(SocketType.FEED)
    f2 = mgr.acquire(SocketType.FEED)
    f3 = mgr.acquire(SocketType.FEED)
    assert len([f1, f2, f3]) == 3

    # 4th feed should fail (feed sub-limit 3 reached)
    with pytest.raises(ConnectionBudgetExhaustedError) as exc_info:
        mgr.acquire(SocketType.FEED)
    assert exc_info.value.socket_type == SocketType.FEED
    assert exc_info.value.active_feed == 3

    # Acquire 2 depth sockets
    d1 = mgr.acquire(SocketType.DEPTH)
    d2 = mgr.acquire(SocketType.DEPTH)
    assert len([d1, d2]) == 2

    # Now total is 5/5. Attempting ANY further connection MUST fail
    with pytest.raises(ConnectionBudgetExhaustedError) as exc_info:
        mgr.acquire(SocketType.DEPTH)
    assert exc_info.value.total_active == 5

    # Status check
    status = mgr.get_status()
    assert status.total_active == 5
    assert status.active_feed == 3
    assert status.active_depth == 2
    assert status.available_feed == 0
    assert status.available_depth == 0


def test_independent_pool_mode() -> None:
    """Verify independent pools allow 5 feed and 5 depth connections simultaneously."""
    cfg = ConnectionBudgetConfig(
        pool_mode=PoolMode.INDEPENDENT,
        total_capacity=10,
        feed_capacity=5,
        depth_capacity=5,
        acquire_timeout_seconds=0.01,
    )
    mgr = ConnectionBudgetManager(config=cfg)

    feeds = [mgr.acquire(SocketType.FEED) for _ in range(5)]
    depths = [mgr.acquire(SocketType.DEPTH) for _ in range(5)]
    assert len(feeds) == 5
    assert len(depths) == 5

    # 6th feed or 6th depth fails
    with pytest.raises(ConnectionBudgetExhaustedError):
        mgr.acquire(SocketType.FEED)
    with pytest.raises(ConnectionBudgetExhaustedError):
        mgr.acquire(SocketType.DEPTH)


def test_idempotent_release_and_cleanup() -> None:
    """Verify releasing a lease is idempotent and correctly restores capacity."""
    mgr = ConnectionBudgetManager()
    l1 = mgr.acquire(SocketType.FEED)

    assert mgr.get_status().total_active == 1
    assert mgr.release(l1) is True
    assert mgr.get_status().total_active == 0

    # Second release of the same lease returns False and does not affect counts
    assert mgr.release(l1) is False
    assert mgr.get_status().total_active == 0


def test_sync_context_manager() -> None:
    """Verify context manager acquisition and automatic release on exit."""
    mgr = ConnectionBudgetManager()
    assert mgr.get_status().total_active == 0

    with mgr.lease(SocketType.FEED) as lease:
        assert isinstance(lease, ConnectionLease)
        assert mgr.get_status().total_active == 1

    assert mgr.get_status().total_active == 0


@pytest.mark.anyio
async def test_async_lease_lifecycle() -> None:
    """Verify asynchronous acquire, release, and async context manager."""
    mgr = ConnectionBudgetManager()
    assert mgr.get_status().total_active == 0

    async with mgr.lease_async(SocketType.DEPTH) as lease:
        assert isinstance(lease, ConnectionLease)
        assert mgr.get_status().active_depth == 1

    assert mgr.get_status().active_depth == 0


def test_acquire_blocks_and_unblocks_on_release() -> None:
    """Verify acquire blocks until an existing connection is released."""
    cfg = ConnectionBudgetConfig(
        pool_mode=PoolMode.SHARED,
        total_capacity=1,
        feed_capacity=1,
        depth_capacity=1,
        acquire_timeout_seconds=2.0,
    )
    mgr = ConnectionBudgetManager(config=cfg)
    l1 = mgr.acquire(SocketType.FEED)

    acquired_second = threading.Event()
    second_lease: list[ConnectionLease] = []

    def background_acquire() -> None:
        lease = mgr.acquire(SocketType.FEED, timeout=2.0)
        second_lease.append(lease)
        acquired_second.set()

    t = threading.Thread(target=background_acquire)
    t.start()

    time.sleep(0.05)
    assert not acquired_second.is_set()

    # Release l1
    mgr.release(l1)
    t.join(timeout=1.0)
    assert acquired_second.is_set()
    assert len(second_lease) == 1
    mgr.release(second_lease[0])


# Hypothesis Property Test: Invariant that active connections <= total capacity
@given(
    actions=st.lists(
        st.tuples(
            st.sampled_from(["acquire_feed", "acquire_depth", "release_random"]),
            st.floats(min_value=0.001, max_value=0.01),
        ),
        min_size=1,
        max_size=50,
    )
)
@settings(max_examples=40, deadline=None)
def test_hypothesis_never_exceeds_ceiling(actions: list[tuple[str, float]]) -> None:
    """Property test: random sequences of operations never violate configured ceilings."""
    cfg = ConnectionBudgetConfig(
        pool_mode=PoolMode.SHARED,
        total_capacity=5,
        feed_capacity=3,
        depth_capacity=2,
        acquire_timeout_seconds=0.001,
    )
    mgr = ConnectionBudgetManager(config=cfg)
    active_leases: list[ConnectionLease] = []

    for action, _ in actions:
        if action == "acquire_feed":
            try:
                lease = mgr.acquire(SocketType.FEED, timeout=0.001)
                active_leases.append(lease)
            except ConnectionBudgetExhaustedError:
                pass
        elif action == "acquire_depth":
            try:
                lease = mgr.acquire(SocketType.DEPTH, timeout=0.001)
                active_leases.append(lease)
            except ConnectionBudgetExhaustedError:
                pass
        elif action == "release_random" and active_leases:
            to_rel = active_leases.pop(0)
            mgr.release(to_rel)

        # Invariant checks at every single step:
        status = mgr.get_status()
        assert status.total_active <= 5, f"Ceiling breached: {status.total_active} > 5"
        assert status.active_feed <= 3, f"Feed capacity breached: {status.active_feed} > 3"
        assert status.active_depth <= 2, f"Depth capacity breached: {status.active_depth} > 2"
        assert status.total_active == status.active_feed + status.active_depth
