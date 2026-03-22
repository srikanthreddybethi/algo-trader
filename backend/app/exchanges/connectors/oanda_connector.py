"""OANDA connector — forex & CFD trading via v20 REST API.

Live:     https://api-fxtrade.oanda.com
Practice: https://api-fxpractice.oanda.com
Auth:     Bearer token in Authorization header.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

_LIVE_URL = "https://api-fxtrade.oanda.com"
_PRACTICE_URL = "https://api-fxpractice.oanda.com"

_TF_MAP = {
    "1m": "M1",
    "5m": "M5",
    "15m": "M15",
    "30m": "M30",
    "1h": "H1",
    "4h": "H4",
    "1d": "D",
    "1w": "W",
}


class OandaConnector(BaseConnector):
    """OANDA v20 REST API connector."""

    name = "oanda"
    display_name = "OANDA"
    connector_type = "forex"
    supported_asset_types = ["forex", "indices", "commodities", "shares_cfd", "metals"]
    default_pairs = [
        "EUR_USD",
        "GBP_USD",
        "USD_JPY",
        "AUD_USD",
        "USD_CAD",
        "NZD_USD",
        "USD_CHF",
        "EUR_GBP",
    ]

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._account_id: str = ""
        self._rate_limiter = asyncio.Semaphore(25)

    @classmethod
    def get_config_fields(cls) -> list:
        return [
            {"name": "api_token", "label": "API Token (Bearer)", "type": "password", "required": True},
            {"name": "account_id", "label": "Account ID", "type": "text", "required": True},
            {"name": "is_demo", "label": "Practice Account", "type": "boolean", "default": True},
        ]

    # ── connection ────────────────────────────────────────────────────

    async def connect(self, credentials: dict) -> dict:
        try:
            token = credentials["api_token"]
            self._account_id = credentials["account_id"]
            self._is_demo = credentials.get("is_demo", True)
        except KeyError as exc:
            return {"status": "error", "message": f"Missing credential: {exc}"}

        base_url = _PRACTICE_URL if self._is_demo else _LIVE_URL
        self._session_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339",
        }
        self._client = httpx.AsyncClient(base_url=base_url, headers=self._session_headers, timeout=30)

        try:
            resp = await self._client.get(f"/v3/accounts/{self._account_id}/summary")
            resp.raise_for_status()
            self._credentials = credentials
            self._connected = True
            logger.info("OANDA: connected (account=%s, practice=%s)", self._account_id, self._is_demo)
            return {"status": "connected", "account_id": self._account_id, "demo": self._is_demo}
        except httpx.HTTPStatusError as exc:
            logger.error("OANDA auth failed: %s", exc.response.text)
            return {"status": "error", "message": f"Auth failed: {exc.response.status_code}"}
        except Exception as exc:
            logger.error("OANDA connect error: %s", exc)
            return {"status": "error", "message": str(exc)}

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        self._connected = False
        self._client = None
        logger.info("OANDA: disconnected")

    # ── private helpers ───────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self._connected or not self._client:
            raise ConnectionError("OANDA connector is not connected")
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
            data = await self._request("GET", f"/v3/accounts/{self._account_id}/summary")
            acct = data.get("account", {})
            return {
                "balance": float(acct.get("balance", 0)),
                "equity": float(acct.get("NAV", 0)),
                "margin_used": float(acct.get("marginUsed", 0)),
                "margin_available": float(acct.get("marginAvailable", 0)),
                "unrealised_pnl": float(acct.get("unrealizedPL", 0)),
                "currency": acct.get("currency", "USD"),
            }
        except Exception as exc:
            logger.error("OANDA get_account_info error: %s", exc)
            return self._get_simulated_account()

    # ── market data ───────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        if not self._connected:
            return self._get_simulated_ticker(symbol)
        try:
            instrument = self._normalize_symbol(symbol)
            data = await self._request(
                "GET",
                f"/v3/accounts/{self._account_id}/pricing",
                params={"instruments": instrument},
            )
            prices = data.get("prices", [])
            if not prices:
                return self._get_simulated_ticker(symbol)
            p = prices[0]
            bid = float(p.get("bids", [{}])[0].get("price", 0))
            ask = float(p.get("asks", [{}])[0].get("price", 0))
            mid = (bid + ask) / 2
            return {
                "symbol": symbol,
                "last_price": mid,
                "bid": bid,
                "ask": ask,
                "high_24h": 0,  # requires separate candle call
                "low_24h": 0,
                "volume_24h": 0,
                "change_pct_24h": 0,
                "timestamp": p.get("time", datetime.now(timezone.utc).isoformat()),
            }
        except Exception as exc:
            logger.warning("OANDA get_ticker fallback: %s", exc)
            return self._get_simulated_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        if not self._connected:
            return self._get_simulated_ohlcv(symbol, timeframe, limit)
        try:
            instrument = self._normalize_symbol(symbol)
            gran = _TF_MAP.get(timeframe, "H1")
            data = await self._request(
                "GET",
                f"/v3/instruments/{instrument}/candles",
                params={"granularity": gran, "count": limit, "price": "M"},
            )
            candles = []
            for c in data.get("candles", []):
                mid = c.get("mid", {})
                candles.append(
                    {
                        "timestamp": c.get("time", ""),
                        "open": float(mid.get("o", 0)),
                        "high": float(mid.get("h", 0)),
                        "low": float(mid.get("l", 0)),
                        "close": float(mid.get("c", 0)),
                        "volume": c.get("volume", 0),
                    }
                )
            return candles
        except Exception as exc:
            logger.warning("OANDA get_ohlcv fallback: %s", exc)
            return self._get_simulated_ohlcv(symbol, timeframe, limit)

    # ── trading ───────────────────────────────────────────────────────

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Convert symbol formats to OANDA's underscore format: EUR/USD → EUR_USD."""
        return symbol.replace("/", "_")

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: float | None = None,
        stop_distance: float | None = None,
        limit_distance: float | None = None,
        guaranteed_stop: bool = False,
        trailing_stop: bool = False,
        trailing_step: float | None = None,
    ) -> dict:
        """Place an order via OANDA v20 API.

        Args:
            stop_distance: stop-loss distance from fill price (pips).
            limit_distance: take-profit distance from fill price (pips).
            guaranteed_stop: if True, use guaranteedStopLossOnFill.
            trailing_stop: if True, attach a trailing stop.
            trailing_step: trailing stop distance (pips).
        """
        if not self._connected:
            return self._get_simulated_order(symbol, side, quantity, order_type, price)
        try:
            # OANDA requires underscore-separated instruments (EUR_USD, not EUR/USD)
            instrument = self._normalize_symbol(symbol)
            # OANDA requires NEGATIVE units for sell orders
            units = quantity if side.lower() == "buy" else -quantity
            order_body: dict = {
                "instrument": instrument,
                "units": str(int(units)),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
            }
            if order_type.lower() == "market":
                order_body["type"] = "MARKET"
            elif order_type.lower() == "limit":
                order_body["type"] = "LIMIT"
                order_body["price"] = str(price)
                order_body["timeInForce"] = "GTC"
            elif order_type.lower() == "stop":
                order_body["type"] = "STOP"
                order_body["price"] = str(price)
                order_body["timeInForce"] = "GTC"

            # OANDA uses *OnFill suffix for stops/TP attached to orders
            if guaranteed_stop and stop_distance is not None:
                order_body["guaranteedStopLossOnFill"] = {"distance": str(stop_distance)}
            elif stop_distance is not None:
                order_body["stopLossOnFill"] = {"distance": str(stop_distance)}
            if limit_distance is not None:
                order_body["takeProfitOnFill"] = {"distance": str(limit_distance)}
            if trailing_stop and trailing_step is not None:
                order_body["trailingStopLossOnFill"] = {"distance": str(trailing_step)}

            data = await self._request(
                "POST",
                f"/v3/accounts/{self._account_id}/orders",
                json={"order": order_body},
            )
            fill = data.get("orderFillTransaction", {})
            create = data.get("orderCreateTransaction", {})
            order_id = fill.get("id") or create.get("id", "")
            return {
                "order_id": str(order_id),
                "status": "filled" if fill else "submitted",
                "filled_qty": abs(float(fill.get("units", 0))) if fill else 0,
                "filled_price": float(fill.get("price", 0)) if fill else 0,
                "stop_distance": stop_distance,
                "limit_distance": limit_distance,
            }
        except Exception as exc:
            logger.error("OANDA place_order error: %s", exc)
            return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

    async def cancel_order(self, order_id: str) -> dict:
        if not self._connected:
            return {"order_id": order_id, "status": "cancelled"}
        try:
            await self._request("PUT", f"/v3/accounts/{self._account_id}/orders/{order_id}/cancel")
            return {"order_id": order_id, "status": "cancelled"}
        except Exception as exc:
            logger.error("OANDA cancel_order error: %s", exc)
            return {"order_id": order_id, "status": "error", "message": str(exc)}

    async def get_positions(self) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", f"/v3/accounts/{self._account_id}/openPositions")
            positions = []
            for p in data.get("positions", []):
                long_units = float(p.get("long", {}).get("units", 0))
                short_units = float(p.get("short", {}).get("units", 0))
                if long_units > 0:
                    positions.append(
                        {
                            "symbol": p.get("instrument", ""),
                            "side": "buy",
                            "quantity": long_units,
                            "entry_price": float(p.get("long", {}).get("averagePrice", 0)),
                            "current_price": 0,
                            "unrealised_pnl": float(p.get("long", {}).get("unrealizedPL", 0)),
                        }
                    )
                if short_units < 0:
                    positions.append(
                        {
                            "symbol": p.get("instrument", ""),
                            "side": "sell",
                            "quantity": abs(short_units),
                            "entry_price": float(p.get("short", {}).get("averagePrice", 0)),
                            "current_price": 0,
                            "unrealised_pnl": float(p.get("short", {}).get("unrealizedPL", 0)),
                        }
                    )
            return positions
        except Exception as exc:
            logger.error("OANDA get_positions error: %s", exc)
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        if not self._connected:
            return self._get_simulated_order_book(symbol, limit)
        try:
            data = await self._request("GET", f"/v3/instruments/{symbol}/orderBook")
            book = data.get("orderBook", {})
            buckets = book.get("buckets", [])
            mid = float(book.get("price", 0))
            bids = []
            asks = []
            for b in buckets:
                p = float(b.get("price", 0))
                long_pct = float(b.get("longCountPercent", 0))
                short_pct = float(b.get("shortCountPercent", 0))
                if p < mid:
                    bids.append([p, long_pct])
                else:
                    asks.append([p, short_pct])
            return {"bids": bids[:limit], "asks": asks[:limit]}
        except Exception as exc:
            logger.warning("OANDA get_order_book fallback: %s", exc)
            return self._get_simulated_order_book(symbol, limit)

    async def search_instruments(self, query: str) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request(
                "GET",
                f"/v3/accounts/{self._account_id}/instruments",
            )
            results = []
            query_lower = query.lower()
            for inst in data.get("instruments", []):
                name = inst.get("name", "")
                display = inst.get("displayName", "")
                if query_lower in name.lower() or query_lower in display.lower():
                    results.append(
                        {
                            "symbol": name,
                            "name": display,
                            "type": inst.get("type", ""),
                            "exchange": "OANDA",
                        }
                    )
            return results
        except Exception as exc:
            logger.error("OANDA search_instruments error: %s", exc)
            return []
