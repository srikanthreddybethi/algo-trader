"""CMC Markets connector — requires MT5 bridge or CMC's platform API.

NOTE: CMC Markets does not offer a public REST API for direct trading.
Trading is supported via MT5 gateway or simulated mode for paper trading.

This connector implements an MT5 gateway bridge approach:
  1. Connect to CMC's MT5 server via a user-hosted MT5-to-REST bridge proxy.
  2. Fall back to simulated mode when no bridge is available (paper trading).

Requires: CMC Markets MT5 account + local MT5 bridge proxy (e.g., mt5-rest).
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

# MT5 bridge proxy URL (user-hosted or third-party MT5-to-REST bridge)
_DEFAULT_BRIDGE_URL = "http://localhost:8228/api/v1"


class CMCConnector(BaseConnector):
    """CMC Markets connector via MetaTrader 5 bridge.

    CMC Markets does NOT have a public REST API like IG or Capital.com.
    This connector supports two modes:
    1. **MT5 bridge mode**: Connects to a user-hosted MT5-to-REST bridge
       proxy that relays orders/data to CMC's MT5 servers.
    2. **Simulated mode**: When no bridge is available, provides paper
       trading with simulated data.

    Requires a CMC Markets MT5 account for live trading.
    """

    name = "cmc"
    display_name = "CMC Markets"
    connector_type = "spread_betting"
    supported_asset_types = ["forex", "indices", "commodities", "shares", "crypto"]
    default_pairs = [
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "UK100",
        "US30",
        "GER40",
        "XAUUSD",
        "USOIL",
    ]

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._mt5_account: int = 0
        self._bridge_url: str = _DEFAULT_BRIDGE_URL
        self._bridge_available: bool = False
        self._rate_limiter = asyncio.Semaphore(10)

    @classmethod
    def get_config_fields(cls) -> list:
        return [
            {"name": "mt5_login", "label": "CMC MT5 Login (Account Number)", "type": "text", "required": True},
            {"name": "mt5_password", "label": "CMC MT5 Password", "type": "password", "required": True},
            {"name": "mt5_server", "label": "CMC MT5 Server", "type": "text", "required": True, "default": "CMCMarkets-Live"},
            {"name": "bridge_url", "label": "MT5 Bridge URL (requires mt5-rest proxy)", "type": "text", "required": False, "default": "http://localhost:8228/api/v1"},
            {"name": "is_demo", "label": "Demo Account", "type": "boolean", "default": True},
        ]

    # ── connection ────────────────────────────────────────────────────

    async def connect(self, credentials: dict) -> dict:
        try:
            mt5_login = credentials["mt5_login"]
            mt5_password = credentials["mt5_password"]
            mt5_server = credentials.get("mt5_server", "CMCMarkets-Live")
            self._is_demo = credentials.get("is_demo", True)
            self._bridge_url = credentials.get("bridge_url", _DEFAULT_BRIDGE_URL).rstrip("/")
        except KeyError as exc:
            return {"status": "error", "message": f"Missing credential: {exc}"}

        self._client = httpx.AsyncClient(base_url=self._bridge_url, timeout=30)

        # Try to connect via MT5 bridge proxy
        try:
            resp = await self._client.post(
                "/connect",
                json={
                    "login": int(mt5_login),
                    "password": mt5_password,
                    "server": mt5_server,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._mt5_account = int(mt5_login)
            self._bridge_available = True
            self._credentials = credentials
            self._connected = True
            logger.info("CMC: connected via MT5 bridge (account=%s, demo=%s)", mt5_login, self._is_demo)
            return {"status": "connected", "account": mt5_login, "demo": self._is_demo, "mode": "mt5_bridge"}
        except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
            logger.warning("CMC: MT5 bridge not available (%s), falling back to simulated mode", exc)
            # Fall back to simulated mode for paper trading
            self._bridge_available = False
            self._credentials = credentials
            self._connected = True
            return {
                "status": "connected",
                "account": mt5_login,
                "demo": True,
                "mode": "simulated",
                "message": "MT5 bridge not available — running in simulated paper trading mode",
            }
        except Exception as exc:
            logger.error("CMC connect error: %s", exc)
            return {"status": "error", "message": str(exc)}

    async def disconnect(self) -> None:
        if self._client and self._bridge_available:
            try:
                await self._client.post("/disconnect")
            except Exception:
                pass
        if self._client:
            await self._client.aclose()
        self._connected = False
        self._client = None
        self._bridge_available = False
        logger.info("CMC: disconnected")

    # ── private helpers ───────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        if not self._bridge_available or not self._client:
            raise ConnectionError("MT5 bridge is not available")
        await self._rate_limit()
        try:
            resp = await self._client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        finally:
            self._release_rate_limit()

    # ── account ───────────────────────────────────────────────────────

    async def get_account_info(self) -> dict:
        if not self._bridge_available:
            return self._get_simulated_account()
        try:
            data = await self._request("GET", "/account")
            if not isinstance(data, dict):
                return self._get_simulated_account()
            return {
                "balance": float(data.get("balance", 0)),
                "equity": float(data.get("equity", 0)),
                "margin_used": float(data.get("margin", 0)),
                "margin_available": float(data.get("margin_free", 0)),
                "unrealised_pnl": float(data.get("profit", 0)),
                "currency": data.get("currency", "GBP"),
            }
        except Exception as exc:
            logger.error("CMC get_account_info error: %s", exc)
            return self._get_simulated_account()

    # ── market data ───────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        if not self._bridge_available:
            return self._get_simulated_ticker(symbol)
        try:
            data = await self._request("GET", f"/symbol/{symbol}/tick")
            if not isinstance(data, dict):
                return self._get_simulated_ticker(symbol)
            bid = float(data.get("bid", 0))
            ask = float(data.get("ask", 0))
            last = (bid + ask) / 2
            return {
                "symbol": symbol,
                "last_price": last,
                "bid": bid,
                "ask": ask,
                "high_24h": float(data.get("high", 0)),
                "low_24h": float(data.get("low", 0)),
                "volume_24h": float(data.get("volume", 0)),
                "change_pct_24h": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning("CMC get_ticker fallback: %s", exc)
            return self._get_simulated_ticker(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        if not self._bridge_available:
            return self._get_simulated_ohlcv(symbol, timeframe, limit)
        try:
            tf_map = {
                "1m": "M1",
                "5m": "M5",
                "15m": "M15",
                "30m": "M30",
                "1h": "H1",
                "4h": "H4",
                "1d": "D1",
                "1w": "W1",
            }
            mt5_tf = tf_map.get(timeframe, "H1")
            data = await self._request(
                "GET",
                f"/symbol/{symbol}/candles",
                params={"timeframe": mt5_tf, "count": limit},
            )
            candles = []
            items = data if isinstance(data, list) else data.get("candles", [])
            for c in items:
                candles.append(
                    {
                        "timestamp": c.get("time", ""),
                        "open": float(c.get("open", 0)),
                        "high": float(c.get("high", 0)),
                        "low": float(c.get("low", 0)),
                        "close": float(c.get("close", 0)),
                        "volume": float(c.get("tick_volume", c.get("volume", 0))),
                    }
                )
            return candles
        except Exception as exc:
            logger.warning("CMC get_ohlcv fallback: %s", exc)
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
        """Place a spread bet / CFD order via the MT5 bridge.

        For spread bets *quantity* is the stake in £/point.

        Args:
            stop_distance: stop-loss distance in points from entry.
            limit_distance: take-profit distance in points from entry.
            guaranteed_stop: if True, request a guaranteed stop (CMC-specific flag).
            trailing_stop: if True, attach a trailing stop.
            trailing_step: increment for the trailing stop (points).
        """
        if not self._bridge_available:
            return self._get_simulated_order(symbol, side, quantity, order_type, price)
        try:
            mt5_type_map = {
                "market": "ORDER_TYPE_BUY" if side.lower() == "buy" else "ORDER_TYPE_SELL",
                "limit": "ORDER_TYPE_BUY_LIMIT" if side.lower() == "buy" else "ORDER_TYPE_SELL_LIMIT",
                "stop": "ORDER_TYPE_BUY_STOP" if side.lower() == "buy" else "ORDER_TYPE_SELL_STOP",
            }
            payload: dict = {
                "symbol": symbol,
                "type": mt5_type_map.get(order_type.lower(), "ORDER_TYPE_BUY"),
                "volume": quantity,
            }
            if price and order_type.lower() in ("limit", "stop"):
                payload["price"] = price
            if stop_distance is not None:
                # MT5 bridge expects absolute SL price; we compute from current tick
                tick = await self.get_ticker(symbol)
                entry = tick.get("ask", 0) if side.lower() == "buy" else tick.get("bid", 0)
                if entry > 0:
                    if side.lower() == "buy":
                        payload["sl"] = round(entry - stop_distance, 5)
                    else:
                        payload["sl"] = round(entry + stop_distance, 5)
            if limit_distance is not None:
                tick = tick if "tick" in dir() else await self.get_ticker(symbol)
                entry = tick.get("ask", 0) if side.lower() == "buy" else tick.get("bid", 0)
                if entry > 0:
                    if side.lower() == "buy":
                        payload["tp"] = round(entry + limit_distance, 5)
                    else:
                        payload["tp"] = round(entry - limit_distance, 5)
            if guaranteed_stop:
                payload["guaranteed_stop"] = True
            if trailing_stop:
                payload["trailing_stop"] = True
                if trailing_step:
                    payload["trailing_step"] = trailing_step

            data = await self._request("POST", "/order", json=payload)
            if not isinstance(data, dict):
                data = {}
            return {
                "order_id": str(data.get("order", data.get("ticket", ""))),
                "status": "filled" if data.get("retcode") == 10009 else "submitted",
                "filled_qty": float(data.get("volume", 0)),
                "filled_price": float(data.get("price", 0)),
                "guaranteed_stop": guaranteed_stop,
                "stop_distance": stop_distance,
                "limit_distance": limit_distance,
            }
        except Exception as exc:
            logger.error("CMC place_order error: %s", exc)
            return {"order_id": "", "status": "error", "filled_qty": 0, "filled_price": 0}

    async def cancel_order(self, order_id: str) -> dict:
        if not self._bridge_available:
            return {"order_id": order_id, "status": "cancelled"}
        try:
            data = await self._request(
                "POST",
                "/order/cancel",
                json={"ticket": int(order_id)},
            )
            if not isinstance(data, dict):
                data = {}
            return {
                "order_id": order_id,
                "status": "cancelled" if data.get("retcode") == 10009 else "error",
            }
        except Exception as exc:
            logger.error("CMC cancel_order error: %s", exc)
            return {"order_id": order_id, "status": "error", "message": str(exc)}

    async def get_positions(self) -> list:
        if not self._bridge_available:
            return []
        try:
            data = await self._request("GET", "/positions")
            positions = []
            items = data if isinstance(data, list) else data.get("positions", [])
            for p in items:
                vol = float(p.get("volume", 0))
                positions.append(
                    {
                        "symbol": p.get("symbol", ""),
                        "side": "buy" if p.get("type", 0) == 0 else "sell",
                        "quantity": vol,
                        "entry_price": float(p.get("price_open", 0)),
                        "current_price": float(p.get("price_current", 0)),
                        "unrealised_pnl": float(p.get("profit", 0)),
                        "ticket": p.get("ticket", ""),
                    }
                )
            return positions
        except Exception as exc:
            logger.error("CMC get_positions error: %s", exc)
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        if not self._bridge_available:
            return self._get_simulated_order_book(symbol, limit)
        try:
            data = await self._request(
                "GET",
                f"/symbol/{symbol}/book",
                params={"depth": limit},
            )
            if not isinstance(data, dict):
                return self._get_simulated_order_book(symbol, limit)
            return {
                "bids": data.get("bids", [])[:limit],
                "asks": data.get("asks", [])[:limit],
            }
        except Exception as exc:
            logger.warning("CMC get_order_book fallback: %s", exc)
            return self._get_simulated_order_book(symbol, limit)

    async def search_instruments(self, query: str) -> list:
        if not self._bridge_available:
            return []
        try:
            data = await self._request("GET", "/symbols", params={"search": query})
            results = []
            items = data if isinstance(data, list) else data.get("symbols", [])
            for s in items:
                results.append(
                    {
                        "symbol": s.get("name", ""),
                        "name": s.get("description", ""),
                        "type": s.get("path", ""),
                        "exchange": "CMC Markets",
                    }
                )
            return results
        except Exception as exc:
            logger.error("CMC search_instruments error: %s", exc)
            return []

    # ── market info (spread-bet specific) ─────────────────────────────

    async def get_market_info(self, symbol: str) -> dict:
        """Get market details including margin, spread, and deal constraints."""
        if not self._bridge_available:
            return self._get_simulated_market_info(symbol)
        try:
            data = await self._request("GET", f"/symbol/{symbol}/info")
            if not isinstance(data, dict):
                return self._get_simulated_market_info(symbol)
            bid = float(data.get("bid", 0))
            ask = float(data.get("ask", 0))
            return {
                "epic": symbol,
                "name": data.get("description", symbol),
                "margin_factor": float(data.get("margin_rate", 5)),
                "margin_factor_unit": "PERCENTAGE",
                "min_stop_distance": float(data.get("stops_level", 0)),
                "guaranteed_stop_premium": float(data.get("guaranteed_stop_premium", 0.3)),
                "min_deal_size": float(data.get("volume_min", 0.1)),
                "bid": bid,
                "offer": ask,
                "spread": round(ask - bid, 5),
                "market_status": "TRADEABLE" if data.get("trade_mode", 0) > 0 else "CLOSED",
            }
        except Exception as exc:
            logger.warning("CMC get_market_info fallback: %s", exc)
            return self._get_simulated_market_info(symbol)

    def _get_simulated_market_info(self, symbol: str) -> dict:
        """Return simulated market info for paper trading."""
        ticker = self._get_simulated_ticker(symbol)
        spread = round(ticker["ask"] - ticker["bid"], 5)
        return {
            "epic": symbol,
            "name": symbol,
            "margin_factor": 5.0,
            "margin_factor_unit": "PERCENTAGE",
            "min_stop_distance": max(5, int(spread * 10)),
            "guaranteed_stop_premium": 0.3,
            "min_deal_size": 0.1,
            "bid": ticker["bid"],
            "offer": ticker["ask"],
            "spread": spread,
            "market_status": "TRADEABLE",
        }
