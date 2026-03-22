"""
AI Decision Layer — plugs Claude/Gemini into decision points where LLM reasoning
genuinely outperforms rules.

3 high-value integration points:
1. NEWS IMPACT ASSESSOR: Reads headlines, determines if they're bullish/bearish/neutral
   for specific assets, and whether to halt or accelerate trading
2. SMART EXIT ADVISOR: Given a position's context, reasons about whether to hold,
   sell, or add to the position
3. LOSS PATTERN ANALYZER: After a series of losses, identifies the root cause
   (bad timing? wrong strategy? market shifted?) and suggests specific fixes

Each function falls back to rule-based logic when no AI API key is configured.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.services.signals.ai_engine import _call_ai, _get_ai_provider

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 0. AI STRATEGY SELECTOR — reasons about WHY to pick strategies
# ═══════════════════════════════════════════════════════════════
async def ai_select_strategies(
    regime: Dict,
    analysis: Dict,
    available_strategies: List[Dict],
    recent_performance: Dict,
    fear_greed: int,
    news_impact: Optional[Dict] = None,
) -> List[Dict]:
    """
    Use AI to reason about which strategies to use and why.
    
    Unlike the hardcoded regime map, the AI considers:
    - Current regime + how confident the regime detection is
    - AI sentiment analysis (which may disagree with regime)
    - Recent strategy performance (what's been working/failing)
    - Fear & Greed level (extreme conditions need different strategies)
    - News impact (breaking news may override normal strategy selection)
    """
    regime_name = regime.get("regime", "ranging")
    regime_conf = regime.get("confidence", 0.5)
    sentiment = analysis.get("sentiment_assessment", "neutral")
    risk_level = analysis.get("risk_level", "medium")

    strat_names = [s["name"] for s in available_strategies]
    perf_summary = ""
    for name, data in recent_performance.items():
        if data.get("trades", 0) > 0:
            perf_summary += f"  {name}: {data.get('win_rate', 0):.0%} win rate over {data['trades']} trades\n"

    prompt = f"""Select and rank the best trading strategies for current conditions.

## Current Conditions:
- Market Regime: {regime_name} (confidence: {regime_conf:.0%})
- AI Sentiment: {sentiment}
- Risk Level: {risk_level}
- Fear & Greed: {fear_greed}/100
- News: {news_impact.get('impact', 'neutral') if news_impact else 'no data'} ({news_impact.get('key_headline', '') if news_impact else ''})

## Available Strategies:
{', '.join(strat_names)}

## Recent Performance:
{perf_summary or 'No live performance data yet'}

## Return JSON: top 3-5 strategies with weights (must sum to 1.0)
{{
  "strategies": [
    {{"name": "strategy_name", "weight": 0.0 to 1.0, "reasoning": "why this strategy fits"}}
  ],
  "overall_reasoning": "1-2 sentence explanation of the selection logic"
}}"""

    response = await _call_ai(prompt, system="You are a quant portfolio manager selecting strategies. Return only JSON.")

    if response:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            result = json.loads(text.strip())

            # Validate and merge with available strategies
            ai_picks = result.get("strategies", [])
            if ai_picks:
                # Build output using AI weights but keeping params from regime map
                strat_map = {s["name"]: s for s in available_strategies}
                output = []
                for pick in ai_picks:
                    name = pick.get("name")
                    if name in strat_map:
                        entry = {**strat_map[name]}
                        entry["weight"] = pick.get("weight", 0.2)
                        entry["ai_reasoning"] = pick.get("reasoning", "")
                        output.append(entry)

                if output:
                    # Normalize weights
                    total = sum(s["weight"] for s in output)
                    if total > 0:
                        for s in output:
                            s["weight"] = round(s["weight"] / total, 3)
                    output.sort(key=lambda x: x["weight"], reverse=True)
                    return output
        except Exception as e:
            logger.warning(f"AI strategy selection parse failed: {e}")

    # Fall through to None — caller will use rule-based
    return []


# ═══════════════════════════════════════════════════════════════
# 1. NEWS IMPACT ASSESSOR
# ═══════════════════════════════════════════════════════════════
async def assess_news_impact(
    news_articles: List[Dict],
    symbol: str,
    current_position: Optional[Dict] = None,
) -> Dict:
    """
    Read recent news headlines and assess their impact on a specific asset.
    
    This is where AI genuinely shines — understanding that "SEC sues exchange"
    is bearish but "SEC approves ETF" is bullish requires language understanding
    that rules can't match.
    """
    if not news_articles:
        return {"impact": "neutral", "score": 0, "should_halt": False, "reasoning": "No news available"}

    headlines = "\n".join([
        f"- {a['title']} ({a.get('source', '?')}, {a.get('published', '?')})"
        for a in news_articles[:10]
    ])

    prompt = f"""Analyze these crypto/financial news headlines and assess their impact on {symbol}.

## Headlines:
{headlines}

## Current Position:
{"Holding " + str(current_position.get('quantity', 0)) + " " + symbol + " (P&L: " + str(current_position.get('unrealized_pnl_pct', 0)) + "%)" if current_position else "No position"}

## Return JSON only:
{{
  "impact": "bullish" | "bearish" | "neutral",
  "impact_score": -1.0 to 1.0 (negative = bearish, positive = bullish),
  "should_halt_trading": true if major negative event (hack, ban, crash),
  "should_accelerate": true if major positive catalyst (ETF approval, partnership),
  "key_headline": "the most market-moving headline",
  "reasoning": "1-2 sentence explanation",
  "affected_assets": ["BTC", "ETH"] (which assets are most affected)
}}"""

    response = await _call_ai(prompt, system="You are a financial news analyst. Assess market impact. Return only JSON.")

    if response:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            result = json.loads(text.strip())
            result["provider"] = _get_ai_provider()
            return result
        except Exception as e:
            logger.warning(f"News impact AI parse failed: {e}")

    # Rule-based fallback: keyword scanning
    return _rule_based_news_impact(news_articles, symbol)


def _rule_based_news_impact(articles: List[Dict], symbol: str) -> Dict:
    """Simple keyword-based news impact assessment."""
    bullish_keywords = ["approve", "etf", "adoption", "partnership", "rally", "surge", "record", "bullish", "upgrade", "institutional"]
    bearish_keywords = ["hack", "ban", "crash", "sec", "lawsuit", "fraud", "collapse", "bearish", "warning", "sell-off", "plunge"]
    
    bull_count = 0
    bear_count = 0
    key_headline = ""

    for article in articles[:10]:
        title_lower = article.get("title", "").lower()
        for kw in bullish_keywords:
            if kw in title_lower:
                bull_count += 1
                if not key_headline:
                    key_headline = article["title"]
        for kw in bearish_keywords:
            if kw in title_lower:
                bear_count += 1
                if not key_headline:
                    key_headline = article["title"]

    score = (bull_count - bear_count) / max(1, bull_count + bear_count)

    return {
        "impact": "bullish" if score > 0.3 else "bearish" if score < -0.3 else "neutral",
        "impact_score": round(score, 3),
        "should_halt_trading": bear_count >= 3,
        "should_accelerate": bull_count >= 3,
        "key_headline": key_headline or "No significant headlines",
        "reasoning": f"Keyword scan: {bull_count} bullish, {bear_count} bearish signals",
        "provider": "rule-based",
    }


# ═══════════════════════════════════════════════════════════════
# 2. SMART EXIT ADVISOR
# ═══════════════════════════════════════════════════════════════
async def advise_exit(
    position: Dict,
    regime: str,
    fear_greed: int,
    news_impact: Dict,
    recent_price_action: str,
) -> Dict:
    """
    Given full context about a position, advise whether to hold, sell, or add.
    
    This is where AI reasoning beats rules — it can weigh multiple conflicting
    signals: "Position is down 3% but regime just shifted bullish and F&G is
    at extreme fear (historically a bottom signal) — HOLD with conviction."
    """
    prompt = f"""You manage a trading position. Decide: HOLD, SELL, or ADD.

## Position:
- Symbol: {position.get('symbol')}
- Side: {position.get('side', 'long')}
- Entry: ${position.get('avg_entry_price', 0):.2f}
- Current: ${position.get('current_price', 0):.2f}
- P&L: {position.get('unrealized_pnl_pct', 0):.1f}%
- Leverage: {position.get('leverage', 1)}x
- Instrument: {position.get('instrument_type', 'spot')}

## Market Context:
- Regime: {regime}
- Fear & Greed: {fear_greed}/100
- News Impact: {news_impact.get('impact', 'neutral')} ({news_impact.get('reasoning', '')})
- Recent Price: {recent_price_action}

## Return JSON only:
{{
  "action": "hold" | "sell" | "add",
  "confidence": 0.0 to 1.0,
  "reasoning": "clear explanation of why",
  "urgency": "low" | "medium" | "high"
}}"""

    response = await _call_ai(prompt, system="You are a portfolio manager. Be decisive. Return only JSON.")

    if response:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            result = json.loads(text.strip())
            result["provider"] = _get_ai_provider()
            return result
        except Exception as e:
            logger.warning(f"Exit advisor AI parse failed: {e}")

    # Rule-based fallback
    pnl = position.get("unrealized_pnl_pct", 0)
    if pnl < -5:
        return {"action": "sell", "confidence": 0.7, "reasoning": f"Down {pnl:.1f}% — cut losses", "urgency": "high", "provider": "rule-based"}
    if pnl > 8 and fear_greed > 75:
        return {"action": "sell", "confidence": 0.6, "reasoning": f"Up {pnl:.1f}% in greedy market — take profit", "urgency": "medium", "provider": "rule-based"}
    if fear_greed < 20 and pnl > -3:
        return {"action": "hold", "confidence": 0.6, "reasoning": "Extreme fear often marks bottoms — patience", "urgency": "low", "provider": "rule-based"}
    return {"action": "hold", "confidence": 0.5, "reasoning": "No strong exit signal", "urgency": "low", "provider": "rule-based"}


# ═══════════════════════════════════════════════════════════════
# 3. LOSS PATTERN ANALYZER
# ═══════════════════════════════════════════════════════════════
async def analyze_loss_pattern(
    recent_losses: List[Dict],
    strategy_usage: Dict,
    regime_history: List[str],
) -> Dict:
    """
    After consecutive losses, identify the ROOT CAUSE and suggest specific fixes.
    
    Common patterns AI can detect:
    - "All losses happened during Asian session" → avoid trading 00:00-08:00 UTC
    - "Momentum strategy keeps losing in ranging market" → regime detector is wrong
    - "Wins are small but losses are large" → tighten stop-loss
    - "Trading too frequently" → increase interval
    """
    if not recent_losses:
        return {"pattern": "none", "recommendation": "No losses to analyze"}

    loss_summary = "\n".join([
        f"- {l.get('symbol')} via {l.get('strategy')}: {l.get('pnl_pct', 0):+.1f}% in {l.get('regime', '?')} regime"
        for l in recent_losses[:15]
    ])

    prompt = f"""Analyze this series of trading losses and identify the root cause pattern.

## Recent Losses:
{loss_summary}

## Strategy Usage:
{json.dumps(strategy_usage, indent=2)}

## Recent Regime History:
{', '.join(regime_history[-10:])}

## Identify:
1. Is there a common pattern? (same strategy? same time? same regime?)
2. What's the root cause?
3. What specific action would fix it?

## Return JSON only:
{{
  "pattern_identified": "description of the pattern",
  "root_cause": "why the losses are happening",
  "severity": "low" | "medium" | "high",
  "fixes": [
    {{"action": "specific fix", "expected_impact": "what it would change"}}
  ],
  "strategy_to_reduce": "strategy name to reduce weight (if applicable)",
  "strategy_to_increase": "strategy name to increase weight (if applicable)"
}}"""

    response = await _call_ai(prompt, system="You are a quant risk manager diagnosing trading losses. Return only JSON.")

    if response:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            result = json.loads(text.strip())
            result["provider"] = _get_ai_provider()
            return result
        except Exception as e:
            logger.warning(f"Loss pattern AI parse failed: {e}")

    # Rule-based fallback
    strategies = [l.get("strategy") for l in recent_losses if l.get("strategy")]
    regimes = [l.get("regime") for l in recent_losses if l.get("regime")]

    from collections import Counter
    strat_counts = Counter(strategies)
    regime_counts = Counter(regimes)
    worst_strategy = strat_counts.most_common(1)[0][0] if strat_counts else "unknown"
    dominant_regime = regime_counts.most_common(1)[0][0] if regime_counts else "unknown"

    return {
        "pattern_identified": f"Most losses from {worst_strategy} strategy in {dominant_regime} regime",
        "root_cause": f"{worst_strategy} may not be suited for {dominant_regime} conditions",
        "severity": "high" if len(recent_losses) >= 5 else "medium",
        "fixes": [
            {"action": f"Reduce {worst_strategy} weight in {dominant_regime} regime", "expected_impact": "Fewer losses from mismatched strategy"},
            {"action": "Increase trading interval to reduce frequency", "expected_impact": "Less exposure to choppy conditions"},
        ],
        "strategy_to_reduce": worst_strategy,
        "strategy_to_increase": None,
        "provider": "rule-based",
    }
