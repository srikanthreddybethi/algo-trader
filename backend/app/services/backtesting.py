"""
Backtesting Engine — runs strategies against historical data and computes performance metrics.
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.strategies.builtin import get_strategy, list_strategies, STRATEGY_REGISTRY
from app.exchanges.manager import exchange_manager

logger = logging.getLogger(__name__)


def _generate_simulated_history(symbol: str, days: int = 365, timeframe: str = "1h") -> pd.DataFrame:
    """Generate realistic simulated OHLCV history for backtesting."""
    # Determine base price from symbol
    base_prices = {
        "BTC": 67000, "ETH": 3500, "SOL": 170, "BNB": 600,
        "XRP": 0.55, "ADA": 0.45, "DOGE": 0.12, "DOT": 7.5,
        "AVAX": 35, "LINK": 14, "AAPL": 180, "TSLA": 250,
        "GOOGL": 175, "MSFT": 430, "AMZN": 185,
    }
    base_sym = symbol.split("/")[0].upper()
    base_price = base_prices.get(base_sym, 100)

    # Candle count based on timeframe
    tf_hours = {"1m": 1/60, "5m": 5/60, "15m": 0.25, "1h": 1, "4h": 4, "1d": 24}
    hours_per_candle = tf_hours.get(timeframe, 1)
    num_candles = int(days * 24 / hours_per_candle)
    num_candles = min(num_candles, 10000)  # Cap for performance

    np.random.seed(42)  # Reproducible for same inputs

    # Generate price path using geometric Brownian motion
    drift = 0.0001  # Slight upward drift
    volatility = 0.02 if base_price > 1000 else 0.03  # Higher vol for cheaper assets
    returns = np.random.normal(drift, volatility, num_candles)

    prices = [base_price]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    prices = prices[1:]

    # Generate OHLCV
    end = datetime.utcnow()
    start = end - timedelta(hours=num_candles * hours_per_candle)
    timestamps = pd.date_range(start=start, periods=num_candles, freq=f"{int(hours_per_candle * 60)}min")

    rows = []
    for i, ts in enumerate(timestamps):
        close = prices[i]
        high = close * (1 + abs(np.random.normal(0, 0.005)))
        low = close * (1 - abs(np.random.normal(0, 0.005)))
        open_ = prices[i - 1] if i > 0 else close * (1 + np.random.normal(0, 0.002))
        volume = abs(np.random.normal(1000, 300)) * (base_price / 100)
        rows.append({
            "timestamp": ts.isoformat(),
            "open": round(open_, 8),
            "high": round(max(high, open_, close), 8),
            "low": round(min(low, open_, close), 8),
            "close": round(close, 8),
            "volume": round(volume, 2),
        })

    return pd.DataFrame(rows)


async def fetch_historical_data(
    exchange_name: str, symbol: str, timeframe: str = "1h",
    days: int = 90
) -> pd.DataFrame:
    """Fetch historical OHLCV data, falling back to simulated data."""
    try:
        limit = min(int(days * 24 / {"1m": 1/60, "5m": 5/60, "15m": 0.25, "1h": 1, "4h": 4, "1d": 24}.get(timeframe, 1)), 5000)
        candles = await exchange_manager.get_ohlcv(exchange_name, symbol, timeframe, limit)
        if candles and len(candles) > 50:
            df = pd.DataFrame(candles)
            logger.info(f"Fetched {len(df)} candles from {exchange_name} for {symbol}")
            return df
    except Exception as e:
        logger.warning(f"Could not fetch OHLCV from {exchange_name}: {e}")

    # Fallback to simulated data
    logger.info(f"Using simulated data for {symbol} ({days} days, {timeframe})")
    return _generate_simulated_history(symbol, days, timeframe)


def calculate_metrics(equity_curve: List[float], trades: List[Dict],
                      initial_balance: float, days: int) -> Dict:
    """Calculate comprehensive performance metrics."""
    if not equity_curve or len(equity_curve) < 2:
        return _empty_metrics()

    eq = np.array(equity_curve)
    final = eq[-1]
    total_return = (final - initial_balance) / initial_balance
    years = max(days / 365.25, 0.01)

    # Returns series
    returns = np.diff(eq) / eq[:-1]
    returns = returns[np.isfinite(returns)]

    # CAGR
    cagr = (final / initial_balance) ** (1 / years) - 1 if final > 0 else 0

    # Sharpe Ratio (annualized, assuming hourly candles ~= 8760 per year)
    if len(returns) > 1 and np.std(returns) > 0:
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(min(len(equity_curve), 8760))
    else:
        sharpe = 0

    # Sortino Ratio
    downside = returns[returns < 0]
    if len(downside) > 1 and np.std(downside) > 0:
        sortino = (np.mean(returns) / np.std(downside)) * np.sqrt(min(len(equity_curve), 8760))
    else:
        sortino = 0

    # Max Drawdown
    peak = np.maximum.accumulate(eq)
    drawdown = (eq - peak) / peak
    max_drawdown = float(np.min(drawdown)) if len(drawdown) > 0 else 0

    # Drawdown duration (longest consecutive drawdown period)
    in_dd = drawdown < 0
    dd_groups = np.diff(np.where(np.concatenate(([in_dd[0]], in_dd[:-1] != in_dd[1:], [True])))[0])
    max_dd_duration = int(max(dd_groups)) if len(dd_groups) > 0 else 0

    # Win rate
    winning = [t for t in trades if t.get("pnl", 0) > 0]
    losing = [t for t in trades if t.get("pnl", 0) < 0]
    total_trades = len(trades)
    win_rate = len(winning) / total_trades if total_trades > 0 else 0

    # Profit factor
    gross_profit = sum(t["pnl"] for t in winning) if winning else 0
    gross_loss = abs(sum(t["pnl"] for t in losing)) if losing else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Average win/loss
    avg_win = gross_profit / len(winning) if winning else 0
    avg_loss = (gross_loss / len(losing)) if losing else 0

    # Calmar Ratio
    calmar = abs(cagr / max_drawdown) if max_drawdown != 0 else 0

    return {
        "total_return": round(total_return * 100, 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr": round(cagr * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "max_drawdown_duration": max_dd_duration,
        "calmar_ratio": round(calmar, 2),
        "win_rate": round(win_rate * 100, 2),
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "profit_factor": round(profit_factor, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "final_equity": round(final, 2),
        "initial_balance": round(initial_balance, 2),
        "net_profit": round(final - initial_balance, 2),
    }


def _empty_metrics() -> Dict:
    return {
        "total_return": 0, "total_return_pct": 0, "cagr": 0,
        "sharpe_ratio": 0, "sortino_ratio": 0, "max_drawdown": 0,
        "max_drawdown_duration": 0, "calmar_ratio": 0, "win_rate": 0,
        "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
        "profit_factor": 0, "avg_win": 0, "avg_loss": 0,
        "gross_profit": 0, "gross_loss": 0, "final_equity": 0,
        "initial_balance": 0, "net_profit": 0,
    }


async def run_backtest(
    strategy_name: str,
    symbol: str = "BTC/USDT",
    exchange_name: str = "binance",
    timeframe: str = "1h",
    days: int = 90,
    initial_balance: float = 10000.0,
    params: Optional[Dict] = None,
    fee_rate: float = 0.001,
    position_size_pct: float = 10.0,
) -> Dict:
    """Run a complete backtest and return results."""
    strategy = get_strategy(strategy_name)
    params = params or {}

    # Fill defaults for missing params
    for p in strategy.get_params():
        if p.name not in params:
            params[p.name] = p.default

    # Fetch data
    df = await fetch_historical_data(exchange_name, symbol, timeframe, days)
    if df.empty or len(df) < 50:
        return {"error": "Insufficient data for backtesting", "metrics": _empty_metrics()}

    # Generate signals
    df = strategy.generate_signals(df, params)

    # Simulate trades
    cash = initial_balance
    position_qty = 0.0
    position_entry = 0.0
    trades = []
    equity_curve = []
    drawdown_curve = []
    trade_markers = []

    position_size = initial_balance * (position_size_pct / 100)

    for i, row in df.iterrows():
        price = row["close"]
        signal = row.get("signal", 0)
        ts = row.get("timestamp", "")

        if signal == 1 and position_qty == 0 and cash > 0:
            # Buy
            qty = min(position_size, cash) / price
            cost = qty * price
            fee = cost * fee_rate
            if cash >= cost + fee:
                cash -= (cost + fee)
                position_qty = qty
                position_entry = price
                trade_markers.append({
                    "timestamp": ts, "side": "buy", "price": round(price, 2),
                    "quantity": round(qty, 8),
                })

        elif signal == -1 and position_qty > 0:
            # Sell
            revenue = position_qty * price
            fee = revenue * fee_rate
            pnl = (price - position_entry) * position_qty - fee
            cash += revenue - fee
            trades.append({
                "entry_time": trade_markers[-1]["timestamp"] if trade_markers else ts,
                "exit_time": ts,
                "side": "long",
                "entry_price": round(position_entry, 2),
                "exit_price": round(price, 2),
                "quantity": round(position_qty, 8),
                "pnl": round(pnl, 2),
                "pnl_pct": round((price - position_entry) / position_entry * 100, 2),
                "fee": round(fee, 2),
            })
            trade_markers.append({
                "timestamp": ts, "side": "sell", "price": round(price, 2),
                "quantity": round(position_qty, 8),
            })
            position_qty = 0
            position_entry = 0

        # Track equity
        equity = cash + (position_qty * price)
        equity_curve.append(round(equity, 2))

    # Calculate drawdown curve
    peak = 0
    for eq in equity_curve:
        peak = max(peak, eq)
        dd = ((eq - peak) / peak * 100) if peak > 0 else 0
        drawdown_curve.append(round(dd, 2))

    # Metrics
    metrics = calculate_metrics(equity_curve, trades, initial_balance, days)

    # Downsample equity curve for frontend (max 500 points)
    step = max(1, len(equity_curve) // 500)
    sampled_equity = equity_curve[::step]
    sampled_drawdown = drawdown_curve[::step]
    sampled_timestamps = df["timestamp"].tolist()[::step]

    return {
        "strategy": strategy_name,
        "strategy_info": strategy.info(),
        "symbol": symbol,
        "exchange": exchange_name,
        "timeframe": timeframe,
        "days": days,
        "params": params,
        "metrics": metrics,
        "equity_curve": [
            {"timestamp": t, "equity": e, "drawdown": d}
            for t, e, d in zip(sampled_timestamps[:len(sampled_equity)], sampled_equity, sampled_drawdown)
        ],
        "trades": trades[-100:],  # Last 100 trades for display
        "trade_markers": trade_markers[-200:],
        "total_candles": len(df),
        "data_source": "simulated" if len(df) == 0 else "live/simulated",
    }
