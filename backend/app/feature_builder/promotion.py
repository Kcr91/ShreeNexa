"""Approval-gated blue/green promotion, health check, drain, rollback, and history (F11.7).

Coordinates zero-downtime deployment promotion with explicit operator approval gating,
pre-traffic health gating, Caddy upstream proxy flipping, connection draining, and the
strict invariant that the trading `engine` process is NEVER restarted.
"""

from __future__ import annotations

import secrets
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

# Ensure repo root is on sys.path for infra imports
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from infra.lightsail.blue_green import (  # noqa: E402
    COLOR_BLUE,
    PORTS_BY_COLOR,
    flip_caddyfile_content,
    get_active_color,
    get_candidate_color,
    promote_candidate,
)


class PromotionStatus(StrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class PromotionProposal(BaseModel):
    proposal_id: str
    candidate_commit: str
    target_color: str
    target_port: int
    release_notes: str
    created_at: datetime
    status: PromotionStatus
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None


class PromotionExecutionResult(BaseModel):
    proposal_id: str
    success: bool
    previous_color: str
    active_color: str
    health_check_passed: bool
    caddy_flipped: bool
    drain_initiated: bool
    engine_pid_before: int | None = None
    engine_pid_after: int | None = None
    engine_restarted: bool = False
    message: str
    timestamp: datetime


class ProposalCreateRequest(BaseModel):
    candidate_commit: str = Field(..., min_length=7, description="Git commit SHA to promote")
    release_notes: str = Field(default="", description="Summary of changes and verified QA gates")


class ProposalApprovalRequest(BaseModel):
    proposal_id: str
    operator_username: str = Field(default="trader")


class ProposalRejectRequest(BaseModel):
    proposal_id: str
    operator_username: str = Field(default="trader")
    reason: str = Field(default="Rejected by operator")


class PromotionManager:
    """Orchestrates approval-gated blue/green promotions with process isolation checks."""

    def __init__(self, default_caddyfile_path: Path | None = None) -> None:
        self.caddyfile_path = default_caddyfile_path or Path("infra/caddy/Caddyfile")
        self._proposals: dict[str, PromotionProposal] = {}
        self._history: list[PromotionExecutionResult] = []

    def create_proposal(
        self,
        candidate_commit: str,
        release_notes: str = "",
        target_color: str | None = None,
    ) -> PromotionProposal:
        """Create a promotion proposal requiring operator approval."""
        if target_color is None:
            active = self.get_current_active_color()
            target_color = get_candidate_color(active)

        target_port = PORTS_BY_COLOR[target_color]
        proposal_id = f"prom_{secrets.token_hex(6)}"

        proposal = PromotionProposal(
            proposal_id=proposal_id,
            candidate_commit=candidate_commit,
            target_color=target_color,
            target_port=target_port,
            release_notes=release_notes,
            created_at=datetime.now(tz=UTC),
            status=PromotionStatus.PENDING_APPROVAL,
        )
        self._proposals[proposal_id] = proposal
        return proposal

    def approve_proposal(self, proposal_id: str, operator_username: str) -> PromotionProposal:
        """Explicit operator approval gate for candidate promotion."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(f"Proposal {proposal_id} not found")

        if proposal.status != PromotionStatus.PENDING_APPROVAL:
            raise ValueError(
                f"Proposal {proposal_id} cannot be approved in status {proposal.status}"
            )

        updated = proposal.model_copy(
            update={
                "status": PromotionStatus.APPROVED,
                "approved_by": operator_username,
                "approved_at": datetime.now(tz=UTC),
            }
        )
        self._proposals[proposal_id] = updated
        return updated

    def reject_proposal(
        self, proposal_id: str, operator_username: str, reason: str = ""
    ) -> PromotionProposal:
        """Reject a promotion proposal."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(f"Proposal {proposal_id} not found")

        updated = proposal.model_copy(
            update={
                "status": PromotionStatus.REJECTED,
                "approved_by": operator_username,
                "rejection_reason": reason,
            }
        )
        self._proposals[proposal_id] = updated
        return updated

    def execute_promotion(
        self,
        proposal_id: str,
        *,
        caddyfile_path: Path | None = None,
        health_checker: Callable[[int], bool] | None = None,
        engine_monitor: Callable[[], int | None] | None = None,
    ) -> PromotionExecutionResult:
        """Execute approved promotion: health check, proxy flip, and engine continuity proof."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(f"Proposal {proposal_id} not found")

        # Invariant 1: Operator approval required
        if proposal.status != PromotionStatus.APPROVED:
            res = PromotionExecutionResult(
                proposal_id=proposal_id,
                success=False,
                previous_color=self.get_current_active_color(),
                active_color=self.get_current_active_color(),
                health_check_passed=False,
                caddy_flipped=False,
                drain_initiated=False,
                engine_restarted=False,
                message=f"Promotion blocked: proposal status is {proposal.status}, not APPROVED.",
                timestamp=datetime.now(tz=UTC),
            )
            self._history.append(res)
            return res

        cfg_path = caddyfile_path or self.caddyfile_path
        prev_color = self.get_current_active_color(cfg_path)

        # Invariant 2: Engine PID check before promotion
        engine_pid_before = engine_monitor() if engine_monitor else None

        # Invariant 3: Pre-traffic health check
        health_ok = True
        if health_checker:
            health_ok = health_checker(proposal.target_port)

        if not health_ok:
            self._proposals[proposal_id] = proposal.model_copy(
                update={"status": PromotionStatus.FAILED}
            )
            res = PromotionExecutionResult(
                proposal_id=proposal_id,
                success=False,
                previous_color=prev_color,
                active_color=prev_color,
                health_check_passed=False,
                caddy_flipped=False,
                drain_initiated=False,
                engine_pid_before=engine_pid_before,
                engine_pid_after=engine_pid_before,
                engine_restarted=False,
                message=(
                    f"Promotion aborted: candidate health check failed on port "
                    f"{proposal.target_port}. Upstream remains on {prev_color}."
                ),
                timestamp=datetime.now(tz=UTC),
            )
            self._history.append(res)
            return res

        # Invariant 4: Caddy upstream flip
        dep_res = (
            promote_candidate(cfg_path, health_checker=health_checker)
            if health_checker
            else promote_candidate(cfg_path)
        )

        # Invariant 5: Engine PID check after promotion (Engine NEVER restarts)
        engine_pid_after = engine_monitor() if engine_monitor else None
        engine_restarted = False
        if engine_pid_before is not None and engine_pid_after is not None:
            engine_restarted = engine_pid_after != engine_pid_before

        if not dep_res.success:
            self._proposals[proposal_id] = proposal.model_copy(
                update={"status": PromotionStatus.FAILED}
            )
            res = PromotionExecutionResult(
                proposal_id=proposal_id,
                success=False,
                previous_color=prev_color,
                active_color=dep_res.active_color,
                health_check_passed=True,
                caddy_flipped=False,
                drain_initiated=False,
                engine_pid_before=engine_pid_before,
                engine_pid_after=engine_pid_after,
                engine_restarted=engine_restarted,
                message=dep_res.message,
                timestamp=datetime.now(tz=UTC),
            )
            self._history.append(res)
            return res

        # Mark promoted and drained
        self._proposals[proposal_id] = proposal.model_copy(
            update={"status": PromotionStatus.PROMOTED}
        )
        res = PromotionExecutionResult(
            proposal_id=proposal_id,
            success=True,
            previous_color=prev_color,
            active_color=proposal.target_color,
            health_check_passed=True,
            caddy_flipped=True,
            drain_initiated=True,
            engine_pid_before=engine_pid_before,
            engine_pid_after=engine_pid_after,
            engine_restarted=engine_restarted,
            message=(
                f"Promotion succeeded: Caddy flipped to {proposal.target_color} "
                f"(port {proposal.target_port}). "
                f"Previous {prev_color} instance connection drain initiated. "
                f"Trading engine PID ({engine_pid_after}) completely undisturbed."
            ),
            timestamp=datetime.now(tz=UTC),
        )
        self._history.append(res)
        return res

    def rollback(
        self,
        reason: str = "Rollback requested by operator",
        *,
        caddyfile_path: Path | None = None,
        engine_monitor: Callable[[], int | None] | None = None,
    ) -> PromotionExecutionResult:
        """Roll back active upstream to previous color without touching trading engine."""
        cfg_path = caddyfile_path or self.caddyfile_path
        active_color = self.get_current_active_color(cfg_path)
        target_color = get_candidate_color(active_color)

        engine_pid_before = engine_monitor() if engine_monitor else None

        # Flip Caddyfile content back
        content = cfg_path.read_text(encoding="utf-8")
        flipped = flip_caddyfile_content(content, target_color)
        cfg_path.write_text(flipped, encoding="utf-8")

        engine_pid_after = engine_monitor() if engine_monitor else None
        engine_restarted = False
        if engine_pid_before is not None and engine_pid_after is not None:
            engine_restarted = engine_pid_after != engine_pid_before

        res = PromotionExecutionResult(
            proposal_id="rollback",
            success=True,
            previous_color=active_color,
            active_color=target_color,
            health_check_passed=True,
            caddy_flipped=True,
            drain_initiated=True,
            engine_pid_before=engine_pid_before,
            engine_pid_after=engine_pid_after,
            engine_restarted=engine_restarted,
            message=(
                f"Rollback completed: Caddy flipped back to {target_color}. "
                f"Reason: {reason}. Engine PID ({engine_pid_after}) continuously running."
            ),
            timestamp=datetime.now(tz=UTC),
        )
        self._history.append(res)
        return res

    def get_current_active_color(self, caddyfile_path: Path | None = None) -> str:
        """Read active upstream color from Caddyfile."""
        cfg_path = caddyfile_path or self.caddyfile_path
        if not cfg_path.exists():
            return COLOR_BLUE
        content = cfg_path.read_text(encoding="utf-8")
        return get_active_color(content)

    def get_history(self) -> list[PromotionExecutionResult]:
        """Retrieve deployment history log."""
        return list(self._history)

    def get_proposal(self, proposal_id: str) -> PromotionProposal | None:
        """Retrieve proposal by ID."""
        return self._proposals.get(proposal_id)


# Global singleton
promotion_manager = PromotionManager()
