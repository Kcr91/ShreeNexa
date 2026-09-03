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

__all__ = [
    "PROTECTED_PATHS",
    "FeatureRequest",
    "FeatureSpec",
    "FeatureSpecEngine",
    "FeatureSpecUpdate",
    "RiskLevel",
    "SpecApprovalDecision",
    "SpecStatus",
    "evaluate_ambiguity",
    "evaluate_request_risk",
    "spec_engine",
]
