"""
GeoRiskScorer + AssetImpactScorer — composite geopolitical risk scoring.

AssetImpactScorer maps events → asset impacts using the impact matrix with
geographic amplification and recency decay.

GeoRiskScorer aggregates across all active events to produce per-asset
composite risk/opportunity scores.
"""
import logging
import math
from datetime import datetime
from typing import Dict, List, Optional

from app.services.geo_risk.config import GEO_RISK_CONFIG
from app.services.geo_risk.impact_matrix import IMPACT_MATRIX, get_impact
from app.services.geo_risk.models import AssetRiskScore, GeoEvent

logger = logging.getLogger(__name__)


class AssetImpactScorer:
    """Maps a single event to per-asset-class impact scores."""

    def __init__(self):
        self._geo_amplifiers = GEO_RISK_CONFIG["geographic_amplifiers"]
        self._acute_types = set(GEO_RISK_CONFIG["acute_event_types"])
        self._structural_types = set(GEO_RISK_CONFIG["structural_event_types"])
        self._half_lives = GEO_RISK_CONFIG["event_half_life_hours"]

    def score_event(self, event: GeoEvent, asset_class: str) -> Dict:
        """
        Score a single event's impact on an asset class.

        Returns dict with: risk_contribution, opportunity_contribution,
        direction, magnitude, recency_factor, geo_amplifier.
        """
        impact = get_impact(event.event_type, asset_class)
        direction = impact.get("direction", "neutral")
        magnitude = impact.get("magnitude", 0.0)

        # Recency decay
        recency = self._recency_factor(event)

        # Geographic amplification
        geo_amp = self._geographic_amplifier(event, asset_class)

        # Effective impact
        effective = (
            event.severity
            * event.confidence
            * magnitude
            * recency
            * geo_amp
        )

        risk_contribution = 0.0
        opportunity_contribution = 0.0

        if direction == "bearish":
            risk_contribution = effective
        elif direction == "bullish":
            opportunity_contribution = effective
        elif direction == "varies":
            # Split — slightly more risk-weighted for safety
            risk_contribution = effective * 0.4
            opportunity_contribution = effective * 0.3

        return {
            "event_type": event.event_type,
            "event_id": event.event_id,
            "direction": direction,
            "magnitude": round(magnitude, 4),
            "recency_factor": round(recency, 4),
            "geo_amplifier": round(geo_amp, 4),
            "risk_contribution": round(risk_contribution, 4),
            "opportunity_contribution": round(opportunity_contribution, 4),
            "effective_impact": round(effective, 4),
        }

    def _recency_factor(self, event: GeoEvent) -> float:
        """Exponential decay based on event age and type."""
        is_acute = event.event_type in self._acute_types
        half_life = (
            self._half_lives["acute"] if is_acute
            else self._half_lives["structural"]
        )
        decay_rate = math.log(2) / half_life
        return math.exp(-decay_rate * event.age_hours)

    def _geographic_amplifier(self, event: GeoEvent, asset_class: str) -> float:
        """Amplify impact for events in key regions."""
        if not event.regions:
            return 1.0

        max_amp = 1.0
        for region in event.regions:
            region_config = self._geo_amplifiers.get(region, {})
            amplifiers = region_config.get("amplifiers", {})

            # Check for exact match and prefix matches
            for amp_key, amp_value in amplifiers.items():
                if amp_key == asset_class or asset_class.startswith(amp_key.split("_")[0]):
                    max_amp = max(max_amp, amp_value)

        return max_amp


class GeoRiskScorer:
    """
    Produces composite per-asset geopolitical risk + opportunity scores
    by aggregating all active events through the AssetImpactScorer.
    """

    def __init__(self):
        self.impact_scorer = AssetImpactScorer()
        self._thresholds = GEO_RISK_CONFIG["risk_thresholds"]
        self._strength_thresholds = GEO_RISK_CONFIG["signal_strength_thresholds"]
        self._action_thresholds = GEO_RISK_CONFIG["action_thresholds"]

    def score_asset(self, asset: str, asset_class: str,
                    events: List[GeoEvent],
                    data_freshness_minutes: float = 0.0) -> AssetRiskScore:
        """
        Compute composite geo risk score for a single asset.

        Aggregates contributions from all active events, applying recency
        decay and geographic amplification.
        """
        if not events:
            return AssetRiskScore(
                asset=asset,
                asset_class=asset_class,
                data_freshness_minutes=data_freshness_minutes,
            )

        total_risk = 0.0
        total_opportunity = 0.0
        contributions = []

        for event in events:
            result = self.impact_scorer.score_event(event, asset_class)
            total_risk += result["risk_contribution"]
            total_opportunity += result["opportunity_contribution"]

            if result["effective_impact"] > 0.01:
                contributions.append({
                    "type": event.event_type,
                    "description": event.title[:120],
                    "contribution": result["effective_impact"],
                    "direction": result["direction"],
                })

        # Normalize to 0–1 (cap at 1.0)
        geo_risk = min(1.0, total_risk)
        geo_opp = min(1.0, total_opportunity)
        net_signal = geo_opp - geo_risk

        # Signal strength
        abs_signal = abs(net_signal)
        if abs_signal >= self._strength_thresholds["extreme"]:
            strength = "extreme"
        elif abs_signal >= self._strength_thresholds["strong"]:
            strength = "strong"
        elif abs_signal >= self._strength_thresholds["moderate"]:
            strength = "moderate"
        else:
            strength = "weak"

        # Recommended action
        action = self._recommend_action(geo_risk, geo_opp, net_signal)

        # Position size modifier
        size_mod = self._position_size_modifier(geo_risk, geo_opp)

        # Confidence from data volume and recency
        confidence = self._compute_confidence(events, data_freshness_minutes)

        # Top contributions sorted by impact
        contributions.sort(key=lambda c: -c["contribution"])
        top_events = contributions[:5]

        return AssetRiskScore(
            asset=asset,
            asset_class=asset_class,
            geo_risk_score=round(geo_risk, 4),
            geo_opportunity_score=round(geo_opp, 4),
            net_signal=round(net_signal, 4),
            signal_strength=strength,
            dominant_events=top_events,
            recommended_action=action,
            position_size_modifier=round(size_mod, 2),
            confidence=round(confidence, 4),
            data_freshness_minutes=round(data_freshness_minutes, 1),
            sources_analyzed=len(events),
        )

    def score_all_assets(self, assets: Dict[str, str],
                         events: List[GeoEvent],
                         data_freshness_minutes: float = 0.0) -> Dict[str, AssetRiskScore]:
        """
        Score multiple assets at once.

        assets: dict of {symbol: asset_class}
        """
        return {
            symbol: self.score_asset(
                symbol, ac, events, data_freshness_minutes
            )
            for symbol, ac in assets.items()
        }

    def get_news_risk_level(self, events: List[GeoEvent],
                            asset_class: str = "crypto") -> str:
        """
        Map current geo risk to a news_risk level compatible with the
        ExecutionTrustScorer interface: "none" / "low" / "medium" / "high".
        """
        if not events:
            return "none"

        # Build a quick aggregate
        total_impact = 0.0
        for event in events:
            result = self.impact_scorer.score_event(event, asset_class)
            total_impact += result["risk_contribution"]

        total_impact = min(1.0, total_impact)

        if total_impact >= self._thresholds["high"]:
            return "high"
        elif total_impact >= self._thresholds["moderate"]:
            return "medium"
        elif total_impact >= self._thresholds["low"]:
            return "low"
        return "none"

    def _recommend_action(self, risk: float, opp: float,
                          net_signal: float) -> str:
        """Determine recommended action from scores."""
        if risk >= self._thresholds["extreme"]:
            return "reduce_exposure"
        if risk >= self._thresholds["high"]:
            return "reduce_exposure"
        if risk >= self._thresholds["moderate"]:
            return "hedge"
        if opp >= 0.5 and net_signal > 0:
            return "increase_exposure"
        return "hold"

    def _position_size_modifier(self, risk: float, opp: float) -> float:
        """Compute position size multiplier from risk/opportunity balance."""
        if risk >= self._thresholds["extreme"]:
            return 0.2
        if risk >= self._thresholds["high"]:
            return 0.4
        if risk >= self._thresholds["moderate"]:
            return 0.6
        if opp >= 0.7:
            return 1.2  # Opportunity boost
        if risk >= self._thresholds["low"]:
            return 0.8
        return 1.0

    def _compute_confidence(self, events: List[GeoEvent],
                            freshness: float) -> float:
        """Confidence based on data quality and volume."""
        if not events:
            return 0.0

        # Base confidence from event count
        event_count = len(events)
        if event_count >= 20:
            volume_conf = 0.9
        elif event_count >= 10:
            volume_conf = 0.7
        elif event_count >= 5:
            volume_conf = 0.5
        else:
            volume_conf = 0.3

        # Freshness penalty
        if freshness <= 15:
            fresh_conf = 1.0
        elif freshness <= 60:
            fresh_conf = 0.8
        elif freshness <= 180:
            fresh_conf = 0.5
        else:
            fresh_conf = 0.3

        # Average event confidence
        avg_conf = sum(e.confidence for e in events) / event_count

        return min(1.0, volume_conf * 0.4 + fresh_conf * 0.3 + avg_conf * 0.3)
