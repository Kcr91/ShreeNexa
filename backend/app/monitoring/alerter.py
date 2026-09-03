"""Actionable alert engine with deduplication and recovery notices (F13.5)."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from app.monitoring.models import (
    AlertRecord,
    AlertSeverity,
    AlertState,
    HealthStatus,
    SubsystemHealth,
    SubsystemKind,
)

REMEDIATION_GUIDES: dict[SubsystemKind, str] = {
    SubsystemKind.UPTIME: (
        "Inspect systemctl status for the failed service; check Docker container logs "
        "and restart the supervisor."
    ),
    SubsystemKind.FEED_FRESHNESS: (
        "Check Dhan market feed WebSocket connection, verify feedd service health, "
        "and inspect network egress."
    ),
    SubsystemKind.DISK_SPACE: (
        "Prune temporary logs or run backup retention pruning; expand volume storage if needed."
    ),
    SubsystemKind.TOKEN_EXPIRY: (
        "Renew Dhan broker token immediately using DPAPI CLI: "
        "`uv run python -m app.dhan.token_cli renew`."
    ),
    SubsystemKind.QUEUE_DEPTH: (
        "Inspect worker consumer rates, check Redis memory saturation, "
        "and resolve downstream ingestion bottlenecks."
    ),
    SubsystemKind.ENGINE_HEALTH: (
        "Inspect shreenexa-engine journalctl logs for unhandled exceptions or event loop stalls."
    ),
    SubsystemKind.BACKUP_STATUS: (
        "Execute manual backup snapshot via `/opt/shreenexa/infra/lightsail/backup.sh` "
        "and inspect pg_dump outputs."
    ),
    SubsystemKind.DATA_GAP: (
        "Trigger the warehouse backfill worker to fetch and interpolate missing minute bars."
    ),
}


class AlertManager:
    """Manages alert lifecycle, deduplication, and resolution notices."""

    def __init__(self) -> None:
        self._active_alerts: dict[SubsystemKind, AlertRecord] = {}
        self._history: list[AlertRecord] = []
        self._notifications: list[dict[str, str]] = []

    @property
    def active_alerts(self) -> dict[SubsystemKind, AlertRecord]:
        return dict(self._active_alerts)

    @property
    def history(self) -> list[AlertRecord]:
        return list(self._history)

    @property
    def notifications(self) -> list[dict[str, str]]:
        return list(self._notifications)

    def process_subsystem_health(
        self,
        health: SubsystemHealth,
    ) -> tuple[AlertRecord | None, AlertRecord | None]:
        """Evaluate subsystem health and manage alert lifecycle.

        Returns (new_alert, recovery_notice).
        """
        subsystem = health.subsystem
        now = datetime.now(tz=UTC)
        remediation = REMEDIATION_GUIDES.get(subsystem, "Investigate service logs.")

        if health.status in (HealthStatus.DEGRADED, HealthStatus.CRITICAL):
            severity = (
                AlertSeverity.CRITICAL
                if health.status == HealthStatus.CRITICAL
                else AlertSeverity.WARNING
            )

            # Deduplication: If already firing for this subsystem, do not create duplicate alert
            if subsystem in self._active_alerts:
                existing = self._active_alerts[subsystem]
                is_escalation = (
                    existing.severity != AlertSeverity.CRITICAL
                    and severity == AlertSeverity.CRITICAL
                )
                if is_escalation:
                    existing.severity = AlertSeverity.CRITICAL
                    existing.message = health.message
                    existing.metrics = health.metrics
                return None, None

            # Fire new alert
            alert = AlertRecord(
                alert_id=f"alert_{subsystem.lower()}_{secrets.token_hex(4)}",
                subsystem=subsystem,
                severity=severity,
                state=AlertState.FIRING,
                title=f"[{severity}] {subsystem.replace('_', ' ').title()} Issue",
                message=health.message,
                remediation=remediation,
                metrics=health.metrics,
                fired_at=now,
            )
            self._active_alerts[subsystem] = alert
            self._history.append(alert)
            self._notifications.append({
                "type": "ALERT_FIRED",
                "alert_id": alert.alert_id,
                "title": alert.title,
                "message": alert.message,
                "remediation": alert.remediation,
            })
            return alert, None

        if health.status == HealthStatus.HEALTHY:
            # Recovery notice: If an alert was active, resolve it
            if subsystem in self._active_alerts:
                active = self._active_alerts.pop(subsystem)
                active.state = AlertState.RESOLVED
                active.resolved_at = now
                self._notifications.append({
                    "type": "ALERT_RESOLVED",
                    "alert_id": active.alert_id,
                    "title": f"[RESOLVED] {subsystem.replace('_', ' ').title()} Recovered",
                    "message": f"{subsystem} returned to healthy status: {health.message}",
                })
                return None, active

        return None, None

    def acknowledge_alert(self, alert_id: str, operator_username: str) -> AlertRecord:
        """Acknowledge an active alert."""
        for alert in self._active_alerts.values():
            if alert.alert_id == alert_id:
                alert.state = AlertState.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(tz=UTC)
                alert.acknowledged_by = operator_username
                return alert
        raise KeyError(f"Active alert {alert_id} not found")
