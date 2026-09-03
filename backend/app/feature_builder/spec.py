"""Implementation specification generation and ambiguity/risk evaluation engine (F11.1).

Proof requirement: Ambiguous/high-risk requests require approval; generated spec
names scope, tests, risk, dependencies, and protected paths.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.feature_builder.models import (
    FeatureRequest,
    FeatureSpec,
    FeatureSpecUpdate,
    RiskLevel,
    SpecApprovalDecision,
    SpecStatus,
)

PROTECTED_PATHS: tuple[str, ...] = (
    "backend/app/engine/risk.py",
    "backend/app/engine/broker.py",
    "backend/app/dhan/orders.py",
    "backend/tests/parity/",
)

HIGH_RISK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(live[- ]orders?|real[- ]orders?)\b", re.IGNORECASE),
    re.compile(r"\b(bypass[- ]risk|skip[- ]risk)\b", re.IGNORECASE),
    re.compile(r"\b(private[- ]keys?|credentials?|secrets?|tokens?)\b", re.IGNORECASE),
    re.compile(r"\b(delete[- ]all|drop[- ]database|truncate)\b", re.IGNORECASE),
    re.compile(r"\b(live[- ]broker|execute[- ]live)\b", re.IGNORECASE),
)

AMBIGUITY_KEYWORDS: tuple[str, ...] = (
    "etc",
    "tbd",
    "maybe",
    "somehow",
    "look into it",
    "as discussed",
    "quick fix",
    "whatever",
)


def evaluate_request_risk(
    text: str,
    explicit_files: list[str],
) -> tuple[RiskLevel, list[str], list[str]]:
    """Determine risk level, reasons, and protected paths affected by the request."""
    risk = RiskLevel.LOW
    reasons: list[str] = []
    protected_paths_touched: list[str] = []

    # 1. Check protected paths
    all_text = f"{text} {' '.join(explicit_files)}".lower()
    for p_path in PROTECTED_PATHS:
        normalized = p_path.lower().strip("/")
        if normalized in all_text:
            protected_paths_touched.append(p_path)
            reasons.append(f"Direct edit to protected path: {p_path}")
            risk = RiskLevel.HIGH

    # 2. Check high-risk semantic patterns
    for pattern in HIGH_RISK_PATTERNS:
        match = pattern.search(text)
        if match:
            reasons.append(f"High-risk operational action detected: '{match.group(0)}'")
            risk = RiskLevel.HIGH

    # 3. Medium risk check if not already high
    if risk != RiskLevel.HIGH:
        if any(w in all_text for w in ("database", "migration", "paper", "order", "fill")):
            risk = RiskLevel.MEDIUM

    return risk, reasons, protected_paths_touched


def evaluate_ambiguity(title: str, description: str) -> tuple[bool, list[str]]:
    """Check if the feature request lacks concrete requirements or is underspecified."""
    reasons: list[str] = []
    combined = f"{title} {description}".strip()

    if len(combined) < 25:
        reasons.append("Description is excessively brief (<25 characters).")

    for kw in AMBIGUITY_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", combined, re.IGNORECASE):
            reasons.append(f"Ambiguous keyword detected: '{kw}'.")

    is_ambiguous = len(reasons) > 0
    return is_ambiguous, reasons


class FeatureSpecEngine:
    """Creates, validates, and manages implementation specifications linked to manifest."""

    def __init__(self, manifest_path: Path | None = None) -> None:
        self.manifest_path = manifest_path or Path("build/manifest.yaml")
        self._specs: dict[str, FeatureSpec] = {}

    def _read_manifest_dependencies(self) -> set[str]:
        if not self.manifest_path.exists():
            return set()
        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            features = data.get("features", [])
            return {f["id"] for f in features if isinstance(f, dict) and "id" in f}
        except Exception:
            return set()

    def build_spec(self, request: FeatureRequest) -> FeatureSpec:
        """Analyze request, identify risk/protected paths, and build structured FeatureSpec."""
        full_text = f"{request.title}\n{request.description}"
        risk, risk_reasons, protected_paths = evaluate_request_risk(
            full_text, request.target_dependencies
        )
        is_ambiguous, ambiguity_reasons = evaluate_ambiguity(request.title, request.description)

        requires_approval = (risk == RiskLevel.HIGH) or is_ambiguous
        approval_reasons: list[str] = []
        if risk == RiskLevel.HIGH:
            approval_reasons.extend(risk_reasons)
        if is_ambiguous:
            approval_reasons.extend(ambiguity_reasons)

        feat_id = request.target_manifest_id or f"F11.{len(self._specs) + 1}"
        spec_id = f"spec-{uuid.uuid4().hex[:10]}"
        now = datetime.now()

        # Scope bullet generation
        scope = [
            f"Deliver {request.title.strip()}",
            "Implement typed domain models and validation rules",
            "Expose REST API endpoints and integrate with application router",
        ]
        out_of_scope = [
            "Live broker calls or real monetary order routing",
            "Modification of control-plane or audited safety tests",
        ]

        test_plan = [
            f"Unit test suite covering {request.title.strip()} functionality",
            "Quality gates: ruff, mypy --strict, and pytest regression",
            "Boundary validation ensuring zero unintended side-effects",
        ]

        criteria = [
            "All new files adhere to strict static type checking",
            "All quality gates pass cleanly",
        ]
        if protected_paths:
            criteria.append(
                f"Requires explicit approval due to protected paths: {', '.join(protected_paths)}"
            )

        manifest_entry = {
            "id": feat_id,
            "name": request.title.strip(),
            "depends_on": request.target_dependencies,
            "proof": (
                "Independent review and explicit sign-off required"
                if requires_approval
                else "Unit and integration regression test suite"
            ),
            "model": "SOL-XH" if risk == RiskLevel.HIGH else "SOL-H",
        }

        spec = FeatureSpec(
            spec_id=spec_id,
            feature_id=feat_id,
            title=request.title.strip(),
            scope=scope,
            out_of_scope=out_of_scope,
            dependencies=request.target_dependencies,
            risk_level=risk,
            requires_approval=requires_approval,
            approval_reason="; ".join(approval_reasons) if approval_reasons else None,
            is_ambiguous=is_ambiguous,
            ambiguity_reasons=ambiguity_reasons,
            affected_files=[],
            protected_paths_affected=protected_paths,
            test_plan=test_plan,
            acceptance_criteria=criteria,
            manifest_entry=manifest_entry,
            status=SpecStatus.PENDING_APPROVAL if requires_approval else SpecStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )

        self._specs[spec_id] = spec
        return spec

    def get_spec(self, spec_id: str) -> FeatureSpec | None:
        """Retrieve spec by id."""
        return self._specs.get(spec_id)

    def list_specs(self, status: SpecStatus | None = None) -> list[FeatureSpec]:
        """List specifications with optional status filter."""
        all_specs = list(self._specs.values())
        if status:
            return [s for s in all_specs if s.status == status]
        return all_specs

    def update_spec(self, spec_id: str, updates: FeatureSpecUpdate) -> FeatureSpec:
        """Edit scope, tests, or criteria in an existing spec."""
        spec = self._specs.get(spec_id)
        if not spec:
            raise KeyError(f"Spec {spec_id} not found")

        update_dict: dict[str, Any] = {"updated_at": datetime.now()}
        if updates.title is not None:
            update_dict["title"] = updates.title
        if updates.scope is not None:
            update_dict["scope"] = updates.scope
        if updates.out_of_scope is not None:
            update_dict["out_of_scope"] = updates.out_of_scope
        if updates.test_plan is not None:
            update_dict["test_plan"] = updates.test_plan
        if updates.acceptance_criteria is not None:
            update_dict["acceptance_criteria"] = updates.acceptance_criteria
        if updates.affected_files is not None:
            update_dict["affected_files"] = updates.affected_files

        updated = spec.model_copy(update=update_dict)
        self._specs[spec_id] = updated
        return updated

    def approve_spec(self, spec_id: str, decision: SpecApprovalDecision) -> FeatureSpec:
        """Record explicit user authorization for a high-risk or ambiguous specification."""
        spec = self._specs.get(spec_id)
        if not spec:
            raise KeyError(f"Spec {spec_id} not found")

        approved = spec.model_copy(
            update={
                "status": SpecStatus.APPROVED,
                "approved_by": decision.approver,
                "approved_at": datetime.now(),
                "updated_at": datetime.now(),
            }
        )
        self._specs[spec_id] = approved
        return approved

    def reject_spec(self, spec_id: str, decision: SpecApprovalDecision) -> FeatureSpec:
        """Record explicit rejection of a specification."""
        spec = self._specs.get(spec_id)
        if not spec:
            raise KeyError(f"Spec {spec_id} not found")

        rejected = spec.model_copy(
            update={
                "status": SpecStatus.REJECTED,
                "approved_by": decision.approver,
                "updated_at": datetime.now(),
            }
        )
        self._specs[spec_id] = rejected
        return rejected


# Global singleton instance for runtime and API usage
spec_engine = FeatureSpecEngine()
