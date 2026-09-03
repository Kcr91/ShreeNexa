"""REST API endpoints for feature-builder specification management (F11.1)."""

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.feature_builder.gates import (
    GateExecutionSummary,
    RetryPolicy,
    gate_harness,
)
from app.feature_builder.models import (
    FeatureRequest,
    FeatureSpec,
    FeatureSpecUpdate,
    SpecApprovalDecision,
    SpecStatus,
)
from app.feature_builder.runner import (
    CodexAuthenticationError,
    CodexQuotaExceededError,
    RunnerTaskStatus,
    TaskEventType,
    TaskJournalState,
    TaskStartRequest,
    task_runner,
)
from app.feature_builder.spec import spec_engine
from app.feature_builder.worktree import (
    WorktreeAllocation,
    WorktreeCreateRequest,
    worktree_manager,
)

router = APIRouter(prefix="/api/v1/feature-builder", tags=["feature-builder"])


@router.post("/specs", response_model=FeatureSpec)
def create_feature_spec(request: FeatureRequest) -> FeatureSpec:
    """Analyze a feature request and build a structured, editable specification."""
    try:
        return spec_engine.build_spec(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/specs", response_model=list[FeatureSpec])
def list_feature_specs(status: SpecStatus | None = None) -> list[FeatureSpec]:
    """List all created feature specifications with optional lifecycle status filter."""
    return spec_engine.list_specs(status=status)


@router.get("/specs/{spec_id}", response_model=FeatureSpec)
def get_feature_spec(spec_id: str) -> FeatureSpec:
    """Retrieve a feature specification by its unique ID."""
    spec = spec_engine.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"FeatureSpec '{spec_id}' not found")
    return spec


@router.put("/specs/{spec_id}", response_model=FeatureSpec)
def update_feature_spec(spec_id: str, updates: FeatureSpecUpdate) -> FeatureSpec:
    """Update scope, test plan, or acceptance criteria in an editable specification."""
    try:
        return spec_engine.update_spec(spec_id, updates)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"FeatureSpec '{spec_id}' not found") from None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/specs/{spec_id}/approve", response_model=FeatureSpec)
def approve_feature_spec(spec_id: str, decision: SpecApprovalDecision) -> FeatureSpec:
    """Explicitly authorize a high-risk or ambiguous specification."""
    try:
        return spec_engine.approve_spec(spec_id, decision)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"FeatureSpec '{spec_id}' not found") from None


@router.post("/specs/{spec_id}/reject", response_model=FeatureSpec)
def reject_feature_spec(spec_id: str, decision: SpecApprovalDecision) -> FeatureSpec:
    """Reject a specification."""
    try:
        return spec_engine.reject_spec(spec_id, decision)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"FeatureSpec '{spec_id}' not found") from None


# --- Worktree Management Endpoints (F11.2) ---


@router.post("/worktrees", response_model=WorktreeAllocation)
def create_worktree(request: WorktreeCreateRequest) -> WorktreeAllocation:
    """Allocate an isolated Git worktree for feature building."""
    try:
        return worktree_manager.create_worktree(
            feature_id=request.feature_id,
            branch_name=request.branch_name,
            base_commit=request.base_commit,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/worktrees", response_model=list[WorktreeAllocation])
def list_worktrees() -> list[WorktreeAllocation]:
    """List all active and tracked worktree allocations."""
    return worktree_manager.list_worktrees()


@router.get("/worktrees/{worktree_id}", response_model=WorktreeAllocation)
def get_worktree(worktree_id: str) -> WorktreeAllocation:
    """Retrieve details of a specific worktree allocation."""
    alloc = worktree_manager.get_worktree(worktree_id)
    if not alloc:
        raise HTTPException(status_code=404, detail=f"Worktree '{worktree_id}' not found")
    return alloc


@router.delete("/worktrees/{worktree_id}")
def delete_worktree(worktree_id: str) -> dict[str, Any]:
    """Prune and remove an allocated Git worktree."""
    success = worktree_manager.cleanup_worktree(worktree_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Worktree '{worktree_id}' not found")
    return {"status": "CLEANED", "worktree_id": worktree_id}


@router.post("/worktrees/reconcile")
def reconcile_worktrees() -> dict[str, Any]:
    """Reconcile active allocations and prune orphaned worktrees on disk."""
    recovered = worktree_manager.reconcile_and_recover()
    return {"status": "RECONCILED", "recovered_count": len(recovered), "recovered_paths": recovered}


# --- Task Runner Endpoints (F11.3) ---


@router.post("/tasks", response_model=TaskJournalState)
def start_task(request: TaskStartRequest) -> TaskJournalState:
    """Start a new feature building task with bounded fresh context."""
    try:
        return task_runner.start_task(request)
    except CodexAuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err)) from err
    except CodexQuotaExceededError as err:
        raise HTTPException(status_code=429, detail=str(err)) from err
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks", response_model=list[TaskJournalState])
def list_tasks(status: RunnerTaskStatus | None = None) -> list[TaskJournalState]:
    """List task runs with optional status filter."""
    return task_runner.list_tasks(status=status)


@router.get("/tasks/{task_id}", response_model=TaskJournalState)
def get_task(task_id: str) -> TaskJournalState:
    """Retrieve durable checkpoint state of a specific task."""
    state = task_runner.load_durable_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return state


@router.post("/tasks/{task_id}/progress", response_model=TaskJournalState)
def progress_task_step(task_id: str, next_step: int, details: str = "") -> TaskJournalState:
    """Advance task checkpoint step."""
    try:
        return task_runner.progress_step(task_id, next_step, details)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found") from None


@router.post("/tasks/{task_id}/interrupt", response_model=TaskJournalState)
def interrupt_task(task_id: str) -> TaskJournalState:
    """Simulate host interruption on a running task."""
    try:
        return task_runner.interrupt_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found") from None


@router.post("/tasks/{task_id}/resume", response_model=TaskJournalState)
def resume_task(task_id: str) -> TaskJournalState:
    """Resume an interrupted task strictly from durable git/state."""
    try:
        return task_runner.resume_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found") from None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/cancel", response_model=TaskJournalState)
def cancel_task(task_id: str) -> TaskJournalState:
    """Cancel a running task."""
    try:
        return task_runner.cancel_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found") from None


@router.get("/tasks/{task_id}/events")
async def stream_task_events(task_id: str) -> StreamingResponse:
    """Server-Sent Events endpoint streaming structured task events in real-time."""
    q = task_runner.subscribe(task_id)

    async def event_generator() -> AsyncIterator[str]:
        try:
            while True:
                event = await q.get()
                yield f"data: {event.model_dump_json()}\n\n"
                if event.event_type in (
                    TaskEventType.TASK_COMPLETED,
                    TaskEventType.TASK_CANCELLED,
                    TaskEventType.TASK_FAILED,
                ):
                    break
        finally:
            task_runner.unsubscribe(task_id, q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- Quality Gates Endpoints (F11.4) ---


class GateEvaluateRequest(BaseModel):
    task_id: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    g1_vector: list[float] | None = None
    g1_incremental: list[float] | None = None
    g2_full: list[float | int | bool] | None = None
    g2_trunc: list[float | int | bool] | None = None
    g2_point: int | None = None
    g3_run1: dict[str, Any] | None = None
    g3_run2: dict[str, Any] | None = None
    g4_raw_output: str | None = None
    g4_exit_code: int | None = None
    g5_actual_coverage: float | None = None
    g5_required_coverage: float | None = None
    g5_component: str = "backend"


@router.post("/gates/evaluate", response_model=GateExecutionSummary)
def evaluate_gates(request: GateEvaluateRequest) -> GateExecutionSummary:
    """Evaluate G1-G6 quality gates on candidate changes and compute overall disposition."""
    g1_data = None
    if request.g1_vector is not None and request.g1_incremental is not None:
        g1_data = (request.g1_vector, request.g1_incremental)

    g2_data = None
    if (
        request.g2_full is not None
        and request.g2_trunc is not None
        and request.g2_point is not None
    ):
        g2_data = (request.g2_full, request.g2_trunc, request.g2_point)

    g3_data = None
    if request.g3_run1 is not None and request.g3_run2 is not None:
        g3_data = (request.g3_run1, request.g3_run2)

    g4_data = None
    if request.g4_raw_output is not None and request.g4_exit_code is not None:
        g4_data = (request.g4_raw_output, request.g4_exit_code)

    g5_data = None
    if request.g5_actual_coverage is not None and request.g5_required_coverage is not None:
        g5_data = (request.g5_actual_coverage, request.g5_required_coverage, request.g5_component)

    return gate_harness.evaluate_all(
        changed_files=request.changed_files,
        g1_data=g1_data,
        g2_data=g2_data,
        g3_data=g3_data,
        g4_data=g4_data,
        g5_data=g5_data,
        task_id=request.task_id,
    )


@router.post("/gates/retry")
def request_gate_retry() -> dict[str, Any]:
    """Record a retry attempt under the bounded retry policy."""
    if not gate_harness.retry_policy.can_retry():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Max retries ({gate_harness.retry_policy.max_retries}) exceeded "
                "or non-retryable violation"
            ),
        )
    delay = gate_harness.retry_policy.record_retry()
    return {
        "retry_allowed": True,
        "retry_count": gate_harness.retry_policy.retry_count,
        "max_retries": gate_harness.retry_policy.max_retries,
        "backoff_delay_seconds": delay,
    }


@router.get("/gates/policy", response_model=RetryPolicy)
def get_gate_policy() -> RetryPolicy:
    """Retrieve the current gate harness retry policy."""
    return gate_harness.retry_policy
