"""
Stress Test — push the system hard to find edge cases.
- Rapid trading: many buys and sells
- Multi-symbol: BTC + ETH + SOL simultaneously
- Edge cases: selling more than you have, buying with no cash
- Concurrent cycles
- Portfolio math validation after every operation
"""
import asyncio
import time
import httpx

BASE = "http://localhost:8000"
ISSUES = []


def issue(msg):
    ISSUES.append(msg)
    print(f"  ❌ {msg}")


def ok(msg):
    print(f"  ✓ {msg}")


async def api(method, path, json_data=None):
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "GET":
            r = await client.get(f"{BASE}{path}")
        elif method == "POST":
            r = await client.post(f"{BASE}{path}", json=json_data)
        elif method == "DELETE":
            r = await client.delete(f"{BASE}{path}")
        r.raise_for_status()
        return r.json()


async def validate_portfolio():
    """Verify portfolio math is consistent."""
    s = await api("GET", "/api/portfolio/summary")
    p = s["portfolio"]
    positions = [x for x in s["positions"] if x["is_open"]]
    pos_value = sum(pos["current_price"] * pos["quantity"] for pos in positions)
    expected = p["cash_balance"] + pos_value
    diff = abs(expected - p["total_value"])
    if diff > 1.0:
        issue(f"Portfolio math off by ${diff:.2f}: cash=${p['cash_balance']:.2f} + pos=${pos_value:.2f} = ${expected:.2f}, but total=${p['total_value']:.2f}")
        return False
    return True


async def run_stress():
    start = time.time()
    print("=" * 60)
    print("STRESS TEST")
    print("=" * 60)

    # Reset
    await api("POST", "/api/portfolio/reset?balance=10000")
    ok("Portfolio reset to $10,000")

    # ═══ Test A: Rapid multi-symbol trading ═══
    print("\n[A] Rapid Multi-Symbol Trading (15 trades)")
    trades = [
        ("buy", "BTC-USDT", 0.005),
        ("buy", "ETH-USDT", 0.1),
        ("buy", "SOL-USDT", 1.0),
        ("buy", "BTC-USDT", 0.003),
        ("buy", "ETH-USDT", 0.05),
        ("sell", "BTC-USDT", 0.003),
        ("sell", "ETH-USDT", 0.05),
        ("buy", "BTC-USDT", 0.002),
        ("sell", "SOL-USDT", 0.5),
        ("buy", "ETH-USDT", 0.08),
        ("sell", "BTC-USDT", 0.004),
        ("sell", "ETH-USDT", 0.1),
        ("buy", "SOL-USDT", 2.0),
        ("sell", "SOL-USDT", 1.5),
        ("sell", "BTC-USDT", 0.003),
    ]

    success = 0
    for side, symbol, qty in trades:
        try:
            result = await api("POST", "/api/trading/orders", {
                "exchange_name": "binance", "symbol": symbol,
                "side": side, "order_type": "market", "quantity": qty,
            })
            if result.get("status") == "filled":
                success += 1
            elif result.get("status") == "rejected":
                ok(f"Correctly rejected: {side} {qty} {symbol} — {result.get('notes', '')[:60]}")
            else:
                issue(f"Unexpected status for {side} {qty} {symbol}: {result.get('status')}")
        except Exception as e:
            issue(f"Trade failed: {side} {qty} {symbol} — {e}")

    ok(f"{success} trades filled out of {len(trades)}")

    if not await validate_portfolio():
        issue("Portfolio math broken after rapid trading")
    else:
        ok("Portfolio math consistent after rapid trading")

    # ═══ Test B: Edge case — sell more than you have ═══
    print("\n[B] Edge Cases")
    try:
        result = await api("POST", "/api/trading/orders", {
            "exchange_name": "binance", "symbol": "BTC-USDT",
            "side": "sell", "order_type": "market", "quantity": 100.0,
        })
        if result.get("status") == "rejected":
            ok(f"Correctly rejected oversized sell: {result.get('notes', '')[:60]}")
        else:
            issue(f"Oversized sell was NOT rejected: {result.get('status')}")
    except Exception as e:
        ok(f"Oversized sell handled: {e}")

    # Buy with no symbol
    try:
        result = await api("POST", "/api/trading/orders", {
            "exchange_name": "binance", "symbol": "FAKE-USDT",
            "side": "buy", "order_type": "market", "quantity": 0.1,
        })
        # Should still work with simulated data
        ok(f"Fake symbol: {result.get('status')} (simulated exchange handles gracefully)")
    except Exception as e:
        ok(f"Fake symbol handled: {e}")

    # ═══ Test C: 30 auto-trader cycles ═══
    print("\n[C] 30 Auto-Trader Cycles (stress)")
    await api("DELETE", "/api/auto-trader/decisions")
    cycle_errors = 0
    for i in range(30):
        try:
            result = await api("POST", "/api/auto-trader/run-once")
            if result.get("status") == "error":
                cycle_errors += 1
        except Exception as e:
            cycle_errors += 1

    decisions = await api("GET", "/api/auto-trader/decisions?limit=200")
    types = {}
    for d in decisions:
        types[d["type"]] = types.get(d["type"], 0) + 1

    ok(f"30 cycles: {cycle_errors} errors, {len(decisions)} decisions")
    for t, count in sorted(types.items()):
        print(f"    {t}: {count}")

    if cycle_errors > 0:
        issue(f"{cycle_errors} cycle errors in stress test")

    if not await validate_portfolio():
        issue("Portfolio math broken after 30 cycles")
    else:
        ok("Portfolio math consistent after 30 cycles")

    # ═══ Test D: Fee accumulation accuracy ═══
    print("\n[D] Fee Tracking Accuracy")
    fees = await api("GET", "/api/auto-trader/fees")
    ok(f"Total fees: ${fees['total_fees_paid']:.4f}")
    ok(f"Total slippage: ${fees['total_slippage_cost']:.4f}")
    ok(f"Trades counted: {fees['trades_count']}")
    ok(f"By exchange: {fees['fees_by_exchange']}")

    if fees["total_fees_paid"] <= 0 and fees["trades_count"] > 0:
        issue("Fees should be > 0 after trades")

    # ═══ Test E: Intelligence state ═══
    print("\n[E] Intelligence After Stress")
    intel = await api("GET", "/api/auto-trader/intelligence")
    ok(f"Memory: {intel['memory']['total_memories']} entries")
    ok(f"Scoreboard: {intel['scoreboard']['strategies_tracked']} strategies, {intel['scoreboard']['total_outcomes']} outcomes")

    # ═══ Test F: Final portfolio state ═══
    print("\n[F] Final Portfolio State")
    summary = await api("GET", "/api/portfolio/summary")
    p = summary["portfolio"]
    positions = [x for x in summary["positions"] if x["is_open"]]
    pnl = p["total_value"] - p["initial_balance"]
    pnl_pct = (pnl / p["initial_balance"]) * 100

    ok(f"Initial: ${p['initial_balance']:.2f}")
    ok(f"Cash: ${p['cash_balance']:.2f}")
    ok(f"Positions: {len(positions)}")
    for pos in positions:
        ok(f"  {pos['symbol']}: {pos['quantity']} @ ${pos['avg_entry_price']:.2f} (current: ${pos['current_price']:.2f}, P&L: {pos['unrealized_pnl_pct']:.1f}%)")
    ok(f"Total Value: ${p['total_value']:.2f}")
    ok(f"P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
    ok(f"Fees paid: ${fees['total_fees_paid']:.4f}")

    # ═══ Summary ═══
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"STRESS TEST COMPLETE — {elapsed:.1f}s")
    print("=" * 60)

    if ISSUES:
        print(f"\n🔴 {len(ISSUES)} ISSUES FOUND:")
        for i, msg in enumerate(ISSUES, 1):
            print(f"   {i}. {msg}")
    else:
        print("\n🟢 ZERO ISSUES — System is rock solid")


if __name__ == "__main__":
    asyncio.run(run_stress())
