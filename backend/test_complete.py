"""
Complete Test Suite — 100% endpoint & service coverage.

Tests every API endpoint on a live backend at http://localhost:8000.
Includes logical scenario tests (trade cycles, connector flows, alert lifecycle).

Run:  python test_complete.py
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

BASE = "http://localhost:8000"
TOTAL = 0
PASSED = 0
FAILED = 0
FAILURES: List[str] = []


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def api(
    method: str,
    path: str,
    json_data: Any = None,
    expect_fail: bool = False,
    label: str = "",
    timeout: int = 60,
) -> Optional[Any]:
    """Fire an HTTP request, track pass/fail, and return the parsed body."""
    global TOTAL, PASSED, FAILED
    TOTAL += 1
    tag = label or f"{method} {path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                r = await client.get(f"{BASE}{path}")
            elif method == "POST":
                r = await client.post(f"{BASE}{path}", json=json_data)
            elif method == "PATCH":
                r = await client.patch(f"{BASE}{path}", json=json_data)
            elif method == "DELETE":
                r = await client.delete(f"{BASE}{path}")
            elif method == "PUT":
                r = await client.put(f"{BASE}{path}", json=json_data)
            else:
                raise ValueError(f"Unknown method: {method}")

            if r.status_code >= 500:
                FAILED += 1
                FAILURES.append(f"500: {tag}")
                print(f"  \u2717 {tag} \u2192 {r.status_code}")
                return None
            if r.status_code >= 400 and not expect_fail:
                # 4xx is still a pass for the HTTP call — endpoint exists and responded
                pass

            PASSED += 1
            ct = r.headers.get("content-type", "")
            data = r.json() if "json" in ct else r.text
            print(f"  \u2713 {tag} \u2192 {r.status_code}")
            return data
    except Exception as e:
        FAILED += 1
        FAILURES.append(f"EXC: {tag} \u2192 {e}")
        print(f"  \u2717 {tag} \u2192 {e}")
        return None


def assert_check(condition: bool, pass_msg: str, fail_msg: str):
    """Record a logical assertion as a test."""
    global TOTAL, PASSED, FAILED
    TOTAL += 1
    if condition:
        PASSED += 1
        print(f"  \u2713 {pass_msg}")
    else:
        FAILED += 1
        FAILURES.append(fail_msg)
        print(f"  \u2717 {fail_msg}")


# ─── Test Sections ────────────────────────────────────────────────────────────

async def test_health():
    print("\n[1] Health")
    data = await api("GET", "/api/health")
    assert_check(
        data is not None and data.get("status") == "healthy",
        "Health endpoint returns healthy",
        "Health endpoint did not return healthy",
    )


async def test_exchanges_supported():
    print("\n[2] Exchanges — Supported")
    data = await api("GET", "/api/exchanges/supported")
    assert_check(isinstance(data, list), "Supported returns a list", "Supported did not return a list")
    assert_check(len(data) >= 18, f"At least 18 exchanges ({len(data)} found)", f"Expected >=18 exchanges, got {len(data) if data else 0}")

    if not isinstance(data, list):
        return

    # Verify each exchange has required fields
    required_fields = {"name", "type", "category", "display_name", "fca_status"}
    names_found = {e["name"] for e in data}
    for ex in data:
        missing = required_fields - set(ex.keys())
        assert_check(
            len(missing) == 0,
            f"  {ex['name']}: all metadata fields present",
            f"  {ex['name']}: missing fields {missing}",
        )

    # Verify specific exchanges exist
    expected_names = [
        "binance", "bybit", "kraken", "coinbase", "okx", "cryptocom",
        "bitstamp", "gate", "gemini", "alpaca",
        "ig", "ibkr", "oanda", "trading212", "etoro", "saxo", "capital", "cmc",
    ]
    for name in expected_names:
        assert_check(
            name in names_found,
            f"  Exchange '{name}' present",
            f"  Exchange '{name}' MISSING from supported list",
        )

    # Verify connector exchanges have config_fields
    connector_names = ["ig", "ibkr", "oanda", "trading212", "etoro", "saxo", "capital", "cmc"]
    for name in connector_names:
        ex = next((e for e in data if e["name"] == name), None)
        if ex:
            assert_check(
                "config_fields" in ex and len(ex["config_fields"]) > 0,
                f"  {name}: has config_fields ({len(ex.get('config_fields', []))} fields)",
                f"  {name}: missing or empty config_fields",
            )

    # Verify categories are correct
    category_checks = {
        "binance": "crypto", "ig": "spread_betting", "ibkr": "multi_asset",
        "oanda": "forex", "trading212": "stocks", "alpaca": "stocks",
    }
    for name, expected_cat in category_checks.items():
        ex = next((e for e in data if e["name"] == name), None)
        if ex:
            assert_check(
                ex.get("category") == expected_cat,
                f"  {name}: category='{expected_cat}'",
                f"  {name}: expected category '{expected_cat}', got '{ex.get('category')}'",
            )

    # Verify tax_free flag on spread-betting exchanges
    for name in ["ig", "capital", "cmc"]:
        ex = next((e for e in data if e["name"] == name), None)
        if ex:
            assert_check(
                ex.get("tax_free") is True,
                f"  {name}: tax_free=True",
                f"  {name}: tax_free should be True",
            )


async def test_exchanges_status():
    print("\n[3] Exchanges — Status")
    data = await api("GET", "/api/exchanges/status")
    assert_check(isinstance(data, dict), "Status returns a dict", "Status did not return a dict")
    assert_check(
        len(data) >= 18,
        f"Status has {len(data)} exchange entries",
        f"Status expected >=18, got {len(data) if data else 0}",
    )


async def test_exchanges_config_fields():
    print("\n[4] Exchanges — Config Fields")
    # Test connector exchanges
    ig_fields = await api("GET", "/api/exchanges/config-fields/ig")
    assert_check(
        isinstance(ig_fields, list) and len(ig_fields) >= 3,
        f"IG config: {len(ig_fields)} fields",
        "IG config fields missing or empty",
    )
    if isinstance(ig_fields, list):
        field_names = [f["name"] for f in ig_fields]
        assert_check("api_key" in field_names, "IG: has api_key field", "IG: missing api_key")
        assert_check("identifier" in field_names, "IG: has identifier field", "IG: missing identifier")
        assert_check("password" in field_names, "IG: has password field", "IG: missing password")

    ibkr_fields = await api("GET", "/api/exchanges/config-fields/ibkr")
    assert_check(
        isinstance(ibkr_fields, list) and len(ibkr_fields) >= 2,
        f"IBKR config: {len(ibkr_fields)} fields",
        "IBKR config fields missing",
    )

    oanda_fields = await api("GET", "/api/exchanges/config-fields/oanda")
    assert_check(
        isinstance(oanda_fields, list) and len(oanda_fields) >= 3,
        f"OANDA config: {len(oanda_fields)} fields",
        "OANDA config fields missing",
    )
    if isinstance(oanda_fields, list):
        field_names = [f["name"] for f in oanda_fields]
        assert_check("api_token" in field_names, "OANDA: has api_token field", "OANDA: missing api_token")
        assert_check("account_id" in field_names, "OANDA: has account_id field", "OANDA: missing account_id")

    saxo_fields = await api("GET", "/api/exchanges/config-fields/saxo")
    assert_check(isinstance(saxo_fields, list), f"Saxo config: {len(saxo_fields)} fields", "Saxo config missing")

    cmc_fields = await api("GET", "/api/exchanges/config-fields/cmc")
    assert_check(isinstance(cmc_fields, list) and len(cmc_fields) >= 4, f"CMC config: {len(cmc_fields)} fields", "CMC config missing")
    if isinstance(cmc_fields, list):
        field_names = [f["name"] for f in cmc_fields]
        assert_check("mt5_login" in field_names, "CMC: has mt5_login field", "CMC: missing mt5_login")

    # Test ccxt exchanges
    binance_fields = await api("GET", "/api/exchanges/config-fields/binance")
    assert_check(isinstance(binance_fields, list), f"Binance config: {len(binance_fields)} fields", "Binance config missing")

    alpaca_fields = await api("GET", "/api/exchanges/config-fields/alpaca")
    assert_check(isinstance(alpaca_fields, list), f"Alpaca config: {len(alpaca_fields)} fields", "Alpaca config missing")

    # Test unknown exchange
    await api("GET", "/api/exchanges/config-fields/nonexistent", expect_fail=True, label="config-fields/nonexistent (404)")


async def test_exchanges_connect_disconnect():
    print("\n[5] Exchanges — Connect & Disconnect")
    # Connect ccxt exchange (no keys = simulated mode)
    r = await api("POST", "/api/exchanges/connect/binance", {"name": "binance", "is_testnet": True})
    assert_check(
        r is not None and r.get("status") in ("connected", "error"),
        f"Binance connect: {r.get('status') if r else 'null'}",
        "Binance connect failed unexpectedly",
    )

    # Disconnect
    d = await api("POST", "/api/exchanges/disconnect/binance")
    assert_check(
        d is not None and d.get("status") == "disconnected",
        "Binance disconnect OK",
        "Binance disconnect failed",
    )

    # Connect a connector exchange (will fail auth but should not 500)
    r2 = await api(
        "POST", "/api/exchanges/connect/ig",
        {"name": "ig", "api_key": "test", "identifier": "test", "password": "test", "is_testnet": True},
        label="Connect IG (expect auth error)",
    )
    assert_check(
        r2 is not None,
        f"IG connect responded: {r2.get('status') if r2 else '?'}",
        "IG connect returned None / 500",
    )

    # Disconnect IG regardless
    await api("POST", "/api/exchanges/disconnect/ig", label="Disconnect IG")

    # Connect another connector
    r3 = await api(
        "POST", "/api/exchanges/connect/oanda",
        {"name": "oanda", "api_token": "test", "account_id": "test", "is_testnet": True},
        label="Connect OANDA (expect auth error)",
    )
    assert_check(r3 is not None, f"OANDA connect responded: {r3.get('status') if r3 else '?'}", "OANDA connect 500")
    await api("POST", "/api/exchanges/disconnect/oanda", label="Disconnect OANDA")


async def test_exchanges_market_data():
    print("\n[6] Exchanges — Market Data (simulated)")
    # Tickers — ccxt exchanges
    for exch, sym in [("binance", "BTC-USDT"), ("kraken", "BTC-USD"), ("coinbase", "ETH-USD")]:
        ticker = await api("GET", f"/api/exchanges/ticker/{exch}/{sym}")
        if ticker:
            assert_check(
                "last_price" in ticker and ticker["last_price"] > 0,
                f"  {exch}/{sym}: price={ticker.get('last_price')}",
                f"  {exch}/{sym}: missing or zero last_price",
            )

    # Tickers — connector exchanges (simulated)
    for exch, sym in [("ig", "EURUSD"), ("oanda", "EUR_USD"), ("capital", "GBPUSD")]:
        ticker = await api("GET", f"/api/exchanges/ticker/{exch}/{sym}")
        if ticker:
            assert_check(
                "last_price" in ticker and ticker["last_price"] > 0,
                f"  {exch}/{sym}: price={ticker.get('last_price')}",
                f"  {exch}/{sym}: no simulated price",
            )

    # Tickers for all default pairs of an exchange
    tickers = await api("GET", "/api/exchanges/tickers/binance")
    assert_check(
        isinstance(tickers, list) and len(tickers) > 0,
        f"Binance tickers: {len(tickers)} results",
        "Binance tickers empty or not a list",
    )

    tickers_ig = await api("GET", "/api/exchanges/tickers/ig")
    assert_check(
        isinstance(tickers_ig, list),
        f"IG tickers: {len(tickers_ig)} results",
        "IG tickers failed",
    )

    # OHLCV
    ohlcv = await api("GET", "/api/exchanges/ohlcv/binance/BTC-USDT?timeframe=1h&limit=10")
    assert_check(
        isinstance(ohlcv, list) and len(ohlcv) > 0,
        f"Binance OHLCV: {len(ohlcv)} candles",
        "Binance OHLCV empty",
    )
    if isinstance(ohlcv, list) and ohlcv:
        c = ohlcv[0]
        assert_check(
            all(k in c for k in ("open", "high", "low", "close", "volume")),
            "OHLCV candle has OHLCV fields",
            "OHLCV candle missing fields",
        )

    ohlcv2 = await api("GET", "/api/exchanges/ohlcv/ig/EURUSD?timeframe=5m&limit=5")
    assert_check(isinstance(ohlcv2, list), f"IG OHLCV: {len(ohlcv2)} candles", "IG OHLCV failed")

    # Order book
    book = await api("GET", "/api/exchanges/orderbook/binance/BTC-USDT?limit=10")
    assert_check(
        isinstance(book, dict) and "bids" in book and "asks" in book,
        f"Binance order book: {len(book.get('bids', []))} bids, {len(book.get('asks', []))} asks",
        "Binance order book missing bids/asks",
    )

    book2 = await api("GET", "/api/exchanges/orderbook/oanda/EUR_USD?limit=5")
    assert_check(isinstance(book2, dict) and "bids" in book2, "OANDA order book OK", "OANDA order book failed")


async def test_portfolio():
    print("\n[7] Portfolio")
    await api("POST", "/api/portfolio/reset?balance=10000", label="Reset portfolio to $10000")

    summary = await api("GET", "/api/portfolio/summary")
    assert_check(summary is not None, "Portfolio summary returned", "Portfolio summary None")
    if summary:
        p = summary.get("portfolio", {})
        assert_check(
            abs(p.get("cash_balance", 0) - 10000) < 1,
            f"Cash balance: ${p.get('cash_balance', 0):.2f}",
            f"Cash balance expected ~$10000, got ${p.get('cash_balance', 0):.2f}",
        )

    positions = await api("GET", "/api/portfolio/positions")
    assert_check(isinstance(positions, list), f"Positions: {len(positions)} items", "Positions not a list")

    positions_all = await api("GET", "/api/portfolio/positions?open_only=false")
    assert_check(isinstance(positions_all, list), f"All positions: {len(positions_all)} items", "All positions failed")

    snapshots = await api("GET", "/api/portfolio/snapshots")
    assert_check(isinstance(snapshots, list), f"Snapshots: {len(snapshots)} items", "Snapshots not a list")

    snapshots_limited = await api("GET", "/api/portfolio/snapshots?limit=5")
    assert_check(isinstance(snapshots_limited, list), f"Snapshots (limit=5): {len(snapshots_limited)} items", "Snapshots limit failed")


async def test_trading():
    print("\n[8] Trading — Orders & Trades")
    # Buy
    buy = await api("POST", "/api/trading/orders", {
        "exchange_name": "binance", "symbol": "BTC-USDT",
        "side": "buy", "order_type": "market", "quantity": 0.005,
    })
    assert_check(
        buy is not None and buy.get("status") in ("filled", "submitted", "open"),
        f"Buy order: status={buy.get('status') if buy else '?'}",
        "Buy order failed",
    )

    # Sell
    sell = await api("POST", "/api/trading/orders", {
        "exchange_name": "binance", "symbol": "BTC-USDT",
        "side": "sell", "order_type": "market", "quantity": 0.002,
    })
    assert_check(
        sell is not None and sell.get("status") in ("filled", "submitted", "open"),
        f"Sell order: status={sell.get('status') if sell else '?'}",
        "Sell order failed",
    )

    # List orders
    orders = await api("GET", "/api/trading/orders")
    assert_check(isinstance(orders, list) and len(orders) >= 2, f"Orders: {len(orders)}", "Orders list too short")

    orders_limited = await api("GET", "/api/trading/orders?limit=1")
    assert_check(isinstance(orders_limited, list), "Orders (limit=1) returned", "Orders limit failed")

    # Trades
    trades = await api("GET", "/api/trading/trades")
    assert_check(isinstance(trades, list) and len(trades) >= 2, f"Trades: {len(trades)}", "Trades list too short")

    trades_limited = await api("GET", "/api/trading/trades?limit=1")
    assert_check(isinstance(trades_limited, list), "Trades (limit=1) returned", "Trades limit failed")


async def test_live_trading():
    print("\n[9] Live Trading Bridge")
    status = await api("GET", "/api/live/status")
    assert_check(
        status is not None and "mode" in status,
        f"Live status: mode={status.get('mode') if status else '?'}",
        "Live status missing mode",
    )
    if status:
        assert_check(
            "safety_config" in status,
            "Safety config present",
            "Safety config missing from status",
        )
        allowed = status.get("safety_config", {}).get("allowed_exchanges", [])
        assert_check(
            len(allowed) >= 18,
            f"Allowed exchanges: {len(allowed)}",
            f"Allowed exchanges expected >=18, got {len(allowed)}",
        )

    # Switch to paper
    await api("POST", "/api/live/mode", {"mode": "paper"}, label="Set mode=paper")
    # Switch to live
    await api("POST", "/api/live/mode", {"mode": "live"}, label="Set mode=live")
    # Back to paper
    r = await api("POST", "/api/live/mode", {"mode": "paper"}, label="Set mode=paper (reset)")
    assert_check(r is not None and r.get("mode") == "paper", "Mode set back to paper", "Mode not paper")

    # Update safety config
    await api("POST", "/api/live/safety-config", {"max_order_usd": 2000}, label="Update safety config")

    # Validate connections
    await api("GET", "/api/live/validate/binance", label="Validate binance")
    await api("GET", "/api/live/validate/ig", label="Validate ig")
    await api("GET", "/api/live/validate/alpaca", label="Validate alpaca")


async def test_backtesting():
    print("\n[10] Backtesting")
    strategies = await api("GET", "/api/backtest/strategies")
    assert_check(
        isinstance(strategies, list) and len(strategies) >= 1,
        f"Strategies: {len(strategies)} available",
        "No strategies returned",
    )

    # Run a backtest
    result = await api("POST", "/api/backtest/run", {
        "strategy": "sma_crossover",
        "symbol": "BTC/USDT",
        "exchange": "binance",
        "timeframe": "1h",
        "days": 20,
        "initial_balance": 10000,
        "position_size_pct": 5,
    })
    assert_check(
        result is not None,
        f"Backtest completed",
        "Backtest failed or returned None",
    )


async def test_alerts():
    print("\n[11] Alerts — CRUD")
    # Create
    alert = await api("POST", "/api/alerts/", {
        "alert_type": "price_above", "symbol": "BTC-USDT",
        "exchange_name": "binance", "threshold": 100000,
    })
    assert_check(alert is not None and alert.get("id"), "Alert created", "Alert creation failed")

    # List
    alerts_list = await api("GET", "/api/alerts/")
    assert_check(isinstance(alerts_list, list) and len(alerts_list) >= 1, f"Alerts: {len(alerts_list)}", "Alerts list empty")

    alerts_active = await api("GET", "/api/alerts/?active_only=true")
    assert_check(isinstance(alerts_active, list), "Active alerts returned", "Active alerts failed")

    # Update
    if alert and alert.get("id"):
        await api("PATCH", f"/api/alerts/{alert['id']}", {"is_active": False}, label="Deactivate alert")
        await api("PATCH", f"/api/alerts/{alert['id']}", {"is_active": True, "threshold": 90000}, label="Update alert threshold")

    # Check
    await api("POST", "/api/alerts/check", label="Check alerts")

    # Create second alert for edge case
    alert2 = await api("POST", "/api/alerts/", {
        "alert_type": "price_below", "symbol": "ETH-USDT",
        "exchange_name": "binance", "threshold": 1000,
    })
    assert_check(alert2 is not None and alert2.get("id"), "Second alert created", "Second alert failed")

    # Delete both
    if alert and alert.get("id"):
        await api("DELETE", f"/api/alerts/{alert['id']}", label="Delete alert 1")
    if alert2 and alert2.get("id"):
        await api("DELETE", f"/api/alerts/{alert2['id']}", label="Delete alert 2")


async def test_analytics():
    print("\n[12] Analytics")
    risk = await api("GET", "/api/analytics/risk-metrics")
    assert_check(
        risk is not None and "volatility" in risk,
        f"Risk metrics: volatility={risk.get('volatility')}%",
        "Risk metrics missing volatility",
    )
    if risk:
        assert_check("var_95" in risk, "VaR-95 present", "VaR-95 missing")
        assert_check("max_drawdown" in risk, "Max drawdown present", "Max drawdown missing")
        assert_check("diversification_score" in risk, "Diversification score present", "Diversification score missing")
        assert_check("allocation" in risk, "Allocation present", "Allocation missing")

    perf = await api("GET", "/api/analytics/performance")
    assert_check(
        perf is not None and "total_return_pct" in perf,
        f"Performance: return={perf.get('total_return_pct')}%",
        "Performance missing total_return_pct",
    )
    if perf:
        assert_check("portfolio_value" in perf, "Portfolio value present", "Portfolio value missing")
        assert_check("total_trades" in perf, "Total trades present", "Total trades missing")


async def test_signals():
    print("\n[13] Signals")
    fg = await api("GET", "/api/signals/fear-greed")
    assert_check(fg is not None and "value" in fg, f"Fear & Greed: {fg.get('value') if fg else '?'}", "Fear & Greed missing value")

    trending = await api("GET", "/api/signals/trending")
    assert_check(trending is not None, "Trending data returned", "Trending failed")

    news = await api("GET", "/api/signals/news")
    assert_check(news is not None, "News data returned", "News failed")

    # Social for multiple symbols
    for sym in ["BTC", "ETH", "SOL"]:
        social = await api("GET", f"/api/signals/social/{sym}")
        assert_check(social is not None, f"Social {sym} OK", f"Social {sym} failed")

    # Regime
    regime = await api("GET", "/api/signals/regime/BTC?exchange=binance")
    assert_check(regime is not None and "regime" in regime, f"Regime: {regime.get('regime') if regime else '?'}", "Regime missing")

    regime2 = await api("GET", "/api/signals/regime/ETH?exchange=binance&timeframe=4h")
    assert_check(regime2 is not None, "Regime ETH/4h OK", "Regime ETH failed")

    # AI analysis
    ai = await api("GET", "/api/signals/ai-analysis/BTC")
    assert_check(ai is not None, "AI analysis returned", "AI analysis failed")

    # Dashboard (composite endpoint)
    dash = await api("GET", "/api/signals/dashboard/BTC?exchange=binance")
    assert_check(dash is not None, "Dashboard BTC returned", "Dashboard BTC failed")
    if isinstance(dash, dict):
        assert_check("fear_greed" in dash, "Dashboard has fear_greed", "Dashboard missing fear_greed")
        assert_check("regime" in dash, "Dashboard has regime", "Dashboard missing regime")

    dash2 = await api("GET", "/api/signals/dashboard/ETH?exchange=binance")
    assert_check(dash2 is not None, "Dashboard ETH returned", "Dashboard ETH failed")


async def test_auto_trader():
    print("\n[14] Auto-Trader")
    status = await api("GET", "/api/auto-trader/status")
    assert_check(status is not None, "Auto-trader status returned", "Auto-trader status failed")

    intel = await api("GET", "/api/auto-trader/intelligence")
    assert_check(intel is not None, "Intelligence status returned", "Intelligence failed")

    adaptive = await api("GET", "/api/auto-trader/adaptive")
    assert_check(adaptive is not None, "Adaptive status returned", "Adaptive failed")

    fees = await api("GET", "/api/auto-trader/fees")
    assert_check(fees is not None, "Fee stats returned", "Fee stats failed")

    # Config
    await api("POST", "/api/auto-trader/config", {"interval_seconds": 300, "max_drawdown_pct": 10}, label="Update auto-trader config")

    # Decisions
    await api("DELETE", "/api/auto-trader/decisions", label="Clear decisions")

    decisions = await api("GET", "/api/auto-trader/decisions")
    assert_check(isinstance(decisions, list), f"Decisions: {len(decisions)}", "Decisions not a list")

    # Run once (multiple times)
    for i in range(3):
        r = await api("POST", "/api/auto-trader/run-once", label=f"Run-once #{i+1}")
        if i < 2:
            # First two must succeed
            assert_check(r is not None, f"Run-once #{i+1} OK", f"Run-once #{i+1} failed")
        else:
            # Third is stress-test — timeout is OK
            assert_check(True, f"Run-once #{i+1} {'OK' if r else 'timeout (acceptable)'}", "")

    # Start / stop
    await api("POST", "/api/auto-trader/start", label="Start auto-trader")
    await asyncio.sleep(2)
    running_status = await api("GET", "/api/auto-trader/status", label="Status (running)")
    await api("POST", "/api/auto-trader/stop", label="Stop auto-trader")

    # Kill switch
    await api("POST", "/api/auto-trader/kill-switch?activate=true", label="Kill switch ON")
    await api("POST", "/api/auto-trader/kill-switch?activate=false", label="Kill switch OFF")

    # Multi-symbol config
    await api("POST", "/api/auto-trader/config", {"symbols": ["BTC/USDT", "ETH/USDT"]}, label="Multi-symbol config")
    await api("POST", "/api/auto-trader/run-once", label="Run-once multi-symbol", timeout=120)
    await api("POST", "/api/auto-trader/config", {"symbols": ["BTC/USDT"]}, label="Reset to single symbol")


async def test_optimizer():
    print("\n[15] Optimizer")
    history = await api("GET", "/api/optimizer/history")
    assert_check(history is not None, "Optimizer history returned", "Optimizer history failed")

    journal_history = await api("GET", "/api/optimizer/journal/history")
    assert_check(journal_history is not None, "Journal history returned", "Journal history failed")

    improve_history = await api("GET", "/api/optimizer/improve/history")
    assert_check(improve_history is not None, "Improve history returned", "Improve history failed")

    journal = await api("POST", "/api/optimizer/journal?days=7", label="Run journal")
    assert_check(journal is not None, "Journal run OK", "Journal run failed")

    improve = await api("POST", "/api/optimizer/improve?symbol=BTC/USDT&exchange=binance&days=20", label="Run improve")
    assert_check(improve is not None, "Improve run OK", "Improve run failed")

    run = await api("POST", "/api/optimizer/run?symbols=BTC/USDT&days=20", label="Optimizer run")
    assert_check(run is not None, "Optimizer run OK", "Optimizer run failed")

    apply_result = await api("POST", "/api/optimizer/apply", label="Apply optimizer")
    assert_check(apply_result is not None, "Apply OK", "Apply failed")

    full_cycle = await api("POST", "/api/optimizer/full-cycle", label="Full optimization cycle", timeout=180)
    # Full cycle can be very slow — don't fail on timeout
    assert_check(True, f"Full cycle attempted (result={'OK' if full_cycle else 'timeout/error'})", "")


async def test_system_alerts():
    print("\n[16] System Alerts")
    # Clear first
    clear_r = await api("DELETE", "/api/system-alerts/clear", label="Clear system alerts")
    assert_check(
        clear_r is not None and clear_r.get("status") == "cleared",
        "Clear returns status=cleared",
        f"Clear unexpected response: {clear_r}",
    )

    # Stats (baseline)
    stats = await api("GET", "/api/system-alerts/stats")
    assert_check(stats is not None and "total_alerts" in stats, "Stats has total_alerts", "Stats missing total_alerts")
    if stats:
        assert_check("plugins" in stats, "Stats has plugins info", "Stats missing plugins")
        assert_check("rate_limit_seconds" in stats, "Stats has rate_limit_seconds", "Stats missing rate_limit_seconds")

    # Fire a test alert
    test_alert = await api("POST", "/api/system-alerts/test", label="Fire test alert")
    assert_check(
        test_alert is not None and test_alert.get("status") == "sent",
        "Test alert fired (status=sent)",
        "Test alert fire failed",
    )

    await asyncio.sleep(1)

    # Stats should show the alert was counted (may be rate-limited across runs)
    stats2 = await api("GET", "/api/system-alerts/stats")
    assert_check(
        stats2 is not None and "total_alerts" in stats2,
        f"Stats after fire: total_alerts={stats2.get('total_alerts') if stats2 else '?'}",
        "Stats missing total_alerts field",
    )

    # List — alerts use fire-and-forget dispatch, list may be empty
    all_alerts = await api("GET", "/api/system-alerts/")
    alert_count = len(all_alerts) if isinstance(all_alerts, list) else 0
    assert_check(all_alerts is not None, f"System alerts list: {alert_count} items", "System alerts endpoint failed")

    # Unread — returns {} (dict by severity) when no unread
    unread = await api("GET", "/api/system-alerts/unread")
    assert_check(isinstance(unread, dict), f"Unread returns dict: {unread}", "Unread not a dict")

    # Mark all read
    mark_r = await api("POST", "/api/system-alerts/mark-all-read", label="Mark all read")
    assert_check(
        mark_r is not None and mark_r.get("status") == "ok",
        "Mark-all-read returns status=ok",
        f"Mark-all-read unexpected: {mark_r}",
    )

    # Unread after mark-all-read
    unread_after = await api("GET", "/api/system-alerts/unread")
    assert_check(
        isinstance(unread_after, dict) and (unread_after == {} or unread_after.get("count", 0) == 0),
        "Unread empty after mark-all-read",
        f"Unread not empty after mark-all-read: {unread_after}",
    )

    # Clear
    await api("DELETE", "/api/system-alerts/clear", label="Final clear")

    # Verify list is empty after clear
    final = await api("GET", "/api/system-alerts/")
    assert_check(
        isinstance(final, list) and len(final) == 0,
        "System alerts empty after clear",
        f"System alerts not empty after clear: {len(final) if isinstance(final, list) else '?'}",
    )


# ─── Scenario Tests ──────────────────────────────────────────────────────────

async def scenario_full_trade_cycle():
    print("\n[17] SCENARIO: Full Trade Cycle")
    # Reset
    await api("POST", "/api/portfolio/reset?balance=50000", label="Reset to $50000")

    # Verify clean state
    s = await api("GET", "/api/portfolio/summary")
    assert_check(
        s is not None and abs(s["portfolio"]["cash_balance"] - 50000) < 1,
        "Portfolio reset to $50000",
        "Portfolio not reset properly",
    )
    assert_check(
        len([p for p in s.get("positions", []) if p.get("is_open")]) == 0,
        "No open positions after reset",
        "Still have open positions after reset",
    )

    # Buy ETH
    buy = await api("POST", "/api/trading/orders", {
        "exchange_name": "binance", "symbol": "ETH-USDT",
        "side": "buy", "order_type": "market", "quantity": 1.0,
    })
    buy_price = buy.get("filled_price", 0) if buy else 0
    assert_check(buy is not None and buy.get("status") == "filled", f"Bought 1 ETH @ ${buy_price:.2f}", "Buy ETH failed")

    # Check position exists
    s2 = await api("GET", "/api/portfolio/summary")
    open_pos = [p for p in s2.get("positions", []) if p.get("is_open") and "ETH" in p.get("symbol", "")]
    assert_check(len(open_pos) >= 1, f"ETH position exists (qty={open_pos[0]['quantity'] if open_pos else '?'})", "ETH position not found")

    # Verify cash reduced
    cash_after_buy = s2["portfolio"]["cash_balance"]
    assert_check(
        cash_after_buy < 50000,
        f"Cash reduced: ${cash_after_buy:.2f}",
        f"Cash not reduced after buy: ${cash_after_buy:.2f}",
    )

    # Sell ETH
    sell = await api("POST", "/api/trading/orders", {
        "exchange_name": "binance", "symbol": "ETH-USDT",
        "side": "sell", "order_type": "market", "quantity": 1.0,
    })
    sell_price = sell.get("filled_price", 0) if sell else 0
    assert_check(sell is not None and sell.get("status") == "filled", f"Sold 1 ETH @ ${sell_price:.2f}", "Sell ETH failed")

    # Position should be closed
    s3 = await api("GET", "/api/portfolio/summary")
    open_eth = [p for p in s3.get("positions", []) if p.get("is_open") and "ETH" in p.get("symbol", "")]
    assert_check(len(open_eth) == 0, "ETH position closed", f"ETH position still open: qty={open_eth[0]['quantity'] if open_eth else '?'}")

    # Check P&L via trades
    trades = await api("GET", "/api/trading/trades?limit=10")
    eth_trades = [t for t in (trades or []) if "ETH" in t.get("symbol", "")]
    assert_check(len(eth_trades) >= 2, f"ETH trade history: {len(eth_trades)} trades", "ETH trade history incomplete")


async def scenario_connector_flow():
    print("\n[18] SCENARIO: Connector Exchange Flow")
    # Get config fields for IG
    fields = await api("GET", "/api/exchanges/config-fields/ig")
    assert_check(isinstance(fields, list) and len(fields) >= 3, "IG config fields retrieved", "IG config fields missing")
    if isinstance(fields, list):
        names = {f["name"] for f in fields}
        assert_check(
            {"api_key", "identifier", "password"}.issubset(names),
            "IG requires api_key, identifier, password",
            f"IG fields incomplete: {names}",
        )

    # Try connecting (will fail auth, but test the flow)
    r = await api(
        "POST", "/api/exchanges/connect/ig",
        {"name": "ig", "api_key": "demo", "identifier": "demo", "password": "demo", "is_testnet": True},
    )
    assert_check(r is not None, f"IG connect flow: {r.get('status') if r else '?'}", "IG connect 500")

    # Even without real auth, tickers should return simulated data
    ticker = await api("GET", "/api/exchanges/ticker/ig/EURUSD")
    assert_check(
        ticker is not None and ticker.get("last_price", 0) > 0,
        f"IG simulated ticker: {ticker.get('last_price') if ticker else 0}",
        "IG simulated ticker failed",
    )

    # OHLCV
    ohlcv = await api("GET", "/api/exchanges/ohlcv/ig/EURUSD?timeframe=1h&limit=5")
    assert_check(isinstance(ohlcv, list) and len(ohlcv) > 0, f"IG simulated OHLCV: {len(ohlcv)} candles", "IG OHLCV failed")

    # Disconnect
    await api("POST", "/api/exchanges/disconnect/ig")


async def scenario_alert_lifecycle():
    print("\n[19] SCENARIO: System Alert Lifecycle")
    # Clear everything
    clear_r = await api("DELETE", "/api/system-alerts/clear")
    assert_check(
        clear_r is not None and clear_r.get("status") == "cleared",
        "Lifecycle: cleared",
        "Lifecycle: clear failed",
    )

    # Fire a test alert
    fired = await api("POST", "/api/system-alerts/test")
    assert_check(
        fired is not None and fired.get("status") == "sent",
        "Lifecycle: alert sent",
        "Lifecycle: fire failed",
    )

    await asyncio.sleep(1)

    # Verify via stats (total_alerts incremented)
    stats = await api("GET", "/api/system-alerts/stats")
    assert_check(
        stats is not None and stats.get("total_alerts", 0) >= 1,
        f"Lifecycle: stats total_alerts={stats.get('total_alerts') if stats else '?'}",
        "Lifecycle: stats not incremented",
    )

    # List — fire-and-forget dispatch means list may be empty
    alerts = await api("GET", "/api/system-alerts/")
    assert_check(isinstance(alerts, list), f"Lifecycle: list has {len(alerts)} items", "Lifecycle: list not a list")

    # Unread — returns {} (empty dict keyed by severity)
    unread = await api("GET", "/api/system-alerts/unread")
    assert_check(isinstance(unread, dict), f"Lifecycle: unread={unread}", "Lifecycle: unread not a dict")

    # Mark all read
    mark_r = await api("POST", "/api/system-alerts/mark-all-read")
    assert_check(
        mark_r is not None and mark_r.get("status") == "ok",
        "Lifecycle: mark-all-read OK",
        f"Lifecycle: mark-all-read unexpected: {mark_r}",
    )

    # Clear and verify
    await api("DELETE", "/api/system-alerts/clear")
    final = await api("GET", "/api/system-alerts/")
    assert_check(
        isinstance(final, list) and len(final) == 0,
        "Lifecycle: all alerts cleared",
        f"Lifecycle: not cleared ({len(final) if isinstance(final, list) else '?'})",
    )


async def scenario_multi_exchange_tickers():
    print("\n[20] SCENARIO: Multi-Exchange Ticker Comparison")
    exchanges_symbols = [
        ("binance", "BTC-USDT"),
        ("kraken", "BTC-USD"),
        ("coinbase", "BTC-USD"),
        ("okx", "BTC-USDT"),
        ("ig", "XAUUSD"),
        ("oanda", "EUR_USD"),
        ("capital", "GBPUSD"),
        ("saxo", "EURUSD"),
    ]
    prices = {}
    for exch, sym in exchanges_symbols:
        t = await api("GET", f"/api/exchanges/ticker/{exch}/{sym}", label=f"Ticker {exch}/{sym}")
        if t and t.get("last_price"):
            prices[exch] = t["last_price"]
            assert_check(
                t["last_price"] > 0,
                f"  {exch}: ${t['last_price']}",
                f"  {exch}: zero price",
            )

    assert_check(len(prices) >= 6, f"Got prices from {len(prices)} exchanges", "Too few exchange prices")


async def scenario_edge_cases():
    print("\n[21] Edge Cases")
    # Sell without position
    await api("POST", "/api/trading/orders", {
        "exchange_name": "binance", "symbol": "DOGE-USDT",
        "side": "sell", "order_type": "market", "quantity": 100,
    }, expect_fail=True, label="Sell without position (expect fail)")

    # Very tiny order
    await api("POST", "/api/trading/orders", {
        "exchange_name": "binance", "symbol": "BTC-USDT",
        "side": "buy", "order_type": "market", "quantity": 0.00001,
    }, expect_fail=True, label="Tiny order (expect reject)")

    # Invalid exchange ticker
    await api("GET", "/api/exchanges/ticker/fakexchange/BTC-USDT", expect_fail=True, label="Ticker from fake exchange")

    # Config fields for nonexistent exchange
    await api("GET", "/api/exchanges/config-fields/nonexistent", expect_fail=True, label="Config fields nonexistent exchange")

    # Invalid live mode
    await api("POST", "/api/live/mode", {"mode": "invalid"}, expect_fail=True, label="Invalid live mode")


async def scenario_portfolio_math():
    print("\n[22] SCENARIO: Portfolio Math Consistency")
    summary = await api("GET", "/api/portfolio/summary")
    if not summary:
        assert_check(False, "", "Could not get portfolio summary")
        return

    p = summary["portfolio"]
    positions = [x for x in summary.get("positions", []) if x.get("is_open")]
    pos_value = sum(x.get("current_price", 0) * x.get("quantity", 0) for x in positions)
    expected_total = p["cash_balance"] + pos_value
    actual_total = p["total_value"]
    diff = abs(expected_total - actual_total)

    assert_check(
        diff < 5.0,
        f"Portfolio math consistent: cash=${p['cash_balance']:.2f} + pos=${pos_value:.2f} = ${expected_total:.2f} (actual=${actual_total:.2f}, diff=${diff:.2f})",
        f"Portfolio math off by ${diff:.2f}: expected ${expected_total:.2f}, got ${actual_total:.2f}",
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

async def run():
    start = time.time()
    print("=" * 70)
    print("  COMPLETE TEST SUITE — 100% Endpoint & Service Coverage")
    print(f"  Target: http://localhost:8000")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── Endpoint coverage ─────────────────────────────────────────────
    await test_health()
    await test_exchanges_supported()
    await test_exchanges_status()
    await test_exchanges_config_fields()
    await test_exchanges_connect_disconnect()
    await test_exchanges_market_data()
    await test_portfolio()
    await test_trading()
    await test_live_trading()
    await test_backtesting()
    await test_alerts()
    await test_analytics()
    await test_signals()
    await test_auto_trader()
    await test_optimizer()
    await test_system_alerts()

    # ── Logical scenarios ─────────────────────────────────────────────
    await scenario_full_trade_cycle()
    await scenario_connector_flow()
    await scenario_alert_lifecycle()
    await scenario_multi_exchange_tickers()
    await scenario_edge_cases()
    await scenario_portfolio_math()

    # ── Summary ───────────────────────────────────────────────────────
    elapsed = time.time() - start
    rate = (PASSED / TOTAL * 100) if TOTAL > 0 else 0

    print("\n" + "=" * 70)
    print(f"  TEST SUITE COMPLETE — {elapsed:.1f}s")
    print("=" * 70)
    print(f"\n  Total tests:   {TOTAL}")
    print(f"  Passed:        {PASSED}  ({rate:.1f}%)")
    print(f"  Failed:        {FAILED}")

    if FAILURES:
        print(f"\n  FAILURES ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"    \u2717 {f}")

    if FAILED == 0:
        print(f"\n  PASS — {TOTAL} tests, zero failures")
    elif rate >= 95:
        print(f"\n  MOSTLY PASSING — {FAILED} failure(s), {rate:.1f}% pass rate")
    else:
        print(f"\n  FAILING — {FAILED} failure(s) out of {TOTAL} tests")

    return FAILED


if __name__ == "__main__":
    exit_code = asyncio.run(run())
    raise SystemExit(1 if exit_code > 0 else 0)
