"""Unit tests for SimBroker, fill timing, order matching, and slippage models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.engine.contracts import OrderRequest, OrderSide, OrderStatus, OrderType
from app.engine.sim_broker import FillTiming, SimBroker
from app.engine.slippage import (
    NoSlippageModel,
    PercentageSlippageModel,
    SlippageModel,
    TickSlippageModel,
)
from app.warehouse.schema import BarRecord


def _make_bar(
    sec_id: str,
    ts: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
) -> BarRecord:
    return BarRecord(
        symbol=sec_id,
        exchange_segment="NSE_EQ",
        security_id=sec_id,
        timestamp=ts,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=10000,
        open_interest=0,
    )


def test_next_bar_open_fill_timing_no_lookahead() -> None:
    """Test NEXT_BAR_OPEN semantics: order submitted on signal at Bar T fills at Bar T+1 Open."""
    broker = SimBroker(fill_timing=FillTiming.NEXT_BAR_OPEN)
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=1)

    bar1 = _make_bar("INFY", t1, open_=1508.0, high=1520.0, low=1502.0, close=1515.0)

    # Signal occurs at Bar 0 (t0), submitting a Market Buy
    order = OrderRequest(
        security_id="INFY",
        exchange_segment="NSE_EQ",
        side=OrderSide.BUY,
        quantity=50,
        order_type=OrderType.MARKET,
    )
    results = broker.submit([order])
    assert results[0].status == OrderStatus.ACCEPTED

    # Process Bar 1: Fill occurs at Bar 1's Open (1508.0)
    fills = broker.process_bar(bar1)
    assert len(fills) == 1
    assert fills[0].price == 1508.0
    assert fills[0].timestamp == t1
    assert fills[0].quantity == 50
    assert broker.get_positions()["INFY"].quantity == 50


def test_slippage_models_and_price_clamping_invariant() -> None:
    """Property test: No slippage model produces fill price outside [bar.low, bar.high]."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    bar = _make_bar("RELIANCE", t0, open_=2500.0, high=2520.0, low=2480.0, close=2510.0)

    models: list[SlippageModel] = [
        NoSlippageModel(),
        TickSlippageModel(ticks=10, default_tick_size=0.05),  # 0.50 slippage
        TickSlippageModel(ticks=1000, default_tick_size=0.05),  # Huge 50.0 slippage (tests clamp)
        PercentageSlippageModel(percentage=0.01),  # 1%
        PercentageSlippageModel(percentage=0.50),  # 50% huge slippage (tests clamp)
    ]

    test_prices = [2470.0, 2480.0, 2490.0, 2500.0, 2515.0, 2520.0, 2535.0]

    for model in models:
        for ref_price in test_prices:
            for side in [OrderSide.BUY, OrderSide.SELL]:
                fill_price, slip = model.compute_fill_price(ref_price, side, bar)
                # Hard invariant assertion
                assert bar.low <= fill_price <= bar.high, (
                    f"Model {model} violated containment: fill {fill_price} "
                    f"not in [{bar.low}, {bar.high}] for ref {ref_price} {side}"
                )
                assert slip >= 0.0


def test_limit_order_matching() -> None:
    """Test Limit order matching rules against bar OHLC."""
    broker = SimBroker()
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)

    # 1. Limit Buy @ 100.0
    buy_order = OrderRequest(
        security_id="ABC",
        exchange_segment="NSE_EQ",
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.LIMIT,
        price=100.0,
    )
    broker.submit([buy_order])

    # Bar with Low=101.0 -> No Fill
    bar_miss = _make_bar("ABC", t0, open_=105.0, high=106.0, low=101.0, close=102.0)
    assert len(broker.process_bar(bar_miss)) == 0

    # Bar with Low=99.0, Open=102.0 -> Fills at Limit Price 100.0
    bar_hit = _make_bar("ABC", t0, open_=102.0, high=103.0, low=99.0, close=101.0)
    fills = broker.process_bar(bar_hit)
    assert len(fills) == 1
    assert fills[0].price == 100.0

    # 2. Limit Sell @ 200.0 with price improvement (Open=205.0)
    sell_order = OrderRequest(
        security_id="XYZ",
        exchange_segment="NSE_EQ",
        side=OrderSide.SELL,
        quantity=10,
        order_type=OrderType.LIMIT,
        price=200.0,
    )
    broker.submit([sell_order])
    bar_gap = _make_bar("XYZ", t0, open_=205.0, high=210.0, low=204.0, close=208.0)
    fills_sell = broker.process_bar(bar_gap)
    assert len(fills_sell) == 1
    assert fills_sell[0].price == 205.0  # Captured gap up open


def test_stop_loss_order_matching() -> None:
    """Test Stop-Loss Market (SL_M) order triggering and execution."""
    broker = SimBroker()
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)

    sl_order = OrderRequest(
        security_id="TATA",
        exchange_segment="NSE_EQ",
        side=OrderSide.SELL,
        quantity=20,
        order_type=OrderType.SL_M,
        trigger_price=490.0,
    )
    broker.submit([sl_order])

    # Bar stays above trigger (Low=492.0) -> No Fill
    bar_safe = _make_bar("TATA", t0, open_=500.0, high=502.0, low=492.0, close=495.0)
    assert len(broker.process_bar(bar_safe)) == 0

    # Bar breaches trigger (Open=495.0, Low=485.0) -> Triggers and fills at 490.0
    bar_trigger = _make_bar("TATA", t0, open_=495.0, high=496.0, low=485.0, close=488.0)
    fills = broker.process_bar(bar_trigger)
    assert len(fills) == 1
    assert fills[0].price == 490.0


def test_order_cancellation_and_rejection() -> None:
    """Test order cancellation and validation rejection."""
    broker = SimBroker()

    # Reject zero quantity
    bad_order = OrderRequest.model_construct(
        order_id="bad1",
        security_id="TCS",
        exchange_segment="NSE_EQ",
        side=OrderSide.BUY,
        quantity=0,
        order_type=OrderType.MARKET,
    )
    results = broker.submit([bad_order])
    assert results[0].status == OrderStatus.REJECTED

    # Accept and Cancel
    valid_order = OrderRequest(
        security_id="TCS",
        exchange_segment="NSE_EQ",
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.LIMIT,
        price=3500.0,
    )
    res = broker.submit([valid_order])
    assert res[0].status == OrderStatus.ACCEPTED
    assert broker.cancel(valid_order.order_id) is True
    assert broker.cancel("non_existent_id") is False
