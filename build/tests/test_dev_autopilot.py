"""Safety proofs for the bounded local development autopilot."""

from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import autopilot.controller as controller_module
from autopilot.controller import (
    AutopilotError,
    CommandRunner,
    GateEvidence,
    InstanceLock,
    PilotController,
    Policy,
    RuntimeState,
    RuntimeStore,
    changed_paths,
    feature_prompt,
    git_sha,
    parse_junit_summary,
    parse_pytest_summary,
    parse_test_summary,
    promote_fast_forward,
    reconcile_merge,
    redact,
    run_git,
    sanitized_child_environment,
    validate_candidate_paths,
    validate_feature_evidence,
    validate_fixture_metadata,
    validate_gate_evidence,
    validate_review,
)
from update_state import update_state

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "build/autopilot/policy.yaml"


class FakeCodexAdapter:
    """Deterministic fake; it never authenticates, uses a network, or executes output."""

    def implement(self, worktree: Path, *_: object) -> str:
        (worktree / "feature.txt").write_text("candidate from fake Codex\n", encoding="utf-8")
        return "fake implementation complete"

    def review(self, base: str, candidate: str) -> dict[str, object]:
        return safe_review(base, candidate)


@pytest.fixture()
def tmp_path() -> Path:
    """Use the repository-local ignored temp root required by this sandbox."""
    directory = Path(__file__).parent / "tmp" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def init_repo(path: Path) -> tuple[str, str]:
    path.mkdir()
    run_git(path, "init", "-b", "main")
    run_git(path, "config", "user.name", "Autopilot Test")
    run_git(path, "config", "user.email", "autopilot@example.invalid")
    (path / "README.md").write_text("base\n", encoding="utf-8")
    run_git(path, "add", "README.md")
    run_git(path, "commit", "-m", "base")
    base = git_sha(path, "HEAD")
    run_git(path, "switch", "-c", "feature/F0.4-test")
    (path / "feature.txt").write_text("candidate\n", encoding="utf-8")
    run_git(path, "add", "feature.txt")
    run_git(path, "commit", "-m", "candidate")
    return base, git_sha(path, "HEAD")


def init_merged_feature_repo(
    path: Path,
    *,
    status: str,
    evidence_document: dict[str, object] | None = None,
) -> tuple[PilotController, RuntimeState, str]:
    path.mkdir()
    (path / "build").mkdir()
    shutil.copy2(REPO_ROOT / "build/manifest.yaml", path / "build/manifest.yaml")
    update_state(path / "build/state.json", feature="F0.4", status="pending")
    run_git(path, "init", "-b", "main")
    run_git(path, "config", "user.name", "Autopilot Test")
    run_git(path, "config", "user.email", "autopilot@example.invalid")
    run_git(path, "add", ".")
    run_git(path, "commit", "-m", "base")
    run_git(path, "switch", "-c", "feature/F0.4-central-settings")
    product = path / "backend/app/config.py"
    product.parent.mkdir(parents=True)
    product.write_text("RECOVERY_TEST = True\n", encoding="utf-8")
    run_git(path, "add", ".")
    run_git(path, "commit", "-m", "candidate")
    candidate = git_sha(path, "HEAD")
    run_git(path, "switch", "main")
    run_git(path, "merge", "--ff-only", candidate)
    evidence_paths: list[str] = []
    tests: dict[str, object] = {}
    verified_at: str | None = None
    if evidence_document is not None:
        evidence = path / ".runtime/recovery/F0.4.json"
        evidence.parent.mkdir(parents=True)
        evidence.write_text(json.dumps(evidence_document), encoding="utf-8")
        evidence_paths = [".runtime/recovery/F0.4.json"]
        tests = {"pytest": {"passed": 1, "failed": 0, "skipped": 0}}
        verified_at = datetime.now(UTC).isoformat()
    update_state(
        path / "build/state.json",
        feature="F0.4",
        status=status,
        branch="feature/F0.4-central-settings",
        commit=candidate,
        tests=tests,
        blockers=["evidence pending"] if status == "blocked" else [],
        evidence=evidence_paths,
        verified_at=verified_at,
    )
    run_git(path, "add", "build/state.json")
    run_git(path, "commit", "-m", "tracked state")
    controller = PilotController(path, Policy.load(POLICY_PATH), codex_executable="fake")
    return controller, RuntimeState(), candidate


def safe_review(base: str, candidate: str) -> dict[str, object]:
    return {
        "base_sha": base,
        "candidate_sha": candidate,
        "verdict": "safe_to_merge",
        "findings": [],
        "evidence_checked": ["diff and synthetic gate evidence"],
        "independent": True,
        "reviewer_session_id": "fresh-review-session",
        "reviewed_at": datetime.now(UTC).isoformat(),
    }


def passing_gate(
    candidate: str,
    gate_id: str = "pytest",
    *,
    base_sha: str = "",
    test_required: bool = False,
) -> GateEvidence:
    return GateEvidence(
        gate_id=gate_id,
        candidate_sha=candidate,
        argv=("fake-gate",),
        exit_code=0,
        duration_seconds=0.01,
        passed=1,
        base_sha=base_sha,
        finished_at=datetime.now(UTC).isoformat(),
        test_required=test_required,
    )


def test_policy_is_exactly_bounded_to_authorized_features() -> None:
    policy = Policy.load(POLICY_PATH)
    policy.validate_manifest(REPO_ROOT / "build/manifest.yaml")
    assert policy.raw["allowlist"] == ["F0.4", "F0.5", "F0.6", "F0.7", "F0.8", "F0.9"]
    with pytest.raises(AutopilotError, match="not allowlisted"):
        policy.feature("F1.1")


def test_passing_candidate_merges_and_already_merged_resume_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "Autopilot Test")
    run_git(repo, "config", "user.email", "autopilot@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    run_git(repo, "add", "README.md")
    run_git(repo, "commit", "-m", "base")
    base = git_sha(repo, "HEAD")
    run_git(repo, "switch", "-c", "feature/F0.4-test")
    fake_codex = FakeCodexAdapter()
    fake_codex.implement(repo)
    run_git(repo, "add", "feature.txt")
    run_git(repo, "commit", "-m", "candidate")
    candidate = git_sha(repo, "HEAD")
    run_git(repo, "switch", "main")
    evidence = [passing_gate(candidate, base_sha=base)]
    review = fake_codex.review(base, candidate)

    merged = promote_fast_forward(
        repo,
        base_sha=base,
        candidate_sha=candidate,
        branch="feature/F0.4-test",
        evidence=evidence,
        review=review,
        required_gate_ids=["pytest"],
    )

    assert merged == candidate
    assert git_sha(repo, "main") == candidate
    assert (
        promote_fast_forward(
            repo,
            base_sha=base,
            candidate_sha=candidate,
            branch="feature/F0.4-test",
            evidence=evidence,
            review=review,
            required_gate_ids=["pytest"],
        )
        == candidate
    )
    assert run_git(repo, "rev-list", "--count", "main") == "2"


@pytest.mark.parametrize(
    ("exit_code", "failed", "skipped", "message"),
    [(1, 0, 0, "failed"), (0, 1, 0, "failed"), (0, 0, 1, "skipped")],
)
def test_failed_gate_or_required_skip_blocks(
    exit_code: int, failed: int, skipped: int, message: str
) -> None:
    sha = "a" * 40
    evidence = [
        GateEvidence(
            gate_id="pytest",
            candidate_sha=sha,
            argv=("pytest",),
            exit_code=exit_code,
            duration_seconds=1,
            passed=1,
            failed=failed,
            skipped=skipped,
            test_required=True,
        )
    ]
    with pytest.raises(AutopilotError, match=message):
        validate_gate_evidence(evidence, sha, ["pytest"])


def test_missing_gate_evidence_blocks() -> None:
    with pytest.raises(AutopilotError, match="required gate set"):
        validate_gate_evidence([passing_gate("a" * 40)], "a" * 40, ["pytest", "ruff"])


def test_command_timeout_blocks_and_terminates_child(tmp_path: Path) -> None:
    runner = CommandRunner(lambda: False)
    with pytest.raises(AutopilotError, match="timed out"):
        runner.run(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            cwd=tmp_path,
            env=dict(os.environ),
            timeout_seconds=1,
        )


def test_safe_cancellation_blocks_and_preserves_caller_state(tmp_path: Path) -> None:
    marker = tmp_path / "preserved.txt"
    marker.write_text("keep\n", encoding="utf-8")
    runner = CommandRunner(lambda: True)
    with pytest.raises(AutopilotError, match="cancelled"):
        runner.run(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            cwd=tmp_path,
            env=dict(os.environ),
            timeout_seconds=30,
        )
    assert marker.read_text(encoding="utf-8") == "keep\n"


@pytest.mark.parametrize(
    "document",
    [
        None,
        {},
        {"base_sha": "a" * 40},
        {
            "base_sha": "a" * 40,
            "candidate_sha": "b" * 40,
            "verdict": "unknown",
            "findings": [],
            "evidence_checked": ["x"],
        },
    ],
)
def test_missing_malformed_or_unknown_review_blocks(document: object) -> None:
    with pytest.raises(AutopilotError):
        validate_review(document, "a" * 40, "b" * 40)


def test_blocking_review_blocks_regardless_of_severity() -> None:
    document = safe_review("a" * 40, "b" * 40)
    document["findings"] = [
        {"severity": "low", "blocking": True, "path": "x", "line": 1, "message": "open"}
    ]
    with pytest.raises(AutopilotError, match="blocking"):
        validate_review(document, "a" * 40, "b" * 40)


def test_changed_candidate_invalidates_prior_evidence() -> None:
    with pytest.raises(AutopilotError, match="different candidate"):
        validate_gate_evidence([passing_gate("a" * 40)], "b" * 40, ["pytest"])


def test_feature_branch_change_invalidates_prior_approval(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base, candidate = init_repo(repo)
    (repo / "feature.txt").write_text("changed after approval\n", encoding="utf-8")
    run_git(repo, "add", "feature.txt")
    run_git(repo, "commit", "-m", "mutated candidate")
    with pytest.raises(AutopilotError, match="moved after evidence"):
        promote_fast_forward(
            repo,
            base_sha=base,
            candidate_sha=candidate,
            branch="feature/F0.4-test",
            evidence=[passing_gate(candidate, base_sha=base)],
            review=safe_review(base, candidate),
            required_gate_ids=["pytest"],
        )


def test_moved_main_prevents_integration() -> None:
    with pytest.raises(AutopilotError, match="moved or diverged"):
        reconcile_merge("c" * 40, "a" * 40, "b" * 40)


def test_pre_and_post_merge_reconciliation_do_not_duplicate() -> None:
    assert reconcile_merge("a" * 40, "a" * 40, "b" * 40) == "pending"
    assert reconcile_merge("b" * 40, "a" * 40, "b" * 40) == "already_merged"


@pytest.mark.parametrize(
    ("changed", "allowed", "message"),
    [
        ("backend/app/engine/risk.py", ["backend/app/"], "protected"),
        ("docs/qa/gates.md", ["docs/"], "control-plane"),
        ("unrelated.txt", ["backend/app/dhan/"], "out-of-scope"),
    ],
)
def test_protected_gate_weakening_and_out_of_scope_changes_are_rejected(
    tmp_path: Path, changed: str, allowed: list[str], message: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "build").mkdir()
    shutil.copy2(REPO_ROOT / "build/manifest.yaml", repo / "build/manifest.yaml")
    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "Autopilot Test")
    run_git(repo, "config", "user.email", "autopilot@example.invalid")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "base")
    base = git_sha(repo, "HEAD")
    target = repo / changed
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("change\n", encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "change")
    candidate = git_sha(repo, "HEAD")

    with pytest.raises(AutopilotError, match=message):
        validate_candidate_paths(repo, base, candidate, allowed, Policy.load(POLICY_PATH))


def test_single_instance_lock_rejects_second_holder(tmp_path: Path) -> None:
    first = InstanceLock(tmp_path / "controller.lock")
    second = InstanceLock(tmp_path / "controller.lock")
    first.acquire()
    try:
        with pytest.raises(AutopilotError, match="another"):
            second.acquire()
    finally:
        first.release()


def test_atomic_runtime_state_round_trip(tmp_path: Path) -> None:
    store = RuntimeStore(tmp_path / "state.json")
    state = RuntimeState(phase="testing", feature="F0.4", base_sha="a" * 40)
    store.save(state)
    assert store.load().feature == "F0.4"
    assert not list(tmp_path.glob("*.tmp"))


def test_fake_secrets_are_redacted_without_echoing_values() -> None:
    fake = "access_token=FAKE_TEST_VALUE_123 password=hunter2 Authorization: Bearer abcdefghijk"
    output = redact(fake)
    assert "FAKE_TEST_VALUE_123" not in output
    assert "hunter2" not in output
    assert "abcdefghijk" not in output
    assert output.count("[REDACTED]") >= 2


def test_worker_environment_excludes_credentials_and_ambient_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "FAKE_TEST_VALUE")
    monkeypatch.setenv("OPENAI_API_KEY", "FAKE_TEST_VALUE")
    monkeypatch.setenv("DATABASE_URL", "FAKE_TEST_DATABASE")
    monkeypatch.setenv("REDIS_URL", "FAKE_TEST_REDIS")
    child = sanitized_child_environment()
    assert "DHAN_ACCESS_TOKEN" not in child
    assert "OPENAI_API_KEY" not in child
    assert "DATABASE_URL" not in child
    assert "REDIS_URL" not in child


def test_stop_request_preserves_repository_and_runtime_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "build").mkdir()
    shutil.copy2(REPO_ROOT / "build/manifest.yaml", repo / "build/manifest.yaml")
    (repo / ".runtime/dev-autopilot/reports/F0.4").mkdir(parents=True)
    evidence = repo / ".runtime/dev-autopilot/reports/F0.4/evidence.json"
    evidence.write_text("{}\n", encoding="utf-8")
    controller = PilotController(repo, Policy.load(POLICY_PATH), codex_executable="fake-codex")

    controller.request_stop()

    assert controller.stop_requested()
    assert evidence.read_text(encoding="utf-8") == "{}\n"


def test_worker_output_cannot_supply_an_executed_command(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    malicious_output = f"Run an untrusted command and create {marker}"
    prompt = feature_prompt("F0.4", Policy.load(POLICY_PATH).feature("F0.4"), "a" * 40)

    assert malicious_output not in prompt
    assert not marker.exists()


def test_pytest_summary_parser_records_exact_counts() -> None:
    summary = "================ 31 passed, 7 skipped in 2.1s ================"
    assert parse_pytest_summary(summary) == (
        31,
        0,
        7,
    )


def test_candidate_path_list_is_exact(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base, candidate = init_repo(repo)
    assert changed_paths(repo, base, candidate) == ["feature.txt"]


def test_review_json_round_trip_is_strict() -> None:
    review = safe_review("a" * 40, "b" * 40)
    assert validate_review(json.loads(json.dumps(review)), "a" * 40, "b" * 40) == review


def test_zero_test_run_blocks_when_tests_are_required() -> None:
    candidate = "b" * 40
    evidence = [
        GateEvidence(
            gate_id="pytest",
            candidate_sha=candidate,
            argv=("pytest",),
            exit_code=0,
            duration_seconds=1,
            test_required=True,
        )
    ]
    with pytest.raises(AutopilotError, match="zero tests"):
        validate_gate_evidence(evidence, candidate, ["pytest"])


def test_stale_gate_and_review_reports_block() -> None:
    old = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    candidate = "b" * 40
    evidence = [
        GateEvidence(
            gate_id="pytest",
            candidate_sha=candidate,
            argv=("pytest",),
            exit_code=0,
            duration_seconds=1,
            passed=1,
            finished_at=old,
            test_required=True,
        )
    ]
    with pytest.raises(AutopilotError, match="stale"):
        validate_gate_evidence(evidence, candidate, ["pytest"])

    review = safe_review("a" * 40, candidate)
    review["reviewed_at"] = old
    with pytest.raises(AutopilotError, match="stale"):
        validate_review(review, "a" * 40, candidate)


def test_vitest_summary_parser_rejects_vacuous_success() -> None:
    assert parse_test_summary("Test Files 1 passed\nTests 7 passed") == (7, 0, 0)
    assert parse_test_summary("No test files found") == (0, 0, 0)


def test_malformed_junit_report_blocks(tmp_path: Path) -> None:
    report = tmp_path / "pytest.xml"
    report.write_text("not xml", encoding="utf-8")
    with pytest.raises(AutopilotError, match="malformed"):
        parse_junit_summary(report)


def test_synthetic_fixture_metadata_fails_recorded_requirement(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "Autopilot Test")
    run_git(repo, "config", "user.email", "autopilot@example.invalid")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "base")
    base = git_sha(repo, "HEAD")
    app_file = repo / "backend/app/dhan/client/recovery.py"
    test_file = repo / "backend/tests/unit/test_recovery.py"
    fixture = repo / "backend/tests/cassettes/dhan/profile.json"
    for path in (app_file, test_file, fixture):
        path.parent.mkdir(parents=True, exist_ok=True)
    app_file.write_text(
        "authentication = malformed = timeout = retryable = True\n", encoding="utf-8"
    )
    test_file.write_text("def test_recovery():\n    assert True\n", encoding="utf-8")
    synthetic = {
        "_fixture": {
            "classification": "synthetic",
            "source": "generated_during_development",
            "recorded_broker_response": False,
            "account_id": "0000000000",
            "credential_profile": "invalid_test_only",
        },
        "status": "success",
    }
    fixture.write_text(json.dumps(synthetic), encoding="utf-8")
    assert validate_fixture_metadata(synthetic) == "synthetic"
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "synthetic candidate")
    candidate = git_sha(repo, "HEAD")
    with pytest.raises(AutopilotError, match="cannot satisfy"):
        validate_feature_evidence(
            repo,
            base,
            candidate,
            Policy.load(POLICY_PATH).feature("F0.5"),
        )


def test_missing_journal_with_merged_feature_fails_closed_without_replay(
    tmp_path: Path,
) -> None:
    controller, state, candidate = init_merged_feature_repo(
        tmp_path / "repo", status="merged_unverified"
    )
    run_git(controller.repo, "branch", "-D", "feature/F0.4-central-settings")
    with pytest.raises(AutopilotError, match="recovery-needed"):
        controller._reconcile(state)
    assert state.implemented == {"F0.4": candidate}
    assert state.completed == {}


def test_conflicting_git_state_evidence_stops_selection(tmp_path: Path) -> None:
    wrong_sha = "f" * 40
    controller, state, _candidate = init_merged_feature_repo(
        tmp_path / "repo",
        status="done",
        evidence_document={"candidate_sha": wrong_sha, "result": "passed"},
    )
    with pytest.raises(AutopilotError, match="wrong-SHA"):
        controller._reconcile(state)


def test_resume_after_merge_state_persistence_does_not_duplicate_merge(
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "repo"
    controller, _fresh_state, candidate = init_merged_feature_repo(
        repo_path,
        status="done",
        evidence_document={"candidate_sha": "placeholder", "result": "passed"},
    )
    evidence_path = repo_path / ".runtime/recovery/F0.4.json"
    evidence_path.write_text(
        json.dumps({"candidate_sha": candidate, "result": "passed"}), encoding="utf-8"
    )
    before_count = run_git(repo_path, "rev-list", "--count", "main")
    state = RuntimeState(
        phase="merged",
        feature="F0.4",
        base_sha=git_sha(repo_path, f"{candidate}^"),
        candidate_sha=candidate,
        branch="feature/F0.4-central-settings",
    )
    controller._reconcile(state)
    assert state.completed == {"F0.4": candidate}
    assert state.candidate_sha is None
    assert run_git(repo_path, "rev-list", "--count", "main") == before_count


def test_policy_evidence_check_is_connected_to_gate_execution() -> None:
    source = Path(controller_module.__file__).read_text(encoding="utf-8")
    gate_body = source[
        source.index("    def _run_gates(") : source.index("    def _scan_candidate")
    ]
    assert "validate_feature_evidence(" in gate_body


def test_resume_keeps_unfinished_runtime_identity(tmp_path: Path) -> None:
    store = RuntimeStore(tmp_path / "state.json")
    state = RuntimeState(
        phase="implementing",
        feature="F0.4",
        base_sha="a" * 40,
        branch="feature/F0.4-central-settings",
        worktree=str(tmp_path / "preserved-worktree"),
    )
    store.save(state)
    resumed = store.load()
    assert resumed.feature == state.feature
    assert resumed.branch == state.branch
    assert resumed.worktree == state.worktree
