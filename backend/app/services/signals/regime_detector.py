"""
Market Regime Detector — classifies market conditions using technical data.

Regimes:
- trending_up: Strong bullish trend
- trending_down: Strong bearish trend
- ranging: Sideways, mean-reverting
- volatile: High volatility, no clear direction
- breakout: Potential regime change

Uses: OHLCV data, volatility metrics, moving averages, ADX-like trend strength.
"""
import numpy as np
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def detect_regime(ohlcv_data: List[Dict], lookback: int = 50) -> Dict:
    """
    Analyze OHLCV data and classify the current market regime.

    Returns regime classification with confidence score and supporting metrics.
    """
    if not ohlcv_data or len(ohlcv_data) < 20:
        return {
            "regime": "unknown",
            "confidence": 0,
            "metrics": {},
            "description": "Insufficient data for regime detection",
            "timestamp": datetime.utcnow().isoformat(),
        }

    closes = np.array([c["close"] for c in ohlcv_data[-lookback:]])
    highs = np.array([c["high"] for c in ohlcv_data[-lookback:]])
    lows = np.array([c["low"] for c in ohlcv_data[-lookback:]])
    volumes = np.array([c.get("volume", 0) for c in ohlcv_data[-lookback:]])

    n = len(closes)

    # 1. Trend strength via linear regression slope
    x = np.arange(n)
    slope = np.polyfit(x, closes, 1)[0]
    # Normalize slope as percentage of price
    slope_pct = (slope / closes.mean()) * 100 if closes.mean() > 0 else 0

    # 2. Moving averages
    sma_20 = np.mean(closes[-20:]) if n >= 20 else closes.mean()
    sma_50 = np.mean(closes[-min(50, n):])
    current_price = closes[-1]

    # Price relative to MAs
    price_vs_sma20 = ((current_price - sma_20) / sma_20) * 100 if sma_20 > 0 else 0
    sma_cross = "bullish" if sma_20 > sma_50 else "bearish"

    # 3. Volatility (ATR-like)
    true_ranges = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)

    atr = np.mean(true_ranges[-14:]) if len(true_ranges) >= 14 else np.mean(true_ranges) if true_ranges else 0
    atr_pct = (atr / current_price) * 100 if current_price > 0 else 0

    # Historical volatility (annualized)
    returns = np.diff(np.log(closes))
    volatility = float(np.std(returns) * np.sqrt(252) * 100) if len(returns) > 1 else 0

    # 4. ADX-like trend strength (simplified)
    if n >= 14:
        plus_dm = []
        minus_dm = []
        for i in range(1, n):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            plus_dm.append(max(up_move, 0) if up_move > down_move else 0)
            minus_dm.append(max(down_move, 0) if down_move > up_move else 0)

        # Smoothed DI
        plus_di = np.mean(plus_dm[-14:]) / atr * 100 if atr > 0 else 0
        minus_di = np.mean(minus_dm[-14:]) / atr * 100 if atr > 0 else 0
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
        adx_approx = dx  # Simplified ADX
    else:
        adx_approx = 0
        plus_di = 0
        minus_di = 0

    # 5. Range detection (Bollinger Band width)
    bb_std = np.std(closes[-20:]) if n >= 20 else np.std(closes)
    bb_width = (4 * bb_std / sma_20) * 100 if sma_20 > 0 else 0

    # 6. Volume trend
    if len(volumes) >= 10:
        vol_recent = np.mean(volumes[-5:])
        vol_older = np.mean(volumes[-10:-5])
        vol_change = ((vol_recent - vol_older) / vol_older * 100) if vol_older > 0 else 0
    else:
        vol_change = 0

    # === Regime Classification ===
    regime = "ranging"
    confidence = 0.5
    description = ""

    # Strong trend
    if adx_approx > 25 and abs(slope_pct) > 0.5:
        if slope_pct > 0:
            regime = "trending_up"
            confidence = min(0.95, 0.5 + adx_approx / 100 + abs(slope_pct) / 10)
            description = f"Strong uptrend — price {price_vs_sma20:+.1f}% above 20-MA, ADX≈{adx_approx:.0f}"
        else:
            regime = "trending_down"
            confidence = min(0.95, 0.5 + adx_approx / 100 + abs(slope_pct) / 10)
            description = f"Strong downtrend — price {price_vs_sma20:+.1f}% from 20-MA, ADX≈{adx_approx:.0f}"

    # High volatility, no clear trend
    elif volatility > 60 or atr_pct > 4:
        regime = "volatile"
        confidence = min(0.9, 0.5 + volatility / 200)
        description = f"High volatility ({volatility:.0f}% annualized), ATR {atr_pct:.1f}% of price"

    # Tight range / mean-reverting
    elif bb_width < 8 and abs(slope_pct) < 0.3:
        regime = "ranging"
        confidence = min(0.9, 0.5 + (8 - bb_width) / 16)
        description = f"Tight range — BB width {bb_width:.1f}%, low directional bias"

    # Potential breakout (tightening range + volume spike)
    elif bb_width < 6 and vol_change > 30:
        regime = "breakout"
        confidence = min(0.85, 0.4 + vol_change / 200)
        description = f"Potential breakout — compressed range (BB {bb_width:.1f}%) with {vol_change:.0f}% volume increase"

    # Moderate trend
    elif abs(slope_pct) > 0.2:
        if slope_pct > 0:
            regime = "trending_up"
            confidence = 0.5 + abs(slope_pct) / 5
            description = f"Moderate uptrend — slope {slope_pct:.2f}%/bar"
        else:
            regime = "trending_down"
            confidence = 0.5 + abs(slope_pct) / 5
            description = f"Moderate downtrend — slope {slope_pct:.2f}%/bar"
    else:
        regime = "ranging"
        confidence = 0.6
        description = "Sideways market, no strong directional bias"

    confidence = round(min(confidence, 0.95), 2)

    # Strategy recommendations based on regime
    strategy_map = {
        "trending_up": ["Momentum", "SMA Crossover", "EMA Crossover", "MACD"],
        "trending_down": ["Mean Reversion", "RSI", "DCA", "Grid Trading"],
        "ranging": ["Bollinger Bands", "RSI", "Grid Trading", "Mean Reversion"],
        "volatile": ["DCA", "Grid Trading", "VWAP"],
        "breakout": ["Momentum", "MACD", "Bollinger Bands"],
        "unknown": ["DCA"],
    }

    return {
        "regime": regime,
        "confidence": confidence,
        "description": description,
        "recommended_strategies": strategy_map.get(regime, ["DCA"]),
        "metrics": {
            "slope_pct": round(slope_pct, 3),
            "adx_approx": round(adx_approx, 1),
            "volatility_annual": round(volatility, 1),
            "atr_pct": round(atr_pct, 2),
            "bb_width": round(bb_width, 2),
            "price_vs_sma20": round(price_vs_sma20, 2),
            "sma_cross": sma_cross,
            "volume_change_pct": round(vol_change, 1),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
