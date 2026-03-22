from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PortfolioCreate(BaseModel):
    name: str = "Default Portfolio"
    initial_balance: float = 10000.0
    currency: str = "USD"
    is_paper: bool = True


class PortfolioResponse(BaseModel):
    id: int
    name: str
    is_paper: bool
    initial_balance: float
    cash_balance: float
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    currency: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    exchange_name: str
    side: str
    quantity: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float
    is_open: bool
    opened_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortfolioSnapshotResponse(BaseModel):
    id: int
    portfolio_id: int
    total_value: float
    cash_balance: float
    positions_value: float
    total_pnl: float
    timestamp: datetime

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    portfolio: PortfolioResponse
    positions: List[PositionResponse]
    recent_snapshots: List[PortfolioSnapshotResponse]
