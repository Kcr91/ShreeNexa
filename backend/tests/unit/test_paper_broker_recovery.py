"""Unit tests for PaperBroker state machine, fill policy, restart recovery, and idempotency."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.api.paper import (
    CreateAccountRequest,
    SubmitPaperOrderRequest,
    cancel_order,
    create_or_reset_account,
    get_account,
    list_fills,
    list_orders,
    list_positions,
    submit_order,
)
from app.main import app
from app.paper.broker import PaperBroker
from app.paper.fill_policy import PaperFillPolicy, calculate_indian_statutory_costs
from app.paper.models import (
    PaperFill,
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
)
from app.paper.repository import PaperRepository
from fastapi.testclient import TestClient

IST = ZoneInfo("Asia/Kolkata")
client = TestClient(app)


def test_paper_order_submission_and_cash_validation() -> None:
    repo = PaperRepository()
    repo.get_or_create_account("acc-1", initial_capital=50000.0)
    broker = PaperBroker(repository=repo)

    # Valid order within budget
    order_ok = PaperOrder(
        order_id="ord-1",
        account_id="acc-1",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=10,
        price=3500.0,
    )
    res_ok = broker.submit_orders([order_ok])
    assert res_ok[0].status.value == "ACCEPTED"
    stored_order = repo.get_order("ord-1")
    assert stored_order is not None
    assert stored_order.status == PaperOrderStatus.ACCEPTED

    # Order exceeding cash balance
    order_huge = PaperOrder(
        order_id="ord-2",
        account_id="acc-1",
        symbol="INFY",
        security_id="1594",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=1000,
        price=1800.0,
    )
    res_huge = broker.submit_orders([order_huge])
    assert res_huge[0].status.value == "REJECTED"
    assert "Insufficient funds" in (order_huge.reject_reason or "")


def test_market_order_fill_and_slippage() -> None:
    repo = PaperRepository()
    repo.get_or_create_account("acc-1", initial_capital=100000.0)
    broker = PaperBroker(repository=repo)

    order = PaperOrder(
        order_id="ord-mkt",
        account_id="acc-1",
        symbol="RELIANCE",
        security_id="2885",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=20,
    )
    broker.submit_orders([order])

    fills = broker.process_price_update(
        security_id="2885",
        current_price=2900.0,
    )
    assert len(fills) == 1
    assert fills[0].quantity == 20
    assert fills[0].price == 2900.0
    stored = repo.get_order("ord-mkt")
    assert stored is not None
    assert stored.status == PaperOrderStatus.FILLED

    # Check Position
    pos = repo.get_position("acc-1", "2885")
    assert pos is not None
    assert pos.quantity == 20
    assert pos.avg_entry_price == 2900.0

    # Check Account Cash Balance (100,000 - 58,000 - charges)
    acc = repo.get_account("acc-1")
    assert acc is not None
    assert acc.cash_balance < 42000.0


def test_limit_order_execution() -> None:
    repo = PaperRepository()
    repo.get_or_create_account("acc-1", initial_capital=100000.0)
    broker = PaperBroker(repository=repo)

    buy_limit = PaperOrder(
        order_id="ord-limit-buy",
        account_id="acc-1",
        symbol="SBIN",
        security_id="3045",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=50,
        price=800.0,
    )
    broker.submit_orders([buy_limit])

    # Price stays above limit (820 > 800) -> No fill
    fills_1 = broker.process_price_update(security_id="3045", current_price=820.0, low_price=815.0)
    assert len(fills_1) == 0
    stored_1 = repo.get_order("ord-limit-buy")
    assert stored_1 is not None
    assert stored_1.status == PaperOrderStatus.ACCEPTED

    # Price drops to 795 (<= 800) -> Fills
    fills_2 = broker.process_price_update(security_id="3045", current_price=795.0, low_price=795.0)
    assert len(fills_2) == 1
    assert fills_2[0].quantity == 50
    stored_2 = repo.get_order("ord-limit-buy")
    assert stored_2 is not None
    assert stored_2.status == PaperOrderStatus.FILLED


def test_stop_loss_trigger_and_fill() -> None:
    repo = PaperRepository()
    repo.get_or_create_account("acc-1", initial_capital=100000.0)
    broker = PaperBroker(repository=repo)

    sl_order = PaperOrder(
        order_id="ord-sl",
        account_id="acc-1",
        symbol="NIFTY",
        security_id="26000",
        side=PaperOrderSide.SELL,
        order_type=PaperOrderType.STOP_LOSS_MARKET,
        quantity=25,
        trigger_price=24900.0,
    )
    broker.submit_orders([sl_order])

    # Price at 25000 -> No trigger
    fills_1 = broker.process_price_update(
        security_id="26000", current_price=25000.0, low_price=24950.0
    )
    assert len(fills_1) == 0

    # Price falls to 24880 (<= 24900) -> Triggers and fills
    fills_2 = broker.process_price_update(
        security_id="26000", current_price=24880.0, low_price=24880.0
    )
    assert len(fills_2) == 1
    assert fills_2[0].price == 24880.0
    stored_sl = repo.get_order("ord-sl")
    assert stored_sl is not None
    assert stored_sl.status == PaperOrderStatus.FILLED


def test_fill_idempotency_and_no_double_counting() -> None:
    repo = PaperRepository()
    repo.get_or_create_account("acc-1", initial_capital=100000.0)
    broker = PaperBroker(repository=repo)

    fill = PaperFill(
        fill_id="fill-idem-1",
        order_id="ord-1",
        account_id="acc-1",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        quantity=10,
        price=3500.0,
        transaction_cost=40.0,
        timestamp=datetime.now(tz=UTC),
    )

    # 1st apply: Success
    applied_1 = broker.apply_fill(fill)
    assert applied_1 is True
    acc = repo.get_account("acc-1")
    assert acc is not None
    cash_after_first = acc.cash_balance

    # 2nd apply with same fill_id: Rejected by idempotency guard
    applied_2 = broker.apply_fill(fill)
    assert applied_2 is False
    assert acc.cash_balance == cash_after_first  # Cash untouched!


def test_restart_recovery() -> None:
    repo = PaperRepository()
    acc = repo.get_or_create_account("acc-rec", initial_capital=200000.0)
    acc.cash_balance = 150000.0
    acc.realized_pnl = 5000.0
    repo.save_account(acc)

    fill = PaperFill(
        fill_id="fill-rec-1",
        order_id="ord-rec-1",
        account_id="acc-rec",
        symbol="INFY",
        security_id="1594",
        side=PaperOrderSide.BUY,
        quantity=30,
        price=1600.0,
        transaction_cost=50.0,
        timestamp=datetime.now(tz=UTC),
    )
    repo.save_fill(fill)

    # Instantiate brand new broker instance representing engine restart
    new_broker = PaperBroker(repository=repo)
    recovered_acc = new_broker.recover("acc-rec")

    assert recovered_acc.account_id == "acc-rec"
    assert recovered_acc.cash_balance == 150000.0
    assert "fill-rec-1" in new_broker._processed_fill_ids


def test_paper_rest_api_endpoints() -> None:
    # 1. Create account
    resp_acc = client.post(
        "/api/v1/paper/accounts",
        json={"account_id": "api-acc-1", "name": "API Account", "initial_capital": 500000.0},
    )
    assert resp_acc.status_code == 200
    assert resp_acc.json()["cash_balance"] == 500000.0

    # 2. Get account
    resp_get = client.get("/api/v1/paper/accounts/api-acc-1")
    assert resp_get.status_code == 200
    assert resp_get.json()["name"] == "API Account"

    # 3. Submit order
    order_payload = {
        "account_id": "api-acc-1",
        "symbol": "TATASTEEL",
        "security_id": "3499",
        "side": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": 140.0,
    }
    resp_order = client.post("/api/v1/paper/orders", json=order_payload)
    assert resp_order.status_code == 200
    order_data = resp_order.json()
    assert order_data["status"] == "ACCEPTED"
    oid = order_data["order_id"]

    # 4. List orders
    resp_list = client.get("/api/v1/paper/orders?account_id=api-acc-1")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # 5. Cancel order
    resp_cancel = client.delete(f"/api/v1/paper/orders/{oid}")
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "CANCELLED"

    # 6. Cancel non-existent order -> 400
    resp_bad_cancel = client.delete("/api/v1/paper/orders/non-existent-oid")
    assert resp_bad_cancel.status_code == 400

    # 7. Get non-existent account -> 404
    resp_missing_acc = client.get("/api/v1/paper/accounts/unknown-acc-xyz")
    assert resp_missing_acc.status_code == 404

    # 8. Query positions and fills endpoints
    resp_pos = client.get("/api/v1/paper/positions?account_id=api-acc-1")
    assert resp_pos.status_code == 200
    assert isinstance(resp_pos.json(), list)

    resp_fills = client.get("/api/v1/paper/fills?account_id=api-acc-1")
    assert resp_fills.status_code == 200
    assert isinstance(resp_fills.json(), list)


def test_stop_loss_limit_execution() -> None:
    repo = PaperRepository()
    repo.get_or_create_account("acc-sll", initial_capital=100000.0)
    broker = PaperBroker(repository=repo)

    # Buy Stop Loss Limit: trigger at 105, limit at 106
    buy_sll = PaperOrder(
        order_id="ord-sll-buy",
        account_id="acc-sll",
        symbol="HDFCBANK",
        security_id="1333",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.STOP_LOSS_LIMIT,
        quantity=50,
        trigger_price=105.0,
        price=106.0,
    )
    broker.submit_orders([buy_sll])

    # Price at 102 (high 104) -> Not triggered
    fills_1 = broker.process_price_update(
        security_id="1333", current_price=102.0, high_price=104.0, low_price=101.0
    )
    assert len(fills_1) == 0

    # Price rises to 105.5 (high 105.8, low 103.0) -> Triggered and filled within limit 106
    fills_2 = broker.process_price_update(
        security_id="1333", current_price=105.5, high_price=105.8, low_price=103.0
    )
    assert len(fills_2) == 1
    assert fills_2[0].quantity == 50
    assert fills_2[0].price <= 106.0
    stored_buy = repo.get_order("ord-sll-buy")
    assert stored_buy is not None
    assert stored_buy.status == PaperOrderStatus.FILLED


def test_sell_limit_execution() -> None:
    repo = PaperRepository()
    repo.get_or_create_account("acc-sell-lmt", initial_capital=100000.0)
    broker = PaperBroker(repository=repo)

    sell_lmt = PaperOrder(
        order_id="ord-sell-lmt",
        account_id="acc-sell-lmt",
        symbol="WIPRO",
        security_id="3787",
        side=PaperOrderSide.SELL,
        order_type=PaperOrderType.LIMIT,
        quantity=30,
        price=550.0,
    )
    broker.submit_orders([sell_lmt])

    # Price at 540 (high 545) -> Below limit, no fill
    fills_1 = broker.process_price_update(
        security_id="3787", current_price=540.0, high_price=545.0, low_price=538.0
    )
    assert len(fills_1) == 0

    # High penetrates limit (555 >= 550) -> Fills
    fills_2 = broker.process_price_update(
        security_id="3787", current_price=552.0, high_price=555.0, low_price=548.0
    )
    assert len(fills_2) == 1
    assert fills_2[0].price >= 550.0


def test_mark_to_market_unrealized_pnl() -> None:
    repo = PaperRepository()
    repo.get_or_create_account("acc-mtm", initial_capital=100000.0)
    broker = PaperBroker(repository=repo)

    # Buy 10 shares of RELIANCE @ 2900 via market order
    buy_order = PaperOrder(
        order_id="ord-mtm-buy",
        account_id="acc-mtm",
        symbol="RELIANCE",
        security_id="2885",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=10,
    )
    broker.submit_orders([buy_order])
    broker.process_price_update(security_id="2885", current_price=2900.0)

    pos = repo.get_position("acc-mtm", "2885")
    assert pos is not None
    assert pos.quantity == 10
    assert pos.unrealized_pnl == 0.0

    # Price moves to 2950 -> Unrealized P&L is +500
    broker.process_price_update(security_id="2885", current_price=2950.0)
    assert pos.current_price == 2950.0
    assert pos.unrealized_pnl == 500.0

    # Price drops to 2850 -> Unrealized P&L is -500
    broker.process_price_update(security_id="2885", current_price=2850.0)
    assert pos.current_price == 2850.0
    assert pos.unrealized_pnl == -500.0


def test_on_bar_processing() -> None:
    from app.warehouse.schema import BarRecord

    repo = PaperRepository()
    repo.get_or_create_account("acc-bar", initial_capital=100000.0)
    broker = PaperBroker(repository=repo)

    order = PaperOrder(
        order_id="ord-bar-1",
        account_id="acc-bar",
        symbol="ICICIBANK",
        security_id="4963",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=20,
        price=1200.0,
    )
    broker.submit_orders([order])

    # Bar with low 1195 (<= 1200 limit)
    bar = BarRecord(
        symbol="ICICIBANK",
        security_id="4963",
        exchange_segment="NSE_EQ",
        timestamp=datetime.now(tz=UTC),
        open=1210.0,
        high=1215.0,
        low=1195.0,
        close=1198.0,
        volume=50000,
    )
    fills = broker.on_bar(bar)
    assert len(fills) == 1
    assert fills[0].quantity == 20
    assert fills[0].price == 1198.0


def test_g1_replay_cannot_duplicate_fills() -> None:
    """Proof G1: replaying identical tick/bar events cannot produce duplicate fills."""
    from app.warehouse.schema import BarRecord

    repo = PaperRepository()
    repo.get_or_create_account("acc-g1", initial_capital=500000.0)
    broker = PaperBroker(repository=repo)

    order = PaperOrder(
        order_id="ord-g1-1",
        account_id="acc-g1",
        symbol="LT",
        security_id="11483",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=10,
    )
    broker.submit_orders([order])

    now = datetime.now(tz=UTC)
    bar = BarRecord(
        symbol="LT",
        security_id="11483",
        exchange_segment="NSE_EQ",
        timestamp=now,
        open=3500.0,
        high=3520.0,
        low=3490.0,
        close=3510.0,
        volume=10000,
    )

    # 1. First execution
    fills_first = broker.on_bar(bar)
    assert len(fills_first) == 1
    first_fill = fills_first[0]
    acc = repo.get_account("acc-g1")
    assert acc is not None
    cash_after_first = acc.cash_balance

    # 2. Duplicate fill event replayed directly
    dup_applied = broker.apply_fill(first_fill)
    assert dup_applied is False  # Guard blocks duplicate
    assert acc.cash_balance == cash_after_first  # Cash preserved

    # 3. Bar re-fed to broker
    fills_second = broker.on_bar(bar)
    # Order is already FILLED, so match_order returns None
    assert len(fills_second) == 0
    assert acc.cash_balance == cash_after_first
    assert len(repo.list_fills("acc-g1")) == 1


def test_paper_api_direct_handlers() -> None:
    """Direct handler and Pydantic validation tests covering AST graph links."""
    req = CreateAccountRequest(account_id="direct-acc-1", initial_capital=250000.0)
    acc = create_or_reset_account(req)
    assert acc.account_id == "direct-acc-1"
    assert acc.cash_balance == 250000.0

    got = get_account("direct-acc-1")
    assert got.account_id == "direct-acc-1"

    order_req = SubmitPaperOrderRequest(
        account_id="direct-acc-1",
        symbol="SBIN",
        security_id="3045",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=20,
        price=820.0,
    )
    ord_res = submit_order(order_req)
    assert ord_res.symbol == "SBIN"

    orders = list_orders("direct-acc-1")
    assert len(orders) >= 1

    positions = list_positions("direct-acc-1")
    assert isinstance(positions, list)

    fills = list_fills("direct-acc-1")
    assert isinstance(fills, list)

    del_res = cancel_order(ord_res.order_id)
    assert del_res["status"] == "CANCELLED"


def test_calculate_indian_statutory_costs_and_policy() -> None:
    """Direct tests for Indian statutory costs and PaperFillPolicy matching logic."""
    # Zero or negative value -> 0.0
    assert calculate_indian_statutory_costs(PaperOrderSide.BUY, 0, 100.0) == 0.0
    assert calculate_indian_statutory_costs(PaperOrderSide.BUY, 10, 0.0) == 0.0

    # BUY 100 shares @ 500 = ₹50,000 trade value
    buy_cost = calculate_indian_statutory_costs(PaperOrderSide.BUY, 100, 500.0)
    assert buy_cost > 0.0

    # SELL 100 shares @ 500 = ₹50,000 trade value (stamp duty is 0 on sell)
    sell_cost = calculate_indian_statutory_costs(PaperOrderSide.SELL, 100, 500.0)
    assert sell_cost > 0.0
    assert sell_cost < buy_cost  # BUY has stamp duty, SELL does not

    # PaperFillPolicy tests
    policy = PaperFillPolicy()

    # Inactive order (not ACCEPTED or PARTIALLY_FILLED) -> None
    cancelled_order = PaperOrder(
        order_id="ord-c1",
        account_id="acc-1",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=10,
        status=PaperOrderStatus.CANCELLED,
    )
    assert policy.match_order(cancelled_order, current_price=3500.0) is None

    # Fully filled order (rem_qty <= 0) -> None
    filled_order = PaperOrder(
        order_id="ord-f1",
        account_id="acc-1",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=10,
        filled_quantity=10,
        status=PaperOrderStatus.ACCEPTED,
    )
    assert policy.match_order(filled_order, current_price=3500.0) is None

    # Limit order with price=None -> None
    bad_limit = PaperOrder(
        order_id="ord-l-none",
        account_id="acc-1",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=10,
        price=None,
        status=PaperOrderStatus.ACCEPTED,
    )
    assert policy.match_order(bad_limit, current_price=3500.0) is None

    # Stop market with trigger_price=None -> None
    bad_sl = PaperOrder(
        order_id="ord-sl-none",
        account_id="acc-1",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.STOP_LOSS_MARKET,
        quantity=10,
        trigger_price=None,
        status=PaperOrderStatus.ACCEPTED,
    )
    assert policy.match_order(bad_sl, current_price=3500.0) is None

    # Stop limit with trigger_price=None or price=None -> None
    bad_sll = PaperOrder(
        order_id="ord-sll-none",
        account_id="acc-1",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.STOP_LOSS_LIMIT,
        quantity=10,
        trigger_price=None,
        price=None,
        status=PaperOrderStatus.ACCEPTED,
    )
    assert policy.match_order(bad_sll, current_price=3500.0) is None
