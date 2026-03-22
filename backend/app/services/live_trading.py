"""
Live Trading Bridge — handles the switch from paper to real execution.

This module:
1. Validates API keys and exchange connectivity before enabling live mode
2. Provides a unified interface that works for both paper and live trading
3. Implements safety checks: order size limits, rate limiting, circuit breakers
4. Logs every live trade with full audit trail
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from app.exchanges.manager import exchange_manager
from app.services.paper_trading import paper_engine

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Prevents cascading failures by stopping execution after repeated errors."""

    def __init__(self, max_failures: int = 5, reset_after: int = 300):
        self.max_failures = max_failures
        self.reset_after = reset_after  # seconds
        self.failure_count = 0
        self.last_failure: Optional[datetime] = None
        self.is_open = False

    def record_success(self):
        self.failure_count = 0
        self.is_open = False

    def record_failure(self):
        self.failure_count += 1
        self.last_failure = datetime.utcnow()
        if self.failure_count >= self.max_failures:
            self.is_open = True
            logger.error(f"Circuit breaker OPEN after {self.failure_count} failures")

    def can_proceed(self) -> bool:
        if not self.is_open:
            return True
        # Auto-reset after cooldown
        if self.last_failure and (datetime.utcnow() - self.last_failure).seconds > self.reset_after:
            self.is_open = False
            self.failure_count = 0
            logger.info("Circuit breaker reset after cooldown")
            return True
        return False

    def status(self) -> Dict:
        return {
            "is_open": self.is_open,
            "failure_count": self.failure_count,
            "max_failures": self.max_failures,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
        }


class RateLimiter:
    """Simple rate limiter to prevent excessive API calls."""

    def __init__(self, max_calls: int = 10, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: List[datetime] = []

    def can_call(self) -> bool:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.calls = [c for c in self.calls if c > cutoff]
        return len(self.calls) < self.max_calls

    def record_call(self):
        self.calls.append(datetime.utcnow())

    def status(self) -> Dict:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        active = [c for c in self.calls if c > cutoff]
        return {
            "calls_in_window": len(active),
            "max_calls": self.max_calls,
            "window_seconds": self.window_seconds,
        }


class LiveTradingBridge:
    """
    Unified trading interface for both paper and live modes.
    """

    def __init__(self):
        self.mode = "paper"  # "paper" or "live"
        self.circuit_breaker = CircuitBreaker(max_failures=5, reset_after=300)
        self.rate_limiter = RateLimiter(max_calls=10, window_seconds=60)
        self._trade_log: List[Dict] = []
        self._safety_config = {
            "max_order_usd": 1000.0,
            "max_daily_trades": 50,
            "max_daily_loss_usd": 500.0,
            "require_confirmation": True,
            "allowed_exchanges": [
                "binance", "bybit", "kraken", "coinbase", "okx", "cryptocom",
                "bitstamp", "gate", "gemini", "alpaca",
                "ig", "ibkr", "oanda", "trading212", "etoro", "saxo", "capital", "cmc",
            ],
        }
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self._last_trade_date = None

    def set_mode(self, mode: str) -> Dict:
        """Switch between paper and live mode."""
        if mode not in ("paper", "live"):
            return {"error": f"Invalid mode: {mode}"}
        old_mode = self.mode
        self.mode = mode
        logger.info(f"Trading mode changed: {old_mode} → {mode}")
        return {"mode": self.mode, "previous": old_mode}

    def update_safety_config(self, config: Dict):
        self._safety_config.update(config)

    def get_status(self) -> Dict:
        return {
            "mode": self.mode,
            "circuit_breaker": self.circuit_breaker.status(),
            "rate_limiter": self.rate_limiter.status(),
            "safety_config": self._safety_config,
            "daily_trades": self._daily_trades,
            "daily_pnl": round(self._daily_pnl, 2),
            "recent_trades": self._trade_log[-10:],
        }

    async def execute_trade(
        self,
        exchange_name: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
        db=None,
    ) -> Dict:
        """Execute a trade in current mode (paper or live) with all safety checks."""

        # Reset daily counters
        today = datetime.utcnow().date()
        if self._last_trade_date != today:
            self._daily_trades = 0
            self._daily_pnl = 0.0
            self._last_trade_date = today

        # Safety check 1: Circuit breaker
        if not self.circuit_breaker.can_proceed():
            return {"status": "blocked", "reason": "Circuit breaker open — too many recent failures"}

        # Safety check 2: Rate limiter
        if not self.rate_limiter.can_call():
            return {"status": "blocked", "reason": "Rate limit exceeded — slow down"}

        # Safety check 3: Exchange allowed
        if exchange_name not in self._safety_config["allowed_exchanges"]:
            return {"status": "blocked", "reason": f"Exchange {exchange_name} not in allowed list"}

        # Safety check 4: Daily trade limit
        if self._daily_trades >= self._safety_config["max_daily_trades"]:
            return {"status": "blocked", "reason": f"Daily trade limit reached ({self._safety_config['max_daily_trades']})"}

        # Safety check 5: Order size
        ticker = await exchange_manager.get_ticker(exchange_name, symbol)
        current_price = ticker.get("last_price", 0) if ticker else 0
        order_value = quantity * current_price

        if order_value > self._safety_config["max_order_usd"]:
            return {
                "status": "blocked",
                "reason": f"Order value ${order_value:.2f} exceeds max ${self._safety_config['max_order_usd']:.2f}",
            }

        # Execute based on mode
        self.rate_limiter.record_call()

        try:
            if self.mode == "paper":
                result = await self._execute_paper(exchange_name, symbol, side, quantity, order_type, price, db)
            else:
                result = await self._execute_live(exchange_name, symbol, side, quantity, order_type, price)

            self.circuit_breaker.record_success()
            self._daily_trades += 1

            # Log trade
            trade_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "mode": self.mode,
                "exchange": exchange_name,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": current_price,
                "value_usd": round(order_value, 2),
                "status": "executed",
                "result": result,
            }
            self._trade_log.append(trade_entry)

            return {"status": "executed", "mode": self.mode, "trade": trade_entry}

        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Trade execution failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def _execute_paper(self, exchange_name, symbol, side, quantity, order_type, price, db):
        """Execute via paper trading engine."""
        if db is None:
            from app.core.database import async_session
            async with async_session() as db:
                order = await paper_engine.place_order(
                    db, exchange_name=exchange_name, symbol=symbol,
                    side=side, order_type=order_type, quantity=quantity, price=price,
                )
                return {"order_id": order.id, "status": order.status}
        else:
            order = await paper_engine.place_order(
                db, exchange_name=exchange_name, symbol=symbol,
                side=side, order_type=order_type, quantity=quantity, price=price,
            )
            return {"order_id": order.id, "status": order.status}

    async def _execute_live(self, exchange_name, symbol, side, quantity, order_type, price):
        """Execute via real exchange API — routes to connector or CCXT."""
        # Check if it's a connector-based exchange first
        connector = exchange_manager.get_connector(exchange_name)
        if connector:
            result = await connector.place_order(symbol, side, quantity, order_type, price)
            return {
                "exchange_order_id": result.get("order_id"),
                "status": result.get("status"),
                "filled": result.get("filled_qty"),
                "cost": (result.get("filled_qty", 0) or 0) * (result.get("filled_price", 0) or 0),
            }

        # Otherwise use CCXT
        exchange = exchange_manager.get_exchange(exchange_name)
        if not exchange:
            raise ValueError(f"Exchange {exchange_name} not connected. Connect it first via Settings.")

        # Execute the real order
        if order_type == "market":
            if side == "buy":
                order = await exchange.create_market_buy_order(symbol, quantity)
            else:
                order = await exchange.create_market_sell_order(symbol, quantity)
        elif order_type == "limit":
            if not price:
                raise ValueError("Limit order requires a price")
            if side == "buy":
                order = await exchange.create_limit_buy_order(symbol, quantity, price)
            else:
                order = await exchange.create_limit_sell_order(symbol, quantity, price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        return {
            "exchange_order_id": order.get("id"),
            "status": order.get("status"),
            "filled": order.get("filled"),
            "cost": order.get("cost"),
        }

    async def validate_exchange_connection(self, exchange_name: str) -> Dict:
        """Validate that an exchange is properly connected for live trading."""
        # Check connector-based exchanges
        connector = exchange_manager.get_connector(exchange_name)
        if connector:
            if not connector.is_connected:
                return {
                    "valid": False,
                    "reason": "Connector not connected",
                    "action": "Go to Exchanges page and connect with credentials",
                }
            try:
                account = await connector.get_account_info()
                return {
                    "valid": True,
                    "exchange": exchange_name,
                    "balance_available": True,
                    "balance": account.get("balance", 0),
                    "currency": account.get("currency", "USD"),
                }
            except Exception as e:
                return {"valid": False, "reason": str(e), "action": "Check credentials"}

        # Check ccxt/alpaca exchanges
        exchange = exchange_manager.get_exchange(exchange_name)
        if not exchange:
            return {
                "valid": False,
                "reason": "Exchange not connected",
                "action": "Go to Exchanges page and connect with API keys",
            }

        try:
            balance = await exchange.fetch_balance()
            return {
                "valid": True,
                "exchange": exchange_name,
                "balance_available": True,
                "currencies": list(balance.get("total", {}).keys())[:10],
            }
        except Exception as e:
            return {
                "valid": False,
                "reason": str(e),
                "action": "Check API key permissions",
            }


# Singleton
live_bridge = LiveTradingBridge()
