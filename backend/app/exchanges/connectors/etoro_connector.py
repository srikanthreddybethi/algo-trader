"""eToro connector — stocks, crypto, ETFs, CFDs + social trading.

REST API: https://api.etoro.com/api/v1 (public API launched Feb 2026)
Auth: API key in X-API-KEY header.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.etoro.com/api/v1"
_DEMO_URL = "https://demo-api.etoro.com/api/v1"


class EToroConnector(BaseConnector):
    """eToro REST API connector with social trading support."""

    name = "etoro"
    display_name = "eToro"
    connector_type = "multi_asset"
    supported_asset_types = ["stocks", "crypto", "etfs", "cfds"]
    default_pairs = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "BTC",
        "ETH",
        "SPY",
    ]

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._rate_limiter = asyncio.Semaphore(15)

    @classmethod
    def get_config_fields(cls) -> list:
        return [
            {"name": "api_key", "label": "API Key", "type": "password", "required": True},
            {"name": "is_demo", "label": "Virtual Portfolio", "type": "boolean", "default": True},
        ]

    # ── connection ────────────────────────────────────────────────────

    async def connect(self, credentials: dict) -> dict:
        try:
            api_key = credentials["api_key"]
            self._is_demo = credentials.get("is_demo", True)
        except KeyError as exc:
            return {"status": "error", "message": f"Missing credential: {exc}"}

        base_url = _DEMO_URL if self._is_demo else _BASE_URL
        self._session_headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._client = httpx.AsyncClient(base_url=base_url, headers=self._session_headers, timeout=30)

        try:
            resp = await self._client.get("/account")
            resp.raise_for_status()
            data = resp.json()
            self._credentials = credentials
            self._connected = True
            logger.info("eToro: connected (demo=%s)", self._is_demo)
            return {"status": "connected", "demo": self._is_demo, "username": data.get("username", "")}
        except httpx.HTTPStatusError as exc:
            logger.error("eToro auth failed: %s", exc.response.text)
            return {"status": "error", "message": f"Auth failed: {exc.response.status_code}"}
        except Exception as exc:
            logger.error("eToro connect error: %s", exc)
            return {"status": "error", "message": str(exc)}

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        self._connected = False
        self._client = None
        logger.info("eToro: disconnected")

    # ── private helpers ───────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        if not self._connected or not self._client:
            raise ConnectionError("eToro connector is not connected")
        await self._rate_limit()
        try:
            resp = await self._client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        finally:
            self._release_rate_limit()

    # ── instrument resolution ─────────────────────────────────────────

    async def _resolve_instrument(self, symbol: str) -> str:
        """Resolve a ticker symbol to eToro's instrumentId.

        eToro's API (launched Feb 2026) requires instrumentId for trading.
        If resolution fails, returns the original symbol as fallback.
        """
        if not self._connected:
            return symbol
        try:
            data = await self._request("GET", "/instruments/search", params={"q": symbol})
            items = data if isinstance(data, list) else data.get("instruments", [])
            if items:
                instrument_id = items[0].get("instrumentId")
                if instrument_id:
                    return str(instrument_id)
        except Exception:
            pass
        return symbol

    # ── account ───────────────────────────────────────────────────────

    async def get_account_info(self) -> dict:
        if not self._connected:
            return self._get_simulated_account()
        try:
            data = await self._request("GET", "/account")
            if not isinstance(data, dict):
                data = {}
            return {
                "balance": float(data.get("balance", 0)),
                "equity": float(data.get("equity", 0)),
                "margin_used": float(data.get("marginUsed", 0)),
                "margin_available": float(data.get("availableBalance", 0)),
                "unrealised_pnl": float(data.get("unrealisedPnl", 0)),
                "currency": data.get("currency", "USD"),
            }
        except Exception as exc:
            logger.error("eToro get_account_info error: %s", exc)
            return self._get_simulated_account()

    # ── market data ───────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        if not self._connected:
            return self._get_simulated_ticker(symbol)
        try:
            data = await self._request("GET", f"/instruments/{symbol}/price")
            if not isinstance(data, dict):
                return self._get_simulated_ticker(symbol)
            return {
                "symbol": symbol,
                "last_price": float(data.get("lastPrice", 0)),
                "bid": float(data.get("bid", 0)),
                "ask": float(data.get("ask", 0)),
                "high_24h": float(data.get("high24h", 0)),
                "low_24h": float(data.get("low24h", 0)),
                "volume_24h": float(data.get("volume24h", 0)),
                "change_pct_24h": float(data.get("changePct24h", 0)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning("eToro get_ticker fallback: %s", exc)
            return self._get_simulated_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        if not self._connected:
            return self._get_simulated_ohlcv(symbol, timeframe, limit)
        try:
            data = await self._request(
                "GET",
                f"/instruments/{symbol}/candles",
                params={"interval": timeframe, "limit": limit},
            )
            candles = []
            items = data if isinstance(data, list) else data.get("candles", [])
            for c in items:
                candles.append(
                    {
                        "timestamp": c.get("timestamp", ""),
                        "open": float(c.get("open", 0)),
                        "high": float(c.get("high", 0)),
                        "low": float(c.get("low", 0)),
                        "close": float(c.get("close", 0)),
                        "volume": float(c.get("volume", 0)),
                    }
                )
            return candles
        except Exception as exc:
            logger.warning("eToro get_ohlcv fallback: %s", exc)
            return self._get_simulated_ohlcv(symbol, timeframe, limit)

    # ── trading ───────────────────────────────────────────────────────

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: float | None = None,
    ) -> dict:
        if not self._connected:
            return self._get_simulated_order(symbol, side, quantity, order_type, price)
        try:
            # Resolve symbol to eToro's instrumentId
            instrument_id = await self._resolve_instrument(symbol)
            payload: dict = {
                "instrumentId": instrument_id,
                "instrument": symbol,
                "side": side.upper(),
                "amount": quantity,
                "type": order_type.upper(),
            }
            if price and order_type.lower() in ("limit", "stop"):
                payload["price"] = price

            data = await self._request("POST", "/orders", json=payload)
            if not isinstance(data, dict):
                data = {}
            return {
                "order_id": str(data.get("orderId", "")),
                "status": data.get("status", "submitted").lower(),
                "filled_qty": float(data.get("filledAmount", 0)),
                "filled_price": float(data.get("filledPrice", 0)),
            }
        except Exception as exc:
            logger.error("eToro place_order error: %s", exc)
            return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

    async def cancel_order(self, order_id: str) -> dict:
        if not self._connected:
            return {"order_id": order_id, "status": "cancelled"}
        try:
            await self._request("DELETE", f"/orders/{order_id}")
            return {"order_id": order_id, "status": "cancelled"}
        except Exception as exc:
            logger.error("eToro cancel_order error: %s", exc)
            return {"order_id": order_id, "status": "error", "message": str(exc)}

    async def get_positions(self) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/portfolio/positions")
            positions = []
            items = data if isinstance(data, list) else data.get("positions", [])
            for p in items:
                positions.append(
                    {
                        "symbol": p.get("instrument", ""),
                        "side": p.get("side", "buy").lower(),
                        "quantity": float(p.get("amount", 0)),
                        "entry_price": float(p.get("openRate", 0)),
                        "current_price": float(p.get("currentRate", 0)),
                        "unrealised_pnl": float(p.get("pnl", 0)),
                    }
                )
            return positions
        except Exception as exc:
            logger.error("eToro get_positions error: %s", exc)
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        return self._get_simulated_order_book(symbol, limit)

    async def search_instruments(self, query: str) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/instruments/search", params={"q": query})
            results = []
            items = data if isinstance(data, list) else data.get("instruments", [])
            for inst in items:
                results.append(
                    {
                        "symbol": inst.get("symbol", ""),
                        "name": inst.get("name", ""),
                        "type": inst.get("assetClass", ""),
                        "exchange": "eToro",
                    }
                )
            return results
        except Exception as exc:
            logger.error("eToro search_instruments error: %s", exc)
            return []

    # ── eToro social trading extras ───────────────────────────────────

    async def get_popular_investors(self, limit: int = 10) -> list:
        """Fetch top Popular Investors (social trading feature)."""
        if not self._connected:
            return []
        try:
            data = await self._request(
                "GET",
                "/social/popular-investors",
                params={"limit": limit},
            )
            return data if isinstance(data, list) else data.get("investors", [])
        except Exception as exc:
            logger.warning("eToro get_popular_investors error: %s", exc)
            return []

    async def copy_trader(self, username: str, amount: float) -> dict:
        """Start copying a Popular Investor."""
        if not self._connected:
            return {"status": "error", "message": "Not connected"}
        try:
            data = await self._request(
                "POST",
                "/social/copy",
                json={"username": username, "amount": amount},
            )
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.error("eToro copy_trader error: %s", exc)
            return {"status": "error", "message": str(exc)}
