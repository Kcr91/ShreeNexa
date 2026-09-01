"""Fail-closed controller primitives and the bounded F0.4-F0.9 feature loop."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from state_schema import StateError, validate_state
from update_state import update_state

ALLOWLIST = ("F0.4", "F0.5", "F0.6", "F0.7", "F0.8", "F0.9")
BASELINE_COMPLETE = {"M0.3", "F0.1", "F0.2", "F0.3"}
CONTROLLER_VERSION = 2
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TEST_SUMMARY_RE = re.compile(
    r"(?:(?P<passed>\d+) passed)?(?:,?\s*(?P<failed>\d+) failed)?"
    r"(?:,?\s*(?P<skipped>\d+) skipped)?"
)
SECRET_PATTERNS = (
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]{8,}"),
    re.compile(
        r"(?i)(access[-_ ]?token|authorization|api[-_ ]?secret|client[-_ ]?id|password|totp|pin)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(r"\beyJ[a-zA-Z0-9_-]{12,}\.[a-zA-Z0-9_-]{8,}(?:\.[a-zA-Z0-9_-]+)?\b"),
)
SECRET_SCAN_ASSIGNMENT_RE = re.compile(
    r"(?i)(access[-_ ]?token|authorization|api[-_ ]?secret|client[-_ ]?id|password|totp|pin)"
    r"\s*[:=]\s*['\"]?([^'\"\s,;]+)"
)
SAFE_TEST_VALUE_RE = re.compile(r"(?i)^(fake|test|dummy|example|placeholder|changeme|redacted)")


class AutopilotError(RuntimeError):
    """A fail-closed pilot blocker."""


class RepairableError(AutopilotError):
    """A candidate-code or confirmed-review finding eligible for a repair cycle."""


class GateFailureError(RepairableError):
    """A controller-defined gate failed without an infrastructure skip."""


class ReviewFindingsError(RepairableError):
    """A well-formed exact-SHA review contains findings."""


@dataclass(frozen=True)
class GateEvidence:
    gate_id: str
    candidate_sha: str
    argv: tuple[str, ...]
    exit_code: int
    duration_seconds: float
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    output_file: str | None = None
    base_sha: str = ""
    controller_version: int = CONTROLLER_VERSION
    policy_digest: str = ""
    started_at: str = ""
    finished_at: str = ""
    output_sha256: str = ""
    test_required: bool = False
    test_report_file: str | None = None
    test_report_sha256: str = ""


@dataclass
class RuntimeState:
    version: int = 1
    phase: str = "idle"
    setup_sha: str | None = None
    remote_fingerprint: str | None = None
    acceptance_sha256: str | None = None
    feature: str | None = None
    base_sha: str | None = None
    candidate_sha: str | None = None
    branch: str | None = None
    worktree: str | None = None
    repair_cycle: int = 0
    completed: dict[str, str] = field(default_factory=dict)
    implemented: dict[str, str] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    active_pid: int | None = None
    blocker: str | None = None
    implementation_session_id: str | None = None
    updated_at: str | None = None


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def redact(text: str) -> str:
    """Remove secret-shaped values without returning the match itself."""
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        if os.name != "nt":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp.unlink()


class RuntimeStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> RuntimeState:
        if not self.path.exists():
            return RuntimeState()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("version") != 1:
            raise AutopilotError("runtime state is malformed or has an unsupported version")
        allowed = set(RuntimeState.__dataclass_fields__)
        if set(raw) - allowed:
            raise AutopilotError("runtime state contains unknown fields")
        state = RuntimeState(**raw)
        validate_runtime_state(state)
        return state

    def save(self, state: RuntimeState) -> None:
        validate_runtime_state(state)
        state.updated_at = utc_now()
        atomic_write_json(self.path, asdict(state))


def validate_runtime_state(state: RuntimeState) -> None:
    if state.phase not in {
        "idle",
        "implementing",
        "testing",
        "repairing",
        "approved",
        "merged",
        "blocked",
        "stopped",
        "complete",
    }:
        raise AutopilotError("runtime state phase is unknown")
    completed_ids = list(state.completed)
    if completed_ids != list(ALLOWLIST[: len(completed_ids)]):
        raise AutopilotError("runtime completed features are not an ordered allowlist prefix")
    if any(not SHA_RE.fullmatch(sha) for sha in state.completed.values()):
        raise AutopilotError("runtime completed feature contains an invalid SHA")
    implemented_ids = list(state.implemented)
    if implemented_ids != list(ALLOWLIST[: len(implemented_ids)]):
        raise AutopilotError("runtime implemented features are not an ordered allowlist prefix")
    if any(not SHA_RE.fullmatch(sha) for sha in state.implemented.values()):
        raise AutopilotError("runtime implemented feature contains an invalid SHA")
    if any(state.implemented.get(key) != value for key, value in state.completed.items()):
        raise AutopilotError("verified runtime completion is not present in implemented Git state")
    for field_name in ("setup_sha", "base_sha", "candidate_sha"):
        value = getattr(state, field_name)
        if value is not None and not SHA_RE.fullmatch(value):
            raise AutopilotError(f"runtime {field_name} is not a full Git SHA")
    if state.acceptance_sha256 is not None and not re.fullmatch(
        r"[0-9a-f]{64}", state.acceptance_sha256
    ):
        raise AutopilotError("runtime acceptance hash is invalid")
    if not isinstance(state.repair_cycle, int) or not 0 <= state.repair_cycle <= 3:
        raise AutopilotError("runtime repair cycle is outside the bounded range")
    if state.feature is not None and state.feature not in ALLOWLIST:
        raise AutopilotError("runtime current feature is not allowlisted")


class InstanceLock:
    """An OS-held lock; a stale metadata file alone never blocks recovery."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: Any | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            handle.seek(0)
            if handle.read(1) == b"":
                handle.seek(0)
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            handle.close()
            raise AutopilotError("another development autopilot instance holds the lock") from exc
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps({"pid": os.getpid(), "started_at": utc_now()}).encode())
        handle.flush()
        self._handle = handle

    def release(self) -> None:
        if self._handle is None:
            return
        handle = self._handle
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            self._handle = None

    def __enter__(self) -> InstanceLock:
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


def _normalized_repo_path(raw: str) -> str:
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise AutopilotError(f"unsafe repository path reported by Git: {raw!r}")
    return path.as_posix()


def path_matches(path: str, rule: str) -> bool:
    normalized = _normalized_repo_path(path)
    rule_normalized = _normalized_repo_path(rule.rstrip("/"))
    return normalized == rule_normalized or normalized.startswith(f"{rule_normalized}/")


@dataclass(frozen=True)
class Policy:
    raw: dict[str, Any]
    digest: str

    @classmethod
    def load(cls, path: Path) -> Policy:
        payload = path.read_bytes()
        raw = yaml.safe_load(payload)
        if not isinstance(raw, dict) or raw.get("version") != CONTROLLER_VERSION:
            raise AutopilotError(f"policy must match controller version {CONTROLLER_VERSION}")
        if tuple(raw.get("allowlist", ())) != ALLOWLIST:
            raise AutopilotError("policy allowlist differs from the authorized F0.4-F0.9 sequence")
        if set(raw.get("features", {})) != set(ALLOWLIST):
            raise AutopilotError("policy feature definitions do not exactly match the allowlist")
        if raw.get("max_repair_cycles") != 3:
            raise AutopilotError("repair-cycle limit must remain exactly three")
        return cls(raw=raw, digest=hashlib.sha256(payload).hexdigest())

    @property
    def control_plane(self) -> list[str]:
        return list(self.raw["control_plane"])

    @property
    def protected_paths(self) -> list[str]:
        return list(self.raw["protected_paths"])

    def feature(self, feature_id: str) -> dict[str, Any]:
        if feature_id not in ALLOWLIST:
            raise AutopilotError(f"feature {feature_id!r} is not allowlisted")
        value = self.raw["features"][feature_id]
        if not isinstance(value, dict):
            raise AutopilotError(f"feature policy for {feature_id} is malformed")
        return value

    def validate_manifest(self, manifest_path: Path) -> None:
        manifest = yaml.safe_load(manifest_path.read_bytes())
        if not isinstance(manifest, dict) or not isinstance(manifest.get("items"), list):
            raise AutopilotError("build manifest is malformed")
        items = {
            item.get("id"): item
            for item in manifest["items"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for feature_id in ALLOWLIST:
            if feature_id not in items:
                raise AutopilotError(f"allowlisted feature {feature_id} is absent from manifest")
            manifest_dependencies = tuple(items[feature_id].get("depends_on", ()))
            policy_dependencies = tuple(self.feature(feature_id).get("dependencies", ()))
            if manifest_dependencies != policy_dependencies:
                raise AutopilotError(
                    f"policy dependencies for {feature_id} differ from build/manifest.yaml"
                )


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if check and result.returncode != 0:
        raise AutopilotError(redact(f"git {' '.join(args)} failed: {result.stderr.strip()}"))
    return result.stdout.strip()


def git_sha(repo: Path, revision: str) -> str:
    sha = run_git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if not SHA_RE.fullmatch(sha):
        raise AutopilotError(f"Git returned an invalid SHA for {revision!r}")
    return sha


def git_is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise AutopilotError("Git ancestry check failed")
    return result.returncode == 0


def git_ref_exists(repo: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", ref],
        cwd=repo,
        timeout=120,
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise AutopilotError("Git reference check failed")
    return result.returncode == 0


def changed_paths(repo: Path, base_sha: str, candidate_sha: str) -> list[str]:
    output = run_git(repo, "diff", "--name-only", f"{base_sha}..{candidate_sha}")
    return [_normalized_repo_path(line) for line in output.splitlines() if line.strip()]


def validate_candidate_paths(
    repo: Path,
    base_sha: str,
    candidate_sha: str,
    allowed: Sequence[str],
    policy: Policy,
    *,
    controller_paths_allowed: bool = False,
) -> list[str]:
    paths = changed_paths(repo, base_sha, candidate_sha)
    forbidden = policy.protected_paths + policy.control_plane
    if controller_paths_allowed:
        forbidden = policy.protected_paths
    for path in paths:
        if any(path_matches(path, rule) for rule in forbidden):
            raise AutopilotError(f"candidate changes protected/control-plane path: {path}")
        if not any(path_matches(path, rule) for rule in allowed):
            raise AutopilotError(f"candidate changes out-of-scope path: {path}")
    tree = run_git(repo, "ls-tree", "-r", candidate_sha)
    for line in tree.splitlines():
        metadata, _, raw_path = line.partition("\t")
        mode = metadata.split(" ", 1)[0]
        path = _normalized_repo_path(raw_path)
        if path in paths and mode in {"120000", "160000"}:
            raise AutopilotError(f"candidate introduces a symlink or submodule: {path}")
    return paths


def validate_review(
    document: Any,
    base_sha: str,
    candidate_sha: str,
    *,
    expected_review_session_id: str | None = None,
    implementer_session_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise AutopilotError("review output is missing or not a JSON object")
    required = {
        "base_sha",
        "candidate_sha",
        "verdict",
        "findings",
        "evidence_checked",
        "independent",
        "reviewer_session_id",
        "reviewed_at",
    }
    if set(document) != required:
        raise AutopilotError("review output has missing or unknown fields")
    if document["base_sha"] != base_sha or document["candidate_sha"] != candidate_sha:
        raise AutopilotError("review output does not match the exact base/candidate SHAs")
    if not SHA_RE.fullmatch(document["base_sha"]) or not SHA_RE.fullmatch(
        document["candidate_sha"]
    ):
        raise AutopilotError("review output contains invalid SHA syntax")
    if document["verdict"] not in {"safe_to_merge", "blocked"}:
        raise AutopilotError("review verdict is unknown")
    if document["independent"] is not True:
        raise AutopilotError("implementer self-review is not independent review")
    if not isinstance(document["reviewer_session_id"], str) or not document["reviewer_session_id"]:
        raise AutopilotError("reviewer session identity is missing")
    if (
        expected_review_session_id is not None
        and document["reviewer_session_id"] != expected_review_session_id
    ):
        raise AutopilotError("review output came from the wrong reviewer session")
    if implementer_session_id and document["reviewer_session_id"] == implementer_session_id:
        raise AutopilotError("implementer self-review is not independent review")
    reviewed_at = parse_utc(document["reviewed_at"], "reviewed_at")
    age = (datetime.now(UTC) - reviewed_at).total_seconds()
    if age < -300 or age > 86_400:
        raise AutopilotError("independent review is stale or has an invalid timestamp")
    findings = document["findings"]
    evidence = document["evidence_checked"]
    if not isinstance(findings, list) or not isinstance(evidence, list) or not evidence:
        raise AutopilotError("review findings/evidence are malformed or missing")
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {
            "severity",
            "blocking",
            "path",
            "line",
            "message",
        }:
            raise AutopilotError("review finding is malformed")
        if finding["severity"] not in {"critical", "high", "medium", "low"}:
            raise AutopilotError("review finding severity is unknown")
        line = finding["line"]
        line_is_valid = line is None or (
            isinstance(line, int) and not isinstance(line, bool) and line >= 1
        )
        if (
            not isinstance(finding["blocking"], bool)
            or not isinstance(finding["path"], str)
            or not isinstance(finding["message"], str)
            or not finding["message"]
            or not line_is_valid
        ):
            raise AutopilotError("review finding has invalid blocking/message fields")
    if not all(isinstance(item, str) and item for item in evidence):
        raise AutopilotError("review evidence entries are malformed")
    if document["verdict"] != "safe_to_merge" or findings:
        raise ReviewFindingsError(
            "independent review is blocked or contains unresolved blocking findings"
        )
    return document


def parse_utc(value: object, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise AutopilotError(f"{field_name} is missing or malformed")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AutopilotError(f"{field_name} is missing or malformed") from exc
    if parsed.tzinfo is None:
        raise AutopilotError(f"{field_name} must include a timezone")
    return parsed.astimezone(UTC)


def parse_pytest_summary(output: str) -> tuple[int, int, int]:
    passed = failed = skipped = 0
    for match in TEST_SUMMARY_RE.finditer(output):
        values = tuple(int(match.group(name) or 0) for name in ("passed", "failed", "skipped"))
        if sum(values) > sum((passed, failed, skipped)):
            passed, failed, skipped = values
    return passed, failed, skipped


def parse_test_summary(output: str) -> tuple[int, int, int]:
    pytest_counts = parse_pytest_summary(output)
    if sum(pytest_counts):
        return pytest_counts
    match = re.search(
        r"Tests\s+(?:(?P<passed>\d+)\s+passed)?(?:\s*\|\s*)?"
        r"(?:(?P<failed>\d+)\s+failed)?(?:\s*\|\s*)?"
        r"(?:(?P<skipped>\d+)\s+skipped)?",
        output,
        re.IGNORECASE,
    )
    if not match:
        return 0, 0, 0
    return tuple(int(match.group(name) or 0) for name in ("passed", "failed", "skipped"))


def parse_junit_summary(path: Path) -> tuple[int, int, int]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise AutopilotError("pytest JUnit report is missing or malformed") from exc
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise AutopilotError("pytest JUnit report contains no test suites")
    total = sum(int(suite.attrib.get("tests", "0")) for suite in suites)
    failed = sum(
        int(suite.attrib.get("failures", "0")) + int(suite.attrib.get("errors", "0"))
        for suite in suites
    )
    skipped = sum(int(suite.attrib.get("skipped", "0")) for suite in suites)
    passed = total - failed - skipped
    if min(total, failed, skipped, passed) < 0:
        raise AutopilotError("pytest JUnit report has invalid test counts")
    return passed, failed, skipped


def validate_fixture_metadata(document: object) -> str:
    if not isinstance(document, dict) or not isinstance(document.get("_fixture"), dict):
        raise AutopilotError("cassette fixture provenance metadata is missing")
    metadata = document["_fixture"]
    required = {
        "classification",
        "source",
        "recorded_broker_response",
        "account_id",
        "credential_profile",
    }
    if not required.issubset(metadata):
        raise AutopilotError("cassette fixture provenance metadata is malformed")
    account_id = metadata["account_id"]
    if not isinstance(account_id, str) or not re.fullmatch(r"\d{10}", account_id):
        raise AutopilotError("cassette fixture account identifier has the wrong format")
    classification = metadata["classification"]
    if classification == "synthetic":
        if (
            set(metadata) != required
            or metadata["source"] != "generated_during_development"
            or metadata["recorded_broker_response"] is not False
            or account_id != "0000000000"
            or metadata["credential_profile"] != "invalid_test_only"
        ):
            raise AutopilotError("synthetic cassette fixture metadata is ambiguous")
        return "synthetic"
    if classification == "recorded_sanitized":
        recorded_required = required | {"recorded_at", "broker_origin", "sanitization"}
        if set(metadata) != recorded_required or metadata["recorded_broker_response"] is not True:
            raise AutopilotError("recorded cassette metadata contradicts its classification")
        if not all(
            isinstance(metadata[key], str) and metadata[key].strip()
            for key in ("recorded_at", "broker_origin", "sanitization")
        ):
            raise AutopilotError("recorded cassette provenance is incomplete")
        return "recorded_sanitized"
    raise AutopilotError("cassette fixture classification is unknown")


def validate_feature_evidence(
    worktree: Path,
    base_sha: str,
    candidate_sha: str,
    feature: dict[str, Any],
) -> dict[str, Any]:
    checks = feature.get("evidence_checks", {})
    paths = changed_paths(worktree, base_sha, candidate_sha)
    for pattern in checks.get("required_changed_globs", []):
        if not any(PurePosixPath(path).match(pattern) for path in paths):
            raise AutopilotError(f"feature evidence is missing required changed path: {pattern}")
    allowed_paths = list(feature.get("allowed_paths", []))
    searchable_paths = [
        path for path in paths if any(path_matches(path, allowed) for allowed in allowed_paths)
    ]
    searchable = "\n".join(
        (worktree / path).read_text(encoding="utf-8", errors="replace")
        for path in searchable_paths
        if (worktree / path).is_file()
    ).lower()
    missing_terms = [
        term for term in checks.get("required_terms", []) if str(term).lower() not in searchable
    ]
    if missing_terms:
        raise AutopilotError("feature evidence is missing required acceptance terms")
    fixture_classes: dict[str, str] = {}
    recorded_glob = checks.get("recorded_json_glob")
    if recorded_glob:
        fixtures = sorted(worktree.glob(str(recorded_glob)))
        if not fixtures:
            raise AutopilotError("recorded-cassette evidence is missing")
        for fixture in fixtures:
            try:
                document = json.loads(fixture.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise AutopilotError("cassette fixture JSON is malformed") from exc
            fixture_classes[fixture.name] = validate_fixture_metadata(document)
        if any(value != "recorded_sanitized" for value in fixture_classes.values()):
            raise AutopilotError(
                "synthetic fixtures cannot satisfy the recorded-cassette evidence requirement"
            )
    return {
        "base_sha": base_sha,
        "candidate_sha": candidate_sha,
        "required_terms": list(checks.get("required_terms", [])),
        "fixture_classifications": fixture_classes,
        "result": "passed",
        "validated_at": utc_now(),
    }


def validate_gate_evidence(
    evidence: Sequence[GateEvidence],
    candidate_sha: str,
    required_gate_ids: Sequence[str] | None = None,
    *,
    base_sha: str | None = None,
    controller_version: int | None = None,
    policy_digest: str | None = None,
    repo: Path | None = None,
) -> None:
    if not evidence:
        raise AutopilotError("no gate evidence was supplied")
    ids: set[str] = set()
    for item in evidence:
        if item.gate_id in ids:
            raise AutopilotError(f"duplicate gate evidence: {item.gate_id}")
        ids.add(item.gate_id)
        if item.candidate_sha != candidate_sha:
            raise AutopilotError("gate evidence was produced for a different candidate SHA")
        if base_sha is not None and item.base_sha != base_sha:
            raise AutopilotError("gate evidence was produced for a different base SHA")
        if controller_version is not None and item.controller_version != controller_version:
            raise AutopilotError("gate evidence used a different controller version")
        if policy_digest is not None and item.policy_digest != policy_digest:
            raise AutopilotError("gate evidence used a different policy digest")
        if item.exit_code != 0 or item.failed:
            raise GateFailureError(f"gate {item.gate_id} failed")
        if item.test_required and item.passed + item.failed + item.skipped == 0:
            raise AutopilotError(f"required test gate {item.gate_id} executed zero tests")
        if item.test_required and item.skipped:
            raise AutopilotError(f"required test gate {item.gate_id} contains skipped tests")
        if item.finished_at:
            age = (
                datetime.now(UTC) - parse_utc(item.finished_at, "gate finished_at")
            ).total_seconds()
            if age < -300 or age > 86_400:
                raise AutopilotError(f"gate evidence for {item.gate_id} is stale")
        elif repo is not None:
            raise AutopilotError(f"gate evidence for {item.gate_id} has no timestamp")
        if repo is not None:
            if not item.output_file or not item.output_sha256:
                raise AutopilotError(f"gate report for {item.gate_id} is missing")
            report = (repo / item.output_file).resolve()
            if repo.resolve() not in report.parents or not report.is_file():
                raise AutopilotError(f"gate report for {item.gate_id} is missing")
            if hashlib.sha256(report.read_bytes()).hexdigest() != item.output_sha256:
                raise AutopilotError(f"gate report for {item.gate_id} is malformed or stale")
            if item.gate_id == "pytest":
                if not item.test_report_file or not item.test_report_sha256:
                    raise AutopilotError("pytest JUnit report is missing")
                test_report = (repo / item.test_report_file).resolve()
                if repo.resolve() not in test_report.parents or not test_report.is_file():
                    raise AutopilotError("pytest JUnit report is missing")
                if hashlib.sha256(test_report.read_bytes()).hexdigest() != item.test_report_sha256:
                    raise AutopilotError("pytest JUnit report is malformed or stale")
                if parse_junit_summary(test_report) != (
                    item.passed,
                    item.failed,
                    item.skipped,
                ):
                    raise AutopilotError("pytest JUnit counts disagree with gate evidence")
    if required_gate_ids is not None and ids != set(required_gate_ids):
        raise AutopilotError("gate evidence does not exactly match the pinned required gate set")


def reconcile_merge(main_sha: str, base_sha: str, candidate_sha: str) -> str:
    if main_sha == base_sha:
        return "pending"
    if main_sha == candidate_sha:
        return "already_merged"
    raise AutopilotError("main moved or diverged from the recorded base/candidate")


def promote_fast_forward(
    repo: Path,
    *,
    base_sha: str,
    candidate_sha: str,
    branch: str,
    evidence: Sequence[GateEvidence],
    review: dict[str, Any],
    required_gate_ids: Sequence[str] | None = None,
    controller_version: int | None = None,
    policy_digest: str | None = None,
    review_file: Path | None = None,
    review_sha256: str | None = None,
) -> str:
    validate_gate_evidence(
        evidence,
        candidate_sha,
        required_gate_ids,
        base_sha=base_sha,
        controller_version=controller_version,
        policy_digest=policy_digest,
        repo=repo if controller_version is not None else None,
    )
    validate_review(review, base_sha, candidate_sha)
    if review_file is not None:
        resolved_review = review_file.resolve()
        if repo.resolve() not in resolved_review.parents or not resolved_review.is_file():
            raise AutopilotError("independent review report is absent")
        actual_review_sha256 = hashlib.sha256(resolved_review.read_bytes()).hexdigest()
        if not review_sha256 or actual_review_sha256 != review_sha256:
            raise AutopilotError("independent review report is malformed or stale")
    main_sha = git_sha(repo, "main")
    reconciliation = reconcile_merge(main_sha, base_sha, candidate_sha)
    if reconciliation == "already_merged":
        return candidate_sha
    if run_git(repo, "status", "--porcelain"):
        raise AutopilotError("integration worktree is not clean")
    if git_sha(repo, branch) != candidate_sha:
        raise AutopilotError("feature branch moved after evidence was produced")
    run_git(repo, "switch", "main")
    run_git(repo, "merge", "--ff-only", candidate_sha)
    if git_sha(repo, "main") != candidate_sha:
        raise AutopilotError("fast-forward did not produce the reviewed candidate")
    return candidate_sha


class CommandRunner:
    def __init__(self, stop_requested: Callable[[], bool]) -> None:
        self.stop_requested = stop_requested

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: int,
        input_text: str | None = None,
    ) -> tuple[int, float, str]:
        started = time.monotonic()
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = ""
        pending_input = input_text
        while True:
            try:
                result, _ = process.communicate(input=pending_input, timeout=1)
                pending_input = None
                output = result or ""
                break
            except subprocess.TimeoutExpired:
                pending_input = None
                if self.stop_requested():
                    terminate_process_tree(process.pid)
                    result, _ = process.communicate(timeout=10)
                    raise AutopilotError(
                        redact(f"command cancelled; output: {result or ''}")
                    ) from None
                if time.monotonic() - started > timeout_seconds:
                    terminate_process_tree(process.pid)
                    result, _ = process.communicate(timeout=10)
                    raise AutopilotError(
                        redact(f"command timed out; output: {result or ''}")
                    ) from None
        return process.returncode, time.monotonic() - started, redact(output)


def terminate_process_tree(pid: int) -> None:
    try:
        import psutil

        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for process in reversed(children):
            process.terminate()
        parent.terminate()
        _, alive = psutil.wait_procs([*children, parent], timeout=5)
        for process in alive:
            process.kill()
    except ImportError, OSError:
        with contextlib.suppress(OSError):
            os.kill(pid, 15)


class CodexAdapter:
    def __init__(self, executable: str, runner: CommandRunner, policy: Policy) -> None:
        self.executable = executable
        self.runner = runner
        self.policy = policy

    def _validate_argv(self, argv: Sequence[str]) -> None:
        forbidden = set(self.policy.raw["forbidden_codex_arguments"])
        if any(argument in forbidden for argument in argv):
            raise AutopilotError("forbidden Codex permission/configuration argument requested")

    def implement(self, worktree: Path, prompt: str, output: Path) -> str:
        argv = [
            self.executable,
            "exec",
            "--sandbox",
            "workspace-write",
            "--ephemeral",
            "--json",
            "-C",
            str(worktree),
            "-",
        ]
        self._validate_argv(argv)
        event_stream = self._invoke(argv, worktree, prompt)
        output.write_text(event_stream, encoding="utf-8", newline="\n")
        return event_stream

    def review(
        self,
        worktree: Path,
        prompt: str,
        schema: Path,
        output: Path,
        base_sha: str,
    ) -> dict[str, Any]:
        argv = [
            self.executable,
            "exec",
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--output-schema",
            str(schema),
            "--json",
            "-C",
            str(worktree),
            "-",
        ]
        self._validate_argv(argv)
        event_stream = self._invoke(argv, worktree, prompt)
        try:
            final_message = extract_final_agent_message(event_stream)
            document = json.loads(final_message)
        except (AutopilotError, json.JSONDecodeError) as exc:
            raise AutopilotError("review output is missing or malformed") from exc
        output.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return document

    def _invoke(self, argv: Sequence[str], cwd: Path, prompt: str) -> str:
        # Prompts contain policy/feature text only. Credentials are never accepted here.
        env = sanitized_child_environment()
        exit_code, duration, output = self.runner.run(
            argv,
            cwd=cwd,
            env=env,
            timeout_seconds=int(self.policy.raw["codex_timeout_seconds"]),
            input_text=prompt,
        )
        if exit_code != 0:
            raise AutopilotError(redact(f"Codex invocation failed after {duration:.1f}s: {output}"))
        return redact(output)


def extract_final_agent_message(event_stream: str) -> str:
    final_message: str | None = None
    for line in event_stream.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if (
            event.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("type") == "agent_message"
            and isinstance(item.get("text"), str)
        ):
            final_message = item["text"]
    if final_message is None:
        raise AutopilotError("Codex event stream has no final agent message")
    return final_message


def sanitized_child_environment() -> dict[str, str]:
    blocked_fragments = (
        "DHAN",
        "TOKEN",
        "SECRET",
        "PASSWORD",
        "TOTP",
        "PIN",
        "COOKIE",
        "API_KEY",
    )
    return {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in {"DATABASE_URL", "REDIS_URL", "OPENAI_API_KEY"}
        and not any(fragment in key.upper() for fragment in blocked_fragments)
    }


class DisposableServices:
    """Create an explicitly named disposable Postgres DB and isolated Redis DB."""

    PREFIX = "shreenexa_autopilot_test_"

    def __init__(self) -> None:
        self.name = f"{self.PREFIX}{secrets.token_hex(6)}"
        self.admin_dsn = "postgresql://shreenexa:shreenexa_local_dev_only@127.0.0.1:5432/shreenexa"

    def __enter__(self) -> dict[str, str]:
        try:
            import psycopg
            from psycopg import sql
        except ImportError as exc:
            raise AutopilotError("psycopg is unavailable; run the controller through uv") from exc
        try:
            with psycopg.connect(self.admin_dsn, autocommit=True, connect_timeout=5) as conn:
                conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.name)))
        except Exception as exc:
            raise AutopilotError(
                "configured local Postgres is unavailable for isolated tests"
            ) from exc
        env = sanitized_child_environment()
        env["DATABASE_URL"] = (
            f"postgresql+psycopg://shreenexa:shreenexa_local_dev_only@127.0.0.1:5432/{self.name}"
        )
        env["REDIS_URL"] = "redis://127.0.0.1:6379/15"
        env["SHREENEXA_AUTOPILOT_TEST_DATABASE"] = self.name
        return env

    def __exit__(self, *_: object) -> None:
        if not self.name.startswith(self.PREFIX):
            raise AutopilotError("refusing to remove a database outside the disposable prefix")
        import psycopg
        from psycopg import sql

        with psycopg.connect(self.admin_dsn, autocommit=True, connect_timeout=5) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(self.name)))


def feature_prompt(feature_id: str, feature: dict[str, Any], base_sha: str) -> str:
    allowed = "\n".join(f"- {path}" for path in feature["allowed_paths"])
    non_goals = "\n".join(f"- {item}" for item in feature["non_goals"])
    evidence = "\n".join(f"- {item}" for item in feature["evidence"])
    return f"""Implement only ShreeNexa {feature_id} from base {base_sha}.
Read AGENTS.md, the controller-pinned feature acceptance contract, and the
repository source-of-truth documents first. Do not modify the acceptance
contract and do not access any unrelated project.

Allowed product paths:
{allowed}

Controller-owned build/state.json and PROJECT_UPDATE.md are forbidden to you.
All control-plane and protected paths in AGENTS.md are forbidden. Do not change
Git configuration, remotes, permissions, QA thresholds, or the allowlist. Do
not use or request real credentials. Do not make external writes or live calls.

Non-goals:
{non_goals}

Required evidence:
{evidence}

Run narrow checks where useful, but do not claim completion, commit, merge, or
invent evidence. The controller will validate scope, run the canonical gates,
commit, and request independent review. If evidence or a decision is missing,
stop and state the exact blocker in your final response.
"""


def review_prompt(
    feature_id: str, base_sha: str, candidate_sha: str, reviewer_session_id: str
) -> str:
    return f"""Independently review ShreeNexa {feature_id}. Base SHA is
{base_sha}; exact candidate SHA is {candidate_sha}. Remain read-only. Verify
scope, acceptance behavior, tests, secrets, path safety, determinism,
migrations, service isolation, control-plane/protected paths, and truthful
evidence. Any unresolved finding is blocking regardless of severity. Return
only the required JSON shape bound to those exact SHAs. Never use credentials,
make external writes, or accept the implementer's summary as evidence.
Set independent to true, reviewer_session_id to {reviewer_session_id}, and
reviewed_at to the current UTC instant. This is a fresh ephemeral reviewer
session distinct from the implementation session.
"""


class PilotController:
    def __init__(self, repo: Path, policy: Policy, codex_executable: str = "codex") -> None:
        self.repo = repo.resolve()
        self.policy = policy
        self.policy.validate_manifest(self.repo / "build/manifest.yaml")
        self.runtime_root = self.repo / policy.raw["runtime_root"]
        self.store = RuntimeStore(self.runtime_root / "state.json")
        self.stop_file = self.runtime_root / "stop-requested.json"
        self.runner = CommandRunner(self.stop_requested)
        self.codex = CodexAdapter(codex_executable, self.runner, policy)

    def stop_requested(self) -> bool:
        return self.stop_file.exists()

    def request_stop(self) -> None:
        atomic_write_json(self.stop_file, {"requested_at": utc_now()})

    def clear_stop(self) -> None:
        with contextlib.suppress(FileNotFoundError):
            self.stop_file.unlink()

    def status(self) -> dict[str, Any]:
        status = asdict(self.store.load())
        launcher = self.runtime_root / "launcher.json"
        if launcher.exists():
            try:
                status["launcher"] = json.loads(launcher.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                status["launcher"] = {"status": "malformed"}
        return status

    def run(self, *, resume: bool = False) -> RuntimeState:
        with InstanceLock(self.runtime_root / "controller.lock"):
            if resume:
                self.clear_stop()
            state = self.store.load()
            self._verify_setup_pin(state)
            self._reconcile(state)
            while True:
                if self.stop_requested():
                    state.phase = "stopped"
                    self.store.save(state)
                    return state
                feature_id = next((item for item in ALLOWLIST if item not in state.completed), None)
                if feature_id is None:
                    state.phase = "complete"
                    state.feature = None
                    self.store.save(state)
                    return state
                if feature_id in state.implemented:
                    state.phase = "blocked"
                    state.feature = feature_id
                    state.blocker = (
                        f"recovery-needed: {feature_id} is merged but is not verified complete"
                    )
                    self.store.save(state)
                    raise AutopilotError(state.blocker)
                self._run_feature(state, feature_id)

    def _verify_setup_pin(self, state: RuntimeState) -> None:
        if state.setup_sha is None:
            setup_sha = run_git(
                self.repo,
                "log",
                "-1",
                "--format=%H",
                "main",
                "--",
                "build/autopilot/controller.py",
            )
            if not SHA_RE.fullmatch(setup_sha):
                raise AutopilotError("approved controller version is not present in Git history")
            state.setup_sha = setup_sha
            state.remote_fingerprint = hashlib.sha256(
                run_git(self.repo, "remote", "-v").encode("utf-8")
            ).hexdigest()
            self.store.save(state)
        if not SHA_RE.fullmatch(state.setup_sha):
            raise AutopilotError("runtime setup pin is invalid")
        current_remote_fingerprint = hashlib.sha256(
            run_git(self.repo, "remote", "-v").encode("utf-8")
        ).hexdigest()
        if state.remote_fingerprint != current_remote_fingerprint:
            raise AutopilotError("Git remote configuration changed after the setup pin")
        for path in self.policy.control_plane:
            output = run_git(self.repo, "diff", "--name-only", state.setup_sha, "--", path)
            if output:
                raise AutopilotError(f"pinned control-plane path changed after setup: {path}")

    def _reconcile(self, state: RuntimeState) -> None:
        tracked_path = self.repo / "build/state.json"
        try:
            tracked = json.loads(tracked_path.read_text(encoding="utf-8"))
            validate_state(tracked)
        except (OSError, json.JSONDecodeError, StateError) as exc:
            raise AutopilotError("recovery-needed: tracked feature state is invalid") from exc
        tracked_features = tracked.get("features", {})
        main_sha = git_sha(self.repo, "main")
        implemented: dict[str, str] = {}
        for feature_id in ALLOWLIST:
            branch = str(self.policy.feature(feature_id)["branch"])
            ref = f"refs/heads/{branch}"
            record = tracked_features.get(feature_id)
            tracked_commit = record.get("commit") if isinstance(record, dict) else None
            candidate: str | None = None
            if tracked_commit:
                try:
                    candidate = git_sha(self.repo, str(tracked_commit))
                except AutopilotError as exc:
                    raise AutopilotError(
                        f"recovery-needed: tracked commit for {feature_id} is invalid"
                    ) from exc
            if git_ref_exists(self.repo, ref):
                branch_candidate = git_sha(self.repo, ref)
                if candidate is not None and branch_candidate != candidate:
                    raise AutopilotError(
                        f"recovery-needed: branch and tracked commit disagree for {feature_id}"
                    )
                candidate = branch_candidate
            if candidate is None:
                break
            if not git_is_ancestor(self.repo, candidate, main_sha):
                break
            implemented[feature_id] = candidate
        if state.implemented and state.implemented != implemented:
            raise AutopilotError(
                "recovery-needed: durable journal disagrees with merged Git feature history"
            )
        state.implemented = implemented
        verified: dict[str, str] = {}
        pending_finalize = False
        for feature_id, candidate_sha in implemented.items():
            record = tracked_features.get(feature_id)
            if not isinstance(record, dict):
                state.completed = verified
                state.phase = "blocked"
                state.blocker = (
                    f"recovery-needed: {feature_id} is merged but has no tracked feature record"
                )
                self.store.save(state)
                raise AutopilotError(state.blocker)
            try:
                tracked_commit = git_sha(self.repo, str(record.get("commit")))
            except AutopilotError as exc:
                raise AutopilotError(
                    f"recovery-needed: tracked commit for {feature_id} is invalid"
                ) from exc
            if tracked_commit != candidate_sha:
                raise AutopilotError(
                    f"recovery-needed: Git and tracked commit disagree for {feature_id}"
                )
            if record.get("status") != "done":
                if (
                    state.feature == feature_id
                    and state.candidate_sha == candidate_sha
                    and main_sha == candidate_sha
                    and state.phase in {"approved", "merged"}
                ):
                    pending_finalize = True
                    break
                state.completed = verified
                state.phase = "blocked"
                state.feature = feature_id
                state.blocker = (
                    f"recovery-needed: {feature_id} is merged with status {record.get('status')!r}"
                )
                self.store.save(state)
                raise AutopilotError(state.blocker)
            self._validate_tracked_evidence(feature_id, candidate_sha, record)
            verified[feature_id] = candidate_sha
        if pending_finalize:
            state.completed = verified
            self._resume_merged_candidate(state)
            return
        if state.completed and state.completed != verified:
            raise AutopilotError(
                "recovery-needed: durable verified state disagrees with tracked evidence"
            )
        state.completed = verified
        if state.base_sha and state.candidate_sha:
            if (
                git_is_ancestor(self.repo, state.candidate_sha, main_sha)
                and state.candidate_sha != main_sha
                and state.completed.get(state.feature or "") == state.candidate_sha
            ):
                state.base_sha = None
                state.candidate_sha = None
                state.feature = None
                state.branch = None
                state.worktree = None
                state.acceptance_sha256 = None
                state.evidence = []
                state.blocker = None
                state.phase = "merged"
                self.store.save(state)
                return
            result = reconcile_merge(main_sha, state.base_sha, state.candidate_sha)
            if result == "already_merged" and state.feature:
                state.completed.setdefault(state.feature, state.candidate_sha)
                state.phase = "merged"
                self.store.save(state)
        elif state.base_sha and git_sha(self.repo, "main") != state.base_sha:
            raise AutopilotError("main moved while an unfinished feature was recorded")
        self.store.save(state)

    def _resume_merged_candidate(self, state: RuntimeState) -> None:
        feature_id = state.feature
        candidate_sha = state.candidate_sha
        base_sha = state.base_sha
        branch = state.branch
        if not feature_id or not candidate_sha or not base_sha or not branch:
            raise AutopilotError("recovery-needed: merged runtime candidate is incomplete")
        feature = self.policy.feature(feature_id)
        evidence = [GateEvidence(**item) for item in state.evidence]
        report_dir = self.runtime_root / "reports" / feature_id
        review_file = report_dir / f"review-{state.repair_cycle}.json"
        try:
            review = json.loads(review_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AutopilotError("recovery-needed: merged review evidence is unavailable") from exc
        promote_fast_forward(
            self.repo,
            base_sha=base_sha,
            candidate_sha=candidate_sha,
            branch=branch,
            evidence=evidence,
            review=review,
            required_gate_ids=[item["id"] for item in self.policy.raw["gate_commands"]],
            controller_version=CONTROLLER_VERSION,
            policy_digest=self.policy.digest,
            review_file=review_file,
            review_sha256=hashlib.sha256(review_file.read_bytes()).hexdigest(),
        )
        self._persist_verified_completion(
            state, feature_id, feature, candidate_sha, evidence, review_file
        )
        state.completed[feature_id] = candidate_sha
        state.base_sha = None
        state.candidate_sha = None
        state.feature = None
        state.branch = None
        state.worktree = None
        state.acceptance_sha256 = None
        state.evidence = []
        state.blocker = None
        state.phase = "merged"
        self.store.save(state)

    def _validate_tracked_evidence(
        self, feature_id: str, candidate_sha: str, record: dict[str, Any]
    ) -> None:
        evidence_paths = record.get("evidence")
        if not isinstance(evidence_paths, list) or not evidence_paths:
            raise AutopilotError(f"recovery-needed: verified {feature_id} has no evidence paths")
        for raw_path in evidence_paths:
            relative = _normalized_repo_path(str(raw_path))
            report = (self.repo / relative).resolve()
            if self.repo not in report.parents or not report.is_file():
                raise AutopilotError(f"recovery-needed: evidence for {feature_id} is missing")
            try:
                document = json.loads(report.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise AutopilotError(
                    f"recovery-needed: evidence for {feature_id} is malformed"
                ) from exc
            if (
                not isinstance(document, dict)
                or document.get("candidate_sha") != candidate_sha
                or document.get("result") != "passed"
            ):
                raise AutopilotError(
                    f"recovery-needed: evidence for {feature_id} is wrong-SHA or failed"
                )

    def _run_feature(self, state: RuntimeState, feature_id: str) -> None:
        feature = self.policy.feature(feature_id)
        completed = BASELINE_COMPLETE | set(state.completed)
        missing = set(feature["dependencies"]) - completed
        if missing:
            raise AutopilotError(f"{feature_id} dependencies are incomplete: {sorted(missing)}")
        if run_git(self.repo, "symbolic-ref", "--short", "HEAD") != "main":
            raise AutopilotError("integration worktree must be on main")
        if run_git(self.repo, "status", "--porcelain"):
            raise AutopilotError("main has user or unrelated changes")
        resuming = state.feature == feature_id and state.base_sha is not None
        if resuming:
            base_sha = state.base_sha
            branch = state.branch
            worktree = Path(state.worktree or "")
            if branch != feature["branch"] or not worktree.is_dir():
                raise AutopilotError("recorded feature worktree/branch is missing or inconsistent")
            if git_sha(self.repo, "main") != base_sha:
                raise AutopilotError("main moved before the preserved candidate could resume")
            if git_sha(worktree, branch) != git_sha(worktree, "HEAD"):
                raise AutopilotError("preserved feature branch moved away from its worktree HEAD")
            if state.acceptance_sha256 is None:
                state.acceptance_sha256 = self._recover_acceptance_contract(
                    worktree, feature, base_sha
                )
                self.store.save(state)
            self._verify_acceptance_contract(state, worktree, feature)
        else:
            base_sha = git_sha(self.repo, "main")
            branch = feature["branch"]
            worktree = self.runtime_root / "worktrees" / feature_id
            if worktree.exists():
                raise AutopilotError(f"unrecorded preserved worktree requires review: {worktree}")
            worktree.parent.mkdir(parents=True, exist_ok=True)
            run_git(self.repo, "worktree", "add", "-b", branch, str(worktree), base_sha)
            state.feature = feature_id
            state.base_sha = base_sha
            state.candidate_sha = None
            state.branch = branch
            state.worktree = str(worktree)
            state.repair_cycle = 0
            state.phase = "implementing"
            state.evidence = []
            state.acceptance_sha256 = None
            self.store.save(state)
            state.acceptance_sha256 = self._prepare_acceptance_contract(
                worktree, feature_id, feature, base_sha
            )
            self.store.save(state)
        report_dir = self.runtime_root / "reports" / feature_id
        report_dir.mkdir(parents=True, exist_ok=True)
        try:
            while state.repair_cycle <= int(self.policy.raw["max_repair_cycles"]):
                candidate_can_be_revalidated = bool(
                    state.candidate_sha
                    and state.phase in {"testing", "approved"}
                    and git_sha(worktree, "HEAD") == state.candidate_sha
                    and not run_git(worktree, "status", "--porcelain")
                )
                if not candidate_can_be_revalidated:
                    worker_output = report_dir / f"worker-{state.repair_cycle}.txt"
                    prompt = feature_prompt(feature_id, feature, base_sha)
                    if state.repair_cycle:
                        prompt += (
                            "\nRepair cycle "
                            f"{state.repair_cycle}/3. Address this controller/review blocker only: "
                            f"{state.blocker or 'previous evidence failed'}. All evidence will be "
                            "rerun for the new commit.\n"
                        )
                    worker_head = git_sha(worktree, "HEAD")
                    state.implementation_session_id = uuid.uuid4().hex
                    self.store.save(state)
                    self.codex.implement(worktree, prompt, worker_output)
                    self._verify_acceptance_contract(state, worktree, feature)
                    self._commit_candidate(
                        state,
                        worktree,
                        feature_id,
                        feature,
                        report_dir,
                        expected_worker_head=worker_head,
                    )
                candidate_sha = state.candidate_sha
                assert candidate_sha is not None
                try:
                    evidence = self._run_gates(worktree, candidate_sha, report_dir)
                    review_file = report_dir / f"review-{state.repair_cycle}.json"
                    reviewer_session_id = uuid.uuid4().hex
                    review = self.codex.review(
                        worktree,
                        review_prompt(feature_id, base_sha, candidate_sha, reviewer_session_id),
                        self.repo / "build/autopilot/review.schema.json",
                        review_file,
                        base_sha,
                    )
                    validate_review(
                        review,
                        base_sha,
                        candidate_sha,
                        expected_review_session_id=reviewer_session_id,
                        implementer_session_id=state.implementation_session_id,
                    )
                    if git_sha(worktree, "HEAD") != candidate_sha or run_git(
                        worktree, "status", "--porcelain"
                    ):
                        raise AutopilotError("candidate changed after gates/review")
                    state.evidence = [asdict(item) for item in evidence]
                    state.phase = "approved"
                    self.store.save(state)
                    review_sha256 = hashlib.sha256(review_file.read_bytes()).hexdigest()
                    promote_fast_forward(
                        self.repo,
                        base_sha=base_sha,
                        candidate_sha=candidate_sha,
                        branch=branch,
                        evidence=evidence,
                        review=review,
                        required_gate_ids=[item["id"] for item in self.policy.raw["gate_commands"]],
                        controller_version=CONTROLLER_VERSION,
                        policy_digest=self.policy.digest,
                        review_file=review_file,
                        review_sha256=review_sha256,
                    )
                    state.phase = "merged"
                    self.store.save(state)
                    self._persist_verified_completion(
                        state, feature_id, feature, candidate_sha, evidence, review_file
                    )
                    state.completed[feature_id] = candidate_sha
                    state.base_sha = None
                    state.candidate_sha = None
                    state.feature = None
                    state.branch = None
                    state.worktree = None
                    state.acceptance_sha256 = None
                    state.evidence = []
                    state.blocker = None
                    state.implementation_session_id = None
                    self.store.save(state)
                    run_git(self.repo, "worktree", "remove", str(worktree))
                    return
                except RepairableError as exc:
                    if state.repair_cycle >= int(self.policy.raw["max_repair_cycles"]):
                        raise AutopilotError(
                            f"{feature_id} exhausted three repair cycles: {exc}"
                        ) from exc
                    state.repair_cycle += 1
                    state.phase = "repairing"
                    state.blocker = redact(str(exc))
                    self.store.save(state)
        except Exception as exc:
            state.phase = "blocked"
            state.blocker = redact(str(exc))
            self.store.save(state)
            raise

    def _prepare_acceptance_contract(
        self, worktree: Path, feature_id: str, feature: dict[str, Any], base_sha: str
    ) -> str:
        relative = _normalized_repo_path(str(feature["acceptance_path"]))
        path = worktree / relative
        if path.exists():
            raise AutopilotError(f"acceptance contract already exists unexpectedly: {relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        allowed = "\n".join(f"- `{item}`" for item in feature["allowed_paths"])
        non_goals = "\n".join(f"- {item}" for item in feature["non_goals"])
        evidence = "\n".join(f"- {item}" for item in feature["evidence"])
        sources = "\n".join(f"- {item}" for item in feature.get("official_sources", []))
        content = f"""# {feature_id} Acceptance Contract

## Controller pin

- Feature: {feature_id}
- Integration base: `{base_sha}`
- Manifest dependencies: {", ".join(feature["dependencies"])}
- This contract is controller-owned. The worker may not edit it or its thresholds.

## Allowed product paths

{allowed}

## Acceptance evidence

{evidence}

## Official sources requiring dated verification

{sources}

## Non-goals

{non_goals}

## Mandatory gates

Every pinned controller gate, feature-specific evidence check, exact-SHA fresh
review, clean scope/protected/control-plane diff, unchanged remote and main
base, zero required test skips, and fast-forward-only integration must pass.
"""
        path.write_text(content, encoding="utf-8", newline="\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        run_git(worktree, "add", "--", relative)
        run_git(worktree, "commit", "-m", f"docs({feature_id}): pin acceptance contract")
        return digest

    def _verify_acceptance_contract(
        self, state: RuntimeState, worktree: Path, feature: dict[str, Any]
    ) -> None:
        path = worktree / _normalized_repo_path(str(feature["acceptance_path"]))
        if not path.is_file() or state.acceptance_sha256 is None:
            raise AutopilotError("controller-pinned acceptance contract is missing")
        if hashlib.sha256(path.read_bytes()).hexdigest() != state.acceptance_sha256:
            raise AutopilotError("controller-pinned acceptance contract was modified")

    def _recover_acceptance_contract(
        self, worktree: Path, feature: dict[str, Any], base_sha: str
    ) -> str:
        relative = _normalized_repo_path(str(feature["acceptance_path"]))
        head = git_sha(worktree, "HEAD")
        if run_git(worktree, "rev-list", "--count", f"{base_sha}..{head}") != "1":
            raise AutopilotError("cannot safely recover the acceptance-contract commit")
        if changed_paths(worktree, base_sha, head) != [relative]:
            raise AutopilotError("acceptance recovery found unexpected committed paths")
        path = worktree / relative
        if not path.is_file() or run_git(worktree, "status", "--porcelain"):
            raise AutopilotError("acceptance recovery worktree is missing or dirty")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _commit_candidate(
        self,
        state: RuntimeState,
        worktree: Path,
        feature_id: str,
        feature: dict[str, Any],
        report_dir: Path,
        *,
        expected_worker_head: str,
    ) -> None:
        base_sha = state.base_sha
        assert base_sha is not None
        if git_sha(worktree, "HEAD") != expected_worker_head:
            raise AutopilotError("worker created or moved commits; candidate history is untrusted")
        status = run_git(worktree, "status", "--porcelain")
        if not status:
            raise AutopilotError("worker produced no candidate changes")
        tracked = run_git(worktree, "diff", "--name-only", "HEAD")
        untracked = run_git(worktree, "ls-files", "--others", "--exclude-standard")
        uncommitted_paths = sorted(
            {
                _normalized_repo_path(line)
                for line in f"{tracked}\n{untracked}".splitlines()
                if line.strip()
            }
        )
        allowed = list(feature["allowed_paths"])
        for path in uncommitted_paths:
            if any(path_matches(path, rule) for rule in self.policy.control_plane):
                raise AutopilotError(f"worker attempted control-plane change: {path}")
            if any(path_matches(path, rule) for rule in self.policy.protected_paths):
                raise AutopilotError(f"worker attempted protected change: {path}")
            if not any(path_matches(path, rule) for rule in allowed):
                raise AutopilotError(f"worker attempted out-of-scope change: {path}")
        update = worktree / "build/update_state.py"
        result = subprocess.run(
            [
                sys.executable,
                str(update),
                "--feature",
                feature_id,
                "--status",
                "review",
                "--branch",
                str(feature["branch"]),
                "--started-at",
                utc_now(),
            ],
            cwd=worktree,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise AutopilotError("validated project-state helper rejected the candidate update")
        self._update_project_progress(worktree, feature_id, feature)
        allowed.extend(self.policy.raw["controller_owned_progress"])
        allowed.append(str(feature["acceptance_path"]))
        run_git(worktree, "add", "--all")
        run_git(worktree, "commit", "-m", f"feat({feature_id}): complete bounded feature")
        candidate_sha = git_sha(worktree, "HEAD")
        validate_candidate_paths(worktree, base_sha, candidate_sha, allowed, self.policy)
        state.candidate_sha = candidate_sha
        state.phase = "testing"
        state.blocker = None
        state.evidence = []
        self.store.save(state)
        atomic_write_json(
            report_dir / f"candidate-{state.repair_cycle}.json",
            {"base_sha": base_sha, "candidate_sha": candidate_sha, "paths": uncommitted_paths},
        )

    def _persist_verified_completion(
        self,
        state: RuntimeState,
        feature_id: str,
        feature: dict[str, Any],
        candidate_sha: str,
        evidence: Sequence[GateEvidence],
        review_file: Path,
    ) -> None:
        tests = {
            item.gate_id: {
                "passed": item.passed,
                "failed": item.failed,
                "skipped": item.skipped,
                "exit_code": item.exit_code,
            }
            for item in evidence
            if item.test_required
        }
        gate_manifest = self.runtime_root / "reports" / feature_id / f"gates-{candidate_sha}.json"
        completion_manifest = (
            self.runtime_root / "reports" / feature_id / f"completion-{candidate_sha}.json"
        )
        atomic_write_json(
            completion_manifest,
            {
                "base_sha": state.base_sha,
                "candidate_sha": candidate_sha,
                "result": "passed",
                "controller_version": CONTROLLER_VERSION,
                "policy_digest": self.policy.digest,
                "gates_sha256": hashlib.sha256(gate_manifest.read_bytes()).hexdigest(),
                "review_sha256": hashlib.sha256(review_file.read_bytes()).hexdigest(),
                "verified_at": utc_now(),
            },
        )
        evidence_paths = [str(completion_manifest.relative_to(self.repo)).replace("\\", "/")]
        update_state(
            self.repo / "build/state.json",
            feature=feature_id,
            status="done",
            branch=str(feature["branch"]),
            commit=candidate_sha,
            tests=tests,
            finished_at=utc_now(),
            blockers=[],
            evidence=evidence_paths,
            verified_at=utc_now(),
        )
        run_git(self.repo, "add", "--", "build/state.json")
        run_git(self.repo, "commit", "-m", f"chore: record verified {feature_id} evidence")

    def _update_project_progress(
        self, worktree: Path, feature_id: str, feature: dict[str, Any]
    ) -> None:
        path = worktree / "PROJECT_UPDATE.md"
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"\| Current feature \|.*\|",
            f"| Current feature | {feature_id} — candidate prepared by controlled pilot |",
            text,
            count=1,
        )
        text = re.sub(
            r"\| Current branch \|.*\|",
            f"| Current branch | `{feature['branch']}` |",
            text,
            count=1,
        )
        marker = f"### {datetime.now(UTC).date().isoformat()} — {feature_id} pilot candidate"
        if marker not in text:
            text += (
                f"\n{marker}\n\n"
                "- The controller prepared this bounded candidate and updated tracked state "
                "through "
                "`build/update_state.py`. Automatic integration remains conditional on every "
                "controller-defined gate and a fresh independent review for the exact final SHA; "
                "durable command/review evidence is stored under the ignored pilot runtime root.\n"
            )
        path.write_text(text, encoding="utf-8", newline="\n")

    def _run_gates(
        self, worktree: Path, candidate_sha: str, report_dir: Path
    ) -> list[GateEvidence]:
        evidence: list[GateEvidence] = []
        with DisposableServices() as env:
            for gate in self.policy.raw["gate_commands"]:
                junit_path = report_dir / f"pytest-{candidate_sha}.xml"
                base_sha = self.store.load().base_sha
                assert base_sha is not None
                argv = tuple(
                    str(part).format(
                        junit_path=str(junit_path),
                        base_sha=base_sha,
                        candidate_sha=candidate_sha,
                    )
                    for part in gate["argv"]
                )
                started_at = utc_now()
                exit_code, duration, output = self.runner.run(
                    argv,
                    cwd=worktree,
                    env=env,
                    timeout_seconds=int(
                        gate.get("timeout_seconds", self.policy.raw["command_timeout_seconds"])
                    ),
                )
                output_path = report_dir / f"gate-{gate['id']}-{candidate_sha}.log"
                output_path.write_text(output, encoding="utf-8", newline="\n")
                finished_at = utc_now()
                passed = failed = skipped = 0
                test_report_file: str | None = None
                test_report_sha256 = ""
                if gate["id"] == "pytest":
                    passed, failed, skipped = parse_junit_summary(junit_path)
                    test_report_file = str(junit_path.relative_to(self.repo))
                    test_report_sha256 = hashlib.sha256(junit_path.read_bytes()).hexdigest()
                elif gate.get("requires_tests"):
                    passed, failed, skipped = parse_test_summary(output)
                item = GateEvidence(
                    gate_id=gate["id"],
                    candidate_sha=candidate_sha,
                    argv=argv,
                    exit_code=exit_code,
                    duration_seconds=round(duration, 3),
                    passed=passed,
                    failed=failed,
                    skipped=skipped,
                    output_file=str(output_path.relative_to(self.repo)),
                    base_sha=base_sha,
                    controller_version=CONTROLLER_VERSION,
                    policy_digest=self.policy.digest,
                    started_at=started_at,
                    finished_at=finished_at,
                    output_sha256=hashlib.sha256(output_path.read_bytes()).hexdigest(),
                    test_required=bool(gate.get("requires_tests", False)),
                    test_report_file=test_report_file,
                    test_report_sha256=test_report_sha256,
                )
                evidence.append(item)
                if git_sha(worktree, "HEAD") != candidate_sha or run_git(
                    worktree, "status", "--porcelain"
                ):
                    raise AutopilotError(f"gate {gate['id']} changed the candidate")
        validate_gate_evidence(
            evidence,
            candidate_sha,
            [item["id"] for item in self.policy.raw["gate_commands"]],
            base_sha=self.store.load().base_sha,
            controller_version=CONTROLLER_VERSION,
            policy_digest=self.policy.digest,
            repo=self.repo,
        )
        base_sha = self.store.load().base_sha
        assert base_sha is not None
        feature_id = self.store.load().feature
        assert feature_id is not None
        feature_report = validate_feature_evidence(
            worktree, base_sha, candidate_sha, self.policy.feature(feature_id)
        )
        atomic_write_json(report_dir / f"feature-evidence-{candidate_sha}.json", feature_report)
        self._scan_candidate_for_secrets(worktree, candidate_sha, report_dir)
        atomic_write_json(report_dir / f"gates-{candidate_sha}.json", [asdict(x) for x in evidence])
        return evidence

    def _scan_candidate_for_secrets(
        self, worktree: Path, candidate_sha: str, report_dir: Path
    ) -> None:
        base_sha = self.store.load().base_sha
        assert base_sha is not None
        findings: list[dict[str, Any]] = []
        for path in changed_paths(worktree, base_sha, candidate_sha):
            target = worktree / path
            if not target.is_file():
                continue
            try:
                lines = target.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(lines, start=1):
                assignment = SECRET_SCAN_ASSIGNMENT_RE.search(line)
                assignment_value = assignment.group(2).strip("'\"<>{}[]()") if assignment else ""
                assignment_is_unsafe = bool(
                    assignment
                    and len(assignment_value) >= 20
                    and not SAFE_TEST_VALUE_RE.match(assignment_value)
                    and not assignment_value.startswith(("os.", "self.", "credentials.", "$"))
                )
                jwt_or_key = bool(SECRET_PATTERNS[2].search(line) or "BEGIN PRIVATE KEY" in line)
                if assignment_is_unsafe or jwt_or_key:
                    findings.append({"path": path, "line": number, "category": "secret-shaped"})
        atomic_write_json(report_dir / f"secret-scan-{candidate_sha}.json", findings)
        if findings:
            raise AutopilotError("secret-shaped values detected; see redacted secret-scan report")


def remove_runtime_worktree(repo: Path, worktree: Path) -> None:
    """Test helper: remove only a validated, repository-owned runtime worktree."""
    resolved_repo = repo.resolve()
    resolved = worktree.resolve()
    expected = (resolved_repo / ".runtime/dev-autopilot/worktrees").resolve()
    if expected not in resolved.parents:
        raise AutopilotError("refusing to remove a worktree outside the runtime worktree root")
    run_git(repo, "worktree", "remove", str(resolved))
    if resolved.exists():
        shutil.rmtree(resolved)
