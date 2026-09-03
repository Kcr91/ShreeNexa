"""Data models for feature specifications, requests, and risk classifications (F11.1)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(StrEnum):
    """Categorization of operational, financial, or architectural risk."""

    LOW = "LOW"  # Read-only, UI widgets, mathematical analytics
    MEDIUM = "MEDIUM"  # New database tables, paper trading logic, indicators
    HIGH = "HIGH"  # Protected paths, orders, live brokers, credentials, destructive


class SpecStatus(StrEnum):
    """Lifecycle state of an implementation specification."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class FeatureRequest(BaseModel):
    """Raw or structured user feature proposal."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    title: str
    description: str
    requested_by: str = "user"
    target_manifest_id: str | None = None
    target_dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class FeatureSpec(BaseModel):
    """Structured, editable implementation specification tied to the manifest."""

    model_config = ConfigDict(frozen=True)

    spec_id: str
    feature_id: str
    title: str
    scope: list[str]
    out_of_scope: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    requires_approval: bool
    approval_reason: str | None = None
    is_ambiguous: bool = False
    ambiguity_reasons: list[str] = Field(default_factory=list)
    affected_files: list[str] = Field(default_factory=list)
    protected_paths_affected: list[str] = Field(default_factory=list)
    test_plan: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    manifest_entry: dict[str, Any] = Field(default_factory=dict)
    status: SpecStatus = SpecStatus.DRAFT
    created_at: datetime
    updated_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None


class FeatureSpecUpdate(BaseModel):
    """Editable fields for modifying an existing FeatureSpec."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    scope: list[str] | None = None
    out_of_scope: list[str] | None = None
    test_plan: list[str] | None = None
    acceptance_criteria: list[str] | None = None
    affected_files: list[str] | None = None


class SpecApprovalDecision(BaseModel):
    """User decision to approve or reject a high-risk or ambiguous specification."""

    model_config = ConfigDict(extra="ignore")

    approver: str
    comments: str = ""
