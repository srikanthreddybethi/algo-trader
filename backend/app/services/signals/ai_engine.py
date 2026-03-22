"""
AI Analysis Engine — uses Claude or Gemini for intelligent market analysis.
Falls back to rule-based analysis when no API key is configured.

The AI engine:
1. Analyzes aggregated market data (sentiment, news, technicals)
2. Generates market briefs and trade signals
3. Scores overall market conditions
4. Recommends strategy selection
"""
import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Cache AI responses (expensive calls)
_ai_cache: Dict[str, Any] = {}
_ai_cache_ttl: Dict[str, datetime] = {}
AI_CACHE_DURATION = timedelta(minutes=15)


def _get_ai_cached(key: str) -> Optional[Any]:
    if key in _ai_cache and key in _ai_cache_ttl:
        if datetime.utcnow() - _ai_cache_ttl[key] < AI_CACHE_DURATION:
            return _ai_cache[key]
    return None


def _set_ai_cached(key: str, value: Any):
    _ai_cache[key] = value
    _ai_cache_ttl[key] = datetime.utcnow()


def _get_ai_provider() -> Optional[str]:
    """Detect which AI provider is available."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return None


async def _call_claude(prompt: str, system: str = "") -> str:
    """Call Claude API for analysis."""
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system or "You are an expert quantitative analyst and crypto trader.",
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def _call_gemini(prompt: str) -> str:
    """Call Gemini API for analysis."""
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = await model.generate_content_async(prompt)
    return response.text


async def _call_ai(prompt: str, system: str = "") -> Optional[str]:
    """Call whichever AI provider is available."""
    provider = _get_ai_provider()
    if not provider:
        return None
    try:
        if provider == "claude":
            return await _call_claude(prompt, system)
        elif provider == "gemini":
            return await _call_gemini(prompt)
    except Exception as e:
        logger.error(f"AI call failed ({provider}): {e}")
        return None


def _build_analysis_prompt(signals_data: Dict, symbol: str = "BTC") -> str:
    """Build a comprehensive prompt from all available signals data."""
    fear_greed = signals_data.get("fear_greed", {})
    social = signals_data.get("social_sentiment", {})
    market = signals_data.get("market_data", {})
    news = signals_data.get("news", [])
    regime = signals_data.get("regime", {})

    news_summary = "\n".join([
        f"- {a['title']} ({a['source']})"
        for a in (news[:8] if isinstance(news, list) else [])
    ])

    return f"""Analyze the current market conditions for {symbol} and crypto markets.

## Data Points:

**Fear & Greed Index:** {fear_greed.get('value', 'N/A')} ({fear_greed.get('label', 'N/A')})

**Social Sentiment ({symbol}):**
- Bullish: {social.get('bullish_pct', 'N/A')}% | Bearish: {social.get('bearish_pct', 'N/A')}%
- Sentiment Score: {social.get('sentiment_score', 'N/A')} (-1 to 1)
- 24h Mentions: {social.get('mentions_24h', 'N/A')}
- Volume Change: {social.get('volume_change_pct', 'N/A')}%
- Trending Keywords: {', '.join(social.get('trending_keywords', []))}

**Global Market:**
- BTC Dominance: {market.get('global_data', {}).get('btc_dominance', 'N/A')}%
- 24h Market Cap Change: {market.get('global_data', {}).get('market_cap_change_24h', 'N/A')}%

**Market Regime:** {regime.get('regime', 'N/A')} (Confidence: {regime.get('confidence', 'N/A')})

**Recent Headlines:**
{news_summary or 'No headlines available'}

## Provide your analysis as JSON with this exact structure:
{{
  "market_brief": "2-3 sentence summary of current market conditions",
  "sentiment_assessment": "bullish" | "bearish" | "neutral",
  "confidence": 0.0 to 1.0,
  "key_factors": ["factor1", "factor2", "factor3"],
  "risk_level": "low" | "medium" | "high",
  "recommended_action": "accumulate" | "hold" | "reduce" | "wait",
  "recommended_strategies": ["strategy1", "strategy2"],
  "price_outlook": "short description of expected price action",
  "warnings": ["any risk warnings"]
}}

Return ONLY the JSON, no other text."""


async def get_ai_analysis(signals_data: Dict, symbol: str = "BTC") -> Dict:
    """
    Get AI-powered market analysis. Falls back to rule-based if no AI configured.
    """
    cache_key = f"analysis_{symbol}_{datetime.utcnow().strftime('%Y%m%d%H')}"
    cached = _get_ai_cached(cache_key)
    if cached:
        return cached

    prompt = _build_analysis_prompt(signals_data, symbol)

    # Try AI first
    ai_response = await _call_ai(prompt, system="You are an expert quantitative analyst. Return only valid JSON.")

    if ai_response:
        try:
            # Parse JSON from response (handle markdown code blocks)
            text = ai_response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            result = json.loads(text.strip())
            result["provider"] = _get_ai_provider()
            result["timestamp"] = datetime.utcnow().isoformat()
            _set_ai_cached(cache_key, result)
            return result
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse AI response: {e}")

    # Fallback: rule-based analysis
    result = _rule_based_analysis(signals_data, symbol)
    _set_ai_cached(cache_key, result)
    return result


def _rule_based_analysis(signals_data: Dict, symbol: str) -> Dict:
    """Rule-based fallback analysis when no AI is available."""
    fear_greed = signals_data.get("fear_greed", {})
    social = signals_data.get("social_sentiment", {})
    regime = signals_data.get("regime", {})

    fg_value = fear_greed.get("value", 50)
    bullish_pct = social.get("bullish_pct", 50)
    sentiment_score = social.get("sentiment_score", 0)
    regime_type = regime.get("regime", "unknown")

    # Composite score: -1 (very bearish) to +1 (very bullish)
    # Weights: regime 0.5, fear&greed 0.35, social 0.15
    # Social weight reduced from 0.4 → 0.15 because simulated social data
    # is neutral/unreliable and was dominating the composite.
    fg_score = (fg_value - 50) / 50
    social_score = sentiment_score
    regime_score = 0.5 if regime_type == "trending_up" else -0.3 if regime_type == "trending_down" else 0
    composite = (fg_score * 0.35 + social_score * 0.15 + regime_score * 0.5)
    composite = max(-1, min(1, composite))

    # Determine sentiment
    if composite > 0.3:
        sentiment = "bullish"
        action = "accumulate"
        strategies = ["Momentum", "SMA Crossover", "EMA Crossover"]
    elif composite < -0.3:
        sentiment = "bearish"
        action = "reduce"
        strategies = ["Mean Reversion", "Grid Trading", "DCA"]
    else:
        sentiment = "neutral"
        action = "hold"
        strategies = ["Bollinger Bands", "RSI", "Grid Trading"]

    # Risk level
    if fg_value < 20 or fg_value > 80:
        risk = "high"
    elif fg_value < 35 or fg_value > 65:
        risk = "medium"
    else:
        risk = "low"

    # Build brief
    fg_label = fear_greed.get("label", "Neutral")
    brief = f"The crypto market is showing {fg_label.lower()} sentiment with Fear & Greed at {fg_value}/100. "
    brief += f"Social sentiment for {symbol} is {bullish_pct}% bullish. "
    if regime_type != "unknown":
        brief += f"The market regime is {regime_type.replace('_', ' ')}."

    # Key factors
    factors = []
    if fg_value < 30:
        factors.append("Extreme fear — potential contrarian buy opportunity")
    elif fg_value > 70:
        factors.append("High greed — potential overextension risk")

    if bullish_pct > 65:
        factors.append(f"Strong social bullishness ({bullish_pct}%)")
    elif bullish_pct < 35:
        factors.append(f"Social bearishness dominant ({100 - bullish_pct}% bearish)")

    keywords = social.get("trending_keywords", [])
    if keywords:
        factors.append(f"Trending: {', '.join(keywords[:3])}")

    if not factors:
        factors = ["Mixed signals — no strong directional bias", "Monitor for breakout or breakdown"]

    # Warnings
    warnings = []
    if fg_value > 80:
        warnings.append("Extreme greed often precedes corrections")
    if fg_value < 20:
        warnings.append("Extreme fear can lead to capitulation or reversal")
    if abs(social.get("volume_change_pct", 0)) > 40:
        warnings.append("Unusual social volume detected — potential volatility ahead")

    return {
        "market_brief": brief,
        "sentiment_assessment": sentiment,
        "confidence": round(abs(composite), 2),
        "key_factors": factors,
        "risk_level": risk,
        "recommended_action": action,
        "recommended_strategies": strategies,
        "price_outlook": f"{'Upward' if composite > 0.2 else 'Downward' if composite < -0.2 else 'Sideways'} bias with {risk} volatility expected",
        "warnings": warnings or ["No significant warnings"],
        "composite_score": round(composite, 3),
        "provider": "rule-based",
        "timestamp": datetime.utcnow().isoformat(),
    }
