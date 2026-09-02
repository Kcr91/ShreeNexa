"""Capital allocation validation, initial splits, and rebalance transfer logic."""

from __future__ import annotations

from datetime import datetime

from app.portfolio.models import (
    PortfolioAllocationConfig,
    RebalanceTransferRecord,
    RebalanceTrigger,
)

TOLERANCE = 1e-6


class AllocationValidationError(Exception):
    """Raised when portfolio allocation specification violates system invariants."""


def validate_allocation_config(config: PortfolioAllocationConfig) -> None:
    """Validate that strategy allocation weights sum to 1.0 and each weight is positive."""
    if not config.allocations:
        raise AllocationValidationError("Portfolio must contain at least one strategy allocation.")

    if config.total_initial_capital <= 0:
        raise AllocationValidationError(
            f"Total initial capital must be strictly positive, got {config.total_initial_capital}"
        )

    total_weight = 0.0
    for alloc in config.allocations:
        if alloc.weight <= 0.0:
            raise AllocationValidationError(
                f"Strategy '{alloc.strategy_id}' allocation weight must be > 0, got {alloc.weight}"
            )
        total_weight += alloc.weight

    if abs(total_weight - 1.0) > TOLERANCE:
        raise AllocationValidationError(
            f"Strategy allocation weights must sum to 1.0 (within {TOLERANCE}), "
            f"got total sum: {total_weight:.8f}"
        )


def split_initial_capital(config: PortfolioAllocationConfig) -> dict[str, float]:
    """Deterministically slice total portfolio capital according to strategy weights.

    Guarantees no double-spend: sum of allocated capital equals total initial capital.
    """
    validate_allocation_config(config)

    allocations_map: dict[str, float] = {}
    accumulated_cap = 0.0
    total_cap = config.total_initial_capital

    for i, alloc in enumerate(config.allocations):
        if i == len(config.allocations) - 1:
            # Last allocation absorbs any fractional cent rounding drift
            cap = round(total_cap - accumulated_cap, 4)
        else:
            cap = round(total_cap * alloc.weight, 4)
            accumulated_cap += cap

        allocations_map[alloc.strategy_id] = cap

    # Invariant: sum of split capital must equal initial capital
    assert abs(sum(allocations_map.values()) - total_cap) <= 1e-4, (
        f"Allocation split {sum(allocations_map.values())} violates total capital {total_cap}"
    )

    return allocations_map


def compute_rebalance_transfers(
    *,
    current_equities: dict[str, float],
    target_weights: dict[str, float],
    trigger: RebalanceTrigger,
    timestamp: datetime,
) -> list[RebalanceTransferRecord]:
    """Compute rebalancing cash transfers between sub-strategy books.

    Enforces the zero-sum capital conservation invariant: sum of delta_cash == 0.
    """
    total_equity = sum(current_equities.values())
    if total_equity <= 0.0:
        return []

    transfers: list[RebalanceTransferRecord] = []
    accumulated_target = 0.0
    items = list(target_weights.items())

    for i, (strat_id, weight) in enumerate(items):
        curr_eq = current_equities.get(strat_id, 0.0)
        if i == len(items) - 1:
            # Final strategy absorbs rounding to conserve total portfolio equity
            target_cap = round(total_equity - accumulated_target, 4)
        else:
            target_cap = round(total_equity * weight, 4)
            accumulated_target += target_cap

        delta_cash = round(target_cap - curr_eq, 4)

        transfers.append(
            RebalanceTransferRecord(
                timestamp=timestamp,
                trigger=trigger,
                strategy_id=strat_id,
                pre_rebalance_capital=curr_eq,
                target_capital=target_cap,
                delta_cash=delta_cash,
            )
        )

    # Invariant: zero-sum transfer (no money created or destroyed)
    net_transfer = sum(t.delta_cash for t in transfers)
    assert abs(net_transfer) <= 1e-3, (
        f"Rebalance transfer broke capital conservation with net drift {net_transfer}"
    )

    return transfers
