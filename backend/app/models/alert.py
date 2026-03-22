"""Alert model for price and portfolio alerts."""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum
from app.core.database import Base
from datetime import datetime
import enum


class AlertType(str, enum.Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PNL_ABOVE = "pnl_above"
    PNL_BELOW = "pnl_below"
    DRAWDOWN = "drawdown"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String, nullable=False)
    symbol = Column(String, nullable=True)
    exchange_name = Column(String, nullable=True)
    threshold = Column(Float, nullable=False)
    message = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
