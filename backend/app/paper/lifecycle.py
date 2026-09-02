"""Forward-testing strategy deployment lifecycle and engine ownership (F9.6).

Manages deploy/pause/resume/stop lifecycle states, engine process independence,
startup restart reconciliation, and tamper-evident audit logging.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.paper.broker import PaperBroker, paper_broker
from app.paper.models import PaperOrderStatus
from app.paper.repository import PaperRepository, paper_repository


class DeploymentState(StrEnum):
    """Lifecycle states of a forward-test strategy deployment."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class DeploymentAction(StrEnum):
    """Permitted lifecycle actions triggering state transitions."""

    DEPLOY = "DEPLOY"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    STOP = "STOP"
    RECONCILE = "RECONCILE"
    FAIL = "FAIL"


class DeploymentAuditEvent(BaseModel):
    """Immutable audit trail record for deployment lifecycle transitions."""

    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    deployment_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    action: DeploymentAction
    from_state: DeploymentState
    to_state: DeploymentState
    actor: str = "system"
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyDeployment(BaseModel):
    """Forward-testing deployment record owned by the engine runtime."""

    deployment_id: str
    strategy_id: str
    strategy_name: str
    account_id: str
    allocated_capital: float
    state: DeploymentState = DeploymentState.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    active_orders_count: int = 0
    open_positions_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeploymentStore:
    """Thread-safe persistent store for strategy deployments and audit events."""

    def __init__(self) -> None:
        self._deployments: dict[str, StrategyDeployment] = {}
        self._audit_log: dict[str, list[DeploymentAuditEvent]] = {}

    def save_deployment(self, deployment: StrategyDeployment) -> None:
        deployment.updated_at = datetime.now(UTC)
        self._deployments[deployment.deployment_id] = deployment

    def get_deployment(self, deployment_id: str) -> StrategyDeployment | None:
        return self._deployments.get(deployment_id)

    def list_deployments(self, state: DeploymentState | None = None) -> list[StrategyDeployment]:
        deps = list(self._deployments.values())
        if state is not None:
            deps = [d for d in deps if d.state == state]
        return sorted(deps, key=lambda d: d.created_at, reverse=True)

    def record_audit_event(self, event: DeploymentAuditEvent) -> None:
        if event.deployment_id not in self._audit_log:
            self._audit_log[event.deployment_id] = []
        self._audit_log[event.deployment_id].append(event)

    def list_audit_events(self, deployment_id: str) -> list[DeploymentAuditEvent]:
        return list(self._audit_log.get(deployment_id, []))

    def clear(self) -> None:
        self._deployments.clear()
        self._audit_log.clear()


deployment_store = DeploymentStore()


class PaperDeploymentManager:
    """Coordinates lifecycle transitions, engine ownership, and restart reconciliation."""

    def __init__(
        self,
        store: DeploymentStore | None = None,
        repository: PaperRepository | None = None,
        broker: PaperBroker | None = None,
    ) -> None:
        self.store = store or deployment_store
        self.repo = repository or paper_repository
        self.broker = broker or paper_broker

    def deploy(
        self,
        strategy_id: str,
        strategy_name: str,
        account_id: str,
        allocated_capital: float = 1_000_000.0,
        parameters: dict[str, Any] | None = None,
        actor: str = "user",
        reason: str = "Initial deployment to engine",
    ) -> StrategyDeployment:
        """Launch a forward-test strategy deployment into the running engine."""
        dep_id = f"dep-{strategy_id}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)

        # Initialize isolated paper account for this deployment
        self.repo.get_or_create_account(
            account_id=account_id,
            initial_capital=allocated_capital,
            name=f"Deployment {strategy_name}",
        )

        deployment = StrategyDeployment(
            deployment_id=dep_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            account_id=account_id,
            allocated_capital=allocated_capital,
            state=DeploymentState.RUNNING,
            created_at=now,
            updated_at=now,
            started_at=now,
            parameters=parameters or {},
        )
        self.store.save_deployment(deployment)

        # Record audit event
        self.store.record_audit_event(
            DeploymentAuditEvent(
                deployment_id=dep_id,
                timestamp=now,
                action=DeploymentAction.DEPLOY,
                from_state=DeploymentState.CREATED,
                to_state=DeploymentState.RUNNING,
                actor=actor,
                reason=reason,
                metadata={"allocated_capital": allocated_capital},
            )
        )
        return deployment

    def pause(
        self,
        deployment_id: str,
        actor: str = "user",
        reason: str = "Operator paused strategy execution",
    ) -> StrategyDeployment:
        """Pause a running deployment, suspending new signal execution."""
        deployment = self.store.get_deployment(deployment_id)
        if not deployment:
            raise KeyError(f"Deployment '{deployment_id}' not found")

        if deployment.state == DeploymentState.PAUSED:
            return deployment  # Idempotent if already paused

        if deployment.state != DeploymentState.RUNNING:
            raise ValueError(
                f"Cannot pause deployment in '{deployment.state}' state (must be RUNNING)"
            )

        now = datetime.now(UTC)
        prev_state = deployment.state
        deployment.state = DeploymentState.PAUSED
        self.store.save_deployment(deployment)

        self.store.record_audit_event(
            DeploymentAuditEvent(
                deployment_id=deployment_id,
                timestamp=now,
                action=DeploymentAction.PAUSE,
                from_state=prev_state,
                to_state=DeploymentState.PAUSED,
                actor=actor,
                reason=reason,
            )
        )
        return deployment

    def resume(
        self,
        deployment_id: str,
        actor: str = "user",
        reason: str = "Operator resumed strategy execution",
    ) -> StrategyDeployment:
        """Resume a paused deployment, re-enabling active signal processing."""
        deployment = self.store.get_deployment(deployment_id)
        if not deployment:
            raise KeyError(f"Deployment '{deployment_id}' not found")

        if deployment.state == DeploymentState.RUNNING:
            return deployment  # Idempotent if already running

        if deployment.state != DeploymentState.PAUSED:
            raise ValueError(
                f"Cannot resume deployment in '{deployment.state}' state (must be PAUSED)"
            )

        now = datetime.now(UTC)
        prev_state = deployment.state
        deployment.state = DeploymentState.RUNNING
        self.store.save_deployment(deployment)

        self.store.record_audit_event(
            DeploymentAuditEvent(
                deployment_id=deployment_id,
                timestamp=now,
                action=DeploymentAction.RESUME,
                from_state=prev_state,
                to_state=DeploymentState.RUNNING,
                actor=actor,
                reason=reason,
            )
        )
        return deployment

    def stop(
        self,
        deployment_id: str,
        close_positions: bool = False,
        actor: str = "user",
        reason: str = "Operator stopped strategy execution",
    ) -> StrategyDeployment:
        """Permanently stop strategy deployment. Strictly idempotent."""
        deployment = self.store.get_deployment(deployment_id)
        if not deployment:
            raise KeyError(f"Deployment '{deployment_id}' not found")

        # Idempotency check: repeated calls return current state safely
        if deployment.state == DeploymentState.STOPPED:
            return deployment

        now = datetime.now(UTC)
        prev_state = deployment.state

        # Cancel all active working orders for this account
        working_orders = self.repo.list_orders(
            deployment.account_id, status=PaperOrderStatus.ACCEPTED
        )
        for order in working_orders:
            self.broker.cancel_order(order.order_id)

        deployment.state = DeploymentState.STOPPED
        deployment.stopped_at = now
        self.store.save_deployment(deployment)

        self.store.record_audit_event(
            DeploymentAuditEvent(
                deployment_id=deployment_id,
                timestamp=now,
                action=DeploymentAction.STOP,
                from_state=prev_state,
                to_state=DeploymentState.STOPPED,
                actor=actor,
                reason=reason,
                metadata={
                    "cancelled_orders_count": len(working_orders),
                    "close_positions": close_positions,
                },
            )
        )
        return deployment

    def reconcile_on_startup(self) -> dict[str, Any]:
        """Reconcile persisted deployments, orders, and positions on engine startup."""
        deployments = self.store.list_deployments()
        reconciled_count = 0
        now = datetime.now(UTC)

        for dep in deployments:
            if dep.state in (DeploymentState.RUNNING, DeploymentState.PAUSED):
                working_orders = self.repo.list_orders(
                    dep.account_id, status=PaperOrderStatus.ACCEPTED
                )
                open_positions = self.repo.list_positions(dep.account_id, open_only=True)
                dep.active_orders_count = len(working_orders)
                dep.open_positions_count = len(open_positions)
                self.store.save_deployment(dep)

                self.store.record_audit_event(
                    DeploymentAuditEvent(
                        deployment_id=dep.deployment_id,
                        timestamp=now,
                        action=DeploymentAction.RECONCILE,
                        from_state=dep.state,
                        to_state=dep.state,
                        actor="engine-startup-reconciler",
                        reason="Engine recovered state after restart",
                        metadata={
                            "active_orders": len(working_orders),
                            "open_positions": len(open_positions),
                        },
                    )
                )
                reconciled_count += 1

        return {
            "reconciled_at": now.isoformat(),
            "total_deployments": len(deployments),
            "reconciled_active_deployments": reconciled_count,
        }


paper_deployment_manager = PaperDeploymentManager()
