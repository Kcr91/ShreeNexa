"""Unit test suite for Feature 5: Paper Trading Engine, Shadow Tracker & Readiness Score."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import pytest
from app.api.deps import require_csrf, require_non_demo_session, require_session
from app.api.paper_engine import get_db_engine
from app.main import app
from app.paper.paper_adapter import PaperExecutionAdapter
from app.paper.readiness_engine import (
    compute_readiness_score,
    generate_drift_analysis,
    generate_quick_comparison,
)
from app.paper.shadow_tracker import ShadowVariantTracker
from app.strategy.models import metadata, strategy_configs_table
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_engine() -> Generator[Engine]:
    """In-memory SQLite engine for paper trading testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(sqlite_engine: Engine) -> Generator[TestClient]:
    """TestClient with database dependency and auth overrides."""
    app.dependency_overrides[get_db_engine] = lambda: sqlite_engine
    app.dependency_overrides[require_session] = lambda: {"user_id": "test_user"}
    app.dependency_overrides[require_non_demo_session] = lambda: {"user_id": "test_user"}
    app.dependency_overrides[require_csrf] = lambda: None

    tc = TestClient(app, raise_server_exceptions=True)
    yield tc

    app.dependency_overrides.clear()


def sample_strategy_dict() -> dict[str, Any]:
    """Sample strategy definition for paper session testing."""
    return {
        "strategy_type": "OPTION",
        "name": "Paper Test Strategy",
        "version": 1,
        "part_1_scope": {"underlying_symbol": "NIFTY"},
        "part_2_entry": {"direction": "LONG", "conditions": []},
        "part_3_stoploss": {"sl_type": "PERCENTAGE", "percentage_val": 20.0},
        "part_4_exit": {
            "targets": [
                {"target_number": 1, "percentage_gain": 40.0, "exit_lots_percentage": 100.0}
            ]
        },
    }


def test_readiness_score_engine() -> None:
    """Verify 0-100% Go/No-Go readiness score calculation and threshold verdicts."""
    # High match scenario (>= 80%)
    high_match = compute_readiness_score(
        paper_pnl=18500.0,
        expected_pnl=19200.0,
        paper_win_rate=64.2,
        backtest_win_rate=66.0,
        paper_drawdown_pct=4.8,
        backtest_drawdown_pct=5.2,
        total_trades=28,
    )
    assert high_match.total_readiness_score >= 80.0
    assert high_match.verdict == "READY_FOR_LIVE"
    assert "Ready for live deployment" in high_match.verdict_message

    # Low sample size & heavy drift scenario (< 80%)
    low_match = compute_readiness_score(
        paper_pnl=2000.0,
        expected_pnl=15000.0,
        paper_win_rate=40.0,
        backtest_win_rate=65.0,
        paper_drawdown_pct=12.0,
        backtest_drawdown_pct=5.0,
        total_trades=4,
    )
    assert low_match.total_readiness_score < 80.0
    assert low_match.verdict == "NEEDS_FURTHER_VALIDATION"


def test_quick_comparison_and_drift_generators() -> None:
    """Verify quick comparison card and drift analysis response structures."""
    qc = generate_quick_comparison(
        strategy_id=1,
        strategy_name="Nifty Strategy",
        session_id=10,
        paper_pnl=18500.0,
        backtest_pnl=19200.0,
        paper_win_rate=64.2,
        backtest_win_rate=66.0,
        paper_dd=4.8,
        backtest_dd=5.2,
        paper_trades_count=28,
        backtest_trades_count=30,
        open_positions=[],
        shadow_leaderboard=[],
    )
    assert len(qc.metrics) == 4
    assert qc.metrics[0].status == "ON_TRACK"
    assert qc.metrics[1].status == "STABLE"

    drift = generate_drift_analysis(
        session_id=10,
        strategy_name="Nifty Strategy",
        paper_pnl=18500.0,
        backtest_pnl=19200.0,
        paper_win_rate=64.2,
        backtest_win_rate=66.0,
        paper_dd=4.8,
        backtest_dd=5.2,
        total_paper_trades=28,
    )
    assert drift.win_rate_drift_pct == -1.8
    assert drift.readiness.total_readiness_score >= 80.0


def test_shadow_variant_tracker_leaderboard() -> None:
    """Verify in-memory shadow variant tracker and leaderboard rankings."""
    tracker = ShadowVariantTracker(strategy_id=1)

    # Record trades across baseline and shadow variants
    tracker.variants["Variant 0 (Baseline Default)"].record_trade(1500.0)
    tracker.variants["Variant 1 (Multi-Target Grid)"].record_trade(2400.0)
    tracker.variants["Variant 2 (Trailing SL Grid)"].record_trade(1200.0)

    leaderboard = tracker.get_leaderboard()
    assert len(leaderboard) == 3
    # Variant 1 made 2400 > Baseline 1500 -> Outperforming Baseline is True
    v1 = next(
        item for item in leaderboard if item["variant_name"] == "Variant 1 (Multi-Target Grid)"
    )
    assert v1["outperforming_baseline"] is True
    assert leaderboard[0]["variant_name"] == "Variant 1 (Multi-Target Grid)"


def test_paper_execution_adapter(sqlite_engine: Engine) -> None:
    """Verify paper execution adapter order opening, latency simulation, and square-off."""
    adapter = PaperExecutionAdapter(engine=sqlite_engine, simulated_latency_ms=10)

    # 1. Create a paper session in DB
    now = datetime.now(UTC)
    with sqlite_engine.begin() as conn:
        s_res = conn.execute(
            insert(strategy_configs_table).values(
                name="Adapter Test Strat",
                strategy_type="OPTION",
                current_version=1,
                is_active=True,
                config_json=sample_strategy_dict(),
                created_at=now,
                updated_at=now,
            )
        )
        strat_id = s_res.inserted_primary_key[0]  # type: ignore[index]

    # Create session via API or direct insert
    from app.paper.paper_models import paper_sessions_table

    with sqlite_engine.begin() as conn:
        sess_res = conn.execute(
            insert(paper_sessions_table).values(
                strategy_id=strat_id,
                session_name="Session 1",
                status="RUNNING",
                initial_capital=500000.0,
                current_capital=500000.0,
                start_time=now,
                readiness_score=0.0,
            )
        )
        session_id = sess_res.inserted_primary_key[0]  # type: ignore[index]

    # 2. Open Position
    pos_res = adapter.open_position(
        session_id=session_id,
        symbol="NIFTY26OCT25000PE",
        signal_type="BUY",
        price=150.0,
        quantity=50,
        active_sl=120.0,
        active_target=210.0,
    )
    assert pos_res["status"] == "OPENED"
    pos_id = pos_res["position_id"]

    # 3. Square off Position
    sq_res = adapter.square_off_position(
        position_id=pos_id,
        exit_price=180.0,
        exit_reason="TARGET_1",
    )
    assert sq_res["status"] == "CLOSED"
    assert sq_res["realized_pnl"] > 1400.0  # (180 - 150) * 50 = 1500 - costs


def test_paper_api_endpoints(client: TestClient, sqlite_engine: Engine) -> None:
    """Test full FastAPI REST endpoints for Paper Trading Engine."""
    now = datetime.now(UTC)

    # 1. Seed strategy
    with sqlite_engine.begin() as conn:
        res = conn.execute(
            insert(strategy_configs_table).values(
                name="Paper API Test Strat",
                strategy_type="OPTION",
                current_version=1,
                is_active=True,
                config_json=sample_strategy_dict(),
                created_at=now,
                updated_at=now,
            )
        )
        strat_id = res.inserted_primary_key[0]  # type: ignore[index]

    # 2. Start Paper Session
    start_payload = {
        "strategy_id": strat_id,
        "session_name": "Paper Alpha Session 1",
        "initial_capital": 500000.00,
    }
    start_resp = client.post("/api/v1/paper/sessions", json=start_payload)
    assert start_resp.status_code == 201
    session_data = start_resp.json()
    session_id = session_data["session_id"]
    assert session_data["session_name"] == "Paper Alpha Session 1"
    assert session_data["status"] == "RUNNING"

    # 3. List Sessions
    list_resp = client.get("/api/v1/paper/sessions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 4. Pause Session
    pause_resp = client.post(f"/api/v1/paper/sessions/{session_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    # 5. Resume Session
    resume_resp = client.post(f"/api/v1/paper/sessions/{session_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "RUNNING"

    # 6. Quick Compare
    qc_resp = client.get(f"/api/v1/paper/sessions/{session_id}/quick-compare")
    assert qc_resp.status_code == 200
    qc_data = qc_resp.json()
    assert len(qc_data["metrics"]) == 4
    assert len(qc_data["shadow_leaderboard"]) >= 2

    # 7. Drift Analysis
    drift_resp = client.get(f"/api/v1/paper/sessions/{session_id}/drift-analysis")
    assert drift_resp.status_code == 200
    drift_data = drift_resp.json()
    assert "readiness" in drift_data
    assert drift_data["readiness"]["total_readiness_score"] >= 80.0

    # 8. Square off Session Positions
    sq_resp = client.post(f"/api/v1/paper/sessions/{session_id}/squareoff")
    assert sq_resp.status_code == 200
    assert sq_resp.json()["status"] == "SQUARED_OFF"

    # 9. 1-Click Switch to Live
    live_resp = client.post(f"/api/v1/paper/sessions/{session_id}/switch-to-live")
    assert live_resp.status_code == 200
    live_data = live_resp.json()
    assert live_data["current_mode"] == "LIVE"
    assert live_data["status"] == "SWITCHED_SUCCESS"
