from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ExchangeCreate(BaseModel):
    name: str
    exchange_type: str = "crypto"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    is_testnet: bool = True
    # Connector-specific credential fields (used by non-ccxt exchanges)
    identifier: Optional[str] = None       # IG, Capital.com username
    password: Optional[str] = None         # IG, Capital.com password
    api_token: Optional[str] = None        # OANDA bearer token
    account_id: Optional[str] = None       # OANDA, Saxo account ID
    access_token: Optional[str] = None     # Saxo OAuth token
    account_key: Optional[str] = None      # Saxo account key
    gateway_url: Optional[str] = None      # IBKR gateway URL
    mt5_login: Optional[str] = None        # CMC MT5 login
    mt5_password: Optional[str] = None     # CMC MT5 password
    mt5_server: Optional[str] = None       # CMC MT5 server
    bridge_url: Optional[str] = None       # CMC MT5 bridge proxy URL


class ExchangeUpdate(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    is_testnet: Optional[bool] = None
    is_active: Optional[bool] = None


class ExchangeResponse(BaseModel):
    id: int
    name: str
    exchange_type: str
    is_testnet: bool
    is_active: bool
    status: str
    supported_pairs: List[str]
    last_connected: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExchangeTickerResponse(BaseModel):
    symbol: str
    exchange: str
    last_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    change_24h: Optional[float] = None
    change_pct_24h: Optional[float] = None
    timestamp: Optional[datetime] = None
