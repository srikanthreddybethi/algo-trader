"""Backtesting API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from app.services.backtesting import run_backtest
from app.strategies.builtin import list_strategies

router = APIRouter(prefix="/api/backtest", tags=["backtesting"])


class BacktestRequest(BaseModel):
    strategy: str
    symbol: str = "BTC/USDT"
    exchange: str = "binance"
    timeframe: str = "1h"
    days: int = 90
    initial_balance: float = 10000.0
    params: Optional[Dict] = None
    fee_rate: float = 0.001
    position_size_pct: float = 10.0


@router.get("/strategies")
async def get_strategies():
    """List all available backtesting strategies."""
    return list_strategies()


@router.post("/run")
async def run_backtest_endpoint(req: BacktestRequest):
    """Run a backtest with the specified strategy and parameters."""
    try:
        result = await run_backtest(
            strategy_name=req.strategy,
            symbol=req.symbol,
            exchange_name=req.exchange,
            timeframe=req.timeframe,
            days=req.days,
            initial_balance=req.initial_balance,
            params=req.params,
            fee_rate=req.fee_rate,
            position_size_pct=req.position_size_pct,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")
