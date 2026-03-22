from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.core.database import get_db
from app.services.paper_trading import paper_engine
from app.exchanges.manager import exchange_manager

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _serialize_portfolio(p):
    return {
        "id": p.id, "name": p.name, "is_paper": p.is_paper,
        "initial_balance": p.initial_balance, "cash_balance": p.cash_balance,
        "total_value": p.total_value, "total_pnl": p.total_pnl,
        "total_pnl_pct": p.total_pnl_pct, "currency": p.currency,
        "created_at": str(p.created_at) if p.created_at else None,
        "updated_at": str(p.updated_at) if p.updated_at else None,
    }


def _serialize_position(p):
    return {
        "id": p.id, "portfolio_id": p.portfolio_id, "symbol": p.symbol,
        "exchange_name": p.exchange_name, "side": p.side, "quantity": p.quantity,
        "avg_entry_price": p.avg_entry_price, "current_price": p.current_price,
        "unrealized_pnl": p.unrealized_pnl, "unrealized_pnl_pct": p.unrealized_pnl_pct,
        "realized_pnl": p.realized_pnl, "is_open": p.is_open,
        "opened_at": str(p.opened_at) if p.opened_at else None,
        "closed_at": str(p.closed_at) if p.closed_at else None,
    }


def _serialize_snapshot(s):
    return {
        "id": s.id, "portfolio_id": s.portfolio_id, "total_value": s.total_value,
        "cash_balance": s.cash_balance, "positions_value": s.positions_value,
        "total_pnl": s.total_pnl,
        "timestamp": str(s.timestamp) if s.timestamp else None,
    }


@router.get("/")
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    """Get the default portfolio."""
    portfolio = await paper_engine.get_or_create_default_portfolio(db)
    return _serialize_portfolio(portfolio)


@router.post("/")
async def create_portfolio(db: AsyncSession = Depends(get_db),
                           name: str = "Default Portfolio",
                           initial_balance: float = 10000.0,
                           currency: str = "USD"):
    """Create a new paper trading portfolio."""
    portfolio = await paper_engine.create_portfolio(db, name=name,
                                                     initial_balance=initial_balance, currency=currency)
    return _serialize_portfolio(portfolio)


@router.get("/summary")
async def get_portfolio_summary(db: AsyncSession = Depends(get_db)):
    """Get full portfolio summary with positions and snapshots."""
    portfolio = await paper_engine.get_or_create_default_portfolio(db)
    positions = await paper_engine.get_positions(db, portfolio.id)
    snapshots = await paper_engine.get_snapshots(db, portfolio.id, limit=50)

    # Serialize everything into plain dicts BEFORE making any external calls
    portfolio_data = _serialize_portfolio(portfolio)
    positions_data = [_serialize_position(p) for p in positions]
    snapshots_data = [_serialize_snapshot(s) for s in reversed(snapshots)]

    # Now update prices for open positions using external API calls
    for pd in positions_data:
        if pd["is_open"]:
            try:
                ticker = await exchange_manager.get_ticker(pd["exchange_name"], pd["symbol"])
                if ticker:
                    pd["current_price"] = ticker["last_price"]
                    pd["unrealized_pnl"] = (ticker["last_price"] - pd["avg_entry_price"]) * pd["quantity"]
                    if pd["avg_entry_price"] > 0:
                        pd["unrealized_pnl_pct"] = (
                            (ticker["last_price"] - pd["avg_entry_price"]) / pd["avg_entry_price"] * 100
                        )
            except Exception:
                pass

    # Recalculate portfolio totals
    positions_value = sum(p["current_price"] * p["quantity"] for p in positions_data if p["is_open"])
    portfolio_data["total_value"] = portfolio_data["cash_balance"] + positions_value
    portfolio_data["total_pnl"] = portfolio_data["total_value"] - portfolio_data["initial_balance"]
    if portfolio_data["initial_balance"] > 0:
        portfolio_data["total_pnl_pct"] = (portfolio_data["total_pnl"] / portfolio_data["initial_balance"]) * 100

    return {
        "portfolio": portfolio_data,
        "positions": positions_data,
        "recent_snapshots": snapshots_data,
    }


@router.get("/positions")
async def get_positions(open_only: bool = True, db: AsyncSession = Depends(get_db)):
    """Get all positions."""
    portfolio = await paper_engine.get_or_create_default_portfolio(db)
    positions = await paper_engine.get_positions(db, portfolio.id, open_only=open_only)
    positions_data = [_serialize_position(p) for p in positions]

    # Update prices
    for pd in positions_data:
        if pd["is_open"]:
            try:
                ticker = await exchange_manager.get_ticker(pd["exchange_name"], pd["symbol"])
                if ticker:
                    pd["current_price"] = ticker["last_price"]
                    pd["unrealized_pnl"] = (ticker["last_price"] - pd["avg_entry_price"]) * pd["quantity"]
                    if pd["avg_entry_price"] > 0:
                        pd["unrealized_pnl_pct"] = (
                            (ticker["last_price"] - pd["avg_entry_price"]) / pd["avg_entry_price"] * 100
                        )
            except Exception:
                pass

    return positions_data


@router.get("/snapshots")
async def get_snapshots(limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get portfolio value snapshots for charting."""
    portfolio = await paper_engine.get_or_create_default_portfolio(db)
    snapshots = await paper_engine.get_snapshots(db, portfolio.id, limit=limit)
    return [_serialize_snapshot(s) for s in reversed(snapshots)]


@router.post("/reset")
async def reset_portfolio(balance: float = 10000.0, db: AsyncSession = Depends(get_db)):
    """Reset paper portfolio to starting state."""
    portfolio = await paper_engine.reset_portfolio(db, new_balance=balance)
    return {"message": "Portfolio reset", "new_balance": balance}
