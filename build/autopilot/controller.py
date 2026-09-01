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
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ALLOWLIST = ("F0.4", "F0.5", "F0.6", "F0.7", "F0.8", "F0.9")
BASELINE_COMPLETE = {"M0.3", "F0.1", "F0.2", "F0.3"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TEST_SUMMARY_RE = re.compile(
    r"(?:(?P<passed>\d+) passed)?(?:,?\s*(?P<failed>\d+) failed)?"
    r"(?:,?\s*(?P<skipped>\d+) skipped)?"
)
SECRET_PATTERNS = (
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]{8,}"),
    re.compile(
        r"(?i)(access[-_ ]?token|authorization|api[-_ ]?secret|password|totp|pin)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(r"\beyJ[a-zA-Z0-9_-]{12,}\.[a-zA-Z0-9_-]{8,}(?:\.[a-zA-Z0-9_-]+)?\b"),
)
SECRET_SCAN_ASSIGNMENT_RE = re.compile(
    r"(?i)(access[-_ ]?token|authorization|api[-_ ]?secret|password|totp|pin)"
    r"\s*[:=]\s*['\"]?([^'\"\s,;]+)"
)
SAFE_TEST_VALUE_RE = re.compile(r"(?i)^(fake|test|dummy|example|placeholder|changeme|redacted)")


class AutopilotError(RuntimeError):
    """A fail-closed pilot blocker."""


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


@dataclass
class RuntimeState:
    version: int = 1
    phase: str = "idle"
    setup_sha: str | None = None
    remote_fingerprint: str | None = None
    feature: str | None = None
    base_sha: str | None = None
    candidate_sha: str | None = None
    branch: str | None = None
    worktree: str | None = None
    repair_cycle: int = 0
    completed: dict[str, str] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    active_pid: int | None = None
    blocker: str | None = None
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
        return RuntimeState(**raw)

    def save(self, state: RuntimeState) -> None:
        state.updated_at = utc_now()
        atomic_write_json(self.path, asdict(state))


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
        if not isinstance(raw, dict) or raw.get("version") != 1:
            raise AutopilotError("policy must be a version-1 mapping")
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


def validate_review(document: Any, base_sha: str, candidate_sha: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise AutopilotError("review output is missing or not a JSON object")
    required = {"base_sha", "candidate_sha", "verdict", "findings", "evidence_checked"}
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
    if document["verdict"] != "safe_to_merge" or any(item["blocking"] for item in findings):
        raise AutopilotError("independent review contains a blocking result")
    return document


def parse_pytest_summary(output: str) -> tuple[int, int, int]:
    passed = failed = skipped = 0
    for match in TEST_SUMMARY_RE.finditer(output):
        values = tuple(int(match.group(name) or 0) for name in ("passed", "failed", "skipped"))
        if sum(values) > sum((passed, failed, skipped)):
            passed, failed, skipped = values
    return passed, failed, skipped


def validate_gate_evidence(
    evidence: Sequence[GateEvidence],
    candidate_sha: str,
    required_gate_ids: Sequence[str] | None = None,
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
        if item.exit_code != 0 or item.failed:
            raise AutopilotError(f"gate {item.gate_id} failed")
        if item.gate_id == "pytest" and item.skipped:
            raise AutopilotError("required pytest run contains skipped tests")
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
) -> str:
    validate_gate_evidence(evidence, candidate_sha, required_gate_ids)
    validate_review(review, base_sha, candidate_sha)
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
            "-o",
            str(output),
            "-C",
            str(worktree),
            "-",
        ]
        self._validate_argv(argv)
        return self._invoke(argv, worktree, prompt)

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
            "review",
            "--base",
            base_sha,
            "-c",
            'sandbox_mode="read-only"',
            "--ephemeral",
            "--output-schema",
            str(schema),
            "--json",
            "-o",
            str(output),
            "-",
        ]
        self._validate_argv(argv)
        self._invoke(argv, worktree, prompt)
        try:
            document = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AutopilotError("review output is missing or malformed") from exc
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
Read AGENTS.md and the repository source-of-truth documents first. Write the
feature acceptance contract before code. Do not access any unrelated project.

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


def review_prompt(feature_id: str, base_sha: str, candidate_sha: str) -> str:
    return f"""Independently review ShreeNexa {feature_id}. Base SHA is
{base_sha}; exact candidate SHA is {candidate_sha}. Remain read-only. Verify
scope, acceptance behavior, tests, secrets, path safety, determinism,
migrations, service isolation, control-plane/protected paths, and truthful
evidence. Any unresolved finding is blocking regardless of severity. Return
only the required JSON shape bound to those exact SHAs. Never use credentials,
make external writes, or accept the implementer's summary as evidence.
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
                self._run_feature(state, feature_id)

    def _verify_setup_pin(self, state: RuntimeState) -> None:
        if state.setup_sha is None:
            state.setup_sha = git_sha(self.repo, "main")
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
        if state.base_sha and state.candidate_sha:
            result = reconcile_merge(
                git_sha(self.repo, "main"), state.base_sha, state.candidate_sha
            )
            if result == "already_merged" and state.feature:
                state.completed.setdefault(state.feature, state.candidate_sha)
                state.phase = "merged"
                self.store.save(state)
        elif state.base_sha and git_sha(self.repo, "main") != state.base_sha:
            raise AutopilotError("main moved while an unfinished feature was recorded")

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
                    self.codex.implement(worktree, prompt, worker_output)
                    self._commit_candidate(state, worktree, feature_id, feature, report_dir)
                candidate_sha = state.candidate_sha
                assert candidate_sha is not None
                try:
                    evidence = self._run_gates(worktree, candidate_sha, report_dir)
                    review_file = report_dir / f"review-{state.repair_cycle}.json"
                    review = self.codex.review(
                        worktree,
                        review_prompt(feature_id, base_sha, candidate_sha),
                        self.repo / "build/autopilot/review.schema.json",
                        review_file,
                        base_sha,
                    )
                    validate_review(review, base_sha, candidate_sha)
                    if git_sha(worktree, "HEAD") != candidate_sha or run_git(
                        worktree, "status", "--porcelain"
                    ):
                        raise AutopilotError("candidate changed after gates/review")
                    state.evidence = [asdict(item) for item in evidence]
                    state.phase = "approved"
                    self.store.save(state)
                    promote_fast_forward(
                        self.repo,
                        base_sha=base_sha,
                        candidate_sha=candidate_sha,
                        branch=branch,
                        evidence=evidence,
                        review=review,
                        required_gate_ids=[item["id"] for item in self.policy.raw["gate_commands"]],
                    )
                    state.completed[feature_id] = candidate_sha
                    state.phase = "merged"
                    self.store.save(state)
                    run_git(self.repo, "worktree", "remove", str(worktree))
                    return
                except AutopilotError as exc:
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

    def _commit_candidate(
        self,
        state: RuntimeState,
        worktree: Path,
        feature_id: str,
        feature: dict[str, Any],
        report_dir: Path,
    ) -> None:
        base_sha = state.base_sha
        assert base_sha is not None
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
                "done",
                "--branch",
                str(feature["branch"]),
                "--started-at",
                utc_now(),
                "--finished-at",
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
                exit_code, duration, output = self.runner.run(
                    argv,
                    cwd=worktree,
                    env=env,
                    timeout_seconds=int(
                        gate.get("timeout_seconds", self.policy.raw["command_timeout_seconds"])
                    ),
                )
                output_path = report_dir / f"gate-{gate['id']}-{candidate_sha}.log"
                output_path.write_text(output, encoding="utf-8")
                passed = failed = skipped = 0
                if gate["id"] == "pytest":
                    passed, failed, skipped = parse_pytest_summary(output)
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
        )
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
