"""
Geopolitical Risk & Sentiment Intelligence Module.

Monitors real-time geopolitical events, news sentiment, and reputation signals
to produce per-asset risk/opportunity scores that feed into the Execution Trust
Layer pipeline.

Components:
1. GeoEventClassifier  — keyword-based event type classification
2. GeoRiskScorer       — composite risk scoring with geographic amplification
3. AssetImpactScorer   — maps events to asset class impacts via impact matrix
4. GeoNewsIngester     — GDELT + RSS data ingestion
5. GeoMonitor          — background polling and threshold alerting
"""
from app.services.geo_risk.classifier import GeoEventClassifier
from app.services.geo_risk.scorer import GeoRiskScorer, AssetImpactScorer
from app.services.geo_risk.ingester import GeoNewsIngester
from app.services.geo_risk.monitor import GeoMonitor, geo_monitor

__all__ = [
    "GeoEventClassifier",
    "GeoRiskScorer",
    "AssetImpactScorer",
    "GeoNewsIngester",
    "GeoMonitor",
    "geo_monitor",
]
