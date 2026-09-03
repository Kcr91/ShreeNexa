"""Unit and acceptance tests for protected-path layered enforcement and security auditing (F11.5).

Proof requirement: Attempted protected edit is denied and audited even if one enforcement
layer is bypassed.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from app.feature_builder.security import (
    DiffGuard,
    EnforcementLayer,
    PromotionGuard,
    PromptGuard,
    ProtectedPathAuditLogger,
    ProtectedPathViolationError,
    SecurityAuditAction,
    ToolGuard,
    audit_logger,
    is_protected_path,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def local_tmp_path() -> Iterator[Path]:
    """Isolated local temporary path fixture within repo build root."""
    base = Path("build/test_tmp").resolve()
    base.mkdir(parents=True, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="security_test_", dir=base)
    p = Path(temp_dir).resolve()
    try:
        yield p
    finally:
        shutil.rmtree(p, ignore_errors=True)


def test_is_protected_path_detection() -> None:
    """Verify exact match and subpath detection for all four protected paths."""
    # 1. engine/risk.py
    assert is_protected_path("backend/app/engine/risk.py") is True
    assert is_protected_path("./backend/app/engine/risk.py") is True
    assert is_protected_path("backend\\app\\engine\\risk.py") is True

    # 2. engine/broker.py
    assert is_protected_path("backend/app/engine/broker.py") is True

    # 3. dhan/orders.py
    assert is_protected_path("backend/app/dhan/orders.py") is True

    # 4. backend/tests/parity/ directory and subfiles
    assert is_protected_path("backend/tests/parity/") is True
    assert is_protected_path("backend/tests/parity/test_indicators.py") is True
    assert is_protected_path("backend/tests/parity/subdir/nested.py") is True

    # Non-protected normal files
    assert is_protected_path("backend/app/strategy/moving_average.py") is False
    assert is_protected_path("backend/tests/unit/test_something.py") is False


def test_layer1_prompt_guard_blocks_and_audits(local_tmp_path: Path) -> None:
    """Proof: Layer 1 blocks task requesting edit to protected path and writes audit record."""
    test_logger = ProtectedPathAuditLogger(log_path=local_tmp_path / "audit.json")
    prompt_guard = PromptGuard(logger=test_logger)

    with pytest.raises(ProtectedPathViolationError) as exc_info:
        prompt_guard.validate_request(
            prompt_text="Please update backend/app/engine/risk.py to increase risk limits",
            task_id="task-001",
        )

    assert "backend/app/engine/risk.py" in str(exc_info.value)
    assert exc_info.value.layer == EnforcementLayer.PROMPT

    # Verify audit event
    trail = test_logger.get_audit_trail()
    assert len(trail) == 1
    event = trail[0]
    assert event.layer == EnforcementLayer.PROMPT
    assert event.offending_path == "backend/app/engine/risk.py"
    assert event.action_taken == SecurityAuditAction.TASK_ABORTED


def test_layer2_tool_guard_blocks_and_audits_when_layer1_bypassed(
    local_tmp_path: Path,
) -> None:
    """Proof: If Layer 1 is bypassed, Layer 2 (tool write) intercepts and records bypass."""
    test_logger = ProtectedPathAuditLogger(log_path=local_tmp_path / "audit.json")
    tool_guard = ToolGuard(logger=test_logger)

    # Simulate Layer 1 being bypassed (e.g. generic instruction: 'apply optimization')
    with pytest.raises(ProtectedPathViolationError) as exc_info:
        tool_guard.intercept_file_write(
            target_path="backend/app/engine/broker.py",
            task_id="task-002",
            bypassed_layers=[EnforcementLayer.PROMPT],
        )

    assert "backend/app/engine/broker.py" in str(exc_info.value)
    assert exc_info.value.layer == EnforcementLayer.TOOL

    # Verify audit event captures that Layer 1 was bypassed
    trail = test_logger.get_audit_trail()
    assert len(trail) == 1
    event = trail[0]
    assert event.layer == EnforcementLayer.TOOL
    assert event.offending_path == "backend/app/engine/broker.py"
    assert EnforcementLayer.PROMPT in event.bypassed_layers


def test_layer3_diff_guard_blocks_and_audits_when_layers1_and_2_bypassed(
    local_tmp_path: Path,
) -> None:
    """Proof: If Layers 1 and 2 are bypassed, Layer 3 (git diff) blocks commit and audits."""
    test_logger = ProtectedPathAuditLogger(log_path=local_tmp_path / "audit.json")
    diff_guard = DiffGuard(logger=test_logger)

    changeset = [
        "backend/app/strategy/momentum.py",
        "backend/app/dhan/orders.py",  # Protected!
    ]

    # Simulate Layers 1 and 2 being bypassed (e.g. unintercepted external script edit)
    with pytest.raises(ProtectedPathViolationError) as exc_info:
        diff_guard.verify_diff(
            changed_files=changeset,
            task_id="task-003",
            bypassed_layers=[EnforcementLayer.PROMPT, EnforcementLayer.TOOL],
        )

    assert "backend/app/dhan/orders.py" in str(exc_info.value)
    assert exc_info.value.layer == EnforcementLayer.DIFF

    # Verify audit event captures both prior bypassed layers
    trail = test_logger.get_audit_trail()
    assert len(trail) == 1
    event = trail[0]
    assert event.layer == EnforcementLayer.DIFF
    assert event.offending_path == "backend/app/dhan/orders.py"
    assert event.action_taken == SecurityAuditAction.COMMIT_REJECTED
    assert EnforcementLayer.PROMPT in event.bypassed_layers
    assert EnforcementLayer.TOOL in event.bypassed_layers


def test_layer4_promotion_guard_blocks_and_audits_when_layers1_to_3_bypassed(
    local_tmp_path: Path,
) -> None:
    """Proof: If Layers 1-3 are bypassed, Layer 4 (promotion/merge) bars merge into main."""
    test_logger = ProtectedPathAuditLogger(log_path=local_tmp_path / "audit.json")
    promotion_guard = PromotionGuard(logger=test_logger)

    candidate_files = [
        "backend/tests/parity/test_indicators.py",  # Protected!
    ]

    # Simulate Layers 1-3 being bypassed (e.g. forced local commit on feature branch)
    with pytest.raises(ProtectedPathViolationError) as exc_info:
        promotion_guard.verify_promotion(
            candidate_files=candidate_files,
            commit_sha="a1b2c3d",
            task_id="task-004",
            bypassed_layers=[
                EnforcementLayer.PROMPT,
                EnforcementLayer.TOOL,
                EnforcementLayer.DIFF,
            ],
        )

    assert "backend/tests/parity/test_indicators.py" in str(exc_info.value)
    assert exc_info.value.layer == EnforcementLayer.PROMOTION

    # Verify audit event captures all 3 prior bypassed layers
    trail = test_logger.get_audit_trail()
    assert len(trail) == 1
    event = trail[0]
    assert event.layer == EnforcementLayer.PROMOTION
    assert event.action_taken == SecurityAuditAction.PROMOTION_REJECTED
    assert len(event.bypassed_layers) == 3


def test_unprotected_paths_pass_all_defense_layers(local_tmp_path: Path) -> None:
    """Verify clean paths pass through all defense layers without triggering security errors."""
    test_logger = ProtectedPathAuditLogger(log_path=local_tmp_path / "audit.json")
    prompt_guard = PromptGuard(logger=test_logger)
    tool_guard = ToolGuard(logger=test_logger)
    diff_guard = DiffGuard(logger=test_logger)
    promotion_guard = PromotionGuard(logger=test_logger)

    safe_path = "backend/app/strategy/trend_filter.py"

    # Layer 1
    prompt_guard.validate_request("Create a trend filter", target_files=[safe_path])
    # Layer 2
    tool_guard.intercept_file_write(safe_path)
    # Layer 3
    verified = diff_guard.verify_diff([safe_path])
    assert verified == [safe_path]
    # Layer 4
    promotion_guard.verify_promotion([safe_path])

    # No violations recorded in audit trail
    assert len(test_logger.get_audit_trail()) == 0


def test_security_rest_api_lifecycle() -> None:
    """Proof: REST API endpoints for path verification, diff checks, and audit trail inspection."""
    audit_logger.clear_audit_trail()

    # 1. Verify path - protected
    resp1 = client.post(
        "/api/v1/feature-builder/security/verify-path",
        json={"path": "backend/app/engine/risk.py"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["is_protected"] is True

    # 2. Verify path - safe
    resp2 = client.post(
        "/api/v1/feature-builder/security/verify-path",
        json={"path": "backend/app/strategy/rsi.py"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["is_protected"] is False

    # 3. Check diff - clean
    resp3 = client.post(
        "/api/v1/feature-builder/security/check-diff",
        json={"changed_files": ["backend/app/strategy/rsi.py"]},
    )
    assert resp3.status_code == 200
    assert resp3.json()["status"] == "PASSED"

    # 4. Check diff - protected violation
    resp4 = client.post(
        "/api/v1/feature-builder/security/check-diff",
        json={"changed_files": ["backend/app/engine/risk.py"]},
    )
    assert resp4.status_code == 403
    err_detail = resp4.json()["detail"]
    assert err_detail["error"] == "PROTECTED_PATH_VIOLATION"
    assert err_detail["offending_path"] == "backend/app/engine/risk.py"

    # 5. Audit trail
    resp5 = client.get("/api/v1/feature-builder/security/audit")
    assert resp5.status_code == 200
    trail = resp5.json()
    assert len(trail) >= 1
    assert trail[-1]["offending_path"] == "backend/app/engine/risk.py"
