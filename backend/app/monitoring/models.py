"""Data models for system health checks, subsystem telemetry, and actionable alerts (F13.5)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    """Aggregate or subsystem operational status."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AlertSeverity(StrEnum):
    """Urgency tier of an operational alert."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertState(StrEnum):
    """Current state in the alert lifecycle."""

    FIRING = "FIRING"
    RESOLVED = "RESOLVED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class SubsystemKind(StrEnum):
    """The 8 monitored subsystems mandated by F13.5."""

    UPTIME = "UPTIME"
    FEED_FRESHNESS = "FEED_FRESHNESS"
    DISK_SPACE = "DISK_SPACE"
    TOKEN_EXPIRY = "TOKEN_EXPIRY"
    QUEUE_DEPTH = "QUEUE_DEPTH"
    ENGINE_HEALTH = "ENGINE_HEALTH"
    BACKUP_STATUS = "BACKUP_STATUS"
    DATA_GAP = "DATA_GAP"


class SubsystemHealth(BaseModel):
    """Health check outcome for a specific subsystem."""

    subsystem: SubsystemKind
    status: HealthStatus
    message: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime


class SystemHealthReport(BaseModel):
    """Composite system health evaluation across all 8 subsystems."""

    overall_status: HealthStatus
    checked_at: datetime
    subsystems: dict[SubsystemKind, SubsystemHealth] = Field(default_factory=dict)


class AlertRecord(BaseModel):
    """Actionable alert with remediation advice, deduplication, and recovery tracking."""

    alert_id: str
    subsystem: SubsystemKind
    severity: AlertSeverity
    state: AlertState
    title: str
    message: str
    remediation: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    fired_at: datetime
    resolved_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
