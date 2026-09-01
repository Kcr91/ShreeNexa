"""Central connection-budget manager for Dhan market-feed and depth sockets."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BUDGET_CONFIG_PATH = REPO_ROOT / "config" / "feed_budget.yaml"


class SocketType(StrEnum):
    """Supported WebSocket connection types for Dhan."""

    FEED = "feed"
    DEPTH = "depth"


class PoolMode(StrEnum):
    """Connection allocation strategy."""

    SHARED = "shared"
    INDEPENDENT = "independent"


class ConnectionBudgetConfig(BaseModel):
    """Configuration governing Dhan WebSocket capacity and pool splits."""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    updated_at: str | None = None
    pool_mode: PoolMode = PoolMode.SHARED
    total_capacity: int = Field(default=5, ge=1)
    feed_capacity: int = Field(default=3, ge=1)
    depth_capacity: int = Field(default=2, ge=1)
    acquire_timeout_seconds: float = Field(default=5.0, ge=0.0)

    @field_validator("feed_capacity", "depth_capacity")
    @classmethod
    def validate_individual_capacity(cls, val: int, info: Any) -> int:
        return val


class ConnectionLease(BaseModel):
    """Active lease token representing an allocated WebSocket connection."""

    model_config = ConfigDict(frozen=True)

    lease_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    socket_type: SocketType
    allocated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class BudgetStatus(BaseModel):
    """Snapshot of connection budget capacity, usage, and active leases."""

    pool_mode: PoolMode
    total_capacity: int
    feed_capacity: int
    depth_capacity: int
    active_feed: int
    active_depth: int
    total_active: int
    available_feed: int
    available_depth: int
    active_leases: list[ConnectionLease]


class ConnectionBudgetExhaustedError(RuntimeError):
    """Raised when an attempt to allocate a WebSocket connection exceeds configured budget."""

    def __init__(
        self,
        socket_type: SocketType,
        active_feed: int,
        active_depth: int,
        total_active: int,
        limit: int,
        pool_mode: PoolMode,
        detail: str | None = None,
    ) -> None:
        self.socket_type = socket_type
        self.active_feed = active_feed
        self.active_depth = active_depth
        self.total_active = total_active
        self.limit = limit
        self.pool_mode = pool_mode
        msg = (
            f"Dhan WebSocket connection budget exhausted for socket type '{socket_type.value}'. "
            f"Active: {total_active}/{limit} "
            f"(feed={active_feed}, depth={active_depth}, mode={pool_mode.value})."
        )
        if detail:
            msg += f" {detail}"
        super().__init__(msg)


def load_budget_config(config_path: Path | str | None = None) -> ConnectionBudgetConfig:
    """Load connection budget configuration from YAML file or return defaults."""
    target_path = Path(config_path) if config_path else DEFAULT_BUDGET_CONFIG_PATH
    if not target_path.is_file():
        logger.warning(
            "Budget config file not found at %s; using conservative built-in defaults",
            target_path,
        )
        return ConnectionBudgetConfig()

    try:
        content = target_path.read_text(encoding="utf-8")
        raw: Any = yaml.safe_load(content)
        if isinstance(raw, dict):
            return ConnectionBudgetConfig.model_validate(raw)
        return ConnectionBudgetConfig()
    except Exception as exc:
        logger.error("Failed to parse budget config from %s: %s; using defaults", target_path, exc)
        return ConnectionBudgetConfig()


class ConnectionBudgetManager:
    """Thread-safe and async-aware manager for Dhan WebSocket connections.

    Enforces hard ceiling limits across market-feed and depth sockets, preventing
    the 6th socket bug (where opening a 6th socket silently terminates the 1st).
    """

    def __init__(self, config: ConnectionBudgetConfig | None = None) -> None:
        self._config = config or load_budget_config()
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._active_leases: dict[str, ConnectionLease] = {}

    @property
    def config(self) -> ConnectionBudgetConfig:
        """Active configuration."""
        with self._lock:
            return self._config

    def _can_allocate_locked(self, st: SocketType) -> bool:
        feed_count = sum(
            1 for item in self._active_leases.values() if item.socket_type == SocketType.FEED
        )
        depth_count = sum(
            1 for item in self._active_leases.values() if item.socket_type == SocketType.DEPTH
        )
        total_count = feed_count + depth_count

        if self._config.pool_mode == PoolMode.SHARED:
            if total_count >= self._config.total_capacity:
                return False
            if st == SocketType.FEED and feed_count >= self._config.feed_capacity:
                return False
            if st == SocketType.DEPTH and depth_count >= self._config.depth_capacity:
                return False
            return True
        else:
            # Independent pools
            if st == SocketType.FEED and feed_count >= self._config.feed_capacity:
                return False
            if st == SocketType.DEPTH and depth_count >= self._config.depth_capacity:
                return False
            return True

    def acquire(
        self,
        socket_type: SocketType | str,
        timeout: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConnectionLease:
        """Acquire a connection lease synchronously. Blocks up to `timeout` seconds if full."""
        st = SocketType(socket_type)
        wait_timeout = timeout if timeout is not None else self._config.acquire_timeout_seconds
        deadline = time.monotonic() + wait_timeout if wait_timeout > 0 else 0.0

        with self._condition:
            while not self._can_allocate_locked(st):
                if wait_timeout <= 0.0:
                    self._raise_exhausted(st)
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    self._raise_exhausted(st, detail="Acquisition timed out waiting for capacity.")
                self._condition.wait(timeout=remaining)

            lease = ConnectionLease(
                socket_type=st,
                metadata=metadata or {},
            )
            self._active_leases[lease.lease_id] = lease
            logger.info(
                "Allocated Dhan %s socket lease %s (active: %d)",
                st.value,
                lease.lease_id,
                len(self._active_leases),
            )
            return lease

    async def acquire_async(
        self,
        socket_type: SocketType | str,
        timeout: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConnectionLease:
        """Acquire a connection lease asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.acquire, socket_type, timeout, metadata)

    def release(self, lease_or_id: ConnectionLease | str) -> bool:
        """Release an allocated connection lease. Idempotent and thread-safe."""
        lease_id = (
            lease_or_id.lease_id if isinstance(lease_or_id, ConnectionLease) else str(lease_or_id)
        )
        with self._condition:
            if lease_id in self._active_leases:
                removed = self._active_leases.pop(lease_id)
                self._condition.notify_all()
                logger.info(
                    "Released Dhan %s socket lease %s (active: %d)",
                    removed.socket_type.value,
                    lease_id,
                    len(self._active_leases),
                )
                return True
            return False

    async def release_async(self, lease_or_id: ConnectionLease | str) -> bool:
        """Release an allocated connection lease asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.release, lease_or_id)

    @contextmanager
    def lease(
        self,
        socket_type: SocketType | str,
        timeout: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[ConnectionLease]:
        """Synchronous context manager for connection lease lifecycle."""
        token = self.acquire(socket_type=socket_type, timeout=timeout, metadata=metadata)
        try:
            yield token
        finally:
            self.release(token)

    @asynccontextmanager
    async def lease_async(
        self,
        socket_type: SocketType | str,
        timeout: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[ConnectionLease]:
        """Asynchronous context manager for connection lease lifecycle."""
        token = await self.acquire_async(
            socket_type=socket_type, timeout=timeout, metadata=metadata
        )
        try:
            yield token
        finally:
            await self.release_async(token)

    def get_status(self) -> BudgetStatus:
        """Get snapshot of current budget capacity and active leases."""
        with self._lock:
            feed_count = sum(
                1 for item in self._active_leases.values() if item.socket_type == SocketType.FEED
            )
            depth_count = sum(
                1 for item in self._active_leases.values() if item.socket_type == SocketType.DEPTH
            )
            total_count = feed_count + depth_count

            if self._config.pool_mode == PoolMode.SHARED:
                avail_feed = max(
                    0,
                    min(
                        self._config.feed_capacity - feed_count,
                        self._config.total_capacity - total_count,
                    ),
                )
                avail_depth = max(
                    0,
                    min(
                        self._config.depth_capacity - depth_count,
                        self._config.total_capacity - total_count,
                    ),
                )
            else:
                avail_feed = max(0, self._config.feed_capacity - feed_count)
                avail_depth = max(0, self._config.depth_capacity - depth_count)

            return BudgetStatus(
                pool_mode=self._config.pool_mode,
                total_capacity=self._config.total_capacity,
                feed_capacity=self._config.feed_capacity,
                depth_capacity=self._config.depth_capacity,
                active_feed=feed_count,
                active_depth=depth_count,
                total_active=total_count,
                available_feed=avail_feed,
                available_depth=avail_depth,
                active_leases=list(self._active_leases.values()),
            )

    def reset(self) -> None:
        """Clear all active leases and notify waiting callers (used in testing)."""
        with self._condition:
            self._active_leases.clear()
            self._condition.notify_all()

    def _raise_exhausted(self, st: SocketType, detail: str | None = None) -> None:
        feed_count = sum(
            1 for item in self._active_leases.values() if item.socket_type == SocketType.FEED
        )
        depth_count = sum(
            1 for item in self._active_leases.values() if item.socket_type == SocketType.DEPTH
        )
        total_count = feed_count + depth_count
        if self._config.pool_mode == PoolMode.SHARED:
            limit = self._config.total_capacity
        else:
            limit = (
                self._config.feed_capacity if st == SocketType.FEED else self._config.depth_capacity
            )
        raise ConnectionBudgetExhaustedError(
            socket_type=st,
            active_feed=feed_count,
            active_depth=depth_count,
            total_active=total_count,
            limit=limit,
            pool_mode=self._config.pool_mode,
            detail=detail,
        )


_GLOBAL_BUDGET_MANAGER: ConnectionBudgetManager | None = None
_GLOBAL_LOCK = threading.Lock()


def get_connection_budget_manager(
    config: ConnectionBudgetConfig | None = None,
) -> ConnectionBudgetManager:
    """Retrieve or initialize the global connection budget manager singleton."""
    global _GLOBAL_BUDGET_MANAGER
    with _GLOBAL_LOCK:
        if _GLOBAL_BUDGET_MANAGER is None:
            _GLOBAL_BUDGET_MANAGER = ConnectionBudgetManager(config=config)
        return _GLOBAL_BUDGET_MANAGER
