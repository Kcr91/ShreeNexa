"""StrategyIR schema migration utilities and legacy version upgrades."""

from __future__ import annotations

from typing import Any

from app.strategy.ir import StrategyIR


class MigrationError(Exception):
    """Raised when an IR payload cannot be migrated to the target version."""


def migrate_strategy_ir(data: dict[str, Any], target_version: int = 1) -> StrategyIR:
    """Migrate an arbitrary or legacy StrategyIR dictionary to the target version schema.

    Args:
        data: Dictionary payload of strategy IR.
        target_version: Desired schema version (default 1).

    Returns:
        Validated `StrategyIR` instance conforming to target schema.

    Raises:
        MigrationError: If data cannot be upgraded.
    """
    if not isinstance(data, dict):
        raise MigrationError(f"Expected dictionary payload, got {type(data).__name__}")

    raw = dict(data)
    current_version = raw.get("ir_version", 1)

    if not isinstance(current_version, int) or current_version < 1:
        raw["ir_version"] = 1
        current_version = 1

    if current_version > target_version:
        raise MigrationError(
            f"Cannot downgrade StrategyIR version {current_version} to {target_version}"
        )

    # Legacy V0/V1 normalization rules
    if "horizon" not in raw:
        raw["horizon"] = "swing"

    if "strategy_type" not in raw:
        raw["strategy_type"] = "trend_following"

    if "kind" not in raw:
        raw["kind"] = "stock"

    # Universe normalization
    univ = raw.get("universe")
    if isinstance(univ, list):
        # Convert legacy raw list of symbols to StaticUniverse
        instruments = []
        for item in univ:
            if isinstance(item, str):
                instruments.append({"segment": "NSE_EQ", "security_id": item})
            elif isinstance(item, dict):
                instruments.append(item)
        raw["universe"] = {"type": "static", "instruments": instruments}
    elif isinstance(univ, dict) and "type" not in univ:
        if "instruments" in univ:
            univ["type"] = "static"
        elif "watchlist_id" in univ:
            univ["type"] = "watchlist"
        elif "index_name" in univ:
            univ["type"] = "index"

    # Sizing normalization
    sizing = raw.get("sizing")
    if isinstance(sizing, (int, float)):
        raw["sizing"] = {"type": "pct_capital", "pct": float(sizing)}

    try:
        return StrategyIR.from_dict(raw)
    except Exception as exc:
        raise MigrationError(
            f"Failed to migrate StrategyIR to version {target_version}: {exc}"
        ) from exc
