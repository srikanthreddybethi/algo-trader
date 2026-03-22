from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.services.paper_trading import paper_engine
from app.schemas.order import OrderCreate

router = APIRouter(prefix="/api/trading", tags=["trading"])


def serialize_order(order):
    return {
        "id": order.id, "portfolio_id": order.portfolio_id,
        "exchange_name": order.exchange_name, "symbol": order.symbol,
        "order_type": order.order_type, "side": order.side,
        "quantity": order.quantity, "price": order.price,
        "stop_price": order.stop_price, "filled_quantity": order.filled_quantity,
        "filled_price": order.filled_price, "status": order.status,
        "is_paper": order.is_paper, "strategy_name": order.strategy_name,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "filled_at": order.filled_at.isoformat() if order.filled_at else None,
    }


def serialize_trade(trade):
    return {
        "id": trade.id, "portfolio_id": trade.portfolio_id,
        "order_id": trade.order_id, "exchange_name": trade.exchange_name,
        "symbol": trade.symbol, "side": trade.side,
        "quantity": trade.quantity, "price": trade.price,
        "fee": trade.fee, "fee_currency": trade.fee_currency,
        "total_cost": trade.total_cost, "is_paper": trade.is_paper,
        "strategy_name": trade.strategy_name,
        "executed_at": trade.executed_at.isoformat() if trade.executed_at else None,
    }


@router.post("/orders")
async def place_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Place a paper trading order."""
    try:
        order = await paper_engine.place_order(db, order_data.model_dump())
        return serialize_order(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders")
async def get_orders(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent orders."""
    orders = await paper_engine.get_orders(db, limit=limit)
    return [serialize_order(o) for o in orders]


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Cancel a pending order."""
    order = await paper_engine.cancel_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order(order)


@router.get("/trades")
async def get_trades(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent trades."""
    trades = await paper_engine.get_trades(db, limit=limit)
    return [serialize_trade(t) for t in trades]
