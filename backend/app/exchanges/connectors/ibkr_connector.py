"""Interactive Brokers connector — Client Portal REST API.

Requires IB Gateway or TWS running locally.
REST base: https://localhost:5000/v1/api
Markets: Stocks, options, futures, forex, bonds, ETFs — 170 markets, 40 countries.
"""

import asyncio
import logging
import ssl
import time
from datetime import datetime, timezone

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

_LIVE_URL = "https://localhost:5000/v1/api"
_PAPER_URL = "https://localhost:5000/v1/api"  # same URL; mode set in IB Gateway config

_TF_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
}


class IBKRConnector(BaseConnector):
    """Interactive Brokers Client Portal REST connector."""

    name = "ibkr"
    display_name = "Interactive Brokers"
    connector_type = "multi_asset"
    supported_asset_types = ["stocks", "options", "futures", "forex", "bonds", "etfs"]
    default_pairs = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "EUR.USD",
        "GBP.USD",
        "SPY",
    ]

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._account_id: str = ""
        self._rate_limiter = asyncio.Semaphore(20)

    @classmethod
    def get_config_fields(cls) -> list:
        return [
            {"name": "gateway_url", "label": "Gateway URL", "type": "text", "required": False, "default": "https://localhost:5000"},
            {"name": "account_id", "label": "Account ID", "type": "text", "required": False},
            {"name": "is_demo", "label": "Paper Trading", "type": "boolean", "default": True},
        ]

    # ── connection ────────────────────────────────────────────────────

    async def connect(self, credentials: dict) -> dict:
        self._is_demo = credentials.get("is_demo", True)
        gateway = credentials.get("gateway_url", "https://localhost:5000").rstrip("/")
        base_url = f"{gateway}/v1/api"

        # IB Gateway uses a self-signed cert — skip verification for local gateway
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        self._client = httpx.AsyncClient(base_url=base_url, timeout=30, verify=ssl_ctx)

        try:
            # Tickle to keep session alive / validate
            resp = await self._client.post("/tickle")
            resp.raise_for_status()

            # Initialize brokerage session (required before trading)
            try:
                init_resp = await self._client.post("/iserver/auth/ssodh/init")
                init_resp.raise_for_status()
                logger.info("IBKR: brokerage session initialized")
            except Exception as init_exc:
                logger.warning("IBKR: brokerage session init skipped (%s) — may already be active", init_exc)

            # Get accounts
            acct_resp = await self._client.get("/portfolio/accounts")
            acct_resp.raise_for_status()
            accounts = acct_resp.json()
            if not accounts:
                return {"status": "error", "message": "No accounts found — is IB Gateway running?"}

            self._account_id = credentials.get("account_id") or accounts[0].get("accountId", "")
            self._credentials = credentials
            self._connected = True
            logger.info("IBKR: connected (account=%s)", self._account_id)
            return {"status": "connected", "account_id": self._account_id}
        except httpx.ConnectError:
            msg = "Cannot reach IB Gateway — make sure TWS or IB Gateway is running"
            logger.error("IBKR: %s", msg)
            return {"status": "error", "message": msg}
        except Exception as exc:
            logger.error("IBKR connect error: %s", exc)
            return {"status": "error", "message": str(exc)}

    async def disconnect(self) -> None:
        if self._client and self._connected:
            try:
                await self._client.post("/logout")
            except Exception:
                pass
            await self._client.aclose()
        self._connected = False
        self._client = None
        logger.info("IBKR: disconnected")

    # ── private helpers ───────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        if not self._connected or not self._client:
            raise ConnectionError("IBKR connector is not connected")
        await self._rate_limit()
        try:
            resp = await self._client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        finally:
            self._release_rate_limit()

    async def _resolve_conid(self, symbol: str) -> int | None:
        """Resolve a ticker symbol to an IB contract ID."""
        try:
            results = await self._request("GET", "/iserver/secdef/search", params={"symbol": symbol})
            if results and isinstance(results, list):
                return results[0].get("conid")
        except Exception as exc:
            logger.warning("IBKR _resolve_conid(%s) failed: %s", symbol, exc)
        return None

    # ── account ───────────────────────────────────────────────────────

    async def get_account_info(self) -> dict:
        if not self._connected:
            return self._get_simulated_account()
        try:
            data = await self._request("GET", f"/portfolio/{self._account_id}/summary")
            return {
                "balance": data.get("totalcashvalue", {}).get("amount", 0),
                "equity": data.get("netliquidation", {}).get("amount", 0),
                "margin_used": data.get("initmarginreq", {}).get("amount", 0),
                "margin_available": data.get("availablefunds", {}).get("amount", 0),
                "unrealised_pnl": data.get("unrealizedpnl", {}).get("amount", 0),
                "currency": data.get("netliquidation", {}).get("currency", "USD"),
            }
        except Exception as exc:
            logger.error("IBKR get_account_info error: %s", exc)
            return self._get_simulated_account()

    # ── market data ───────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        if not self._connected:
            return self._get_simulated_ticker(symbol)
        try:
            conid = await self._resolve_conid(symbol)
            if not conid:
                return self._get_simulated_ticker(symbol)
            data = await self._request("GET", f"/iserver/marketdata/snapshot", params={"conids": str(conid), "fields": "31,84,85,86,87,88"})
            snap = data[0] if isinstance(data, list) and data else {}
            last = float(snap.get("31", 0))
            bid = float(snap.get("84", 0))
            ask = float(snap.get("86", 0))
            high = float(snap.get("87", 0))
            low = float(snap.get("88", 0))
            volume = float(snap.get("85", 0))
            return {
                "symbol": symbol,
                "last_price": last,
                "bid": bid,
                "ask": ask,
                "high_24h": high,
                "low_24h": low,
                "volume_24h": volume,
                "change_pct_24h": round((last - low) / low * 100 if low else 0, 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning("IBKR get_ticker fallback: %s", exc)
            return self._get_simulated_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        if not self._connected:
            return self._get_simulated_ohlcv(symbol, timeframe, limit)
        try:
            conid = await self._resolve_conid(symbol)
            if not conid:
                return self._get_simulated_ohlcv(symbol, timeframe, limit)
            bar = _TF_MAP.get(timeframe, "1h")
            data = await self._request(
                "GET",
                f"/iserver/marketdata/history",
                params={"conid": conid, "period": "1d", "bar": bar},
            )
            candles = []
            for pt in data.get("data", []):
                candles.append(
                    {
                        "timestamp": datetime.fromtimestamp(pt.get("t", 0) / 1000, tz=timezone.utc).isoformat(),
                        "open": pt.get("o", 0),
                        "high": pt.get("h", 0),
                        "low": pt.get("l", 0),
                        "close": pt.get("c", 0),
                        "volume": pt.get("v", 0),
                    }
                )
            return candles[-limit:]
        except Exception as exc:
            logger.warning("IBKR get_ohlcv fallback: %s", exc)
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
            conid = await self._resolve_conid(symbol)
            if not conid:
                return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}
            order_payload = {
                "conid": conid,
                "orderType": order_type.upper() if order_type != "market" else "MKT",
                "side": side.upper(),
                "quantity": quantity,
                "tif": "DAY",
            }
            if price and order_type.lower() in ("limit", "lmt"):
                order_payload["orderType"] = "LMT"
                order_payload["price"] = price
            elif price and order_type.lower() in ("stop", "stp"):
                order_payload["orderType"] = "STP"
                order_payload["auxPrice"] = price

            data = await self._request(
                "POST",
                f"/iserver/account/{self._account_id}/orders",
                json={"orders": [order_payload]},
            )
            # IB may return confirmation prompts — auto-confirm
            if isinstance(data, list) and data and "id" in data[0]:
                confirm_id = data[0]["id"]
                data = await self._request(
                    "POST",
                    f"/iserver/reply/{confirm_id}",
                    json={"confirmed": True},
                )

            order_id = ""
            if isinstance(data, list) and data:
                order_id = str(data[0].get("order_id", data[0].get("orderId", "")))
            return {
                "order_id": order_id,
                "status": "submitted",
                "filled_qty": 0,
                "filled_price": 0,
            }
        except Exception as exc:
            logger.error("IBKR place_order error: %s", exc)
            return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

    async def cancel_order(self, order_id: str) -> dict:
        if not self._connected:
            return {"order_id": order_id, "status": "cancelled"}
        try:
            await self._request("DELETE", f"/iserver/account/{self._account_id}/order/{order_id}")
            return {"order_id": order_id, "status": "cancelled"}
        except Exception as exc:
            logger.error("IBKR cancel_order error: %s", exc)
            return {"order_id": order_id, "status": "error", "message": str(exc)}

    async def get_positions(self) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", f"/portfolio/{self._account_id}/positions/0")
            positions = []
            for p in data if isinstance(data, list) else []:
                positions.append(
                    {
                        "symbol": p.get("contractDesc", ""),
                        "side": "buy" if p.get("position", 0) > 0 else "sell",
                        "quantity": abs(p.get("position", 0)),
                        "entry_price": p.get("avgCost", 0),
                        "current_price": p.get("mktPrice", 0),
                        "unrealised_pnl": p.get("unrealizedPnl", 0),
                        "conid": p.get("conid", ""),
                    }
                )
            return positions
        except Exception as exc:
            logger.error("IBKR get_positions error: %s", exc)
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        # Client Portal API does not expose full L2 book
        return self._get_simulated_order_book(symbol, limit)

    async def search_instruments(self, query: str) -> list:
        if not self._connected:
            return []
        try:
            data = await self._request("GET", "/iserver/secdef/search", params={"symbol": query})
            results = []
            for item in data if isinstance(data, list) else []:
                results.append(
                    {
                        "symbol": item.get("symbol", ""),
                        "name": item.get("companyName", item.get("description", "")),
                        "type": item.get("secType", ""),
                        "conid": item.get("conid", ""),
                        "exchange": "IBKR",
                    }
                )
            return results
        except Exception as exc:
            logger.error("IBKR search_instruments error: %s", exc)
            return []
