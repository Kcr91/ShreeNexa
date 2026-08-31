"""Schema for build/state.json — status only, no conversational history.

Field set and semantics come from SHREENEXA_CODEX_VSCODE_BUILD_PLAN.md section 10
("Progress control"). This module defines the schema and a pure validation
function; build/update_state.py is the only writer that should use it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

VALID_STATUSES = ("pending", "in_progress", "review", "done", "blocked", "parked")

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
        }


def validate_state(doc: dict) -> None:
    if not isinstance(doc, dict):
        raise StateError("state document must be a mapping")

    missing = [f for f in REQUIRED_FIELDS if f not in doc]
    if missing:
        raise StateError(f"missing required field(s): {missing}")

    extra = set(doc) - set(REQUIRED_FIELDS)
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

    for field_name in ("branch", "commit", "started_at", "finished_at"):
        if doc[field_name] is not None and not isinstance(doc[field_name], str):
            raise StateError(f"{field_name} must be a string or null")
