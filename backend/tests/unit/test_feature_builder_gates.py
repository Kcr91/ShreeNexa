"""Unit and acceptance tests for gate harness, filtered summaries, and retry policy (F11.4).

Proof requirement: Deliberately broken parity/look-ahead/type/UI/protected-path
fixtures are blocked.
"""

from __future__ import annotations

import pytest
from app.feature_builder.gates import (
    FailureCategory,
    FilteredFailureSummary,
    GateHarness,
    GateStatus,
    GateType,
    RetryPolicy,
    gate_harness,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_deliberately_broken_parity_fixture_is_blocked() -> None:
    """Proof: Deliberately broken parity between vector and incremental signals is blocked by G1."""
    harness = GateHarness()

    # Identical except at bar index 3
    vector_output = [0.0, 1.0, 2.0, 5.0, 4.0]
    incremental_output = [0.0, 1.0, 2.0, 99.0, 4.0]

    result = harness.evaluate_g1_parity(vector_output, incremental_output)
    assert result.status == GateStatus.FAILED
    assert result.gate == GateType.G1
    assert result.failure_summary is not None
    assert result.failure_summary.category == FailureCategory.PARITY_MISMATCH
    assert "bar_3" in result.failure_summary.culprit_lines
    assert "vector produced 5.0, incremental produced 99.0" in result.failure_summary.message


def test_deliberately_broken_parity_length_mismatch_is_blocked() -> None:
    """Proof: Series length discrepancy between vector and incremental signals is blocked by G1."""
    harness = GateHarness()

    vector_output = [1.0, 2.0, 3.0]
    incremental_output = [1.0, 2.0]

    result = harness.evaluate_g1_parity(vector_output, incremental_output)
    assert result.status == GateStatus.FAILED
    assert result.failure_summary is not None
    assert result.failure_summary.category == FailureCategory.PARITY_MISMATCH
    assert (
        "Vector length (3) does not match incremental length (2)" in result.failure_summary.message
    )


def test_deliberately_broken_lookahead_fixture_is_blocked() -> None:
    """Proof: Signal look-ahead leak across truncated history is blocked by G2."""
    harness = GateHarness()

    # In full history, bar 2 had signal 1 (because future bars altered it)
    # In truncated history up to bar 4, bar 2 had signal 0
    full_history = [0, 0, 1, 1, 0, 1]
    truncated_history = [0, 0, 0, 1]

    result = harness.evaluate_g2_lookahead(full_history, truncated_history, truncation_point=4)
    assert result.status == GateStatus.FAILED
    assert result.gate == GateType.G2
    assert result.failure_summary is not None
    assert result.failure_summary.category == FailureCategory.LOOK_AHEAD_LEAK
    assert "bar_2" in result.failure_summary.culprit_lines
    # Look-ahead is an architectural violation: non-retryable
    assert result.failure_summary.retryable is False


def test_deliberately_broken_determinism_fixture_is_blocked() -> None:
    """Proof: Nondeterministic execution output across repeat runs is blocked by G3."""
    harness = GateHarness()

    run1 = {"trades": [{"id": 1, "pnl": 100.5}], "seed": 42}
    run2 = {"trades": [{"id": 1, "pnl": 100.6}], "seed": 42}

    result = harness.evaluate_g3_determinism(run1, run2)
    assert result.status == GateStatus.FAILED
    assert result.gate == GateType.G3
    assert result.failure_summary is not None
    assert result.failure_summary.category == FailureCategory.NONDETERMINISM


def test_deliberately_broken_type_and_compilation_is_blocked() -> None:
    """Proof: Failed typechecking or syntax errors are blocked by G4 with filtered summaries."""
    harness = GateHarness()

    raw_mypy_error = (
        "backend/app/strategy/broken.py:42: error: Incompatible types in assignment "
        "(expression has type 'str', variable has type 'int')\n"
        "Found 1 error in 1 file (checked 278 source files)\n"
    )

    result = harness.evaluate_g4_compilation(raw_mypy_error, exit_code=1)
    assert result.status == GateStatus.FAILED
    assert result.gate == GateType.G4
    assert result.failure_summary is not None
    assert result.failure_summary.category == FailureCategory.TYPE_ERROR
    assert "backend/app/strategy/broken.py" in result.failure_summary.culprit_files
    assert "42" in result.failure_summary.culprit_lines
    assert "Incompatible types in assignment" in result.failure_summary.message


def test_deliberately_broken_coverage_fixture_is_blocked() -> None:
    """Proof: Insufficient test coverage is blocked by G5 with deficit breakdown."""
    harness = GateHarness()

    result = harness.evaluate_g5_coverage(
        actual_coverage=75.4, required_coverage=90.0, component="engine"
    )
    assert result.status == GateStatus.FAILED
    assert result.gate == GateType.G5
    assert result.failure_summary is not None
    assert result.failure_summary.category == FailureCategory.COVERAGE_DEFICIT
    assert "-14.6%" in result.failure_summary.message


def test_deliberately_broken_protected_path_fixture_is_blocked() -> None:
    """Proof: Unattended edit touching protected paths is strictly BLOCKED by G6."""
    harness = GateHarness()

    violating_files = [
        "backend/app/strategy/new_indicator.py",
        "backend/app/engine/risk.py",  # Protected!
    ]

    result = harness.evaluate_g6_protected_paths(violating_files)
    assert result.status == GateStatus.BLOCKED
    assert result.gate == GateType.G6
    assert result.failure_summary is not None
    assert result.failure_summary.category == FailureCategory.PROTECTED_PATH_VIOLATION
    assert "backend/app/engine/risk.py" in result.failure_summary.culprit_files
    # Security invariant: strictly non-retryable
    assert result.failure_summary.retryable is False


def test_evaluate_all_aggregates_and_enforces_blocked_invariant() -> None:
    """Proof: Any protected-path violation sets overall status to BLOCKED and denies retry."""
    harness = GateHarness()

    summary = harness.evaluate_all(
        changed_files=["backend/app/engine/broker.py"],
        g1_data=([1.0, 2.0], [1.0, 2.0]),  # Parity passed
    )

    assert summary.overall_status == GateStatus.BLOCKED
    assert summary.blocked_count == 1
    assert summary.can_retry is False


def test_bounded_retry_policy() -> None:
    """Proof: Automated retry policy enforces maximum bounded attempts and backoff schedule."""
    policy = RetryPolicy(max_retries=3, backoff_seconds=1.0, exponential_factor=2.0)

    # Retryable failure
    retryable_sum = FilteredFailureSummary(
        gate=GateType.G4,
        category=FailureCategory.TYPE_ERROR,
        message="Type mismatch",
        retryable=True,
    )

    # Non-retryable failure (security / protected path)
    non_retryable_sum = FilteredFailureSummary(
        gate=GateType.G6,
        category=FailureCategory.PROTECTED_PATH_VIOLATION,
        message="Protected path modified",
        retryable=False,
    )

    # Attempt 0
    assert policy.can_retry(retryable_sum) is True
    assert policy.can_retry(non_retryable_sum) is False
    delay_1 = policy.record_retry()
    assert delay_1 == 1.0
    assert policy.retry_count == 1

    # Attempt 1
    assert policy.can_retry(retryable_sum) is True
    delay_2 = policy.record_retry()
    assert delay_2 == 2.0
    assert policy.retry_count == 2

    # Attempt 2
    assert policy.can_retry(retryable_sum) is True
    delay_3 = policy.record_retry()
    assert delay_3 == 4.0
    assert policy.retry_count == 3

    # Attempt 3: Max retries exceeded
    assert policy.can_retry(retryable_sum) is False
    with pytest.raises(ValueError, match="Max retries"):
        policy.record_retry()


def test_gates_rest_api_lifecycle() -> None:
    """Proof: Quality gates REST API supports evaluate, retry, and policy inspection."""
    # Reset global harness policy for clean test run
    gate_harness.retry_policy.reset()

    # 1. Evaluate clean run
    resp_clean = client.post(
        "/api/v1/feature-builder/gates/evaluate",
        json={
            "changed_files": ["backend/app/strategy/moving_avg.py"],
            "g1_vector": [1.0, 2.0, 3.0],
            "g1_incremental": [1.0, 2.0, 3.0],
            "g5_actual_coverage": 92.5,
            "g5_required_coverage": 90.0,
        },
    )
    assert resp_clean.status_code == 200
    data_clean = resp_clean.json()
    assert data_clean["overall_status"] == "PASSED"
    assert data_clean["failed_count"] == 0
    assert data_clean["blocked_count"] == 0

    # 2. Evaluate protected path violation
    resp_violation = client.post(
        "/api/v1/feature-builder/gates/evaluate",
        json={
            "changed_files": ["backend/app/dhan/orders.py"],
        },
    )
    assert resp_violation.status_code == 200
    data_violation = resp_violation.json()
    assert data_violation["overall_status"] == "BLOCKED"
    assert data_violation["blocked_count"] == 1
    assert data_violation["can_retry"] is False

    # 3. Policy inspection
    resp_pol = client.get("/api/v1/feature-builder/gates/policy")
    assert resp_pol.status_code == 200
    assert resp_pol.json()["max_retries"] == 3

    # 4. Retry request
    resp_retry = client.post("/api/v1/feature-builder/gates/retry")
    assert resp_retry.status_code == 200
    retry_data = resp_retry.json()
    assert retry_data["retry_allowed"] is True
    assert retry_data["retry_count"] == 1
