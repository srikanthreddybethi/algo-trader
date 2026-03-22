"""Alerts API — CRUD for price and portfolio alerts."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.core.database import get_db
from app.models.alert import Alert
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    alert_type: str
    symbol: Optional[str] = None
    exchange_name: Optional[str] = None
    threshold: float
    message: Optional[str] = None


class AlertUpdate(BaseModel):
    is_active: Optional[bool] = None
    threshold: Optional[float] = None
    message: Optional[str] = None


def _serialize(a: Alert) -> dict:
    return {
        "id": a.id,
        "alert_type": a.alert_type,
        "symbol": a.symbol,
        "exchange_name": a.exchange_name,
        "threshold": a.threshold,
        "message": a.message,
        "is_active": a.is_active,
        "is_triggered": a.is_triggered,
        "triggered_at": str(a.triggered_at) if a.triggered_at else None,
        "created_at": str(a.created_at) if a.created_at else None,
    }


@router.get("/")
async def list_alerts(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    """List all alerts."""
    q = select(Alert).order_by(Alert.created_at.desc())
    if active_only:
        q = q.where(Alert.is_active == True)
    result = await db.execute(q)
    alerts = result.scalars().all()
    return [_serialize(a) for a in alerts]


@router.post("/")
async def create_alert(body: AlertCreate, db: AsyncSession = Depends(get_db)):
    """Create a new alert."""
    alert = Alert(
        alert_type=body.alert_type,
        symbol=body.symbol,
        exchange_name=body.exchange_name,
        threshold=body.threshold,
        message=body.message,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _serialize(alert)


@router.patch("/{alert_id}")
async def update_alert(alert_id: int, body: AlertUpdate, db: AsyncSession = Depends(get_db)):
    """Update an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if body.is_active is not None:
        alert.is_active = body.is_active
    if body.threshold is not None:
        alert.threshold = body.threshold
    if body.message is not None:
        alert.message = body.message

    await db.commit()
    await db.refresh(alert)
    return _serialize(alert)


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.delete(alert)
    await db.commit()
    return {"message": "Alert deleted", "id": alert_id}


@router.post("/check")
async def check_alerts(db: AsyncSession = Depends(get_db)):
    """Check all active alerts against current prices. Returns triggered alerts."""
    from app.exchanges.manager import exchange_manager

    result = await db.execute(select(Alert).where(Alert.is_active == True, Alert.is_triggered == False))
    alerts = result.scalars().all()
    triggered = []

    for alert in alerts:
        try:
            if alert.alert_type in ("price_above", "price_below") and alert.symbol and alert.exchange_name:
                ticker = await exchange_manager.get_ticker(alert.exchange_name, alert.symbol)
                if ticker:
                    current_price = ticker.get("last_price", 0)
                    if alert.alert_type == "price_above" and current_price >= alert.threshold:
                        alert.is_triggered = True
                        alert.triggered_at = datetime.utcnow()
                        triggered.append(_serialize(alert))
                    elif alert.alert_type == "price_below" and current_price <= alert.threshold:
                        alert.is_triggered = True
                        alert.triggered_at = datetime.utcnow()
                        triggered.append(_serialize(alert))
        except Exception:
            pass

    if triggered:
        await db.commit()

    return {"triggered": triggered, "checked": len(alerts)}
