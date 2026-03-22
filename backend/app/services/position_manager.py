"""
Intelligent Position Manager — the missing piece for truly autonomous trading.

Gaps fixed:
1. STOP-LOSS / TAKE-PROFIT: Auto-exits positions at configurable thresholds
2. TRAILING STOP: Locks in profits as price moves favorably
3. POSITION MONITORING: Checks all open positions every cycle and acts
4. LOSING STREAK COOLDOWN: Reduces exposure after consecutive losses
5. TIME-BASED EXITS: Closes stale positions that haven't moved
6. MEMORY PERSISTENCE: Saves intelligence state to disk for restart survival

This runs inside every auto-trader cycle, managing existing positions
independently from new trade signals.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

PERSISTENCE_DIR = Path("/home/user/workspace/algo-trader/backend/data")
PERSISTENCE_DIR.mkdir(parents=True, exist_ok=True)


class PositionManager:
    """Intelligent management of open positions."""

    def __init__(self):
        self.config = {
            "stop_loss_pct": 5.0,       # Close position if down 5%
            "take_profit_pct": 10.0,     # Close position if up 10%
            "trailing_stop_pct": 3.0,    # Trail 3% behind peak
            "max_hold_hours": 168,       # Close after 7 days if no movement
            "stale_threshold_pct": 0.5,  # Consider "no movement" if <0.5% change
        }
        # Track peak prices for trailing stops
        self._peak_prices: Dict[str, float] = {}  # symbol -> highest price since entry

    def update_config(self, new_config: Dict):
        self.config.update(new_config)

    async def check_all_positions(self, positions: List[Dict], exchange: str) -> List[Dict]:
        """
        Check all open positions against exit rules.
        Returns list of exit signals with reasons.
        """
        from app.exchanges.manager import exchange_manager

        exit_signals = []

        for pos in positions:
            if not pos.get("is_open"):
                continue

            symbol = pos["symbol"]
            entry_price = pos.get("avg_entry_price", 0)
            quantity = pos.get("quantity", 0)

            if entry_price <= 0 or quantity <= 0:
                continue

            # Get current price
            try:
                ticker = await exchange_manager.get_ticker(exchange, symbol)
                current_price = ticker.get("last_price", 0) if ticker else 0
            except Exception:
                continue

            if current_price <= 0:
                continue

            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Update peak price for trailing stop
            peak_key = f"{symbol}_{pos.get('id', '')}"
            if peak_key not in self._peak_prices or current_price > self._peak_prices[peak_key]:
                self._peak_prices[peak_key] = current_price

            peak_price = self._peak_prices[peak_key]
            drop_from_peak_pct = ((peak_price - current_price) / peak_price) * 100 if peak_price > 0 else 0

            # Check exit rules
            exit_reason = None

            # Rule 1: Stop-loss
            if pnl_pct <= -self.config["stop_loss_pct"]:
                exit_reason = f"STOP LOSS: position down {pnl_pct:.1f}% (limit: -{self.config['stop_loss_pct']}%)"

            # Rule 2: Take-profit
            elif pnl_pct >= self.config["take_profit_pct"]:
                exit_reason = f"TAKE PROFIT: position up {pnl_pct:.1f}% (target: +{self.config['take_profit_pct']}%)"

            # Rule 3: Trailing stop (only after position is profitable)
            elif pnl_pct > 1.0 and drop_from_peak_pct >= self.config["trailing_stop_pct"]:
                exit_reason = f"TRAILING STOP: dropped {drop_from_peak_pct:.1f}% from peak ${peak_price:.2f} (trail: {self.config['trailing_stop_pct']}%)"

            # Rule 4: Time-based exit (stale positions)
            elif pos.get("opened_at"):
                try:
                    opened = datetime.fromisoformat(str(pos["opened_at"]))
                    hours_held = (datetime.utcnow() - opened).total_seconds() / 3600
                    if hours_held > self.config["max_hold_hours"] and abs(pnl_pct) < self.config["stale_threshold_pct"]:
                        exit_reason = f"STALE EXIT: held {hours_held:.0f}h with only {pnl_pct:+.1f}% movement"
                except Exception:
                    pass

            if exit_reason:
                exit_signals.append({
                    "symbol": symbol,
                    "quantity": quantity,
                    "current_price": current_price,
                    "entry_price": entry_price,
                    "pnl_pct": round(pnl_pct, 2),
                    "reason": exit_reason,
                    "position_id": pos.get("id"),
                })

                # Clean up peak tracking
                if peak_key in self._peak_prices:
                    del self._peak_prices[peak_key]

        return exit_signals

    def get_status(self) -> Dict:
        return {
            "config": self.config,
            "tracked_peaks": len(self._peak_prices),
        }


class LosingStreakDetector:
    """
    Detects losing streaks and reduces exposure to prevent drawdown spirals.
    After N consecutive losses, reduces position sizes and trading frequency.
    """

    def __init__(self):
        self._recent_outcomes: List[bool] = []  # True=win, False=loss
        self._max_history = 20
        self.config = {
            "cooldown_after_losses": 3,       # After 3 consecutive losses
            "cooldown_reduction_pct": 50,      # Reduce position size by 50%
            "severe_cooldown_losses": 5,       # After 5 consecutive losses
            "severe_reduction_pct": 80,        # Reduce by 80%
            "skip_cycles_on_severe": 3,        # Skip N cycles after severe streak
        }
        self._skip_cycles_remaining = 0

    def record_outcome(self, won: bool):
        self._recent_outcomes.append(won)
        if len(self._recent_outcomes) > self._max_history:
            self._recent_outcomes = self._recent_outcomes[-self._max_history:]

        # Check for severe losing streak
        if self._get_consecutive_losses() >= self.config["severe_cooldown_losses"]:
            self._skip_cycles_remaining = self.config["skip_cycles_on_severe"]

    def _get_consecutive_losses(self) -> int:
        count = 0
        for outcome in reversed(self._recent_outcomes):
            if not outcome:
                count += 1
            else:
                break
        return count

    def should_trade(self) -> Dict:
        """Check if the system should trade or cool down."""
        if self._skip_cycles_remaining > 0:
            self._skip_cycles_remaining -= 1
            return {
                "can_trade": False,
                "reason": f"Severe losing streak cooldown — {self._skip_cycles_remaining + 1} cycles remaining",
                "consecutive_losses": self._get_consecutive_losses(),
            }

        consecutive_losses = self._get_consecutive_losses()

        if consecutive_losses >= self.config["severe_cooldown_losses"]:
            return {
                "can_trade": True,
                "size_multiplier": (100 - self.config["severe_reduction_pct"]) / 100,
                "reason": f"Severe streak ({consecutive_losses} losses) — position size at {100 - self.config['severe_reduction_pct']}%",
                "consecutive_losses": consecutive_losses,
            }
        elif consecutive_losses >= self.config["cooldown_after_losses"]:
            return {
                "can_trade": True,
                "size_multiplier": (100 - self.config["cooldown_reduction_pct"]) / 100,
                "reason": f"Losing streak ({consecutive_losses} losses) — position size at {100 - self.config['cooldown_reduction_pct']}%",
                "consecutive_losses": consecutive_losses,
            }

        return {
            "can_trade": True,
            "size_multiplier": 1.0,
            "reason": "Normal trading",
            "consecutive_losses": consecutive_losses,
        }

    def get_stats(self) -> Dict:
        wins = sum(1 for o in self._recent_outcomes if o)
        losses = sum(1 for o in self._recent_outcomes if not o)
        return {
            "total_tracked": len(self._recent_outcomes),
            "wins": wins,
            "losses": losses,
            "consecutive_losses": self._get_consecutive_losses(),
            "skip_cycles_remaining": self._skip_cycles_remaining,
            "win_rate": round(wins / len(self._recent_outcomes), 3) if self._recent_outcomes else 0,
        }


class IntelligencePersistence:
    """
    Saves and loads intelligence state to/from disk so it survives restarts.
    Persists: market memory, scoreboard outcomes, losing streak data.
    """

    MEMORY_FILE = PERSISTENCE_DIR / "market_memory.json"
    SCOREBOARD_FILE = PERSISTENCE_DIR / "scoreboard.json"
    STREAK_FILE = PERSISTENCE_DIR / "streak.json"

    @staticmethod
    def save_memory(memories: List[Dict]):
        try:
            with open(IntelligencePersistence.MEMORY_FILE, "w") as f:
                json.dump(memories, f, default=str)
        except Exception as e:
            logger.warning(f"Failed to persist memory: {e}")

    @staticmethod
    def load_memory() -> List[Dict]:
        try:
            if IntelligencePersistence.MEMORY_FILE.exists():
                with open(IntelligencePersistence.MEMORY_FILE) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
        return []

    @staticmethod
    def save_scoreboard(outcomes: Dict):
        try:
            serializable = {}
            for k, v in outcomes.items():
                serializable[k] = v
            with open(IntelligencePersistence.SCOREBOARD_FILE, "w") as f:
                json.dump(serializable, f, default=str)
        except Exception as e:
            logger.warning(f"Failed to persist scoreboard: {e}")

    @staticmethod
    def load_scoreboard() -> Dict:
        try:
            if IntelligencePersistence.SCOREBOARD_FILE.exists():
                with open(IntelligencePersistence.SCOREBOARD_FILE) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load scoreboard: {e}")
        return {}

    @staticmethod
    def save_streak(outcomes: List[bool]):
        try:
            with open(IntelligencePersistence.STREAK_FILE, "w") as f:
                json.dump(outcomes, f)
        except Exception as e:
            logger.warning(f"Failed to persist streak: {e}")

    @staticmethod
    def load_streak() -> List[bool]:
        try:
            if IntelligencePersistence.STREAK_FILE.exists():
                with open(IntelligencePersistence.STREAK_FILE) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load streak: {e}")
        return []


# Singletons
position_manager = PositionManager()
losing_streak = LosingStreakDetector()
persistence = IntelligencePersistence()

# Load persisted state on import
_loaded_streak = persistence.load_streak()
if _loaded_streak:
    losing_streak._recent_outcomes = _loaded_streak
    logger.info(f"Loaded {len(_loaded_streak)} streak outcomes from disk")

_loaded_memory = persistence.load_memory()
# Will be injected into intelligence.memory on first use
