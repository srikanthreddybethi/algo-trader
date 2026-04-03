"""Trust Score API — evaluate execution confidence, view analytics, venue scores."""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.execution_trust import trust_scorer
from app.services.asset_trading_rules import asset_router
from app.services.signals.regime_detector import detect_regime
from app.services.signals.data_feeds import get_all_signals_data, get_fear_greed_index
from app.services.signals.ai_engine import get_ai_analysis
from app.services.intelligence import intelligence
from app.exchanges.manager import exchange_manager
from app.services.geo_risk.monitor import geo_monitor

router = APIRouter(prefix="/api/trust-score", tags=["trust-score"])


@router.get("/evaluate")
async def evaluate_trust(
    symbol: str = Query(..., description="Instrument symbol (e.g. BTC/USDT, EUR/USD)"),
    direction: str = Query("buy", description="Trade direction: buy or sell"),
    exchange: str = Query("binance", description="Exchange name"),
    asset_class: Optional[str] = Query(None, description="Asset class (auto-detected if missing)"),
):
    """
    Evaluate execution trust for a potential trade.

    Gathers current regime, sentiment, spread, and strategy data,
    then computes a single 0-1 trust score with grade and recommendation.
    """
    # Auto-detect asset class if not provided
    if not asset_class:
        classification = asset_router.classify(symbol)
        asset_class = classification.get("asset_class", "crypto")

    # Gather live data
    base = symbol.split("/")[0]
    signals_data = {}
    regime = {}
    analysis = {}

    try:
        signals_data = await get_all_signals_data(base)
    except Exception:
        pass

    try:
        ohlcv = await exchange_manager.get_ohlcv(exchange, symbol, "1h", limit=100)
        if ohlcv:
            regime = detect_regime(ohlcv)
    except Exception:
        pass

    try:
        if signals_data:
            analysis = await get_ai_analysis(signals_data, base)
    except Exception:
        pass

    # Compute MTF agreement from intelligence
    mtf_agreement = 0.5
    try:
        mtf = intelligence.check_mtf_consensus(exchange, symbol)
        if mtf and mtf.get("consensus"):
            mtf_agreement = 1.0
        elif mtf:
            mtf_agreement = 0.33
    except Exception:
        pass

    # Strategy win rate from scoreboard
    strategy_win_rate = 0.5
    strategy_trades_count = 0
    try:
        live_scores = intelligence.scoreboard.get_live_scores()
        if live_scores:
            # Average across strategies
            rates = [v.get("win_rate", 0.5) for v in live_scores.values() if v.get("total_trades", 0) > 0]
            counts = [v.get("total_trades", 0) for v in live_scores.values()]
            if rates:
                strategy_win_rate = sum(rates) / len(rates)
            strategy_trades_count = sum(counts)
    except Exception:
        pass

    # Sentiment score
    sentiment_score = 0.0
    try:
        us = signals_data.get("universal_sentiment", {})
        sentiment_score = us.get("sentiment_score", 0.0)
    except Exception:
        pass

    # News risk level — powered by Geopolitical Risk module
    news_risk = "none"
    try:
        # Use geo_monitor for comprehensive geo-risk-aware news assessment
        geo_news_risk = geo_monitor.get_news_risk_level(asset_class)
        if geo_news_risk != "none":
            news_risk = geo_news_risk
        else:
            # Fallback to basic keyword scan when geo module has no data
            news = signals_data.get("news", [])
            if news:
                news_risk = "low"
                for n in news[:5]:
                    title = (n.get("title", "") + n.get("text", "")).lower()
                    if any(w in title for w in ("crash", "hack", "ban", "lawsuit", "fraud")):
                        news_risk = "high"
                        break
                    if any(w in title for w in ("warning", "risk", "concern", "drop")):
                        news_risk = "medium"
    except Exception:
        pass

    # Determine regime alignment
    regime_type = regime.get("regime", "ranging")
    regime_aligns = (
        (direction == "buy" and regime_type in ("trending_up", "ranging")) or
        (direction == "sell" and regime_type in ("trending_down", "ranging"))
    )

    # Sentiment alignment
    sentiment_aligns = (
        (direction == "buy" and sentiment_score >= 0) or
        (direction == "sell" and sentiment_score <= 0)
    )

    is_sb = exchange in ("ig", "capital", "cmc")

    result = trust_scorer.evaluate(
        symbol=symbol,
        asset_class=asset_class,
        direction=direction,
        exchange=exchange,
        signal_confidence=analysis.get("confidence", 0.5),
        mtf_agreement=mtf_agreement,
        regime_confidence=regime.get("confidence", 0.5),
        regime_aligns_with_direction=regime_aligns,
        sentiment_score=sentiment_score,
        sentiment_aligns=sentiment_aligns,
        strategy_win_rate=strategy_win_rate,
        strategy_trades_count=strategy_trades_count,
        current_spread_vs_avg=1.0,
        data_age_seconds=0,
        news_risk=news_risk,
        portfolio_drawdown_pct=0,
        max_drawdown_pct=10,
        is_spread_bet=is_sb,
    )

    return result


@router.get("/analytics")
async def get_analytics():
    """Get trust score analytics: grade distribution, outcome correlation, venue scores."""
    return trust_scorer.get_analytics()


@router.get("/venues")
async def get_venues():
    """Get venue quality scores for all tracked exchanges."""
    return trust_scorer.venue_tracker.get_all_venues()


@router.get("/history")
async def get_history(
    limit: int = Query(20, description="Number of recent evaluations to return"),
):
    """Get recent trust score evaluations."""
    return trust_scorer.history.get_recent(limit)


@router.get("/weights/{asset_class}")
async def get_weights(asset_class: str):
    """Get the weight profile for an asset class."""
    weights = trust_scorer.WEIGHT_PROFILES.get(
        asset_class, trust_scorer.DEFAULT_WEIGHTS
    )
    return {
        "asset_class": asset_class,
        "weights": weights,
        "total": round(sum(weights.values()), 4),
    }
