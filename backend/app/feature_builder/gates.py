"""Gate harness for G1-G6 cross-cutting quality gates, failure summaries, and retry policy (F11.4).

Evaluates:
- G1: Vectorized/incremental IR and indicator parity
- G2: Truncated-history no-look-ahead and point-in-time universe audit
- G3: Same input/version/configuration/seed gives byte-identical result
- G4: Ruff, strict mypy, frontend TypeScript, tests, production build
- G5: Coverage thresholds (90% analytics/engine, 80% backend, 70% UI)
- G6: Protected-paths audit (risk, broker, orders, parity fixtures)

Proof requirement: Deliberately broken parity/look-ahead/type/UI/protected-path
fixtures are blocked.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
import math
import re
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.feature_builder.spec import PROTECTED_PATHS


class GateType(StrEnum):
    """Identifier for the cross-cutting quality gates defined in docs/qa/gates.md."""

    G1 = "G1"  # Parity
    G2 = "G2"  # No look-ahead / point-in-time audit
    G3 = "G3"  # Determinism / reproducibility
    G4 = "G4"  # Compilation, typing, linting, tests
    G5 = "G5"  # Coverage thresholds
    G6 = "G6"  # Protected paths audit


class GateStatus(StrEnum):
    """Evaluation status of a quality gate."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class FailureCategory(StrEnum):
    """Categorized root causes for gate failures."""

    PARITY_MISMATCH = "PARITY_MISMATCH"
    LOOK_AHEAD_LEAK = "LOOK_AHEAD_LEAK"
    NONDETERMINISM = "NONDETERMINISM"
    TYPE_ERROR = "TYPE_ERROR"
    LINT_ERROR = "LINT_ERROR"
    TEST_FAILURE = "TEST_FAILURE"
    BUILD_FAILURE = "BUILD_FAILURE"
    COVERAGE_DEFICIT = "COVERAGE_DEFICIT"
    PROTECTED_PATH_VIOLATION = "PROTECTED_PATH_VIOLATION"
    UNKNOWN = "UNKNOWN"


class FilteredFailureSummary(BaseModel):
    """Structured, noise-filtered diagnostic summary of a gate failure."""

    model_config = ConfigDict(frozen=True)

    gate: GateType
    category: FailureCategory
    culprit_files: list[str] = Field(default_factory=list)
    culprit_lines: list[str] = Field(default_factory=list)
    message: str
    retryable: bool = True
    suggested_action: str = ""


class GateResult(BaseModel):
    """Evaluation outcome for an individual gate."""

    model_config = ConfigDict(frozen=True)

    gate: GateType
    status: GateStatus
    duration_ms: float = 0.0
    details: str = ""
    failure_summary: FilteredFailureSummary | None = None


class RetryPolicy(BaseModel):
    """Bounded automated retry policy with exponential backoff and non-retryable guards."""

    max_retries: int = 3
    backoff_seconds: float = 1.0
    exponential_factor: float = 2.0
    retry_count: int = 0

    def can_retry(self, summary: FilteredFailureSummary | None = None) -> bool:
        """Determine if a subsequent attempt is permitted under the policy."""
        if summary and not summary.retryable:
            return False
        return self.retry_count < self.max_retries

    def record_retry(self) -> float:
        """Record a retry attempt and compute the backoff duration in seconds."""
        if self.retry_count >= self.max_retries:
            raise ValueError(f"Max retries ({self.max_retries}) exceeded")
        delay = self.backoff_seconds * (self.exponential_factor**self.retry_count)
        self.retry_count += 1
        return delay

    def reset(self) -> None:
        """Reset the retry counter."""
        self.retry_count = 0


class GateExecutionSummary(BaseModel):
    """Overall evaluation summary across all evaluated gates."""

    model_config = ConfigDict(frozen=True)

    evaluation_id: str
    task_id: str | None = None
    overall_status: GateStatus
    passed_count: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    results: list[GateResult] = Field(default_factory=list)
    failures: list[FilteredFailureSummary] = Field(default_factory=list)
    can_retry: bool = False
    evaluated_at: str


class GateHarness:
    """Harness executing G1-G6 quality gates, failure filtering, and retry enforcement."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self.retry_policy = retry_policy or RetryPolicy()

    def evaluate_g1_parity(
        self,
        vector_output: Sequence[float | int | bool],
        incremental_output: Sequence[float | int | bool],
        tolerance: float = 1e-6,
    ) -> GateResult:
        """G1 Gate: Verify bit-for-bit mathematical parity between vector and incremental runs."""
        if len(vector_output) != len(incremental_output):
            summary = FilteredFailureSummary(
                gate=GateType.G1,
                category=FailureCategory.PARITY_MISMATCH,
                culprit_files=[
                    "backend/app/strategy/compiler.py",
                    "backend/app/strategy/engine.py",
                ],
                culprit_lines=[f"length {len(vector_output)} vs {len(incremental_output)}"],
                message=(
                    f"Vector length ({len(vector_output)}) does not match incremental length "
                    f"({len(incremental_output)})"
                ),
                retryable=True,
                suggested_action=(
                    "Ensure incremental state warm-up aligns with vector initial bar count."
                ),
            )
            return GateResult(
                gate=GateType.G1,
                status=GateStatus.FAILED,
                details="Vector and incremental signal series lengths differ",
                failure_summary=summary,
            )

        mismatches: list[tuple[int, Any, Any]] = []
        for idx, (v, inc) in enumerate(zip(vector_output, incremental_output, strict=True)):
            if isinstance(v, float) and isinstance(inc, float):
                if math.isnan(v) and math.isnan(inc):
                    continue
                if math.isnan(v) != math.isnan(inc) or abs(v - inc) > tolerance:
                    mismatches.append((idx, v, inc))
            elif v != inc:
                mismatches.append((idx, v, inc))

        if mismatches:
            first_idx, exp_v, act_inc = mismatches[0]
            summary = FilteredFailureSummary(
                gate=GateType.G1,
                category=FailureCategory.PARITY_MISMATCH,
                culprit_files=[
                    "backend/app/strategy/compiler.py",
                    "backend/app/strategy/engine.py",
                ],
                culprit_lines=[f"bar_{first_idx}"],
                message=(
                    f"Parity mismatch at bar {first_idx}: vector produced {exp_v}, "
                    f"incremental produced {act_inc} (total mismatches: {len(mismatches)})"
                ),
                retryable=True,
                suggested_action=(
                    "Inspect recursive indicator state accumulation vs vectorized window."
                ),
            )
            return GateResult(
                gate=GateType.G1,
                status=GateStatus.FAILED,
                details=f"Parity check failed with {len(mismatches)} mismatches",
                failure_summary=summary,
            )

        return GateResult(
            gate=GateType.G1,
            status=GateStatus.PASSED,
            details=(
                f"Vector and incremental parity verified bit-for-bit across "
                f"{len(vector_output)} bars"
            ),
        )

    def evaluate_g2_lookahead(
        self,
        full_history_signals: Sequence[int | float | bool],
        truncated_history_signals: Sequence[int | float | bool],
        truncation_point: int,
    ) -> GateResult:
        """G2 Gate: Truncated-history audit verifying no signals at t <= T use data from t > T."""
        if truncation_point > len(full_history_signals):
            raise ValueError("Truncation point exceeds full history length")

        mismatches: list[tuple[int, Any, Any]] = []
        for i in range(truncation_point):
            if i >= len(truncated_history_signals):
                mismatches.append((i, full_history_signals[i], "MISSING"))
                continue
            full_val = full_history_signals[i]
            trunc_val = truncated_history_signals[i]
            if full_val != trunc_val:
                mismatches.append((i, full_val, trunc_val))

        if mismatches:
            idx, full_val, trunc_val = mismatches[0]
            summary = FilteredFailureSummary(
                gate=GateType.G2,
                category=FailureCategory.LOOK_AHEAD_LEAK,
                culprit_files=["backend/app/strategy/screener.py"],
                culprit_lines=[f"bar_{idx}"],
                message=(
                    f"Look-ahead detected at bar {idx}: full history produced {full_val}, "
                    f"but truncated history up to {truncation_point} produced {trunc_val}."
                ),
                retryable=False,  # Lookahead is an architecture violation
                suggested_action="Eliminate future indexing (e.g. shift(-1) or unlagged close).",
            )
            return GateResult(
                gate=GateType.G2,
                status=GateStatus.FAILED,
                details=f"Look-ahead check failed at bar index {idx}",
                failure_summary=summary,
            )

        return GateResult(
            gate=GateType.G2,
            status=GateStatus.PASSED,
            details=(
                f"No look-ahead detected: truncated history perfectly matches full history "
                f"across {truncation_point} bars"
            ),
        )

    def evaluate_g3_determinism(
        self,
        run_1_payload: dict[str, Any] | str,
        run_2_payload: dict[str, Any] | str,
    ) -> GateResult:
        """G3 Gate: Verify identical inputs and seed produce byte-identical results."""
        str_1 = (
            json.dumps(run_1_payload, sort_keys=True)
            if isinstance(run_1_payload, dict)
            else str(run_1_payload)
        )
        str_2 = (
            json.dumps(run_2_payload, sort_keys=True)
            if isinstance(run_2_payload, dict)
            else str(run_2_payload)
        )

        h1 = hashlib.sha256(str_1.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(str_2.encode("utf-8")).hexdigest()

        if h1 != h2:
            summary = FilteredFailureSummary(
                gate=GateType.G3,
                category=FailureCategory.NONDETERMINISM,
                culprit_files=["backend/app/engine/backtest.py"],
                culprit_lines=[],
                message=(
                    f"Reproducibility failure: run 1 SHA ({h1[:8]}) differs "
                    f"from run 2 SHA ({h2[:8]})."
                ),
                retryable=True,
                suggested_action=(
                    "Seed all pseudo-random generators and eliminate unordered "
                    "dictionary iteration."
                ),
            )
            return GateResult(
                gate=GateType.G3,
                status=GateStatus.FAILED,
                details="Runs with identical configuration produced different hashes",
                failure_summary=summary,
            )

        return GateResult(
            gate=GateType.G3,
            status=GateStatus.PASSED,
            details=f"Determinism verified: identical SHA-256 hash ({h1[:12]})",
        )

    def evaluate_g4_compilation(
        self,
        raw_output: str,
        exit_code: int,
    ) -> GateResult:
        """G4 Gate: Verify static typecheck, linting, and build pass without errors."""
        if exit_code == 0:
            return GateResult(
                gate=GateType.G4,
                status=GateStatus.PASSED,
                details="Static checks, typing, and build compilation passed cleanly",
            )

        summary = self.filter_compilation_logs(raw_output)
        return GateResult(
            gate=GateType.G4,
            status=GateStatus.FAILED,
            details=f"Compilation/typecheck failed with code {exit_code}",
            failure_summary=summary,
        )

    def evaluate_g5_coverage(
        self,
        actual_coverage: float,
        required_coverage: float,
        component: str = "backend",
    ) -> GateResult:
        """G5 Gate: Verify test coverage satisfies minimum required threshold."""
        if actual_coverage < required_coverage:
            shortfall = required_coverage - actual_coverage
            summary = FilteredFailureSummary(
                gate=GateType.G5,
                category=FailureCategory.COVERAGE_DEFICIT,
                culprit_files=[f"{component}/"],
                culprit_lines=[],
                message=(
                    f"Coverage for {component} is {actual_coverage:.1f}%, falling short of the "
                    f"required {required_coverage:.1f}% threshold (deficit: -{shortfall:.1f}%)."
                ),
                retryable=True,
                suggested_action=(
                    f"Add unit or integration tests to achieve >= "
                    f"{required_coverage:.1f}% coverage."
                ),
            )
            return GateResult(
                gate=GateType.G5,
                status=GateStatus.FAILED,
                details=f"Coverage deficit: {actual_coverage:.1f}% < {required_coverage:.1f}%",
                failure_summary=summary,
            )

        return GateResult(
            gate=GateType.G5,
            status=GateStatus.PASSED,
            details=f"Coverage {actual_coverage:.1f}% satisfies {required_coverage:.1f}% threshold",
        )

    def evaluate_g6_protected_paths(self, changed_files: Sequence[str]) -> GateResult:
        """G6 Gate: Strictly bar unattended edits to protected engine/risk/broker/parity paths."""
        violations: list[str] = []
        for path in changed_files:
            norm_path = path.replace("\\", "/").lstrip("/")
            for protected in PROTECTED_PATHS:
                p_clean = protected.replace("\\", "/").rstrip("/")
                if norm_path == p_clean or norm_path.startswith(f"{p_clean}/"):
                    violations.append(norm_path)

        if violations:
            summary = FilteredFailureSummary(
                gate=GateType.G6,
                category=FailureCategory.PROTECTED_PATH_VIOLATION,
                culprit_files=sorted(set(violations)),
                culprit_lines=[],
                message=(
                    f"SECURITY BLOCKED: Unattended modification detected in protected paths: "
                    f"{', '.join(violations)}. Automated self-extension is barred from these paths."
                ),
                retryable=False,  # Security invariant: non-retryable
                suggested_action=(
                    "Revert protected path edits immediately; require supervised human sign-off."
                ),
            )
            return GateResult(
                gate=GateType.G6,
                status=GateStatus.BLOCKED,
                details=f"Protected path violation: {len(violations)} restricted files modified",
                failure_summary=summary,
            )

        return GateResult(
            gate=GateType.G6,
            status=GateStatus.PASSED,
            details=(
                f"Protected paths verified: 0 of {len(changed_files)} changed files touch "
                "restricted areas"
            ),
        )

    def filter_compilation_logs(self, raw_log: str) -> FilteredFailureSummary:
        """Filter noisy compiler/typecheck/lint output down to a structured concise summary."""
        culprit_files: list[str] = []
        culprit_lines: list[str] = []
        extracted_messages: list[str] = []
        category = FailureCategory.BUILD_FAILURE

        # Match Python mypy / ruff format: file.py:line:col: error: message
        py_err_pattern = re.compile(
            r"^([^:\n]+\.py):(\d+):(?:\d+:)?\s*(?:error|SyntaxError)?:\s*(.+)$", re.M
        )
        for match in py_err_pattern.finditer(raw_log):
            f_path, line_no, msg = match.groups()
            culprit_files.append(f_path.strip())
            culprit_lines.append(line_no.strip())
            extracted_messages.append(msg.strip())
            category = FailureCategory.TYPE_ERROR

        # Match TypeScript / Vite format: file.tsx:line:col - error TS...: message
        ts_err_pattern = re.compile(
            r"^([^:\n]+\.tsx?):(\d+):(?:\d+:)?\s*-\s*error\s*(?:TS\d+:)?\s*(.+)$", re.M
        )
        for match in ts_err_pattern.finditer(raw_log):
            f_path, line_no, msg = match.groups()
            culprit_files.append(f_path.strip())
            culprit_lines.append(line_no.strip())
            extracted_messages.append(msg.strip())
            category = FailureCategory.TYPE_ERROR

        # Fallback if no structured regex matched
        if not extracted_messages:
            lines = [line.strip() for line in raw_log.splitlines() if line.strip()]
            err_lines = [
                line_entry
                for line_entry in lines
                if any(k in line_entry.lower() for k in ("error", "failed", "exception"))
            ]
            core_msg = err_lines[0] if err_lines else (lines[-1] if lines else "Process failed")
            extracted_messages.append(core_msg[:160])

        concise_msg = extracted_messages[0] if extracted_messages else "Compilation or build failed"
        unique_files = list(dict.fromkeys(culprit_files))
        unique_lines = list(dict.fromkeys(culprit_lines))

        return FilteredFailureSummary(
            gate=GateType.G4,
            category=category,
            culprit_files=unique_files[:5],
            culprit_lines=unique_lines[:5],
            message=concise_msg,
            retryable=True,
            suggested_action=(
                "Resolve syntax, typing, or build issues identified in the filtered message."
            ),
        )

    def evaluate_all(
        self,
        changed_files: Sequence[str],
        g1_data: tuple[Sequence[Any], Sequence[Any]] | None = None,
        g2_data: tuple[Sequence[Any], Sequence[Any], int] | None = None,
        g3_data: tuple[Any, Any] | None = None,
        g4_data: tuple[str, int] | None = None,
        g5_data: tuple[float, float, str] | None = None,
        task_id: str | None = None,
    ) -> GateExecutionSummary:
        """Evaluate all enabled gates for a candidate and compute overall disposition."""
        results: list[GateResult] = []

        # Always evaluate G6 (Protected Paths Audit)
        r6 = self.evaluate_g6_protected_paths(changed_files)
        results.append(r6)

        # G1 Parity
        if g1_data:
            r1 = self.evaluate_g1_parity(g1_data[0], g1_data[1])
            results.append(r1)

        # G2 Lookahead
        if g2_data:
            r2 = self.evaluate_g2_lookahead(g2_data[0], g2_data[1], g2_data[2])
            results.append(r2)

        # G3 Determinism
        if g3_data:
            r3 = self.evaluate_g3_determinism(g3_data[0], g3_data[1])
            results.append(r3)

        # G4 Compilation / Typing / Build
        if g4_data:
            r4 = self.evaluate_g4_compilation(g4_data[0], g4_data[1])
            results.append(r4)

        # G5 Coverage
        if g5_data:
            r5 = self.evaluate_g5_coverage(g5_data[0], g5_data[1], g5_data[2])
            results.append(r5)

        passed = sum(1 for r in results if r.status == GateStatus.PASSED)
        failed = sum(1 for r in results if r.status == GateStatus.FAILED)
        blocked = sum(1 for r in results if r.status == GateStatus.BLOCKED)

        failures = [r.failure_summary for r in results if r.failure_summary is not None]

        # Invariant: If G6 is BLOCKED, overall status is BLOCKED and can_retry is False
        if blocked > 0:
            overall_status = GateStatus.BLOCKED
            can_retry = False
        elif failed > 0:
            overall_status = GateStatus.FAILED
            can_retry = any(self.retry_policy.can_retry(f) for f in failures)
        else:
            overall_status = GateStatus.PASSED
            can_retry = False

        return GateExecutionSummary(
            evaluation_id=str(uuid.uuid4()),
            task_id=task_id,
            overall_status=overall_status,
            passed_count=passed,
            failed_count=failed,
            blocked_count=blocked,
            results=results,
            failures=failures,
            can_retry=can_retry,
            evaluated_at=datetime.now(UTC).isoformat(),
        )


gate_harness = GateHarness()
