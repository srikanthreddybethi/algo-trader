from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrderCreate(BaseModel):
    portfolio_id: int = 1
    exchange_name: str
    symbol: str
    order_type: str = "market"  # market, limit, stop_loss, take_profit
    side: str  # buy, sell
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    strategy_name: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    portfolio_id: int
    exchange_name: str
    symbol: str
    order_type: str
    side: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: float
    filled_price: Optional[float] = None
    status: str
    is_paper: str
    strategy_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    filled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: int
    portfolio_id: int
    order_id: int
    exchange_name: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    fee_currency: str
    total_cost: float
    is_paper: str
    strategy_name: Optional[str] = None
    executed_at: datetime

    class Config:
        from_attributes = True
