from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    exchange_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # "buy" or "sell"
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    fee_currency = Column(String, default="USD")
    total_cost = Column(Float, nullable=False)  # quantity * price + fee
    is_paper = Column(String, default="true")
    strategy_name = Column(String, nullable=True)
    executed_at = Column(DateTime, server_default=func.now())
