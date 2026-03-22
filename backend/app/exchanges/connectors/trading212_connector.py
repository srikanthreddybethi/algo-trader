"""Trading 212 connector — commission-free stocks & ETFs.

REST API (Beta): https://live.trading212.com/api/v0
Auth: HTTP Basic Auth — base64(API_KEY:API_SECRET) in Authorization header.
Markets: UK/EU/US stocks, ETFs.
Note: Market orders only on live; Limit/Stop/StopLimit available on demo.
"""

import asyncio
import base64
import logging
import time
from datetime import datetime, timezone

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

_LIVE_URL = "https://live.trading212.com/api/v0"
_DEMO_URL = "https://demo.trading212.com/api/v0"


class Trading212Connector(BaseConnector):
    """Trading 212 REST API connector."""

    name = "trading212"
    display_name = "Trading 212"
    connector_type = "stocks"
    supported_asset_types = ["stocks", "etfs"]
    default_pairs = [
        "AAPL_US_EQ",
        "MSFT_US_EQ",
        "GOOGL_US_EQ",
        "AMZN_US_EQ",
        "TSLA_US_EQ",
        "VOO_US_EQ",
        "VUSA_EQ",
        "IUSA_EQ",
    ]

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._rate_limiter = asyncio.Semaphore(5)  # conservative — API is beta

    @classmethod
    def get_config_fields(cls) -> list:
        return [
            {"name": "api_key", "label": "API Key", "type": "password", "required": True},
            {"name": "api_secret", "label": "API Secret", "type": "password", "required": True},
            {"name": "is_demo", "label": "Demo Account", "type": "boolean", "default": True},
        ]

    # ── connection ────────────────────────────────────────────────────

    async def connect(self, credentials: dict) -> dict:
        try:
            api_key = credentials["api_key"]
            api_secret = credentials["api_secret"]
            self._is_demo = credentials.get("is_demo", True)
        except KeyError as exc:
            return {"status": "error", "message": f"Missing credential: {exc}"}

        base_url = _DEMO_URL if self._is_demo else _LIVE_URL
        # Trading 212 uses HTTP Basic Auth: base64(API_KEY:API_SECRET)
        credentials_str = f"{api_key}:{api_secret}"
        encoded = base64.b64encode(credentials_str.encode()).decode()
        self._session_headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(base_url=base_url, headers=self._session_headers, timeout=30)

        try:
            resp = await self._client.get("/equity/account/cash")
            resp.raise_for_status()
            self._credentials = credentials
            self._connected = True
            logger.info("Trading212: connected (demo=%s)", self._is_demo)
            return {"status": "connected", "demo": self._is_demo}
        except httpx.HTTPStatusError as exc:
            logger.error("Trading212 auth failed: %s", exc.response.text)
            return {"status": "error", "message": f"Auth failed: {exc.response.status_code}"}
        except Exception as exc:
            logger.error("Trading212 connect error: %s", exc)
            return {"status": "error", "message": str(exc)}

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        self._connected = False
        self._client = None
        logger.info("Trading212: disconnected")

    # ── private helpers ───────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        if not self._connected or not self._client:
            raise ConnectionError("Trading212 connector is not connected")
        await self._rate_limit()
        try:
            resp = await self._client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        finally:
            self._release_rate_limit()

    # ── account ───────────────────────────────────────────────────────

    async def get_account_info(self) -> dict:
        if not self._connected:
            return self._get_simulated_account()
        try:
            cash = await self._request("GET", "/equity/account/cash")
            return {
                "balance": float(cash.get("free", 0)),
                "equity": float(cash.get("total", 0)),
                "margin_used": float(cash.get("invested", 0)),
                "margin_available": float(cash.get("free", 0)),
                "unrealised_pnl": float(cash.get("ppl", 0)),
                "currency": "GBP",
            }
        except Exception as exc:
            logger.error("Trading212 get_account_info error: %s", exc)
            return self._get_simulated_account()

    # ── market data ───────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        if not self._connected:
            return self._get_simulated_ticker(symbol)
        # Trading 212 API (v0) doesn't have a dedicated ticker endpoint;
        # fall back to simulated data
        return self._get_simulated_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        # Trading 212 API (v0) does not expose OHLCV data
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
            if order_type.lower() == "market":
                payload = {
                    "ticker": symbol,
                    "quantity": quantity if side.lower() == "buy" else -quantity,
                }
                data = await self._request("POST", "/equity/orders/market", json=payload)
            elif order_type.lower() == "limit":
                payload = {
                    "ticker": symbol,
                    "quantity": quantity if side.lower() == "buy" else -quantity,
                    "limitPrice": price,
                    "timeValidity": "DAY",
                }
                data = await self._request("POST", "/equity/orders/limit", json=payload)
            elif order_type.lower() == "stop":
                payload = {
                    "ticker": symbol,
                    "quantity": quantity if side.lower() == "buy" else -quantity,
                    "stopPrice": price,
                    "timeValidity": "DAY",
                }
                data = await self._request("POST", "/equity/orders/stop", json=payload)
            elif order_type.lower() == "stop_limit":
                payload = {
                    "ticker": symbol,
                    "quantity": quantity if side.lower() == "buy" else -quantity,
                    "limitPrice": price,
                    "stopPrice": price,
                    "timeValidity": "DAY",
                }
                data = await self._request("POST", "/equity/orders/stop_limit", json=payload)
            else:
                return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

            if not isinstance(data, dict):
                data = {}
            return {
                "order_id": str(data.get("id", "")),
                "status": data.get("status", "submitted").lower(),
                "filled_qty": float(data.get("filledQuantity", 0)),
                "filled_price": float(data.get("filledValue", 0)),
            }
        except Exception as exc:
            logger.error("Trading212 place_order error: %s", exc)
            return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

    async def cancel_order(self, order_id: str) -> dict:
        if not self._connected:
            return {"order_id": order_id, "status": "cancelled"}
        try:
            await self._request("DELETE", f"/equity/orders/{order_id}")
            return {"order_id": order_id, "status": "cancelled"}
        except Exception as exc:
            logger.error("Trading212 cancel_order error: %s", exc)
            return {"order_id": order_id, "status": "error", "message": str(exc)}

    async def get_positions(self) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/equity/portfolio")
            positions = []
            for p in data if isinstance(data, list) else []:
                qty = float(p.get("quantity", 0))
                positions.append(
                    {
                        "symbol": p.get("ticker", ""),
                        "side": "buy" if qty > 0 else "sell",
                        "quantity": abs(qty),
                        "entry_price": float(p.get("averagePrice", 0)),
                        "current_price": float(p.get("currentPrice", 0)),
                        "unrealised_pnl": float(p.get("ppl", 0)),
                    }
                )
            return positions
        except Exception as exc:
            logger.error("Trading212 get_positions error: %s", exc)
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        return self._get_simulated_order_book(symbol, limit)

    async def search_instruments(self, query: str) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/equity/metadata/instruments")
            results = []
            query_lower = query.lower()
            for inst in data if isinstance(data, list) else []:
                ticker = inst.get("ticker", "")
                name = inst.get("name", "")
                if query_lower in ticker.lower() or query_lower in name.lower():
                    results.append(
                        {
                            "symbol": ticker,
                            "name": name,
                            "type": inst.get("type", "EQUITY"),
                            "exchange": "Trading212",
                            "currency": inst.get("currencyCode", ""),
                        }
                    )
            return results[:50]
        except Exception as exc:
            logger.error("Trading212 search_instruments error: %s", exc)
            return []
