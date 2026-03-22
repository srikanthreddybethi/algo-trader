from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="Default Portfolio")
    is_paper = Column(Boolean, default=True)
    initial_balance = Column(Float, nullable=False, default=10000.0)
    cash_balance = Column(Float, nullable=False, default=10000.0)
    total_value = Column(Float, nullable=False, default=10000.0)
    total_pnl = Column(Float, default=0.0)
    total_pnl_pct = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String, nullable=False)  # e.g., "BTC/USDT", "AAPL"
    exchange_name = Column(String, nullable=False)
    side = Column(String, nullable=False)  # "long" or "short"
    quantity = Column(Float, nullable=False, default=0.0)
    avg_entry_price = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_pct = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    is_open = Column(Boolean, default=True)
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Derivatives fields
    instrument_type = Column(String, default="spot")  # spot, perpetual, future, option, margin
    leverage = Column(Float, default=1.0)  # 1x = no leverage
    margin_used = Column(Float, default=0.0)  # Collateral locked
    liquidation_price = Column(Float, nullable=True)  # Price at which position is liquidated
    funding_paid = Column(Float, default=0.0)  # Cumulative funding fees (perpetuals)
    expiry_date = Column(DateTime, nullable=True)  # For futures/options
    strike_price = Column(Float, nullable=True)  # For options
    option_type = Column(String, nullable=True)  # "call" or "put" for options


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False, default=0.0)
    total_pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime, server_default=func.now())
