"""Signals & AI Analysis API endpoints."""
from fastapi import APIRouter, Query
from app.services.signals.data_feeds import (
    get_fear_greed_index,
    get_coingecko_trending,
    get_crypto_news,
    get_social_sentiment,
    get_all_signals_data,
    classify_asset,
)
from app.services.signals.ai_engine import get_ai_analysis
from app.services.signals.regime_detector import detect_regime
from app.exchanges.manager import exchange_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/fear-greed")
async def fear_greed():
    """Get Crypto Fear & Greed Index."""
    return await get_fear_greed_index()


@router.get("/trending")
async def trending():
    """Get trending coins and global market data from CoinGecko."""
    return await get_coingecko_trending()


@router.get("/news")
async def news():
    """Get latest crypto news from RSS feeds."""
    return await get_crypto_news()


@router.get("/social/{symbol}")
async def social_sentiment(symbol: str = "BTC"):
    """Get social media sentiment for a symbol."""
    return await get_social_sentiment(symbol.upper())


@router.get("/regime/{symbol}")
async def market_regime(
    symbol: str = "BTC",
    exchange: str = Query(default="binance"),
    timeframe: str = Query(default="1h"),
):
    """Detect current market regime using technical analysis."""
    # Normalize symbol
    norm_symbol = symbol.replace("-", "/")
    if "/" not in norm_symbol:
        norm_symbol = f"{norm_symbol}/USDT"

    ohlcv = await exchange_manager.get_ohlcv(exchange, norm_symbol, timeframe, limit=100)
    return detect_regime(ohlcv)


@router.get("/ai-analysis/{symbol}")
async def ai_analysis(
    symbol: str = "BTC",
    exchange: str = Query(default="binance"),
):
    """
    Get AI-powered comprehensive market analysis.
    Uses Claude or Gemini if API key is configured, falls back to rule-based.
    """
    # Normalize
    norm_symbol = symbol.replace("-", "/")
    if "/" not in norm_symbol:
        norm_symbol = f"{norm_symbol}/USDT"

    # Gather all signals data
    signals_data = await get_all_signals_data(symbol.upper().split("/")[0])

    # Get regime data
    ohlcv = await exchange_manager.get_ohlcv(exchange, norm_symbol, "1h", limit=100)
    regime = detect_regime(ohlcv)
    signals_data["regime"] = regime

    # Get AI analysis
    analysis = await get_ai_analysis(signals_data, symbol.upper().split("/")[0])

    return {
        "analysis": analysis,
        "signals": {
            "fear_greed": signals_data.get("fear_greed", {}),
            "social_sentiment": signals_data.get("social_sentiment", {}),
            "regime": regime,
        },
    }


@router.get("/dashboard/{symbol}")
async def signals_dashboard(
    symbol: str = "BTC",
    exchange: str = Query(default="binance"),
    asset_class: str = Query(default=None),
):
    """
    Full signals dashboard data — one endpoint for the entire Signals UI.
    Aggregates: fear & greed, social sentiment, news, regime, AI analysis.
    Supports all asset classes: crypto, forex, stocks, indices, commodities.
    """
    base_symbol = symbol.upper().split("/")[0].split("-")[0]
    detected_class = asset_class or classify_asset(base_symbol)

    # For crypto, normalize to exchange pair format
    norm_symbol = symbol.replace("-", "/")
    if "/" not in norm_symbol:
        norm_symbol = f"{norm_symbol}/USDT"

    # Gather all data in parallel — routes to correct sources per asset class
    signals_data = await get_all_signals_data(base_symbol, detected_class)

    # Regime detection (works for all tradeable assets via OHLCV)
    try:
        ohlcv = await exchange_manager.get_ohlcv(exchange, norm_symbol, "1h", limit=100)
        regime = detect_regime(ohlcv)
    except Exception:
        regime = {"regime": "unknown", "confidence": 0, "description": "No OHLCV data available"}
    signals_data["regime"] = regime

    # AI analysis
    analysis = await get_ai_analysis(signals_data, base_symbol)

    # Build response — include all data from get_all_signals_data plus extras
    response = {**signals_data}
    response["regime"] = regime
    response["ai_analysis"] = analysis
    response["symbol"] = base_symbol
    response["exchange"] = exchange
    response["asset_class"] = detected_class

    # Ensure backward-compatible keys exist for crypto consumers
    if detected_class == "crypto":
        response.setdefault("fear_greed", {})
        response.setdefault("social_sentiment", {})
        response.setdefault("market_data", {})
        response.setdefault("news", [])

    return response
