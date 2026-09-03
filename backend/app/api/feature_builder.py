"""REST API endpoints for feature-builder specification management (F11.1)."""

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

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
