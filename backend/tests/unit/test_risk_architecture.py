"""Exhaustive AST architecture test verifying that no execution path reaches

DhanBroker without passing pre-trade risk filtering (QA-17 / F12.4).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from app.dhan.orders import (
    DhanOrderRequest,
    ExchangeSegment,
    OrderType,
    ProductType,
    TransactionType,
)
from app.engine.gateway import get_risk_filtered_broker
from app.engine.risk import KillSwitchActiveError, RiskCheckFailedError, RiskLimits


def test_ast_prohibits_direct_dhan_broker_instantiation() -> None:
    """Walk the AST of all backend/app/ modules.

    Fail if any code outside app/engine/gateway.py or app/engine/broker.py
    instantiates DhanBroker directly.
    """
    repo_root = Path(__file__).resolve().parents[3]
    app_dir = repo_root / "backend" / "app"
    assert app_dir.is_dir(), f"Expected directory {app_dir}"

    allowed_modules = {
        app_dir / "engine" / "broker.py",
        app_dir / "engine" / "gateway.py",
        app_dir / "engine" / "risk.py",
    }

    violations: list[str] = []

    for py_file in app_dir.rglob("*.py"):
        if py_file in allowed_modules:
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception as exc:
            violations.append(f"{py_file}: Parse error: {exc}")
            continue

        for node in ast.walk(tree):
            # Check Call nodes: DhanBroker(...) or broker.DhanBroker(...)
            if isinstance(node, ast.Call):
                func = node.func
                called_name = None
                if isinstance(func, ast.Name):
                    called_name = func.id
                elif isinstance(func, ast.Attribute):
                    called_name = func.attr

                if called_name == "DhanBroker":
                    rel_path = py_file.relative_to(repo_root)
                    violations.append(
                        f"{rel_path}:{node.lineno}: Direct instantiation of DhanBroker "
                        "bypasses risk filtering. "
                        "Use app.engine.gateway.get_risk_filtered_broker()."
                    )

    assert not violations, (
        "Architecture invariant violated: DhanBroker instantiated outside gateway:\n"
        + "\n".join(violations)
    )


def test_ast_prohibits_raw_place_order_outside_risk_layer() -> None:
    """Walk the AST of all backend/app/ modules.

    Fail if any code outside broker.py or risk.py invokes raw .place_order
    directly on an unshielded broker.
    """
    repo_root = Path(__file__).resolve().parents[3]
    app_dir = repo_root / "backend" / "app"

    allowed_place_order_callers = {
        app_dir / "engine" / "broker.py",
        app_dir / "engine" / "risk.py",
        app_dir / "api" / "orders.py",  # invokes risk_filtered.place_order
    }

    violations: list[str] = []

    for py_file in app_dir.rglob("*.py"):
        if py_file in allowed_place_order_callers:
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception as exc:
            violations.append(f"{py_file}: Parse error: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("place_order", "place_sliced_order"):
                    rel_path = py_file.relative_to(repo_root)
                    violations.append(
                        f"{rel_path}:{node.lineno}: Call to .{node.func.attr}() outside "
                        f"authorized risk-shielded execution boundary."
                    )

    assert not violations, (
        "Architecture invariant violated: direct order placement found:\n"
        + "\n".join(violations)
    )


def test_gateway_enforces_risk_filters_and_killswitch() -> None:
    """Verify that get_risk_filtered_broker returns a broker that blocks violations."""
    limits = RiskLimits(max_order_value=50_000.0)
    risk_broker = get_risk_filtered_broker(
        limits=limits,
        enable_live_trading=False,
    )

    huge_order = DhanOrderRequest(
        securityId="1333",
        exchangeSegment=ExchangeSegment.NSE_EQ,
        transactionType=TransactionType.BUY,
        orderType=OrderType.LIMIT,
        productType=ProductType.INTRADAY,
        quantity=1000,
        price=100.0,  # 1000 * 100 = 100,000 > 50,000 limit
    )

    with pytest.raises(RiskCheckFailedError) as exc_info:
        risk_broker.place_order(huge_order)
    assert "exceeds max_order_value cap" in str(exc_info.value)

    # Halt the risk engine and verify all subsequent orders are blocked
    risk_broker.risk_engine.halt("Simulated crash trigger")
    small_order = DhanOrderRequest(
        securityId="1333",
        exchangeSegment=ExchangeSegment.NSE_EQ,
        transactionType=TransactionType.BUY,
        orderType=OrderType.LIMIT,
        productType=ProductType.INTRADAY,
        quantity=1,
        price=100.0,
    )
    with pytest.raises(KillSwitchActiveError) as kill_exc:
        risk_broker.place_order(small_order)
    assert "emergency kill switch" in str(kill_exc.value)
