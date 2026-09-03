"""REST API endpoints for feature-builder specification management (F11.1)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.feature_builder.models import (
    FeatureRequest,
    FeatureSpec,
    FeatureSpecUpdate,
    SpecApprovalDecision,
    SpecStatus,
)
from app.feature_builder.spec import spec_engine

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
