"""
Execution Trust Layer — the unified confidence scoring system.

Instead of fragmented gates that independently block trades,
this layer consumes ALL signal sources and produces a single
0-1 trust score that determines execution confidence.

Components:
1. ExecutionTrustScorer — weighted composite scoring across 10 dimensions
2. VenueQualityTracker — per-exchange execution quality tracking
3. TrustScoreHistory — tracks trust scores over time for analytics
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ─── Venue Quality ────────────────────────────────────────────────────────────

@dataclass
class VenueStats:
    """Rolling stats for a single exchange/venue."""
    fill_rates: List[float] = field(default_factory=list)
    slippages: List[float] = field(default_factory=list)
    latencies: List[float] = field(default_factory=list)
    successes: int = 0
    failures: int = 0

    @property
    def total_trades(self) -> int:
        return self.successes + self.failures

    def trim(self, max_entries: int = 100):
        """Keep only the last N entries."""
        if len(self.fill_rates) > max_entries:
            self.fill_rates = self.fill_rates[-max_entries:]
        if len(self.slippages) > max_entries:
            self.slippages = self.slippages[-max_entries:]
        if len(self.latencies) > max_entries:
            self.latencies = self.latencies[-max_entries:]


class VenueQualityTracker:
    """Tracks execution quality per exchange/venue over time."""

    def __init__(self):
        self._venue_stats: Dict[str, VenueStats] = {}

    def record_execution(self, exchange: str, success: bool, slippage_pct: float,
                         latency_ms: float, fill_rate: float = 1.0):
        """Record a trade execution outcome."""
        if exchange not in self._venue_stats:
            self._venue_stats[exchange] = VenueStats()
        stats = self._venue_stats[exchange]
        stats.fill_rates.append(fill_rate)
        stats.slippages.append(slippage_pct)
        stats.latencies.append(latency_ms)
        if success:
            stats.successes += 1
        else:
            stats.failures += 1
        stats.trim(100)

    def get_venue_score(self, exchange: str) -> dict:
        """Get venue quality score 0-1."""
        stats = self._venue_stats.get(exchange)
        if not stats or stats.total_trades < 5:
            return {
                "score": 0.7,
                "fill_rate": 1.0,
                "avg_slippage": 0.0,
                "avg_latency": 0.0,
                "success_rate": 1.0,
                "total_trades": stats.total_trades if stats else 0,
                "grade": "B",
            }

        avg_fill = sum(stats.fill_rates) / len(stats.fill_rates) if stats.fill_rates else 1.0
        avg_slip = sum(stats.slippages) / len(stats.slippages) if stats.slippages else 0.0
        avg_lat = sum(stats.latencies) / len(stats.latencies) if stats.latencies else 0.0
        success_rate = stats.successes / stats.total_trades if stats.total_trades > 0 else 1.0

        # Normalize slippage: 0% → 1.0, 1%+ → 0.0
        slip_norm = max(0.0, min(1.0, 1.0 - avg_slip))
        # Simple uptime proxy — success rate itself
        uptime = success_rate

        score = (avg_fill * 0.3 + slip_norm * 0.3 + success_rate * 0.3 + uptime * 0.1)
        score = round(max(0.0, min(1.0, score)), 4)

        if score >= 0.85:
            grade = "A"
        elif score >= 0.70:
            grade = "B"
        elif score >= 0.50:
            grade = "C"
        else:
            grade = "F"

        return {
            "score": score,
            "fill_rate": round(avg_fill, 4),
            "avg_slippage": round(avg_slip, 4),
            "avg_latency": round(avg_lat, 2),
            "success_rate": round(success_rate, 4),
            "total_trades": stats.total_trades,
            "grade": grade,
        }

    def get_all_venues(self) -> dict:
        """Get quality scores for all tracked venues."""
        return {exchange: self.get_venue_score(exchange)
                for exchange in self._venue_stats}


# ─── Trust Score History ──────────────────────────────────────────────────────

class TrustScoreHistory:
    """Records trust scores and correlates with trade outcomes."""

    def __init__(self, max_entries: int = 1000):
        self._history: deque = deque(maxlen=max_entries)

    def record(self, symbol: str, asset_class: str, trust_score: float,
               grade: str, recommendation: str, components: dict,
               trade_executed: bool):
        """Record a trust score evaluation."""
        self._history.append({
            "symbol": symbol,
            "asset_class": asset_class,
            "trust_score": trust_score,
            "grade": grade,
            "recommendation": recommendation,
            "components": {k: round(v, 4) for k, v in components.items()},
            "trade_executed": trade_executed,
            "pnl_pct": None,  # Updated later by update_outcome
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_outcome_correlation(self) -> dict:
        """Analyse: do high-trust trades actually perform better?"""
        by_grade: Dict[str, List[float]] = {}
        for entry in self._history:
            g = entry["grade"]
            if g not in by_grade:
                by_grade[g] = []
            if entry["pnl_pct"] is not None:
                by_grade[g].append(entry["pnl_pct"])

        result = {}
        for grade, pnls in by_grade.items():
            if pnls:
                avg_pnl = sum(pnls) / len(pnls)
                wins = sum(1 for p in pnls if p > 0)
                result[grade] = {
                    "count": len(pnls),
                    "avg_pnl_pct": round(avg_pnl, 4),
                    "win_rate": round(wins / len(pnls), 4) if pnls else 0,
                }
            else:
                result[grade] = {"count": 0, "avg_pnl_pct": 0, "win_rate": 0}
        return result

    def update_outcome(self, symbol: str, pnl_pct: float):
        """Update the most recent entry for this symbol with actual P&L."""
        for entry in reversed(self._history):
            if entry["symbol"] == symbol and entry["pnl_pct"] is None:
                entry["pnl_pct"] = round(pnl_pct, 4)
                break

    def get_recent(self, limit: int = 20) -> list:
        """Get recent trust score evaluations."""
        items = list(self._history)
        return items[-limit:] if len(items) > limit else items

    def get_stats(self) -> dict:
        """Overall stats: avg score, grade distribution, correlation strength."""
        if not self._history:
            return {
                "total_evaluations": 0,
                "avg_trust_score": 0,
                "grade_distribution": {},
                "executed_pct": 0,
            }

        scores = [e["trust_score"] for e in self._history]
        grades: Dict[str, int] = {}
        executed = 0
        for e in self._history:
            grades[e["grade"]] = grades.get(e["grade"], 0) + 1
            if e["trade_executed"]:
                executed += 1

        return {
            "total_evaluations": len(self._history),
            "avg_trust_score": round(sum(scores) / len(scores), 4),
            "grade_distribution": grades,
            "executed_pct": round(executed / len(self._history) * 100, 1),
        }


# ─── Execution Trust Scorer (THE MAIN ENGINE) ────────────────────────────────

class ExecutionTrustScorer:
    """
    Produces a single 0-1 trust score from 10 signal dimensions.

    This replaces the fragmented gate approach where each module
    independently blocks trades. Instead, all signals contribute to
    a weighted composite score, and the final score determines
    execution confidence and position sizing.
    """

    def __init__(self):
        self.venue_tracker = VenueQualityTracker()
        self.history = TrustScoreHistory()

        # ASSET-SPECIFIC WEIGHTS — different assets need different signal emphasis
        self.WEIGHT_PROFILES = {
            "crypto": {
                "signal_strength": 0.15,
                "timeframe_agreement": 0.10,
                "regime_confidence": 0.15,
                "sentiment_alignment": 0.15,
                "strategy_track_record": 0.15,
                "spread_quality": 0.05,
                "data_freshness": 0.05,
                "venue_quality": 0.05,
                "news_safety": 0.10,
                "risk_headroom": 0.05,
            },
            "forex": {
                "signal_strength": 0.15,
                "timeframe_agreement": 0.15,
                "regime_confidence": 0.15,
                "sentiment_alignment": 0.10,
                "strategy_track_record": 0.10,
                "spread_quality": 0.10,
                "data_freshness": 0.05,
                "venue_quality": 0.05,
                "news_safety": 0.10,
                "risk_headroom": 0.05,
            },
            "stocks": {
                "signal_strength": 0.15,
                "timeframe_agreement": 0.10,
                "regime_confidence": 0.10,
                "sentiment_alignment": 0.10,
                "strategy_track_record": 0.15,
                "spread_quality": 0.05,
                "data_freshness": 0.05,
                "venue_quality": 0.05,
                "news_safety": 0.10,
                "risk_headroom": 0.15,
            },
            "indices": {
                "signal_strength": 0.12,
                "timeframe_agreement": 0.12,
                "regime_confidence": 0.15,
                "sentiment_alignment": 0.10,
                "strategy_track_record": 0.12,
                "spread_quality": 0.08,
                "data_freshness": 0.06,
                "venue_quality": 0.05,
                "news_safety": 0.10,
                "risk_headroom": 0.10,
            },
            "commodities": {
                "signal_strength": 0.12,
                "timeframe_agreement": 0.10,
                "regime_confidence": 0.12,
                "sentiment_alignment": 0.15,
                "strategy_track_record": 0.12,
                "spread_quality": 0.08,
                "data_freshness": 0.06,
                "venue_quality": 0.05,
                "news_safety": 0.12,
                "risk_headroom": 0.08,
            },
            "spread_betting": {
                "signal_strength": 0.12,
                "timeframe_agreement": 0.10,
                "regime_confidence": 0.12,
                "sentiment_alignment": 0.10,
                "strategy_track_record": 0.12,
                "spread_quality": 0.12,
                "data_freshness": 0.06,
                "venue_quality": 0.08,
                "news_safety": 0.10,
                "risk_headroom": 0.08,
            },
        }
        # Default weights for unknown asset classes
        self.DEFAULT_WEIGHTS = {k: 0.10 for k in [
            "signal_strength", "timeframe_agreement", "regime_confidence",
            "sentiment_alignment", "strategy_track_record", "spread_quality",
            "data_freshness", "venue_quality", "news_safety", "risk_headroom"
        ]}

    def evaluate(
        self,
        symbol: str,
        asset_class: str,
        direction: str,
        exchange: str,
        # Component inputs
        signal_confidence: float = 0.5,
        mtf_agreement: float = 0.5,
        regime_confidence: float = 0.5,
        regime_aligns_with_direction: bool = True,
        sentiment_score: float = 0.0,
        sentiment_aligns: bool = True,
        strategy_win_rate: float = 0.5,
        strategy_trades_count: int = 0,
        current_spread_vs_avg: float = 1.0,
        data_age_seconds: float = 0,
        news_risk: str = "none",
        portfolio_drawdown_pct: float = 0,
        max_drawdown_pct: float = 10,
        is_spread_bet: bool = False,
    ) -> dict:
        """
        Evaluate execution trust for a potential trade.
        Returns a single trust score 0-1 with grade and recommendation.
        """
        # Determine weight profile
        if is_spread_bet:
            weights = self.WEIGHT_PROFILES["spread_betting"]
        else:
            base_class = (
                asset_class
                .replace("_major", "")
                .replace("_minor", "")
                .replace("shares_us", "stocks")
                .replace("shares_uk", "stocks")
                .replace("metals", "commodities")
            )
            weights = self.WEIGHT_PROFILES.get(base_class, self.DEFAULT_WEIGHTS)

        # Calculate each component score (all normalized to 0-1)
        components = {}

        # 1. Signal strength
        components["signal_strength"] = min(1.0, max(0.0, signal_confidence))

        # 2. Timeframe agreement
        components["timeframe_agreement"] = min(1.0, max(0.0, mtf_agreement))

        # 3. Regime confidence (bonus if regime aligns with direction)
        regime_score = regime_confidence
        if not regime_aligns_with_direction:
            regime_score *= 0.4
        components["regime_confidence"] = min(1.0, max(0.0, regime_score))

        # 4. Sentiment alignment
        sent_norm = (sentiment_score + 1) / 2  # Normalize -1..+1 to 0..1
        if not sentiment_aligns:
            sent_norm = 1 - sent_norm
        components["sentiment_alignment"] = min(1.0, max(0.0, sent_norm))

        # 5. Strategy track record
        if strategy_trades_count < 5:
            components["strategy_track_record"] = 0.5
        else:
            components["strategy_track_record"] = min(1.0, max(0.0, strategy_win_rate))

        # 6. Spread quality (lower is better — 1.0 = normal)
        if current_spread_vs_avg <= 1.0:
            components["spread_quality"] = 1.0
        elif current_spread_vs_avg <= 1.5:
            components["spread_quality"] = 0.7
        elif current_spread_vs_avg <= 2.0:
            components["spread_quality"] = 0.4
        else:
            components["spread_quality"] = 0.1

        # 7. Data freshness
        if data_age_seconds <= 60:
            components["data_freshness"] = 1.0
        elif data_age_seconds <= 300:
            components["data_freshness"] = 0.8
        elif data_age_seconds <= 900:
            components["data_freshness"] = 0.5
        else:
            components["data_freshness"] = 0.2

        # 8. Venue quality
        venue = self.venue_tracker.get_venue_score(exchange)
        components["venue_quality"] = venue["score"]

        # 9. News safety
        news_scores = {"none": 1.0, "low": 0.8, "medium": 0.5, "high": 0.1}
        components["news_safety"] = news_scores.get(news_risk, 0.5)

        # 10. Risk headroom (how far from max drawdown)
        if max_drawdown_pct > 0:
            headroom = 1 - (portfolio_drawdown_pct / max_drawdown_pct)
            components["risk_headroom"] = min(1.0, max(0.0, headroom))
        else:
            components["risk_headroom"] = 1.0

        # Calculate weighted composite score
        trust_score = sum(components[k] * weights[k] for k in components)
        trust_score = round(min(1.0, max(0.0, trust_score)), 4)

        # Determine grade and recommendation
        if trust_score >= 0.80:
            grade = "A"
            recommendation = "execute"
            size_modifier = 1.0
        elif trust_score >= 0.65:
            grade = "B"
            recommendation = "execute"
            size_modifier = 0.7
        elif trust_score >= 0.50:
            grade = "C"
            recommendation = "reduce_size"
            size_modifier = 0.4
        elif trust_score >= 0.35:
            grade = "D"
            recommendation = "wait"
            size_modifier = 0.0
        else:
            grade = "F"
            recommendation = "reject"
            size_modifier = 0.0

        # Build reasoning
        top_positive = sorted(
            [(k, v) for k, v in components.items() if v >= 0.7],
            key=lambda x: -x[1],
        )[:3]
        top_negative = sorted(
            [(k, v) for k, v in components.items() if v < 0.5],
            key=lambda x: x[1],
        )[:3]

        reasoning_parts = []
        if top_positive:
            reasoning_parts.append(
                f"Strong: {', '.join(f'{k}({v:.0%})' for k, v in top_positive)}"
            )
        if top_negative:
            reasoning_parts.append(
                f"Weak: {', '.join(f'{k}({v:.0%})' for k, v in top_negative)}"
            )
        reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Balanced signals"

        result = {
            "trust_score": trust_score,
            "grade": grade,
            "recommendation": recommendation,
            "size_modifier": size_modifier,
            "components": {k: round(v, 4) for k, v in components.items()},
            "weights_used": weights,
            "asset_class": asset_class,
            "symbol": symbol,
            "exchange": exchange,
            "direction": direction,
            "reasoning": reasoning,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Record in history
        self.history.record(
            symbol=symbol,
            asset_class=asset_class,
            trust_score=trust_score,
            grade=grade,
            recommendation=recommendation,
            components=components,
            trade_executed=(recommendation in ("execute", "reduce_size")),
        )

        return result

    def get_analytics(self) -> dict:
        """Get trust score analytics and outcome correlation."""
        return {
            "history_stats": self.history.get_stats(),
            "outcome_correlation": self.history.get_outcome_correlation(),
            "venue_scores": self.venue_tracker.get_all_venues(),
            "recent_evaluations": self.history.get_recent(10),
        }


# Global singleton
trust_scorer = ExecutionTrustScorer()
