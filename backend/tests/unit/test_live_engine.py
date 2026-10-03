"""Unit test suite for Feature 6: Dhan Live Trading, Risk Guardrails & Emergency Controls."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from app.api.deps import require_csrf, require_non_demo_session, require_session
from app.api.live_engine import get_db_engine
from app.live.dhan_adapter import DhanLiveExecutionAdapter
from app.live.live_models import (
    live_risk_settings_table,
    live_tradebook_table,
)
from app.live.reconciler import BrokerPositionReconciler
from app.live.safety_guard import SafetyGuardEngine
from app.live.security_resolver import DynamicSecurityResolver
from app.live.telegram_bot import TelegramAlertDispatcher
from app.main import app
from app.strategy.models import metadata, strategy_configs_table
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
def in_memory_engine() -> Generator[Engine]:
    """Create in-memory SQLite database engine with all tables for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)

    # Seed default strategy config & risk settings
    with engine.begin() as conn:
        conn.execute(
            insert(strategy_configs_table).values(
                id=1,
                name="Nifty Momentum Breakout",
                description="Intraday Momentum F&O",
                strategy_type="INTRADAY",
                current_version=1,
                is_active=True,
                config_json={
                    "scope": {"underlying": "NIFTY", "instrument_type": "OPTIDX"},
                    "entry": {"conditions": []},
                    "stoploss": {"type": "FIXED_POINTS", "points": 30.0},
                    "target": {"type": "FIXED_POINTS", "points": 60.0},
                },
            )
        )
        conn.execute(
            insert(live_risk_settings_table).values(
                id=1,
                max_daily_loss_pct=3.0,
                max_trade_exposure_pct=10.0,
                max_concurrent_trades=5,
                circuit_buffer_pct=0.5,
                kill_switch_active=False,
            )
        )
        conn.execute(
            insert(live_tradebook_table).values(
                trade_id=1,
                dhan_order_id="DH-LIVE-001",
                strategy_id=1,
                symbol="NIFTY26OCT25000CE",
                signal_type="BUY",
                fill_time=datetime.now(UTC),
                buy_price=145.0,
                sell_price=168.0,
                quantity=50,
                entry_vix=13.2,
                exit_vix=13.0,
                entry_iv=14.5,
                exit_iv=14.8,
                exit_reason="TARGET_1",
                realized_pnl=1150.0,
                brokerage_charges=20.0,
                stt_taxes=12.5,
                slippage_amount=5.0,
            )
        )

    yield engine
    metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(in_memory_engine: Engine) -> Generator[TestClient]:
    """FastAPI TestClient with overridden dependencies."""
    app.dependency_overrides[require_session] = lambda: {"user_id": 1, "is_demo": False}
    app.dependency_overrides[require_non_demo_session] = lambda: {
        "user_id": 1,
        "is_demo": False,
    }
    app.dependency_overrides[require_csrf] = lambda: None
    app.dependency_overrides[get_db_engine] = lambda: in_memory_engine

    tc = TestClient(app, raise_server_exceptions=True)
    yield tc

    app.dependency_overrides.clear()


# =========================================================
# 1. Safety Guardrails Unit Tests
# =========================================================


def test_safety_guardrails_all_pass() -> None:
    """Test all safety guardrails passing on normal safe conditions."""
    guard = SafetyGuardEngine(
        total_capital=500000.0,
        max_daily_loss_pct=3.0,
        max_trade_exposure_pct=10.0,
        max_concurrent_trades=5,
        circuit_buffer_pct=0.5,
    )

    passed, results = guard.validate_pre_order_all_guards(
        current_realized_pnl=1500.0,
        current_unrealized_pnl=500.0,
        required_trade_capital=25000.0,  # 5% of 500k -> within 10%
        current_open_positions_count=2,  # 2 < 5
        current_ltp=150.0,
        upper_circuit=200.0,
        lower_circuit=100.0,
    )
    assert passed is True
    assert all(r.passed for r in results)


def test_safety_guardrail_max_daily_loss_auto_kill() -> None:
    """Test auto-kill switch trigger when daily loss breaches limit."""
    guard = SafetyGuardEngine(total_capital=500000.0, max_daily_loss_pct=3.0)
    # 3% of 500k = ₹15,000 max allowed loss
    res = guard.check_daily_loss_limit(
        current_realized_pnl=-10000.0, current_unrealized_pnl=-6000.0
    )
    assert res.passed is False
    assert res.trigger_auto_kill is True
    assert guard.kill_switch_active is True
    assert "breached max daily loss limit" in (res.rejection_reason or "")


def test_safety_guardrail_trade_exposure_cap() -> None:
    """Test trade exposure rejection when exceeding 10% single trade cap."""
    guard = SafetyGuardEngine(total_capital=500000.0, max_trade_exposure_pct=10.0)
    # 10% of 500k = ₹50,000 max trade cap
    res_pass = guard.check_trade_exposure(45000.0)
    assert res_pass.passed is True

    res_fail = guard.check_trade_exposure(65000.0)
    assert res_fail.passed is False
    assert "exceeds max single trade exposure cap" in (res_fail.rejection_reason or "")


def test_safety_guardrail_max_concurrent_positions() -> None:
    """Test rejection when max concurrent positions limit is reached."""
    guard = SafetyGuardEngine(max_concurrent_trades=5)
    res_pass = guard.check_concurrent_positions(4)
    assert res_pass.passed is True

    res_fail = guard.check_concurrent_positions(5)
    assert res_fail.passed is False
    assert "Max concurrent open positions limit" in (res_fail.rejection_reason or "")


def test_safety_guardrail_circuit_breaker() -> None:
    """Test rejection when price approaches upper or lower circuit limit within buffer."""
    guard = SafetyGuardEngine(circuit_buffer_pct=0.5)
    # Upper circuit = 200, buffer 0.5% = threshold at 199.0
    res_near_circuit = guard.check_circuit_breaker(
        current_ltp=199.5, upper_circuit_limit=200.0, lower_circuit_limit=100.0
    )
    assert res_near_circuit.passed is False
    assert "Upper Circuit" in (res_near_circuit.rejection_reason or "")

    res_safe = guard.check_circuit_breaker(
        current_ltp=150.0, upper_circuit_limit=200.0, lower_circuit_limit=100.0
    )
    assert res_safe.passed is True


# =========================================================
# 2. Dynamic Option Security ID Resolver Tests
# =========================================================


def test_dynamic_security_resolver() -> None:
    """Test spot price and offset resolution to Dhan security IDs."""
    resolver = DynamicSecurityResolver()

    # NIFTY spot 25010 -> ATM CE = 25000 CE
    contract = resolver.resolve_live_option_contract(
        underlying="NIFTY",
        spot_price=25010.0,
        strike_offset="ATM",
        option_type="CE",
        expiry_date="2026-10-08",
    )
    assert contract.strike == 25000.0
    assert contract.option_type == "CE"
    assert contract.symbol == "NIFTY_2026-10-08_25000_CE"
    assert contract.lot_size == 50
    assert contract.dhan_security_id is not None

    # BANKNIFTY spot 54320 -> ITM1 PE = 54400 PE
    bn_contract = resolver.resolve_live_option_contract(
        underlying="BANKNIFTY",
        spot_price=54320.0,
        strike_offset="ITM1",
        option_type="PE",
        expiry_date="2026-10-08",
    )
    assert bn_contract.strike == 54400.0
    assert bn_contract.lot_size == 15
    assert bn_contract.symbol == "BANKNIFTY_2026-10-08_54400_PE"


def test_dhan_live_execution_adapter() -> None:
    """Test asynchronous order submission, position tracking, and square-off."""
    import asyncio

    async def _run_test() -> None:
        adapter = DhanLiveExecutionAdapter(client_id="TEST_CLIENT", access_token="TEST_TOKEN")
        assert adapter.is_connected() is True

        # 1. Submit BUY Order
        order = await adapter.submit_order_async(
            security_id="45001",
            exchange_segment="NSE_FNO",
            transaction_type="BUY",
            quantity=50,
            order_type="MARKET",
            price=150.0,
            symbol="NIFTY26OCT25000CE",
        )
        assert order["order_status"] == "TRADED"
        assert order["dhan_order_id"].startswith("DH-")
        assert order["latency_ms"] >= 0.0

        # 2. Verify Position Opened
        positions = adapter.get_broker_positions()
        assert len(positions) == 1
        assert positions[0]["symbol"] == "NIFTY26OCT25000CE"

        # 3. Square Off Single Position
        pos_id = positions[0]["position_id"]
        sq_res = await adapter.square_off_single_position(pos_id)
        assert sq_res is not None
        assert sq_res["status"] == "SUCCESS"
        assert len(adapter.get_broker_positions()) == 0

    asyncio.run(_run_test())


# =========================================================
# 4. Reconciliation Engine Tests
# =========================================================


def test_broker_position_reconciler() -> None:
    """Test position reconciler identifying synchronized state and discrepancies."""
    reconciler = BrokerPositionReconciler()

    # 1. Synchronized
    local_pos = [{"symbol": "NIFTY26OCT25000CE", "quantity": 50}]
    broker_pos = [{"symbol": "NIFTY26OCT25000CE", "quantity": 50}]
    res_sync = reconciler.reconcile_positions(local_pos, broker_pos)
    assert res_sync["status"] == "SYNCHRONIZED"
    assert res_sync["mismatch_detected"] is False

    # 2. Quantity Mismatch
    broker_pos_mismatch = [{"symbol": "NIFTY26OCT25000CE", "quantity": 100}]
    res_mismatch = reconciler.reconcile_positions(local_pos, broker_pos_mismatch)
    assert res_mismatch["status"] == "WARNING_MISMATCH"
    assert res_mismatch["mismatch_detected"] is True
    assert res_mismatch["drift_details"][0]["issue_type"] == "QUANTITY_MISMATCH"


# =========================================================
# 5. Telegram Alert Dispatcher Tests
# =========================================================


def test_telegram_alert_dispatcher() -> None:
    """Test Telegram dispatcher message formatting and dispatch records."""
    dispatcher = TelegramAlertDispatcher(bot_token="test_token", chat_id="12345", enabled=True)

    # Order fill alert
    res_fill = dispatcher.send_order_fill_alert(
        symbol="NIFTY26OCT25000CE",
        transaction_type="BUY",
        quantity=50,
        executed_price=150.05,
        dhan_order_id="DH-982142",
    )
    assert res_fill["event_type"] == "ORDER_FILLED"
    assert "NIFTY26OCT25000CE" in res_fill["text"]

    # Kill switch alert
    res_ks = dispatcher.send_kill_switch_alert(
        reason="Daily Loss Limit Breached",
        daily_pnl=-16000.0,
        positions_closed=2,
    )
    assert res_ks["event_type"] == "KILL_SWITCH_HALT"
    assert "KILL SWITCH ACTIVATED" in res_ks["text"]
    assert len(dispatcher.dispatched_messages) == 2


# =========================================================
# 6. FastAPI Live Engine Endpoints Tests
# =========================================================


def test_api_live_status_and_positions(client: TestClient) -> None:
    """Test GET /api/v1/live/status and GET /api/v1/live/positions."""
    resp_status = client.get("/api/v1/live/status")
    assert resp_status.status_code == 200
    data_status = resp_status.json()
    assert "status" in data_status
    assert data_status["dhan_api_connected"] is True
    assert data_status["max_concurrent_trades"] == 5

    resp_pos = client.get("/api/v1/live/positions")
    assert resp_pos.status_code == 200
    data_pos = resp_pos.json()
    assert "positions" in data_pos
    assert "total_positions" in data_pos


def test_api_live_risk_settings_and_update(client: TestClient) -> None:
    """Test GET and PUT /api/v1/live/risk-settings."""
    resp_get = client.get("/api/v1/live/risk-settings")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["max_daily_loss_pct"] == 3.0
    assert data_get["max_concurrent_trades"] == 5

    # Update risk limits
    resp_put = client.put(
        "/api/v1/live/risk-settings",
        json={
            "max_daily_loss_pct": 4.5,
            "max_concurrent_trades": 8,
        },
    )
    assert resp_put.status_code == 200
    data_put = resp_put.json()
    assert data_put["max_daily_loss_pct"] == 4.5
    assert data_put["max_concurrent_trades"] == 8


def test_api_live_tradebook(client: TestClient) -> None:
    """Test GET /api/v1/live/tradebook."""
    resp = client.get("/api/v1/live/tradebook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 1
    assert data["trades"][0]["dhan_order_id"] == "DH-LIVE-001"
    assert data["trades"][0]["realized_pnl"] == 1150.0
    assert data["trades"][0]["net_pnl"] == 1117.5  # 1150 - 32.5 charges


def test_api_live_emergency_kill_switch(client: TestClient) -> None:
    """Test POST /api/v1/live/kill-switch."""
    resp = client.post(
        "/api/v1/live/kill-switch",
        json={"reason": "Manual Operator Test Trigger"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kill_switch_active"] is True
    assert data["status"] == "EMERGENCY_HALTED"
    assert "Trading is HALTED" in data["message"]


def test_api_live_reconcile(client: TestClient) -> None:
    """Test POST /api/v1/live/reconcile."""
    resp = client.post("/api/v1/live/reconcile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("SYNCHRONIZED", "WARNING_MISMATCH")
    assert "broker_positions_count" in data
