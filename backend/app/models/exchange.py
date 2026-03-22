from sqlalchemy import Column, String, Boolean, Float, DateTime, Integer, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class Exchange(Base):
    __tablename__ = "exchanges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # e.g., "binance", "bybit", "alpaca"
    exchange_type = Column(String, nullable=False)  # "crypto" or "stock"
    api_key = Column(String, nullable=True)
    api_secret = Column(String, nullable=True)
    passphrase = Column(String, nullable=True)  # Some exchanges require this
    is_testnet = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    status = Column(String, default="disconnected")  # connected, disconnected, error
    supported_pairs = Column(JSON, default=[])
    last_connected = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
