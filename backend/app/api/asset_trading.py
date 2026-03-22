"""Asset Trading API — classify instruments, get rules, validate trades, sentiment, strategies."""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.asset_trading_rules import asset_router

router = APIRouter(prefix="/api/asset-trading", tags=["asset-trading"])


@router.get("/classify")
async def classify_asset(
    symbol: str = Query(..., description="Instrument symbol (e.g. BTC/USDT, EURUSD, AAPL)"),
):
    """Classify a symbol into its asset class and return metadata."""
    return asset_router.classify(symbol)


@router.get("/rules")
async def get_trading_rules(
    symbol: str = Query(..., description="Instrument symbol"),
    regime: str = Query("ranging", description="Market regime"),
):
    """Get asset-specific risk parameters and trading rules for a symbol."""
    risk = asset_router.get_risk_params(symbol, regime)
    classification = asset_router.classify(symbol)
    return {
        **classification,
        "risk_params": risk,
    }


@router.get("/validate")
async def validate_trade(
    symbol: str = Query(..., description="Instrument symbol"),
    direction: str = Query(..., description="buy/sell/long/short"),
    fear_greed: Optional[float] = Query(None, description="Fear & Greed index (0-100)"),
    volatility: Optional[float] = Query(None, description="Annualised volatility %"),
    vix: Optional[float] = Query(None, description="VIX level (indices)"),
    btc_dominance: Optional[float] = Query(None, description="BTC dominance % (crypto)"),
    retail_long_pct: Optional[float] = Query(None, description="Retail long % (forex)"),
    earnings_within_days: Optional[int] = Query(None, description="Days until earnings (stocks)"),
    pe_ratio: Optional[float] = Query(None, description="P/E ratio (stocks)"),
    pct_from_52w_high: Optional[float] = Query(None, description="% below 52-week high (stocks)"),
    breadth_ratio: Optional[float] = Query(None, description="Advance/decline ratio (indices)"),
    geopolitical_risk: Optional[float] = Query(None, description="Geopolitical risk 0-1 (commodities)"),
    high_impact_event: bool = Query(False, description="High-impact event imminent (forex)"),
):
    """Validate a trade against asset-specific rules (market hours, sentiment gates, etc.)."""
    kwargs = {}
    if fear_greed is not None:
        kwargs["fear_greed"] = fear_greed
    if volatility is not None:
        kwargs["volatility"] = volatility
    if vix is not None:
        kwargs["vix"] = vix
    if btc_dominance is not None:
        kwargs["btc_dominance"] = btc_dominance
    if retail_long_pct is not None:
        kwargs["retail_long_pct"] = retail_long_pct
    if earnings_within_days is not None:
        kwargs["earnings_within_days"] = earnings_within_days
    if pe_ratio is not None:
        kwargs["pe_ratio"] = pe_ratio
    if pct_from_52w_high is not None:
        kwargs["pct_from_52w_high"] = pct_from_52w_high
    if breadth_ratio is not None:
        kwargs["breadth_ratio"] = breadth_ratio
    if geopolitical_risk is not None:
        kwargs["geopolitical_risk"] = geopolitical_risk
    if high_impact_event:
        kwargs["high_impact_event"] = True

    return asset_router.validate_trade(symbol, direction, **kwargs)


@router.get("/sentiment")
async def get_sentiment_factors(
    symbol: str = Query(..., description="Instrument symbol"),
    fear_greed: Optional[float] = Query(None),
    btc_dominance: Optional[float] = Query(None),
    vix: Optional[float] = Query(None),
    retail_long_pct: Optional[float] = Query(None),
    geopolitical_risk: Optional[float] = Query(None),
    risk_sentiment: Optional[str] = Query(None, description="risk_on or risk_off"),
):
    """Get asset-specific sentiment factors and trading bias."""
    kwargs = {}
    if fear_greed is not None:
        kwargs["fear_greed"] = fear_greed
    if btc_dominance is not None:
        kwargs["btc_dominance"] = btc_dominance
    if vix is not None:
        kwargs["vix"] = vix
    if retail_long_pct is not None:
        kwargs["retail_long_pct"] = retail_long_pct
    if geopolitical_risk is not None:
        kwargs["geopolitical_risk"] = geopolitical_risk
    if risk_sentiment is not None:
        kwargs["risk_sentiment"] = risk_sentiment

    return asset_router.get_sentiment_factors(symbol, **kwargs)


@router.get("/strategies")
async def get_asset_strategies(
    symbol: str = Query(..., description="Instrument symbol"),
    regime: str = Query("ranging", description="Market regime"),
):
    """Get optimal strategies for a symbol based on asset class and regime."""
    return asset_router.get_optimal_strategies(symbol, regime)
