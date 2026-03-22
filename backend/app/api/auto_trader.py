"""Auto-Trader API — control the autonomous trading engine."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.services.orchestrator import auto_trader, get_decision_log, clear_decision_log
from app.services.intelligence import intelligence
from app.services.paper_trading import get_fee_stats
from app.services.adaptive_intelligence import adaptive

router = APIRouter(prefix="/api/auto-trader", tags=["auto-trader"])


class AutoTraderConfig(BaseModel):
    symbols: Optional[List[str]] = None
    exchange: Optional[str] = None
    interval_seconds: Optional[int] = None
    max_drawdown_pct: Optional[float] = None
    max_position_pct: Optional[float] = None
    max_total_exposure_pct: Optional[float] = None
    max_positions: Optional[int] = None
    stop_loss_pct: Optional[float] = None
    daily_loss_limit_pct: Optional[float] = None


@router.get("/status")
async def get_status():
    """Get current auto-trader status."""
    return auto_trader.get_status()


@router.post("/start")
async def start_trader():
    """Start the autonomous trading engine."""
    result = await auto_trader.start()
    return result


@router.post("/stop")
async def stop_trader():
    """Stop the autonomous trading engine."""
    result = await auto_trader.stop()
    return result


@router.post("/config")
async def update_config(config: AutoTraderConfig):
    """Update auto-trader configuration."""
    updates = config.model_dump(exclude_none=True)
    if updates:
        auto_trader.update_config(updates)
    return {"status": "updated", "config": auto_trader.config}


@router.get("/decisions")
async def get_decisions(limit: int = 50):
    """Get the decision log."""
    return get_decision_log(limit)


@router.delete("/decisions")
async def clear_decisions():
    """Clear the decision log."""
    clear_decision_log()
    return {"status": "cleared"}


@router.post("/kill-switch")
async def toggle_kill_switch(activate: bool = True):
    """Activate or deactivate the emergency kill switch."""
    if activate:
        auto_trader.risk_manager.activate_kill_switch()
        # Also stop the trader
        if auto_trader.running:
            await auto_trader.stop()
        return {"status": "kill_switch_activated", "trading_stopped": True}
    else:
        auto_trader.risk_manager.deactivate_kill_switch()
        return {"status": "kill_switch_deactivated"}


@router.get("/intelligence")
async def get_intelligence_status():
    """Get intelligence pipeline status — scoreboard, memory, all modules."""
    return intelligence.get_full_status()


@router.get("/fees")
async def get_fees():
    """Get cumulative fee and slippage statistics."""
    return get_fee_stats()


@router.get("/adaptive")
async def get_adaptive_status():
    """Get adaptive intelligence status — exit levels, AI accuracy, time profile."""
    return adaptive.get_full_status()


@router.post("/run-once")
async def run_single_cycle():
    """Run a single trading cycle manually (for testing)."""
    if auto_trader.running:
        return {"status": "error", "message": "Auto-trader is already running in loop mode"}

    try:
        await auto_trader._execute_cycle()
        return {
            "status": "cycle_complete",
            "cycle": auto_trader._cycle_count,
            "active_strategies": auto_trader._active_strategies,
            "last_analysis": auto_trader._last_analysis,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
