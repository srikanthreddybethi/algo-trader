"""Self-Optimizer API — autonomous parameter tuning and trade journal analysis."""
from fastapi import APIRouter, Query
from typing import Optional, List
from app.services.self_optimizer import (
    run_optimization,
    analyze_trade_journal,
    apply_optimization_results,
    get_optimization_history,
    get_journal_history,
)
from app.services.continuous_improver import (
    run_continuous_improvement,
    get_improvement_log,
)

router = APIRouter(prefix="/api/optimizer", tags=["optimizer"])


@router.post("/run")
async def run_optimizer(
    symbols: str = Query(default="BTC/USDT"),
    exchange: str = Query(default="binance"),
    timeframe: str = Query(default="1h"),
    days: int = Query(default=60),
):
    """
    Run full parameter optimization across all strategies.
    This tests hundreds of parameter combinations and finds the best config.
    Takes 30-60 seconds to complete.
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    result = await run_optimization(
        symbols=symbol_list,
        exchange=exchange,
        timeframe=timeframe,
        days=days,
    )
    return result


@router.post("/apply")
async def apply_optimization():
    """Apply the latest optimization results to the live orchestrator."""
    history = get_optimization_history(limit=1)
    if not history:
        return {"status": "error", "message": "No optimization results to apply. Run /optimizer/run first."}

    result = await apply_optimization_results(history[0])
    return result


@router.get("/history")
async def optimization_history(limit: int = 20):
    """Get optimization run history."""
    return get_optimization_history(limit)


@router.post("/journal")
async def run_journal_analysis(days: int = Query(default=7)):
    """
    Run AI-powered trade journal analysis.
    Reviews recent trading decisions and generates improvement recommendations.
    """
    return await analyze_trade_journal(days_back=days)


@router.get("/journal/history")
async def journal_history(limit: int = 20):
    """Get journal analysis history."""
    return get_journal_history(limit)


@router.post("/improve")
async def run_improvement(
    symbol: str = Query(default="BTC/USDT"),
    exchange: str = Query(default="binance"),
    days: int = Query(default=45),
):
    """
    Run continuous improvement: regime-specific backtesting with parameter
    mutation, blended with live performance, auto-applied to orchestrator.
    """
    return await run_continuous_improvement(symbol, exchange, days)


@router.get("/improve/history")
async def improvement_history(limit: int = 20):
    """Get continuous improvement run history."""
    return get_improvement_log(limit)


@router.post("/full-cycle")
async def run_full_optimization_cycle(
    symbols: str = Query(default="BTC/USDT"),
    exchange: str = Query(default="binance"),
    days: int = Query(default=60),
):
    """
    Run a complete autonomous optimization cycle:
    1. Grid-search parameter optimization
    2. Apply best parameters
    3. Analyze trade journal
    Returns all results in one response.
    """
    # Step 1: Optimize
    optimization = await run_optimization(
        symbols=[s.strip() for s in symbols.split(",")],
        exchange=exchange,
        days=days,
    )

    # Step 2: Apply
    applied = await apply_optimization_results(optimization)

    # Step 3: Journal analysis
    journal = await analyze_trade_journal(days_back=7)

    return {
        "status": "complete",
        "optimization": {
            "total_backtests": optimization["total_backtests"],
            "duration_seconds": optimization["duration_seconds"],
            "top_strategy": optimization["top_strategy"],
            "overall_ranking": optimization["overall_ranking"][:5],
        },
        "applied": applied,
        "journal": journal,
        "timestamp": optimization["timestamp"],
    }
