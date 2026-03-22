"""Live Trading API — mode switching, safety config, trade execution."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict
from app.services.live_trading import live_bridge

router = APIRouter(prefix="/api/live", tags=["live-trading"])


class ModeSwitch(BaseModel):
    mode: str  # "paper" or "live"


class SafetyConfig(BaseModel):
    max_order_usd: Optional[float] = None
    max_daily_trades: Optional[int] = None
    max_daily_loss_usd: Optional[float] = None
    require_confirmation: Optional[bool] = None


@router.get("/status")
async def get_live_status():
    """Get current live trading bridge status."""
    return live_bridge.get_status()


@router.post("/mode")
async def set_mode(body: ModeSwitch):
    """Switch between paper and live trading mode."""
    return live_bridge.set_mode(body.mode)


@router.post("/safety-config")
async def update_safety(body: SafetyConfig):
    """Update safety configuration."""
    updates = body.model_dump(exclude_none=True)
    live_bridge.update_safety_config(updates)
    return {"status": "updated", "config": live_bridge._safety_config}


@router.get("/validate/{exchange_name}")
async def validate_exchange(exchange_name: str):
    """Validate exchange connection for live trading."""
    return await live_bridge.validate_exchange_connection(exchange_name)
