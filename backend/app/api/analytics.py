"""Portfolio Analytics API — risk metrics, diversification, performance analysis."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.paper_trading import paper_engine
from app.exchanges.manager import exchange_manager
import numpy as np
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/risk-metrics")
async def get_risk_metrics(db: AsyncSession = Depends(get_db)):
    """Calculate portfolio risk metrics: volatility, beta, VaR, diversification score."""
    portfolio = await paper_engine.get_or_create_default_portfolio(db)
    snapshots = await paper_engine.get_snapshots(db, portfolio.id, limit=100)
    positions = await paper_engine.get_positions(db, portfolio.id, open_only=True)

    # Build timestamped values from snapshots
    timed_values = [
        (s.timestamp, s.total_value)
        for s in snapshots
        if s.total_value and s.total_value > 0 and s.timestamp
    ]

    # Aggregate to daily values (use last snapshot per calendar day) to get proper daily returns
    daily_map: dict[str, float] = {}
    for ts, val in timed_values:
        day_key = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        daily_map[day_key] = val  # last value wins per day
    daily_values = [v for _, v in sorted(daily_map.items())]

    if len(daily_values) < 2:
        returns = []
    else:
        returns = [
            (daily_values[i] - daily_values[i - 1]) / daily_values[i - 1]
            for i in range(1, len(daily_values))
            if daily_values[i - 1] > 0
        ]

    # Volatility (annualized std of daily returns, as percentage)
    # Clamp to reasonable range: 0-200%
    if returns and len(returns) >= 2:
        volatility = float(np.std(returns, ddof=1) * np.sqrt(252))
    else:
        volatility = 0.0
    volatility = min(volatility, 2.0)  # Cap at 200%

    # Value at Risk (95% confidence, parametric)
    # VaR = portfolio_value * daily_volatility * z_score
    var_95 = 0.0
    total_value = portfolio.total_value or portfolio.cash_balance
    if returns and len(returns) >= 2:
        daily_vol = float(np.std(returns, ddof=1))
        var_95 = float(total_value * daily_vol * 1.645)
        # Sanity: VaR should never exceed portfolio value
        var_95 = min(var_95, total_value * 0.5)

    # Max drawdown from daily portfolio values
    # Only consider values after the first trade to avoid initial-deposit artifacts
    max_drawdown = 0.0
    peak = 0.0
    dd_values = daily_values if len(daily_values) > 1 else [v for _, v in timed_values]
    for v in dd_values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_drawdown:
                max_drawdown = dd
    # Clamp: ignore tiny drawdowns from rounding, cap at 100%
    max_drawdown = min(max_drawdown, 1.0)

    # Diversification score (0-100 based on position count and allocation evenness)
    open_positions = [p for p in positions if p.is_open]
    n_positions = len(open_positions)
    diversification = 0
    allocation = []

    if n_positions > 0:
        total_pos_value = 0
        pos_values = []
        for p in open_positions:
            try:
                ticker = await exchange_manager.get_ticker(p.exchange_name, p.symbol)
                price = ticker.get("last_price", p.current_price or p.avg_entry_price) if ticker else (p.current_price or p.avg_entry_price)
            except Exception:
                price = p.current_price or p.avg_entry_price
            val = abs(p.quantity * price)
            pos_values.append({"symbol": p.symbol, "exchange": p.exchange_name, "value": val})
            total_pos_value += val

        if total_pos_value > 0:
            weights = [pv["value"] / total_pos_value for pv in pos_values]
            # Herfindahl index: lower = more diversified
            hhi = sum(w**2 for w in weights)
            # Diversification score: 1 asset = 0, perfectly diversified = 100
            if n_positions > 1:
                # Ideal HHI = 1/n
                ideal_hhi = 1.0 / n_positions
                diversification = min(100, int((1 - hhi) / (1 - ideal_hhi) * 100)) if hhi < 1 else 0
            else:
                diversification = 10  # Single asset

            allocation = [
                {
                    "symbol": pv["symbol"],
                    "exchange": pv["exchange"],
                    "value": round(pv["value"], 2),
                    "weight": round(pv["value"] / total_pos_value * 100, 2),
                }
                for pv in pos_values
            ]

    # Cash allocation — reuse total_value computed earlier
    cash_pct = 0
    if total_value > 0:
        cash_pct = round((portfolio.cash_balance / total_value) * 100, 2)

    allocation.append({
        "symbol": "CASH",
        "exchange": "—",
        "value": round(portfolio.cash_balance, 2),
        "weight": cash_pct,
    })

    return {
        "volatility": round(volatility * 100, 2),
        "var_95": round(var_95, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "diversification_score": diversification,
        "position_count": n_positions,
        "allocation": allocation,
        "daily_returns": [round(r * 100, 4) for r in returns[-30:]],  # Last 30 daily returns
        "portfolio_value": round(total_value, 2),
        "cash_balance": round(portfolio.cash_balance, 2),
    }


@router.get("/performance")
async def get_performance(db: AsyncSession = Depends(get_db)):
    """Get detailed performance metrics over time."""
    portfolio = await paper_engine.get_or_create_default_portfolio(db)
    snapshots = await paper_engine.get_snapshots(db, portfolio.id, limit=365)

    values = []
    for s in snapshots:
        values.append({
            "timestamp": str(s.timestamp) if s.timestamp else None,
            "total_value": s.total_value,
            "cash_balance": s.cash_balance,
            "positions_value": s.positions_value,
        })

    # Calculate cumulative returns
    initial = portfolio.initial_balance
    total_return = ((portfolio.total_value - initial) / initial * 100) if initial > 0 else 0

    # Win/loss trade stats
    from sqlalchemy import select
    from app.models.trade import Trade
    result = await db.execute(select(Trade).where(Trade.portfolio_id == portfolio.id))
    all_trades = result.scalars().all()

    winning_trades = 0
    losing_trades = 0
    total_profit = 0
    total_loss = 0
    trades_by_symbol = {}

    # Group trades by symbol to calculate P&L per round-trip
    for t in all_trades:
        sym = t.symbol
        if sym not in trades_by_symbol:
            trades_by_symbol[sym] = []
        trades_by_symbol[sym].append({
            "side": t.side,
            "price": t.price,
            "quantity": t.quantity,
            "fee": t.fee or 0,
        })

    return {
        "total_return_pct": round(total_return, 2),
        "portfolio_value": round(portfolio.total_value, 2),
        "initial_balance": round(initial, 2),
        "total_trades": len(all_trades),
        "snapshots": values[-90:],  # Last 90 snapshots
    }
