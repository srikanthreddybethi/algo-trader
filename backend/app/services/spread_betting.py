"""
Spread Betting Engine — handles £/point position sizing, margin management,
guaranteed stops, overnight funding costs, spread monitoring, market hours,
gap protection, and tax-efficiency routing.

Spread betting is fundamentally different from quantity-based trading:
- Positions are sized in £/point (GBP per point of price movement)
- Leverage is built-in (3.33% to 20% margin depending on asset class)
- Profits are tax-free in the UK
- Overnight funding costs erode profits on held positions
- Guaranteed stops exist (pay premium for absolute protection)
- Markets have specific trading hours (gaps occur at open/close)
"""

import logging
import math
import re
import statistics
from collections import deque
from datetime import datetime, time, timedelta, timezone

logger = logging.getLogger(__name__)

# ── FCA margin requirements ────────────────────────────────────────────────

MARGIN_RATES: dict[str, float] = {
    "forex_major": 0.0333,   # 3.33% = 30:1
    "forex_minor": 0.05,     # 5% = 20:1
    "indices": 0.05,         # 5% = 20:1
    "commodities": 0.10,     # 10% = 10:1
    "metals": 0.05,          # 5% = 20:1
    "shares_uk": 0.20,       # 20% = 5:1
    "shares_us": 0.20,       # 20% = 5:1
    "crypto": 0.50,          # 50% = 2:1
}

# Approximate LIBOR / SONIA rate for overnight funding calc
_BENCHMARK_RATE = 0.045  # 4.5%
_BROKER_MARKUP = 0.025   # 2.5%

# ── Symbol classification patterns ─────────────────────────────────────────

_FOREX_MAJORS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD",
    "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", "USD_CAD", "NZD_USD",
}

_INDEX_PATTERNS = re.compile(
    r"(?i)(FTSE|DAX|GER40|UK100|US500|US30|SPX|NAS100|CAC40|AUS200|JPN225|"
    r"IX\.D\.|US Tech|S&P|Dow|Nasdaq|Nikkei|STOXX)",
)

_METALS = {"XAUUSD", "XAGUSD", "GOLD", "SILVER", "XAU/USD", "XAG/USD"}

_COMMODITY_PATTERNS = re.compile(
    r"(?i)(OIL|USOIL|UKOIL|BRENT|WTI|NATGAS|WHEAT|CORN|SOYBEAN|SUGAR|"
    r"COFFEE|COTTON|COPPER|PLATINUM|PALLADIUM)",
)

_CRYPTO_PATTERNS = re.compile(
    r"(?i)(BTC|ETH|XRP|LTC|ADA|SOL|DOT|DOGE|AVAX|MATIC|LINK|UNI)",
)

_UK_SHARES = re.compile(
    r"(?i)(\.L$|LSE:|BARC|HSBA|BP\.|SHEL|VOD|RIO|GSK|AZN|ULVR|LLOY)",
)

_US_SHARES = re.compile(
    r"(?i)(AAPL|MSFT|GOOGL|GOOG|AMZN|TSLA|META|NVDA|JPM|V$|MA$|WMT|"
    r"DIS|NFLX|PYPL|INTC|AMD|BA$|GE$|PFE|KO$|PEP)",
)


# ═══════════════════════════════════════════════════════════════════════════
# Class 1: SpreadBetPositionSizer
# ═══════════════════════════════════════════════════════════════════════════


class SpreadBetPositionSizer:
    """Calculate £/point position sizes respecting FCA margin rules."""

    def classify_asset(self, symbol: str) -> str:
        """Classify *symbol* into an FCA margin asset class."""
        sym = symbol.upper().replace(" ", "")
        if sym in _METALS or any(m in sym for m in ("XAU", "XAG", "GOLD", "SILVER")):
            return "metals"
        if _INDEX_PATTERNS.search(sym):
            return "indices"
        if _COMMODITY_PATTERNS.search(sym):
            return "commodities"
        if _CRYPTO_PATTERNS.search(sym):
            return "crypto"
        if _UK_SHARES.search(sym):
            return "shares_uk"
        if _US_SHARES.search(sym):
            return "shares_us"
        # Forex detection — check major pairs first
        normalised = sym.replace("/", "").replace("_", "")
        for pair in _FOREX_MAJORS:
            if normalised == pair.replace("/", "").replace("_", ""):
                return "forex_major"
        # Any remaining 6-char currency-like symbol → minor forex
        if len(normalised) == 6 and normalised.isalpha():
            return "forex_minor"
        # Default
        return "shares_uk"

    def calculate_stake(
        self,
        account_balance: float,
        risk_pct: float,
        stop_distance_points: float,
        asset_class: str | None = None,
        symbol: str = "",
        current_price: float = 0.0,
    ) -> dict:
        """Core formula: stake_per_point = (balance × risk%) / stop_distance.

        Returns sizing details including margin requirements.
        """
        if asset_class is None:
            asset_class = self.classify_asset(symbol) if symbol else "forex_major"

        if stop_distance_points <= 0:
            return {
                "stake_per_point": 0.0,
                "max_loss": 0.0,
                "margin_required": 0.0,
                "leverage_ratio": "N/A",
                "notional_exposure": 0.0,
                "error": "stop_distance_points must be > 0",
            }

        max_risk = account_balance * (risk_pct / 100.0)
        stake_per_point = max_risk / stop_distance_points

        # If we know the current price, clamp by margin
        margin_rate = MARGIN_RATES.get(asset_class, 0.20)
        if current_price > 0:
            notional = stake_per_point * current_price
            margin_required = notional * margin_rate
            # If margin exceeds available balance, scale down
            if margin_required > account_balance * 0.8:
                margin_required = account_balance * 0.8
                notional = margin_required / margin_rate
                stake_per_point = notional / current_price
        else:
            notional = 0.0
            margin_required = 0.0

        leverage = 1.0 / margin_rate if margin_rate > 0 else 1.0
        return {
            "stake_per_point": round(stake_per_point, 2),
            "max_loss": round(stake_per_point * stop_distance_points, 2),
            "margin_required": round(margin_required, 2),
            "leverage_ratio": f"{leverage:.0f}:1",
            "notional_exposure": round(notional, 2),
        }

    def calculate_margin_required(
        self,
        stake_per_point: float,
        current_price: float,
        asset_class: str,
    ) -> dict:
        """Calculate margin for a given stake and price."""
        margin_rate = MARGIN_RATES.get(asset_class, 0.20)
        notional = stake_per_point * current_price
        margin_required = notional * margin_rate
        leverage = 1.0 / margin_rate if margin_rate > 0 else 1.0
        return {
            "margin_required": round(margin_required, 2),
            "margin_pct": round(margin_rate * 100, 2),
            "leverage_ratio": f"{leverage:.0f}:1",
            "notional_value": round(notional, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Class 2: MarginMonitor
# ═══════════════════════════════════════════════════════════════════════════


class MarginMonitor:
    """Track margin utilisation and warn about margin call risk."""

    def __init__(self) -> None:
        self._account_balance: float = 0.0
        self._used_margin: float = 0.0
        self._open_positions: list[dict] = []

    def update_margin(
        self,
        account_balance: float,
        used_margin: float,
        open_positions: list[dict] | None = None,
    ) -> None:
        self._account_balance = account_balance
        self._used_margin = used_margin
        self._open_positions = open_positions or []

    def get_margin_utilisation(self) -> dict:
        available = max(self._account_balance - self._used_margin, 0.0)
        utilisation = (
            (self._used_margin / self._account_balance * 100)
            if self._account_balance > 0
            else 0.0
        )
        if utilisation < 50:
            level = "safe"
        elif utilisation < 75:
            level = "caution"
        elif utilisation < 90:
            level = "danger"
        else:
            level = "critical"
        return {
            "available": round(available, 2),
            "used": round(self._used_margin, 2),
            "utilisation_pct": round(utilisation, 2),
            "warning_level": level,
        }

    def can_open_trade(self, required_margin: float) -> dict:
        available = max(self._account_balance - self._used_margin, 0.0)
        if required_margin <= 0:
            return {"allowed": False, "reason": "Margin requirement must be > 0"}
        if required_margin > available:
            return {
                "allowed": False,
                "reason": (
                    f"Insufficient margin: need £{required_margin:.2f}, "
                    f"available £{available:.2f}"
                ),
            }
        new_util = (self._used_margin + required_margin) / self._account_balance * 100 if self._account_balance > 0 else 100
        if new_util > 90:
            return {
                "allowed": False,
                "reason": f"Would push utilisation to {new_util:.1f}% (>90% critical threshold)",
            }
        return {"allowed": True, "reason": "OK"}

    def check_margin_call_risk(self) -> dict:
        if self._account_balance <= 0:
            return {"at_risk": True, "margin_level_pct": 0.0, "positions_at_risk": []}
        margin_level = (
            (self._account_balance / self._used_margin * 100)
            if self._used_margin > 0
            else 999.0
        )
        at_risk = margin_level < 100
        positions_at_risk = []
        if at_risk:
            # Flag the largest margin consumers
            sorted_pos = sorted(
                self._open_positions,
                key=lambda p: abs(p.get("margin_used", 0)),
                reverse=True,
            )
            positions_at_risk = [
                {"symbol": p.get("symbol", "?"), "margin": p.get("margin_used", 0)}
                for p in sorted_pos[:5]
            ]
        return {
            "at_risk": at_risk,
            "margin_level_pct": round(margin_level, 2),
            "positions_at_risk": positions_at_risk,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Class 3: OvernightFundingCalculator
# ═══════════════════════════════════════════════════════════════════════════


class OvernightFundingCalculator:
    """Model overnight funding costs that erode spread betting profits."""

    def calculate_daily_funding(
        self,
        stake_per_point: float,
        current_price: float,
        asset_class: str,
        direction: str = "buy",
    ) -> dict:
        """Calculate daily overnight funding cost.

        Formula: daily_cost = notional × (benchmark + markup) / 365
        For shorts: funding = notional × (benchmark − markup) / 365
        (shorts may earn credit if benchmark > markup, but rarely in practice)
        """
        notional = stake_per_point * current_price
        if direction.lower() in ("buy", "long"):
            annual_rate = _BENCHMARK_RATE + _BROKER_MARKUP
        else:
            # Shorts: receive benchmark, pay markup — net is usually still a cost
            annual_rate = max(_BROKER_MARKUP - _BENCHMARK_RATE, 0.002)

        daily_cost = abs(notional * annual_rate / 365)
        return {
            "daily_cost": round(daily_cost, 2),
            "annual_rate_pct": round(annual_rate * 100, 2),
            "weekly_cost": round(daily_cost * 7, 2),
        }

    def should_hold_overnight(
        self,
        stake_per_point: float,
        current_price: float,
        expected_daily_return_pct: float,
        asset_class: str,
        direction: str = "buy",
    ) -> dict:
        """Recommend whether to hold a position overnight."""
        funding = self.calculate_daily_funding(
            stake_per_point, current_price, asset_class, direction
        )
        notional = stake_per_point * current_price
        expected_return = notional * (expected_daily_return_pct / 100.0)
        net = expected_return - funding["daily_cost"]
        recommend = net > 0

        if recommend:
            reasoning = (
                f"Expected return £{expected_return:.2f} exceeds funding cost "
                f"£{funding['daily_cost']:.2f} — hold is justified."
            )
        else:
            reasoning = (
                f"Funding cost £{funding['daily_cost']:.2f} exceeds or matches "
                f"expected return £{expected_return:.2f} — consider closing before "
                f"market close to avoid overnight charge."
            )

        return {
            "recommend_hold": recommend,
            "daily_funding_cost": funding["daily_cost"],
            "expected_return": round(expected_return, 2),
            "net_expected": round(net, 2),
            "reasoning": reasoning,
        }

    def calculate_holding_cost(
        self,
        stake: float,
        price: float,
        asset_class: str,
        days: int,
        direction: str = "buy",
    ) -> float:
        """Total cost of holding a position for *days* days."""
        daily = self.calculate_daily_funding(stake, price, asset_class, direction)
        return round(daily["daily_cost"] * days, 2)


# ═══════════════════════════════════════════════════════════════════════════
# Class 4: SpreadMonitor
# ═══════════════════════════════════════════════════════════════════════════


class SpreadMonitor:
    """Track live spread widths and detect abnormal conditions."""

    def __init__(self, window_size: int = 100) -> None:
        self._window_size = window_size
        self._readings: dict[str, deque] = {}

    def record_spread(
        self,
        symbol: str,
        bid: float,
        ask: float,
        timestamp: datetime | None = None,
    ) -> None:
        """Store a spread reading in the rolling window."""
        if symbol not in self._readings:
            self._readings[symbol] = deque(maxlen=self._window_size)
        spread = abs(ask - bid)
        ts = timestamp or datetime.now(timezone.utc)
        self._readings[symbol].append({"spread": spread, "timestamp": ts})

    def get_current_spread(self, symbol: str) -> dict:
        """Return the latest spread and comparison to average."""
        readings = self._readings.get(symbol)
        if not readings:
            return {
                "spread_points": 0.0,
                "spread_pct": 0.0,
                "is_normal": True,
                "vs_average": "no data",
            }
        current = readings[-1]["spread"]
        spreads = [r["spread"] for r in readings]
        avg = statistics.mean(spreads) if len(spreads) > 1 else current
        is_normal = current <= avg * 2.0

        if avg > 0:
            ratio = current / avg
            if ratio < 0.8:
                vs = "tight"
            elif ratio <= 1.2:
                vs = "normal"
            elif ratio <= 2.0:
                vs = "wide"
            else:
                vs = "very wide"
        else:
            vs = "normal"

        return {
            "spread_points": round(current, 6),
            "spread_pct": 0.0,  # needs mid-price context from caller
            "is_normal": is_normal,
            "vs_average": vs,
        }

    def is_spread_acceptable(self, symbol: str, max_multiple: float = 2.0) -> bool:
        """True if current spread <= max_multiple × rolling average."""
        readings = self._readings.get(symbol)
        if not readings or len(readings) < 2:
            return True
        current = readings[-1]["spread"]
        avg = statistics.mean(r["spread"] for r in readings)
        return current <= avg * max_multiple

    def get_spread_stats(self, symbol: str) -> dict:
        """Full spread statistics for a symbol."""
        readings = self._readings.get(symbol)
        if not readings:
            return {"current": 0.0, "average": 0.0, "min": 0.0, "max": 0.0, "std_dev": 0.0}
        spreads = [r["spread"] for r in readings]
        return {
            "current": round(spreads[-1], 6),
            "average": round(statistics.mean(spreads), 6),
            "min": round(min(spreads), 6),
            "max": round(max(spreads), 6),
            "std_dev": round(statistics.stdev(spreads), 6) if len(spreads) >= 2 else 0.0,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Class 5: MarketHoursFilter
# ═══════════════════════════════════════════════════════════════════════════

# Market sessions (UTC): (open_hour, open_min, close_hour, close_min, weekdays)
_MARKET_HOURS: dict[str, dict] = {
    "forex": {
        "open": time(22, 0),   # Sunday 22:00 UTC
        "close": time(22, 0),  # Friday 22:00 UTC
        "open_day": 6,         # Sunday
        "close_day": 4,        # Friday
        "continuous": True,    # 24h during the week
    },
    "lse": {
        "open": time(8, 0),
        "close": time(16, 30),
        "weekdays": (0, 1, 2, 3, 4),
        "continuous": False,
    },
    "nyse": {
        "open": time(14, 30),
        "close": time(21, 0),
        "weekdays": (0, 1, 2, 3, 4),
        "continuous": False,
    },
    "ftse_index": {
        "open": time(8, 0),
        "close": time(16, 30),
        "weekdays": (0, 1, 2, 3, 4),
        "continuous": False,
    },
    "us_index": {
        "open": time(14, 30),
        "close": time(21, 0),
        "weekdays": (0, 1, 2, 3, 4),
        "continuous": False,
    },
    "commodities": {
        "open": time(1, 0),
        "close": time(22, 0),
        "weekdays": (0, 1, 2, 3, 4),
        "continuous": False,
    },
}


class MarketHoursFilter:
    """Determine if markets are open and identify gap risk windows."""

    def _get_session_type(self, symbol: str) -> str:
        """Map symbol to market session type."""
        sym = symbol.upper().replace(" ", "")
        if _UK_SHARES.search(sym):
            return "lse"
        if _US_SHARES.search(sym):
            return "nyse"
        if any(x in sym for x in ("FTSE", "UK100")):
            return "ftse_index"
        if any(x in sym for x in ("SPX", "US500", "US30", "NAS100", "S&P")):
            return "us_index"
        if _COMMODITY_PATTERNS.search(sym) or any(x in sym for x in ("XAU", "XAG")):
            return "commodities"
        # Default to forex (longest hours)
        return "forex"

    def is_market_open(self, symbol: str) -> dict:
        """Check if the market for *symbol* is currently open (UTC)."""
        now = datetime.now(timezone.utc)
        session_type = self._get_session_type(symbol)
        session = _MARKET_HOURS.get(session_type, _MARKET_HOURS["forex"])

        if session.get("continuous"):
            # Forex: open Sun 22:00 – Fri 22:00 UTC
            wd = now.weekday()
            t = now.time()
            if wd == 6 and t >= time(22, 0):
                is_open = True  # Sunday after 22:00
            elif wd == 4 and t >= time(22, 0):
                is_open = False  # Friday after 22:00
            elif wd == 5:
                is_open = False  # Saturday
            elif wd == 6 and t < time(22, 0):
                is_open = False  # Sunday before 22:00
            else:
                is_open = True

            # Next close: Friday 22:00
            days_to_friday = (4 - wd) % 7
            if days_to_friday == 0 and t >= time(22, 0):
                days_to_friday = 7
            next_close = now.replace(
                hour=22, minute=0, second=0, microsecond=0
            ) + timedelta(days=days_to_friday)

            # Next open: Sunday 22:00
            days_to_sunday = (6 - wd) % 7
            if days_to_sunday == 0 and t >= time(22, 0):
                days_to_sunday = 7
            next_open = now.replace(
                hour=22, minute=0, second=0, microsecond=0
            ) + timedelta(days=days_to_sunday)

            minutes_to_close = max(int((next_close - now).total_seconds() / 60), 0) if is_open else 0
        else:
            weekdays = session.get("weekdays", (0, 1, 2, 3, 4))
            wd = now.weekday()
            t = now.time()
            open_t = session["open"]
            close_t = session["close"]

            is_open = wd in weekdays and open_t <= t <= close_t

            # Next close
            if is_open:
                next_close = now.replace(
                    hour=close_t.hour, minute=close_t.minute, second=0, microsecond=0
                )
                minutes_to_close = max(int((next_close - now).total_seconds() / 60), 0)
            else:
                next_close = self._next_occurrence(now, close_t, weekdays)
                minutes_to_close = 0

            next_open = self._next_occurrence(now, open_t, weekdays)
            if is_open:
                # Next open is tomorrow or next weekday
                next_open = self._next_occurrence(
                    now + timedelta(days=1), open_t, weekdays
                )

        return {
            "is_open": is_open,
            "session": session_type,
            "next_open": next_open.isoformat() if not is_open else None,
            "next_close": next_close.isoformat() if is_open else None,
            "minutes_to_close": minutes_to_close,
        }

    @staticmethod
    def _next_occurrence(
        after: datetime, target_time: time, weekdays: tuple
    ) -> datetime:
        """Find the next datetime matching target_time on a valid weekday."""
        candidate = after.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=0,
            microsecond=0,
        )
        if candidate <= after:
            candidate += timedelta(days=1)
        for _ in range(8):
            if candidate.weekday() in weekdays:
                return candidate
            candidate += timedelta(days=1)
        return candidate

    def should_close_before_gap(
        self, symbol: str, minutes_threshold: int = 30
    ) -> dict:
        """Recommend closing if market closes soon and no guaranteed stop."""
        info = self.is_market_open(symbol)
        if not info["is_open"]:
            return {
                "should_close": False,
                "reason": "Market is already closed",
                "minutes_to_close": 0,
            }
        mtc = info["minutes_to_close"]
        if mtc <= minutes_threshold:
            return {
                "should_close": True,
                "reason": (
                    f"Market closes in {mtc} minutes — risk of gap on reopen. "
                    f"Close position or ensure a guaranteed stop is in place."
                ),
                "minutes_to_close": mtc,
            }
        return {
            "should_close": False,
            "reason": f"Market open for another {mtc} minutes",
            "minutes_to_close": mtc,
        }

    def get_optimal_trading_windows(self, symbol: str) -> list[dict]:
        """Return best trading windows (avoid first/last 15 mins, prefer overlaps)."""
        session_type = self._get_session_type(symbol)
        windows = []

        if session_type == "forex":
            windows = [
                {
                    "window": "London Open",
                    "start_utc": "08:15",
                    "end_utc": "11:00",
                    "quality": "high",
                    "reason": "High liquidity, tight spreads",
                },
                {
                    "window": "London/NY Overlap",
                    "start_utc": "14:45",
                    "end_utc": "17:00",
                    "quality": "highest",
                    "reason": "Peak liquidity — London and New York overlap",
                },
                {
                    "window": "NY Session",
                    "start_utc": "14:45",
                    "end_utc": "20:45",
                    "quality": "high",
                    "reason": "Good liquidity, avoid last 15 min",
                },
                {
                    "window": "Tokyo Session",
                    "start_utc": "00:15",
                    "end_utc": "06:45",
                    "quality": "medium",
                    "reason": "Lower volatility, better for range trading",
                },
            ]
        elif session_type in ("lse", "ftse_index"):
            windows = [
                {
                    "window": "Morning",
                    "start_utc": "08:15",
                    "end_utc": "12:00",
                    "quality": "high",
                    "reason": "Post-open momentum, avoid first 15 min",
                },
                {
                    "window": "Afternoon",
                    "start_utc": "13:00",
                    "end_utc": "16:15",
                    "quality": "medium",
                    "reason": "Steady volume, avoid last 15 min",
                },
            ]
        elif session_type in ("nyse", "us_index"):
            windows = [
                {
                    "window": "Opening Hour",
                    "start_utc": "14:45",
                    "end_utc": "16:00",
                    "quality": "high",
                    "reason": "High volume post-open, avoid first 15 min",
                },
                {
                    "window": "Midday",
                    "start_utc": "16:00",
                    "end_utc": "19:00",
                    "quality": "medium",
                    "reason": "Steady, lower volatility",
                },
                {
                    "window": "Power Hour",
                    "start_utc": "19:00",
                    "end_utc": "20:45",
                    "quality": "high",
                    "reason": "Closing momentum, avoid last 15 min",
                },
            ]
        else:
            windows = [
                {
                    "window": "Core Hours",
                    "start_utc": "08:15",
                    "end_utc": "16:15",
                    "quality": "medium",
                    "reason": "Avoid first/last 15 minutes",
                },
            ]
        return windows


# ═══════════════════════════════════════════════════════════════════════════
# Class 6: GapProtectionManager
# ═══════════════════════════════════════════════════════════════════════════


class GapProtectionManager:
    """Assess gap risk and recommend protective actions."""

    def __init__(self) -> None:
        self._market_hours = MarketHoursFilter()

    def assess_gap_risk(
        self, symbol: str, position_direction: str = "buy"
    ) -> dict:
        """Assess the risk of a price gap for an open position.

        Checks: market close proximity, weekend proximity, session type.
        """
        now = datetime.now(timezone.utc)
        hours_info = self._market_hours.is_market_open(symbol)
        reasons: list[str] = []
        risk_level = "low"

        # Check if market is about to close
        if hours_info["is_open"] and hours_info["minutes_to_close"] <= 30:
            reasons.append(f"Market closes in {hours_info['minutes_to_close']} minutes")
            risk_level = "high"
        elif hours_info["is_open"] and hours_info["minutes_to_close"] <= 60:
            reasons.append(f"Market closes in {hours_info['minutes_to_close']} minutes")
            risk_level = _escalate(risk_level, "medium")

        # Weekend risk (Friday afternoon)
        if now.weekday() == 4:
            reasons.append("Friday — weekend gap risk")
            risk_level = _escalate(risk_level, "medium")
            if now.hour >= 19:
                risk_level = _escalate(risk_level, "high")

        # Market already closed
        if not hours_info["is_open"]:
            reasons.append("Market is closed — gap will occur at reopen")
            risk_level = _escalate(risk_level, "high")

        # Determine recommendation
        if risk_level == "high":
            action = "close_position"
        elif risk_level == "medium":
            action = "upgrade_to_guaranteed_stop"
        else:
            action = "hold"

        if not reasons:
            reasons.append("No elevated gap risk detected")

        return {
            "risk_level": risk_level,
            "reasons": reasons,
            "recommended_action": action,
        }


def _escalate(current: str, new: str) -> str:
    """Return the higher of two risk levels."""
    order = {"low": 0, "medium": 1, "high": 2}
    return new if order.get(new, 0) > order.get(current, 0) else current


# ═══════════════════════════════════════════════════════════════════════════
# Class 7: TaxEfficiencyRouter
# ═══════════════════════════════════════════════════════════════════════════

_CGT_RATE = 0.20  # UK Capital Gains Tax rate (higher rate)


class TaxEfficiencyRouter:
    """Route trades to the most tax-efficient venue.

    UK spread betting is tax-free. CFDs allow loss offset against gains.
    Direct stock purchase avoids overnight funding for long holds.
    """

    def recommend_venue(
        self,
        symbol: str,
        direction: str,
        hold_duration_days: int,
        expected_pnl: float,
    ) -> dict:
        """Recommend the optimal trading venue for tax efficiency.

        - Expected profit → spread bet (tax-free)
        - Expected loss → CFD (losses offset CGT)
        - Long hold (>30 days) → consider stock purchase (no funding cost)
        """
        sizer = SpreadBetPositionSizer()
        asset_class = sizer.classify_asset(symbol)

        # Long-term holds on shares — direct purchase avoids overnight funding
        if (
            hold_duration_days > 30
            and asset_class in ("shares_uk", "shares_us")
            and direction.lower() in ("buy", "long")
        ):
            daily_funding = abs(expected_pnl) * 0.0002  # rough estimate
            total_funding = daily_funding * hold_duration_days
            if total_funding > abs(expected_pnl) * 0.05:
                exchange = "trading212" if asset_class == "shares_uk" else "alpaca"
                return {
                    "venue": "stock",
                    "exchange": exchange,
                    "reason": (
                        f"Hold duration {hold_duration_days} days — direct stock "
                        f"purchase avoids ~£{total_funding:.2f} in overnight funding."
                    ),
                    "tax_saving": 0.0,
                }

        if expected_pnl > 0:
            # Profitable trade → spread bet for tax-free gains
            tax_saving = round(expected_pnl * _CGT_RATE, 2)
            # Pick best spread betting exchange
            if asset_class in ("forex_major", "forex_minor"):
                exchange = "ig"
            elif asset_class in ("indices", "commodities", "metals"):
                exchange = "ig"
            elif asset_class in ("shares_uk",):
                exchange = "capital"
            else:
                exchange = "ig"

            return {
                "venue": "spread_bet",
                "exchange": exchange,
                "reason": (
                    f"Expected profit £{expected_pnl:.2f} — spread bet is tax-free, "
                    f"saving ~£{tax_saving:.2f} in CGT."
                ),
                "tax_saving": tax_saving,
            }
        else:
            # Expected loss → CFD so loss can offset gains
            return {
                "venue": "cfd",
                "exchange": "ig",
                "reason": (
                    f"Expected loss £{expected_pnl:.2f} — use CFD so the loss "
                    f"can offset other capital gains for tax purposes."
                ),
                "tax_saving": 0.0,
            }


# ═══════════════════════════════════════════════════════════════════════════
# Composite SpreadBetEngine
# ═══════════════════════════════════════════════════════════════════════════


class SpreadBetEngine:
    """Composite engine exposing all spread-betting sub-engines."""

    def __init__(self) -> None:
        self.sizer = SpreadBetPositionSizer()
        self.margin = MarginMonitor()
        self.funding = OvernightFundingCalculator()
        self.spread_monitor = SpreadMonitor()
        self.market_hours = MarketHoursFilter()
        self.gap_protection = GapProtectionManager()
        self.tax_router = TaxEfficiencyRouter()

    def evaluate_spread_bet(
        self,
        symbol: str,
        direction: str,
        account_balance: float,
        risk_pct: float = 1.0,
        stop_distance: float = 20.0,
        asset_class: str | None = None,
        current_price: float = 0.0,
    ) -> dict:
        """Run ALL checks and return a comprehensive recommendation."""
        warnings: list[str] = []

        # 1. Classify asset
        if asset_class is None:
            asset_class = self.sizer.classify_asset(symbol)

        # 2. Position sizing
        sizing = self.sizer.calculate_stake(
            account_balance=account_balance,
            risk_pct=risk_pct,
            stop_distance_points=stop_distance,
            asset_class=asset_class,
            symbol=symbol,
            current_price=current_price,
        )
        if sizing.get("error"):
            return {
                "approved": False,
                "stake_per_point": 0.0,
                "margin_required": 0.0,
                "guaranteed_stop_recommended": False,
                "max_loss": 0.0,
                "overnight_hold_recommended": False,
                "daily_funding_cost": 0.0,
                "spread_acceptable": False,
                "market_open": False,
                "gap_risk": "high",
                "tax_venue": "spread_bet",
                "warnings": [sizing["error"]],
                "reasoning": sizing["error"],
            }

        stake = sizing["stake_per_point"]
        margin_required = sizing["margin_required"]

        # 3. Margin check
        can_trade = self.margin.can_open_trade(margin_required)
        if not can_trade["allowed"]:
            warnings.append(f"Margin: {can_trade['reason']}")

        # 4. Overnight funding
        funding = self.funding.calculate_daily_funding(
            stake, current_price if current_price > 0 else 100.0, asset_class, direction
        )
        hold_advice = self.funding.should_hold_overnight(
            stake,
            current_price if current_price > 0 else 100.0,
            0.1,  # conservative 0.1% daily expected return
            asset_class,
            direction,
        )

        # 5. Spread check
        spread_ok = self.spread_monitor.is_spread_acceptable(symbol)
        if not spread_ok:
            warnings.append("Spread is abnormally wide — consider waiting")

        # 6. Market hours
        hours = self.market_hours.is_market_open(symbol)
        if not hours["is_open"]:
            warnings.append("Market is currently closed")

        # 7. Gap risk
        gap = self.gap_protection.assess_gap_risk(symbol, direction)
        if gap["risk_level"] in ("medium", "high"):
            warnings.extend(gap["reasons"])

        guaranteed_stop_recommended = gap["risk_level"] in ("medium", "high")
        if guaranteed_stop_recommended:
            warnings.append("Guaranteed stop recommended due to gap risk")

        # 8. Tax routing
        tax = self.tax_router.recommend_venue(
            symbol, direction, hold_duration_days=1, expected_pnl=100.0
        )

        # Overall approval
        approved = (
            can_trade["allowed"]
            and hours["is_open"]
            and spread_ok
            and stake > 0
        )

        # Build reasoning
        parts = [
            f"Asset class: {asset_class} (margin {MARGIN_RATES.get(asset_class, 0.2)*100:.1f}%).",
            f"Stake: £{stake:.2f}/pt, max loss £{sizing['max_loss']:.2f}, "
            f"margin £{margin_required:.2f}.",
            f"Overnight funding: £{funding['daily_cost']:.2f}/day.",
            f"Market {'open' if hours['is_open'] else 'closed'}, gap risk: {gap['risk_level']}.",
            f"Tax venue: {tax['venue']} via {tax['exchange']}.",
        ]
        if warnings:
            parts.append(f"Warnings: {'; '.join(warnings)}")

        return {
            "approved": approved,
            "stake_per_point": stake,
            "margin_required": margin_required,
            "guaranteed_stop_recommended": guaranteed_stop_recommended,
            "max_loss": sizing["max_loss"],
            "overnight_hold_recommended": hold_advice["recommend_hold"],
            "daily_funding_cost": funding["daily_cost"],
            "spread_acceptable": spread_ok,
            "market_open": hours["is_open"],
            "gap_risk": gap["risk_level"],
            "tax_venue": tax["venue"],
            "warnings": warnings,
            "reasoning": " ".join(parts),
        }


# Global singleton
spread_bet_engine = SpreadBetEngine()
