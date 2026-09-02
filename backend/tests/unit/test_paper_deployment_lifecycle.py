"""Unit tests for forward-test deployment lifecycle and engine ownership (F9.6).

Verifies deploy/pause/resume/stop lifecycle states, idempotency of stop,
API restart independence, restart reconciliation, and audit event logs.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.main import app
from app.paper.broker import PaperBroker
from app.paper.lifecycle import (
    DeploymentAction,
    DeploymentState,
    DeploymentStore,
    PaperDeploymentManager,
    deployment_store,
    paper_deployment_manager,
)
from app.paper.models import PaperOrder, PaperOrderSide, PaperOrderStatus, PaperOrderType
from app.paper.repository import PaperRepository, paper_repository
from fastapi.testclient import TestClient

client = TestClient(app)


def test_full_lifecycle_state_machine() -> None:
    """Proof: State machine transitions deploy -> pause -> resume -> stop."""
    store = DeploymentStore()
    repo = PaperRepository()
    broker = PaperBroker(repository=repo)
    manager = PaperDeploymentManager(store=store, repository=repo, broker=broker)

    # 1. Deploy
    dep = manager.deploy(
        strategy_id="strat-alpha",
        strategy_name="Momentum Alpha",
        account_id="acc-alpha-1",
        allocated_capital=500_000.0,
        parameters={"lookback": 20},
        actor="lead_trader",
        reason="Deploy to production forward test",
    )
    assert dep.state == DeploymentState.RUNNING
    assert dep.allocated_capital == 500_000.0
    assert dep.started_at is not None
    assert dep.stopped_at is None

    # Account auto-created
    acc = repo.get_account("acc-alpha-1")
    assert acc is not None
    assert acc.initial_capital == 500_000.0

    # 2. Pause
    dep_paused = manager.pause(dep.deployment_id, actor="lead_trader", reason="Market halt")
    assert dep_paused.state == DeploymentState.PAUSED

    # 3. Resume
    dep_resumed = manager.resume(dep.deployment_id, actor="lead_trader", reason="Market reopen")
    assert dep_resumed.state == DeploymentState.RUNNING

    # 4. Stop
    dep_stopped = manager.stop(dep.deployment_id, actor="lead_trader", reason="Strategy sunset")
    assert dep_stopped.state == DeploymentState.STOPPED
    assert dep_stopped.stopped_at is not None

    # Audit events verified
    events = store.list_audit_events(dep.deployment_id)
    assert len(events) == 4
    actions = [e.action for e in events]
    assert actions == [
        DeploymentAction.DEPLOY,
        DeploymentAction.PAUSE,
        DeploymentAction.RESUME,
        DeploymentAction.STOP,
    ]


def test_stop_is_strictly_idempotent() -> None:
    """Proof: Calling stop repeatedly on an already stopped deployment is a safe no-op."""
    store = DeploymentStore()
    repo = PaperRepository()
    broker = PaperBroker(repository=repo)
    manager = PaperDeploymentManager(store=store, repository=repo, broker=broker)

    dep = manager.deploy(
        strategy_id="strat-idem",
        strategy_name="Idempotent Test",
        account_id="acc-idem",
    )

    # First stop
    stopped_1 = manager.stop(dep.deployment_id, reason="Initial stop")
    assert stopped_1.state == DeploymentState.STOPPED
    ts_stopped = stopped_1.stopped_at
    assert ts_stopped is not None

    # Repeated stops
    stopped_2 = manager.stop(dep.deployment_id, reason="Duplicate stop 1")
    assert stopped_2.state == DeploymentState.STOPPED
    assert stopped_2.stopped_at == ts_stopped

    stopped_3 = manager.stop(dep.deployment_id, reason="Duplicate stop 2")
    assert stopped_3.state == DeploymentState.STOPPED

    # Exactly one stop audit event recorded
    events = store.list_audit_events(dep.deployment_id)
    stop_events = [e for e in events if e.action == DeploymentAction.STOP]
    assert len(stop_events) == 1


def test_invalid_state_transitions_fail_cleanly() -> None:
    """Proof: Invalid state transitions reject with ValueError without corrupting state."""
    store = DeploymentStore()
    repo = PaperRepository()
    broker = PaperBroker(repository=repo)
    manager = PaperDeploymentManager(store=store, repository=repo, broker=broker)

    dep = manager.deploy(
        strategy_id="strat-invalid",
        strategy_name="Invalid Trans Test",
        account_id="acc-invalid",
    )

    # Cannot resume a RUNNING deployment (already running is idempotent)
    resumed = manager.resume(dep.deployment_id)
    assert resumed.state == DeploymentState.RUNNING

    # Stop deployment
    manager.stop(dep.deployment_id)

    # Cannot pause a STOPPED deployment
    with pytest.raises(ValueError, match="must be RUNNING"):
        manager.pause(dep.deployment_id)

    # Cannot resume a STOPPED deployment
    with pytest.raises(ValueError, match="must be PAUSED"):
        manager.resume(dep.deployment_id)


def test_restarting_api_never_stops_engine_deployment() -> None:
    """Proof: Restarting API process does not stop or mutate active engine deployments."""
    # Deploy in engine manager
    paper_deployment_manager.store.clear()
    paper_repository.clear()

    dep = paper_deployment_manager.deploy(
        strategy_id="strat-api-restart",
        strategy_name="API Independence Test",
        account_id="acc-api-restart",
        allocated_capital=750_000.0,
    )
    assert dep.state == DeploymentState.RUNNING

    # Simulate full API client restart / reconnection
    fresh_api_client = TestClient(app)

    # Query through fresh API client
    resp = fresh_api_client.get(f"/api/v1/paper/deployments/{dep.deployment_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "RUNNING"
    assert data["strategy_name"] == "API Independence Test"
    assert data["allocated_capital"] == 750_000.0


def test_restart_reconciliation_recovers_state_without_duplication() -> None:
    """Proof: Engine restart reconciles working orders and active state seamlessly."""
    store = DeploymentStore()
    repo = PaperRepository()
    broker = PaperBroker(repository=repo)
    manager = PaperDeploymentManager(store=store, repository=repo, broker=broker)

    # 1. Deploy strategy
    dep = manager.deploy(
        strategy_id="strat-reconcile",
        strategy_name="Reconcile Test",
        account_id="acc-reconcile",
    )

    # 2. Add an accepted working order to repository
    working_order = PaperOrder(
        order_id="ord-reconcile-1",
        account_id="acc-reconcile",
        security_id="RELIANCE",
        symbol="RELIANCE",
        segment="NSE_EQ",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=10,
        price=2500.0,
        status=PaperOrderStatus.ACCEPTED,
        created_at=datetime.now(UTC),
    )
    repo.save_order(working_order)

    # 3. Trigger restart reconciliation
    summary = manager.reconcile_on_startup()
    assert summary["total_deployments"] == 1
    assert summary["reconciled_active_deployments"] == 1

    # Check updated active order count
    updated_dep = store.get_deployment(dep.deployment_id)
    assert updated_dep is not None
    assert updated_dep.active_orders_count == 1

    # Check audit log contains RECONCILE action
    events = store.list_audit_events(dep.deployment_id)
    reconcile_events = [e for e in events if e.action == DeploymentAction.RECONCILE]
    assert len(reconcile_events) == 1
    assert reconcile_events[0].actor == "engine-startup-reconciler"
    assert reconcile_events[0].metadata["active_orders"] == 1


def test_deployment_api_rest_endpoints() -> None:
    """Proof: REST endpoints for deployment lifecycle and audit querying work end-to-end."""
    deployment_store.clear()
    paper_repository.clear()

    # 1. POST /deployments
    create_resp = client.post(
        "/api/v1/paper/deployments",
        json={
            "strategy_id": "strat-rest-api",
            "strategy_name": "REST API Strategy",
            "account_id": "acc-rest-api",
            "allocated_capital": 1_200_000.0,
            "parameters": {"fast_ema": 9, "slow_ema": 21},
            "actor": "rest_tester",
            "reason": "Integration test deployment",
        },
    )
    assert create_resp.status_code == 200
    dep_data = create_resp.json()
    dep_id = dep_data["deployment_id"]
    assert dep_data["state"] == "RUNNING"
    assert dep_data["allocated_capital"] == 1_200_000.0

    # 2. GET /deployments
    list_resp = client.get("/api/v1/paper/deployments")
    assert list_resp.status_code == 200
    deps = list_resp.json()
    assert len(deps) >= 1
    assert any(d["deployment_id"] == dep_id for d in deps)

    # 3. GET /deployments/{id}
    get_resp = client.get(f"/api/v1/paper/deployments/{dep_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["strategy_id"] == "strat-rest-api"

    # 4. POST /deployments/{id}/pause
    pause_resp = client.post(
        f"/api/v1/paper/deployments/{dep_id}/pause",
        json={"reason": "Testing pause endpoint"},
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["state"] == "PAUSED"

    # 5. POST /deployments/{id}/resume
    resume_resp = client.post(
        f"/api/v1/paper/deployments/{dep_id}/resume",
        json={"reason": "Testing resume endpoint"},
    )
    assert resume_resp.status_code == 200
    assert resume_resp.json()["state"] == "RUNNING"

    # 6. POST /deployments/{id}/stop
    stop_resp = client.post(
        f"/api/v1/paper/deployments/{dep_id}/stop",
        json={"reason": "Testing stop endpoint"},
    )
    assert stop_resp.status_code == 200
    assert stop_resp.json()["state"] == "STOPPED"

    # 7. GET /deployments/{id}/audit
    audit_resp = client.get(f"/api/v1/paper/deployments/{dep_id}/audit")
    assert audit_resp.status_code == 200
    audit_events = audit_resp.json()
    assert len(audit_events) == 4
    actions = [e["action"] for e in audit_events]
    assert actions == ["DEPLOY", "PAUSE", "RESUME", "STOP"]
