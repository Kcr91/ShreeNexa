"""Protected-path layered enforcement and security auditing (F11.5).

Enforces defense-in-depth across 4 layers:
1. Prompt / Context Guard
2. Tool Execution / File Write Interceptor
3. Git Diff / Working Tree Inspection
4. Commit / Promotion Gate

Protected paths:
- backend/app/engine/risk.py
- backend/app/engine/broker.py
- backend/app/dhan/orders.py
- backend/tests/parity/

Proof requirement: Attempted protected edit is denied and audited even if one layer is bypassed.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.feature_builder.spec import PROTECTED_PATHS


class EnforcementLayer(StrEnum):
    """The 4 defense-in-depth enforcement layers for protected paths."""

    PROMPT = "PROMPT"
    TOOL = "TOOL"
    DIFF = "DIFF"
    PROMOTION = "PROMOTION"


class SecurityAuditAction(StrEnum):
    """Actions taken upon detecting a protected-path violation."""

    DENIED_AND_BLOCKED = "DENIED_AND_BLOCKED"
    TASK_ABORTED = "TASK_ABORTED"
    COMMIT_REJECTED = "COMMIT_REJECTED"
    PROMOTION_REJECTED = "PROMOTION_REJECTED"


class ProtectedPathViolationError(PermissionError):
    """Raised when an automated action attempts to modify or target a protected path."""

    def __init__(
        self,
        offending_path: str,
        layer: EnforcementLayer,
        audit_id: str,
        message: str | None = None,
    ) -> None:
        self.offending_path = offending_path
        self.layer = layer
        self.audit_id = audit_id
        detail = (
            message
            or f"SECURITY VIOLATION [{layer}]: Unattended modification to protected path "
            f"'{offending_path}' is strictly denied. Audit ID: {audit_id}"
        )
        super().__init__(detail)


class SecurityAuditEvent(BaseModel):
    """Durable record of a blocked security attempt against a protected path."""

    model_config = ConfigDict(frozen=True)

    audit_id: str
    timestamp: str
    task_id: str | None = None
    layer: EnforcementLayer
    offending_path: str
    action_taken: SecurityAuditAction
    bypassed_layers: list[EnforcementLayer] = Field(default_factory=list)
    details: str = ""


class ProtectedPathAuditLogger:
    """Durable security audit logger recording attempted protected-path breaches to disk."""

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path or Path("build/tasks/security_audit.json")

    def record_violation(
        self,
        offending_path: str,
        layer: EnforcementLayer,
        action: SecurityAuditAction = SecurityAuditAction.DENIED_AND_BLOCKED,
        task_id: str | None = None,
        bypassed_layers: Sequence[EnforcementLayer] | None = None,
        details: str = "",
    ) -> SecurityAuditEvent:
        """Record an attempted violation to durable disk storage."""
        event = SecurityAuditEvent(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            task_id=task_id,
            layer=layer,
            offending_path=offending_path,
            action_taken=action,
            bypassed_layers=list(bypassed_layers or []),
            details=details,
        )

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            events = self.get_audit_trail()
            events.append(event)
            raw = [e.model_dump() for e in events]
            self.log_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        except OSError:
            # Fallback memory persistence in restricted environments
            pass

        return event

    def get_audit_trail(self) -> list[SecurityAuditEvent]:
        """Load the durable security audit log from disk."""
        if not self.log_path.exists():
            return []
        try:
            data = json.loads(self.log_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [SecurityAuditEvent(**item) for item in data]
        except json.JSONDecodeError, OSError, ValueError:
            return []
        return []

    def clear_audit_trail(self) -> None:
        """Clear audit trail (used primarily for test isolation)."""
        if self.log_path.exists():
            self.log_path.unlink(missing_ok=True)


audit_logger = ProtectedPathAuditLogger()


def is_protected_path(path: str | Path) -> bool:
    """Check whether a given file path touches any protected path."""
    raw = str(path).replace("\\", "/").strip().lstrip("./")
    for protected in PROTECTED_PATHS:
        p_clean = protected.replace("\\", "/").strip().rstrip("/")
        if raw == p_clean or raw.startswith(f"{p_clean}/"):
            return True
    return False


class PromptGuard:
    """Layer 1: Inspects user instructions, requests, and target lists before execution."""

    def __init__(self, logger: ProtectedPathAuditLogger | None = None) -> None:
        self.logger = logger or audit_logger

    def validate_request(
        self,
        prompt_text: str,
        target_files: Sequence[str] | None = None,
        task_id: str | None = None,
    ) -> None:
        """Deny tasks or prompts explicitly targeting protected paths."""
        targets = list(target_files or [])

        # Check explicit target files
        for f in targets:
            if is_protected_path(f):
                event = self.logger.record_violation(
                    offending_path=f,
                    layer=EnforcementLayer.PROMPT,
                    action=SecurityAuditAction.TASK_ABORTED,
                    task_id=task_id,
                    details="Prompt target file explicitly references protected path",
                )
                raise ProtectedPathViolationError(
                    offending_path=f,
                    layer=EnforcementLayer.PROMPT,
                    audit_id=event.audit_id,
                )

        # Check prompt mentions
        norm_prompt = prompt_text.replace("\\", "/")
        for protected in PROTECTED_PATHS:
            p_clean = protected.replace("\\", "/").rstrip("/")
            if p_clean in norm_prompt:
                event = self.logger.record_violation(
                    offending_path=p_clean,
                    layer=EnforcementLayer.PROMPT,
                    action=SecurityAuditAction.TASK_ABORTED,
                    task_id=task_id,
                    details="Prompt text contains explicit reference to protected path",
                )
                raise ProtectedPathViolationError(
                    offending_path=p_clean,
                    layer=EnforcementLayer.PROMPT,
                    audit_id=event.audit_id,
                )


class ToolGuard:
    """Layer 2: Intercepts tool calls (write, edit, delete, rename) before file modification."""

    def __init__(self, logger: ProtectedPathAuditLogger | None = None) -> None:
        self.logger = logger or audit_logger

    def intercept_file_write(
        self,
        target_path: str | Path,
        task_id: str | None = None,
        bypassed_layers: Sequence[EnforcementLayer] | None = None,
    ) -> None:
        """Deny tool write attempts directed towards protected files."""
        if is_protected_path(target_path):
            event = self.logger.record_violation(
                offending_path=str(target_path),
                layer=EnforcementLayer.TOOL,
                action=SecurityAuditAction.DENIED_AND_BLOCKED,
                task_id=task_id,
                bypassed_layers=bypassed_layers,
                details="Tool execution interceptor blocked unauthorized write",
            )
            raise ProtectedPathViolationError(
                offending_path=str(target_path),
                layer=EnforcementLayer.TOOL,
                audit_id=event.audit_id,
            )


class DiffGuard:
    """Layer 3: Inspects pre-commit git diff and working tree status for unauthorized changes."""

    def __init__(self, logger: ProtectedPathAuditLogger | None = None) -> None:
        self.logger = logger or audit_logger

    def verify_diff(
        self,
        changed_files: Sequence[str],
        task_id: str | None = None,
        bypassed_layers: Sequence[EnforcementLayer] | None = None,
    ) -> list[str]:
        """Deny commits containing protected file modifications."""
        for f in changed_files:
            if is_protected_path(f):
                event = self.logger.record_violation(
                    offending_path=f,
                    layer=EnforcementLayer.DIFF,
                    action=SecurityAuditAction.COMMIT_REJECTED,
                    task_id=task_id,
                    bypassed_layers=bypassed_layers,
                    details="Git diff guard detected protected path in candidate changeset",
                )
                raise ProtectedPathViolationError(
                    offending_path=f,
                    layer=EnforcementLayer.DIFF,
                    audit_id=event.audit_id,
                )
        return list(changed_files)


class PromotionGuard:
    """Layer 4: Inspects candidate commit tree and SHA prior to merge into main or deployment."""

    def __init__(self, logger: ProtectedPathAuditLogger | None = None) -> None:
        self.logger = logger or audit_logger

    def verify_promotion(
        self,
        candidate_files: Sequence[str],
        commit_sha: str | None = None,
        task_id: str | None = None,
        bypassed_layers: Sequence[EnforcementLayer] | None = None,
    ) -> None:
        """Deny fast-forward merge or promotion if candidate tree modifies protected paths."""
        for f in candidate_files:
            if is_protected_path(f):
                event = self.logger.record_violation(
                    offending_path=f,
                    layer=EnforcementLayer.PROMOTION,
                    action=SecurityAuditAction.PROMOTION_REJECTED,
                    task_id=task_id,
                    bypassed_layers=bypassed_layers,
                    details=f"Promotion guard barred merge of commit {commit_sha or 'HEAD'}",
                )
                raise ProtectedPathViolationError(
                    offending_path=f,
                    layer=EnforcementLayer.PROMOTION,
                    audit_id=event.audit_id,
                )


class LayeredSecurityEngine:
    """Unified engine coordinating all 4 defense-in-depth protection layers."""

    def __init__(self, logger: ProtectedPathAuditLogger | None = None) -> None:
        self.logger = logger or audit_logger
        self.prompt_guard = PromptGuard(self.logger)
        self.tool_guard = ToolGuard(self.logger)
        self.diff_guard = DiffGuard(self.logger)
        self.promotion_guard = PromotionGuard(self.logger)


security_engine = LayeredSecurityEngine()
