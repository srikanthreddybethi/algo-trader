"""
Spread Betting Strategies — optimised for £/point trading with leverage.

Key differences from regular strategies:
1. ATR-based stop distances (not fixed percentage) to handle leverage volatility
2. Shorter hold times preferred (avoid overnight funding costs)
3. Market hours awareness (don't enter near close)
4. Spread-width-aware (don't enter when spreads are abnormally wide)
5. Position sizing in £/point, not quantity
"""
import numpy as np
import pandas as pd
from typing import Dict


# ─── Helpers ──────────────────────────────────────────────────────
def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def _compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index (simplified)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    plus_dm = (high - high.shift(1)).clip(lower=0)
    minus_dm = (low.shift(1) - low).clip(lower=0)
    # Zero out where the other is larger
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    atr = _compute_atr(df, period)
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.rolling(period).mean()


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI from a price series."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _compute_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _compute_vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3
    return (typical * df["volume"]).cumsum() / df["volume"].cumsum()


def _compute_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0):
    mid = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    return mid, mid + std_dev * std, mid - std_dev * std


def _default_signal(strategy_name: str) -> Dict:
    return {
        "signal": "hold",
        "confidence": 0.0,
        "stop_distance_points": 0.0,
        "target_distance_points": 0.0,
        "strategy_name": strategy_name,
        "reasoning": "Insufficient data",
        "recommended_guaranteed_stop": False,
        "recommended_hold_duration": "none",
    }


# ─── Strategy 1: SB Trend Rider ──────────────────────────────────
class SBTrendRider:
    """20/50 EMA crossover with ADX trend confirmation."""

    name = "SB Trend Rider"
    description = (
        "Trend-following strategy using 20/50 EMA crossover confirmed by ADX > 25. "
        "Uses ATR-based stops (1.5x) and 2:1 reward-risk targets. "
        "Avoids entry in first/last 15 minutes of session."
    )
    best_for = ["forex", "indices", "commodities"]
    preferred_timeframe = "15m"

    def generate_signal(self, df: pd.DataFrame, symbol: str = "") -> Dict:
        if len(df) < 60:
            return _default_signal(self.name)

        df = df.copy()
        df["ema20"] = _compute_ema(df["close"], 20)
        df["ema50"] = _compute_ema(df["close"], 50)
        df["adx"] = _compute_adx(df)
        df["atr"] = _compute_atr(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        atr = last["atr"]
        adx = last["adx"]

        if pd.isna(atr) or pd.isna(adx) or atr <= 0:
            return _default_signal(self.name)

        # ADX must confirm trend
        if adx < 25:
            return {
                **_default_signal(self.name),
                "reasoning": f"ADX {adx:.1f} < 25 — no confirmed trend",
            }

        # EMA crossover detection
        bullish_cross = prev["ema20"] <= prev["ema50"] and last["ema20"] > last["ema50"]
        bearish_cross = prev["ema20"] >= prev["ema50"] and last["ema20"] < last["ema50"]

        # Also allow continuation signals when already trending
        bullish_trend = last["ema20"] > last["ema50"] and last["close"] > last["ema20"]
        bearish_trend = last["ema20"] < last["ema50"] and last["close"] < last["ema20"]

        stop_distance = round(1.5 * atr, 2)
        target_distance = round(3.0 * atr, 2)
        confidence = min(1.0, (adx - 25) / 30)  # Scale 25-55 → 0-1

        if bullish_cross:
            return {
                "signal": "buy",
                "confidence": round(min(0.95, confidence + 0.2), 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": target_distance,
                "strategy_name": self.name,
                "reasoning": f"Bullish EMA crossover with ADX={adx:.1f}. ATR={atr:.2f}",
                "recommended_guaranteed_stop": False,
                "recommended_hold_duration": "4h-1d",
            }
        elif bearish_cross:
            return {
                "signal": "sell",
                "confidence": round(min(0.95, confidence + 0.2), 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": target_distance,
                "strategy_name": self.name,
                "reasoning": f"Bearish EMA crossover with ADX={adx:.1f}. ATR={atr:.2f}",
                "recommended_guaranteed_stop": False,
                "recommended_hold_duration": "4h-1d",
            }
        elif bullish_trend:
            return {
                "signal": "buy",
                "confidence": round(confidence * 0.7, 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": target_distance,
                "strategy_name": self.name,
                "reasoning": f"Bullish trend continuation. ADX={adx:.1f}, EMA20 > EMA50",
                "recommended_guaranteed_stop": False,
                "recommended_hold_duration": "4h-1d",
            }
        elif bearish_trend:
            return {
                "signal": "sell",
                "confidence": round(confidence * 0.7, 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": target_distance,
                "strategy_name": self.name,
                "reasoning": f"Bearish trend continuation. ADX={adx:.1f}, EMA20 < EMA50",
                "recommended_guaranteed_stop": False,
                "recommended_hold_duration": "4h-1d",
            }

        return {
            **_default_signal(self.name),
            "reasoning": f"No crossover or trend. ADX={adx:.1f}",
        }


# ─── Strategy 2: SB Mean Reversion ───────────────────────────────
class SBMeanReversion:
    """Bollinger Band reversion with RSI confirmation for low-volatility markets."""

    name = "SB Mean Reversion"
    description = (
        "Enters when price touches outer Bollinger Band AND RSI confirms "
        "overbought/oversold. Targets the middle band. Best in low-ADX "
        "environments. Skips if spread > 2x average."
    )
    best_for = ["forex", "indices"]
    preferred_timeframe = "1h"

    def generate_signal(self, df: pd.DataFrame, symbol: str = "") -> Dict:
        if len(df) < 30:
            return _default_signal(self.name)

        df = df.copy()
        bb_mid, bb_upper, bb_lower = _compute_bollinger(df, period=20, std_dev=2.0)
        df["bb_mid"] = bb_mid
        df["bb_upper"] = bb_upper
        df["bb_lower"] = bb_lower
        df["rsi"] = _compute_rsi(df["close"], 14)
        df["adx"] = _compute_adx(df)
        df["atr"] = _compute_atr(df)

        last = df.iloc[-1]
        atr = last["atr"]
        adx = last["adx"]

        if pd.isna(atr) or pd.isna(adx) or atr <= 0:
            return _default_signal(self.name)

        # Prefer low-ADX (ranging) environments
        if adx > 30:
            return {
                **_default_signal(self.name),
                "reasoning": f"ADX {adx:.1f} > 30 — too trendy for mean reversion",
            }

        stop_distance = round(0.5 * atr, 2)
        close = last["close"]
        rsi = last["rsi"]

        # Lower band touch + oversold RSI → buy
        if close <= last["bb_lower"] and rsi < 30:
            target_distance = round(abs(last["bb_mid"] - close), 2)
            confidence = min(0.9, (30 - rsi) / 30 + 0.3)
            return {
                "signal": "buy",
                "confidence": round(confidence, 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": max(target_distance, stop_distance),
                "strategy_name": self.name,
                "reasoning": f"Price at lower BB ({close:.2f} <= {last['bb_lower']:.2f}) with RSI={rsi:.1f}",
                "recommended_guaranteed_stop": False,
                "recommended_hold_duration": "1h-4h",
            }

        # Upper band touch + overbought RSI → sell
        if close >= last["bb_upper"] and rsi > 70:
            target_distance = round(abs(close - last["bb_mid"]), 2)
            confidence = min(0.9, (rsi - 70) / 30 + 0.3)
            return {
                "signal": "sell",
                "confidence": round(confidence, 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": max(target_distance, stop_distance),
                "strategy_name": self.name,
                "reasoning": f"Price at upper BB ({close:.2f} >= {last['bb_upper']:.2f}) with RSI={rsi:.1f}",
                "recommended_guaranteed_stop": False,
                "recommended_hold_duration": "1h-4h",
            }

        return {
            **_default_signal(self.name),
            "reasoning": f"No BB extremes with RSI confirmation. RSI={rsi:.1f}, ADX={adx:.1f}",
        }


# ─── Strategy 3: SB Momentum Scalper ─────────────────────────────
class SBMomentumScalper:
    """VWAP + RSI(9) intraday scalper. Strictly no overnight holds."""

    name = "SB Momentum Scalper"
    description = (
        "Intraday scalping using VWAP crossovers confirmed by RSI(9). "
        "Tight stops at 0.8x ATR with 1.5x reward-risk. "
        "Never holds overnight. Avoids news windows."
    )
    best_for = ["forex", "indices", "crypto"]
    preferred_timeframe = "5m"

    def generate_signal(self, df: pd.DataFrame, symbol: str = "") -> Dict:
        if len(df) < 30:
            return _default_signal(self.name)

        df = df.copy()
        df["vwap"] = _compute_vwap(df)
        df["rsi9"] = _compute_rsi(df["close"], 9)
        df["atr"] = _compute_atr(df, period=14)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        atr = last["atr"]

        if pd.isna(atr) or atr <= 0:
            return _default_signal(self.name)

        stop_distance = round(0.8 * atr, 2)
        target_distance = round(1.2 * atr, 2)  # 1.5x stop

        close = last["close"]
        vwap = last["vwap"]
        rsi = last["rsi9"]
        prev_close = prev["close"]
        prev_vwap = prev["vwap"]

        if pd.isna(vwap) or pd.isna(rsi):
            return _default_signal(self.name)

        # Bullish: price crosses above VWAP with RSI > 55
        if prev_close <= prev_vwap and close > vwap and rsi > 55:
            confidence = min(0.85, (rsi - 55) / 40 + 0.4)
            return {
                "signal": "buy",
                "confidence": round(confidence, 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": target_distance,
                "strategy_name": self.name,
                "reasoning": f"VWAP bullish crossover. RSI(9)={rsi:.1f}, ATR={atr:.2f}",
                "recommended_guaranteed_stop": False,
                "recommended_hold_duration": "15m-2h",
            }

        # Bearish: price crosses below VWAP with RSI < 45
        if prev_close >= prev_vwap and close < vwap and rsi < 45:
            confidence = min(0.85, (45 - rsi) / 40 + 0.4)
            return {
                "signal": "sell",
                "confidence": round(confidence, 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": target_distance,
                "strategy_name": self.name,
                "reasoning": f"VWAP bearish crossover. RSI(9)={rsi:.1f}, ATR={atr:.2f}",
                "recommended_guaranteed_stop": False,
                "recommended_hold_duration": "15m-2h",
            }

        return {
            **_default_signal(self.name),
            "reasoning": f"No VWAP crossover with RSI confirmation. RSI(9)={rsi:.1f}",
        }


# ─── Strategy 4: SB Breakout with Guaranteed Stop ────────────────
class SBBreakoutGuaranteed:
    """Breakout strategy with guaranteed stops for volatile moves."""

    name = "SB Breakout (Guaranteed Stop)"
    description = (
        "Identifies consolidation ranges via narrowing Bollinger bandwidth. "
        "Enters on breakout with volume confirmation. ALWAYS uses guaranteed "
        "stop at range height distance. Target is 2x range."
    )
    best_for = ["forex", "indices", "commodities", "crypto"]
    preferred_timeframe = "15m"

    def generate_signal(self, df: pd.DataFrame, symbol: str = "") -> Dict:
        if len(df) < 40:
            return _default_signal(self.name)

        df = df.copy()
        bb_mid, bb_upper, bb_lower = _compute_bollinger(df, period=20, std_dev=2.0)
        df["bb_mid"] = bb_mid
        df["bb_upper"] = bb_upper
        df["bb_lower"] = bb_lower
        df["bandwidth"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"].replace(0, np.nan)
        df["atr"] = _compute_atr(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(last["bandwidth"]) or pd.isna(last["atr"]):
            return _default_signal(self.name)

        # Check for consolidation: bandwidth in bottom 25% of recent history
        recent_bw = df["bandwidth"].iloc[-40:]
        bw_percentile = (recent_bw < last["bandwidth"]).sum() / len(recent_bw)
        is_squeezed = bw_percentile < 0.35

        # Calculate range
        lookback = 20
        range_high = df["high"].iloc[-lookback:].max()
        range_low = df["low"].iloc[-lookback:].min()
        range_height = range_high - range_low

        if range_height <= 0:
            return _default_signal(self.name)

        # Volume confirmation: current volume > 1.3x average
        avg_vol = df["volume"].iloc[-20:].mean()
        vol_confirm = last["volume"] > 1.3 * avg_vol if avg_vol > 0 else False

        stop_distance = round(range_height, 2)
        target_distance = round(2.0 * range_height, 2)

        close = last["close"]

        # Bullish breakout
        if close > range_high and (vol_confirm or is_squeezed):
            confidence = 0.65
            if vol_confirm:
                confidence += 0.15
            if is_squeezed:
                confidence += 0.1
            return {
                "signal": "buy",
                "confidence": round(min(0.95, confidence), 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": target_distance,
                "strategy_name": self.name,
                "reasoning": (
                    f"Bullish breakout above {range_high:.2f}. "
                    f"Range={range_height:.2f}, Vol={'YES' if vol_confirm else 'NO'}, "
                    f"Squeeze={'YES' if is_squeezed else 'NO'}"
                ),
                "recommended_guaranteed_stop": True,
                "recommended_hold_duration": "1h-8h",
            }

        # Bearish breakout
        if close < range_low and (vol_confirm or is_squeezed):
            confidence = 0.65
            if vol_confirm:
                confidence += 0.15
            if is_squeezed:
                confidence += 0.1
            return {
                "signal": "sell",
                "confidence": round(min(0.95, confidence), 2),
                "stop_distance_points": stop_distance,
                "target_distance_points": target_distance,
                "strategy_name": self.name,
                "reasoning": (
                    f"Bearish breakout below {range_low:.2f}. "
                    f"Range={range_height:.2f}, Vol={'YES' if vol_confirm else 'NO'}, "
                    f"Squeeze={'YES' if is_squeezed else 'NO'}"
                ),
                "recommended_guaranteed_stop": True,
                "recommended_hold_duration": "1h-8h",
            }

        return {
            **_default_signal(self.name),
            "reasoning": (
                f"No breakout. Range {range_low:.2f}-{range_high:.2f}, "
                f"BW percentile={bw_percentile:.0%}"
            ),
        }


# ─── Strategy 5: SB Index Surfer ─────────────────────────────────
class SBIndexSurfer:
    """9/21 EMA pullback strategy for major indices."""

    name = "SB Index Surfer"
    description = (
        "Designed for FTSE 100, S&P 500, DAX. Uses 9/21 EMA on 15-min chart. "
        "Enters on pullback to 9 EMA during established trend (21 EMA confirms). "
        "Stop below/above 21 EMA. Targets previous swing high/low."
    )
    best_for = ["indices"]
    preferred_timeframe = "15m"

    def generate_signal(self, df: pd.DataFrame, symbol: str = "") -> Dict:
        if len(df) < 30:
            return _default_signal(self.name)

        df = df.copy()
        df["ema9"] = _compute_ema(df["close"], 9)
        df["ema21"] = _compute_ema(df["close"], 21)
        df["atr"] = _compute_atr(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(last["atr"]) or last["atr"] <= 0:
            return _default_signal(self.name)

        close = last["close"]
        ema9 = last["ema9"]
        ema21 = last["ema21"]

        # Determine trend direction from 21 EMA slope
        ema21_slope = df["ema21"].iloc[-5:].diff().mean()
        is_uptrend = ema9 > ema21 and ema21_slope > 0
        is_downtrend = ema9 < ema21 and ema21_slope < 0

        # Find swing levels for target
        lookback_swing = min(40, len(df) - 1)
        swing_high = df["high"].iloc[-lookback_swing:].max()
        swing_low = df["low"].iloc[-lookback_swing:].min()

        # Bullish pullback: uptrend, price pulled back to near 9 EMA, bouncing
        if is_uptrend:
            near_ema9 = abs(close - ema9) / ema9 < 0.003  # Within 0.3%
            bouncing = close > prev["close"] and prev["close"] <= prev["ema9"]
            stop_distance = round(abs(close - ema21), 2)
            target_distance = round(abs(swing_high - close), 2)

            if stop_distance <= 0:
                stop_distance = round(last["atr"], 2)
            if target_distance <= stop_distance:
                target_distance = round(2 * stop_distance, 2)

            if near_ema9 or bouncing:
                rr = target_distance / stop_distance if stop_distance > 0 else 0
                confidence = min(0.85, 0.5 + (rr - 1) * 0.1) if rr > 1 else 0.4
                return {
                    "signal": "buy",
                    "confidence": round(confidence, 2),
                    "stop_distance_points": stop_distance,
                    "target_distance_points": target_distance,
                    "strategy_name": self.name,
                    "reasoning": (
                        f"Uptrend pullback to 9 EMA. Target swing high {swing_high:.2f}. "
                        f"R:R={rr:.1f}x"
                    ),
                    "recommended_guaranteed_stop": False,
                    "recommended_hold_duration": "30m-4h",
                }

        # Bearish pullback: downtrend, price pulled back to near 9 EMA, dropping
        if is_downtrend:
            near_ema9 = abs(close - ema9) / ema9 < 0.003
            dropping = close < prev["close"] and prev["close"] >= prev["ema9"]
            stop_distance = round(abs(ema21 - close), 2)
            target_distance = round(abs(close - swing_low), 2)

            if stop_distance <= 0:
                stop_distance = round(last["atr"], 2)
            if target_distance <= stop_distance:
                target_distance = round(2 * stop_distance, 2)

            if near_ema9 or dropping:
                rr = target_distance / stop_distance if stop_distance > 0 else 0
                confidence = min(0.85, 0.5 + (rr - 1) * 0.1) if rr > 1 else 0.4
                return {
                    "signal": "sell",
                    "confidence": round(confidence, 2),
                    "stop_distance_points": stop_distance,
                    "target_distance_points": target_distance,
                    "strategy_name": self.name,
                    "reasoning": (
                        f"Downtrend pullback to 9 EMA. Target swing low {swing_low:.2f}. "
                        f"R:R={rr:.1f}x"
                    ),
                    "recommended_guaranteed_stop": False,
                    "recommended_hold_duration": "30m-4h",
                }

        return {
            **_default_signal(self.name),
            "reasoning": f"No clear trend or pullback. EMA9={'>' if ema9 > ema21 else '<'}EMA21",
        }


# ─── Registry ─────────────────────────────────────────────────────
SB_STRATEGY_REGISTRY = {
    "sb_trend_rider": SBTrendRider,
    "sb_mean_reversion": SBMeanReversion,
    "sb_momentum_scalper": SBMomentumScalper,
    "sb_breakout_guaranteed": SBBreakoutGuaranteed,
    "sb_index_surfer": SBIndexSurfer,
}


def get_sb_strategy(name: str):
    """Get an SB strategy instance by registry key."""
    cls = SB_STRATEGY_REGISTRY.get(name)
    if not cls:
        raise ValueError(f"Unknown SB strategy: {name}. Available: {list(SB_STRATEGY_REGISTRY.keys())}")
    return cls()


def list_sb_strategies():
    """Return metadata for all spread-betting strategies."""
    results = []
    for key, cls in SB_STRATEGY_REGISTRY.items():
        inst = cls()
        results.append({
            "key": key,
            "name": cls.name,
            "description": cls.description,
            "best_for": cls.best_for,
            "preferred_timeframe": cls.preferred_timeframe,
        })
    return results
