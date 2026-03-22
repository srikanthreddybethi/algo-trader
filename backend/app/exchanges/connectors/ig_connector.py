"""IG Group connector — spread betting & CFD trading.

REST API docs: https://labs.ig.com/rest-trading-api-reference
Auth: API key + identifier + password → CST + X-SECURITY-TOKEN headers.
Rate limit: ~40 trade requests/min.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

_LIVE_URL = "https://api.ig.com/gateway/deal"
_DEMO_URL = "https://demo-api.ig.com/gateway/deal"

# Timeframe map: our canonical names → IG resolution codes
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


class IGConnector(BaseConnector):
    """IG Group spread-betting / CFD connector (REST + httpx)."""

    name = "ig"
    display_name = "IG Group"
    connector_type = "spread_betting"
    supported_asset_types = ["forex", "indices", "commodities", "shares", "crypto"]
    default_pairs = [
        "CS.D.EURUSD.CFD.IP",
        "CS.D.GBPUSD.CFD.IP",
        "CS.D.USDJPY.CFD.IP",
        "IX.D.FTSE.DAILY.IP",
        "IX.D.DAX.DAILY.IP",
        "IX.D.SPTRD.DAILY.IP",
        "CS.D.USCGC.TODAY.IP",
        "CS.D.USCSI.TODAY.IP",
    ]

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._cst: str = ""
        self._security_token: str = ""
        self._account_id: str = ""
        # ~40 req/min → semaphore of 10 concurrent + small delay
        self._rate_limiter = asyncio.Semaphore(10)
        self._min_request_interval = 1.5  # seconds between bursts

    @classmethod
    def get_config_fields(cls) -> list:
        return [
            {"name": "api_key", "label": "API Key", "type": "text", "required": True},
            {"name": "identifier", "label": "Username / Identifier", "type": "text", "required": True},
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
                    "X-IG-API-KEY": api_key,
                    "Content-Type": "application/json; charset=UTF-8",
                    "Accept": "application/json; charset=UTF-8",
                    "VERSION": "3",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._cst = resp.headers.get("CST", "")
            self._security_token = resp.headers.get("X-SECURITY-TOKEN", "")
            self._account_id = data.get("currentAccountId", "")
            self._session_headers = {
                "X-IG-API-KEY": api_key,
                "CST": self._cst,
                "X-SECURITY-TOKEN": self._security_token,
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json; charset=UTF-8",
            }
            self._credentials = credentials
            self._connected = True
            logger.info("IG: connected (account=%s, demo=%s)", self._account_id, self._is_demo)
            return {"status": "connected", "account_id": self._account_id, "demo": self._is_demo}
        except httpx.HTTPStatusError as exc:
            logger.error("IG auth failed: %s", exc.response.text)
            return {"status": "error", "message": f"Auth failed: {exc.response.status_code}"}
        except Exception as exc:
            logger.error("IG connect error: %s", exc)
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
        logger.info("IG: disconnected")

    # ── private helpers ───────────────────────────────────────────────

    async def _request(self, method: str, path: str, *, version: str = "1", **kwargs) -> dict:
        if not self._connected or not self._client:
            raise ConnectionError("IG connector is not connected")
        await self._rate_limit()
        try:
            headers = {**self._session_headers, "VERSION": version}
            resp = await self._client.request(method, path, headers=headers, **kwargs)
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
            acct = next((a for a in accounts if a.get("accountId") == self._account_id), accounts[0] if accounts else {})
            balance_info = acct.get("balance", {})
            return {
                "balance": balance_info.get("balance", 0),
                "equity": balance_info.get("balance", 0) + balance_info.get("profitLoss", 0),
                "margin_used": balance_info.get("deposit", 0),
                "margin_available": balance_info.get("available", 0),
                "unrealised_pnl": balance_info.get("profitLoss", 0),
                "currency": acct.get("currency", "GBP"),
            }
        except Exception as exc:
            logger.error("IG get_account_info error: %s", exc)
            return self._get_simulated_account()

    # ── market data ───────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        if not self._connected:
            return self._get_simulated_ticker(symbol)
        try:
            data = await self._request("GET", f"/markets/{symbol}", version="3")
            snapshot = data.get("snapshot", {})
            return {
                "symbol": symbol,
                "last_price": snapshot.get("offer", 0),
                "bid": snapshot.get("bid", 0),
                "ask": snapshot.get("offer", 0),
                "high_24h": snapshot.get("high", 0),
                "low_24h": snapshot.get("low", 0),
                "volume_24h": 0,  # IG doesn't expose volume directly
                "change_pct_24h": snapshot.get("percentageChange", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning("IG get_ticker fallback to simulated: %s", exc)
            return self._get_simulated_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        if not self._connected:
            return self._get_simulated_ohlcv(symbol, timeframe, limit)
        try:
            resolution = _TF_MAP.get(timeframe, "HOUR")
            data = await self._request(
                "GET",
                f"/prices/{symbol}",
                version="3",
                params={"resolution": resolution, "max": limit, "pageSize": limit},
            )
            candles = []
            for p in data.get("prices", []):
                close_price = p.get("closePrice", {})
                open_price = p.get("openPrice", {})
                high_price = p.get("highPrice", {})
                low_price = p.get("lowPrice", {})
                candles.append(
                    {
                        "timestamp": p.get("snapshotTimeUTC", ""),
                        "open": (open_price.get("bid", 0) + open_price.get("ask", 0)) / 2,
                        "high": (high_price.get("bid", 0) + high_price.get("ask", 0)) / 2,
                        "low": (low_price.get("bid", 0) + low_price.get("ask", 0)) / 2,
                        "close": (close_price.get("bid", 0) + close_price.get("ask", 0)) / 2,
                        "volume": p.get("lastTradedVolume", 0),
                    }
                )
            return candles
        except Exception as exc:
            logger.warning("IG get_ohlcv fallback to simulated: %s", exc)
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
        """Place a spread bet / CFD order on IG.

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
                "orderType": order_type.upper() if order_type != "market" else "MARKET",
                "guaranteedStop": guaranteed_stop,
                "forceOpen": True,
                "currencyCode": "GBP",
            }
            if price and order_type.lower() in ("limit", "stop"):
                payload["level"] = price
                payload["type"] = order_type.upper()
            if stop_distance is not None:
                payload["stopDistance"] = stop_distance
            if limit_distance is not None:
                payload["limitDistance"] = limit_distance
            if trailing_stop:
                payload["trailingStop"] = True
                payload["trailingStopIncrement"] = trailing_step or 1.0

            data = await self._request("POST", "/positions/otc", version="2", json=payload)
            deal_ref = data.get("dealReference", "")

            # Confirm the deal
            confirm = await self._request("GET", f"/confirms/{deal_ref}", version="1")
            return {
                "order_id": confirm.get("dealId", deal_ref),
                "status": confirm.get("dealStatus", "UNKNOWN").lower(),
                "filled_qty": confirm.get("size", quantity),
                "filled_price": confirm.get("level", 0),
                "guaranteed_stop": guaranteed_stop,
                "stop_distance": stop_distance,
                "limit_distance": limit_distance,
            }
        except Exception as exc:
            logger.error("IG place_order error: %s", exc)
            return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

    async def cancel_order(self, order_id: str) -> dict:
        if not self._connected:
            return {"order_id": order_id, "status": "cancelled"}
        try:
            # IG uses DELETE with _method override for working orders
            await self._request(
                "POST",
                f"/workingorders/otc/{order_id}",
                version="2",
                headers={"_method": "DELETE"},
            )
            return {"order_id": order_id, "status": "cancelled"}
        except Exception as exc:
            logger.error("IG cancel_order error: %s", exc)
            return {"order_id": order_id, "status": "error", "message": str(exc)}

    async def get_positions(self) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/positions", version="2")
            positions = []
            for p in data.get("positions", []):
                pos = p.get("position", {})
                market = p.get("market", {})
                positions.append(
                    {
                        "symbol": market.get("epic", ""),
                        "side": pos.get("direction", "").lower(),
                        "quantity": pos.get("size", 0),
                        "entry_price": pos.get("level", 0),
                        "current_price": market.get("offer", 0) if pos.get("direction") == "BUY" else market.get("bid", 0),
                        "unrealised_pnl": pos.get("profit", 0),
                        "deal_id": pos.get("dealId", ""),
                    }
                )
            return positions
        except Exception as exc:
            logger.error("IG get_positions error: %s", exc)
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        # IG doesn't expose a traditional order book — return simulated
        return self._get_simulated_order_book(symbol, limit)

    async def search_instruments(self, query: str) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/markets", version="1", params={"searchTerm": query})
            results = []
            for m in data.get("markets", []):
                results.append(
                    {
                        "symbol": m.get("epic", ""),
                        "name": m.get("instrumentName", ""),
                        "type": m.get("instrumentType", ""),
                        "exchange": "IG",
                    }
                )
            return results
        except Exception as exc:
            logger.error("IG search_instruments error: %s", exc)
            return []

    # ── market info (spread-bet specific) ─────────────────────────────

    async def get_market_info(self, epic: str) -> dict:
        """Get market details including margin requirements, min stop distance, spread."""
        if not self._connected:
            return self._get_simulated_market_info(epic)
        try:
            data = await self._request("GET", f"/markets/{epic}", version="3")
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
            logger.warning("IG get_market_info fallback to simulated: %s", exc)
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
