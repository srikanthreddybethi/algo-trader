"""
Asset-Specific Trading Rules Engine — applies instrument-aware constraints,
strategy selection, and risk parameters per asset class.

Each asset class (crypto, forex, stocks, indices, commodities) has unique
characteristics that affect:
- Which strategies are optimal
- Risk parameters (position sizing, stop distance, max leverage)
- Timing rules (market sessions, earnings windows, weekends)
- Sentiment signals (fear/greed for crypto, VIX for indices, etc.)
- Validation rules (minimum trade size, lot sizing, tick values)

The AssetTradingRouter is the main entry point — it classifies the symbol,
delegates to the correct rules engine, and returns validated recommendations.
"""

import logging
import re
from datetime import datetime, time, timezone
from typing import Any

from app.services.spread_betting import (
    SpreadBetPositionSizer,
    _CRYPTO_PATTERNS,
    _COMMODITY_PATTERNS,
    _INDEX_PATTERNS,
    _UK_SHARES,
    _US_SHARES,
    _FOREX_MAJORS,
    _METALS,
)

logger = logging.getLogger(__name__)

_sizer = SpreadBetPositionSizer()


# ═══════════════════════════════════════════════════════════════════════════
# Class 1: CryptoTradingRules
# ═══════════════════════════════════════════════════════════════════════════


class CryptoTradingRules:
    """Crypto-specific trading logic: fear/greed gates, weekend liquidity
    adjustments, BTC dominance regime filtering, and 24/7 session handling."""

    # Strategies ranked for crypto
    STRATEGY_MAP: dict[str, list[dict]] = {
        "trending_up": [
            {"name": "Momentum", "params": {"lookback": 14, "threshold": 0.03}, "weight": 0.30},
            {"name": "EMA Crossover", "params": {"short_window": 9, "long_window": 21}, "weight": 0.25},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.20},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.15},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.10},
        ],
        "trending_down": [
            {"name": "DCA", "params": {"interval_bars": 12, "amount_pct": 3}, "weight": 0.30},
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 2.5}, "weight": 0.25},
            {"name": "RSI", "params": {"period": 14, "oversold": 25, "overbought": 75}, "weight": 0.20},
            {"name": "Grid Trading", "params": {"grid_size": 12, "grid_spacing": 1.5}, "weight": 0.15},
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.10},
        ],
        "ranging": [
            {"name": "Grid Trading", "params": {"grid_size": 10, "grid_spacing": 1.0}, "weight": 0.30},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.25},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.20},
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.15},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.10},
        ],
        "volatile": [
            {"name": "DCA", "params": {"interval_bars": 6, "amount_pct": 2}, "weight": 0.30},
            {"name": "Grid Trading", "params": {"grid_size": 15, "grid_spacing": 2.0}, "weight": 0.25},
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.20},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 3.0}, "weight": 0.15},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.10},
        ],
        "breakout": [
            {"name": "Momentum", "params": {"lookback": 10, "threshold": 0.04}, "weight": 0.35},
            {"name": "Pure AI", "params": {"aggression": "aggressive"}, "weight": 0.25},
            {"name": "MACD", "params": {"fast": 8, "slow": 21, "signal": 5}, "weight": 0.20},
            {"name": "EMA Crossover", "params": {"short_window": 5, "long_window": 13}, "weight": 0.15},
            {"name": "Bollinger Bands", "params": {"window": 15, "std_dev": 2.0}, "weight": 0.05},
        ],
    }

    def get_risk_params(self, symbol: str, regime: str = "ranging") -> dict:
        """Crypto risk parameters — higher volatility = wider stops."""
        is_major = any(
            tok in symbol.upper()
            for tok in ("BTC", "ETH")
        )
        if is_major:
            base_stop_pct = 3.0
            max_position_pct = 15.0
            max_leverage = 2.0
        else:
            base_stop_pct = 5.0
            max_position_pct = 10.0
            max_leverage = 2.0

        # Volatile regime → widen stops, shrink size
        if regime == "volatile":
            base_stop_pct *= 1.5
            max_position_pct *= 0.6
        elif regime == "breakout":
            base_stop_pct *= 1.2

        return {
            "asset_class": "crypto",
            "stop_loss_pct": round(base_stop_pct, 2),
            "take_profit_pct": round(base_stop_pct * 2.5, 2),
            "trailing_stop_pct": round(base_stop_pct * 0.6, 2),
            "max_position_pct": round(max_position_pct, 2),
            "max_leverage": max_leverage,
            "min_trade_usd": 10.0,
        }

    def validate_trade(self, symbol: str, direction: str, **kwargs: Any) -> dict:
        """Validate a crypto trade against fear/greed, weekend liquidity, etc."""
        warnings: list[str] = []
        allowed = True

        # Fear & Greed gate (check strictest threshold first)
        fear_greed = kwargs.get("fear_greed", 50)
        if fear_greed >= 90 and direction in ("buy", "long"):
            allowed = False
            warnings.append(
                f"Fear/Greed at {fear_greed} — refusing new long. Wait for pullback."
            )
        elif fear_greed >= 85 and direction in ("buy", "long"):
            warnings.append(
                f"Extreme Greed ({fear_greed}) — buying into euphoria is high risk"
            )
        elif fear_greed <= 15 and direction in ("sell", "short"):
            warnings.append(
                f"Extreme Fear ({fear_greed}) — selling into panic may be premature"
            )

        # Weekend liquidity check (Sat/Sun lower volume)
        now = datetime.now(timezone.utc)
        if now.weekday() in (5, 6):
            warnings.append("Weekend trading — expect wider spreads and lower liquidity")
            # Don't block, but flag

        # BTC dominance check (if available)
        btc_dominance = kwargs.get("btc_dominance")
        if btc_dominance is not None:
            sym_upper = symbol.upper()
            if btc_dominance > 60 and "BTC" not in sym_upper:
                warnings.append(
                    f"BTC dominance at {btc_dominance}% — altcoins may underperform"
                )
            elif btc_dominance < 40 and "BTC" in sym_upper:
                warnings.append(
                    f"BTC dominance at {btc_dominance}% — capital rotating to alts"
                )

        # Volatility gate
        volatility = kwargs.get("volatility", 0)
        if volatility > 100:
            warnings.append(
                f"Annualised volatility {volatility:.0f}% — extreme; reduce position size"
            )
            if volatility > 150:
                allowed = False
                warnings.append("Volatility >150% — refusing trade until conditions stabilise")

        return {
            "allowed": allowed,
            "warnings": warnings,
            "size_multiplier": 0.5 if now.weekday() in (5, 6) else 1.0,
        }

    def get_strategies(self, regime: str) -> list[dict]:
        return self.STRATEGY_MAP.get(regime, self.STRATEGY_MAP["ranging"])

    def get_sentiment_factors(self, **kwargs: Any) -> dict:
        """Return crypto-specific sentiment signals."""
        fear_greed = kwargs.get("fear_greed", 50)
        if fear_greed <= 20:
            sentiment = "extreme_fear"
            bias = "contrarian_buy"
        elif fear_greed <= 40:
            sentiment = "fear"
            bias = "cautious_buy"
        elif fear_greed <= 60:
            sentiment = "neutral"
            bias = "neutral"
        elif fear_greed <= 80:
            sentiment = "greed"
            bias = "cautious_sell"
        else:
            sentiment = "extreme_greed"
            bias = "contrarian_sell"

        return {
            "fear_greed": fear_greed,
            "sentiment": sentiment,
            "bias": bias,
            "btc_dominance": kwargs.get("btc_dominance"),
            "funding_rate": kwargs.get("funding_rate"),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Class 2: ForexTradingRules
# ═══════════════════════════════════════════════════════════════════════════


class ForexTradingRules:
    """Forex-specific rules: session-based timing, carry trade logic,
    correlation checks, and retail sentiment contrarian signals."""

    STRATEGY_MAP: dict[str, list[dict]] = {
        "trending_up": [
            {"name": "Momentum", "params": {"lookback": 20, "threshold": 0.015}, "weight": 0.30},
            {"name": "SMA Crossover", "params": {"short_window": 10, "long_window": 30}, "weight": 0.25},
            {"name": "EMA Crossover", "params": {"short_window": 12, "long_window": 26}, "weight": 0.20},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.15},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.10},
        ],
        "trending_down": [
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 1.5}, "weight": 0.25},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.25},
            {"name": "SMA Crossover", "params": {"short_window": 10, "long_window": 30}, "weight": 0.20},
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.15},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.15},
        ],
        "ranging": [
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 1.5}, "weight": 0.30},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.25},
            {"name": "Grid Trading", "params": {"grid_size": 10, "grid_spacing": 0.3}, "weight": 0.20},
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 1.5}, "weight": 0.15},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.10},
        ],
        "volatile": [
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.30},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.5}, "weight": 0.25},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.20},
            {"name": "Grid Trading", "params": {"grid_size": 12, "grid_spacing": 0.5}, "weight": 0.15},
            {"name": "RSI", "params": {"period": 14, "oversold": 25, "overbought": 75}, "weight": 0.10},
        ],
        "breakout": [
            {"name": "Momentum", "params": {"lookback": 14, "threshold": 0.02}, "weight": 0.30},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.25},
            {"name": "Pure AI", "params": {"aggression": "aggressive"}, "weight": 0.20},
            {"name": "EMA Crossover", "params": {"short_window": 8, "long_window": 21}, "weight": 0.15},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.10},
        ],
    }

    # Session quality mapping (UTC hours)
    _SESSIONS = {
        "london_open": (8, 12, "high"),
        "london_ny_overlap": (14, 17, "highest"),
        "ny_session": (14, 21, "high"),
        "tokyo_session": (0, 7, "medium"),
        "dead_zone": (21, 24, "low"),
    }

    def _current_session(self) -> tuple[str, str]:
        """Return (session_name, quality) for the current hour."""
        hour = datetime.now(timezone.utc).hour
        if 14 <= hour < 17:
            return "london_ny_overlap", "highest"
        if 8 <= hour < 12:
            return "london_open", "high"
        if 12 <= hour < 14:
            return "london_afternoon", "medium"
        if 14 <= hour < 21:
            return "ny_session", "high"
        if 0 <= hour < 7:
            return "tokyo_session", "medium"
        return "off_hours", "low"

    def get_risk_params(self, symbol: str, regime: str = "ranging") -> dict:
        norm = symbol.upper().replace("/", "").replace("_", "")
        is_major = any(
            norm == pair.replace("/", "").replace("_", "")
            for pair in _FOREX_MAJORS
        )
        if is_major:
            base_stop_pct = 0.5
            max_position_pct = 20.0
            max_leverage = 30.0
        else:
            base_stop_pct = 0.8
            max_position_pct = 15.0
            max_leverage = 20.0

        if regime == "volatile":
            base_stop_pct *= 1.5
            max_position_pct *= 0.7

        return {
            "asset_class": "forex_major" if is_major else "forex_minor",
            "stop_loss_pct": round(base_stop_pct, 2),
            "take_profit_pct": round(base_stop_pct * 2.0, 2),
            "trailing_stop_pct": round(base_stop_pct * 0.5, 2),
            "max_position_pct": round(max_position_pct, 2),
            "max_leverage": max_leverage,
            "min_trade_usd": 1.0,
        }

    def validate_trade(self, symbol: str, direction: str, **kwargs: Any) -> dict:
        warnings: list[str] = []
        allowed = True

        # Session quality check
        session_name, quality = self._current_session()
        if quality == "low":
            warnings.append(
                f"Trading during {session_name} — low liquidity, wider spreads likely"
            )

        # Weekend check (forex closed Fri 22:00 – Sun 22:00 UTC)
        now = datetime.now(timezone.utc)
        wd = now.weekday()
        if wd == 5 or (wd == 4 and now.hour >= 22) or (wd == 6 and now.hour < 22):
            allowed = False
            warnings.append("Forex market is closed (weekend)")

        # Carry trade check
        carry_direction = kwargs.get("carry_direction")
        if carry_direction and carry_direction != direction:
            warnings.append(
                f"Trading against carry ({carry_direction}) — "
                "overnight funding will work against you"
            )

        # Retail sentiment contrarian signal
        retail_long_pct = kwargs.get("retail_long_pct")
        if retail_long_pct is not None:
            if retail_long_pct > 75 and direction in ("buy", "long"):
                warnings.append(
                    f"Retail {retail_long_pct:.0f}% long — contrarian signal says sell"
                )
            elif retail_long_pct < 25 and direction in ("sell", "short"):
                warnings.append(
                    f"Retail {100-retail_long_pct:.0f}% short — contrarian signal says buy"
                )

        # News/event proximity
        high_impact_event = kwargs.get("high_impact_event", False)
        if high_impact_event:
            warnings.append("High-impact economic event imminent — consider waiting")

        size_mult = 0.7 if quality == "low" else 1.0
        return {"allowed": allowed, "warnings": warnings, "size_multiplier": size_mult}

    def get_strategies(self, regime: str) -> list[dict]:
        return self.STRATEGY_MAP.get(regime, self.STRATEGY_MAP["ranging"])

    def get_sentiment_factors(self, **kwargs: Any) -> dict:
        session_name, quality = self._current_session()
        return {
            "session": session_name,
            "session_quality": quality,
            "retail_long_pct": kwargs.get("retail_long_pct"),
            "carry_direction": kwargs.get("carry_direction"),
            "high_impact_event": kwargs.get("high_impact_event", False),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Class 3: StockTradingRules
# ═══════════════════════════════════════════════════════════════════════════


class StockTradingRules:
    """Stock-specific rules: earnings blackout windows, P/E ratio checks,
    52-week high/low proximity, and sector rotation awareness."""

    STRATEGY_MAP: dict[str, list[dict]] = {
        "trending_up": [
            {"name": "Momentum", "params": {"lookback": 20, "threshold": 0.02}, "weight": 0.30},
            {"name": "SMA Crossover", "params": {"short_window": 10, "long_window": 50}, "weight": 0.25},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.20},
            {"name": "EMA Crossover", "params": {"short_window": 12, "long_window": 26}, "weight": 0.15},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.10},
        ],
        "trending_down": [
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.30},
            {"name": "DCA", "params": {"interval_bars": 24, "amount_pct": 5}, "weight": 0.25},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.20},
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.15},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.10},
        ],
        "ranging": [
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.25},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.25},
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 1.5}, "weight": 0.20},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.15},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.15},
        ],
        "volatile": [
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.30},
            {"name": "DCA", "params": {"interval_bars": 12, "amount_pct": 3}, "weight": 0.25},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.5}, "weight": 0.20},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.15},
            {"name": "RSI", "params": {"period": 14, "oversold": 25, "overbought": 75}, "weight": 0.10},
        ],
        "breakout": [
            {"name": "Momentum", "params": {"lookback": 14, "threshold": 0.025}, "weight": 0.30},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.25},
            {"name": "Pure AI", "params": {"aggression": "aggressive"}, "weight": 0.20},
            {"name": "EMA Crossover", "params": {"short_window": 8, "long_window": 21}, "weight": 0.15},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.10},
        ],
    }

    def get_risk_params(self, symbol: str, regime: str = "ranging") -> dict:
        is_uk = bool(_UK_SHARES.search(symbol.upper()))
        base_stop_pct = 2.0
        max_position_pct = 15.0
        max_leverage = 5.0

        if regime == "volatile":
            base_stop_pct *= 1.4
            max_position_pct *= 0.6

        return {
            "asset_class": "shares_uk" if is_uk else "shares_us",
            "stop_loss_pct": round(base_stop_pct, 2),
            "take_profit_pct": round(base_stop_pct * 2.5, 2),
            "trailing_stop_pct": round(base_stop_pct * 0.5, 2),
            "max_position_pct": round(max_position_pct, 2),
            "max_leverage": max_leverage,
            "min_trade_usd": 50.0,
        }

    def validate_trade(self, symbol: str, direction: str, **kwargs: Any) -> dict:
        warnings: list[str] = []
        allowed = True

        # Market hours check
        now = datetime.now(timezone.utc)
        wd = now.weekday()
        hour = now.hour
        minute = now.minute
        is_uk = bool(_UK_SHARES.search(symbol.upper()))

        if wd >= 5:
            allowed = False
            warnings.append("Stock market is closed (weekend)")
        elif is_uk:
            if not (8 <= hour < 16 or (hour == 16 and minute <= 30)):
                allowed = False
                warnings.append("LSE is closed (hours: 08:00–16:30 UTC)")
        else:
            if not (14 <= hour < 21 or (hour == 14 and minute >= 30)):
                allowed = False
                warnings.append("NYSE is closed (hours: 14:30–21:00 UTC)")

        # Earnings blackout — avoid trading around earnings if flagged
        earnings_within_days = kwargs.get("earnings_within_days")
        if earnings_within_days is not None and earnings_within_days <= 3:
            warnings.append(
                f"Earnings in {earnings_within_days} day(s) — "
                "high volatility expected. Consider waiting."
            )
            if earnings_within_days <= 1:
                allowed = False
                warnings.append("Earnings tomorrow/today — refusing new positions")

        # P/E ratio check
        pe_ratio = kwargs.get("pe_ratio")
        if pe_ratio is not None:
            if pe_ratio > 50 and direction in ("buy", "long"):
                warnings.append(
                    f"P/E ratio {pe_ratio:.1f} — significantly above market average"
                )
            elif pe_ratio < 0:
                warnings.append("Negative P/E (company losing money) — elevated risk")

        # 52-week high/low proximity
        pct_from_52w_high = kwargs.get("pct_from_52w_high")
        if pct_from_52w_high is not None:
            if pct_from_52w_high <= 2 and direction in ("buy", "long"):
                warnings.append(
                    f"Within {pct_from_52w_high:.1f}% of 52-week high — resistance expected"
                )
            elif pct_from_52w_high >= 40 and direction in ("sell", "short"):
                warnings.append(
                    f"{pct_from_52w_high:.1f}% below 52-week high — "
                    "may be near support for a bounce"
                )

        # Sector rotation
        sector_momentum = kwargs.get("sector_momentum")
        if sector_momentum is not None and sector_momentum < -0.5:
            warnings.append(
                f"Sector momentum is negative ({sector_momentum:.2f}) — "
                "sector rotation headwind"
            )

        return {"allowed": allowed, "warnings": warnings, "size_multiplier": 1.0}

    def get_strategies(self, regime: str) -> list[dict]:
        return self.STRATEGY_MAP.get(regime, self.STRATEGY_MAP["ranging"])

    def get_sentiment_factors(self, **kwargs: Any) -> dict:
        return {
            "pe_ratio": kwargs.get("pe_ratio"),
            "pct_from_52w_high": kwargs.get("pct_from_52w_high"),
            "earnings_within_days": kwargs.get("earnings_within_days"),
            "sector_momentum": kwargs.get("sector_momentum"),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Class 4: IndexTradingRules
# ═══════════════════════════════════════════════════════════════════════════


class IndexTradingRules:
    """Index-specific rules: breadth/advance-decline checks, VIX levels,
    gap risk on market open, and session-based timing."""

    STRATEGY_MAP: dict[str, list[dict]] = {
        "trending_up": [
            {"name": "Momentum", "params": {"lookback": 20, "threshold": 0.015}, "weight": 0.30},
            {"name": "SMA Crossover", "params": {"short_window": 10, "long_window": 30}, "weight": 0.25},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.20},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.15},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.10},
        ],
        "trending_down": [
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.25},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.25},
            {"name": "DCA", "params": {"interval_bars": 24, "amount_pct": 5}, "weight": 0.20},
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.20},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.10},
        ],
        "ranging": [
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.25},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.25},
            {"name": "Grid Trading", "params": {"grid_size": 10, "grid_spacing": 0.5}, "weight": 0.20},
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 1.5}, "weight": 0.15},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.15},
        ],
        "volatile": [
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.30},
            {"name": "DCA", "params": {"interval_bars": 12, "amount_pct": 3}, "weight": 0.25},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.5}, "weight": 0.20},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.15},
            {"name": "Grid Trading", "params": {"grid_size": 15, "grid_spacing": 1.0}, "weight": 0.10},
        ],
        "breakout": [
            {"name": "Momentum", "params": {"lookback": 14, "threshold": 0.02}, "weight": 0.30},
            {"name": "Pure AI", "params": {"aggression": "aggressive"}, "weight": 0.25},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.20},
            {"name": "EMA Crossover", "params": {"short_window": 8, "long_window": 21}, "weight": 0.15},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.10},
        ],
    }

    def get_risk_params(self, symbol: str, regime: str = "ranging") -> dict:
        base_stop_pct = 1.5
        max_position_pct = 20.0
        max_leverage = 20.0

        if regime == "volatile":
            base_stop_pct *= 1.5
            max_position_pct *= 0.6

        return {
            "asset_class": "indices",
            "stop_loss_pct": round(base_stop_pct, 2),
            "take_profit_pct": round(base_stop_pct * 2.0, 2),
            "trailing_stop_pct": round(base_stop_pct * 0.5, 2),
            "max_position_pct": round(max_position_pct, 2),
            "max_leverage": max_leverage,
            "min_trade_usd": 100.0,
        }

    def validate_trade(self, symbol: str, direction: str, **kwargs: Any) -> dict:
        warnings: list[str] = []
        allowed = True

        # VIX-based volatility gate
        vix = kwargs.get("vix")
        if vix is not None:
            if vix > 30:
                warnings.append(
                    f"VIX at {vix:.1f} — elevated fear, expect large moves"
                )
                if vix > 40:
                    warnings.append("VIX >40 — extreme volatility, reduce size significantly")
            elif vix < 12:
                warnings.append(
                    f"VIX at {vix:.1f} — complacency; mean-reversion spike possible"
                )

        # Market breadth (advance/decline ratio)
        breadth_ratio = kwargs.get("breadth_ratio")
        if breadth_ratio is not None:
            if breadth_ratio < 0.3 and direction in ("buy", "long"):
                warnings.append(
                    f"Breadth ratio {breadth_ratio:.2f} — broad weakness, "
                    "rally may not be sustainable"
                )
            elif breadth_ratio > 0.8 and direction in ("sell", "short"):
                warnings.append(
                    f"Breadth ratio {breadth_ratio:.2f} — broad strength, "
                    "short may face headwinds"
                )

        # Gap risk on open (first 15 minutes)
        now = datetime.now(timezone.utc)
        hour, minute = now.hour, now.minute
        sym = symbol.upper()
        is_us = any(x in sym for x in ("SPX", "US500", "US30", "NAS100", "S&P", "DOW"))

        if is_us:
            if hour == 14 and 30 <= minute < 45:
                warnings.append(
                    "First 15 minutes after US open — gap risk, wait for price to settle"
                )
        elif any(x in sym for x in ("FTSE", "UK100", "DAX", "GER40")):
            if hour == 8 and minute < 15:
                warnings.append(
                    "First 15 minutes after European open — gap risk"
                )

        # Weekend check
        if now.weekday() >= 5:
            allowed = False
            warnings.append("Index market is closed (weekend)")

        return {"allowed": allowed, "warnings": warnings, "size_multiplier": 1.0}

    def get_strategies(self, regime: str) -> list[dict]:
        return self.STRATEGY_MAP.get(regime, self.STRATEGY_MAP["ranging"])

    def get_sentiment_factors(self, **kwargs: Any) -> dict:
        return {
            "vix": kwargs.get("vix"),
            "breadth_ratio": kwargs.get("breadth_ratio"),
            "put_call_ratio": kwargs.get("put_call_ratio"),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Class 5: CommodityTradingRules
# ═══════════════════════════════════════════════════════════════════════════


class CommodityTradingRules:
    """Commodity-specific rules: seasonal patterns, geopolitical risk premium,
    safe-haven flows (gold), and contango/backwardation detection."""

    STRATEGY_MAP: dict[str, list[dict]] = {
        "trending_up": [
            {"name": "Momentum", "params": {"lookback": 20, "threshold": 0.02}, "weight": 0.30},
            {"name": "SMA Crossover", "params": {"short_window": 10, "long_window": 30}, "weight": 0.25},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.20},
            {"name": "EMA Crossover", "params": {"short_window": 12, "long_window": 26}, "weight": 0.15},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.10},
        ],
        "trending_down": [
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.30},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.25},
            {"name": "DCA", "params": {"interval_bars": 24, "amount_pct": 5}, "weight": 0.20},
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.15},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.10},
        ],
        "ranging": [
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.30},
            {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.25},
            {"name": "Grid Trading", "params": {"grid_size": 10, "grid_spacing": 1.0}, "weight": 0.20},
            {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 1.5}, "weight": 0.15},
            {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.10},
        ],
        "volatile": [
            {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.30},
            {"name": "DCA", "params": {"interval_bars": 12, "amount_pct": 3}, "weight": 0.25},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.5}, "weight": 0.20},
            {"name": "Grid Trading", "params": {"grid_size": 15, "grid_spacing": 1.5}, "weight": 0.15},
            {"name": "VWAP", "params": {"period": 20}, "weight": 0.10},
        ],
        "breakout": [
            {"name": "Momentum", "params": {"lookback": 14, "threshold": 0.03}, "weight": 0.30},
            {"name": "Pure AI", "params": {"aggression": "aggressive"}, "weight": 0.25},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.20},
            {"name": "EMA Crossover", "params": {"short_window": 8, "long_window": 21}, "weight": 0.15},
            {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.10},
        ],
    }

    # Seasonal patterns (month → commodity → bias)
    _SEASONAL: dict[int, dict[str, str]] = {
        # Heating oil / nat gas bullish in winter
        10: {"NATGAS": "bullish", "OIL": "bullish"},
        11: {"NATGAS": "bullish", "OIL": "bullish"},
        12: {"NATGAS": "bullish"},
        1: {"NATGAS": "bullish"},
        # Grains: plant in spring, harvest in autumn
        3: {"WHEAT": "bullish", "CORN": "bullish", "SOYBEAN": "bullish"},
        4: {"WHEAT": "bullish", "CORN": "bullish"},
        9: {"WHEAT": "bearish", "CORN": "bearish", "SOYBEAN": "bearish"},
        10: {"WHEAT": "bearish", "CORN": "bearish"},
        # Gold: Indian wedding season, Chinese New Year
        8: {"GOLD": "bullish", "XAUUSD": "bullish"},
        9: {"GOLD": "bullish", "XAUUSD": "bullish"},
        1: {"GOLD": "bullish", "XAUUSD": "bullish"},
    }

    def _is_safe_haven(self, symbol: str) -> bool:
        sym = symbol.upper()
        return any(x in sym for x in ("GOLD", "XAU", "SILVER", "XAG"))

    def get_risk_params(self, symbol: str, regime: str = "ranging") -> dict:
        is_metal = self._is_safe_haven(symbol)
        if is_metal:
            base_stop_pct = 1.5
            max_position_pct = 18.0
            max_leverage = 20.0
            asset_class = "metals"
        else:
            base_stop_pct = 2.5
            max_position_pct = 12.0
            max_leverage = 10.0
            asset_class = "commodities"

        if regime == "volatile":
            base_stop_pct *= 1.4
            max_position_pct *= 0.6

        return {
            "asset_class": asset_class,
            "stop_loss_pct": round(base_stop_pct, 2),
            "take_profit_pct": round(base_stop_pct * 2.0, 2),
            "trailing_stop_pct": round(base_stop_pct * 0.5, 2),
            "max_position_pct": round(max_position_pct, 2),
            "max_leverage": max_leverage,
            "min_trade_usd": 50.0,
        }

    def validate_trade(self, symbol: str, direction: str, **kwargs: Any) -> dict:
        warnings: list[str] = []
        allowed = True

        # Weekend check
        now = datetime.now(timezone.utc)
        if now.weekday() >= 5:
            allowed = False
            warnings.append("Commodity market is closed (weekend)")

        # Seasonal pattern check
        month = now.month
        sym_upper = symbol.upper()
        monthly_patterns = self._SEASONAL.get(month, {})
        for pattern_key, seasonal_bias in monthly_patterns.items():
            if pattern_key in sym_upper:
                if seasonal_bias == "bearish" and direction in ("buy", "long"):
                    warnings.append(
                        f"Seasonal headwind: {pattern_key} typically bearish in "
                        f"{now.strftime('%B')}"
                    )
                elif seasonal_bias == "bullish" and direction in ("sell", "short"):
                    warnings.append(
                        f"Seasonal tailwind: {pattern_key} typically bullish in "
                        f"{now.strftime('%B')}"
                    )

        # Safe-haven flow check (gold rises in risk-off)
        if self._is_safe_haven(symbol):
            risk_sentiment = kwargs.get("risk_sentiment")
            if risk_sentiment == "risk_on" and direction in ("buy", "long"):
                warnings.append(
                    "Risk-on environment — safe haven demand typically falls"
                )
            elif risk_sentiment == "risk_off" and direction in ("sell", "short"):
                warnings.append(
                    "Risk-off environment — safe haven demand likely to increase"
                )

        # Geopolitical risk premium
        geopolitical_risk = kwargs.get("geopolitical_risk")
        if geopolitical_risk and geopolitical_risk > 0.7:
            if any(x in sym_upper for x in ("OIL", "BRENT", "WTI", "USOIL", "UKOIL")):
                warnings.append(
                    f"Geopolitical risk elevated ({geopolitical_risk:.2f}) — "
                    "oil price may have risk premium"
                )

        # Contango/backwardation
        curve_shape = kwargs.get("curve_shape")
        if curve_shape == "contango" and direction in ("buy", "long"):
            warnings.append(
                "Futures in contango — roll costs will erode long positions"
            )
        elif curve_shape == "backwardation" and direction in ("sell", "short"):
            warnings.append(
                "Futures in backwardation — roll costs work against shorts"
            )

        return {"allowed": allowed, "warnings": warnings, "size_multiplier": 1.0}

    def get_strategies(self, regime: str) -> list[dict]:
        return self.STRATEGY_MAP.get(regime, self.STRATEGY_MAP["ranging"])

    def get_sentiment_factors(self, **kwargs: Any) -> dict:
        now = datetime.now(timezone.utc)
        monthly_patterns = self._SEASONAL.get(now.month, {})
        return {
            "seasonal_patterns": monthly_patterns,
            "geopolitical_risk": kwargs.get("geopolitical_risk"),
            "curve_shape": kwargs.get("curve_shape"),
            "risk_sentiment": kwargs.get("risk_sentiment"),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Class 6: AssetTradingRouter — Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════


class AssetTradingRouter:
    """Routes trading decisions to the correct asset-specific rules engine.

    Usage:
        router = AssetTradingRouter()
        classification = router.classify(symbol)
        validation = router.validate_trade(symbol, "buy", fear_greed=25)
        strategies = router.get_optimal_strategies(symbol, regime="trending_up")
        risk = router.get_risk_params(symbol, regime="volatile")
    """

    RULES_MAP: dict[str, CryptoTradingRules | ForexTradingRules | StockTradingRules | IndexTradingRules | CommodityTradingRules] = {
        "crypto": CryptoTradingRules(),
        "forex_major": ForexTradingRules(),
        "forex_minor": ForexTradingRules(),
        "indices": IndexTradingRules(),
        "shares_uk": StockTradingRules(),
        "shares_us": StockTradingRules(),
        "metals": CommodityTradingRules(),
        "commodities": CommodityTradingRules(),
    }

    def classify(self, symbol: str) -> dict:
        """Classify a symbol into its asset class with metadata."""
        asset_class = _sizer.classify_asset(symbol)

        # Determine the friendly category
        if asset_class in ("forex_major", "forex_minor"):
            category = "forex"
        elif asset_class in ("shares_uk", "shares_us"):
            category = "stocks"
        elif asset_class == "metals":
            category = "commodities"
        else:
            category = asset_class

        # Market type
        market_type = {
            "crypto": "24/7",
            "forex_major": "24/5",
            "forex_minor": "24/5",
            "indices": "exchange_hours",
            "shares_uk": "exchange_hours",
            "shares_us": "exchange_hours",
            "metals": "near_24/5",
            "commodities": "exchange_hours",
        }.get(asset_class, "exchange_hours")

        return {
            "symbol": symbol,
            "asset_class": asset_class,
            "category": category,
            "market_type": market_type,
            "rules_engine": type(self._get_engine(asset_class)).__name__,
        }

    def _get_engine(self, asset_class: str):
        """Get the rules engine for a given asset class."""
        return self.RULES_MAP.get(asset_class, self.RULES_MAP["crypto"])

    def validate_trade(self, symbol: str, direction: str, **kwargs: Any) -> dict:
        """Validate a trade using the appropriate asset-specific rules."""
        asset_class = _sizer.classify_asset(symbol)
        engine = self._get_engine(asset_class)
        result = engine.validate_trade(symbol, direction, **kwargs)
        result["asset_class"] = asset_class
        result["rules_engine"] = type(engine).__name__
        return result

    def get_optimal_strategies(self, symbol: str, regime: str = "ranging") -> dict:
        """Get asset-optimised strategies for the current regime."""
        asset_class = _sizer.classify_asset(symbol)
        engine = self._get_engine(asset_class)
        strategies = engine.get_strategies(regime)
        return {
            "asset_class": asset_class,
            "regime": regime,
            "strategies": strategies,
            "rules_engine": type(engine).__name__,
        }

    def get_risk_params(self, symbol: str, regime: str = "ranging") -> dict:
        """Get asset-specific risk parameters."""
        asset_class = _sizer.classify_asset(symbol)
        engine = self._get_engine(asset_class)
        params = engine.get_risk_params(symbol, regime)
        params["rules_engine"] = type(engine).__name__
        return params

    def get_sentiment_factors(self, symbol: str, **kwargs: Any) -> dict:
        """Get asset-specific sentiment factors."""
        asset_class = _sizer.classify_asset(symbol)
        engine = self._get_engine(asset_class)
        factors = engine.get_sentiment_factors(**kwargs)
        factors["asset_class"] = asset_class
        return factors


# Global singleton
asset_router = AssetTradingRouter()
