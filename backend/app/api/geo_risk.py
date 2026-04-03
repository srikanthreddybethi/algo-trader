"""Geo Risk API — geopolitical risk scores, events, heatmap, alerts, and analytics."""
from dataclasses import asdict
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

from app.services.geo_risk.monitor import geo_monitor
from app.services.geo_risk.impact_matrix import IMPACT_MATRIX, get_all_event_types, update_impact

router = APIRouter(prefix="/api/v1/geo-risk", tags=["geo-risk"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _event_to_dict(event) -> dict:
    """Convert a GeoEvent dataclass to a JSON-safe dict."""
    d = asdict(event)
    if d.get("timestamp"):
        d["timestamp"] = d["timestamp"].isoformat()
    return d


def _score_to_dict(score) -> dict:
    """Convert an AssetRiskScore dataclass to a JSON-safe dict."""
    return asdict(score)


def _alert_to_dict(alert) -> dict:
    d = asdict(alert)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("last_triggered"):
        d["last_triggered"] = d["last_triggered"].isoformat()
    return d


def _heatmap_to_dict(region) -> dict:
    return asdict(region)


# ── Score Endpoints ──────────────────────────────────────────────────────────

@router.get("/score/{asset_symbol}")
async def get_score(
    asset_symbol: str,
    asset_class: str = Query("crypto", description="Asset class: crypto, equities, forex, commodities"),
):
    """Get current geo risk score for a single asset."""
    score = geo_monitor.score_asset(asset_symbol, asset_class)
    return _score_to_dict(score)


@router.get("/scores")
async def get_all_scores(
    asset_class: str = Query("crypto", description="Asset class to score"),
):
    """Get geo risk scores for common assets in an asset class."""
    default_assets = {
        "crypto": {"BTC/USDT": "crypto", "ETH/USDT": "crypto", "SOL/USDT": "crypto"},
        "equities": {"AAPL": "equities", "MSFT": "equities", "GOOGL": "equities", "AMZN": "equities"},
        "forex": {"EUR/USD": "forex", "GBP/USD": "forex", "USD/JPY": "forex"},
        "commodities": {"GOLD": "commodities", "OIL": "commodities", "SILVER": "commodities"},
    }
    assets = default_assets.get(asset_class, {"BTC/USDT": asset_class})
    scores = geo_monitor.score_all_assets(assets)
    return {symbol: _score_to_dict(s) for symbol, s in scores.items()}


# ── Event Endpoints ──────────────────────────────────────────────────────────

@router.get("/events")
async def list_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    region: Optional[str] = Query(None, description="Filter by region"),
    limit: int = Query(50, ge=1, le=200),
):
    """List active geopolitical events."""
    events = geo_monitor.get_active_events(event_type=event_type, region=region, limit=limit)
    return [_event_to_dict(e) for e in events]


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get detailed view of a single event."""
    event = geo_monitor.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    # Include per-asset-class impact breakdown
    impact_breakdown = {}
    for ac in ["equities", "crypto", "commodities", "forex"]:
        result = geo_monitor.scorer.impact_scorer.score_event(event, ac)
        impact_breakdown[ac] = result
    d = _event_to_dict(event)
    d["impact_breakdown"] = impact_breakdown
    return d


# ── Timeline & Heatmap ───────────────────────────────────────────────────────

@router.get("/timeline")
async def get_timeline(
    asset_class: str = Query("equities", description="Asset class for timeline"),
    hours: int = Query(168, ge=1, le=720, description="Hours of history"),
):
    """Risk score timeline bucketed by hour."""
    return geo_monitor.get_risk_timeline(asset_class=asset_class, hours=hours)


@router.get("/heatmap")
async def get_heatmap():
    """Geographic risk heatmap data."""
    regions = geo_monitor.get_heatmap()
    return [_heatmap_to_dict(r) for r in regions]


# ── Manual Evaluation ────────────────────────────────────────────────────────

@router.post("/evaluate")
async def evaluate_event(body: dict):
    """
    Manually submit an event description for classification and scoring.

    Body: {"title": "...", "description": "...", "source": "manual"}
    """
    title = body.get("title", "")
    description = body.get("description", "")
    source = body.get("source", "manual")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    event = geo_monitor.evaluate_event(title, description, source)
    if not event:
        return {"classified": False, "message": "Could not classify event — no matching patterns"}
    return {"classified": True, "event": _event_to_dict(event)}


# ── Impact Matrix ────────────────────────────────────────────────────────────

@router.get("/impact-matrix")
async def get_impact_matrix():
    """View the full impact matrix."""
    return {
        "event_types": get_all_event_types(),
        "matrix": IMPACT_MATRIX,
    }


@router.put("/impact-matrix")
async def update_impact_matrix(body: dict):
    """
    Update impact matrix weights at runtime.

    Body: {"event_type": "SANCTIONS", "asset_class": "crypto", "updates": {"magnitude": 0.6}}
    """
    event_type = body.get("event_type")
    asset_class = body.get("asset_class")
    updates = body.get("updates", {})
    if not event_type or not asset_class or not updates:
        raise HTTPException(status_code=400, detail="event_type, asset_class, and updates required")
    success = update_impact(event_type, asset_class, updates)
    if not success:
        raise HTTPException(status_code=404, detail=f"Unknown event type: {event_type}")
    return {"updated": True, "event_type": event_type, "asset_class": asset_class}


# ── Alerts ───────────────────────────────────────────────────────────────────

@router.get("/alerts")
async def get_alerts():
    """Get configured alerts."""
    return [_alert_to_dict(a) for a in geo_monitor.get_alerts()]


@router.post("/alerts")
async def create_alert(body: dict):
    """
    Create a new geo risk alert.

    Body: {"asset_class": "crypto", "event_types": ["SANCTIONS"], "threshold": 0.7, "description": "..."}
    """
    alert = geo_monitor.create_alert(
        asset_class=body.get("asset_class"),
        event_types=body.get("event_types"),
        threshold=body.get("threshold", 0.7),
        description=body.get("description", ""),
    )
    return _alert_to_dict(alert)


# ── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics():
    """Analytics and status data for the geo risk module."""
    return geo_monitor.get_analytics()


# ── Status (internal) ────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    """Internal status of the GeoMonitor service."""
    return geo_monitor.get_status()
