"""Saxo Bank connector — OpenAPI REST.

Live: https://gateway.saxobank.com/openapi
Sim:  https://gateway.saxobank.com/sim/openapi
Auth: OAuth 2.0 bearer token.
Markets: Stocks, forex, options, futures, bonds, CFDs.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

_LIVE_URL = "https://gateway.saxobank.com/openapi"
_SIM_URL = "https://gateway.saxobank.com/sim/openapi"

_TF_MAP = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
    "1w": 10080,
}


class SaxoConnector(BaseConnector):
    """Saxo Bank OpenAPI connector."""

    name = "saxo"
    display_name = "Saxo Bank"
    connector_type = "multi_asset"
    supported_asset_types = ["stocks", "forex", "options", "futures", "bonds", "cfds"]
    default_pairs = [
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AAPL:xnas",
        "MSFT:xnas",
        "VOD:xlon",
        "XAUUSD",
        "SPX500",
    ]

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._client_key: str = ""
        self._account_key: str = ""
        self._rate_limiter = asyncio.Semaphore(20)
        self._token_expiry: float = 0
        self._refresh_token: str = ""

    @classmethod
    def get_config_fields(cls) -> list:
        return [
            {"name": "access_token", "label": "OAuth Access Token", "type": "password", "required": True},
            {"name": "refresh_token", "label": "Refresh Token (optional)", "type": "password", "required": False},
            {"name": "account_key", "label": "Account Key", "type": "text", "required": False},
            {"name": "is_demo", "label": "SIM Environment", "type": "boolean", "default": True},
        ]

    # ── connection ────────────────────────────────────────────────────

    async def connect(self, credentials: dict) -> dict:
        try:
            token = credentials["access_token"]
            self._is_demo = credentials.get("is_demo", True)
            self._refresh_token = credentials.get("refresh_token", "")
        except KeyError as exc:
            return {"status": "error", "message": f"Missing credential: {exc}"}

        base_url = _SIM_URL if self._is_demo else _LIVE_URL
        self._session_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        # Saxo tokens expire after ~20 minutes; track expiry
        self._token_expiry = time.time() + 1200  # Default 20min from now
        self._client = httpx.AsyncClient(base_url=base_url, headers=self._session_headers, timeout=30)

        try:
            # Fetch user info to validate token
            resp = await self._client.get("/port/v1/users/me")
            resp.raise_for_status()
            user_data = resp.json()
            self._client_key = user_data.get("ClientKey", "")

            # Resolve account
            if credentials.get("account_key"):
                self._account_key = credentials["account_key"]
            else:
                acct_resp = await self._client.get("/port/v1/accounts/me")
                acct_resp.raise_for_status()
                accounts = acct_resp.json().get("Data", [])
                if accounts:
                    self._account_key = accounts[0].get("AccountKey", "")

            self._credentials = credentials
            self._connected = True
            logger.info("Saxo: connected (client=%s, sim=%s)", self._client_key, self._is_demo)
            return {"status": "connected", "client_key": self._client_key, "demo": self._is_demo}
        except httpx.HTTPStatusError as exc:
            logger.error("Saxo auth failed: %s", exc.response.text)
            return {"status": "error", "message": f"Auth failed: {exc.response.status_code}"}
        except Exception as exc:
            logger.error("Saxo connect error: %s", exc)
            return {"status": "error", "message": str(exc)}

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        self._connected = False
        self._client = None
        logger.info("Saxo: disconnected")

    # ── private helpers ───────────────────────────────────────────────

    async def _ensure_token_valid(self):
        """Check if OAuth token is still valid; refresh if needed."""
        if time.time() < self._token_expiry - 60:
            return  # Token still valid (with 60s buffer)
        if not self._refresh_token or not self._client:
            logger.warning("Saxo: token may be expired and no refresh_token available")
            return
        try:
            # Saxo token refresh endpoint
            auth_url = "https://gateway.saxobank.com/openapi" if not self._is_demo else "https://gateway.saxobank.com/sim/openapi"
            resp = await self._client.post(
                "/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            new_token = data.get("access_token", "")
            if new_token:
                self._session_headers["Authorization"] = f"Bearer {new_token}"
                self._token_expiry = time.time() + data.get("expires_in", 1200)
                if data.get("refresh_token"):
                    self._refresh_token = data["refresh_token"]
                # Update client headers
                self._client.headers.update(self._session_headers)
                logger.info("Saxo: token refreshed, expires in %ss", data.get("expires_in", 1200))
        except Exception as exc:
            logger.error("Saxo: token refresh failed: %s", exc)
            self._connected = False

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self._connected or not self._client:
            raise ConnectionError("Saxo connector is not connected")
        await self._ensure_token_valid()
        await self._rate_limit()
        try:
            resp = await self._client.request(method, path, **kwargs)
            # Handle 401 — token may have expired
            if resp.status_code == 401:
                self._token_expiry = 0  # Force refresh on next call
                await self._ensure_token_valid()
                if self._connected:
                    resp = await self._client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        finally:
            self._release_rate_limit()

    async def _search_uic(self, keyword: str, asset_type: str = "FxSpot") -> int | None:
        """Resolve a keyword to a Saxo UIC (Unique Instrument Code)."""
        try:
            data = await self._request(
                "GET",
                "/ref/v1/instruments",
                params={"Keywords": keyword, "AssetTypes": asset_type},
            )
            instruments = data.get("Data", [])
            if instruments:
                return instruments[0].get("Identifier")
        except Exception as exc:
            logger.warning("Saxo _search_uic(%s) failed: %s", keyword, exc)
        return None

    # ── account ───────────────────────────────────────────────────────

    async def get_account_info(self) -> dict:
        if not self._connected:
            return self._get_simulated_account()
        try:
            data = await self._request(
                "GET",
                "/port/v1/balances",
                params={"AccountKey": self._account_key, "ClientKey": self._client_key},
            )
            return {
                "balance": float(data.get("CashBalance", 0)),
                "equity": float(data.get("TotalValue", 0)),
                "margin_used": float(data.get("MarginUsedByCurrentPositions", 0)),
                "margin_available": float(data.get("MarginAvailableForTrading", 0)),
                "unrealised_pnl": float(data.get("UnrealizedPositionsValue", 0)),
                "currency": data.get("Currency", "USD"),
            }
        except Exception as exc:
            logger.error("Saxo get_account_info error: %s", exc)
            return self._get_simulated_account()

    # ── market data ───────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        if not self._connected:
            return self._get_simulated_ticker(symbol)
        try:
            uic = await self._search_uic(symbol)
            if not uic:
                return self._get_simulated_ticker(symbol)
            data = await self._request(
                "GET",
                "/trade/v1/infoprices",
                params={"Uic": uic, "AssetType": "FxSpot", "FieldGroups": "Quote,PriceInfo"},
            )
            quote = data.get("Quote", {})
            return {
                "symbol": symbol,
                "last_price": float(quote.get("Mid", 0)),
                "bid": float(quote.get("Bid", 0)),
                "ask": float(quote.get("Ask", 0)),
                "high_24h": float(data.get("PriceInfo", {}).get("High", 0)),
                "low_24h": float(data.get("PriceInfo", {}).get("Low", 0)),
                "volume_24h": 0,
                "change_pct_24h": float(data.get("PriceInfo", {}).get("PercentChange", 0)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning("Saxo get_ticker fallback: %s", exc)
            return self._get_simulated_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        if not self._connected:
            return self._get_simulated_ohlcv(symbol, timeframe, limit)
        try:
            uic = await self._search_uic(symbol)
            if not uic:
                return self._get_simulated_ohlcv(symbol, timeframe, limit)
            horizon = _TF_MAP.get(timeframe, 60)
            data = await self._request(
                "GET",
                "/chart/v1/charts",
                params={"Uic": uic, "AssetType": "FxSpot", "Horizon": horizon, "Count": limit},
            )
            candles = []
            for pt in data.get("Data", []):
                candles.append(
                    {
                        "timestamp": pt.get("Time", ""),
                        "open": float(pt.get("Open", 0)),
                        "high": float(pt.get("High", 0)),
                        "low": float(pt.get("Low", 0)),
                        "close": float(pt.get("Close", 0)),
                        "volume": float(pt.get("Volume", 0)),
                    }
                )
            return candles
        except Exception as exc:
            logger.warning("Saxo get_ohlcv fallback: %s", exc)
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
            uic = await self._search_uic(symbol)
            if not uic:
                return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

            buy_sell = "Buy" if side.lower() == "buy" else "Sell"
            saxo_order_type = "Market"
            if order_type.lower() == "limit":
                saxo_order_type = "Limit"
            elif order_type.lower() == "stop":
                saxo_order_type = "Stop"

            payload: dict = {
                "AccountKey": self._account_key,
                "Uic": uic,
                "AssetType": "FxSpot",
                "BuySell": buy_sell,
                "Amount": quantity,
                "OrderType": saxo_order_type,
                "OrderDuration": {"DurationType": "DayOrder"},
                "ManualOrder": False,
            }
            if price and saxo_order_type in ("Limit", "Stop"):
                payload["OrderPrice"] = price

            data = await self._request("POST", "/trade/v2/orders", json=payload)
            return {
                "order_id": str(data.get("OrderId", "")),
                "status": "submitted",
                "filled_qty": 0,
                "filled_price": 0,
            }
        except Exception as exc:
            logger.error("Saxo place_order error: %s", exc)
            return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

    async def cancel_order(self, order_id: str) -> dict:
        if not self._connected:
            return {"order_id": order_id, "status": "cancelled"}
        try:
            await self._request(
                "DELETE",
                f"/trade/v2/orders/{order_id}",
                params={"AccountKey": self._account_key},
            )
            return {"order_id": order_id, "status": "cancelled"}
        except Exception as exc:
            logger.error("Saxo cancel_order error: %s", exc)
            return {"order_id": order_id, "status": "error", "message": str(exc)}

    async def get_positions(self) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request(
                "GET",
                "/port/v1/positions",
                params={"ClientKey": self._client_key},
            )
            positions = []
            for p in data.get("Data", []):
                pos = p.get("PositionBase", {})
                view = p.get("PositionView", {})
                positions.append(
                    {
                        "symbol": p.get("DisplayAndFormat", {}).get("Symbol", ""),
                        "side": "buy" if pos.get("Amount", 0) > 0 else "sell",
                        "quantity": abs(float(pos.get("Amount", 0))),
                        "entry_price": float(view.get("AverageOpenPrice", 0)),
                        "current_price": float(view.get("CurrentPrice", 0)),
                        "unrealised_pnl": float(view.get("ProfitLossOnTrade", 0)),
                    }
                )
            return positions
        except Exception as exc:
            logger.error("Saxo get_positions error: %s", exc)
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        # Saxo OpenAPI doesn't provide full order-book depth
        return self._get_simulated_order_book(symbol, limit)

    async def search_instruments(self, query: str) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request(
                "GET",
                "/ref/v1/instruments",
                params={"Keywords": query, "AssetTypes": "FxSpot,Stock,CfdOnIndex,CfdOnStock"},
            )
            results = []
            for inst in data.get("Data", []):
                results.append(
                    {
                        "symbol": inst.get("Symbol", ""),
                        "name": inst.get("Description", ""),
                        "type": inst.get("AssetType", ""),
                        "uic": inst.get("Identifier", ""),
                        "exchange": inst.get("ExchangeId", "Saxo"),
                    }
                )
            return results
        except Exception as exc:
            logger.error("Saxo search_instruments error: %s", exc)
            return []
