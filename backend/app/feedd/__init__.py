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

__all__ = [
    "BudgetStatus",
    "ConnectionBudgetConfig",
    "ConnectionBudgetExhaustedError",
    "ConnectionBudgetManager",
    "ConnectionLease",
    "PoolMode",
    "SocketType",
    "get_connection_budget_manager",
    "load_budget_config",
]
