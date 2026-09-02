"""Unit tests for multi-strategy paper trading with isolated capital and shared account caps."""

from __future__ import annotations

from datetime import UTC, datetime

from app.main import app
from app.paper.models import (
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
)
from app.paper.multi_strategy import (
    MultiStrategyPaperCoordinator,
    SharedAccountCaps,
    StrategyAllocationConfig,
)
from app.paper.repository import PaperRepository
from app.warehouse.schema import BarRecord
from fastapi.testclient import TestClient

client = TestClient(app)


def test_no_cross_strategy_cash_leakage() -> None:
    """Proof: Strategy A exhausting its capital cannot draw on Strategy B's capital."""
    repo = PaperRepository()
    allocations = [
        StrategyAllocationConfig(
            strategy_id="strat-alpha", strategy_name="Alpha Momentum", allocated_capital=100000.0
        ),
        StrategyAllocationConfig(
            strategy_id="strat-beta", strategy_name="Beta Mean Rev", allocated_capital=500000.0
        ),
    ]
    coord = MultiStrategyPaperCoordinator(
        account_id="acc-leakage-test",
        total_capital=600000.0,
        allocations=allocations,
        repository=repo,
    )

    # 1. Strat Alpha exhausts its capital: BUY 28 TCS @ 3500 = 98,000 + charges
    order_a1 = PaperOrder(
        order_id="ord-a1",
        account_id="acc-leakage-test:strat-alpha",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=28,
        price=3500.0,
    )
    res_a1 = coord.submit_strategy_order("strat-alpha", order_a1)
    coord.process_price_update("11536", 3500.0)
    assert res_a1.status == PaperOrderStatus.FILLED

    # Strat Alpha attempts to buy more TCS: BUY 10 TCS @ 3500 = 35,000 > remaining cash (~1900)
    order_a2 = PaperOrder(
        order_id="ord-a2",
        account_id="acc-leakage-test:strat-alpha",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=10,
        price=3500.0,
    )
    res_a2 = coord.submit_strategy_order("strat-alpha", order_a2)
    assert res_a2.status == PaperOrderStatus.REJECTED
    assert "Insufficient funds" in (res_a2.reject_reason or "")

    # 2. Strat Beta has 500,000 allocated and its cash must be 100% intact
    order_b1 = PaperOrder(
        order_id="ord-b1",
        account_id="acc-leakage-test:strat-beta",
        symbol="INFY",
        security_id="1594",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=100,
        price=1600.0,
    )
    res_b1 = coord.submit_strategy_order("strat-beta", order_b1)
    coord.process_price_update("1594", 1600.0)
    assert res_b1.status == PaperOrderStatus.FILLED

    # Check status report
    status = coord.get_status()
    assert status.strategies["strat-alpha"].cash_balance < 2000.0
    assert status.strategies["strat-beta"].cash_balance > 330000.0


def test_no_cross_strategy_position_leakage() -> None:
    """Proof: opposing or concurrent positions in the same stock do not cross-net."""
    repo = PaperRepository()
    allocations = [
        StrategyAllocationConfig(
            strategy_id="strat-long", strategy_name="Long Term", allocated_capital=300000.0
        ),
        StrategyAllocationConfig(
            strategy_id="strat-short", strategy_name="Short Trend", allocated_capital=300000.0
        ),
    ]
    coord = MultiStrategyPaperCoordinator(
        account_id="acc-pos-leakage",
        total_capital=600000.0,
        allocations=allocations,
        repository=repo,
    )

    # Strat Long buys 50 TCS @ 3500
    order_l = PaperOrder(
        order_id="ord-l",
        account_id="acc-pos-leakage:strat-long",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=50,
        price=3500.0,
    )
    coord.submit_strategy_order("strat-long", order_l)

    # Strat Short sells short 20 TCS @ 3500
    order_s = PaperOrder(
        order_id="ord-s",
        account_id="acc-pos-leakage:strat-short",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.SELL,
        order_type=PaperOrderType.MARKET,
        quantity=20,
        price=3500.0,
    )
    coord.submit_strategy_order("strat-short", order_s)

    coord.process_price_update("11536", 3500.0)

    # Check isolated positions in repository
    pos_long = repo.get_position("acc-pos-leakage:strat-long", "11536")
    pos_short = repo.get_position("acc-pos-leakage:strat-short", "11536")

    assert pos_long is not None
    assert pos_short is not None
    assert pos_long.quantity == 50
    assert pos_short.quantity == -20

    # Price moves to 3600
    coord.process_price_update("11536", 3600.0)
    pos_long_upd = repo.get_position("acc-pos-leakage:strat-long", "11536")
    pos_short_upd = repo.get_position("acc-pos-leakage:strat-short", "11536")

    assert pos_long_upd is not None and pos_short_upd is not None
    # Long gained 50 * 100 = +5000
    assert pos_long_upd.unrealized_pnl == 5000.0
    # Short lost 20 * 100 = -2000
    assert pos_short_upd.unrealized_pnl == -2000.0


def test_deterministic_conflict_and_shared_caps() -> None:
    """Proof: orders breaching shared account caps are deterministically rejected."""
    repo = PaperRepository()
    allocations = [
        StrategyAllocationConfig(
            strategy_id="s1", strategy_name="Strategy 1", allocated_capital=500000.0
        ),
        StrategyAllocationConfig(
            strategy_id="s2", strategy_name="Strategy 2", allocated_capital=500000.0
        ),
    ]
    # 25% single stock exposure cap (max 25% of 1,000,000 = 250,000)
    caps = SharedAccountCaps(max_single_stock_exposure_pct=0.25)
    coord = MultiStrategyPaperCoordinator(
        account_id="acc-caps",
        total_capital=1000000.0,
        allocations=allocations,
        shared_caps=caps,
        repository=repo,
    )

    # Strategy 1 buys 60 RELIANCE @ 3000 = 180,000 (18% < 25%) -> SUCCESS
    o1 = PaperOrder(
        order_id="ord-c1",
        account_id="acc-caps:s1",
        symbol="RELIANCE",
        security_id="2885",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=60,
        price=3000.0,
    )
    res_1 = coord.submit_strategy_order("s1", o1)
    assert res_1.status == PaperOrderStatus.ACCEPTED
    coord.process_price_update("2885", 3000.0, low_price=3000.0)
    assert repo.get_order("ord-c1") is not None
    assert repo.get_order("ord-c1").status == PaperOrderStatus.FILLED  # type: ignore[union-attr]

    # Strategy 2 attempts to buy 40 RELIANCE @ 3000 = 120,000.
    # Total RELIANCE exposure would become 180k + 120k = 300k (30% > 25% cap) -> REJECTED
    o2 = PaperOrder(
        order_id="ord-c2",
        account_id="acc-caps:s2",
        symbol="RELIANCE",
        security_id="2885",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=40,
        price=3000.0,
    )
    res_2 = coord.submit_strategy_order("s2", o2)
    assert res_2.status == PaperOrderStatus.REJECTED
    assert "Shared account cap breached" in (res_2.reject_reason or "")
    assert "single stock exposure" in (res_2.reject_reason or "")


def test_kill_switch_behavior() -> None:
    """Proof: kill switch immediately halts all strategies and cancels working orders."""
    repo = PaperRepository()
    allocations = [
        StrategyAllocationConfig(
            strategy_id="s_live", strategy_name="Live Strat", allocated_capital=200000.0
        )
    ]
    coord = MultiStrategyPaperCoordinator(
        account_id="acc-kill",
        total_capital=200000.0,
        allocations=allocations,
        repository=repo,
    )

    # Place working limit order
    o_work = PaperOrder(
        order_id="ord-working-1",
        account_id="acc-kill:s_live",
        symbol="SBIN",
        security_id="3045",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=50,
        price=700.0,
    )
    coord.submit_strategy_order("s_live", o_work)
    assert o_work.status == PaperOrderStatus.ACCEPTED

    # Trigger emergency kill switch
    coord.trigger_kill_switch("Risk threshold breached")

    # Working order should now be cancelled
    stored = repo.get_order("ord-working-1")
    assert stored is not None
    assert stored.status == PaperOrderStatus.CANCELLED

    # Subsequent order should be rejected
    o_new = PaperOrder(
        order_id="ord-after-kill",
        account_id="acc-kill:s_live",
        symbol="SBIN",
        security_id="3045",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=10,
        price=750.0,
    )
    res_new = coord.submit_strategy_order("s_live", o_new)
    assert res_new.status == PaperOrderStatus.REJECTED
    assert "kill switch is active" in (res_new.reject_reason or "")

    # Reset kill switch
    coord.reset_kill_switch()
    o_reset = PaperOrder(
        order_id="ord-after-reset",
        account_id="acc-kill:s_live",
        symbol="SBIN",
        security_id="3045",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=10,
        price=750.0,
    )
    res_reset = coord.submit_strategy_order("s_live", o_reset)
    assert res_reset.status != PaperOrderStatus.REJECTED


def test_multi_strategy_api_integration() -> None:
    """Verify REST API endpoints for multi-strategy coordination."""
    # 1. Initialize multi-strategy
    init_payload = {
        "account_id": "api-multi-acc",
        "total_capital": 500000.0,
        "allocations": [
            {
                "strategy_id": "s_alpha",
                "strategy_name": "Alpha Breakout",
                "allocated_capital": 200000.0,
            },
            {
                "strategy_id": "s_beta",
                "strategy_name": "Beta MeanRev",
                "allocated_capital": 300000.0,
            },
        ],
        "shared_caps": {
            "max_single_stock_exposure_pct": 0.40,
            "max_account_leverage": 1.5,
            "max_account_drawdown_pct": 0.10,
        },
    }
    resp_init = client.post("/api/v1/paper/multi-strategy/init", json=init_payload)
    assert resp_init.status_code == 200
    init_data = resp_init.json()
    assert init_data["account_id"] == "api-multi-acc"
    assert "s_alpha" in init_data["strategies"]
    assert "s_beta" in init_data["strategies"]

    # 2. Submit order for s_alpha
    order_payload = {
        "account_id": "api-multi-acc",
        "strategy_id": "s_alpha",
        "symbol": "WIPRO",
        "security_id": "3787",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 100,
        "price": 450.0,
    }
    resp_ord = client.post("/api/v1/paper/multi-strategy/orders", json=order_payload)
    assert resp_ord.status_code == 200
    ord_data = resp_ord.json()
    assert ord_data["account_id"] == "api-multi-acc:s_alpha"

    # 3. Query status
    resp_stat = client.get("/api/v1/paper/multi-strategy/status?account_id=api-multi-acc")
    assert resp_stat.status_code == 200
    stat_data = resp_stat.json()
    assert stat_data["total_account_equity"] >= 490000.0

    # 4. Kill switch toggle
    resp_kill = client.post(
        "/api/v1/paper/multi-strategy/kill-switch",
        json={"account_id": "api-multi-acc", "action": "trigger"},
    )
    assert resp_kill.status_code == 200
    assert resp_kill.json()["kill_switch_active"] is True


def test_multi_strategy_bar_distribution() -> None:
    """Proof: BarRecord events fan out to all strategy books and trigger fills."""
    repo = PaperRepository()
    allocations = [
        StrategyAllocationConfig(
            strategy_id="strat-1", strategy_name="Strategy 1", allocated_capital=200000.0
        ),
        StrategyAllocationConfig(
            strategy_id="strat-2", strategy_name="Strategy 2", allocated_capital=200000.0
        ),
    ]
    coord = MultiStrategyPaperCoordinator(
        account_id="acc-bar-test",
        total_capital=400000.0,
        allocations=allocations,
        repository=repo,
    )

    # Strategy 1 places BUY LIMIT @ 1500 for INFY
    o1 = PaperOrder(
        order_id="ord-bar-1",
        account_id="acc-bar-test:strat-1",
        symbol="INFY",
        security_id="1594",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=50,
        price=1500.0,
    )
    coord.submit_strategy_order("strat-1", o1)

    # Strategy 2 places SELL LIMIT @ 1520 for INFY
    o2 = PaperOrder(
        order_id="ord-bar-2",
        account_id="acc-bar-test:strat-2",
        symbol="INFY",
        security_id="1594",
        side=PaperOrderSide.SELL,
        order_type=PaperOrderType.LIMIT,
        quantity=30,
        price=1520.0,
    )
    coord.submit_strategy_order("strat-2", o2)

    # Bar arrives with low=1490 (triggers o1 BUY) and high=1530 (triggers o2 SELL)
    bar = BarRecord(
        timestamp=datetime.now(UTC),
        exchange_segment="NSE_EQ",
        security_id="1594",
        symbol="INFY",
        open=1510.0,
        high=1530.0,
        low=1490.0,
        close=1515.0,
        volume=100000,
        open_interest=0,
    )
    fills = coord.on_bar(bar)
    assert len(fills) == 2

    # Check both orders filled in their respective isolated books
    stored_1 = repo.get_order("ord-bar-1")
    stored_2 = repo.get_order("ord-bar-2")
    assert stored_1 is not None and stored_1.status == PaperOrderStatus.FILLED
    assert stored_2 is not None and stored_2.status == PaperOrderStatus.FILLED

    # Check positions in both books
    pos_1 = repo.get_position("acc-bar-test:strat-1", "1594")
    pos_2 = repo.get_position("acc-bar-test:strat-2", "1594")
    assert pos_1 is not None and pos_1.quantity == 50
    assert pos_2 is not None and pos_2.quantity == -30

