from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    exchange_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    order_type = Column(String, nullable=False)  # "market", "limit", "stop_loss", "take_profit"
    side = Column(String, nullable=False)  # "buy" or "sell"
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Limit price (null for market orders)
    stop_price = Column(Float, nullable=True)
    filled_quantity = Column(Float, default=0.0)
    filled_price = Column(Float, nullable=True)
    status = Column(String, default="pending")  # pending, open, filled, partially_filled, cancelled, rejected
    is_paper = Column(String, default="true")
    strategy_name = Column(String, nullable=True)  # Which strategy placed this
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    filled_at = Column(DateTime, nullable=True)
