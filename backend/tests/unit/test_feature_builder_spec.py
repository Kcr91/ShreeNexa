"""Unit tests for feature specification generator, risk/ambiguity gating, and lifecycle (F11.1).

Proof requirement: Ambiguous/high-risk requests require approval; generated spec
names scope, tests, risk, dependencies, and protected paths.
"""

from __future__ import annotations

from app.feature_builder.models import (
    FeatureRequest,
    FeatureSpecUpdate,
    RiskLevel,
    SpecApprovalDecision,
    SpecStatus,
)
from app.feature_builder.spec import FeatureSpecEngine
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_low_risk_feature_spec_generation() -> None:
    """Proof: Low risk feature generates complete spec with scope, tests, and no approval needed."""
    engine = FeatureSpecEngine()
    req = FeatureRequest(
        request_id="req-101",
        title="Portfolio Analytics Heatmap Widget",
        description="Display interactive sectoral returns heatmap in the terminal UI.",
        target_manifest_id="F12.1",
        target_dependencies=["F10.2", "F7.4"],
    )

    spec = engine.build_spec(req)

    # Invariant: Names scope, tests, risk, dependencies, and protected paths
    assert spec.title == "Portfolio Analytics Heatmap Widget"
    assert spec.risk_level == RiskLevel.LOW
    assert spec.is_ambiguous is False
    assert spec.requires_approval is False
    assert spec.status == SpecStatus.DRAFT
    assert len(spec.scope) > 0
    assert len(spec.test_plan) > 0
    assert len(spec.acceptance_criteria) > 0
    assert spec.dependencies == ["F10.2", "F7.4"]
    assert spec.protected_paths_affected == []
    assert spec.manifest_entry["id"] == "F12.1"


def test_high_risk_protected_path_attempt_requires_approval() -> None:
    """Proof: Attempt to touch protected paths flags HIGH risk and blocks without approval."""
    engine = FeatureSpecEngine()
    req = FeatureRequest(
        request_id="req-102",
        title="Tweak Risk Limits",
        description="Modify backend/app/engine/risk.py to relax position limits.",
        target_manifest_id="F12.2",
    )

    spec = engine.build_spec(req)

    # Proof requirement: High-risk requests require approval; spec names protected paths
    assert spec.risk_level == RiskLevel.HIGH
    assert spec.requires_approval is True
    assert spec.status == SpecStatus.PENDING_APPROVAL
    assert "backend/app/engine/risk.py" in spec.protected_paths_affected
    assert spec.approval_reason is not None
    assert "backend/app/engine/risk.py" in spec.approval_reason


def test_high_risk_operational_action_requires_approval() -> None:
    """Proof: Live orders or risk bypass actions flag HIGH risk and require approval."""
    engine = FeatureSpecEngine()
    req = FeatureRequest(
        request_id="req-103",
        title="Direct Live Execution",
        description="Bypass risk checks and send live orders directly to the live broker.",
    )

    spec = engine.build_spec(req)

    assert spec.risk_level == RiskLevel.HIGH
    assert spec.requires_approval is True
    assert spec.status == SpecStatus.PENDING_APPROVAL
    assert spec.approval_reason is not None
    assert "High-risk operational action detected" in spec.approval_reason


def test_ambiguous_request_requires_approval() -> None:
    """Proof: Ambiguous or underspecified requests require explicit approval."""
    engine = FeatureSpecEngine()
    req = FeatureRequest(
        request_id="req-104",
        title="Fix things",
        description="Look into it maybe etc",
    )

    spec = engine.build_spec(req)

    # Proof requirement: Ambiguous requests require approval
    assert spec.is_ambiguous is True
    assert spec.requires_approval is True
    assert spec.status == SpecStatus.PENDING_APPROVAL
    assert len(spec.ambiguity_reasons) > 0


def test_spec_editing_and_approval_lifecycle() -> None:
    """Proof: Specification can be edited and approved or rejected with audit trail."""
    engine = FeatureSpecEngine()
    req = FeatureRequest(
        request_id="req-105",
        title="Custom Execution Hook",
        description="Add a pre-execution hook in backend/app/engine/broker.py for telemetry.",
    )

    spec = engine.build_spec(req)
    assert spec.status == SpecStatus.PENDING_APPROVAL

    # 1. Edit specification
    updates = FeatureSpecUpdate(
        scope=["Deliver telemetry pre-execution logging hook", "Add safety bounds"],
        test_plan=["Unit test verify hook runs without modifying broker logic"],
    )
    updated = engine.update_spec(spec.spec_id, updates)
    assert len(updated.scope) == 2
    assert "Deliver telemetry pre-execution logging hook" in updated.scope

    # 2. Approve specification
    decision = SpecApprovalDecision(
        approver="compliance_lead",
        comments="Approved strictly for read-only telemetry logging.",
    )
    approved = engine.approve_spec(spec.spec_id, decision)
    assert approved.status == SpecStatus.APPROVED
    assert approved.approved_by == "compliance_lead"
    assert approved.approved_at is not None

    # 3. Reject specification test
    spec2 = engine.build_spec(
        FeatureRequest(
            request_id="req-106",
            title="Dangerous drop table action",
            description="Drop database tables on reset.",
        )
    )
    rejected = engine.reject_spec(
        spec2.spec_id,
        SpecApprovalDecision(approver="safety_officer", comments="Destructive command denied."),
    )
    assert rejected.status == SpecStatus.REJECTED


def test_feature_builder_rest_api_endpoints() -> None:
    """Proof: REST API endpoints for creating, retrieving, editing, and approving specs."""
    # 1. Create spec
    create_payload = {
        "request_id": "req-api-1",
        "title": "Strategy Marketplace Filter",
        "description": "Add filter for options strategies in the terminal marketplace UI.",
        "target_manifest_id": "F12.3",
        "target_dependencies": ["F8.1"],
    }
    resp = client.post("/api/v1/feature-builder/specs", json=create_payload)
    assert resp.status_code == 200
    spec_data = resp.json()
    spec_id = spec_data["spec_id"]
    assert spec_data["title"] == "Strategy Marketplace Filter"

    # 2. Get spec
    get_resp = client.get(f"/api/v1/feature-builder/specs/{spec_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["spec_id"] == spec_id

    # 3. Update spec
    update_resp = client.put(
        f"/api/v1/feature-builder/specs/{spec_id}",
        json={"scope": ["New filtered UI view", "Added unit tests"]},
    )
    assert update_resp.status_code == 200
    assert len(update_resp.json()["scope"]) == 2

    # 4. List specs
    list_resp = client.get("/api/v1/feature-builder/specs")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 5. Approve spec
    approve_resp = client.post(
        f"/api/v1/feature-builder/specs/{spec_id}/approve",
        json={"approver": "architect", "comments": "Approved for sprint."},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"
