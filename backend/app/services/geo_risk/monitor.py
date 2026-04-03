"""
GeoMonitor — background service that polls GDELT/RSS, maintains active events,
and provides the query interface used by the API layer and trust scorer.
"""
import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.services.geo_risk.classifier import GeoEventClassifier
from app.services.geo_risk.config import GEO_RISK_CONFIG
from app.services.geo_risk.ingester import GeoNewsIngester
from app.services.geo_risk.models import AssetRiskScore, GeoAlert, GeoEvent, HeatmapRegion
from app.services.geo_risk.scorer import GeoRiskScorer

logger = logging.getLogger(__name__)


class GeoMonitor:
    """
    Central orchestrator for the Geopolitical Risk module.

    - Polls GDELT every 15 minutes and RSS every 5 minutes
    - Maintains a rolling window of classified events (last 30 days)
    - Exposes query methods used by the API router and trust layer
    - Manages alert configurations
    """

    def __init__(self):
        self.classifier = GeoEventClassifier()
        self.ingester = GeoNewsIngester()
        self.scorer = GeoRiskScorer()

        # Active events keyed by event_id
        self._events: Dict[str, GeoEvent] = {}
        self._max_events = GEO_RISK_CONFIG["max_events_tracked"]
        self._event_window_days = GEO_RISK_CONFIG["event_window_days"]

        # Alert configs
        self._alerts: Dict[str, GeoAlert] = {}

        # Score cache
        self._score_cache: Dict[str, AssetRiskScore] = {}
        self._last_score_time: Optional[datetime] = None

        # Polling state
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_poll: Optional[datetime] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self):
        """Start background polling."""
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("GeoMonitor started")

    async def stop(self):
        """Stop background polling."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("GeoMonitor stopped")

    async def _poll_loop(self):
        """Main polling loop — fetch and classify on schedule."""
        while self._running:
            try:
                await self.refresh()
            except Exception as exc:
                logger.error("GeoMonitor poll error: %s", exc)
            # Sleep for the shorter interval (RSS = 5 min)
            await asyncio.sleep(GEO_RISK_CONFIG["rss_poll_interval_minutes"] * 60)

    # ── Data Refresh ──────────────────────────────────────────────────────

    async def refresh(self):
        """Fetch latest data from all sources, classify, and store events."""
        articles = await self.ingester.fetch_all()
        if not articles:
            return

        new_events = self.classifier.classify_batch(articles)

        for event in new_events:
            # De-duplicate by event_id
            if event.event_id not in self._events:
                self._events[event.event_id] = event

        # Prune old events
        self._prune_old_events()

        # Invalidate score cache
        self._score_cache.clear()
        self._last_poll = datetime.utcnow()

        logger.info(
            "GeoMonitor refreshed: %d articles → %d new events (%d total active)",
            len(articles), len(new_events), len(self._events),
        )

    def _prune_old_events(self):
        """Remove events older than the configured window."""
        cutoff = datetime.utcnow() - timedelta(days=self._event_window_days)
        expired = [
            eid for eid, ev in self._events.items()
            if ev.timestamp and ev.timestamp < cutoff
        ]
        for eid in expired:
            del self._events[eid]

        # Enforce max events limit
        if len(self._events) > self._max_events:
            sorted_events = sorted(
                self._events.items(),
                key=lambda x: x[1].timestamp or datetime.min,
            )
            to_remove = len(self._events) - self._max_events
            for eid, _ in sorted_events[:to_remove]:
                del self._events[eid]

    # ── Event Queries ─────────────────────────────────────────────────────

    def get_active_events(self, event_type: Optional[str] = None,
                          region: Optional[str] = None,
                          limit: int = 50) -> List[GeoEvent]:
        """Get active events, optionally filtered."""
        events = list(self._events.values())

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if region:
            events = [e for e in events if region in e.regions]

        events.sort(key=lambda e: e.timestamp or datetime.min, reverse=True)
        return events[:limit]

    def get_event(self, event_id: str) -> Optional[GeoEvent]:
        """Get a single event by ID."""
        return self._events.get(event_id)

    def get_event_count(self) -> int:
        return len(self._events)

    # ── Scoring ───────────────────────────────────────────────────────────

    def score_asset(self, asset: str, asset_class: str) -> AssetRiskScore:
        """Get geo risk score for a single asset."""
        cache_key = f"{asset}:{asset_class}"
        if cache_key in self._score_cache:
            return self._score_cache[cache_key]

        events = list(self._events.values())
        freshness = self._data_freshness_minutes()
        score = self.scorer.score_asset(asset, asset_class, events, freshness)
        self._score_cache[cache_key] = score
        return score

    def score_all_assets(self, assets: Dict[str, str]) -> Dict[str, AssetRiskScore]:
        """Score multiple assets."""
        events = list(self._events.values())
        freshness = self._data_freshness_minutes()
        return self.scorer.score_all_assets(assets, events, freshness)

    def get_news_risk_level(self, asset_class: str = "crypto") -> str:
        """Get news risk level for trust scorer integration."""
        events = list(self._events.values())
        return self.scorer.get_news_risk_level(events, asset_class)

    def _data_freshness_minutes(self) -> float:
        """Minutes since last successful data poll."""
        if self._last_poll is None:
            return 999.0
        delta = (datetime.utcnow() - self._last_poll).total_seconds() / 60
        return delta

    # ── Risk Timeline ─────────────────────────────────────────────────────

    def get_risk_timeline(self, asset_class: str = "equities",
                          hours: int = 168) -> List[Dict]:
        """
        Build a risk timeline by bucketing events into hourly bins
        and computing aggregate risk for each bin.
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)
        events = [e for e in self._events.values()
                  if e.timestamp and e.timestamp >= cutoff]

        # Bucket by hour
        bins: Dict[str, List[GeoEvent]] = {}
        for event in events:
            hour_key = event.timestamp.strftime("%Y-%m-%d %H:00")
            if hour_key not in bins:
                bins[hour_key] = []
            bins[hour_key].append(event)

        timeline = []
        for hour_key in sorted(bins.keys()):
            bin_events = bins[hour_key]
            # Quick aggregate risk
            total = 0.0
            for ev in bin_events:
                result = self.scorer.impact_scorer.score_event(ev, asset_class)
                total += result["risk_contribution"]
            timeline.append({
                "timestamp": hour_key,
                "risk_score": round(min(1.0, total), 4),
                "event_count": len(bin_events),
            })

        return timeline

    # ── Heatmap ───────────────────────────────────────────────────────────

    def get_heatmap(self) -> List[HeatmapRegion]:
        """Compute risk heatmap by geographic region."""
        region_events: Dict[str, List[GeoEvent]] = {}
        for event in self._events.values():
            for region in event.regions:
                if region not in region_events:
                    region_events[region] = []
                region_events[region].append(event)

        heatmap = []
        for region, events in region_events.items():
            if not events:
                continue
            # Aggregate severity
            total_severity = sum(e.severity * e.confidence for e in events)
            avg_severity = total_severity / len(events)
            # Dominant event type
            type_counts: Dict[str, int] = {}
            for e in events:
                type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
            dominant = max(type_counts, key=type_counts.get) if type_counts else ""

            heatmap.append(HeatmapRegion(
                region=region,
                risk_score=round(min(1.0, avg_severity), 4),
                event_count=len(events),
                dominant_event_type=dominant,
                trending="rising" if len(events) > 5 else "stable",
            ))

        heatmap.sort(key=lambda h: -h.risk_score)
        return heatmap

    # ── Alerts ────────────────────────────────────────────────────────────

    def get_alerts(self) -> List[GeoAlert]:
        return list(self._alerts.values())

    def create_alert(self, asset_class: Optional[str] = None,
                     event_types: Optional[List[str]] = None,
                     threshold: float = 0.7,
                     description: str = "") -> GeoAlert:
        alert = GeoAlert(
            alert_id=uuid.uuid4().hex[:12],
            asset_class=asset_class,
            event_types=event_types or [],
            threshold=threshold,
            description=description,
        )
        self._alerts[alert.alert_id] = alert
        return alert

    def get_alert(self, alert_id: str) -> Optional[GeoAlert]:
        return self._alerts.get(alert_id)

    # ── Manual Event Evaluation ───────────────────────────────────────────

    def evaluate_event(self, title: str, description: str = "",
                       source: str = "manual") -> Optional[GeoEvent]:
        """Classify a manually submitted event description."""
        event = self.classifier.classify(
            title=title,
            description=description,
            source=source,
        )
        if event:
            self._events[event.event_id] = event
            self._score_cache.clear()
        return event

    # ── Analytics ─────────────────────────────────────────────────────────

    def get_analytics(self) -> Dict:
        """Return analytics data for the geo risk module."""
        events = list(self._events.values())
        type_counts: Dict[str, int] = {}
        region_counts: Dict[str, int] = {}
        for e in events:
            type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
            for r in e.regions:
                region_counts[r] = region_counts.get(r, 0) + 1

        return {
            "total_active_events": len(events),
            "events_by_type": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
            "events_by_region": dict(sorted(region_counts.items(), key=lambda x: -x[1])),
            "avg_severity": round(
                sum(e.severity for e in events) / len(events), 4
            ) if events else 0,
            "avg_confidence": round(
                sum(e.confidence for e in events) / len(events), 4
            ) if events else 0,
            "data_freshness_minutes": round(self._data_freshness_minutes(), 1),
            "alerts_configured": len(self._alerts),
            "ingester_status": self.ingester.get_status(),
        }

    # ── Status ────────────────────────────────────────────────────────────

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "total_events": len(self._events),
            "last_poll": self._last_poll.isoformat() if self._last_poll else None,
            "data_freshness_minutes": round(self._data_freshness_minutes(), 1),
            "alerts": len(self._alerts),
        }


# Global singleton
geo_monitor = GeoMonitor()
