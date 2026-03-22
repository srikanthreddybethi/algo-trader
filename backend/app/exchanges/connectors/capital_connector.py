"""Capital.com connector — forex, shares, indices, crypto CFDs, spread betting.

REST API: https://api-capital.backend-capital.com/api/v1
Auth: API key + password → session token (X-SECURITY-TOKEN + CST headers).
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

_LIVE_URL = "https://api-capital.backend-capital.com/api/v1"
_DEMO_URL = "https://demo-api-capital.backend-capital.com/api/v1"

_TF_MAP = {
    "1m": "MINUTE",
    "5m": "MINUTE_5",
    "15m": "MINUTE_15",
    "30m": "MINUTE_30",
    "1h": "HOUR",
    "4h": "HOUR_4",
    "1d": "DAY",
    "1w": "WEEK",
}


class CapitalConnector(BaseConnector):
    """Capital.com REST API connector."""

    name = "capital"
    display_name = "Capital.com"
    connector_type = "spread_betting"
    supported_asset_types = ["forex", "shares", "indices", "crypto", "commodities"]
    default_pairs = [
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AAPL",
        "TSLA",
        "US500",
        "UK100",
        "XAUUSD",
    ]

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._cst: str = ""
        self._security_token: str = ""
        self._rate_limiter = asyncio.Semaphore(10)

    @classmethod
    def get_config_fields(cls) -> list:
        return [
            {"name": "api_key", "label": "API Key", "type": "text", "required": True},
            {"name": "identifier", "label": "Email / Identifier", "type": "text", "required": True},
            {"name": "password", "label": "Password", "type": "password", "required": True},
            {"name": "is_demo", "label": "Demo Account", "type": "boolean", "default": True},
        ]

    # ── connection ────────────────────────────────────────────────────

    async def connect(self, credentials: dict) -> dict:
        try:
            api_key = credentials["api_key"]
            identifier = credentials["identifier"]
            password = credentials["password"]
            self._is_demo = credentials.get("is_demo", True)
        except KeyError as exc:
            return {"status": "error", "message": f"Missing credential: {exc}"}

        base_url = _DEMO_URL if self._is_demo else _LIVE_URL
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30)

        try:
            resp = await self._client.post(
                "/session",
                json={"identifier": identifier, "password": password},
                headers={
                    "X-CAP-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            self._cst = resp.headers.get("CST", "")
            self._security_token = resp.headers.get("X-SECURITY-TOKEN", "")
            self._session_headers = {
                "X-CAP-API-KEY": api_key,
                "CST": self._cst,
                "X-SECURITY-TOKEN": self._security_token,
                "Content-Type": "application/json",
            }
            self._credentials = credentials
            self._connected = True
            logger.info("Capital.com: connected (demo=%s)", self._is_demo)
            return {"status": "connected", "demo": self._is_demo}
        except httpx.HTTPStatusError as exc:
            logger.error("Capital.com auth failed: %s", exc.response.text)
            return {"status": "error", "message": f"Auth failed: {exc.response.status_code}"}
        except Exception as exc:
            logger.error("Capital.com connect error: %s", exc)
            return {"status": "error", "message": str(exc)}

    async def disconnect(self) -> None:
        if self._client and self._connected:
            try:
                await self._client.delete("/session", headers=self._session_headers)
            except Exception:
                pass
            await self._client.aclose()
        self._connected = False
        self._client = None
        self._cst = ""
        self._security_token = ""
        logger.info("Capital.com: disconnected")

    # ── private helpers ───────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self._connected or not self._client:
            raise ConnectionError("Capital.com connector is not connected")
        await self._rate_limit()
        try:
            resp = await self._client.request(method, path, headers=self._session_headers, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        finally:
            self._release_rate_limit()

    # ── account ───────────────────────────────────────────────────────

    async def get_account_info(self) -> dict:
        if not self._connected:
            return self._get_simulated_account()
        try:
            data = await self._request("GET", "/accounts")
            accounts = data.get("accounts", [])
            acct = accounts[0] if accounts else {}
            balance = acct.get("balance", {})
            return {
                "balance": float(balance.get("balance", 0)),
                "equity": float(balance.get("balance", 0)) + float(balance.get("profitLoss", 0)),
                "margin_used": float(balance.get("deposit", 0)),
                "margin_available": float(balance.get("available", 0)),
                "unrealised_pnl": float(balance.get("profitLoss", 0)),
                "currency": acct.get("currency", "GBP"),
            }
        except Exception as exc:
            logger.error("Capital.com get_account_info error: %s", exc)
            return self._get_simulated_account()

    # ── market data ───────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        if not self._connected:
            return self._get_simulated_ticker(symbol)
        try:
            data = await self._request("GET", f"/markets/{symbol}")
            snapshot = data.get("snapshot", {})
            return {
                "symbol": symbol,
                "last_price": float(snapshot.get("offer", 0)),
                "bid": float(snapshot.get("bid", 0)),
                "ask": float(snapshot.get("offer", 0)),
                "high_24h": float(snapshot.get("high", 0)),
                "low_24h": float(snapshot.get("low", 0)),
                "volume_24h": 0,
                "change_pct_24h": float(snapshot.get("percentageChange", 0)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning("Capital.com get_ticker fallback: %s", exc)
            return self._get_simulated_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        if not self._connected:
            return self._get_simulated_ohlcv(symbol, timeframe, limit)
        try:
            resolution = _TF_MAP.get(timeframe, "HOUR")
            data = await self._request(
                "GET",
                f"/prices/{symbol}",
                params={"resolution": resolution, "max": limit},
            )
            candles = []
            for p in data.get("prices", []):
                o = p.get("openPrice", {})
                h = p.get("highPrice", {})
                l_p = p.get("lowPrice", {})
                c = p.get("closePrice", {})
                candles.append(
                    {
                        "timestamp": p.get("snapshotTimeUTC", ""),
                        "open": (float(o.get("bid", 0)) + float(o.get("ask", 0))) / 2,
                        "high": (float(h.get("bid", 0)) + float(h.get("ask", 0))) / 2,
                        "low": (float(l_p.get("bid", 0)) + float(l_p.get("ask", 0))) / 2,
                        "close": (float(c.get("bid", 0)) + float(c.get("ask", 0))) / 2,
                        "volume": p.get("lastTradedVolume", 0),
                    }
                )
            return candles
        except Exception as exc:
            logger.warning("Capital.com get_ohlcv fallback: %s", exc)
            return self._get_simulated_ohlcv(symbol, timeframe, limit)

    # ── trading ───────────────────────────────────────────────────────

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
        """Place a spread bet / CFD order on Capital.com.

        For spread bets *quantity* is the stake in £/point.

        Args:
            stop_distance: stop-loss distance in points from entry.
            limit_distance: take-profit distance in points from entry.
            guaranteed_stop: if True, use a guaranteed stop (premium applies).
            trailing_stop: if True, attach a trailing stop.
            trailing_step: increment for the trailing stop (points).
        """
        if not self._connected:
            return self._get_simulated_order(symbol, side, quantity, order_type, price)
        try:
            direction = "BUY" if side.lower() == "buy" else "SELL"
            payload: dict = {
                "epic": symbol,
                "direction": direction,
                "size": quantity,
                "guaranteedStop": guaranteed_stop,
            }
            if stop_distance is not None:
                payload["stopDistance"] = stop_distance
            if limit_distance is not None:
                payload["profitDistance"] = limit_distance
            if trailing_stop:
                payload["trailingStop"] = True
                payload["trailingStopIncrement"] = trailing_step or 1.0

            if order_type.lower() == "market":
                data = await self._request("POST", "/positions", json=payload)
            else:
                payload["type"] = order_type.upper()
                if price:
                    payload["level"] = price
                data = await self._request("POST", "/workingorders", json=payload)

            deal_ref = data.get("dealReference", "")
            try:
                confirm = await self._request("GET", f"/confirms/{deal_ref}")
            except Exception:
                confirm = {}
            return {
                "order_id": confirm.get("dealId", deal_ref),
                "status": confirm.get("dealStatus", "submitted").lower(),
                "filled_qty": float(confirm.get("size", quantity)),
                "filled_price": float(confirm.get("level", 0)),
                "guaranteed_stop": guaranteed_stop,
                "stop_distance": stop_distance,
                "limit_distance": limit_distance,
            }
        except Exception as exc:
            logger.error("Capital.com place_order error: %s", exc)
            return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

    async def cancel_order(self, order_id: str) -> dict:
        if not self._connected:
            return {"order_id": order_id, "status": "cancelled"}
        try:
            await self._request("DELETE", f"/workingorders/{order_id}")
            return {"order_id": order_id, "status": "cancelled"}
        except Exception as exc:
            logger.error("Capital.com cancel_order error: %s", exc)
            return {"order_id": order_id, "status": "error", "message": str(exc)}

    async def get_positions(self) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/positions")
            positions = []
            for p in data.get("positions", []):
                pos = p.get("position", {})
                market = p.get("market", {})
                positions.append(
                    {
                        "symbol": market.get("epic", ""),
                        "side": pos.get("direction", "BUY").lower(),
                        "quantity": float(pos.get("size", 0)),
                        "entry_price": float(pos.get("level", 0)),
                        "current_price": float(market.get("offer", 0)) if pos.get("direction") == "BUY" else float(market.get("bid", 0)),
                        "unrealised_pnl": float(pos.get("profit", 0)),
                        "deal_id": pos.get("dealId", ""),
                    }
                )
            return positions
        except Exception as exc:
            logger.error("Capital.com get_positions error: %s", exc)
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        return self._get_simulated_order_book(symbol, limit)

    async def search_instruments(self, query: str) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/markets", params={"searchTerm": query, "limit": 50})
            results = []
            for m in data.get("markets", []):
                results.append(
                    {
                        "symbol": m.get("epic", ""),
                        "name": m.get("instrumentName", ""),
                        "type": m.get("instrumentType", ""),
                        "exchange": "Capital.com",
                    }
                )
            return results
        except Exception as exc:
            logger.error("Capital.com search_instruments error: %s", exc)
            return []

    # ── market info (spread-bet specific) ─────────────────────────────

    async def get_market_info(self, epic: str) -> dict:
        """Get market details including margin, min stop distance, spread."""
        if not self._connected:
            return self._get_simulated_market_info(epic)
        try:
            data = await self._request("GET", f"/markets/{epic}")
            instrument = data.get("instrument", {})
            snapshot = data.get("snapshot", {})
            min_stop_raw = instrument.get("minNormalStopOrLimitDistance", {})
            gstop_raw = instrument.get("limitedRiskPremium", {})
            min_deal_raw = instrument.get("minDealSize", {})
            bid = float(snapshot.get("bid", 0))
            offer = float(snapshot.get("offer", 0))
            return {
                "epic": epic,
                "name": instrument.get("name", ""),
                "margin_factor": float(instrument.get("marginFactor", 5)),
                "margin_factor_unit": instrument.get("marginFactorUnit", "PERCENTAGE"),
                "min_stop_distance": float(min_stop_raw.get("value", 0)) if isinstance(min_stop_raw, dict) else float(min_stop_raw or 0),
                "guaranteed_stop_premium": float(gstop_raw.get("value", 0)) if isinstance(gstop_raw, dict) else float(gstop_raw or 0),
                "min_deal_size": float(min_deal_raw.get("value", 0.5)) if isinstance(min_deal_raw, dict) else float(min_deal_raw or 0.5),
                "bid": bid,
                "offer": offer,
                "spread": round(offer - bid, 5),
                "market_status": snapshot.get("marketStatus", "UNKNOWN"),
            }
        except Exception as exc:
            logger.warning("Capital.com get_market_info fallback: %s", exc)
            return self._get_simulated_market_info(epic)

    def _get_simulated_market_info(self, epic: str) -> dict:
        """Return simulated market info for paper trading."""
        ticker = self._get_simulated_ticker(epic)
        spread = round(ticker["ask"] - ticker["bid"], 5)
        return {
            "epic": epic,
            "name": epic,
            "margin_factor": 5.0,
            "margin_factor_unit": "PERCENTAGE",
            "min_stop_distance": max(5, int(spread * 10)),
            "guaranteed_stop_premium": 0.3,
            "min_deal_size": 0.5,
            "bid": ticker["bid"],
            "offer": ticker["ask"],
            "spread": spread,
            "market_status": "TRADEABLE",
        }
