"""Unit and proof tests for ContinuousReconciler and freeze-on-mismatch policy (F12.5)."""

from __future__ import annotations

import pytest
from app.dhan.models import DhanPosition
from app.dhan.orders import (
    DhanOrderDetail,
    DhanOrderRequest,
    ExchangeSegment,
    OrderStatus,
    OrderType,
    ProductType,
    TransactionType,
)
from app.engine.continuous_recon import (
    ContinuousReconciler,
    IncidentStatus,
    MismatchDimension,
)
from app.engine.order_reconciler import ReconciledOrderState
from app.engine.risk import RiskCheckFailedError, RiskEngine


def create_sample_order(security_id: str = "1333") -> DhanOrderRequest:
    return DhanOrderRequest(
        securityId=security_id,
        exchangeSegment=ExchangeSegment.NSE_EQ,
        transactionType=TransactionType.BUY,
        orderType=OrderType.LIMIT,
        productType=ProductType.INTRADAY,
        quantity=10,
        price=100.0,
    )


def make_dhan_position(security_id: str, net_qty: int) -> DhanPosition:
    return DhanPosition(
        security_id=security_id,
        exchange_segment="NSE_EQ",
        position_type="INTRADAY",
        net_qty=net_qty,
    )


def test_matching_positions_produce_no_freeze() -> None:
    reconciler = ContinuousReconciler()
    local_positions = {"1333": 50, "11536": -25}
    broker_positions = [
        make_dhan_position("1333", 50),
        make_dhan_position("11536", -25),
    ]

    incidents = reconciler.reconcile_positions(local_positions, broker_positions)
    assert len(incidents) == 0
    assert reconciler.is_symbol_frozen("1333") is False
    assert reconciler.is_symbol_frozen("11536") is False


def test_seeded_position_mismatch_freezes_trading_without_auto_correction() -> None:
    reconciler = ContinuousReconciler()
    # Local believes 100 shares, but broker shows 50 shares
    local_positions = {"1333": 100}
    broker_positions = [
        make_dhan_position("1333", 50),
    ]

    incidents = reconciler.reconcile_positions(local_positions, broker_positions)
    assert len(incidents) == 1
    incident = incidents[0]

    # Invariant: incident created with exact details
    assert incident.dimension == MismatchDimension.POSITION
    assert incident.security_id == "1333"
    assert incident.local_value == 100
    assert incident.broker_value == 50
    assert incident.status == IncidentStatus.ACTIVE_FROZEN

    # Invariant: Symbol is immediately frozen
    assert reconciler.is_symbol_frozen("1333") is True

    # Invariant: Zero silent auto-correction — local positions map is untouched by reconciler
    assert local_positions["1333"] == 100


def test_seeded_order_mismatch_freezes_symbol() -> None:
    reconciler = ContinuousReconciler()
    local_orders = {
        "ORD-001": ReconciledOrderState(
            order_id="ORD-001",
            status=OrderStatus.TRADED,
            cumulative_traded_qty=50,
            avg_traded_price=100.0,
        ),
    }
    # Broker shows order was actually CANCELLED with only 20 filled
    broker_orders = [
        DhanOrderDetail.model_validate(
            {
                "orderId": "ORD-001",
                "orderStatus": "CANCELLED",
                "transactionType": "BUY",
                "exchangeSegment": "NSE_EQ",
                "productType": "INTRADAY",
                "orderType": "LIMIT",
                "quantity": 50,
                "tradedQuantity": 20,
                "securityId": "1333",
            }
        ),
    ]

    incidents = reconciler.reconcile_orders(local_orders, broker_orders)
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.dimension == MismatchDimension.ORDER
    assert incident.security_id == "1333"
    assert incident.status == IncidentStatus.ACTIVE_FROZEN
    assert reconciler.is_symbol_frozen("1333") is True


def test_risk_engine_enforces_freeze_rejection() -> None:
    reconciler = ContinuousReconciler()
    risk_engine = RiskEngine(continuous_reconciler=reconciler)

    # Freeze symbol 1333 via position mismatch
    reconciler.reconcile_positions(
        {"1333": 10},
        [make_dhan_position("1333", 20)],
    )
    assert reconciler.is_symbol_frozen("1333") is True

    # Order for frozen symbol is rejected
    frozen_order = create_sample_order("1333")
    with pytest.raises(RiskCheckFailedError, match="Trading is FROZEN for security '1333'"):
        risk_engine.filter_order(frozen_order)

    # Order for non-frozen symbol is accepted
    unfrozen_order = create_sample_order("11536")
    risk_engine.filter_order(unfrozen_order)


def test_operator_resolution_workflow_unfreezes_symbol() -> None:
    reconciler = ContinuousReconciler()
    risk_engine = RiskEngine(continuous_reconciler=reconciler)

    incidents = reconciler.reconcile_positions(
        {"1333": 0},
        [make_dhan_position("1333", 10)],
    )
    assert len(incidents) == 1
    incident_id = incidents[0].incident_id

    # Trading is blocked
    order = create_sample_order("1333")
    with pytest.raises(RiskCheckFailedError):
        risk_engine.filter_order(order)

    # Operator explicitly resolves incident
    resolved = reconciler.resolve_mismatch(
        incident_id=incident_id,
        resolution_action="OVERRIDE_TO_BROKER",
        operator_notes="Confirmed broker fill was legitimate manual trade.",
    )
    assert resolved is True
    assert reconciler.is_symbol_frozen("1333") is False

    # Now trading is unblocked
    risk_engine.filter_order(order)
