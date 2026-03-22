"""Base connector interface for all exchange connectors."""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Base interface all non-ccxt connectors must implement.

    Provides abstract methods that each exchange connector must override,
    plus simulated data fallback methods for paper trading mode.
    """

    name: str = "base"
    display_name: str = "Base Connector"
    connector_type: str = "unknown"
    supported_asset_types: list = []
    default_pairs: list = []

    def __init__(self):
        self._connected: bool = False
        self._credentials: dict = {}
        self._session_headers: dict = {}
        self._tokens: dict = {}
        self._is_demo: bool = True
        self._rate_limiter: asyncio.Semaphore | None = None
        self._last_request_time: float = 0.0
        self._logger = logging.getLogger(f"connector.{self.name}")

    @property
    def is_connected(self) -> bool:
        """Whether the connector has an active authenticated session."""
        return self._connected

    @classmethod
    def get_config_fields(cls) -> list:
        """Return the credential fields required by this connector."""
        return [
            {"name": "api_key", "label": "API Key", "type": "text", "required": True},
            {"name": "is_demo", "label": "Demo Account", "type": "boolean", "default": True},
        ]

    # ── Abstract methods ──────────────────────────────────────────────

    @abstractmethod
    async def connect(self, credentials: dict) -> dict:
        """Authenticate and establish a session.

        Returns:
            {"status": "connected"|"error", "message": str, ...}
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the session and clean up resources."""

    @abstractmethod
    async def get_account_info(self) -> dict:
        """Retrieve account balance, margin, and equity."""

    @abstractmethod
    async def get_ticker(self, symbol: str) -> dict:
        """Get current ticker data for *symbol*.

        Returns:
            {"symbol", "last_price", "bid", "ask", "high_24h", "low_24h",
             "volume_24h", "change_pct_24h", "timestamp"}
        """

    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list:
        """Get OHLCV candles.

        Returns:
            List of {"timestamp", "open", "high", "low", "close", "volume"}
        """

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        price: float | None = None,
    ) -> dict:
        """Place an order.

        Returns:
            {"order_id", "status", "filled_qty", "filled_price"}
        """

    @abstractmethod
    async def cancel_order(self, order_id: str) -> dict:
        """Cancel an open order."""

    @abstractmethod
    async def get_positions(self) -> list:
        """Return all open positions."""

    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        """Get order book depth.

        Returns:
            {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        """

    @abstractmethod
    async def search_instruments(self, query: str) -> list:
        """Search for tradeable instruments matching *query*."""

    # ── Rate-limiting helper ──────────────────────────────────────────

    async def _rate_limit(self) -> None:
        """Acquire the rate-limit semaphore if configured."""
        if self._rate_limiter is not None:
            await self._rate_limiter.acquire()

    def _release_rate_limit(self) -> None:
        if self._rate_limiter is not None:
            try:
                self._rate_limiter.release()
            except ValueError:
                pass

    # ── Simulated / fallback data ─────────────────────────────────────

    _SIMULATED_BASE_PRICES: dict[str, float] = {
        "EUR/USD": 1.0850,
        "GBP/USD": 1.2650,
        "USD/JPY": 149.50,
        "AUD/USD": 0.6550,
        "USD/CAD": 1.3580,
        "NZD/USD": 0.6120,
        "USD/CHF": 0.8780,
        "EUR/GBP": 0.8575,
        "AAPL": 178.50,
        "MSFT": 378.90,
        "GOOGL": 141.20,
        "AMZN": 178.30,
        "TSLA": 248.50,
        "SPX500": 5120.0,
        "US30": 38950.0,
        "UK100": 7720.0,
        "GER40": 17450.0,
        "XAUUSD": 2035.0,
        "XAGUSD": 22.85,
        "USOIL": 78.40,
        "UKOIL": 82.10,
        "BTC/USD": 64500.0,
        "ETH/USD": 3450.0,
    }

    def _get_simulated_ticker(self, symbol: str) -> dict:
        """Generate a realistic simulated ticker for paper trading."""
        base = self._SIMULATED_BASE_PRICES.get(symbol, 100.0)
        variation = base * random.uniform(-0.002, 0.002)
        price = round(base + variation, 5)
        spread = base * random.uniform(0.0001, 0.0005)
        bid = round(price - spread / 2, 5)
        ask = round(price + spread / 2, 5)
        return {
            "symbol": symbol,
            "last_price": price,
            "bid": bid,
            "ask": ask,
            "high_24h": round(price * (1 + random.uniform(0.001, 0.015)), 5),
            "low_24h": round(price * (1 - random.uniform(0.001, 0.015)), 5),
            "volume_24h": round(random.uniform(10_000, 500_000), 2),
            "change_pct_24h": round(random.uniform(-2.5, 2.5), 4),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _get_simulated_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list:
        """Generate simulated OHLCV candles."""
        base = self._SIMULATED_BASE_PRICES.get(symbol, 100.0)
        tf_seconds = self._timeframe_to_seconds(timeframe)
        now = time.time()
        candles = []
        price = base
        for i in range(limit):
            ts = now - (limit - i) * tf_seconds
            change = price * random.uniform(-0.005, 0.005)
            o = round(price, 5)
            c = round(price + change, 5)
            h = round(max(o, c) * (1 + random.uniform(0, 0.003)), 5)
            low = round(min(o, c) * (1 - random.uniform(0, 0.003)), 5)
            vol = round(random.uniform(100, 10_000), 2)
            candles.append(
                {
                    "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                    "open": o,
                    "high": h,
                    "low": low,
                    "close": c,
                    "volume": vol,
                }
            )
            price = c
        return candles

    def _get_simulated_order_book(self, symbol: str, limit: int = 20) -> dict:
        """Generate a simulated order book."""
        base = self._SIMULATED_BASE_PRICES.get(symbol, 100.0)
        spread = base * 0.0002
        mid = base
        bids = []
        asks = []
        for i in range(limit):
            bp = round(mid - spread / 2 - i * spread * 0.5, 5)
            ap = round(mid + spread / 2 + i * spread * 0.5, 5)
            bids.append([bp, round(random.uniform(0.1, 50.0), 4)])
            asks.append([ap, round(random.uniform(0.1, 50.0), 4)])
        return {"bids": bids, "asks": asks}

    def _get_simulated_order(
        self, symbol: str, side: str, quantity: float, order_type: str, price: float | None
    ) -> dict:
        """Return a simulated order fill."""
        ticker = self._get_simulated_ticker(symbol)
        fill_price = price if price else (ticker["ask"] if side == "buy" else ticker["bid"])
        return {
            "order_id": f"SIM-{int(time.time() * 1000)}",
            "status": "filled",
            "filled_qty": quantity,
            "filled_price": fill_price,
        }

    def _get_simulated_account(self) -> dict:
        """Return a simulated account state."""
        return {
            "balance": 100_000.00,
            "equity": 100_000.00,
            "margin_used": 0.0,
            "margin_available": 100_000.00,
            "unrealised_pnl": 0.0,
            "currency": "USD",
        }

    @staticmethod
    def _timeframe_to_seconds(tf: str) -> int:
        """Convert a timeframe string like '1h' to seconds."""
        mapping = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
            "1w": 604800,
        }
        return mapping.get(tf, 3600)
