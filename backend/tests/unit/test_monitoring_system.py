"""Unit tests for F13.5: Uptime, feed freshness, disk, token expiry, queue, engine,
backup, and data-gap monitoring with actionable alerts.

Proves:
1. Injected failures trigger one clear alert and recovery notice.
2. Alert deduplication: repeated failing cycles do not flood notifications.
3. Stale feed invariant: stale feed cannot look healthy.
4. Comprehensive health checks across all 8 operational subsystems.
5. REST API health and alert management endpoints.
"""

from __future__ import annotations

from app.main import app
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
    AlertSeverity,
    AlertState,
    HealthStatus,
    SubsystemKind,
)
from app.monitoring.service import MonitoringService, monitoring_service
from fastapi.testclient import TestClient

client = TestClient(app)


def test_injected_failure_triggers_one_clear_alert_and_recovery_notice() -> None:
    """Proof: Injected failures trigger one clear alert and recovery notice."""
    service = MonitoringService()

    # Step 1: Baseline healthy state
    rep_healthy = service.run_full_evaluation(disk_free_percent=50.0)
    assert rep_healthy.overall_status == HealthStatus.HEALTHY
    assert len(service.alerter.active_alerts) == 0
    assert len(service.alerter.notifications) == 0

    # Step 2: Inject failure: disk drops to critical 3%
    rep_fail = service.run_full_evaluation(disk_free_percent=3.0)
    assert rep_fail.overall_status == HealthStatus.CRITICAL
    assert len(service.alerter.active_alerts) == 1
    assert SubsystemKind.DISK_SPACE in service.alerter.active_alerts

    alert = service.alerter.active_alerts[SubsystemKind.DISK_SPACE]
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.state == AlertState.FIRING
    assert "Critical disk exhaustion" in alert.message
    assert "Prune temporary logs" in alert.remediation

    # Verify exactly one notification was fired
    assert len(service.alerter.notifications) == 1
    assert service.alerter.notifications[0]["type"] == "ALERT_FIRED"

    # Step 3: Deduplication proof: run another cycle with same failure
    service.run_full_evaluation(disk_free_percent=2.5)
    # Must still have only 1 notification (no duplicate spam)
    assert len(service.alerter.notifications) == 1
    assert len(service.alerter.active_alerts) == 1

    # Step 4: Inject recovery: disk freed up to 45%
    rep_recovered = service.run_full_evaluation(disk_free_percent=45.0)
    assert rep_recovered.overall_status == HealthStatus.HEALTHY
    assert len(service.alerter.active_alerts) == 0

    # Verify explicit recovery notice was dispatched
    assert len(service.alerter.notifications) == 2
    recovery_notif = service.alerter.notifications[1]
    assert recovery_notif["type"] == "ALERT_RESOLVED"
    assert recovery_notif["alert_id"] == alert.alert_id
    assert "Recovered" in recovery_notif["title"]


def test_stale_feed_cannot_look_healthy() -> None:
    """Proof: Stale feed cannot look healthy."""
    # Sub-second latency is healthy
    h_active = check_feed_freshness(0.04)
    assert h_active.status == HealthStatus.HEALTHY
    assert "Market feed is active" in h_active.message

    # Elevated latency (> 2.0s) MUST NOT be healthy
    h_stale = check_feed_freshness(2.8)
    assert h_stale.status == HealthStatus.DEGRADED
    assert "Market feed stale" in h_stale.message

    # Halted packet stream (> 5.0s) MUST be CRITICAL
    h_halted = check_feed_freshness(8.5)
    assert h_halted.status == HealthStatus.CRITICAL
    assert "Market feed halted" in h_halted.message


def test_subsystem_health_evaluators() -> None:
    """Verify health evaluations across all 8 operational domains."""
    # 1. Uptime
    up_all = {"api": True, "engine": True, "postgres": True}
    down_engine = {"api": True, "engine": False, "postgres": True}
    assert check_uptime(up_all).status == HealthStatus.HEALTHY
    assert check_uptime(down_engine).status == HealthStatus.CRITICAL

    # 2. Disk space
    assert check_disk_space(50.0).status == HealthStatus.HEALTHY
    assert check_disk_space(10.0).status == HealthStatus.DEGRADED
    assert check_disk_space(2.0).status == HealthStatus.CRITICAL

    # 3. Token expiry
    assert check_token_expiry(72.0).status == HealthStatus.HEALTHY
    assert check_token_expiry(18.0).status == HealthStatus.DEGRADED
    assert check_token_expiry(1.0).status == HealthStatus.CRITICAL

    # 4. Queue depth
    assert check_queue_depth(500).status == HealthStatus.HEALTHY
    assert check_queue_depth(8000).status == HealthStatus.DEGRADED
    assert check_queue_depth(25000).status == HealthStatus.CRITICAL

    # 5. Engine health
    assert check_engine_health(0.1, unhandled_exceptions=0).status == HealthStatus.HEALTHY
    assert check_engine_health(8.0, unhandled_exceptions=0).status == HealthStatus.DEGRADED
    assert check_engine_health(0.1, unhandled_exceptions=2).status == HealthStatus.CRITICAL

    # 6. Backup status
    assert check_backup_status(6.0, last_backup_success=True).status == HealthStatus.HEALTHY
    assert check_backup_status(30.0, last_backup_success=True).status == HealthStatus.DEGRADED
    assert check_backup_status(2.0, last_backup_success=False).status == HealthStatus.CRITICAL

    # 7. Data gaps
    assert check_data_gaps(0).status == HealthStatus.HEALTHY
    assert check_data_gaps(3).status == HealthStatus.DEGRADED
    assert check_data_gaps(20).status == HealthStatus.CRITICAL


def test_monitoring_rest_api() -> None:
    """Test REST API routes for health reports and alert acknowledgment."""
    # Evaluate system with an injected degraded queue depth
    monitoring_service.run_full_evaluation(queue_length=12000)

    # GET /api/v1/monitoring/health
    res_health = client.get("/api/v1/monitoring/health")
    assert res_health.status_code == 200
    data = res_health.json()
    assert data["overall_status"] in ("DEGRADED", "CRITICAL")
    assert "QUEUE_DEPTH" in data["subsystems"]

    # GET /api/v1/monitoring/alerts
    res_alerts = client.get("/api/v1/monitoring/alerts")
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    assert len(alerts) >= 1
    target_alert = next(a for a in alerts if a["subsystem"] == "QUEUE_DEPTH")

    # POST /api/v1/monitoring/alerts/{alert_id}/acknowledge
    res_ack = client.post(
        f"/api/v1/monitoring/alerts/{target_alert['alert_id']}/acknowledge",
        json={"operator_username": "trader_lead"},
    )
    assert res_ack.status_code == 200
    ack_data = res_ack.json()
    assert ack_data["state"] == AlertState.ACKNOWLEDGED
    assert ack_data["acknowledged_by"] == "trader_lead"


def test_monitoring_rate_limits_endpoint() -> None:
    """Test GET /api/v1/monitoring/limits exposes categories and daily budget usage."""
    res = client.get("/api/v1/monitoring/limits")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert "orders" in data["categories"]
    orders_cat = data["categories"]["orders"]
    assert orders_cat["category"] == "orders"
    assert orders_cat["limit_per_day"] == 7000
    assert orders_cat["limit_per_minute"] == 250
    assert orders_cat["limit_per_hour"] == 1000
    assert "alert_80_pct" in orders_cat
    assert "remaining_today" in orders_cat
