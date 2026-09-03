"""Unit and acceptance tests for Codex task runner, events, cancellation, and durable state (F11.3).

Proof requirement: Interrupt/restart resumes from git/state, not conversation history;
auth/usage errors are explicit.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from app.feature_builder.runner import (
    CodexAuthenticationError,
    CodexQuotaExceededError,
    CodexTaskRunner,
    RunnerTaskStatus,
    TaskEventType,
    TaskStartRequest,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def local_tmp_path() -> Iterator[Path]:
    """Isolated local temporary path fixture within repo build root."""
    base = Path("build/test_tmp").resolve()
    base.mkdir(parents=True, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="runner_test_", dir=base)
    p = Path(temp_dir).resolve()
    try:
        yield p
    finally:
        shutil.rmtree(p, ignore_errors=True)


def test_explicit_authentication_error(local_tmp_path: Path) -> None:
    """Proof: Missing or invalid credentials raise explicit CodexAuthenticationError."""
    runner = CodexTaskRunner(tasks_base_dir=local_tmp_path / "tasks")
    req = TaskStartRequest(
        spec_id="spec-001",
        feature_id="F12.1",
        worktree_id="wt-001",
        auth_token="invalid_key_xyz",
    )

    with pytest.raises(CodexAuthenticationError) as exc_info:
        runner.start_task(req)

    assert "Authentication failed" in str(exc_info.value)

    # Via REST API
    resp = client.post(
        "/api/v1/feature-builder/tasks",
        json=req.model_dump(),
    )
    assert resp.status_code == 401
    assert "Authentication failed" in resp.json()["detail"]


def test_explicit_quota_exceeded_error(local_tmp_path: Path) -> None:
    """Proof: Exhausted quota or rate limit raises explicit CodexQuotaExceededError."""
    runner = CodexTaskRunner(tasks_base_dir=local_tmp_path / "tasks")
    req = TaskStartRequest(
        spec_id="spec-002",
        feature_id="F12.2",
        worktree_id="wt-002",
        auth_token="quota_exhausted",
    )

    with pytest.raises(CodexQuotaExceededError) as exc_info:
        runner.start_task(req)

    assert "Quota exceeded" in str(exc_info.value)

    # Via REST API
    resp = client.post(
        "/api/v1/feature-builder/tasks",
        json=req.model_dump(),
    )
    assert resp.status_code == 429
    assert "Quota exceeded" in resp.json()["detail"]


def test_durable_state_persistence_and_progression(local_tmp_path: Path) -> None:
    """Proof: Task writes state.json to disk and progresses through checkpoint steps."""
    tasks_dir = local_tmp_path / "tasks"
    runner = CodexTaskRunner(tasks_base_dir=tasks_dir)

    req = TaskStartRequest(
        spec_id="spec-003",
        feature_id="F12.3",
        worktree_id="wt-003",
    )
    initial_state = runner.start_task(req)
    task_id = initial_state.task_id

    # Verify state.json was written to disk
    state_file = tasks_dir / task_id / "state.json"
    assert state_file.exists()

    # Progress to step 1
    prog1 = runner.progress_step(task_id, 1, details="Context assembled")
    assert prog1.current_step_index == 1
    assert prog1.steps[0].status == "COMPLETED"
    assert prog1.steps[0].details == "Context assembled"

    # Verify updated on disk
    loaded = runner.load_durable_state(task_id)
    assert loaded is not None
    assert loaded.current_step_index == 1


def test_interrupt_and_resume_from_git_and_durable_state(local_tmp_path: Path) -> None:
    """Proof: Interrupt and resume reconstructs state strictly from disk journal and git."""
    tasks_dir = local_tmp_path / "tasks"
    runner = CodexTaskRunner(tasks_base_dir=tasks_dir)

    req = TaskStartRequest(
        spec_id="spec-004",
        feature_id="F12.4",
        worktree_id="wt-004",
    )
    st = runner.start_task(req)
    task_id = st.task_id

    # Progress to step 2
    runner.progress_step(task_id, 1, details="Step 0 done")
    runner.progress_step(task_id, 2, details="Step 1 done")

    # Simulate host interruption
    interrupted = runner.interrupt_task(task_id)
    assert interrupted.status == RunnerTaskStatus.INTERRUPTED

    # Proof requirement: Wipe all in-memory cache and simulate fresh runner instance
    fresh_runner = CodexTaskRunner(tasks_base_dir=tasks_dir)
    resumed = fresh_runner.resume_task(task_id)

    # Invariants verified:
    # 1. Resumed strictly from disk journal
    # 2. Position is preserved at step 2
    # 3. Status reset to RUNNING
    # 4. Valid Git SHA checked
    assert resumed.status == RunnerTaskStatus.RUNNING
    assert resumed.current_step_index == 2
    assert resumed.git_head_sha is not None


def test_task_cancellation(local_tmp_path: Path) -> None:
    """Proof: Task cancellation halts execution and updates durable status."""
    runner = CodexTaskRunner(tasks_base_dir=local_tmp_path / "tasks")
    req = TaskStartRequest(
        spec_id="spec-005",
        feature_id="F12.5",
        worktree_id="wt-005",
    )
    st = runner.start_task(req)

    cancelled = runner.cancel_task(st.task_id)
    assert cancelled.status == RunnerTaskStatus.CANCELLED

    # Verify disk reflects cancellation
    disk_state = runner.load_durable_state(st.task_id)
    assert disk_state is not None
    assert disk_state.status == RunnerTaskStatus.CANCELLED


def test_structured_event_streaming(local_tmp_path: Path) -> None:
    """Proof: Event subscribers receive structured lifecycle events in real time."""
    runner = CodexTaskRunner(tasks_base_dir=local_tmp_path / "tasks")
    req = TaskStartRequest(
        spec_id="spec-006",
        feature_id="F12.6",
        worktree_id="wt-006",
    )

    st = runner.start_task(req)
    q = runner.subscribe(st.task_id)

    runner.progress_step(st.task_id, 1, details="Step completed")
    event = q.get_nowait()
    assert event.event_type == TaskEventType.STEP_PROGRESSED
    assert event.task_id == st.task_id
    assert event.data["step_index"] == 1


def test_task_runner_rest_api_lifecycle() -> None:
    """Proof: REST API endpoints for starting, progressing, interrupting, and resuming tasks."""
    # 1. Start task
    resp = client.post(
        "/api/v1/feature-builder/tasks",
        json={
            "spec_id": "spec-api-1",
            "feature_id": "F13.2",
            "worktree_id": "wt-api-1",
        },
    )
    assert resp.status_code == 200
    task_data = resp.json()
    task_id = task_data["task_id"]
    assert task_data["status"] == "RUNNING"

    # 2. Progress step
    prog_resp = client.post(
        f"/api/v1/feature-builder/tasks/{task_id}/progress?next_step=1&details=Done"
    )
    assert prog_resp.status_code == 200
    assert prog_resp.json()["current_step_index"] == 1

    # 3. Interrupt task
    int_resp = client.post(f"/api/v1/feature-builder/tasks/{task_id}/interrupt")
    assert int_resp.status_code == 200
    assert int_resp.json()["status"] == "INTERRUPTED"

    # 4. Resume task
    res_resp = client.post(f"/api/v1/feature-builder/tasks/{task_id}/resume")
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "RUNNING"

    # 5. Cancel task
    can_resp = client.post(f"/api/v1/feature-builder/tasks/{task_id}/cancel")
    assert can_resp.status_code == 200
    assert can_resp.json()["status"] == "CANCELLED"
