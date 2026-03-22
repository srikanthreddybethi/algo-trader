"""
Exchange Manager — unified interface for ALL exchanges:
  • CCXT-based crypto exchanges (binance, bybit, kraken, coinbase, okx, etc.)
  • Non-CCXT connectors (IG, IBKR, OANDA, Trading 212, eToro, Saxo, Capital.com, CMC)
  • Alpaca (stocks + crypto)

The manager routes every call to the correct backend transparently.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import ccxt.async_support as ccxt

from app.exchanges.connectors import ALL_CONNECTORS, BaseConnector

logger = logging.getLogger(__name__)

# ─── Exchange registry ────────────────────────────────────────────────────────

EXCHANGE_CONFIGS: Dict[str, Dict[str, Any]] = {
    # ── CCXT Crypto Exchanges ─────────────────────────────────────────────────
    "binance": {
        "class": ccxt.binance,
        "type": "crypto",
        "category": "crypto",
        "display_name": "Binance",
        "fca_status": "Not FCA regulated",
        "testnet_urls": {"api": "https://testnet.binance.vision/api"},
        "default_pairs": [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
        ],
    },
    "bybit": {
        "class": ccxt.bybit,
        "type": "crypto",
        "category": "crypto",
        "display_name": "Bybit",
        "fca_status": "FCA-approved (via Archax)",
        "testnet_urls": {"api": "https://api-testnet.bybit.com"},
        "default_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"],
    },
    "kraken": {
        "class": ccxt.kraken,
        "type": "crypto",
        "category": "crypto",
        "display_name": "Kraken",
        "fca_status": "FCA-registered + EMI licence",
        "testnet_urls": None,
        "default_pairs": [
            "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "ADA/USD",
            "DOT/USD", "DOGE/USD", "AVAX/USD", "BTC/GBP", "ETH/GBP",
        ],
    },
    "coinbase": {
        "class": ccxt.coinbase,
        "type": "crypto",
        "category": "crypto",
        "display_name": "Coinbase Advanced",
        "fca_status": "FCA-registered",
        "testnet_urls": None,
        "default_pairs": ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "DOGE/USD", "BTC/GBP", "ETH/GBP"],
    },
    "okx": {
        "class": ccxt.okx,
        "type": "crypto",
        "category": "crypto",
        "display_name": "OKX",
        "fca_status": "Operating in UK",
        "testnet_urls": None,
        "default_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "OKB/USDT"],
    },
    "cryptocom": {
        "class": ccxt.cryptocom,
        "type": "crypto",
        "category": "crypto",
        "display_name": "Crypto.com",
        "fca_status": "FCA-registered",
        "testnet_urls": None,
        "default_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "CRO/USDT"],
    },
    "bitstamp": {
        "class": ccxt.bitstamp,
        "type": "crypto",
        "category": "crypto",
        "display_name": "Bitstamp",
        "fca_status": "FCA-registered",
        "testnet_urls": None,
        "default_pairs": ["BTC/USD", "ETH/USD", "XRP/USD", "BTC/GBP", "ETH/GBP"],
    },
    "gate": {
        "class": ccxt.gate,
        "type": "crypto",
        "category": "crypto",
        "display_name": "Gate.io",
        "fca_status": "Operating in UK",
        "testnet_urls": None,
        "default_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT"],
    },
    "gemini": {
        "class": ccxt.gemini,
        "type": "crypto",
        "category": "crypto",
        "display_name": "Gemini",
        "fca_status": "FCA-registered",
        "testnet_urls": None,
        "default_pairs": ["BTC/USD", "ETH/USD", "SOL/USD"],
    },
    # ── Non-CCXT Connectors ───────────────────────────────────────────────────
    "ig": {
        "type": "connector",
        "category": "spread_betting",
        "display_name": "IG Group",
        "fca_status": "FCA-regulated",
        "connector_key": "ig",
        "tax_free": True,
    },
    "ibkr": {
        "type": "connector",
        "category": "multi_asset",
        "display_name": "Interactive Brokers",
        "fca_status": "FCA-regulated",
        "connector_key": "ibkr",
    },
    "oanda": {
        "type": "connector",
        "category": "forex",
        "display_name": "OANDA",
        "fca_status": "FCA-regulated",
        "connector_key": "oanda",
    },
    "trading212": {
        "type": "connector",
        "category": "stocks",
        "display_name": "Trading 212",
        "fca_status": "FCA-regulated",
        "connector_key": "trading212",
    },
    "etoro": {
        "type": "connector",
        "category": "multi_asset",
        "display_name": "eToro",
        "fca_status": "FCA-regulated",
        "connector_key": "etoro",
    },
    "saxo": {
        "type": "connector",
        "category": "multi_asset",
        "display_name": "Saxo Bank",
        "fca_status": "FCA-authorized",
        "connector_key": "saxo",
    },
    "capital": {
        "type": "connector",
        "category": "spread_betting",
        "display_name": "Capital.com",
        "fca_status": "FCA-regulated",
        "connector_key": "capital",
        "tax_free": True,
    },
    "cmc": {
        "type": "connector",
        "category": "spread_betting",
        "display_name": "CMC Markets",
        "fca_status": "FCA-regulated",
        "connector_key": "cmc",
        "tax_free": True,
    },
    # ── Alpaca (stock broker) ─────────────────────────────────────────────────
    "alpaca": {
        "type": "alpaca",
        "category": "stocks",
        "display_name": "Alpaca",
        "fca_status": "US-regulated (FINRA/SIPC)",
        "default_pairs": [
            "AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NVDA",
            "SPY", "QQQ", "BTC/USD", "ETH/USD",
        ],
    },
}


class ExchangeManager:
    """Unified manager that routes calls to ccxt, non-ccxt connectors, or alpaca."""

    def __init__(self):
        # ccxt exchange instances  {name: {instance, type, is_testnet, ...}}
        self._exchanges: Dict[str, Dict[str, Any]] = {}
        # non-ccxt connector instances  {name: BaseConnector}
        self._connectors: Dict[str, BaseConnector] = {}
        # price cache
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 5  # seconds

    # ── helpers ───────────────────────────────────────────────────────────────

    def _exchange_type(self, name: str) -> str:
        """Return 'crypto', 'connector', or 'alpaca'."""
        cfg = EXCHANGE_CONFIGS.get(name)
        return cfg["type"] if cfg else "unknown"

    # ── connection ────────────────────────────────────────────────────────────

    async def connect(
        self,
        name: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        is_testnet: bool = True,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Connect to any exchange by name.

        For ccxt exchanges: pass api_key / api_secret / passphrase.
        For connectors: pass a full *credentials* dict (keys vary per connector).
        """
        if name not in EXCHANGE_CONFIGS:
            raise ValueError(
                f"Unsupported exchange: {name}. "
                f"Supported: {list(EXCHANGE_CONFIGS.keys())}"
            )

        config = EXCHANGE_CONFIGS[name]
        etype = config["type"]

        # ── ccxt crypto exchanges ─────────────────────────────────────
        if etype == "crypto":
            return await self._connect_ccxt(name, config, api_key, api_secret, passphrase, is_testnet)

        # ── non-ccxt connectors ───────────────────────────────────────
        if etype == "connector":
            return await self._connect_connector(name, config, credentials or {}, is_testnet)

        # ── alpaca ────────────────────────────────────────────────────
        if etype == "alpaca":
            return await self._connect_alpaca(name, api_key, api_secret, is_testnet)

        return {"status": "error", "message": f"Unknown exchange type: {etype}"}

    async def _connect_ccxt(
        self, name, config, api_key, api_secret, passphrase, is_testnet
    ) -> Dict[str, Any]:
        exchange_opts: Dict[str, Any] = {
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
        if api_key:
            exchange_opts["apiKey"] = api_key
        if api_secret:
            exchange_opts["secret"] = api_secret
        if passphrase:
            exchange_opts["password"] = passphrase

        exchange = config["class"](exchange_opts)
        if is_testnet and config.get("testnet_urls"):
            exchange.set_sandbox_mode(True)

        try:
            await exchange.load_markets()
            self._exchanges[name] = {
                "instance": exchange,
                "type": config["type"],
                "is_testnet": is_testnet,
                "connected_at": datetime.utcnow(),
                "status": "connected",
            }
            logger.info("Connected to %s (%s)", name, "testnet" if is_testnet else "live")
            return {
                "status": "connected",
                "exchange": name,
                "markets_count": len(exchange.markets),
                "pairs": config.get("default_pairs", []),
            }
        except Exception as e:
            logger.error("Failed to connect to %s: %s", name, e)
            return {"status": "error", "message": str(e)}

    async def _connect_connector(
        self, name, config, credentials, is_testnet
    ) -> Dict[str, Any]:
        connector_key = config["connector_key"]
        connector_cls = ALL_CONNECTORS.get(connector_key)
        if not connector_cls:
            return {"status": "error", "message": f"Connector class not found for {connector_key}"}

        connector = connector_cls()
        # Merge is_demo flag from the top-level param
        creds = {**credentials, "is_demo": credentials.get("is_demo", is_testnet)}
        result = await connector.connect(creds)

        if result.get("status") == "connected":
            self._connectors[name] = connector
            logger.info("Connected connector %s (%s)", name, config["display_name"])

        return {**result, "exchange": name}

    async def _connect_alpaca(self, name, api_key, api_secret, is_testnet) -> Dict[str, Any]:
        # Alpaca is handled externally (import only when needed to avoid hard dep)
        try:
            from alpaca.trading.client import TradingClient

            client = TradingClient(api_key or "", api_secret or "", paper=is_testnet)
            account = client.get_account()
            self._exchanges[name] = {
                "instance": client,
                "type": "alpaca",
                "is_testnet": is_testnet,
                "connected_at": datetime.utcnow(),
                "status": "connected",
            }
            logger.info("Connected to Alpaca (paper=%s)", is_testnet)
            return {
                "status": "connected",
                "exchange": name,
                "equity": str(account.equity),
                "pairs": EXCHANGE_CONFIGS["alpaca"]["default_pairs"],
            }
        except ImportError:
            logger.warning("alpaca-py not installed — Alpaca runs in simulated mode")
            self._exchanges[name] = {
                "instance": None,
                "type": "alpaca",
                "is_testnet": True,
                "connected_at": datetime.utcnow(),
                "status": "connected",
            }
            return {"status": "connected", "exchange": name, "mode": "simulated"}
        except Exception as e:
            logger.error("Alpaca connect error: %s", e)
            return {"status": "error", "message": str(e)}

    # ── disconnection ─────────────────────────────────────────────────────────

    async def disconnect(self, name: str):
        """Disconnect from any exchange."""
        # ccxt / alpaca
        if name in self._exchanges:
            try:
                inst = self._exchanges[name]["instance"]
                if inst and hasattr(inst, "close"):
                    await inst.close()
            except Exception:
                pass
            del self._exchanges[name]
            logger.info("Disconnected ccxt/alpaca: %s", name)

        # connector
        if name in self._connectors:
            try:
                await self._connectors[name].disconnect()
            except Exception:
                pass
            del self._connectors[name]
            logger.info("Disconnected connector: %s", name)

    async def disconnect_all(self):
        for name in list(self._exchanges.keys()) + list(self._connectors.keys()):
            await self.disconnect(name)

    # ── accessors ─────────────────────────────────────────────────────────────

    def get_exchange(self, name: str) -> Optional[Any]:
        """Get a connected ccxt/alpaca exchange instance (or None)."""
        entry = self._exchanges.get(name)
        return entry["instance"] if entry else None

    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """Get a connected non-ccxt connector instance (or None)."""
        return self._connectors.get(name)

    def is_connected(self, name: str) -> bool:
        if name in self._exchanges:
            return True
        conn = self._connectors.get(name)
        return conn.is_connected if conn else False

    # ── status ────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Status of ALL exchanges (connected or not)."""
        result: Dict[str, Any] = {}
        for name, config in EXCHANGE_CONFIGS.items():
            base = {
                "type": config["type"],
                "category": config.get("category", config["type"]),
                "display_name": config.get("display_name", name),
                "fca_status": config.get("fca_status", ""),
                "tax_free": config.get("tax_free", False),
            }
            if name in self._exchanges:
                entry = self._exchanges[name]
                base.update({
                    "status": "connected",
                    "is_testnet": entry.get("is_testnet", True),
                    "connected_at": entry["connected_at"].isoformat(),
                })
            elif name in self._connectors:
                conn = self._connectors[name]
                base.update({
                    "status": "connected" if conn.is_connected else "disconnected",
                    "is_testnet": conn._is_demo,
                    "connector_type": conn.connector_type,
                    "supported_asset_types": conn.supported_asset_types,
                })
            else:
                base["status"] = "disconnected"
            result[name] = base
        return result

    def get_supported_exchanges(self) -> List[Dict[str, Any]]:
        """Return full metadata for every exchange (for the UI)."""
        result = []
        for name, config in EXCHANGE_CONFIGS.items():
            entry: Dict[str, Any] = {
                "name": name,
                "type": config["type"],
                "category": config.get("category", config["type"]),
                "display_name": config.get("display_name", name),
                "fca_status": config.get("fca_status", ""),
                "tax_free": config.get("tax_free", False),
                "has_testnet": config.get("testnet_urls") is not None if config["type"] == "crypto" else True,
                "status": "disconnected",
            }

            # default pairs
            if config["type"] == "connector":
                connector_key = config.get("connector_key", "")
                cls = ALL_CONNECTORS.get(connector_key)
                if cls:
                    entry["default_pairs"] = cls.default_pairs
                    entry["supported_asset_types"] = cls.supported_asset_types
                    entry["config_fields"] = cls.get_config_fields()
            else:
                entry["default_pairs"] = config.get("default_pairs", [])

            # live status
            if name in self._exchanges:
                entry["status"] = "connected"
            elif name in self._connectors and self._connectors[name].is_connected:
                entry["status"] = "connected"

            result.append(entry)
        return result

    def get_config_fields(self, name: str) -> List[Dict]:
        """Return the credential fields required for a given exchange."""
        config = EXCHANGE_CONFIGS.get(name)
        if not config:
            return []
        if config["type"] == "connector":
            cls = ALL_CONNECTORS.get(config.get("connector_key", ""))
            return cls.get_config_fields() if cls else []
        if config["type"] == "crypto":
            fields = [
                {"name": "api_key", "label": "API Key", "type": "text", "required": False},
                {"name": "api_secret", "label": "API Secret", "type": "password", "required": False},
            ]
            if name in ("coinbase", "okx"):
                fields.append({"name": "passphrase", "label": "Passphrase", "type": "password", "required": False})
            fields.append({"name": "is_testnet", "label": "Testnet / Paper", "type": "boolean", "default": True})
            return fields
        if config["type"] == "alpaca":
            return [
                {"name": "api_key", "label": "API Key", "type": "text", "required": True},
                {"name": "api_secret", "label": "API Secret", "type": "password", "required": True},
                {"name": "is_testnet", "label": "Paper Trading", "type": "boolean", "default": True},
            ]
        return []

    def get_default_pairs(self, name: str) -> List[str]:
        """Return default trading pairs for an exchange."""
        config = EXCHANGE_CONFIGS.get(name)
        if not config:
            return []
        if config["type"] == "connector":
            cls = ALL_CONNECTORS.get(config.get("connector_key", ""))
            return cls.default_pairs if cls else []
        return config.get("default_pairs", [])

    # ── market data ───────────────────────────────────────────────────────────

    async def get_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict]:
        """Get ticker — routes to ccxt or connector transparently."""
        # ── connector route ───────────────────────────────────────────
        connector = self.get_connector(exchange_name)
        if connector:
            try:
                ticker = await connector.get_ticker(symbol)
                ticker["exchange"] = exchange_name
                return ticker
            except Exception as e:
                logger.error("Connector ticker error (%s/%s): %s", exchange_name, symbol, e)
                return await self._get_simulated_ticker(exchange_name, symbol)

        # ── ccxt route ────────────────────────────────────────────────
        exchange = self.get_exchange(exchange_name)
        if not exchange or (isinstance(exchange, dict) and exchange is None):
            return await self._get_simulated_ticker(exchange_name, symbol)

        # Alpaca instance isn't a ccxt exchange — use simulated for now
        entry = self._exchanges.get(exchange_name, {})
        if entry.get("type") == "alpaca":
            return await self._get_simulated_ticker(exchange_name, symbol)

        try:
            ticker = await exchange.fetch_ticker(symbol)
            result = {
                "symbol": symbol,
                "exchange": exchange_name,
                "last_price": ticker.get("last", 0),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high_24h": ticker.get("high"),
                "low_24h": ticker.get("low"),
                "volume_24h": ticker.get("baseVolume"),
                "change_24h": ticker.get("change"),
                "change_pct_24h": ticker.get("percentage"),
                "timestamp": datetime.utcnow(),
            }
            self._price_cache[f"{exchange_name}:{symbol}"] = {
                "data": result,
                "timestamp": datetime.utcnow(),
            }
            return result
        except Exception as e:
            logger.error("Error fetching ticker %s from %s: %s", symbol, exchange_name, e)
            return await self._get_simulated_ticker(exchange_name, symbol)

    async def get_tickers(self, exchange_name: str, symbols: List[str]) -> List[Dict]:
        """Fetch tickers for multiple symbols concurrently."""
        tasks = [self.get_ticker(exchange_name, s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]

    async def get_ohlcv(
        self, exchange_name: str, symbol: str, timeframe: str = "1h", limit: int = 100
    ) -> List[Dict]:
        """Get OHLCV candle data — routes to ccxt or connector."""
        # connector
        connector = self.get_connector(exchange_name)
        if connector:
            try:
                return await connector.get_ohlcv(symbol, timeframe, limit)
            except Exception as e:
                logger.error("Connector OHLCV error (%s/%s): %s", exchange_name, symbol, e)
                return self._get_simulated_ohlcv(symbol, timeframe, limit)

        # ccxt
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            return self._get_simulated_ohlcv(symbol, timeframe, limit)

        entry = self._exchanges.get(exchange_name, {})
        if entry.get("type") == "alpaca":
            return self._get_simulated_ohlcv(symbol, timeframe, limit)

        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [
                {
                    "timestamp": c[0],
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5],
                }
                for c in ohlcv
            ]
        except Exception as e:
            logger.error("Error fetching OHLCV for %s from %s: %s", symbol, exchange_name, e)
            return self._get_simulated_ohlcv(symbol, timeframe, limit)

    async def get_order_book(self, exchange_name: str, symbol: str, limit: int = 20) -> Dict:
        """Get order book — routes to ccxt or connector."""
        # connector
        connector = self.get_connector(exchange_name)
        if connector:
            try:
                book = await connector.get_order_book(symbol, limit)
                return {
                    "symbol": symbol,
                    "exchange": exchange_name,
                    "bids": [{"price": b[0], "quantity": b[1]} for b in book.get("bids", [])],
                    "asks": [{"price": a[0], "quantity": a[1]} for a in book.get("asks", [])],
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                logger.error("Connector order book error (%s/%s): %s", exchange_name, symbol, e)
                return self._get_simulated_order_book(symbol, limit)

        # ccxt
        exchange = self.get_exchange(exchange_name)
        if not exchange:
            return self._get_simulated_order_book(symbol, limit)

        entry = self._exchanges.get(exchange_name, {})
        if entry.get("type") == "alpaca":
            return self._get_simulated_order_book(symbol, limit)

        try:
            book = await exchange.fetch_order_book(symbol, limit)
            return {
                "symbol": symbol,
                "exchange": exchange_name,
                "bids": [{"price": b[0], "quantity": b[1]} for b in book["bids"][:limit]],
                "asks": [{"price": a[0], "quantity": a[1]} for a in book["asks"][:limit]],
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error("Error fetching order book: %s", e)
            return self._get_simulated_order_book(symbol, limit)

    # ── simulated data (paper trading fallback) ───────────────────────────────

    _BASE_PRICES: Dict[str, float] = {
        "BTC/USDT": 67500, "BTC/USD": 67500, "BTC/GBP": 53500,
        "ETH/USDT": 3450, "ETH/USD": 3450, "ETH/GBP": 2750,
        "SOL/USDT": 185, "SOL/USD": 185,
        "BNB/USDT": 610,
        "XRP/USDT": 0.62, "XRP/USD": 0.62,
        "ADA/USDT": 0.45, "ADA/USD": 0.45,
        "DOGE/USDT": 0.085, "DOGE/USD": 0.085,
        "AVAX/USDT": 38.5, "AVAX/USD": 38.5,
        "DOT/USDT": 7.20, "DOT/USD": 7.20,
        "MATIC/USDT": 0.72,
        "OKB/USDT": 52.0,
        "CRO/USDT": 0.085,
        # Stocks / ETFs
        "AAPL": 178.50, "GOOGL": 142.30, "MSFT": 420.10,
        "TSLA": 175.80, "AMZN": 185.60, "META": 505.20,
        "NVDA": 880.50, "SPY": 520.40, "QQQ": 440.20,
        # Forex
        "EUR/USD": 1.0850, "EUR_USD": 1.0850, "EURUSD": 1.0850,
        "GBP/USD": 1.2650, "GBP_USD": 1.2650, "GBPUSD": 1.2650,
        "USD/JPY": 149.50, "USD_JPY": 149.50, "USDJPY": 149.50,
        "AUD/USD": 0.6550, "AUD_USD": 0.6550,
        "USD/CAD": 1.3580, "USD_CAD": 1.3580,
        "NZD/USD": 0.6120,
        "USD/CHF": 0.8780,
        "EUR/GBP": 0.8575, "EUR_GBP": 0.8575,
        # Indices
        "SPX500": 5120.0, "US500": 5120.0, "US30": 38950.0,
        "UK100": 7720.0, "GER40": 17450.0,
        # Commodities
        "XAUUSD": 2035.0, "XAGUSD": 22.85,
        "USOIL": 78.40, "UKOIL": 82.10,
    }

    async def _get_simulated_ticker(self, exchange_name: str, symbol: str) -> Dict:
        """Generate simulated ticker data for paper trading."""
        base = self._BASE_PRICES.get(symbol, 100.0)
        variation = random.uniform(-0.02, 0.02)
        price = base * (1 + variation)
        change_pct = random.uniform(-5, 5)

        return {
            "symbol": symbol,
            "exchange": exchange_name,
            "last_price": round(price, 6 if price < 1 else 2),
            "bid": round(price * 0.999, 6 if price < 1 else 2),
            "ask": round(price * 1.001, 6 if price < 1 else 2),
            "high_24h": round(price * 1.03, 2),
            "low_24h": round(price * 0.97, 2),
            "volume_24h": round(random.uniform(1_000_000, 50_000_000), 2),
            "change_24h": round(price * change_pct / 100, 2),
            "change_pct_24h": round(change_pct, 2),
            "timestamp": datetime.utcnow(),
        }

    def _get_simulated_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Generate simulated OHLCV candles with realistic trending behaviour.

        Uses a random walk with drift so that strategies can detect trends
        and generate actionable buy/sell signals.  The drift direction
        rotates every ~30 bars to create both uptrends and downtrends.
        """
        import math

        base = self._BASE_PRICES.get(symbol, 100.0)
        tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
        minutes = tf_minutes.get(timeframe, 60)

        candles = []
        price = base * 0.95
        now = datetime.utcnow()

        # Create trending phases — alternate up/down every ~30 bars
        phase_length = max(20, limit // 3)
        drift_per_bar = 0.003  # 0.3 % drift per bar in the trending direction

        for i in range(limit):
            ts = now - timedelta(minutes=minutes * (limit - i))

            # Determine drift direction for this bar's phase
            phase = (i // phase_length) % 3
            if phase == 0:
                drift = drift_per_bar          # uptrend
            elif phase == 1:
                drift = -drift_per_bar * 0.6   # mild downtrend / pullback
            else:
                drift = drift_per_bar * 0.8    # resumed uptrend

            noise = random.gauss(0, 0.008)     # ±0.8 % noise
            change = drift + noise

            o = price
            c = price * (1 + change)
            h = max(o, c) * (1 + random.uniform(0, 0.005))
            low = min(o, c) * (1 - random.uniform(0, 0.005))
            # Volume spikes during trend changes
            base_vol = random.uniform(1000, 8000)
            if abs(change) > 0.01:
                base_vol *= 2
            v = base_vol

            candles.append({
                "timestamp": int(ts.timestamp() * 1000),
                "open": round(o, 2),
                "high": round(h, 2),
                "low": round(low, 2),
                "close": round(c, 2),
                "volume": round(v, 2),
            })
            price = max(c, base * 0.1)  # prevent price going negative

        return candles

    def _get_simulated_order_book(self, symbol: str, limit: int) -> Dict:
        """Generate simulated order book."""
        mid = self._BASE_PRICES.get(symbol, 100.0)
        bids = []
        asks = []
        for i in range(limit):
            spread = mid * 0.0001 * (i + 1)
            bids.append({"price": round(mid - spread, 2), "quantity": round(random.uniform(0.1, 5.0), 4)})
            asks.append({"price": round(mid + spread, 2), "quantity": round(random.uniform(0.1, 5.0), 4)})

        return {
            "symbol": symbol,
            "exchange": "simulated",
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Singleton
exchange_manager = ExchangeManager()
