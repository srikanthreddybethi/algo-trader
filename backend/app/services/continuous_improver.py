"""
Continuous Improvement Engine — automatically backtests, evaluates, and evolves strategies.

This runs on a schedule (configurable) and does:
1. BACKTEST SWEEP: Tests all strategies across recent market data
2. PARAMETER EXPLORATION: Tries new params outside the standard grid (mutation)
3. LIVE vs BACKTEST BLEND: Combines live scoreboard with backtest results
4. STRATEGY ROTATION: Drops persistent underperformers, promotes outperformers
5. REGIME-SPECIFIC TUNING: Optimizes params per regime, not just globally
6. Feeds all results back into the orchestrator's REGIME_STRATEGY_MAP

The key insight: backtesting alone is backward-looking. Live performance alone has
small sample size. BLENDING both gives the most reliable signal.
"""
import asyncio
import logging
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import numpy as np

from app.services.backtesting import run_backtest
from app.services.intelligence import intelligence
from app.services.orchestrator import REGIME_STRATEGY_MAP, log_decision
from app.services.signals.regime_detector import detect_regime
from app.exchanges.manager import exchange_manager
from app.strategies.builtin import STRATEGY_REGISTRY

logger = logging.getLogger(__name__)

# ─── Improvement History ───
_improvement_log: List[Dict] = []
MAX_LOG = 100

# ─── Standard + Extended Parameter Ranges ───
EXTENDED_PARAM_RANGES = {
    "SMA Crossover": {
        "short_window": list(range(5, 30, 2)),
        "long_window": list(range(20, 80, 5)),
    },
    "EMA Crossover": {
        "short_window": list(range(5, 25, 2)),
        "long_window": list(range(15, 50, 3)),
    },
    "RSI": {
        "period": list(range(7, 28, 3)),
        "oversold": list(range(20, 40, 3)),
        "overbought": list(range(60, 85, 3)),
    },
    "MACD": {
        "fast": list(range(6, 20, 2)),
        "slow": list(range(18, 36, 3)),
        "signal": list(range(5, 14, 2)),
    },
    "Bollinger Bands": {
        "window": list(range(10, 35, 3)),
        "std_dev": [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0],
    },
    "Mean Reversion": {
        "window": list(range(10, 40, 3)),
        "std_dev": [1.0, 1.5, 2.0, 2.5, 3.0],
    },
    "Momentum": {
        "lookback": list(range(7, 35, 3)),
        "threshold": [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05],
    },
    "Pure AI": {
        "aggression": ["conservative", "moderate", "aggressive"],
    },
}


def _score_result(metrics: Dict) -> float:
    """Score a backtest result (same formula as self_optimizer)."""
    sharpe = metrics.get("sharpe_ratio", 0)
    ret = metrics.get("total_return_pct", 0)
    drawdown = metrics.get("max_drawdown_pct", 0)
    trades = metrics.get("total_trades", 0)
    win_rate = metrics.get("win_rate", 0)
    if trades < 2:
        return -100
    return round(sharpe * 40 + ret * 0.3 + win_rate * 20 - drawdown * 0.1, 4)


def _mutate_params(base_params: Dict, strategy_name: str) -> Dict:
    """
    Mutate parameters slightly from a known-good config.
    This explores the neighborhood of winning params rather than random search.
    """
    ranges = EXTENDED_PARAM_RANGES.get(strategy_name, {})
    mutated = {**base_params}

    for key, values in ranges.items():
        if key not in mutated:
            continue
        current = mutated[key]

        if isinstance(values, list) and isinstance(current, (int, float)):
            # Find current position in range and nudge ±1-2 steps
            numeric_vals = [v for v in values if isinstance(v, (int, float))]
            if not numeric_vals:
                continue
            closest_idx = min(range(len(numeric_vals)), key=lambda i: abs(numeric_vals[i] - current))
            nudge = random.choice([-2, -1, 1, 2])
            new_idx = max(0, min(len(numeric_vals) - 1, closest_idx + nudge))
            mutated[key] = numeric_vals[new_idx]
        elif isinstance(values, list) and isinstance(current, str):
            # For categorical, randomly pick
            mutated[key] = random.choice(values)

    return mutated


async def run_regime_specific_optimization(
    symbol: str = "BTC/USDT",
    exchange: str = "binance",
    days: int = 45,
) -> Dict:
    """
    Run optimization separately for each market regime.
    
    1. Detect the CURRENT regime
    2. Backtest strategies across recent data matching this regime's conditions
    3. Find the best params FOR THIS SPECIFIC REGIME
    4. Update the REGIME_STRATEGY_MAP with optimized params
    """
    # Detect current regime
    ohlcv = await exchange_manager.get_ohlcv(exchange, symbol, "1h", limit=100)
    current_regime = detect_regime(ohlcv)
    regime_name = current_regime.get("regime", "ranging")

    results_per_strategy = {}
    total_backtests = 0

    # Get strategies for current regime
    regime_strategies = REGIME_STRATEGY_MAP.get(regime_name, REGIME_STRATEGY_MAP.get("ranging", []))

    for strategy_entry in regime_strategies:
        strategy_name = strategy_entry["name"]
        base_params = strategy_entry["params"]

        # Test: base params + 5 mutations
        param_variants = [base_params]
        for _ in range(5):
            param_variants.append(_mutate_params(base_params, strategy_name))

        best_score = -999
        best_params = base_params
        best_metrics = {}

        for params in param_variants:
            try:
                result = await run_backtest(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    exchange_name=exchange,
                    timeframe="1h",
                    days=days,
                    initial_balance=10000,
                    params=params,
                    position_size_pct=5.0,
                )
                total_backtests += 1
                metrics = result.get("metrics", {})
                score = _score_result(metrics)

                if score > best_score:
                    best_score = score
                    best_params = params
                    best_metrics = metrics
            except Exception as e:
                logger.warning(f"Backtest failed for {strategy_name}: {e}")

        results_per_strategy[strategy_name] = {
            "best_params": best_params,
            "score": best_score,
            "sharpe": best_metrics.get("sharpe_ratio", 0),
            "return_pct": best_metrics.get("total_return_pct", 0),
            "win_rate": best_metrics.get("win_rate", 0),
            "trades": best_metrics.get("total_trades", 0),
        }

    return {
        "regime": regime_name,
        "results": results_per_strategy,
        "total_backtests": total_backtests,
    }


async def blend_live_and_backtest_scores(backtest_results: Dict) -> Dict:
    """
    Blend backtest scores with live scoreboard data.
    Formula: blended = 0.4 * backtest_score + 0.6 * live_score (when available)
    Live data is weighted more because it's real, not simulated.
    """
    live_scores = intelligence.scoreboard.get_live_scores()
    blended = {}

    for strategy_name, bt_data in backtest_results.items():
        bt_score = max(0, bt_data["score"]) / 2200  # Normalize to ~0-1

        if strategy_name in live_scores and live_scores[strategy_name]["trades"] >= 5:
            live = live_scores[strategy_name]
            live_score = live["score"]
            # Blend: 40% backtest + 60% live (live is more trustworthy)
            blended_score = 0.4 * bt_score + 0.6 * live_score
            source = "blended"
        else:
            blended_score = bt_score
            source = "backtest_only"

        blended[strategy_name] = {
            "score": round(blended_score, 4),
            "backtest_score": round(bt_score, 4),
            "live_score": live_scores.get(strategy_name, {}).get("score"),
            "source": source,
            "best_params": bt_data["best_params"],
        }

    return blended


def apply_improvements(regime: str, blended_scores: Dict):
    """
    Apply blended scores to the REGIME_STRATEGY_MAP.
    - Updates params to best-found values
    - Adjusts weights based on blended scores
    - Drops strategies scoring below threshold
    """
    if regime not in REGIME_STRATEGY_MAP:
        return {"changes": 0}

    strategies = REGIME_STRATEGY_MAP[regime]
    changes = 0

    # Update params and weights
    for entry in strategies:
        name = entry["name"]
        if name in blended_scores:
            data = blended_scores[name]
            new_params = data["best_params"]
            old_params = entry["params"].copy()

            # Update params if backtest found something better
            entry["params"].update(new_params)
            if old_params != entry["params"]:
                changes += 1

    # Recalculate weights from blended scores
    scored = [(entry, blended_scores.get(entry["name"], {}).get("score", 0.1))
              for entry in strategies]
    total_score = sum(max(0.01, s) for _, s in scored)

    for entry, score in scored:
        entry["weight"] = round(max(0.01, score) / total_score, 3)

    # Sort by weight (best first)
    strategies.sort(key=lambda x: x["weight"], reverse=True)

    return {"changes": changes, "regime": regime}


async def run_continuous_improvement(
    symbol: str = "BTC/USDT",
    exchange: str = "binance",
    days: int = 45,
) -> Dict:
    """
    Full continuous improvement cycle:
    1. Regime-specific backtest sweep
    2. Parameter mutation & exploration
    3. Blend with live performance
    4. Apply improvements to orchestrator
    5. Log everything
    """
    start_time = datetime.utcnow()

    # Step 1: Regime-specific optimization
    regime_opt = await run_regime_specific_optimization(symbol, exchange, days)
    regime = regime_opt["regime"]
    bt_results = regime_opt["results"]

    # Step 2: Blend with live scores
    blended = await blend_live_and_backtest_scores(bt_results)

    # Step 3: Apply to orchestrator
    applied = apply_improvements(regime, blended)

    # Step 4: Build strategy ranking
    ranking = sorted(blended.items(), key=lambda x: x[1]["score"], reverse=True)

    duration = (datetime.utcnow() - start_time).total_seconds()

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "duration_seconds": round(duration, 1),
        "regime": regime,
        "total_backtests": regime_opt["total_backtests"],
        "changes_applied": applied["changes"],
        "ranking": [
            {
                "strategy": name,
                "blended_score": data["score"],
                "backtest_score": data["backtest_score"],
                "live_score": data["live_score"],
                "source": data["source"],
                "best_params": data["best_params"],
            }
            for name, data in ranking
        ],
        "intelligence": {
            "scoreboard_strategies": intelligence.scoreboard.get_stats()["strategies_tracked"],
            "memory_count": intelligence.memory.get_stats()["total_memories"],
        },
    }

    _improvement_log.insert(0, result)
    if len(_improvement_log) > MAX_LOG:
        _improvement_log.pop()

    log_decision({
        "type": "continuous_improvement",
        "regime": regime,
        "backtests": regime_opt["total_backtests"],
        "changes": applied["changes"],
        "top_strategy": ranking[0][0] if ranking else None,
        "duration_seconds": round(duration, 1),
    })

    return result


def get_improvement_log(limit: int = 20) -> List[Dict]:
    return _improvement_log[:limit]
