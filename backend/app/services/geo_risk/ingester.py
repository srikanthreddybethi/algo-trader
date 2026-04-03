"""
GeoNewsIngester — data ingestion from GDELT DOC 2.0 API and RSS feeds.

GDELT (primary): Free, no API key, updates every 15 minutes.
RSS (secondary): Free, real-time breaking news detection.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser
import httpx

from app.services.geo_risk.config import GEO_RISK_CONFIG

logger = logging.getLogger(__name__)

# ── Cache ────────────────────────────────────────────────────────────────────

_ingester_cache: Dict[str, Any] = {}
_ingester_cache_ts: Dict[str, datetime] = {}


def _get_cached(key: str, ttl_minutes: float) -> Optional[Any]:
    if key in _ingester_cache and key in _ingester_cache_ts:
        age = (datetime.utcnow() - _ingester_cache_ts[key]).total_seconds() / 60
        if age < ttl_minutes:
            return _ingester_cache[key]
    return None


def _set_cached(key: str, value: Any) -> None:
    _ingester_cache[key] = value
    _ingester_cache_ts[key] = datetime.utcnow()


class GeoNewsIngester:
    """
    Ingests geopolitical news from multiple free sources.

    Primary: GDELT DOC 2.0 API (free, no key, 15-min updates)
    Secondary: RSS feeds (free, real-time)
    """

    def __init__(self):
        self._gdelt_url = GEO_RISK_CONFIG["gdelt_base_url"]
        self._gdelt_max = GEO_RISK_CONFIG["gdelt_max_records"]
        self._gdelt_lang = GEO_RISK_CONFIG["gdelt_source_lang"]
        self._rss_feeds = GEO_RISK_CONFIG["rss_feeds"]
        self._last_gdelt_fetch: Optional[datetime] = None
        self._last_rss_fetch: Optional[datetime] = None

    # ── GDELT DOC 2.0 ────────────────────────────────────────────────────

    async def fetch_gdelt(self, query: str = "geopolitical risk",
                          mode: str = "artlist") -> List[Dict]:
        """
        Query GDELT DOC 2.0 API for articles.

        Modes:
          artlist      — list of articles with metadata
          timelinetone — sentiment timeline
          timelinevol  — volume timeline
        """
        cache_key = f"gdelt:{query}:{mode}"
        cached = _get_cached(cache_key, GEO_RISK_CONFIG["gdelt_poll_interval_minutes"])
        if cached is not None:
            return cached

        params = {
            "query": f"{query} sourcelang:{self._gdelt_lang}",
            "mode": mode,
            "maxrecords": str(self._gdelt_max),
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(self._gdelt_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("GDELT fetch failed for query=%s: %s", query, exc)
            return []

        articles = self._parse_gdelt_response(data, mode)
        self._last_gdelt_fetch = datetime.utcnow()
        _set_cached(cache_key, articles)
        return articles

    async def fetch_gdelt_by_theme(self, theme: str) -> List[Dict]:
        """Query GDELT by theme code (e.g. TAX_FNCACT_SANCTIONS)."""
        return await self.fetch_gdelt(query=f"theme:{theme}")

    async def fetch_gdelt_geopolitical(self) -> List[Dict]:
        """Fetch a broad set of geopolitical articles from GDELT."""
        queries = [
            "war conflict military",
            "sanctions embargo tariff",
            "terrorism attack",
            "election political crisis",
            "energy crisis oil supply",
            "cyber attack infrastructure",
            "currency crisis default",
        ]
        all_articles: List[Dict] = []
        tasks = [self.fetch_gdelt(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
        return all_articles

    def _parse_gdelt_response(self, data: Dict, mode: str) -> List[Dict]:
        """Parse GDELT JSON response into normalized articles."""
        articles = []

        if mode == "artlist":
            raw_articles = data.get("articles", [])
            for art in raw_articles:
                articles.append({
                    "title": art.get("title", ""),
                    "description": art.get("seendate", ""),
                    "url": art.get("url", ""),
                    "source": art.get("domain", "gdelt"),
                    "tone": art.get("tone", 0.0),
                    "timestamp": self._parse_gdelt_date(art.get("seendate", "")),
                    "language": art.get("language", "English"),
                    "source_country": art.get("sourcecountry", ""),
                })
        elif mode == "timelinetone":
            timeline = data.get("timeline", [])
            for series in timeline:
                for point in series.get("data", []):
                    articles.append({
                        "title": f"Sentiment: {point.get('value', 0):.1f}",
                        "tone": point.get("value", 0.0),
                        "timestamp": self._parse_gdelt_date(point.get("date", "")),
                        "source": "gdelt_timeline",
                    })

        return articles

    def _parse_gdelt_date(self, datestr: str) -> Optional[datetime]:
        """Parse GDELT date string (yyyyMMddHHmmss or yyyy-MM-dd)."""
        if not datestr:
            return None
        try:
            datestr = datestr.strip().replace("T", " ").replace("Z", "")
            if len(datestr) == 14:
                return datetime.strptime(datestr, "%Y%m%d%H%M%S")
            if len(datestr) == 8:
                return datetime.strptime(datestr, "%Y%m%d")
            return datetime.fromisoformat(datestr)
        except (ValueError, TypeError):
            return None

    # ── RSS Feeds ─────────────────────────────────────────────────────────

    async def fetch_rss(self) -> List[Dict]:
        """Fetch and parse all configured RSS feeds."""
        cache_key = "rss:all"
        cached = _get_cached(cache_key, GEO_RISK_CONFIG["rss_poll_interval_minutes"])
        if cached is not None:
            return cached

        all_articles: List[Dict] = []
        for feed_config in self._rss_feeds:
            try:
                articles = await self._fetch_single_rss(
                    feed_config["url"], feed_config["name"]
                )
                all_articles.extend(articles)
            except Exception as exc:
                logger.warning("RSS fetch failed for %s: %s", feed_config["name"], exc)

        self._last_rss_fetch = datetime.utcnow()
        _set_cached(cache_key, all_articles)
        return all_articles

    async def _fetch_single_rss(self, url: str, source_name: str) -> List[Dict]:
        """Fetch and parse a single RSS feed."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                content = resp.text
        except Exception as exc:
            logger.warning("Failed to fetch RSS %s: %s", source_name, exc)
            return []

        feed = feedparser.parse(content)
        articles = []
        for entry in feed.entries[:50]:  # Cap per feed
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    pass

            articles.append({
                "title": getattr(entry, "title", ""),
                "description": getattr(entry, "summary", ""),
                "url": getattr(entry, "link", ""),
                "source": source_name,
                "tone": 0.0,
                "timestamp": pub_date,
            })

        return articles

    # ── Combined fetch ────────────────────────────────────────────────────

    async def fetch_all(self) -> List[Dict]:
        """Fetch from all sources in parallel."""
        gdelt_task = self.fetch_gdelt_geopolitical()
        rss_task = self.fetch_rss()
        gdelt_articles, rss_articles = await asyncio.gather(
            gdelt_task, rss_task, return_exceptions=True
        )

        all_articles = []
        if isinstance(gdelt_articles, list):
            all_articles.extend(gdelt_articles)
        if isinstance(rss_articles, list):
            all_articles.extend(rss_articles)

        return all_articles

    def get_status(self) -> Dict:
        """Return ingester status."""
        return {
            "last_gdelt_fetch": self._last_gdelt_fetch.isoformat() if self._last_gdelt_fetch else None,
            "last_rss_fetch": self._last_rss_fetch.isoformat() if self._last_rss_fetch else None,
            "rss_feeds_configured": len(self._rss_feeds),
            "gdelt_url": self._gdelt_url,
            "cache_entries": len(_ingester_cache),
        }
