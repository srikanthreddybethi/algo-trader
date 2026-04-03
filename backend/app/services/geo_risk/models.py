"""
Data models for the Geopolitical Risk module.

Plain dataclasses — no ORM dependency so the module stays self-contained
and testable without a database.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class GeoEvent:
    """A classified geopolitical event."""
    event_id: str
    event_type: str                        # e.g. "MILITARY_CONFLICT"
    title: str
    description: str
    source: str                            # "gdelt", "rss", "manual"
    source_url: str = ""
    confidence: float = 0.0                # 0.0–1.0
    severity: float = 0.5                  # 0.0–1.0
    regions: List[str] = field(default_factory=list)
    secondary_types: List[str] = field(default_factory=list)  # multi-label
    tone_score: float = 0.0                # GDELT average tone
    article_count: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return (datetime.utcnow() - self.timestamp).total_seconds() / 3600


@dataclass
class AssetRiskScore:
    """Geo risk assessment for a single asset."""
    asset: str
    asset_class: str
    geo_risk_score: float = 0.0             # 0 = no risk, 1 = extreme
    geo_opportunity_score: float = 0.0
    net_signal: float = 0.0                 # negative = bearish, positive = bullish
    signal_strength: str = "weak"           # weak/moderate/strong/extreme
    dominant_events: List[Dict] = field(default_factory=list)
    recommended_action: str = "hold"
    position_size_modifier: float = 1.0
    confidence: float = 0.0
    data_freshness_minutes: float = 0.0
    sources_analyzed: int = 0


@dataclass
class GeoAlert:
    """User-configured alert for geo risk thresholds."""
    alert_id: str
    asset_class: Optional[str] = None       # None = all
    event_types: List[str] = field(default_factory=list)  # empty = all
    threshold: float = 0.7
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    description: str = ""


@dataclass
class HeatmapRegion:
    """Risk level for a geographic region."""
    region: str
    risk_score: float = 0.0
    event_count: int = 0
    dominant_event_type: str = ""
    trending: str = "stable"                # rising/falling/stable
