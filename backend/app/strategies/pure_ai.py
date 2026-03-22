"""
Pure AI Strategy — LLM-powered signal generation.

Unlike quantitative strategies that follow fixed rules, this strategy sends
OHLCV data + technical indicators + sentiment context to an LLM and asks it
to reason about whether to buy, sell, or hold.

Inspired by HKUDS/AI-Trader: the LLM gets zero preset rules, it must reason
from first principles about price action, volume patterns, and market context.

Falls back to a multi-factor scoring model when no AI API key is configured.
"""
import os
import json
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime

from app.strategies.base import BaseStrategy, StrategyParam

logger = logging.getLogger(__name__)


def _compute_technicals(df: pd.DataFrame) -> Dict:
    """Compute a summary of technical indicators from OHLCV data."""
    c = df["close"]
    n = len(c)
    latest = float(c.iloc[-1])

    # RSI
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = float((100 - 100 / (1 + rs)).iloc[-1]) if n > 14 else 50.0

    # Moving averages
    sma_20 = float(c.rolling(20).mean().iloc[-1]) if n >= 20 else latest
    sma_50 = float(c.rolling(min(50, n)).mean().iloc[-1])
    ema_12 = float(c.ewm(span=12).mean().iloc[-1])
    ema_26 = float(c.ewm(span=26).mean().iloc[-1])
    macd = ema_12 - ema_26
    macd_signal = float(c.ewm(span=12).mean().ewm(span=9).mean().iloc[-1]) - float(c.ewm(span=26).mean().ewm(span=9).mean().iloc[-1])

    # Bollinger Bands
    bb_mid = sma_20
    bb_std = float(c.rolling(20).std().iloc[-1]) if n >= 20 else 0
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_position = ((latest - bb_lower) / (bb_upper - bb_lower) * 100) if (bb_upper - bb_lower) > 0 else 50

    # Trend
    pct_5 = float(((c.iloc[-1] / c.iloc[-min(5, n)]) - 1) * 100) if n > 1 else 0
    pct_20 = float(((c.iloc[-1] / c.iloc[-min(20, n)]) - 1) * 100) if n > 1 else 0

    # Volume trend
    if "volume" in df.columns and n >= 10:
        vol_recent = float(df["volume"].iloc[-5:].mean())
        vol_older = float(df["volume"].iloc[-10:-5].mean())
        vol_change = ((vol_recent - vol_older) / vol_older * 100) if vol_older > 0 else 0
    else:
        vol_change = 0

    # Volatility
    returns = np.log(c / c.shift(1)).dropna()
    volatility = float(returns.std() * np.sqrt(252) * 100) if len(returns) > 1 else 0

    return {
        "price": round(latest, 2),
        "rsi": round(rsi, 1),
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
        "price_vs_sma20_pct": round((latest - sma_20) / sma_20 * 100, 2) if sma_20 > 0 else 0,
        "macd": round(macd, 4),
        "macd_histogram": round(macd - macd_signal, 4),
        "bb_position_pct": round(bb_position, 1),
        "change_5_bars_pct": round(pct_5, 2),
        "change_20_bars_pct": round(pct_20, 2),
        "volume_change_pct": round(vol_change, 1),
        "volatility_annual_pct": round(volatility, 1),
        "candle_count": n,
    }


def _summarize_recent_candles(df: pd.DataFrame, count: int = 10) -> str:
    """Create a human-readable summary of recent price action."""
    recent = df.tail(count)
    lines = []
    for _, row in recent.iterrows():
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        body = "green" if c >= o else "red"
        body_pct = abs(c - o) / o * 100 if o > 0 else 0
        wick_pct = (h - l) / l * 100 if l > 0 else 0
        lines.append(f"  O:{o:.2f} H:{h:.2f} L:{l:.2f} C:{c:.2f} ({body}, body:{body_pct:.1f}%, range:{wick_pct:.1f}%)")
    return "\n".join(lines)


async def _ask_llm_for_signal(technicals: Dict, candle_summary: str, params: Dict) -> Optional[int]:
    """Ask Claude or Gemini to analyze and produce a signal."""
    from app.services.signals.ai_engine import _call_ai

    aggression = params.get("aggression", "moderate")
    context = params.get("context", "")

    prompt = f"""You are an expert trader analyzing live market data. Based ONLY on the data below, decide whether to BUY, SELL, or HOLD.

## Technical Indicators
- Current Price: ${technicals['price']}
- RSI (14): {technicals['rsi']} (oversold <30, overbought >70)
- SMA 20: ${technicals['sma_20']} (price is {technicals['price_vs_sma20_pct']:+.1f}% from SMA20)
- SMA 50: ${technicals['sma_50']}
- MACD: {technicals['macd']:.4f}, Histogram: {technicals['macd_histogram']:.4f}
- Bollinger Band Position: {technicals['bb_position_pct']:.0f}% (0=lower band, 100=upper band)
- 5-bar Change: {technicals['change_5_bars_pct']:+.1f}%
- 20-bar Change: {technicals['change_20_bars_pct']:+.1f}%
- Volume Change (recent vs prior): {technicals['volume_change_pct']:+.0f}%
- Annualized Volatility: {technicals['volatility_annual_pct']:.0f}%

## Recent {min(10, technicals['candle_count'])} Candles
{candle_summary}

## Trading Style: {aggression}
{f"Additional context: {context}" if context else ""}

## Rules
- You MUST be decisive. No hedging your answer.
- Consider momentum, mean reversion, support/resistance, volume confirmation
- Aggression "{aggression}" means: conservative = only high-conviction trades, moderate = normal, aggressive = trade on smaller signals

## Response
Return EXACTLY one JSON object:
{{"signal": 1, "confidence": 0.8, "reasoning": "brief explanation"}}

Where signal is: 1 = BUY, -1 = SELL, 0 = HOLD
Confidence is 0.0 to 1.0
Return ONLY the JSON, nothing else."""

    response = await _call_ai(prompt, system="You are a quantitative trader. Return only valid JSON.")

    if response:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            result = json.loads(text.strip())
            signal = int(result.get("signal", 0))
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")

            logger.info(f"Pure AI signal: {signal} (conf: {confidence}) — {reasoning}")

            # Filter by minimum confidence
            min_conf = {"conservative": 0.7, "moderate": 0.5, "aggressive": 0.3}.get(aggression, 0.5)
            if confidence < min_conf:
                return 0

            return signal
        except Exception as e:
            logger.warning(f"Failed to parse AI signal: {e}")

    return None


def _fallback_multi_factor(technicals: Dict, params: Dict) -> int:
    """
    Multi-factor scoring model — fallback when no LLM is available.
    Scores multiple technical factors and produces a composite signal.
    """
    score = 0.0
    aggression = params.get("aggression", "moderate")

    rsi = technicals["rsi"]
    macd_hist = technicals["macd_histogram"]
    bb_pos = technicals["bb_position_pct"]
    price_vs_sma = technicals["price_vs_sma20_pct"]
    change_5 = technicals["change_5_bars_pct"]
    change_20 = technicals["change_20_bars_pct"]
    vol_change = technicals["volume_change_pct"]

    # RSI factor (mean reversion)
    if rsi < 30:
        score += 2.0  # Oversold = buy signal
    elif rsi < 40:
        score += 0.5
    elif rsi > 70:
        score -= 2.0  # Overbought = sell signal
    elif rsi > 60:
        score -= 0.5

    # MACD factor (momentum)
    if macd_hist > 0:
        score += 1.0
    elif macd_hist < 0:
        score -= 1.0

    # Bollinger Band factor
    if bb_pos < 15:
        score += 1.5  # Near lower band = buy
    elif bb_pos > 85:
        score -= 1.5  # Near upper band = sell

    # Trend factor
    if price_vs_sma > 2:
        score += 0.5  # Above SMA = bullish
    elif price_vs_sma < -2:
        score -= 0.5

    # Short-term momentum
    if change_5 > 3:
        score += 0.5
    elif change_5 < -3:
        score -= 0.5

    # Volume confirmation
    if vol_change > 20 and change_5 > 0:
        score += 0.5  # Rising volume + rising price = strong
    elif vol_change > 20 and change_5 < 0:
        score -= 0.5  # Rising volume + falling price = weakness

    # Apply aggression threshold
    thresholds = {"conservative": 3.0, "moderate": 2.0, "aggressive": 1.0}
    threshold = thresholds.get(aggression, 2.0)

    if score >= threshold:
        return 1  # BUY
    elif score <= -threshold:
        return -1  # SELL
    return 0  # HOLD


class PureAI_Strategy(BaseStrategy):
    """
    Pure AI Strategy — lets an LLM reason about market data from first principles.

    When an AI API key is configured (ANTHROPIC_API_KEY or GEMINI_API_KEY),
    the strategy sends technical data to the LLM and asks for a buy/sell/hold decision.

    Without an API key, falls back to a multi-factor scoring model that combines
    RSI, MACD, Bollinger Bands, trend, and volume into a composite signal.
    """

    name = "Pure AI"
    description = "LLM-powered strategy: AI reasons about price action, technicals, and volume to generate trade signals. Falls back to multi-factor scoring without API key."
    category = "ai"

    @classmethod
    def get_params(cls) -> List[StrategyParam]:
        return [
            StrategyParam(
                "aggression", "Trading Aggression", "select", "moderate",
                options=["conservative", "moderate", "aggressive"],
            ),
        ]

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """
        Generate signals using multi-factor scoring (sync version for backtesting).
        The async LLM version is used by the auto-trader via generate_signals_async.
        """
        df = df.copy()
        df["signal"] = 0

        # Need at least 20 bars
        if len(df) < 20:
            return df

        # Run multi-factor scoring on each bar (sliding window)
        for i in range(20, len(df)):
            window = df.iloc[max(0, i - 50):i + 1].copy()
            technicals = _compute_technicals(window)
            df.iloc[i, df.columns.get_loc("signal")] = _fallback_multi_factor(technicals, params)

        return df

    async def generate_signals_async(self, df: pd.DataFrame, params: Dict) -> int:
        """
        Async version for live trading — calls LLM for the latest bar.
        Returns signal for the most recent candle only.
        """
        if len(df) < 20:
            return 0

        technicals = _compute_technicals(df)
        candle_summary = _summarize_recent_candles(df, 10)

        # Try LLM first
        signal = await _ask_llm_for_signal(technicals, candle_summary, params)

        # Fallback to multi-factor
        if signal is None:
            signal = _fallback_multi_factor(technicals, params)

        return signal
