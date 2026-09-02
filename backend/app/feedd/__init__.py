"""feedd: owns Dhan market-feed/depth connections (per ADR-0002)."""

from app.feedd.budget import (
    BudgetStatus,
    ConnectionBudgetConfig,
    ConnectionBudgetExhaustedError,
    ConnectionBudgetManager,
    ConnectionLease,
    PoolMode,
    SocketType,
    get_connection_budget_manager,
    load_budget_config,
)
from app.feedd.subscriptions import (
    MAX_INSTRUMENTS_PER_MESSAGE,
    MAX_INSTRUMENTS_PER_SOCKET,
    FeedSocketRecord,
    InstrumentKey,
    SubscriptionCapacityExceededError,
    SubscriptionItem,
    SubscriptionManager,
    SubscriptionMode,
    SubscriptionPriority,
)

__all__ = [
    "MAX_INSTRUMENTS_PER_MESSAGE",
    "MAX_INSTRUMENTS_PER_SOCKET",
    "BudgetStatus",
    "ConnectionBudgetConfig",
    "ConnectionBudgetExhaustedError",
    "ConnectionBudgetManager",
    "ConnectionLease",
    "FeedSocketRecord",
    "InstrumentKey",
    "PoolMode",
    "SocketType",
    "SubscriptionCapacityExceededError",
    "SubscriptionItem",
    "SubscriptionManager",
    "SubscriptionMode",
    "SubscriptionPriority",
    "get_connection_budget_manager",
    "load_budget_config",
]
