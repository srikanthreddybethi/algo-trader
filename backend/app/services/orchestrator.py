"""
AI Strategy Orchestrator — the autonomous brain of the trading system.

Responsibilities:
1. Periodically analyzes market conditions (regime + sentiment + signals)
2. Selects optimal strategy & parameters for current conditions
3. Generates trade signals and executes them via paper trading engine
4. Manages portfolio-level risk (max drawdown, position limits, exposure caps)
5. Logs every decision for auditability
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import numpy as np
import pandas as pd

from app.services.signals.data_feeds import get_all_signals_data, get_fear_greed_index
from app.services.signals.ai_engine import get_ai_analysis
from app.services.signals.regime_detector import detect_regime
from app.exchanges.manager import exchange_manager
from app.strategies.builtin import STRATEGY_REGISTRY, get_strategy
from app.services.paper_trading import paper_engine
from app.services.intelligence import intelligence
from app.services.position_manager import position_manager, losing_streak, persistence
from app.services.adaptive_intelligence import adaptive
from app.services.instrument_intelligence import instrument_intel
from app.services.ai_decision_layer import assess_news_impact, advise_exit, analyze_loss_pattern, ai_select_strategies
from app.services.alerting import alert_manager
from app.services.spread_betting import spread_bet_engine
from app.services.asset_trading_rules import asset_router
from app.services.execution_trust import trust_scorer

logger = logging.getLogger(__name__)

# Spread betting exchanges — use SB-specific sizing and stops
SB_EXCHANGES = {"ig", "capital", "cmc"}


# ─── Decision Log ───────────────────────────────────────────────
_decision_log: List[Dict] = []
MAX_LOG_SIZE = 200


def log_decision(decision: Dict):
    _decision_log.insert(0, {**decision, "timestamp": datetime.utcnow().isoformat()})
    if len(_decision_log) > MAX_LOG_SIZE:
        _decision_log.pop()


def get_decision_log(limit: int = 50) -> List[Dict]:
    return _decision_log[:limit]


def clear_decision_log():
    _decision_log.clear()


# ─── Risk Manager ───────────────────────────────────────────────
class RiskManager:
    """Dynamic risk management for autonomous trading."""

    def __init__(self, config: Dict):
        self.max_drawdown_pct = config.get("max_drawdown_pct", 10.0)
        self.max_position_pct = config.get("max_position_pct", 20.0)
        self.max_total_exposure_pct = config.get("max_total_exposure_pct", 60.0)
        self.max_positions = config.get("max_positions", 5)
        self.stop_loss_pct = config.get("stop_loss_pct", 5.0)
        self.daily_loss_limit_pct = config.get("daily_loss_limit_pct", 3.0)
        self.killed = False

    def check_portfolio_risk(self, portfolio_data: Dict) -> Dict:
        """Check if portfolio risk limits are breached."""
        portfolio = portfolio_data.get("portfolio", {})
        positions = portfolio_data.get("positions", [])

        total_value = portfolio.get("total_value", 0)
        initial = portfolio.get("initial_balance", 10000)
        cash = portfolio.get("cash_balance", 0)

        drawdown = ((initial - total_value) / initial * 100) if initial > 0 else 0
        open_positions = [p for p in positions if p.get("is_open")]
        n_positions = len(open_positions)

        # Total exposure
        total_invested = sum(
            abs(p.get("quantity", 0) * p.get("current_price", p.get("avg_entry_price", 0)))
            for p in open_positions
        )
        exposure_pct = (total_invested / total_value * 100) if total_value > 0 else 0

        warnings = []
        can_trade = True

        if self.killed:
            can_trade = False
            warnings.append("KILL SWITCH ACTIVE — all trading halted")

        if drawdown > self.max_drawdown_pct:
            can_trade = False
            warnings.append(f"Max drawdown breached: {drawdown:.1f}% > {self.max_drawdown_pct}%")

        if n_positions >= self.max_positions:
            warnings.append(f"Max positions reached: {n_positions}/{self.max_positions}")

        if exposure_pct > self.max_total_exposure_pct:
            warnings.append(f"Exposure limit: {exposure_pct:.1f}% > {self.max_total_exposure_pct}%")

        return {
            "can_trade": can_trade,
            "drawdown_pct": round(drawdown, 2),
            "exposure_pct": round(exposure_pct, 2),
            "open_positions": n_positions,
            "total_value": round(total_value, 2),
            "warnings": warnings,
        }

    def calculate_position_size(self, portfolio_value: float, risk_level: str, confidence: float) -> float:
        """Calculate position size as percentage of portfolio, adjusted for risk."""
        base_pct = self.max_position_pct

        # Scale by confidence
        conf_mult = max(0.3, min(1.0, confidence))

        # Scale by risk level
        risk_mult = {"low": 1.0, "medium": 0.7, "high": 0.4}.get(risk_level, 0.5)

        pct = base_pct * conf_mult * risk_mult
        return round(min(pct, self.max_position_pct), 2)

    def activate_kill_switch(self):
        self.killed = True
        log_decision({"type": "kill_switch", "action": "activated", "reason": "Manual kill switch"})

    def deactivate_kill_switch(self):
        self.killed = False
        log_decision({"type": "kill_switch", "action": "deactivated"})


# ─── Strategy Selector ──────────────────────────────────────────
# Maps regime → best strategies + optimal params
REGIME_STRATEGY_MAP = {
    "trending_up": [
        {"name": "Momentum", "params": {"lookback": 20, "threshold": 0.02}, "weight": 0.30},
        {"name": "SMA Crossover", "params": {"short_window": 10, "long_window": 30}, "weight": 0.25},
        {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.20},
        {"name": "EMA Crossover", "params": {"short_window": 12, "long_window": 26}, "weight": 0.15},
        {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.10},
    ],
    "trending_down": [
        {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.25},
        {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.25},
        {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.20},
        {"name": "DCA", "params": {"interval_bars": 24, "amount_pct": 5}, "weight": 0.20},
        {"name": "Grid Trading", "params": {"grid_size": 10, "grid_spacing": 1.0}, "weight": 0.10},
    ],
    "ranging": [
        {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.25},
        {"name": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}, "weight": 0.25},
        {"name": "Pure AI", "params": {"aggression": "moderate"}, "weight": 0.20},
        {"name": "Grid Trading", "params": {"grid_size": 10, "grid_spacing": 0.5}, "weight": 0.20},
        {"name": "Mean Reversion", "params": {"window": 20, "std_dev": 1.5}, "weight": 0.10},
    ],
    "volatile": [
        {"name": "Pure AI", "params": {"aggression": "conservative"}, "weight": 0.25},
        {"name": "DCA", "params": {"interval_bars": 12, "amount_pct": 3}, "weight": 0.25},
        {"name": "Grid Trading", "params": {"grid_size": 15, "grid_spacing": 1.5}, "weight": 0.25},
        {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.5}, "weight": 0.15},
        {"name": "VWAP", "params": {"period": 20}, "weight": 0.10},
    ],
    "breakout": [
        {"name": "Pure AI", "params": {"aggression": "aggressive"}, "weight": 0.30},
        {"name": "Momentum", "params": {"lookback": 14, "threshold": 0.03}, "weight": 0.25},
        {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "weight": 0.20},
        {"name": "Bollinger Bands", "params": {"window": 20, "std_dev": 2.0}, "weight": 0.15},
        {"name": "EMA Crossover", "params": {"short_window": 8, "long_window": 21}, "weight": 0.10},
    ],
}


def select_strategies(regime: Dict, ai_analysis: Dict) -> List[Dict]:
    """Select optimal strategies based on regime + AI recommendation."""
    regime_type = regime.get("regime", "ranging")
    candidates = REGIME_STRATEGY_MAP.get(regime_type, REGIME_STRATEGY_MAP["ranging"])

    # If AI recommends specific strategies, boost their weight
    ai_strategies = ai_analysis.get("recommended_strategies", [])
    for candidate in candidates:
        if candidate["name"] in ai_strategies:
            candidate["weight"] *= 1.3  # Boost AI-recommended

    # Normalize weights
    total_weight = sum(c["weight"] for c in candidates)
    for c in candidates:
        c["weight"] = round(c["weight"] / total_weight, 3)

    # Sort by weight
    candidates.sort(key=lambda x: x["weight"], reverse=True)
    return candidates


# ─── Auto-Trader Engine ─────────────────────────────────────────
class AutoTrader:
    """The autonomous trading engine that runs the entire loop."""

    def __init__(self):
        self.running = False
        self.config = {
            "symbols": ["BTC/USDT"],
            "exchange": "binance",
            "interval_seconds": 300,  # 5 minutes
            "max_drawdown_pct": 10.0,
            "max_position_pct": 20.0,
            "max_total_exposure_pct": 60.0,
            "max_positions": 5,
            "stop_loss_pct": 5.0,
            "daily_loss_limit_pct": 3.0,
        }
        self.risk_manager = RiskManager(self.config)
        self._task: Optional[asyncio.Task] = None
        self._cycle_count = 0
        self._last_signals: Dict = {}
        self._active_strategies: List[Dict] = []
        self._last_analysis: Dict = {}

    def update_config(self, new_config: Dict):
        self.config.update(new_config)
        self.risk_manager = RiskManager(self.config)
        log_decision({"type": "config_update", "config": self.config})

    async def start(self):
        if self.running:
            return {"status": "already_running"}
        self.running = True
        self._cycle_count = 0
        self._task = asyncio.create_task(self._run_loop())
        log_decision({"type": "system", "action": "started", "config": self.config})
        return {"status": "started", "config": self.config}

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            self._task = None
        log_decision({"type": "system", "action": "stopped", "cycles": self._cycle_count})
        return {"status": "stopped", "cycles_completed": self._cycle_count}

    def get_status(self) -> Dict:
        return {
            "running": self.running,
            "cycle_count": self._cycle_count,
            "config": self.config,
            "active_strategies": self._active_strategies,
            "last_signals": self._last_signals,
            "last_analysis": self._last_analysis,
            "risk_manager_killed": self.risk_manager.killed,
        }

    async def _run_loop(self):
        """Main autonomous trading loop with automatic self-improvement."""
        improvement_interval = 50  # Run improvement every N cycles

        while self.running:
            try:
                await self._execute_cycle()

                # Auto-improvement: run backtesting + parameter tuning every N cycles
                if self._cycle_count > 0 and self._cycle_count % improvement_interval == 0:
                    try:
                        from app.services.continuous_improver import run_continuous_improvement
                        logger.info(f"Running auto-improvement at cycle {self._cycle_count}")
                        result = await run_continuous_improvement(
                            symbol=self.config["symbols"][0],
                            exchange=self.config["exchange"],
                            days=30,
                        )
                        log_decision({
                            "type": "auto_improvement",
                            "cycle": self._cycle_count,
                            "regime": result.get("regime"),
                            "backtests": result.get("total_backtests"),
                            "changes": result.get("changes_applied"),
                            "top": result["ranking"][0]["strategy"] if result.get("ranking") else None,
                        })

                        # AI loss pattern analysis if there are recent losses
                        try:
                            losses = [
                                d for d in get_decision_log(50)
                                if d.get("type") == "auto_exit" and d.get("pnl", 0) < 0
                            ]
                            if len(losses) >= 3:
                                strat_usage = {}
                                regimes = []
                                for l in losses:
                                    s = l.get("strategy", l.get("reason", "unknown"))
                                    strat_usage[s] = strat_usage.get(s, 0) + 1
                                    regimes.append(l.get("regime", "unknown"))
                                pattern = await analyze_loss_pattern(losses, strat_usage, regimes)
                                log_decision({
                                    "type": "loss_analysis",
                                    "pattern": pattern.get("pattern_identified"),
                                    "root_cause": pattern.get("root_cause"),
                                    "severity": pattern.get("severity"),
                                    "fixes": pattern.get("fixes", []),
                                    "provider": pattern.get("provider", "rule-based"),
                                })
                        except Exception as e:
                            logger.warning(f"Loss pattern analysis failed: {e}")
                    except Exception as e:
                        logger.warning(f"Auto-improvement failed: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-trader cycle error: {e}")
                log_decision({"type": "error", "message": str(e)})

            # Wait for next cycle
            try:
                await asyncio.sleep(self.config["interval_seconds"])
            except asyncio.CancelledError:
                break

    async def _execute_cycle(self):
        """Execute one complete trading cycle with position management."""
        self._cycle_count += 1
        cycle_start = datetime.utcnow()
        exchange = self.config["exchange"]

        # ── Step 0A: Time-of-day profiling ──
        time_check = adaptive.time_profile.should_trade_now()
        time_size_mult = time_check.get("size_multiplier", 1.0)
        if not time_check["should_trade"]:
            log_decision({
                "type": "time_block",
                "cycle": self._cycle_count,
                "reason": time_check["reason"],
                "hour": time_check.get("hour"),
            })
            return

        # ── Step 0B: Check losing streak cooldown ──
        streak_check = losing_streak.should_trade()
        if not streak_check["can_trade"]:
            log_decision({
                "type": "streak_cooldown",
                "cycle": self._cycle_count,
                "reason": streak_check["reason"],
                "consecutive_losses": streak_check["consecutive_losses"],
            })
            await alert_manager.fire("losing_streak_detected", streak_check["reason"],
                                     details={"consecutive_losses": streak_check["consecutive_losses"]})
            return  # Skip entire cycle

        streak_size_mult = streak_check.get("size_multiplier", 1.0)

        # ── Step 0C: Update position manager with adaptive exit levels ──
        adaptive_levels = adaptive.exit_levels.get_optimal_levels()
        if adaptive_levels.get("source") == "adaptive":
            position_manager.config["stop_loss_pct"] = adaptive_levels["stop_loss_pct"]
            position_manager.config["take_profit_pct"] = adaptive_levels["take_profit_pct"]
            position_manager.config["trailing_stop_pct"] = adaptive_levels["trailing_stop_pct"]

        # ── Step 0D: Manage existing positions (stop-loss, take-profit, trailing) ──
        try:
            from app.core.database import async_session
            async with async_session() as db:
                portfolio = await paper_engine.get_or_create_default_portfolio(db)
                all_positions = await paper_engine.get_positions(db, portfolio.id)
                positions_data = [
                    {"id": p.id, "is_open": p.is_open, "quantity": p.quantity,
                     "current_price": p.current_price, "avg_entry_price": p.avg_entry_price,
                     "symbol": p.symbol, "exchange_name": p.exchange_name,
                     "opened_at": str(p.opened_at) if p.opened_at else None}
                    for p in all_positions
                ]

            exit_signals = await position_manager.check_all_positions(positions_data, exchange)

            # Also run smart exit intelligence (regime change, AI flip, leverage risk)
            try:
                regime_for_exit = detect_regime(
                    await exchange_manager.get_ohlcv(exchange, self.config["symbols"][0], "1h", limit=50)
                )
                from app.services.signals.data_feeds import get_fear_greed_index, get_crypto_news
                fg_data = await get_fear_greed_index()
                fg_val = fg_data.get("value", 50)

                # Rule-based smart exits
                smart_exits = instrument_intel.evaluate_exits(
                    positions=positions_data,
                    current_regime=regime_for_exit.get("regime", "unknown"),
                    fear_greed=fg_val,
                    ai_sentiment=self._last_analysis.get("sentiment_assessment", "neutral"),
                    volatility=regime_for_exit.get("metrics", {}).get("volatility_annual", 20),
                )

                # AI exit advice for positions not already flagged
                flagged_symbols = {e["position"]["symbol"] for e in smart_exits}
                for pos in positions_data:
                    if not pos.get("is_open") or pos["symbol"] in flagged_symbols:
                        continue
                    try:
                        news_for_exit = await get_crypto_news()
                        news_imp = await assess_news_impact(news_for_exit, pos["symbol"].split("/")[0], pos)
                        ai_advice = await advise_exit(
                            position=pos,
                            regime=regime_for_exit.get("regime", "unknown"),
                            fear_greed=fg_val,
                            news_impact=news_imp,
                            recent_price_action=f"{pos.get('unrealized_pnl_pct', 0):+.1f}% since entry",
                        )
                        if ai_advice.get("action") == "sell" and ai_advice.get("confidence", 0) >= 0.6:
                            smart_exits.append({
                                "position": pos,
                                "decision": {
                                    "should_exit": True,
                                    "urgency": ai_advice.get("urgency", "medium"),
                                    "reasons": [f"AI EXIT: {ai_advice.get('reasoning', '')} ({ai_advice.get('provider', 'rule-based')})"],
                                    "pnl_pct": pos.get("unrealized_pnl_pct", 0),
                                },
                            })
                    except Exception:
                        pass  # AI advice is supplementary, don't block on failures

                for smart_exit in smart_exits:
                    pos = smart_exit["position"]
                    dec = smart_exit["decision"]
                    # Only add if not already in exit_signals
                    already_exiting = any(e["symbol"] == pos["symbol"] for e in exit_signals)
                    if not already_exiting:
                        exit_signals.append({
                            "symbol": pos["symbol"],
                            "quantity": pos["quantity"],
                            "current_price": pos.get("current_price", 0),
                            "entry_price": pos.get("avg_entry_price", 0),
                            "pnl_pct": dec["pnl_pct"],
                            "reason": f"SMART EXIT [{dec['urgency']}]: {dec['reasons'][0]}",
                            "position_id": pos.get("id"),
                        })
            except Exception as e:
                logger.warning(f"Smart exit evaluation error: {e}")

            for exit_sig in exit_signals:
                try:
                    async with async_session() as db:
                        order = await paper_engine.place_order(db, {
                            "exchange_name": exchange,
                            "symbol": exit_sig["symbol"],
                            "side": "sell",
                            "order_type": "market",
                            "quantity": round(exit_sig["quantity"], 6),
                        })

                        # Feed outcome to intelligence
                        pnl = (exit_sig["current_price"] - exit_sig["entry_price"]) * exit_sig["quantity"]
                        won = pnl > 0
                        intelligence.record_trade_outcome(
                            strategy="position_manager",
                            symbol=exit_sig["symbol"],
                            pnl=pnl,
                            regime="managed_exit",
                            entry_price=exit_sig["entry_price"],
                            exit_price=exit_sig["current_price"],
                        )
                        losing_streak.record_outcome(won)

                        log_decision({
                            "type": "auto_exit",
                            "symbol": exit_sig["symbol"],
                            "quantity": round(exit_sig["quantity"], 6),
                            "entry_price": round(exit_sig["entry_price"], 2),
                            "exit_price": round(exit_sig["current_price"], 2),
                            "pnl": round(pnl, 2),
                            "pnl_pct": exit_sig["pnl_pct"],
                            "reason": exit_sig["reason"],
                            "cycle": self._cycle_count,
                        })
                except Exception as e:
                    logger.warning(f"Auto-exit failed for {exit_sig['symbol']}: {e}")
        except Exception as e:
            logger.warning(f"Position management error: {e}")

        # ── Now proceed with new trade signals ──
        for symbol in self.config["symbols"]:
            base = symbol.split("/")[0]

            try:
                # Step 1: Gather signals
                signals_data = await get_all_signals_data(base)

                # Step 2: Detect regime (multi-timeframe for accuracy)
                ohlcv = await exchange_manager.get_ohlcv(exchange, symbol, "1h", limit=100)
                regime_1h = detect_regime(ohlcv)

                # Also check 4H regime for confirmation
                try:
                    ohlcv_4h = await exchange_manager.get_ohlcv(exchange, symbol, "4h", limit=50)
                    regime_4h = detect_regime(ohlcv_4h)
                    # If 1H and 4H disagree, lower confidence
                    if regime_1h["regime"] != regime_4h["regime"]:
                        regime_1h["confidence"] = round(regime_1h["confidence"] * 0.7, 2)
                        regime_1h["description"] += f" (4H shows {regime_4h['regime']} — reduced confidence)"
                except Exception:
                    pass  # Fall back to 1H only

                regime = regime_1h
                signals_data["regime"] = regime

                # Step 3: AI analysis
                analysis = await get_ai_analysis(signals_data, base)
                self._last_analysis = analysis

                # Track AI prediction for accuracy measurement
                adaptive.ai_accuracy.record_prediction(analysis, symbol)
                self._last_signals = {
                    "fear_greed": signals_data.get("fear_greed", {}).get("value"),
                    "social_bullish": signals_data.get("social_sentiment", {}).get("bullish_pct"),
                    "regime": regime.get("regime"),
                }

                # Step 3B: News impact assessment (AI-powered)
                news = signals_data.get("news", [])
                if news:
                    try:
                        news_impact = await assess_news_impact(news, base)
                        if news_impact.get("should_halt_trading"):
                            log_decision({
                                "type": "news_halt",
                                "symbol": symbol,
                                "cycle": self._cycle_count,
                                "headline": news_impact.get("key_headline", ""),
                                "reasoning": news_impact.get("reasoning", ""),
                                "provider": news_impact.get("provider", "rule-based"),
                            })
                            continue
                        elif news_impact.get("impact") == "bearish" and news_impact.get("impact_score", 0) < -0.7:
                            streak_size_mult *= 0.75
                            log_decision({
                                "type": "news_caution",
                                "symbol": symbol,
                                "impact": news_impact.get("impact_score"),
                                "headline": news_impact.get("key_headline", ""),
                                "action": "Reducing position size 25% due to strongly bearish news",
                            })
                    except Exception as e:
                        logger.warning(f"News impact assessment failed: {e}")

                # Step 3C: Contrarian sentiment — extreme fear is a buy opportunity
                fg_value = signals_data.get("fear_greed", {}).get("value", 50)
                if fg_value <= 10:
                    # Extreme fear → contrarian buy signal, keep full size
                    streak_size_mult *= 1.1  # Slight boost — buy when others are fearful
                    log_decision({
                        "type": "contrarian_sentiment",
                        "symbol": symbol,
                        "fear_greed": fg_value,
                        "action": "Extreme fear — contrarian buy opportunity, size +10%",
                        "cycle": self._cycle_count,
                    })
                elif fg_value >= 90:
                    # Extreme greed → reduce exposure modestly
                    streak_size_mult *= 0.75
                    log_decision({
                        "type": "extreme_greed",
                        "symbol": symbol,
                        "fear_greed": fg_value,
                        "action": "Extreme greed — reducing position size 25%",
                        "cycle": self._cycle_count,
                    })

                # Step 4: Check risk
                from app.core.database import async_session
                async with async_session() as db:
                    portfolio = await paper_engine.get_or_create_default_portfolio(db)
                    positions = await paper_engine.get_positions(db, portfolio.id)
                    portfolio_data = {
                        "portfolio": {
                            "total_value": portfolio.total_value,
                            "initial_balance": portfolio.initial_balance,
                            "cash_balance": portfolio.cash_balance,
                        },
                        "positions": [
                            {"is_open": p.is_open, "quantity": p.quantity,
                             "current_price": p.current_price, "avg_entry_price": p.avg_entry_price,
                             "symbol": p.symbol}
                            for p in positions
                        ],
                    }

                risk_check = self.risk_manager.check_portfolio_risk(portfolio_data)

                if not risk_check["can_trade"]:
                    log_decision({
                        "type": "risk_block",
                        "symbol": symbol,
                        "cycle": self._cycle_count,
                        "warnings": risk_check["warnings"],
                    })
                    continue

                # Step 4B: Duplicate position check — don't buy what we already hold
                open_symbols = [p.symbol for p in positions if p.is_open]

                # Step 4C: Data freshness check
                if ohlcv and len(ohlcv) > 0:
                    latest_ts = ohlcv[-1].get("timestamp", 0)
                    if latest_ts > 0:
                        age_minutes = (datetime.utcnow().timestamp() * 1000 - latest_ts) / 60000
                        if age_minutes > 120:  # Data older than 2 hours
                            log_decision({
                                "type": "stale_data",
                                "symbol": symbol,
                                "age_minutes": round(age_minutes),
                                "cycle": self._cycle_count,
                            })
                            continue

                # Step 4D: Asset classification & asset-specific validation
                asset_info = asset_router.classify(symbol)
                asset_class = asset_info["asset_class"]
                asset_validation = asset_router.validate_trade(
                    symbol, "buy",  # direction TBD — validate market access
                    fear_greed=signals_data.get("fear_greed", {}).get("value", 50),
                    volatility=regime.get("metrics", {}).get("volatility_annual", 20),
                )
                if not asset_validation["allowed"]:
                    log_decision({
                        "type": "asset_validation_block",
                        "symbol": symbol,
                        "asset_class": asset_class,
                        "cycle": self._cycle_count,
                        "warnings": asset_validation["warnings"],
                    })
                    continue

                # Asset-specific risk params override defaults for this cycle
                asset_risk = asset_router.get_risk_params(symbol, regime.get("regime", "ranging"))

                # Step 5: Select strategies (asset-aware, AI-powered when available, rule-based fallback)
                # Start with asset-specific strategies instead of generic regime map
                asset_strats = asset_router.get_optimal_strategies(
                    symbol, regime.get("regime", "ranging")
                )
                rule_strategies = asset_strats["strategies"]
                # Also blend with regime-based selection for diversity
                generic_strategies = select_strategies(regime, analysis)
                # Merge: keep asset strategies as primary, append any unique generic ones
                asset_names = {s["name"] for s in rule_strategies}
                for gs in generic_strategies:
                    if gs["name"] not in asset_names:
                        gs["weight"] *= 0.5  # Lower weight for non-asset-specific
                        rule_strategies.append(gs)
                rule_strategies.sort(key=lambda x: x["weight"], reverse=True)
                rule_strategies = rule_strategies[:5]  # Keep top 5

                # Try AI strategy selection (considers regime, sentiment, performance, news)
                try:
                    live_scores = intelligence.scoreboard.get_live_scores()
                    news_imp = None
                    try:
                        news_imp = await assess_news_impact(signals_data.get("news", []), base)
                    except Exception:
                        pass

                    ai_strats = await ai_select_strategies(
                        regime=regime,
                        analysis=analysis,
                        available_strategies=rule_strategies,
                        recent_performance=live_scores,
                        fear_greed=signals_data.get("fear_greed", {}).get("value", 50),
                        news_impact=news_imp,
                    )
                    if ai_strats and len(ai_strats) >= 2:
                        strategies = ai_strats
                        log_decision({
                            "type": "ai_strategy_selection",
                            "symbol": symbol,
                            "cycle": self._cycle_count,
                            "strategies": [{"name": s["name"], "weight": s["weight"], "reasoning": s.get("ai_reasoning", "")} for s in strategies[:3]],
                        })
                    else:
                        strategies = rule_strategies
                except Exception as e:
                    logger.debug(f"AI strategy selection unavailable: {e}")
                    strategies = rule_strategies

                # Apply live scoreboard adjustments
                strategies = intelligence.adjust_strategy_weights(strategies)
                self._active_strategies = strategies

                # Step 6: Try strategies in order until one generates a signal
                # (FIX: previously only tried the top strategy)
                df = pd.DataFrame(ohlcv)
                if df.empty or len(df) < 20:
                    continue

                latest_signal = 0
                strategy_name = None
                strategy_params = None
                tried_strategies = []

                for candidate in strategies[:5]:  # Try top 5
                    s_name = candidate["name"]
                    s_params = candidate["params"]
                    tried_strategies.append(s_name)

                    try:
                        instance = get_strategy(s_name)
                        df_signals = instance.generate_signals(df.copy(), s_params)
                    except Exception as e:
                        logger.warning(f"Strategy {s_name} failed: {e}")
                        continue

                    if "signal" not in df_signals.columns or df_signals.empty:
                        continue

                    # Check last 3 candles for a signal (not just the very last one)
                    # A crossover signal fires once then returns to 0
                    recent_signals = df_signals["signal"].tail(3)
                    sig = 0
                    for s in recent_signals:
                        s_int = int(s)
                        if s_int != 0:
                            sig = s_int
                            break  # Use the most recent non-zero signal

                    # If signal is BUY but we already hold this symbol, skip
                    if sig == 1 and symbol in open_symbols:
                        log_decision({
                            "type": "duplicate_blocked",
                            "symbol": symbol,
                            "strategy": s_name,
                            "cycle": self._cycle_count,
                            "reason": f"Already holding {symbol} — skipping duplicate buy",
                        })
                        sig = 0

                    if sig != 0:
                        latest_signal = sig
                        strategy_name = s_name
                        strategy_params = s_params
                        break

                # ── Strategy sell signal → close position directly ──
                # When a strategy generates SELL (-1) and we hold the symbol,
                # close the position immediately without running the full
                # entry intelligence pipeline (which is designed for new entries).
                if latest_signal == -1 and symbol in open_symbols:
                    try:
                        ticker = await exchange_manager.get_ticker(exchange, symbol)
                        current_price = ticker.get("last_price", ohlcv[-1]["close"]) if ticker else ohlcv[-1]["close"]
                        open_pos = [p for p in positions if p.is_open and p.symbol == symbol]
                        if open_pos:
                            sell_qty = open_pos[0].quantity
                            entry_price = open_pos[0].avg_entry_price
                            from app.services.paper_trading import FEE_RATES
                            fee_rate = FEE_RATES.get(exchange, 0.001)
                            async with async_session() as db:
                                order = await paper_engine.place_order(db, {
                                    "exchange_name": exchange,
                                    "symbol": symbol,
                                    "side": "sell",
                                    "order_type": "market",
                                    "quantity": round(sell_qty, 6),
                                    "strategy_name": strategy_name,
                                })
                                # Feed outcome to learning systems
                                if entry_price and entry_price > 0:
                                    raw_pnl = (current_price - entry_price) * sell_qty
                                    net_pnl = raw_pnl - (sell_qty * current_price * fee_rate * 2)
                                    won = net_pnl > 0
                                    intelligence.record_trade_outcome(
                                        strategy=strategy_name, symbol=symbol,
                                        pnl=net_pnl, regime=regime.get("regime", "unknown"),
                                        entry_price=entry_price, exit_price=current_price,
                                    )
                                    losing_streak.record_outcome(won)
                            log_decision({
                                "type": "strategy_sell_exit",
                                "symbol": symbol,
                                "strategy": strategy_name,
                                "quantity": round(sell_qty, 6),
                                "price": round(current_price, 2),
                                "entry_price": round(entry_price, 2),
                                "cycle": self._cycle_count,
                            })
                            continue  # Position closed — move to next symbol
                    except Exception as e:
                        logger.warning(f"Strategy sell exit failed for {symbol}: {e}")

                if latest_signal == 0:
                    log_decision({
                        "type": "no_signal",
                        "symbol": symbol,
                        "cycle": self._cycle_count,
                        "strategies_tried": tried_strategies,
                        "regime": regime.get("regime"),
                    })
                    continue

                # Step 7: INTELLIGENCE PIPELINE — 5 pre-trade checks
                conditions = {
                    "regime": regime.get("regime"),
                    "fear_greed": signals_data.get("fear_greed", {}).get("value", 50),
                    "social_bullish": signals_data.get("social_sentiment", {}).get("bullish_pct", 50),
                    "volatility": regime.get("metrics", {}).get("volatility_annual", 0),
                }
                positions_data = [
                    {"is_open": p.is_open, "quantity": p.quantity,
                     "current_price": p.current_price, "avg_entry_price": p.avg_entry_price,
                     "symbol": p.symbol}
                    for p in positions
                ]

                intel_check = await intelligence.pre_trade_check(
                    exchange=exchange,
                    symbol=symbol,
                    strategy_name=strategy_name,
                    strategy_params=strategy_params,
                    signal=latest_signal,
                    conditions=conditions,
                    existing_positions=positions_data,
                    portfolio_value=portfolio.total_value,
                    max_position_pct=self.config.get("max_position_pct", 20),
                )

                if not intel_check["approved"]:
                    log_decision({
                        "type": "intelligence_block",
                        "symbol": symbol,
                        "strategy": strategy_name,
                        "cycle": self._cycle_count,
                        "reasons": intel_check["reasons"],
                        "memory_matches": intel_check["memory_matches"],
                    })
                    continue

                # Step 8: Instrument Intelligence — what to trade and is it worth it?
                inst_decision = instrument_intel.decide_trade(
                    signal=latest_signal,
                    regime=regime.get("regime", "ranging"),
                    confidence=analysis.get("confidence", 0.5),
                    risk_level=analysis.get("risk_level", "medium"),
                    volatility=regime.get("metrics", {}).get("volatility_annual", 20),
                    portfolio_value=portfolio.total_value,
                    fear_greed=conditions.get("fear_greed", 50),
                    ai_sentiment=analysis.get("sentiment_assessment", "neutral"),
                    existing_positions=positions_data,
                    exchange=exchange,
                )

                if not inst_decision["approved"]:
                    log_decision({
                        "type": "not_worth_trading",
                        "symbol": symbol,
                        "strategy": strategy_name,
                        "cycle": self._cycle_count,
                        "reasoning": inst_decision["reasoning"],
                        "worthiness": inst_decision["worthiness"],
                    })
                    continue

                # Use instrument intelligence direction (may have flipped signal)
                trade_direction = inst_decision["direction"]
                trade_instrument = inst_decision["instrument"]
                trade_leverage = inst_decision["leverage"]

                # ── Step 9A: Execution Trust Score ──
                trust_eval = trust_scorer.evaluate(
                    symbol=symbol,
                    asset_class=asset_info.get("asset_class", "crypto"),
                    direction=trade_direction,
                    exchange=exchange,
                    signal_confidence=analysis.get("confidence", 0.5),
                    mtf_agreement=intel_check.get("mtf_agreement", 0.5),
                    regime_confidence=regime.get("confidence", 0.5),
                    regime_aligns_with_direction=(
                        (trade_direction == "long" and regime.get("regime") in ("trending_up", "ranging")) or
                        (trade_direction == "short" and regime.get("regime") in ("trending_down", "ranging"))
                    ),
                    sentiment_score=signals_data.get("universal_sentiment", {}).get("sentiment_score", 0),
                    sentiment_aligns=(
                        (trade_direction == "long" and signals_data.get("universal_sentiment", {}).get("sentiment_score", 0) >= 0) or
                        (trade_direction == "short" and signals_data.get("universal_sentiment", {}).get("sentiment_score", 0) <= 0)
                    ),
                    strategy_win_rate=intel_check.get("strategy_score", {}).get("win_rate", 0.5),
                    strategy_trades_count=intel_check.get("strategy_score", {}).get("total_trades", 0),
                    current_spread_vs_avg=1.0,
                    data_age_seconds=0,
                    news_risk=signals_data.get("news_risk_level", "none"),
                    portfolio_drawdown_pct=abs(risk_check.get("drawdown_pct", 0)),
                    max_drawdown_pct=self.risk_manager.max_drawdown_pct,
                    is_spread_bet=(exchange in SB_EXCHANGES),
                )

                log_decision({
                    "type": "trust_score",
                    "symbol": symbol,
                    "trust_score": trust_eval["trust_score"],
                    "grade": trust_eval["grade"],
                    "recommendation": trust_eval["recommendation"],
                    "size_modifier": trust_eval["size_modifier"],
                    "components": trust_eval["components"],
                    "reasoning": trust_eval["reasoning"],
                    "cycle": self._cycle_count,
                })

                # Apply trust score decision
                if trust_eval["recommendation"] == "reject":
                    log_decision({
                        "type": "trust_rejected",
                        "symbol": symbol,
                        "trust_score": trust_eval["trust_score"],
                        "grade": trust_eval["grade"],
                        "reasoning": trust_eval["reasoning"],
                        "cycle": self._cycle_count,
                    })
                    continue

                if trust_eval["recommendation"] == "wait":
                    log_decision({
                        "type": "trust_wait",
                        "symbol": symbol,
                        "trust_score": trust_eval["trust_score"],
                        "grade": trust_eval["grade"],
                        "reasoning": trust_eval["reasoning"],
                        "cycle": self._cycle_count,
                    })
                    continue

                # Trust-based position size modifier
                trust_size_mult = trust_eval["size_modifier"]

                # Step 9: Calculate position size (fee-aware)
                from app.services.paper_trading import estimate_round_trip_cost, FEE_RATES, MIN_ORDER_USD, get_fee_stats

                position_pct = intel_check["position_pct"]
                risk_level = analysis.get("risk_level", "medium")
                confidence = analysis.get("confidence", 0.5)

                # Get current price
                ticker = await exchange_manager.get_ticker(exchange, symbol)
                current_price = ticker.get("last_price", ohlcv[-1]["close"]) if ticker else ohlcv[-1]["close"]

                # Fee-aware sizing: deduct estimated round-trip cost
                raw_position_value = portfolio.cash_balance * (position_pct / 100)
                # Apply losing streak + time-of-day + asset validation reductions
                asset_size_mult = asset_validation.get("size_multiplier", 1.0)
                raw_position_value *= streak_size_mult * time_size_mult * asset_size_mult * trust_size_mult
                # Clamp to asset-specific max position pct
                asset_max_pct = asset_risk.get("max_position_pct", self.config.get("max_position_pct", 20))
                max_asset_value = portfolio.cash_balance * (asset_max_pct / 100)
                if raw_position_value > max_asset_value:
                    raw_position_value = max_asset_value
                round_trip_cost = estimate_round_trip_cost(exchange, raw_position_value)
                position_value = raw_position_value - round_trip_cost

                # Check minimum order size
                min_usd = MIN_ORDER_USD.get(exchange, 10.0)
                if position_value < min_usd:
                    log_decision({
                        "type": "size_too_small",
                        "symbol": symbol,
                        "strategy": strategy_name,
                        "value_usd": round(position_value, 2),
                        "min_usd": min_usd,
                        "cycle": self._cycle_count,
                    })
                    continue

                quantity = position_value / current_price if current_price > 0 else 0
                if quantity <= 0:
                    continue

                # ── Spread Betting Enhancement ──────────────────────────
                # If the exchange is a spread betting provider, use
                # SB-specific sizing and stops instead of regular quantity.
                is_spread_bet = exchange in SB_EXCHANGES
                use_guaranteed_stop = False

                if is_spread_bet:
                    # Derive stop distance from strategy signal or fallback to ATR proxy
                    stop_distance_points = max(position_value * 0.02, 1.0)  # 2% fallback

                    sb_eval = spread_bet_engine.evaluate_spread_bet(
                        symbol=symbol,
                        direction=trade_direction,
                        account_balance=portfolio.cash_balance,
                        risk_pct=self.risk_manager.max_position_pct / 100 * 100,
                        stop_distance=stop_distance_points,
                        current_price=current_price,
                    )

                    if not sb_eval["approved"]:
                        log_decision({
                            "type": "sb_rejected",
                            "symbol": symbol,
                            "exchange": exchange,
                            "reason": sb_eval.get("warnings", []),
                            "reasoning": sb_eval.get("reasoning", ""),
                            "cycle": self._cycle_count,
                        })
                        continue

                    # Override quantity with SB stake_per_point
                    quantity = sb_eval["stake_per_point"]
                    use_guaranteed_stop = sb_eval.get("guaranteed_stop_recommended", False)
                    log_decision({
                        "type": "sb_sized",
                        "symbol": symbol,
                        "exchange": exchange,
                        "stake_per_point": sb_eval["stake_per_point"],
                        "margin_required": sb_eval["margin_required"],
                        "max_loss": sb_eval["max_loss"],
                        "guaranteed_stop": use_guaranteed_stop,
                        "market_open": sb_eval.get("market_open", True),
                        "cycle": self._cycle_count,
                    })

                # Step 10: Execute trade (using instrument intelligence direction)
                side = "buy" if trade_direction == "long" else "sell"
                entry_price_for_pnl = None  # Track for feedback loop

                # For sell, check if we have a position + calculate P&L for feedback
                if side == "sell":
                    open_positions = [p for p in positions if p.is_open and p.symbol == symbol]
                    if not open_positions:
                        log_decision({
                            "type": "skip_sell",
                            "symbol": symbol,
                            "reason": "No open position to sell",
                        })
                        continue
                    quantity = min(quantity, open_positions[0].quantity)
                    entry_price_for_pnl = open_positions[0].avg_entry_price

                fee_rate = FEE_RATES.get(exchange, 0.001)
                estimated_fee = quantity * current_price * fee_rate

                async with async_session() as db:
                    try:
                        order = await paper_engine.place_order(db, {
                            "exchange_name": exchange,
                            "symbol": symbol,
                            "side": side,
                            "order_type": "market",
                            "quantity": round(quantity, 6),
                            "strategy_name": strategy_name,
                        })

                        # Record successful execution with venue tracker
                        trust_scorer.venue_tracker.record_execution(
                            exchange=exchange,
                            success=True,
                            slippage_pct=0.05,
                            latency_ms=0,
                            fill_rate=1.0,
                        )

                        # FEEDBACK LOOP: On sell, feed outcome to ALL learning systems
                        if side == "sell" and entry_price_for_pnl and entry_price_for_pnl > 0:
                            raw_pnl = (current_price - entry_price_for_pnl) * quantity
                            fee_cost = estimated_fee * 2  # Buy + sell fees
                            net_pnl = raw_pnl - fee_cost
                            won = net_pnl > 0
                            # 1. Intelligence scoreboard + memory
                            intelligence.record_trade_outcome(
                                strategy=strategy_name,
                                symbol=symbol,
                                pnl=net_pnl,
                                regime=regime.get("regime", "unknown"),
                                entry_price=entry_price_for_pnl,
                                exit_price=current_price,
                            )
                            # 2. Losing streak detector
                            losing_streak.record_outcome(won)
                            # 3. Adaptive modules
                            adaptive.exit_levels.record_exit(
                                pnl_pct=((current_price - entry_price_for_pnl) / entry_price_for_pnl) * 100,
                                regime=regime.get("regime", "unknown"),
                                volatility=regime.get("metrics", {}).get("volatility_annual", 20),
                                hold_hours=0,  # Would need timestamp tracking
                            )
                            adaptive.time_profile.record_trade(net_pnl, won)
                            adaptive.frequency.record_trade()
                            # 4. Update trust score history with actual outcome
                            pnl_pct = ((current_price - entry_price_for_pnl) / entry_price_for_pnl) * 100
                            trust_scorer.history.update_outcome(symbol, pnl_pct)
                            # 5. Persist learning state to disk
                            persistence.save_memory(intelligence.memory._memories)
                            persistence.save_scoreboard(dict(intelligence.scoreboard._outcomes))
                            persistence.save_streak(losing_streak._recent_outcomes)

                        fee_stats = get_fee_stats()
                        log_decision({
                            "type": "trade_executed",
                            "symbol": symbol,
                            "side": side,
                            "quantity": round(quantity, 6),
                            "price": round(current_price, 2),
                            "strategy": strategy_name,
                            "regime": regime.get("regime"),
                            "risk_level": risk_level,
                            "confidence": confidence,
                            "position_pct": position_pct,
                            "estimated_fee": round(estimated_fee, 4),
                            "total_fees_paid": round(fee_stats["total_fees_paid"], 2),
                            "cycle": self._cycle_count,
                            "order_id": order.id if order else None,
                            "intelligence": intel_check["reasons"],
                            "instrument": trade_instrument,
                            "leverage": trade_leverage,
                            "direction": trade_direction,
                            "inst_reasoning": inst_decision["reasoning"],
                        })
                    except Exception as e:
                        trust_scorer.venue_tracker.record_execution(
                            exchange=exchange,
                            success=False,
                            slippage_pct=0,
                            latency_ms=0,
                            fill_rate=0,
                        )
                        log_decision({
                            "type": "trade_failed",
                            "symbol": symbol,
                            "side": side,
                            "error": str(e),
                            "cycle": self._cycle_count,
                        })
                        await alert_manager.fire("trade_execution_failed",
                            f"Trade failed: {side} {symbol} — {e}",
                            details={"symbol": symbol, "side": side, "error": str(e)})

            except Exception as e:
                logger.error(f"Cycle error for {symbol}: {e}")
                log_decision({"type": "cycle_error", "symbol": symbol, "error": str(e)})

        log_decision({
            "type": "cycle_complete",
            "cycle": self._cycle_count,
            "duration_ms": int((datetime.utcnow() - cycle_start).total_seconds() * 1000),
            "symbols": self.config["symbols"],
        })


# Singleton
auto_trader = AutoTrader()

# Restore persisted intelligence state on startup
try:
    _loaded_memory = persistence.load_memory()
    if _loaded_memory:
        intelligence.memory._memories = _loaded_memory
        logger.info(f"Restored {len(_loaded_memory)} market memories from disk")
    _loaded_scoreboard = persistence.load_scoreboard()
    if _loaded_scoreboard:
        for k, v in _loaded_scoreboard.items():
            intelligence.scoreboard._outcomes[k] = v
        logger.info(f"Restored scoreboard for {len(_loaded_scoreboard)} strategies from disk")
except Exception as e:
    logger.warning(f"Failed to restore intelligence state: {e}")
