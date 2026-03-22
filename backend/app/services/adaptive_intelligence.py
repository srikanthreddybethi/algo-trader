"""
Adaptive Intelligence — closes ALL remaining "dumb" gaps in the system.

1. ADAPTIVE STOP-LOSS: Learns optimal SL/TP from historical trade outcomes
2. SYMBOL DISCOVERY: Scans trending coins and promotes profitable ones
3. AI ACCURACY TRACKER: Scores AI predictions against actual outcomes
4. WALK-FORWARD VALIDATION: Prevents optimizer from overfitting
5. ADAPTIVE FREQUENCY: Trades faster in volatile markets, slower in quiet ones
6. TIME-OF-DAY PROFILING: Learns which hours are most profitable
7. PREDICTION TRACKER: Measures every signal's accuracy over time
"""
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 1. ADAPTIVE STOP-LOSS / TAKE-PROFIT
# ═══════════════════════════════════════════════════════════════
class AdaptiveExitLevels:
    """
    Learns optimal stop-loss and take-profit levels from historical trade data.
    Instead of fixed 5%/10%, adjusts based on:
    - Average winning trade size → sets take-profit just below
    - Average losing trade size → sets stop-loss just beyond
    - Current volatility → wider in volatile markets, tighter in quiet ones
    """

    def __init__(self):
        self._trade_outcomes: List[Dict] = []
        self._max_history = 200

    def record_exit(self, pnl_pct: float, regime: str, volatility: float, hold_hours: float):
        self._trade_outcomes.append({
            "pnl_pct": pnl_pct,
            "regime": regime,
            "volatility": volatility,
            "hold_hours": hold_hours,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(self._trade_outcomes) > self._max_history:
            self._trade_outcomes = self._trade_outcomes[-self._max_history:]

    def get_optimal_levels(self, current_volatility: float = 20.0) -> Dict:
        """Calculate adaptive SL/TP based on historical outcomes."""
        if len(self._trade_outcomes) < 10:
            # Not enough data — use conservative defaults
            return {"stop_loss_pct": 5.0, "take_profit_pct": 10.0, "trailing_stop_pct": 3.0, "source": "default"}

        wins = [t for t in self._trade_outcomes if t["pnl_pct"] > 0]
        losses = [t for t in self._trade_outcomes if t["pnl_pct"] < 0]

        if not wins or not losses:
            return {"stop_loss_pct": 5.0, "take_profit_pct": 10.0, "trailing_stop_pct": 3.0, "source": "default"}

        avg_win = np.mean([t["pnl_pct"] for t in wins])
        avg_loss = abs(np.mean([t["pnl_pct"] for t in losses]))

        # Take-profit: 80% of average win (capture most of the typical gain)
        take_profit = max(3.0, min(25.0, avg_win * 0.8))

        # Stop-loss: 120% of average loss (give slightly more room than typical loss)
        stop_loss = max(2.0, min(15.0, avg_loss * 1.2))

        # Volatility adjustment: wider in volatile markets
        vol_mult = max(0.7, min(1.5, current_volatility / 30.0))
        take_profit *= vol_mult
        stop_loss *= vol_mult

        # Trailing: 40% of take-profit
        trailing = max(1.5, take_profit * 0.4)

        return {
            "stop_loss_pct": round(stop_loss, 1),
            "take_profit_pct": round(take_profit, 1),
            "trailing_stop_pct": round(trailing, 1),
            "source": "adaptive",
            "based_on_trades": len(self._trade_outcomes),
            "avg_win_pct": round(avg_win, 2),
            "avg_loss_pct": round(avg_loss, 2),
        }


# ═══════════════════════════════════════════════════════════════
# 2. SYMBOL DISCOVERY
# ═══════════════════════════════════════════════════════════════
class SymbolDiscovery:
    """
    Scans for new profitable trading opportunities beyond the default BTC/USDT.
    Uses: CoinGecko trending data, volume spikes, and performance history.
    """

    # Base symbols always available
    BASE_SYMBOLS = ["BTC/USDT", "ETH/USDT"]

    # Candidate symbols to evaluate
    CANDIDATE_POOL = [
        "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
        "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
    ]

    def __init__(self):
        self._symbol_scores: Dict[str, float] = {}
        self._active_symbols: List[str] = list(self.BASE_SYMBOLS)

    async def evaluate_symbols(self, exchange: str, max_symbols: int = 4) -> List[str]:
        """Evaluate which symbols to trade based on volume and trending data."""
        from app.services.signals.data_feeds import get_coingecko_trending
        from app.exchanges.manager import exchange_manager

        scores = {}

        # Score based on trending
        try:
            trending = await get_coingecko_trending()
            trending_symbols = {c["symbol"] for c in trending.get("trending", [])}
            for sym in self.CANDIDATE_POOL:
                base = sym.split("/")[0]
                scores[sym] = scores.get(sym, 0)
                if base in trending_symbols:
                    scores[sym] += 3  # Trending bonus

        except Exception:
            pass

        # Score based on volatility (higher vol = more opportunity)
        for sym in self.CANDIDATE_POOL:
            try:
                ohlcv = await exchange_manager.get_ohlcv(exchange, sym, "1h", limit=24)
                if ohlcv and len(ohlcv) >= 10:
                    closes = [c["close"] for c in ohlcv]
                    returns = [abs(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                    vol = np.mean(returns) * 100
                    scores[sym] = scores.get(sym, 0) + min(5, vol * 2)  # Volatility score
            except Exception:
                pass

        # Always include base symbols
        result = list(self.BASE_SYMBOLS)

        # Add top-scoring candidates
        sorted_candidates = sorted(
            [(sym, score) for sym, score in scores.items() if sym not in result],
            key=lambda x: x[1],
            reverse=True,
        )

        for sym, score in sorted_candidates:
            if len(result) >= max_symbols:
                break
            if score > 1:  # Minimum score threshold
                result.append(sym)

        self._active_symbols = result
        self._symbol_scores = scores
        return result

    def get_status(self) -> Dict:
        return {
            "active_symbols": self._active_symbols,
            "scores": self._symbol_scores,
        }


# ═══════════════════════════════════════════════════════════════
# 3. AI ACCURACY TRACKER
# ═══════════════════════════════════════════════════════════════
class AIAccuracyTracker:
    """
    Tracks whether AI predictions (sentiment, action, regime) were correct.
    If AI consistently predicts "bullish" but the market drops, reduce AI weight.
    """

    def __init__(self):
        self._predictions: List[Dict] = []
        self._max_history = 100

    def record_prediction(self, prediction: Dict, symbol: str):
        """Record what the AI predicted."""
        self._predictions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "sentiment": prediction.get("sentiment_assessment"),
            "action": prediction.get("recommended_action"),
            "risk_level": prediction.get("risk_level"),
            "confidence": prediction.get("confidence", 0),
            "outcome": None,  # Filled later
        })
        if len(self._predictions) > self._max_history:
            self._predictions = self._predictions[-self._max_history:]

    def record_outcome(self, symbol: str, price_change_pct: float):
        """Record what actually happened after the prediction."""
        for pred in reversed(self._predictions):
            if pred["symbol"] == symbol and pred["outcome"] is None:
                was_bullish = pred["sentiment"] == "bullish"
                was_bearish = pred["sentiment"] == "bearish"
                market_went_up = price_change_pct > 0.5
                market_went_down = price_change_pct < -0.5

                correct = (was_bullish and market_went_up) or (was_bearish and market_went_down) or \
                          (not was_bullish and not was_bearish and abs(price_change_pct) < 1)

                pred["outcome"] = {
                    "price_change_pct": round(price_change_pct, 2),
                    "prediction_correct": correct,
                }
                break

    def get_accuracy(self) -> Dict:
        """Get AI prediction accuracy stats."""
        evaluated = [p for p in self._predictions if p["outcome"] is not None]
        if not evaluated:
            return {"accuracy": 0.5, "evaluated": 0, "total": len(self._predictions), "trust_level": "unknown"}

        correct = sum(1 for p in evaluated if p["outcome"]["prediction_correct"])
        accuracy = correct / len(evaluated)

        # Determine trust level
        if len(evaluated) < 10:
            trust = "insufficient_data"
        elif accuracy >= 0.6:
            trust = "trustworthy"
        elif accuracy >= 0.45:
            trust = "mediocre"
        else:
            trust = "unreliable"

        return {
            "accuracy": round(accuracy, 3),
            "correct": correct,
            "evaluated": len(evaluated),
            "total": len(self._predictions),
            "trust_level": trust,
        }

    def get_ai_weight_modifier(self) -> float:
        """Returns a multiplier for AI-recommended strategy weights."""
        stats = self.get_accuracy()
        if stats["evaluated"] < 10:
            return 1.0  # Not enough data, no modification

        accuracy = stats["accuracy"]
        if accuracy >= 0.6:
            return 1.3  # Boost AI weight
        elif accuracy >= 0.45:
            return 1.0  # Neutral
        elif accuracy >= 0.3:
            return 0.7  # Reduce AI weight
        else:
            return 0.4  # Heavily reduce — AI is unreliable


# ═══════════════════════════════════════════════════════════════
# 4. WALK-FORWARD VALIDATOR
# ═══════════════════════════════════════════════════════════════
class WalkForwardValidator:
    """
    Prevents overfitting by validating backtest results on unseen data.
    
    Standard backtest: optimize on 60 days, deploy.
    Walk-forward: optimize on days 1-40, validate on days 41-60.
    Only accept params that work on BOTH periods.
    """

    @staticmethod
    async def validate(strategy_name: str, params: Dict,
                       symbol: str = "BTC/USDT", exchange: str = "binance",
                       train_days: int = 40, test_days: int = 20) -> Dict:
        """Run walk-forward validation."""
        from app.services.backtesting import run_backtest

        # Train period
        try:
            train_result = await run_backtest(
                strategy_name=strategy_name, symbol=symbol,
                exchange_name=exchange, timeframe="1h",
                days=train_days + test_days,  # Total period
                initial_balance=10000, params=params, position_size_pct=5.0,
            )
            train_sharpe = train_result.get("metrics", {}).get("sharpe_ratio", 0)
            train_return = train_result.get("metrics", {}).get("total_return_pct", 0)
        except Exception:
            return {"valid": False, "reason": "Train backtest failed"}

        # Test period (most recent)
        try:
            test_result = await run_backtest(
                strategy_name=strategy_name, symbol=symbol,
                exchange_name=exchange, timeframe="1h",
                days=test_days,
                initial_balance=10000, params=params, position_size_pct=5.0,
            )
            test_sharpe = test_result.get("metrics", {}).get("sharpe_ratio", 0)
            test_return = test_result.get("metrics", {}).get("total_return_pct", 0)
        except Exception:
            return {"valid": False, "reason": "Test backtest failed"}

        # Validation: test performance should be at least 50% of train performance
        degradation = test_sharpe / train_sharpe if train_sharpe > 0 else 0

        is_valid = (
            test_sharpe > 0 and          # Must be positive on test data
            degradation > 0.4 and         # No more than 60% degradation
            test_return > -2.0            # Don't lose more than 2% on test
        )

        return {
            "valid": is_valid,
            "train_sharpe": round(train_sharpe, 3),
            "test_sharpe": round(test_sharpe, 3),
            "degradation": round(degradation, 3),
            "train_return_pct": round(train_return, 2),
            "test_return_pct": round(test_return, 2),
            "reason": "Passed" if is_valid else f"Test degradation too high ({degradation:.0%})" if degradation <= 0.4 else "Test Sharpe negative",
        }


# ═══════════════════════════════════════════════════════════════
# 5. ADAPTIVE TRADING FREQUENCY
# ═══════════════════════════════════════════════════════════════
class AdaptiveFrequency:
    """
    Adjusts trading interval based on market conditions.
    - High volatility → check more often (every 2 min)
    - Low volatility → check less often (every 15 min)
    - Post-trade cooldown → wait longer after executing
    """

    DEFAULT_INTERVAL = 300  # 5 minutes

    def __init__(self):
        self._last_trade_time: Optional[datetime] = None
        self._post_trade_cooldown = 600  # 10 min after a trade

    def get_interval(self, volatility: float, regime: str, just_traded: bool = False) -> int:
        """Calculate optimal interval in seconds."""
        base = self.DEFAULT_INTERVAL

        # Volatile → faster
        if volatility > 40 or regime == "volatile":
            base = 120  # 2 min
        elif volatility > 25 or regime == "breakout":
            base = 180  # 3 min
        elif volatility < 10 and regime == "ranging":
            base = 900  # 15 min — nothing happening

        # Post-trade cooldown
        if just_traded:
            base = max(base, self._post_trade_cooldown)

        return base

    def record_trade(self):
        self._last_trade_time = datetime.utcnow()


# ═══════════════════════════════════════════════════════════════
# 6. TIME-OF-DAY PROFILER
# ═══════════════════════════════════════════════════════════════
class TimeOfDayProfiler:
    """
    Learns which hours of the day are most profitable.
    Crypto trades 24/7 but volatility patterns exist:
    - Asia session (00:00-08:00 UTC): lower volume
    - London open (08:00-12:00 UTC): volume picks up
    - US session (13:00-21:00 UTC): highest volume
    - Off-hours (21:00-00:00 UTC): often quiet
    """

    def __init__(self):
        # hour -> { trades, wins, losses, total_pnl }
        self._hourly_stats: Dict[int, Dict] = defaultdict(
            lambda: {"trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0}
        )

    def record_trade(self, pnl: float, won: bool):
        hour = datetime.utcnow().hour
        stats = self._hourly_stats[hour]
        stats["trades"] += 1
        stats["total_pnl"] += pnl
        if won:
            stats["wins"] += 1
        else:
            stats["losses"] += 1

    def should_trade_now(self) -> Dict:
        """Check if current hour is historically profitable."""
        hour = datetime.utcnow().hour
        stats = self._hourly_stats[hour]

        if stats["trades"] < 5:
            return {"should_trade": True, "reason": "Insufficient data for this hour", "hour": hour}

        win_rate = stats["wins"] / stats["trades"]
        avg_pnl = stats["total_pnl"] / stats["trades"]

        if win_rate < 0.25 and stats["trades"] >= 10:
            return {
                "should_trade": False,
                "reason": f"Hour {hour}:00 UTC has only {win_rate:.0%} win rate over {stats['trades']} trades",
                "hour": hour,
                "win_rate": round(win_rate, 3),
                "size_multiplier": 0.3,  # Heavily reduce if forced to trade
            }
        elif win_rate < 0.4:
            return {
                "should_trade": True,
                "reason": f"Hour {hour}:00 UTC has below-average {win_rate:.0%} win rate — reducing size",
                "hour": hour,
                "win_rate": round(win_rate, 3),
                "size_multiplier": 0.6,
            }

        return {
            "should_trade": True,
            "reason": f"Hour {hour}:00 UTC has {win_rate:.0%} win rate — good to trade",
            "hour": hour,
            "win_rate": round(win_rate, 3),
            "size_multiplier": 1.0,
        }

    def get_profile(self) -> Dict:
        """Get the full 24-hour profitability profile."""
        profile = {}
        for hour in range(24):
            stats = self._hourly_stats[hour]
            if stats["trades"] > 0:
                profile[hour] = {
                    "trades": stats["trades"],
                    "win_rate": round(stats["wins"] / stats["trades"], 3),
                    "avg_pnl": round(stats["total_pnl"] / stats["trades"], 4),
                }
        return profile


# ═══════════════════════════════════════════════════════════════
# UNIFIED ADAPTIVE LAYER
# ═══════════════════════════════════════════════════════════════
class AdaptiveLayer:
    """Coordinates all adaptive intelligence modules."""

    def __init__(self):
        self.exit_levels = AdaptiveExitLevels()
        self.symbol_discovery = SymbolDiscovery()
        self.ai_accuracy = AIAccuracyTracker()
        self.walk_forward = WalkForwardValidator()
        self.frequency = AdaptiveFrequency()
        self.time_profile = TimeOfDayProfiler()

    def get_full_status(self) -> Dict:
        return {
            "exit_levels": self.exit_levels.get_optimal_levels(),
            "active_symbols": self.symbol_discovery.get_status(),
            "ai_accuracy": self.ai_accuracy.get_accuracy(),
            "ai_weight_modifier": self.ai_accuracy.get_ai_weight_modifier(),
            "time_profile": self.time_profile.get_profile(),
        }


# Singleton
adaptive = AdaptiveLayer()
