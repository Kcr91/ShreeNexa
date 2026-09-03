"""FastAPI routes for system health evaluation, alert queries, and acknowledgments (F13.5)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.monitoring.models import (
    AlertRecord,
    SystemHealthReport,
)
from app.monitoring.service import monitoring_service

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


class AcknowledgeAlertRequest(BaseModel):
    """Operator acknowledgment request payload."""

    operator_username: str = Field(..., min_length=1, description="Username of operator")


@router.get("/health", response_model=SystemHealthReport)
def get_system_health() -> SystemHealthReport:
    """Retrieve the latest composite system health status across all 8 subsystems."""
    report = monitoring_service.last_report
    if report is None:
        report = monitoring_service.run_full_evaluation()
    return report


@router.get("/alerts", response_model=list[AlertRecord])
def get_active_alerts() -> list[AlertRecord]:
    """Retrieve all currently active firing alerts."""
    return list(monitoring_service.alerter.active_alerts.values())


@router.get("/alerts/history", response_model=list[AlertRecord])
def get_alert_history() -> list[AlertRecord]:
    """Retrieve historical log of all alerts (firing, acknowledged, and resolved)."""
    return monitoring_service.alerter.history


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertRecord)
def acknowledge_alert(alert_id: str, req: AcknowledgeAlertRequest) -> AlertRecord:
    """Acknowledge an active alert by an operator."""
    try:
        return monitoring_service.alerter.acknowledge_alert(alert_id, req.operator_username)
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.post("/evaluate", response_model=SystemHealthReport)
def run_evaluation() -> SystemHealthReport:
    """Trigger an immediate full health evaluation cycle across all 8 subsystems."""
    return monitoring_service.run_full_evaluation()
