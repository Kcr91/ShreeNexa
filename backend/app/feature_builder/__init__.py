"""Feature-builder pipeline package (Epic 11)."""

from __future__ import annotations

from app.feature_builder.models import (
    FeatureRequest,
    FeatureSpec,
    FeatureSpecUpdate,
    RiskLevel,
    SpecApprovalDecision,
    SpecStatus,
)
from app.feature_builder.spec import (
    PROTECTED_PATHS,
    FeatureSpecEngine,
    evaluate_ambiguity,
    evaluate_request_risk,
    spec_engine,
)
from app.feature_builder.worktree import (
    PathEscapeViolationError,
    WorktreeAllocation,
    WorktreeCreateRequest,
    WorktreeManager,
    safe_write_worktree_file,
    validate_worktree_path,
    worktree_manager,
)

__all__ = [
    "PROTECTED_PATHS",
    "FeatureRequest",
    "FeatureSpec",
    "FeatureSpecEngine",
    "FeatureSpecUpdate",
    "PathEscapeViolationError",
    "RiskLevel",
    "SpecApprovalDecision",
    "SpecStatus",
    "WorktreeAllocation",
    "WorktreeCreateRequest",
    "WorktreeManager",
    "evaluate_ambiguity",
    "evaluate_request_risk",
    "safe_write_worktree_file",
    "spec_engine",
    "validate_worktree_path",
    "worktree_manager",
]
