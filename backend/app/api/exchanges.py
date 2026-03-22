from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
from app.core.database import get_db
from app.exchanges.manager import exchange_manager, EXCHANGE_CONFIGS
from app.models.exchange import Exchange
from app.schemas.exchange import (
    ExchangeCreate, ExchangeUpdate, ExchangeResponse, ExchangeTickerResponse,
)

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])


@router.get("/supported")
async def get_supported_exchanges():
    """List all supported exchanges with full metadata."""
    return exchange_manager.get_supported_exchanges()


@router.get("/status")
async def get_exchange_status():
    """Get connection status of all exchanges."""
    return exchange_manager.get_status()


@router.get("/config-fields/{exchange_name}")
async def get_config_fields(exchange_name: str):
    """Return the credential fields required for a given exchange."""
    if exchange_name not in EXCHANGE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange_name} not found")
    return exchange_manager.get_config_fields(exchange_name)


@router.post("/connect/{exchange_name}")
async def connect_exchange(
    exchange_name: str,
    data: ExchangeCreate = None,
    db: AsyncSession = Depends(get_db),
):
    """Connect to any exchange (ccxt, connector, or alpaca)."""
    if exchange_name not in EXCHANGE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Unsupported exchange: {exchange_name}")

    config = EXCHANGE_CONFIGS[exchange_name]
    etype = config["type"]

    if etype == "connector":
        # Build credentials dict from the request body
        credentials: Dict[str, Any] = {}
        if data:
            # Standard fields
            if data.api_key:
                credentials["api_key"] = data.api_key
            if data.api_secret:
                credentials["api_secret"] = data.api_secret
            if data.passphrase:
                credentials["passphrase"] = data.passphrase
            credentials["is_demo"] = data.is_testnet
            # Forward any extra fields from the request body via __dict__
            for field_name in ("identifier", "password", "api_token", "account_id",
                               "access_token", "account_key", "gateway_url",
                               "mt5_login", "mt5_password", "mt5_server", "bridge_url"):
                val = getattr(data, field_name, None)
                if val is not None:
                    credentials[field_name] = val

        result = await exchange_manager.connect(
            name=exchange_name,
            credentials=credentials,
            is_testnet=data.is_testnet if data else True,
        )
    else:
        # ccxt or alpaca
        api_key = data.api_key if data else None
        api_secret = data.api_secret if data else None
        passphrase = data.passphrase if data else None
        is_testnet = data.is_testnet if data else True

        result = await exchange_manager.connect(
            name=exchange_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            is_testnet=is_testnet,
        )

    if result.get("status") == "connected":
        # Persist to DB
        existing = await db.execute(
            select(Exchange).where(Exchange.name == exchange_name)
        )
        exchange_record = existing.scalar_one_or_none()
        is_testnet_val = data.is_testnet if data else True
        if exchange_record:
            exchange_record.status = "connected"
            exchange_record.is_testnet = is_testnet_val
            exchange_record.is_active = True
        else:
            exchange_record = Exchange(
                name=exchange_name,
                exchange_type=config.get("category", etype),
                api_key=data.api_key if data else None,
                api_secret=data.api_secret if data else None,
                is_testnet=is_testnet_val,
                is_active=True,
                status="connected",
                supported_pairs=result.get("pairs", exchange_manager.get_default_pairs(exchange_name)),
            )
            db.add(exchange_record)
        await db.commit()

    return result


@router.post("/disconnect/{exchange_name}")
async def disconnect_exchange(exchange_name: str, db: AsyncSession = Depends(get_db)):
    """Disconnect from any exchange."""
    await exchange_manager.disconnect(exchange_name)

    existing = await db.execute(
        select(Exchange).where(Exchange.name == exchange_name)
    )
    exchange_record = existing.scalar_one_or_none()
    if exchange_record:
        exchange_record.status = "disconnected"
        await db.commit()

    return {"status": "disconnected"}


@router.get("/ticker/{exchange_name}/{symbol}")
async def get_ticker(exchange_name: str, symbol: str):
    """Get current ticker for a symbol on any exchange."""
    symbol = symbol.replace("-", "/")
    ticker = await exchange_manager.get_ticker(exchange_name, symbol)
    if not ticker:
        raise HTTPException(status_code=404, detail="Could not fetch ticker")
    return ticker


@router.get("/tickers/{exchange_name}")
async def get_tickers(exchange_name: str):
    """Get tickers for all default pairs of an exchange."""
    pairs = exchange_manager.get_default_pairs(exchange_name)
    if not pairs:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange_name} not found or has no default pairs")
    tickers = await exchange_manager.get_tickers(exchange_name, pairs)
    return tickers


@router.get("/ohlcv/{exchange_name}/{symbol}")
async def get_ohlcv(exchange_name: str, symbol: str, timeframe: str = "1h", limit: int = 100):
    """Get OHLCV candle data from any exchange."""
    symbol = symbol.replace("-", "/")
    data = await exchange_manager.get_ohlcv(exchange_name, symbol, timeframe, limit)
    return data


@router.get("/orderbook/{exchange_name}/{symbol}")
async def get_order_book(exchange_name: str, symbol: str, limit: int = 20):
    """Get order book for a symbol on any exchange."""
    symbol = symbol.replace("-", "/")
    data = await exchange_manager.get_order_book(exchange_name, symbol, limit)
    return data
