from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    APP_NAME: str = "AlgoTrader"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./algotrader.db"

    # Paper Trading
    DEFAULT_PAPER_BALANCE: float = 10000.0
    DEFAULT_PAPER_CURRENCY: str = "USD"

    # Exchange API Keys (optional - for live trading later)
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET: Optional[str] = None
    BYBIT_API_KEY: Optional[str] = None
    BYBIT_SECRET: Optional[str] = None
    KRAKEN_API_KEY: Optional[str] = None
    KRAKEN_SECRET: Optional[str] = None
    COINBASE_API_KEY: Optional[str] = None
    COINBASE_SECRET: Optional[str] = None

    # Alpaca
    ALPACA_API_KEY: Optional[str] = None
    ALPACA_SECRET_KEY: Optional[str] = None
    ALPACA_PAPER: bool = True

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
