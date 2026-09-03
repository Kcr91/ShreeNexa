"""Unit and safety tests for RiskEngine, RiskLimits, and RiskFilteredBroker (F12.4)."""

from __future__ import annotations

import pytest
from app.dhan.client import DhanRestClient
from app.dhan.credentials import DhanCredentials
from app.dhan.orders import (
    DhanOrderRequest,
    ExchangeSegment,
    OrderType,
    ProductType,
    TransactionType,
)
from app.dhan.transport import MockTransport
from app.engine.broker import DhanBroker
from app.engine.risk import (
    KillSwitchActiveError,
    RiskCheckFailedError,
    RiskEngine,
    RiskFilteredBroker,
    RiskLimits,
)
from pydantic import SecretStr


@pytest.fixture
def mock_dhan_broker() -> DhanBroker:
    transport = MockTransport()
    transport.register(
        "positions",
        status_code=200,
        body={"status": "SUCCESS", "message": "All positions closed"},
    )
    transport.register(
        "killswitch?killSwitchStatus=ACTIVATE",
        status_code=200,
        body={"killSwitchStatus": "ACTIVATE"},
    )
    transport.register(
        "orders",
        status_code=200,
        body={"orderId": "ORD-12345", "orderStatus": "PENDING"},
    )

    creds = DhanCredentials(
        client_id="1100000000",
        access_token=SecretStr("valid_token"),
        source="environment",
    )
    client = DhanRestClient(credentials=creds, transport=transport)
    # Use paper / mock mode with static ip check disabled for offline tests
    return DhanBroker(client=client, enable_live_trading=True, enforce_static_ip=False)


def create_sample_order(
    quantity: int = 10,
    price: float = 100.0,
    security_id: str = "1333",
) -> DhanOrderRequest:
    return DhanOrderRequest(
        securityId=security_id,
        exchangeSegment=ExchangeSegment.NSE_EQ,
        transactionType=TransactionType.BUY,
        orderType=OrderType.LIMIT,
        productType=ProductType.INTRADAY,
        quantity=quantity,
        price=price,
    )


def test_risk_order_value_cap_rejection() -> None:
    limits = RiskLimits(max_order_value=500_000.0)
    engine = RiskEngine(limits=limits)

    # 1,000 shares @ ₹600 = ₹600,000 > ₹500,000
    huge_order = create_sample_order(quantity=1000, price=600.0)
    with pytest.raises(RiskCheckFailedError, match="exceeds max_order_value cap"):
        engine.filter_order(huge_order)

    # Normal order: 100 shares @ ₹600 = ₹60,000 -> passes
    normal_order = create_sample_order(quantity=100, price=600.0)
    engine.filter_order(normal_order)


def test_risk_price_band_rejection() -> None:
    limits = RiskLimits(price_band_pct=0.10)  # ±10%
    engine = RiskEngine(limits=limits)

    ref_ltp = 1000.0
    # Price = 1150 (+15% deviation) -> rejected
    bad_price_order = create_sample_order(quantity=10, price=1150.0)
    with pytest.raises(RiskCheckFailedError, match=r"deviates 15\.0% from ref LTP"):
        engine.filter_order(bad_price_order, ref_ltp=ref_ltp)

    # Price = 1050 (+5% deviation) -> accepted
    good_price_order = create_sample_order(quantity=10, price=1050.0)
    engine.filter_order(good_price_order, ref_ltp=ref_ltp)


def test_risk_max_open_positions_cap() -> None:
    limits = RiskLimits(max_open_positions=5)
    engine = RiskEngine(limits=limits)

    order = create_sample_order()
    # 5 positions open -> rejected
    with pytest.raises(RiskCheckFailedError, match="max_open_positions limit"):
        engine.filter_order(order, current_positions_count=5)

    # 4 positions open -> accepted
    engine.filter_order(order, current_positions_count=4)


def test_risk_order_rate_limit() -> None:
    limits = RiskLimits(max_orders_per_second=5)
    engine = RiskEngine(limits=limits)

    order = create_sample_order()
    for _ in range(5):
        engine.filter_order(order)

    # 6th order in the same second violates rate limit
    with pytest.raises(RiskCheckFailedError, match="Order velocity exceeded"):
        engine.filter_order(order)


def test_emergency_kill_switch_halts_within_one_tick() -> None:
    engine = RiskEngine()
    order = create_sample_order()

    # Normal execution allowed
    engine.filter_order(order)

    # Trigger emergency halt
    engine.halt(reason="Operator emergency manual halt")
    assert engine.is_halted is True
    assert engine.halt_reason == "Operator emergency manual halt"

    # Immediately on the very next tick, all orders are rejected
    with pytest.raises(KillSwitchActiveError, match="Operator emergency manual halt"):
        engine.filter_order(order)

    # Manually unhalting restores order routing
    engine.unhalt()
    assert engine.is_halted is False
    engine.filter_order(order)


def test_max_daily_loss_triggers_automatic_kill_switch(mock_dhan_broker: DhanBroker) -> None:
    limits = RiskLimits(max_daily_loss=25_000.0)
    engine = RiskEngine(limits=limits)

    # Loss within limit
    engine.record_loss(10_000.0, broker=mock_dhan_broker)
    assert engine.is_halted is False

    # Second loss brings cumulative loss to ₹30,000 >= ₹25,000 -> triggers halt & broker exit
    engine.record_loss(20_000.0, broker=mock_dhan_broker)
    assert engine.is_halted is True
    assert "Max daily loss breached" in (engine.halt_reason or "")


def test_kill_switch_triggers_broker_fail_safes(mock_dhan_broker: DhanBroker) -> None:
    engine = RiskEngine()
    report = engine.halt(
        reason="Market crash fail-safe",
        broker=mock_dhan_broker,
        exit_all_positions=True,
        activate_broker_killswitch=True,
    )

    assert report["halted"] is True
    assert report["broker_exit_all_positions"] is True
    assert report["broker_killswitch_activated"] is True


def test_broker_path_enforcement_via_risk_filtered_broker(mock_dhan_broker: DhanBroker) -> None:
    limits = RiskLimits(max_order_value=100_000.0)
    engine = RiskEngine(limits=limits)
    filtered_broker = RiskFilteredBroker(broker=mock_dhan_broker, risk_engine=engine)

    # Valid order places cleanly through DhanBroker
    valid_order = create_sample_order(quantity=10, price=100.0)  # ₹1,000
    resp = filtered_broker.place_order(valid_order)
    assert resp.order_id == "ORD-12345"

    # Violating order is blocked before reaching DhanBroker
    huge_order = create_sample_order(quantity=2000, price=100.0)  # ₹200,000 > ₹100,000
    with pytest.raises(RiskCheckFailedError):
        filtered_broker.place_order(huge_order)

    # Triggering kill switch blocks all orders
    engine.halt("Risk breach")
    with pytest.raises(KillSwitchActiveError):
        filtered_broker.place_order(valid_order)
