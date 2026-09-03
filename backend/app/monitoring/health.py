"""Subsystem health evaluators for the 8 core operational domains (F13.5)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.monitoring.models import (
    HealthStatus,
    SubsystemHealth,
    SubsystemKind,
)


def check_uptime(
    services_status: dict[str, bool],
    *,
    checked_at: datetime | None = None,
) -> SubsystemHealth:
    """Evaluate process and container uptime across independent roles."""
    now = checked_at or datetime.now(tz=UTC)
    down_services = [svc for svc, up in services_status.items() if not up]

    if not down_services:
        return SubsystemHealth(
            subsystem=SubsystemKind.UPTIME,
            status=HealthStatus.HEALTHY,
            message="All supervised processes are healthy and running.",
            metrics={"services": services_status, "down_count": 0},
            checked_at=now,
        )

    # Critical processes failing causes CRITICAL status
    critical_svcs = {"api", "engine", "postgres"}
    has_critical_failure = any(s in critical_svcs for s in down_services)
    status = HealthStatus.CRITICAL if has_critical_failure else HealthStatus.DEGRADED

    return SubsystemHealth(
        subsystem=SubsystemKind.UPTIME,
        status=status,
        message=f"Process downtime detected: {', '.join(down_services)} is down.",
        metrics={"services": services_status, "down_services": down_services},
        checked_at=now,
    )


def check_feed_freshness(
    time_since_last_packet_sec: float,
    *,
    warning_sec: float = 2.0,
    critical_sec: float = 5.0,
    checked_at: datetime | None = None,
) -> SubsystemHealth:
    """Evaluate market feed freshness.

    Invariant: A stale feed cannot look healthy.
    """
    now = checked_at or datetime.now(tz=UTC)
    metrics = {"packet_age_sec": round(time_since_last_packet_sec, 3)}

    if time_since_last_packet_sec >= critical_sec:
        return SubsystemHealth(
            subsystem=SubsystemKind.FEED_FRESHNESS,
            status=HealthStatus.CRITICAL,
            message=(
                f"Market feed halted: no packets received for {time_since_last_packet_sec:.1f}s "
                f"(threshold {critical_sec}s)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    if time_since_last_packet_sec >= warning_sec:
        return SubsystemHealth(
            subsystem=SubsystemKind.FEED_FRESHNESS,
            status=HealthStatus.DEGRADED,
            message=(
                f"Market feed stale: packet latency elevated at {time_since_last_packet_sec:.1f}s "
                f"(threshold {warning_sec}s)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    return SubsystemHealth(
        subsystem=SubsystemKind.FEED_FRESHNESS,
        status=HealthStatus.HEALTHY,
        message=f"Market feed is active and healthy (latency {time_since_last_packet_sec:.2f}s).",
        metrics=metrics,
        checked_at=now,
    )


def check_disk_space(
    free_percent: float,
    *,
    warning_percent: float = 15.0,
    critical_percent: float = 5.0,
    checked_at: datetime | None = None,
) -> SubsystemHealth:
    """Evaluate local disk capacity on the runtime host."""
    now = checked_at or datetime.now(tz=UTC)
    metrics = {"free_percent": round(free_percent, 1)}

    if free_percent <= critical_percent:
        return SubsystemHealth(
            subsystem=SubsystemKind.DISK_SPACE,
            status=HealthStatus.CRITICAL,
            message=(
                f"Critical disk exhaustion: only {free_percent:.1f}% disk space remaining "
                f"(threshold <= {critical_percent}%)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    if free_percent <= warning_percent:
        return SubsystemHealth(
            subsystem=SubsystemKind.DISK_SPACE,
            status=HealthStatus.DEGRADED,
            message=(
                f"Low disk warning: {free_percent:.1f}% disk space remaining "
                f"(threshold <= {warning_percent}%)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    return SubsystemHealth(
        subsystem=SubsystemKind.DISK_SPACE,
        status=HealthStatus.HEALTHY,
        message=f"Disk space is ample ({free_percent:.1f}% free).",
        metrics=metrics,
        checked_at=now,
    )


def check_token_expiry(
    hours_remaining: float,
    *,
    warning_hours: float = 24.0,
    critical_hours: float = 2.0,
    checked_at: datetime | None = None,
) -> SubsystemHealth:
    """Evaluate broker access token validity and remaining lifespan."""
    now = checked_at or datetime.now(tz=UTC)
    metrics = {"hours_remaining": round(hours_remaining, 2)}

    if hours_remaining <= critical_hours:
        return SubsystemHealth(
            subsystem=SubsystemKind.TOKEN_EXPIRY,
            status=HealthStatus.CRITICAL,
            message=(
                f"Broker token nearing immediate expiry: {hours_remaining:.1f}h remaining "
                f"(threshold <= {critical_hours}h)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    if hours_remaining <= warning_hours:
        return SubsystemHealth(
            subsystem=SubsystemKind.TOKEN_EXPIRY,
            status=HealthStatus.DEGRADED,
            message=(
                f"Broker token renewal needed: {hours_remaining:.1f}h remaining "
                f"(threshold <= {warning_hours}h)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    return SubsystemHealth(
        subsystem=SubsystemKind.TOKEN_EXPIRY,
        status=HealthStatus.HEALTHY,
        message=f"Broker token is valid ({hours_remaining:.1f}h remaining).",
        metrics=metrics,
        checked_at=now,
    )


def check_queue_depth(
    queue_length: int,
    *,
    warning_len: int = 5000,
    critical_len: int = 20000,
    checked_at: datetime | None = None,
) -> SubsystemHealth:
    """Evaluate ingestion and fanout buffer congestion."""
    now = checked_at or datetime.now(tz=UTC)
    metrics = {"queue_length": queue_length}

    if queue_length >= critical_len:
        return SubsystemHealth(
            subsystem=SubsystemKind.QUEUE_DEPTH,
            status=HealthStatus.CRITICAL,
            message=(
                f"Severe queue backpressure: {queue_length} pending messages "
                f"(threshold >= {critical_len})."
            ),
            metrics=metrics,
            checked_at=now,
        )

    if queue_length >= warning_len:
        return SubsystemHealth(
            subsystem=SubsystemKind.QUEUE_DEPTH,
            status=HealthStatus.DEGRADED,
            message=(
                f"Elevated queue depth: {queue_length} pending messages "
                f"(threshold >= {warning_len})."
            ),
            metrics=metrics,
            checked_at=now,
        )

    return SubsystemHealth(
        subsystem=SubsystemKind.QUEUE_DEPTH,
        status=HealthStatus.HEALTHY,
        message=f"Queue backlog is nominal ({queue_length} messages).",
        metrics=metrics,
        checked_at=now,
    )


def check_engine_health(
    heartbeat_age_sec: float,
    *,
    unhandled_exceptions: int = 0,
    warning_sec: float = 5.0,
    critical_sec: float = 15.0,
    checked_at: datetime | None = None,
) -> SubsystemHealth:
    """Evaluate trading engine event loop heartbeat and error rates."""
    now = checked_at or datetime.now(tz=UTC)
    metrics = {
        "heartbeat_age_sec": round(heartbeat_age_sec, 2),
        "unhandled_exceptions": unhandled_exceptions,
    }

    if unhandled_exceptions > 0:
        return SubsystemHealth(
            subsystem=SubsystemKind.ENGINE_HEALTH,
            status=HealthStatus.CRITICAL,
            message=f"Trading engine encountered {unhandled_exceptions} unhandled exceptions.",
            metrics=metrics,
            checked_at=now,
        )

    if heartbeat_age_sec >= critical_sec:
        return SubsystemHealth(
            subsystem=SubsystemKind.ENGINE_HEALTH,
            status=HealthStatus.CRITICAL,
            message=(
                f"Trading engine heartbeat stalled: {heartbeat_age_sec:.1f}s without pulse "
                f"(threshold >= {critical_sec}s)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    if heartbeat_age_sec >= warning_sec:
        return SubsystemHealth(
            subsystem=SubsystemKind.ENGINE_HEALTH,
            status=HealthStatus.DEGRADED,
            message=(
                f"Trading engine heartbeat delayed: {heartbeat_age_sec:.1f}s "
                f"(threshold >= {warning_sec}s)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    return SubsystemHealth(
        subsystem=SubsystemKind.ENGINE_HEALTH,
        status=HealthStatus.HEALTHY,
        message=f"Trading engine is responsive (heartbeat age {heartbeat_age_sec:.2f}s).",
        metrics=metrics,
        checked_at=now,
    )


def check_backup_status(
    hours_since_backup: float,
    *,
    last_backup_success: bool = True,
    warning_hours: float = 26.0,
    checked_at: datetime | None = None,
) -> SubsystemHealth:
    """Evaluate timeliness and success of nightly backup snapshots."""
    now = checked_at or datetime.now(tz=UTC)
    metrics = {
        "hours_since_backup": round(hours_since_backup, 2),
        "last_backup_success": last_backup_success,
    }

    if not last_backup_success:
        return SubsystemHealth(
            subsystem=SubsystemKind.BACKUP_STATUS,
            status=HealthStatus.CRITICAL,
            message="Most recent backup snapshot failed integrity or dump check.",
            metrics=metrics,
            checked_at=now,
        )

    if hours_since_backup >= warning_hours:
        return SubsystemHealth(
            subsystem=SubsystemKind.BACKUP_STATUS,
            status=HealthStatus.DEGRADED,
            message=(
                f"Nightly backup overdue: {hours_since_backup:.1f}h elapsed since last snapshot "
                f"(threshold >= {warning_hours}h)."
            ),
            metrics=metrics,
            checked_at=now,
        )

    return SubsystemHealth(
        subsystem=SubsystemKind.BACKUP_STATUS,
        status=HealthStatus.HEALTHY,
        message=f"Backups are current (last completed {hours_since_backup:.1f}h ago).",
        metrics=metrics,
        checked_at=now,
    )


def check_data_gaps(
    missing_minute_count: int,
    *,
    warning_gap: int = 1,
    critical_gap: int = 15,
    checked_at: datetime | None = None,
) -> SubsystemHealth:
    """Evaluate market hours historical bar completeness."""
    now = checked_at or datetime.now(tz=UTC)
    metrics = {"missing_minute_count": missing_minute_count}

    if missing_minute_count >= critical_gap:
        return SubsystemHealth(
            subsystem=SubsystemKind.DATA_GAP,
            status=HealthStatus.CRITICAL,
            message=(
                f"Significant market data gap detected: {missing_minute_count} missing minute bars "
                f"(threshold >= {critical_gap})."
            ),
            metrics=metrics,
            checked_at=now,
        )

    if missing_minute_count >= warning_gap:
        return SubsystemHealth(
            subsystem=SubsystemKind.DATA_GAP,
            status=HealthStatus.DEGRADED,
            message=(
                f"Minor data gap detected: {missing_minute_count} missing minute bars "
                f"(threshold >= {warning_gap})."
            ),
            metrics=metrics,
            checked_at=now,
        )

    return SubsystemHealth(
        subsystem=SubsystemKind.DATA_GAP,
        status=HealthStatus.HEALTHY,
        message="No data gaps detected in active market trading window.",
        metrics=metrics,
        checked_at=now,
    )
