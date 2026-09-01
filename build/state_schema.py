"""Schema for build/state.json — status only, no conversational history.

Field set and semantics come from SHREENEXA_CODEX_VSCODE_BUILD_PLAN.md section 10
("Progress control"). This module defines the schema and a pure validation
function; build/update_state.py is the only writer that should use it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

# ``merged_unverified`` means implementation is present in main but required
# gates/review have not been established. ``blocked`` always carries a reason.
# ``done`` is reserved for verified complete records with exact-SHA evidence.
VALID_STATUSES = (
    "pending",
    "in_progress",
    "review",
    "merged_unverified",
    "done",
    "blocked",
    "parked",
)

REQUIRED_FIELDS = (
    "feature",
    "status",
    "branch",
    "commit",
    "tests",
    "started_at",
    "finished_at",
    "blockers",
)
ALLOWED_FIELDS = (*REQUIRED_FIELDS, "features")
FEATURE_RECORD_FIELDS = {
    "status",
    "branch",
    "commit",
    "tests",
    "evidence",
    "verified_at",
    "blockers",
}


class StateError(Exception):
    """Raised when a proposed build/state.json document fails validation."""


@dataclass
class State:
    feature: str
    status: str
    branch: str | None = None
    commit: str | None = None
    tests: dict = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    blockers: list[str] = field(default_factory=list)
    features: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "status": self.status,
            "branch": self.branch,
            "commit": self.commit,
            "tests": self.tests,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "blockers": self.blockers,
            "features": self.features,
        }


def _validate_evidence_path(value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise StateError("feature evidence entries must be non-empty relative paths")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise StateError("feature evidence paths must remain inside the repository/runtime root")


def _validate_feature_record(feature_id: str, record: object) -> None:
    if not isinstance(record, dict) or set(record) != FEATURE_RECORD_FIELDS:
        raise StateError(f"feature record {feature_id!r} has missing or unexpected fields")
    if record["status"] not in VALID_STATUSES:
        raise StateError(f"feature record {feature_id!r} has an invalid status")
    if not isinstance(record["tests"], dict):
        raise StateError(f"feature record {feature_id!r} tests must be a mapping")
    if not isinstance(record["evidence"], list):
        raise StateError(f"feature record {feature_id!r} evidence must be a list")
    for evidence_path in record["evidence"]:
        _validate_evidence_path(evidence_path)
    if not isinstance(record["blockers"], list) or not all(
        isinstance(item, str) and item for item in record["blockers"]
    ):
        raise StateError(f"feature record {feature_id!r} blockers must be strings")
    for field_name in ("branch", "commit", "verified_at"):
        if record[field_name] is not None and not isinstance(record[field_name], str):
            raise StateError(f"feature record {feature_id!r} {field_name} is invalid")
    if record["status"] == "done" and (
        not record["commit"]
        or not record["tests"]
        or not record["evidence"]
        or not record["verified_at"]
        or record["blockers"]
    ):
        raise StateError(
            f"feature record {feature_id!r} cannot be done without commit, tests, "
            "evidence, verified_at, and zero blockers"
        )
    if record["status"] == "blocked" and not record["blockers"]:
        raise StateError(f"feature record {feature_id!r} cannot be blocked without a reason")


def validate_state(doc: dict) -> None:
    if not isinstance(doc, dict):
        raise StateError("state document must be a mapping")

    missing = [f for f in REQUIRED_FIELDS if f not in doc]
    if missing:
        raise StateError(f"missing required field(s): {missing}")

    extra = set(doc) - set(ALLOWED_FIELDS)
    if extra:
        raise StateError(f"unexpected field(s), state.json is status-only: {sorted(extra)}")

    if not isinstance(doc["feature"], str) or not doc["feature"].strip():
        raise StateError("feature must be a non-empty string")

    if doc["status"] not in VALID_STATUSES:
        raise StateError(f"status {doc['status']!r} is not one of {VALID_STATUSES}")

    if not isinstance(doc["tests"], dict):
        raise StateError("tests must be a mapping")

    if not isinstance(doc["blockers"], list):
        raise StateError("blockers must be a list")

    features = doc.get("features", {})
    if not isinstance(features, dict):
        raise StateError("features must be a mapping")
    for feature_id, record in features.items():
        if not isinstance(feature_id, str) or not feature_id.strip():
            raise StateError("feature ledger keys must be non-empty strings")
        _validate_feature_record(feature_id, record)

    for field_name in ("branch", "commit", "started_at", "finished_at"):
        if doc[field_name] is not None and not isinstance(doc[field_name], str):
            raise StateError(f"{field_name} must be a string or null")
