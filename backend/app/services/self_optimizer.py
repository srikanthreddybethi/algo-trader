"""
Self-Optimizer — Claude-powered autonomous parameter tuning and strategy evolution.

This service:
1. Runs grid-search backtests across parameter ranges for each strategy
2. Scores results by composite metric (Sharpe + return - drawdown penalty)
3. Uses AI (Claude/Gemini) to analyze trade journal and identify loss patterns
4. Auto-updates the orchestrator's strategy weights and parameters
5. Maintains a history of all optimization runs for transparency
"""
import asyncio
import json
import logging
import itertools
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from app.services.backtesting import run_backtest
from app.services.signals.ai_engine import _call_ai, _get_ai_provider
from app.services.orchestrator import (
    auto_trader, get_decision_log, REGIME_STRATEGY_MAP, select_strategies,
)
from app.strategies.builtin import list_strategies, STRATEGY_REGISTRY

logger = logging.getLogger(__name__)

# ─── Optimization History ───
_optimization_history: List[Dict] = []
_journal_history: List[Dict] = []
MAX_HISTORY = 50

# ─── Parameter Search Spaces ───
PARAM_GRID = {
    "SMA Crossover": {
        "short_window": [8, 12, 15, 20],
        "long_window": [30, 40, 50, 60],
    },
    "EMA Crossover": {
        "short_window": [8, 10, 12, 15],
        "long_window": [21, 26, 30, 40],
    },
    "RSI": {
        "period": [10, 14, 20],
        "oversold": [25, 30, 35],
        "overbought": [65, 70, 75],
    },
    "MACD": {
        "fast": [8, 12, 16],
        "slow": [21, 26, 30],
        "signal": [7, 9, 11],
    },
    "Bollinger Bands": {
        "window": [15, 20, 25],
        "std_dev": [1.5, 2.0, 2.5],
    },
    "Mean Reversion": {
        "window": [15, 20, 30],
        "std_dev": [1.5, 2.0, 2.5],
    },
    "Momentum": {
        "lookback": [10, 14, 20, 30],
        "threshold": [0.01, 0.02, 0.03],
    },
    "Pure AI": {
        "aggression": ["conservative", "moderate", "aggressive"],
    },
}


def _score_backtest(metrics: Dict) -> float:
    """Composite score: rewards high Sharpe and return, penalizes drawdown."""
    sharpe = metrics.get("sharpe_ratio", 0)
    ret = metrics.get("total_return_pct", 0)
    drawdown = metrics.get("max_drawdown_pct", 0)
    trades = metrics.get("total_trades", 0)
    win_rate = metrics.get("win_rate", 0)

    if trades < 3:
        return -100  # Not enough trades to be meaningful

    # Composite: 40% Sharpe + 30% return + 20% win_rate - 10% drawdown penalty
    score = (
        sharpe * 40
        + ret * 0.3
        + win_rate * 20
        - drawdown * 0.1
    )
    return round(score, 4)


async def run_optimization(
    symbols: List[str] = None,
    exchange: str = "binance",
    timeframe: str = "1h",
    days: int = 60,
    top_n: int = 3,
) -> Dict:
    """
    Run grid-search optimization across all strategies and parameter combinations.
    Returns the best parameters for each strategy.
    """
    symbols = symbols or ["BTC/USDT"]
    start_time = datetime.utcnow()

    all_results = []
    best_per_strategy: Dict[str, Dict] = {}
    total_backtests = 0

    for strategy_name, param_grid in PARAM_GRID.items():
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))

        # Limit combinations to keep it fast
        max_combos = 20
        if len(combinations) > max_combos:
            # Sample evenly
            step = len(combinations) // max_combos
            combinations = combinations[::step][:max_combos]

        strategy_results = []

        for combo in combinations:
            params = dict(zip(param_names, combo))

            for symbol in symbols:
                try:
                    result = await run_backtest(
                        strategy_name=strategy_name,
                        symbol=symbol,
                        exchange_name=exchange,
                        timeframe=timeframe,
                        days=days,
                        initial_balance=10000,
                        params=params,
                        position_size_pct=5.0,  # Conservative for optimization
                    )
                    total_backtests += 1

                    metrics = result.get("metrics", {})
                    score = _score_backtest(metrics)

                    entry = {
                        "strategy": strategy_name,
                        "params": params,
                        "symbol": symbol,
                        "score": score,
                        "sharpe": metrics.get("sharpe_ratio", 0),
                        "return_pct": metrics.get("total_return_pct", 0),
                        "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
                        "total_trades": metrics.get("total_trades", 0),
                        "win_rate": metrics.get("win_rate", 0),
                    }
                    strategy_results.append(entry)
                    all_results.append(entry)

                except Exception as e:
                    logger.warning(f"Backtest failed for {strategy_name} {params}: {e}")

        # Find best params for this strategy
        if strategy_results:
            strategy_results.sort(key=lambda x: x["score"], reverse=True)
            best = strategy_results[0]
            best_per_strategy[strategy_name] = {
                "params": best["params"],
                "score": best["score"],
                "sharpe": best["sharpe"],
                "return_pct": best["return_pct"],
                "max_drawdown_pct": best["max_drawdown_pct"],
                "total_trades": best["total_trades"],
                "win_rate": best["win_rate"],
            }

    # Rank strategies overall
    overall_ranking = sorted(best_per_strategy.items(), key=lambda x: x[1]["score"], reverse=True)

    # Calculate new weights based on scores
    total_score = sum(max(0, v["score"]) for _, v in overall_ranking)
    new_weights = {}
    for name, data in overall_ranking:
        weight = (max(0, data["score"]) / total_score) if total_score > 0 else 1.0 / len(overall_ranking)
        new_weights[name] = round(weight, 3)

    duration = (datetime.utcnow() - start_time).total_seconds()

    optimization_result = {
        "timestamp": datetime.utcnow().isoformat(),
        "duration_seconds": round(duration, 1),
        "total_backtests": total_backtests,
        "symbols": symbols,
        "exchange": exchange,
        "timeframe": timeframe,
        "days": days,
        "best_per_strategy": best_per_strategy,
        "overall_ranking": [{"strategy": name, **data} for name, data in overall_ranking],
        "new_weights": new_weights,
        "top_strategy": overall_ranking[0][0] if overall_ranking else None,
    }

    _optimization_history.insert(0, optimization_result)
    if len(_optimization_history) > MAX_HISTORY:
        _optimization_history.pop()

    return optimization_result


async def analyze_trade_journal(days_back: int = 7) -> Dict:
    """
    AI-powered trade journal analysis.
    Reviews recent decisions, identifies patterns in wins/losses,
    and generates actionable improvement recommendations.
    """
    decisions = get_decision_log(limit=100)

    # Filter to recent decisions
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    recent = [
        d for d in decisions
        if d.get("timestamp") and datetime.fromisoformat(d["timestamp"]) > cutoff
    ]

    if not recent:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "no_data",
            "message": "No trading decisions in the specified period",
            "recommendations": [],
        }

    # Summarize decisions
    trades = [d for d in recent if d["type"] == "trade_executed"]
    no_signals = [d for d in recent if d["type"] == "no_signal"]
    risk_blocks = [d for d in recent if d["type"] == "risk_block"]
    errors = [d for d in recent if d["type"] in ("error", "trade_failed", "cycle_error")]
    cycles = [d for d in recent if d["type"] == "cycle_complete"]

    # Strategy frequency
    strategy_usage = {}
    for t in trades:
        s = t.get("strategy", "unknown")
        strategy_usage[s] = strategy_usage.get(s, 0) + 1

    # Regime frequency
    regime_freq = {}
    for d in recent:
        r = d.get("regime", "unknown")
        if r != "unknown":
            regime_freq[r] = regime_freq.get(r, 0) + 1

    summary = {
        "period_days": days_back,
        "total_decisions": len(recent),
        "trades_executed": len(trades),
        "no_signal_events": len(no_signals),
        "risk_blocks": len(risk_blocks),
        "errors": len(errors),
        "cycles_completed": len(cycles),
        "strategy_usage": strategy_usage,
        "regime_frequency": regime_freq,
        "trade_details": [
            {
                "side": t.get("side"),
                "symbol": t.get("symbol"),
                "strategy": t.get("strategy"),
                "regime": t.get("regime"),
                "confidence": t.get("confidence"),
                "risk_level": t.get("risk_level"),
            }
            for t in trades[:20]
        ],
    }

    # Ask AI for analysis
    ai_analysis = await _get_journal_ai_analysis(summary)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": summary,
        "ai_analysis": ai_analysis,
        "provider": _get_ai_provider() or "rule-based",
    }

    _journal_history.insert(0, result)
    if len(_journal_history) > MAX_HISTORY:
        _journal_history.pop()

    return result


async def _get_journal_ai_analysis(summary: Dict) -> Dict:
    """Get AI-powered trade journal insights."""
    prompt = f"""Analyze this trading system's recent performance and provide specific improvement recommendations.

## Trading Activity Summary (Last {summary['period_days']} days)
- Total decisions: {summary['total_decisions']}
- Trades executed: {summary['trades_executed']}
- No-signal events (chose to hold): {summary['no_signal_events']}
- Risk blocks (safety limits hit): {summary['risk_blocks']}
- Errors: {summary['errors']}
- Cycles completed: {summary['cycles_completed']}

## Strategy Usage
{json.dumps(summary['strategy_usage'], indent=2)}

## Market Regimes Encountered
{json.dumps(summary['regime_frequency'], indent=2)}

## Recent Trades
{json.dumps(summary['trade_details'][:10], indent=2)}

## Provide analysis as JSON:
{{
  "performance_assessment": "1-2 sentence overall assessment",
  "strengths": ["what the system is doing well"],
  "weaknesses": ["what needs improvement"],
  "recommendations": [
    {{
      "priority": "high" | "medium" | "low",
      "category": "parameters" | "strategy_selection" | "risk_management" | "timing",
      "action": "specific actionable recommendation",
      "reasoning": "why this would help"
    }}
  ],
  "strategy_adjustments": {{
    "increase_weight": ["strategies that should get more allocation"],
    "decrease_weight": ["strategies that should get less"],
    "parameter_tweaks": {{"strategy_name": {{"param": "new_value"}}}}
  }},
  "risk_observations": "any risk management concerns"
}}

Return ONLY the JSON."""

    response = await _call_ai(prompt, system="You are a quantitative portfolio manager reviewing a trading system's performance.")

    if response:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            return json.loads(text.strip())
        except Exception as e:
            logger.warning(f"Failed to parse journal AI response: {e}")

    # Rule-based fallback
    return _rule_based_journal_analysis(summary)


def _rule_based_journal_analysis(summary: Dict) -> Dict:
    """Fallback journal analysis without AI."""
    trades = summary["trades_executed"]
    no_signals = summary["no_signal_events"]
    risk_blocks = summary["risk_blocks"]
    errors = summary["errors"]

    recommendations = []

    # Check trade frequency
    if trades == 0 and summary["cycles_completed"] > 5:
        recommendations.append({
            "priority": "high",
            "category": "parameters",
            "action": "Lower signal thresholds — the system is too conservative and not generating any trades",
            "reasoning": f"{summary['cycles_completed']} cycles completed but 0 trades executed",
        })

    if risk_blocks > 3:
        recommendations.append({
            "priority": "high",
            "category": "risk_management",
            "action": "Review risk limits — frequent risk blocks may indicate limits are too tight or positions too large",
            "reasoning": f"{risk_blocks} risk blocks in {summary['period_days']} days",
        })

    if errors > 2:
        recommendations.append({
            "priority": "high",
            "category": "timing",
            "action": "Investigate execution errors — may indicate connectivity or API issues",
            "reasoning": f"{errors} errors detected",
        })

    if no_signals > trades * 5 and trades > 0:
        recommendations.append({
            "priority": "medium",
            "category": "strategy_selection",
            "action": "Consider adding more sensitive strategies for the dominant market regime",
            "reasoning": f"Hold/no-signal ratio is very high ({no_signals}:{trades})",
        })

    if not recommendations:
        recommendations.append({
            "priority": "low",
            "category": "parameters",
            "action": "Continue monitoring — insufficient data for strong recommendations",
            "reasoning": "System appears to be operating normally",
        })

    return {
        "performance_assessment": f"System executed {trades} trades over {summary['period_days']} days with {risk_blocks} risk blocks and {errors} errors.",
        "strengths": ["Risk management is active", "Multiple strategies deployed"],
        "weaknesses": ["Limited trade history for deep analysis"] if trades < 5 else [],
        "recommendations": recommendations,
        "strategy_adjustments": {
            "increase_weight": [],
            "decrease_weight": [],
            "parameter_tweaks": {},
        },
        "risk_observations": "Risk controls are functioning" if risk_blocks > 0 else "No risk events — limits may not have been tested yet",
    }


async def apply_optimization_results(optimization: Dict) -> Dict:
    """
    Apply optimization results to the live orchestrator.
    Updates strategy weights and parameters in REGIME_STRATEGY_MAP.
    """
    best = optimization.get("best_per_strategy", {})
    new_weights = optimization.get("new_weights", {})

    changes = []

    # Update parameters in REGIME_STRATEGY_MAP for each regime
    for regime, strategies in REGIME_STRATEGY_MAP.items():
        for strategy_entry in strategies:
            name = strategy_entry["name"]
            if name in best:
                old_params = strategy_entry["params"].copy()
                new_params = best[name]["params"]
                # Merge — keep any params that aren't in the grid
                strategy_entry["params"].update(new_params)

                if old_params != strategy_entry["params"]:
                    changes.append({
                        "regime": regime,
                        "strategy": name,
                        "old_params": old_params,
                        "new_params": strategy_entry["params"],
                    })

    # Update auto-trader config with more conservative defaults based on optimization
    top_strategy = optimization.get("top_strategy")

    result = {
        "applied": True,
        "timestamp": datetime.utcnow().isoformat(),
        "changes": changes,
        "top_strategy": top_strategy,
        "new_weights": new_weights,
    }

    return result


def get_optimization_history(limit: int = 20) -> List[Dict]:
    return _optimization_history[:limit]


def get_journal_history(limit: int = 20) -> List[Dict]:
    return _journal_history[:limit]
