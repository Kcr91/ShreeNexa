"""Strategy Definition Parser & Validator Module."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.strategy.models import StrategyDefinition


def parse_and_validate_strategy(config_json: dict[str, Any]) -> dict[str, Any]:
    """Validate and parse a raw strategy configuration dictionary.

    Returns:
        dict containing:
            - 'valid': bool
            - 'strategy': StrategyDefinition instance (if valid)
            - 'errors': list of validation error strings
            - 'warnings': list of non-fatal warnings
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        parsed = StrategyDefinition.model_validate(config_json)
    except ValidationError as e:
        for err in e.errors():
            loc = " -> ".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", "Invalid field")
            errors.append(f"{loc}: {msg}")
        return {"valid": False, "strategy": None, "errors": errors, "warnings": warnings}

    # Additional semantic checks
    # 1. Stop-loss validation
    sl = parsed.part_3_stoploss
    if sl.sl_type == "PERCENTAGE" and (sl.percentage_val is None or sl.percentage_val <= 0):
        errors.append("part_3_stoploss.percentage_val must be greater than 0 for PERCENTAGE SL.")
    elif sl.sl_type == "POINTS" and (sl.points_val is None or sl.points_val <= 0):
        errors.append("part_3_stoploss.points_val must be greater than 0 for POINTS SL.")

    # 2. Scope validation
    scope = parsed.part_1_scope
    if parsed.strategy_type == "OPTION" and not scope.underlying_symbol:
        warnings.append(
            "underlying_symbol is empty for OPTION strategy; defaulting to NIFTY in execution."
        )

    # 3. Targets validation
    targets = parsed.part_4_exit.targets
    total_exit_lots = sum(t.exit_lots_percentage for t in targets)
    if targets and total_exit_lots > 100.0:
        errors.append(f"Sum of target exit lot percentages ({total_exit_lots}%) exceeds 100%.")

    return {
        "valid": len(errors) == 0,
        "strategy": parsed if len(errors) == 0 else None,
        "errors": errors,
        "warnings": warnings,
    }
