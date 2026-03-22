"""System Alerts API — failure monitoring, severity-based alerting, notification config."""
from fastapi import APIRouter, Query
from typing import Optional
from pydantic import BaseModel
from app.services.alerting import alert_manager

router = APIRouter(prefix="/api/system-alerts", tags=["system-alerts"])


class AlertConfig(BaseModel):
    webhook_url: Optional[str] = None
    email_to: Optional[str] = None


@router.get("/")
async def get_system_alerts(
    limit: int = 50,
    severity: Optional[str] = None,
    unread_only: bool = False,
):
    """Get system alerts with optional severity filter."""
    return alert_manager.get_alerts(limit=limit, severity=severity, unread_only=unread_only)


@router.get("/unread")
async def get_unread_count():
    """Get unread alert counts by severity."""
    return alert_manager.get_unread_count()


@router.get("/stats")
async def get_alert_stats():
    """Get alerting system statistics and plugin status."""
    return alert_manager.get_stats()


@router.post("/mark-read/{alert_id}")
async def mark_alert_read(alert_id: str):
    """Mark an alert as read."""
    alert_manager.mark_read(alert_id)
    return {"status": "ok"}


@router.post("/mark-all-read")
async def mark_all_read():
    """Mark all alerts as read."""
    for a in alert_manager.in_app._alerts:
        a["read"] = True
    return {"status": "ok"}


@router.delete("/clear")
async def clear_alerts(severity: Optional[str] = None):
    """Clear alerts, optionally by severity."""
    alert_manager.clear(severity)
    return {"status": "cleared"}


@router.post("/test")
async def test_alert():
    """Fire a test alert to verify all plugins are working."""
    await alert_manager.fire(
        category="startup_complete",
        message="Test alert — all notification plugins are working",
        severity="low",
    )
    return {"status": "sent", "plugins": alert_manager.get_config()}
