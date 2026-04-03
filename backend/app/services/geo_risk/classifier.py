"""
GeoEventClassifier — keyword-based geopolitical event classification.

Fast, deterministic, no API cost.  Each of the 14 event categories has a
curated keyword dictionary with weighted terms.  Confidence is computed from
keyword density and co-occurrence.  Supports multi-label classification.
"""
import hashlib
import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple

from app.services.geo_risk.config import GEO_RISK_CONFIG
from app.services.geo_risk.models import GeoEvent

logger = logging.getLogger(__name__)


# ── Keyword Dictionaries (term → weight) ─────────────────────────────────────
# Higher weight = more diagnostic of that category.

KEYWORD_DICTIONARIES: Dict[str, Dict[str, float]] = {
    "MILITARY_CONFLICT": {
        "war": 1.0, "military": 0.8, "invasion": 1.0, "troops": 0.8,
        "airstrike": 1.0, "bombing": 0.9, "missile": 0.9, "artillery": 0.9,
        "armed forces": 0.8, "combat": 0.8, "battlefield": 0.9,
        "escalation": 0.7, "ceasefire": 0.8, "military operation": 1.0,
        "nato": 0.6, "defense ministry": 0.7, "army": 0.6, "navy": 0.6,
        "air force": 0.6, "drone strike": 0.9, "ground offensive": 1.0,
        "occupation": 0.7, "siege": 0.8, "casualties": 0.7,
        "weapons": 0.5, "ammunition": 0.7, "warzone": 1.0,
    },
    "TERRORISM": {
        "terrorist": 1.0, "terrorism": 1.0, "terror attack": 1.0,
        "bombing attack": 0.9, "suicide bomber": 1.0, "hostage": 0.8,
        "extremist": 0.7, "jihadist": 0.9, "isis": 0.9, "al-qaeda": 0.9,
        "car bomb": 1.0, "mass shooting": 0.8, "lone wolf": 0.8,
        "radicalized": 0.7, "counterterrorism": 0.6, "threat level": 0.6,
        "security alert": 0.5, "improvised explosive": 0.9,
    },
    "SANCTIONS": {
        "sanctions": 1.0, "sanctioned": 0.9, "embargo": 0.9,
        "trade restrictions": 0.8, "asset freeze": 0.9, "blacklist": 0.7,
        "ofac": 0.9, "economic sanctions": 1.0, "export controls": 0.8,
        "import ban": 0.8, "financial sanctions": 0.9, "travel ban": 0.6,
        "entity list": 0.8, "blocked transactions": 0.8,
        "sanctions evasion": 0.8, "secondary sanctions": 0.9,
        "swift ban": 0.9, "oil embargo": 1.0,
    },
    "TRADE_WAR": {
        "tariff": 1.0, "tariffs": 1.0, "trade war": 1.0, "trade dispute": 0.9,
        "protectionism": 0.8, "retaliatory tariff": 1.0, "import duty": 0.8,
        "trade deficit": 0.6, "trade surplus": 0.5, "dumping": 0.7,
        "wto dispute": 0.8, "trade negotiation": 0.6, "trade deal": 0.6,
        "customs duty": 0.7, "trade barrier": 0.8, "countervailing duty": 0.8,
        "most favored nation": 0.5, "trade retaliation": 0.9,
    },
    "ELECTION": {
        "election": 0.9, "vote": 0.5, "ballot": 0.7, "presidential election": 1.0,
        "parliamentary election": 0.9, "referendum": 0.8, "polling": 0.5,
        "inauguration": 0.7, "regime change": 0.9, "political transition": 0.8,
        "coalition government": 0.6, "opposition party": 0.5, "campaign": 0.4,
        "electoral": 0.7, "runoff": 0.7, "primary election": 0.7,
        "midterm": 0.7, "swing state": 0.6, "voter turnout": 0.5,
    },
    "CIVIL_UNREST": {
        "protest": 0.8, "protests": 0.8, "riot": 0.9, "riots": 0.9,
        "demonstration": 0.7, "civil unrest": 1.0, "uprising": 0.9,
        "revolution": 0.9, "martial law": 1.0, "curfew": 0.7,
        "tear gas": 0.8, "looting": 0.8, "general strike": 0.8,
        "mass protest": 0.9, "social unrest": 0.8, "political unrest": 0.8,
        "crackdown": 0.7, "state of emergency": 0.8, "insurrection": 0.9,
    },
    "DIPLOMATIC_CRISIS": {
        "diplomatic crisis": 1.0, "ambassador recall": 1.0,
        "embassy closure": 0.9, "expelled diplomat": 0.9,
        "diplomatic tension": 0.8, "bilateral relations": 0.5,
        "treaty violation": 0.9, "diplomatic row": 0.8,
        "severed relations": 1.0, "diplomatic fallout": 0.8,
        "persona non grata": 0.9, "consulate": 0.4,
        "foreign ministry": 0.4, "summit collapse": 0.8,
    },
    "NATURAL_DISASTER": {
        "earthquake": 1.0, "hurricane": 1.0, "typhoon": 1.0, "tsunami": 1.0,
        "flood": 0.8, "flooding": 0.8, "wildfire": 0.8, "volcano": 0.9,
        "pandemic": 0.9, "epidemic": 0.8, "drought": 0.7, "cyclone": 0.9,
        "tornado": 0.8, "natural disaster": 1.0, "famine": 0.8,
        "landslide": 0.7, "avalanche": 0.6, "heatwave": 0.5,
        "climate emergency": 0.6, "supply chain disruption": 0.5,
    },
    "REGULATORY_CHANGE": {
        "regulation": 0.6, "regulatory": 0.6, "deregulation": 0.7,
        "central bank": 0.7, "interest rate": 0.7, "rate hike": 0.8,
        "rate cut": 0.8, "monetary policy": 0.7, "fiscal policy": 0.6,
        "new regulation": 0.8, "regulatory crackdown": 0.9,
        "compliance": 0.4, "antitrust": 0.7, "policy shift": 0.7,
        "legislation": 0.5, "executive order": 0.7, "federal reserve": 0.6,
        "ecb decision": 0.7, "quantitative easing": 0.7, "tapering": 0.7,
        "crypto regulation": 0.9, "sec ruling": 0.8,
    },
    "ENERGY_CRISIS": {
        "energy crisis": 1.0, "oil supply": 0.8, "energy shortage": 0.9,
        "power outage": 0.7, "blackout": 0.7, "pipeline attack": 0.9,
        "refinery": 0.5, "opec cut": 0.9, "oil production cut": 0.9,
        "fuel shortage": 0.8, "energy price": 0.6, "gas pipeline": 0.7,
        "oil embargo": 0.9, "energy infrastructure": 0.6,
        "power grid": 0.6, "lng": 0.5, "oil price shock": 0.9,
    },
    "CYBER_ATTACK": {
        "cyber attack": 1.0, "cyberattack": 1.0, "hack": 0.7, "hacked": 0.7,
        "ransomware": 0.9, "data breach": 0.8, "malware": 0.8,
        "ddos": 0.8, "phishing": 0.6, "zero-day": 0.8,
        "critical infrastructure": 0.6, "cybersecurity": 0.5,
        "nation-state hack": 1.0, "apt": 0.7, "exploit": 0.5,
        "security breach": 0.7, "compromised": 0.5,
    },
    "REPUTATION_EVENT": {
        "scandal": 0.9, "ceo resign": 0.9, "fraud": 0.8,
        "accounting fraud": 1.0, "esg violation": 0.8, "controversy": 0.6,
        "whistleblower": 0.8, "misconduct": 0.8, "lawsuit": 0.6,
        "class action": 0.7, "regulatory fine": 0.7, "corruption": 0.8,
        "insider trading": 0.9, "embezzlement": 0.9, "cover-up": 0.8,
        "toxic culture": 0.6, "product recall": 0.7, "safety violation": 0.7,
    },
    "COMMODITY_DISRUPTION": {
        "supply disruption": 0.9, "production cut": 0.8,
        "opec": 0.7, "mining strike": 0.9, "crop failure": 0.8,
        "supply shortage": 0.8, "port closure": 0.8, "shipping disruption": 0.8,
        "export ban": 0.8, "stockpile": 0.5, "inventory drawdown": 0.6,
        "rare earth": 0.7, "chip shortage": 0.8, "semiconductor": 0.5,
        "grain export": 0.7, "food supply": 0.6, "metal shortage": 0.7,
    },
    "CURRENCY_CRISIS": {
        "currency crisis": 1.0, "currency collapse": 1.0, "devaluation": 0.9,
        "hyperinflation": 1.0, "capital controls": 0.9, "debt default": 1.0,
        "sovereign default": 1.0, "imf bailout": 0.9, "currency peg": 0.7,
        "foreign reserves": 0.6, "balance of payments": 0.5,
        "capital flight": 0.8, "dollarization": 0.7, "exchange rate crash": 0.9,
        "currency intervention": 0.7, "monetary crisis": 0.9,
    },
}


# ── Region Detection Keywords ────────────────────────────────────────────────

REGION_KEYWORDS: Dict[str, List[str]] = {
    "middle_east": [
        "iran", "iraq", "syria", "yemen", "saudi", "israel", "palestine",
        "gaza", "lebanon", "qatar", "uae", "bahrain", "oman", "kuwait",
        "jordan", "middle east", "persian gulf",
    ],
    "us_china": [
        "united states", "china", "beijing", "washington", "taiwan",
        "us-china", "sino-american", "pentagon", "white house",
    ],
    "europe": [
        "europe", "european union", "germany", "france", "italy", "spain",
        "netherlands", "brussels", "ecb", "eurozone", "uk", "britain",
        "london", "paris", "berlin",
    ],
    "russia": [
        "russia", "moscow", "kremlin", "putin", "ukraine", "kyiv",
        "gazprom", "nord stream", "russian",
    ],
    "asia_pacific": [
        "japan", "south korea", "north korea", "india", "australia",
        "asean", "singapore", "indonesia", "vietnam", "philippines",
        "asia-pacific", "tokyo", "delhi", "mumbai",
    ],
}


class GeoEventClassifier:
    """
    Classifies text into geopolitical event categories using keyword matching.

    Fast, deterministic, no external API calls.  Supports multi-label
    classification and confidence scoring based on keyword density.
    """

    def __init__(self):
        self.keyword_dicts = KEYWORD_DICTIONARIES
        self.region_keywords = REGION_KEYWORDS
        self._min_confidence = GEO_RISK_CONFIG["min_confidence_threshold"]

    def classify(self, title: str, description: str = "",
                 source: str = "unknown", source_url: str = "",
                 tone_score: float = 0.0, article_count: int = 1,
                 timestamp: datetime | None = None) -> GeoEvent | None:
        """
        Classify a news article / event description.

        Returns a GeoEvent if confidence ≥ threshold, else None.
        """
        text = f"{title} {description}".lower()
        if not text.strip():
            return None

        scores = self._score_all_types(text)
        if not scores:
            return None

        # Primary type is the highest-scoring one
        primary_type, primary_conf = scores[0]
        if primary_conf < self._min_confidence:
            return None

        # Secondary types above threshold
        secondary = [t for t, c in scores[1:] if c >= self._min_confidence]

        # Detect regions
        regions = self._detect_regions(text)

        # Severity based on tone and confidence
        severity = self._compute_severity(primary_conf, tone_score, article_count)

        event_id = hashlib.sha256(
            f"{title}:{primary_type}:{source}".encode()
        ).hexdigest()[:16]

        return GeoEvent(
            event_id=event_id,
            event_type=primary_type,
            title=title,
            description=description,
            source=source,
            source_url=source_url,
            confidence=round(primary_conf, 4),
            severity=round(severity, 4),
            regions=regions,
            secondary_types=secondary,
            tone_score=tone_score,
            article_count=article_count,
            timestamp=timestamp or datetime.utcnow(),
        )

    def classify_batch(self, articles: List[Dict]) -> List[GeoEvent]:
        """Classify a batch of articles, returning only those above threshold."""
        events = []
        for article in articles:
            event = self.classify(
                title=article.get("title", ""),
                description=article.get("description", article.get("text", "")),
                source=article.get("source", "unknown"),
                source_url=article.get("url", ""),
                tone_score=article.get("tone", 0.0),
                article_count=article.get("article_count", 1),
                timestamp=article.get("timestamp"),
            )
            if event:
                events.append(event)
        return events

    def _score_all_types(self, text: str) -> List[Tuple[str, float]]:
        """Score text against all event type dictionaries, return sorted."""
        results = []
        words = set(re.findall(r'\b[\w-]+\b', text))

        for event_type, keywords in self.keyword_dicts.items():
            score = 0.0
            matches = 0
            total_weight = sum(keywords.values())

            for keyword, weight in keywords.items():
                # Check for multi-word keywords via substring, single words via set
                if " " in keyword:
                    if keyword in text:
                        score += weight
                        matches += 1
                else:
                    if keyword in words:
                        score += weight
                        matches += 1

            if matches == 0:
                continue

            # Confidence = weighted match ratio, boosted by match count
            raw_confidence = score / total_weight
            # Co-occurrence bonus: more matching keywords = higher confidence
            co_occurrence_bonus = min(0.3, matches * 0.05)
            confidence = min(1.0, raw_confidence + co_occurrence_bonus)

            if confidence >= self._min_confidence:
                results.append((event_type, confidence))

        results.sort(key=lambda x: -x[1])
        return results

    def _detect_regions(self, text: str) -> List[str]:
        """Detect geographic regions mentioned in text."""
        regions = []
        for region, keywords in self.region_keywords.items():
            for kw in keywords:
                if kw in text:
                    regions.append(region)
                    break
        return regions

    def _compute_severity(self, confidence: float, tone_score: float,
                          article_count: int) -> float:
        """
        Compute event severity from confidence, tone, and coverage volume.

        Tone: GDELT range is roughly -100 to +100; more negative = worse.
        """
        base = confidence

        # Negative tone amplifies severity
        if tone_score < -5:
            tone_factor = min(0.2, abs(tone_score) / 100 * 0.3)
            base += tone_factor
        elif tone_score > 5:
            base -= 0.05

        # High article count = more significant
        if article_count > 100:
            base += 0.15
        elif article_count > 50:
            base += 0.10
        elif article_count > 10:
            base += 0.05

        return min(1.0, max(0.0, base))

    def get_keyword_dict(self, event_type: str) -> Dict[str, float]:
        """Return the keyword dictionary for an event type."""
        return self.keyword_dicts.get(event_type, {})

    def get_all_event_types(self) -> List[str]:
        """Return all supported event types."""
        return sorted(self.keyword_dicts.keys())
