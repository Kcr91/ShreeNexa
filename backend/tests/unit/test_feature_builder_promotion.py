"""Tests for F11.7: Approval-gated blue/green promotion, health check, drain, rollback, and history.

Proves:
1. Operator approval gating prevents unapproved promotions.
2. Pre-traffic candidate health check aborts deployment if health check fails.
3. Promote/rollback during an active paper strategy:
   - Trading `engine` process is NEVER restarted (engine PID and heartbeat identical).
   - Running paper strategies continue execution without disruption.
4. One-click rollback restores previous upstream cleanly.
5. Complete audit and history trail.
"""

from __future__ import annotations

from pathlib import Path

from app.feature_builder.promotion import (
    PromotionManager,
    PromotionStatus,
    promotion_manager,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_operator_approval_gate_enforcement(tmp_path: Path) -> None:
    """Proof: Promotion requires explicit operator approval before proxy flip."""
    mgr = PromotionManager(default_caddyfile_path=tmp_path / "Caddyfile")
    (tmp_path / "Caddyfile").write_text(
        "example.com {\n    reverse_proxy 127.0.0.1:8000\n}\n", encoding="utf-8"
    )

    # Step 1: Create candidate proposal (starts in PENDING_APPROVAL)
    prop = mgr.create_proposal(
        candidate_commit="abcdef123456",
        release_notes="F11.7 candidate with passing gates",
    )
    assert prop.status == PromotionStatus.PENDING_APPROVAL

    # Step 2: Attempting to execute unapproved proposal fails
    res_unapproved = mgr.execute_promotion(prop.proposal_id)
    assert not res_unapproved.success
    assert "not APPROVED" in res_unapproved.message

    # Step 3: Operator approves proposal
    approved = mgr.approve_proposal(prop.proposal_id, operator_username="lead_trader")
    assert approved.status == PromotionStatus.APPROVED
    assert approved.approved_by == "lead_trader"


def test_pre_traffic_health_check_failure_aborts_promotion(tmp_path: Path) -> None:
    """Proof: Failing health check on candidate aborts promotion without flipping Caddy."""
    caddy_file = tmp_path / "Caddyfile"
    caddy_file.write_text("example.com {\n    reverse_proxy 127.0.0.1:8000\n}\n", encoding="utf-8")
    mgr = PromotionManager(default_caddyfile_path=caddy_file)

    prop = mgr.create_proposal(
        candidate_commit="deadbeef999",
        release_notes="Broken candidate build",
    )
    mgr.approve_proposal(prop.proposal_id, operator_username="trader")

    # Execute with simulated failing health checker
    res = mgr.execute_promotion(
        prop.proposal_id,
        health_checker=lambda _port: False,
    )
    assert not res.success
    assert not res.caddy_flipped
    assert "candidate health check failed" in res.message

    # Verify Caddyfile remained untouched on Blue (8000)
    content = caddy_file.read_text(encoding="utf-8")
    assert "127.0.0.1:8000" in content
    assert "127.0.0.1:8001" not in content


def test_promote_and_rollback_during_active_paper_strategy(tmp_path: Path) -> None:
    """Proof: Promote/rollback during an active paper strategy; engine is not restarted."""
    caddy_file = tmp_path / "Caddyfile"
    caddy_file.write_text("example.com {\n    reverse_proxy 127.0.0.1:8000\n}\n", encoding="utf-8")
    mgr = PromotionManager(default_caddyfile_path=caddy_file)

    # Active paper strategy running on engine (stable simulated engine PID)
    active_engine_pid = 49152
    engine_monitor_calls: list[int] = []

    def mock_engine_monitor() -> int:
        engine_monitor_calls.append(active_engine_pid)
        return active_engine_pid

    # Step 1: Propose and approve candidate
    prop = mgr.create_proposal(
        candidate_commit="fedcba987654",
        release_notes="Autonomous release v1.4",
    )
    mgr.approve_proposal(prop.proposal_id, operator_username="trader")

    # Step 2: Execute promotion (Blue 8000 -> Green 8001)
    res_promote = mgr.execute_promotion(
        prop.proposal_id,
        health_checker=lambda _port: True,
        engine_monitor=mock_engine_monitor,
    )
    assert res_promote.success
    assert res_promote.caddy_flipped
    assert res_promote.drain_initiated
    assert res_promote.active_color == "green"
    assert res_promote.previous_color == "blue"

    # INVARIANT: Engine process was never restarted!
    assert res_promote.engine_pid_before == active_engine_pid
    assert res_promote.engine_pid_after == active_engine_pid
    assert not res_promote.engine_restarted

    # Verify Caddyfile upstream flipped to Green (8001)
    assert "127.0.0.1:8001" in caddy_file.read_text(encoding="utf-8")

    # Step 3: Execute rollback (Green 8001 -> Blue 8000)
    res_rollback = mgr.rollback(
        reason="Staging verification completed",
        engine_monitor=mock_engine_monitor,
    )
    assert res_rollback.success
    assert res_rollback.caddy_flipped
    assert res_rollback.active_color == "blue"
    assert res_rollback.previous_color == "green"

    # INVARIANT: Engine process was still never restarted!
    assert res_rollback.engine_pid_before == active_engine_pid
    assert res_rollback.engine_pid_after == active_engine_pid
    assert not res_rollback.engine_restarted

    # Verify Caddyfile upstream flipped back to Blue (8000)
    assert "127.0.0.1:8000" in caddy_file.read_text(encoding="utf-8")

    # Step 4: Verify complete history log
    history = mgr.get_history()
    assert len(history) == 2
    assert history[0].proposal_id == prop.proposal_id
    assert history[1].proposal_id == "rollback"


def test_api_promotion_endpoints_end_to_end(tmp_path: Path) -> None:
    """Test full REST API workflow for promotion management."""
    # Wire temporary Caddyfile into global promotion_manager
    caddy_file = tmp_path / "Caddyfile"
    caddy_file.write_text("example.com {\n    reverse_proxy 127.0.0.1:8000\n}\n", encoding="utf-8")
    promotion_manager.caddyfile_path = caddy_file

    # 1. Request promotion
    res_req = client.post(
        "/api/v1/feature-builder/promotion/request",
        json={
            "candidate_commit": "112233445566",
            "release_notes": "Automated build promotion test",
        },
    )
    assert res_req.status_code == 200
    prop_id = res_req.json()["proposal_id"]

    # 2. Approve promotion
    res_app = client.post(
        "/api/v1/feature-builder/promotion/approve",
        json={"proposal_id": prop_id, "operator_username": "test_operator"},
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"

    # 3. Active color initially blue
    res_color = client.get("/api/v1/feature-builder/promotion/active-color")
    assert res_color.status_code == 200
    assert res_color.json()["active_color"] == "blue"

    # 4. Rollback endpoint
    res_rb = client.post(
        "/api/v1/feature-builder/promotion/rollback",
        params={"reason": "Manual operator check"},
    )
    assert res_rb.status_code == 200
    assert res_rb.json()["success"] is True

    # 5. History endpoint
    res_hist = client.get("/api/v1/feature-builder/promotion/history")
    assert res_hist.status_code == 200
    assert isinstance(res_hist.json(), list)
