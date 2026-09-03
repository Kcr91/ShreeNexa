"""Central monitoring service coordinating all 8 health checks and alert dispatches (F13.5)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.monitoring.alerter import AlertManager
from app.monitoring.health import (
    check_backup_status,
    check_data_gaps,
    check_disk_space,
    check_engine_health,
    check_feed_freshness,
    check_queue_depth,
    check_token_expiry,
    check_uptime,
)
from app.monitoring.models import (
    HealthStatus,
    SubsystemHealth,
    SubsystemKind,
    SystemHealthReport,
)


class MonitoringService:
    """Coordinates telemetry gathering, health evaluations, and actionable alerts."""

    def __init__(self) -> None:
        self.alerter = AlertManager()
        self._subsystems: dict[SubsystemKind, SubsystemHealth] = {}
        self._last_report: SystemHealthReport | None = None

    @property
    def last_report(self) -> SystemHealthReport | None:
        return self._last_report

    def record_subsystem_health(self, health: SubsystemHealth) -> SubsystemHealth:
        """Ingest a subsystem health evaluation and trigger alert engine."""
        self._subsystems[health.subsystem] = health
        self.alerter.process_subsystem_health(health)
        return health

    def run_full_evaluation(
        self,
        *,
        services_status: dict[str, bool] | None = None,
        feed_latency_sec: float = 0.05,
        disk_free_percent: float = 45.0,
        token_hours_remaining: float = 168.0,
        queue_length: int = 0,
        engine_heartbeat_age_sec: float = 0.2,
        engine_unhandled_exceptions: int = 0,
        hours_since_backup: float = 4.0,
        last_backup_success: bool = True,
        missing_minute_count: int = 0,
        checked_at: datetime | None = None,
    ) -> SystemHealthReport:
        """Perform evaluation across all 8 subsystems."""
        now = checked_at or datetime.now(tz=UTC)
        services = services_status or {
            "api": True,
            "engine": True,
            "feedd": True,
            "worker": True,
            "redis": True,
            "postgres": True,
            "caddy": True,
        }

        # 1. Uptime
        h_uptime = check_uptime(services, checked_at=now)
        self.record_subsystem_health(h_uptime)

        # 2. Feed freshness (Invariant: Stale feed cannot look healthy)
        h_feed = check_feed_freshness(feed_latency_sec, checked_at=now)
        self.record_subsystem_health(h_feed)

        # 3. Disk space
        h_disk = check_disk_space(disk_free_percent, checked_at=now)
        self.record_subsystem_health(h_disk)

        # 4. Token expiry
        h_token = check_token_expiry(token_hours_remaining, checked_at=now)
        self.record_subsystem_health(h_token)

        # 5. Queue depth
        h_queue = check_queue_depth(queue_length, checked_at=now)
        self.record_subsystem_health(h_queue)

        # 6. Engine health
        h_engine = check_engine_health(
            engine_heartbeat_age_sec,
            unhandled_exceptions=engine_unhandled_exceptions,
            checked_at=now,
        )
        self.record_subsystem_health(h_engine)

        # 7. Backup status
        h_backup = check_backup_status(
            hours_since_backup,
            last_backup_success=last_backup_success,
            checked_at=now,
        )
        self.record_subsystem_health(h_backup)

        # 8. Data gaps
        h_gap = check_data_gaps(missing_minute_count, checked_at=now)
        self.record_subsystem_health(h_gap)

        # Compute composite status
        all_statuses = [h.status for h in self._subsystems.values()]
        if HealthStatus.CRITICAL in all_statuses:
            overall = HealthStatus.CRITICAL
        elif HealthStatus.DEGRADED in all_statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        report = SystemHealthReport(
            overall_status=overall,
            checked_at=now,
            subsystems=dict(self._subsystems),
        )
        self._last_report = report
        return report


monitoring_service = MonitoringService()
