"""
Unit tests for GeoNewsIngester — GDELT and RSS data ingestion.

Uses mocked HTTP responses for deterministic testing.

Run:  python test_geo_risk_ingester.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from unittest.mock import AsyncMock, patch, MagicMock
from app.services.geo_risk.ingester import GeoNewsIngester, _ingester_cache

TOTAL = 0
PASSED = 0
FAILED = 0
FAILURES = []


def check(condition: bool, pass_msg: str, fail_msg: str):
    global TOTAL, PASSED, FAILED
    TOTAL += 1
    if condition:
        PASSED += 1
        print(f"  ✓ {pass_msg}")
    else:
        FAILED += 1
        FAILURES.append(fail_msg)
        print(f"  ✗ {fail_msg}")


# ── Mock GDELT Response ──────────────────────────────────────────────────────

MOCK_GDELT_RESPONSE = {
    "articles": [
        {
            "title": "Russia escalates military operations in eastern Ukraine",
            "url": "https://example.com/article1",
            "domain": "reuters.com",
            "seendate": "20260401120000",
            "tone": -5.2,
            "language": "English",
            "sourcecountry": "US",
        },
        {
            "title": "US Treasury imposes new sanctions on Russian banks",
            "url": "https://example.com/article2",
            "domain": "bbc.co.uk",
            "seendate": "20260401100000",
            "tone": -3.8,
            "language": "English",
            "sourcecountry": "UK",
        },
        {
            "title": "China retaliates with tariffs in trade war escalation",
            "url": "https://example.com/article3",
            "domain": "aljazeera.com",
            "seendate": "20260401080000",
            "tone": -4.1,
            "language": "English",
            "sourcecountry": "QA",
        },
    ]
}

# ── Mock RSS Feed ─────────────────────────────────────────────────────────────

MOCK_RSS_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Test Feed</title>
<item>
<title>Major earthquake strikes coastal region</title>
<description>A 7.2 magnitude earthquake has devastated the coastal area</description>
<link>https://example.com/quake</link>
<pubDate>Wed, 01 Apr 2026 10:00:00 GMT</pubDate>
</item>
<item>
<title>Election results contested in key state</title>
<description>Opposition claims fraud in presidential election</description>
<link>https://example.com/election</link>
<pubDate>Wed, 01 Apr 2026 09:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""


async def run_tests():
    global TOTAL, PASSED, FAILED

    # Clear cache between test runs
    _ingester_cache.clear()

    ingester = GeoNewsIngester()

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 1. GDELT PARSING ═══")
    # ═══════════════════════════════════════════════════════════════

    articles = ingester._parse_gdelt_response(MOCK_GDELT_RESPONSE, "artlist")
    check(len(articles) == 3, f"Parsed 3 GDELT articles ({len(articles)})", f"Expected 3, got {len(articles)}")

    if articles:
        art = articles[0]
        check("title" in art, "Article has title", "Missing title")
        check("url" in art, "Article has URL", "Missing URL")
        check("tone" in art, "Article has tone", "Missing tone")
        check("source" in art, "Article has source", "Missing source")
        check(art["tone"] == -5.2, f"Tone preserved: {art['tone']}", f"Tone wrong: {art['tone']}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 2. GDELT DATE PARSING ═══")
    # ═══════════════════════════════════════════════════════════════

    # yyyyMMddHHmmss format
    dt = ingester._parse_gdelt_date("20260401120000")
    check(dt is not None, "Parsed GDELT date format", "Failed to parse date")
    if dt:
        check(dt.year == 2026 and dt.month == 4, f"Date correct: {dt}", f"Date wrong: {dt}")

    # yyyyMMdd format
    dt2 = ingester._parse_gdelt_date("20260401")
    check(dt2 is not None, "Parsed short GDELT date", "Failed to parse short date")

    # Empty
    check(ingester._parse_gdelt_date("") is None, "Empty date → None", "Should return None")
    check(ingester._parse_gdelt_date("invalid") is None, "Invalid date → None", "Should return None")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 3. GDELT FETCH WITH MOCK ═══")
    # ═══════════════════════════════════════════════════════════════

    _ingester_cache.clear()

    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_GDELT_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.geo_risk.ingester.httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_client_instance

        articles = await ingester.fetch_gdelt("test query")
        check(len(articles) == 3, f"Fetched 3 articles from mock GDELT ({len(articles)})", f"Expected 3, got {len(articles)}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 4. RSS FETCH WITH MOCK ═══")
    # ═══════════════════════════════════════════════════════════════

    _ingester_cache.clear()

    mock_rss_response = MagicMock()
    mock_rss_response.text = MOCK_RSS_CONTENT
    mock_rss_response.raise_for_status = MagicMock()

    with patch("app.services.geo_risk.ingester.httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_rss_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_client_instance

        articles = await ingester.fetch_rss()
        check(len(articles) >= 2, f"Parsed >= 2 RSS articles ({len(articles)})", f"Expected >= 2, got {len(articles)}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 5. GDELT FAILURE HANDLING ═══")
    # ═══════════════════════════════════════════════════════════════

    _ingester_cache.clear()

    with patch("app.services.geo_risk.ingester.httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_client_instance

        articles = await ingester.fetch_gdelt("failing query")
        check(len(articles) == 0, "GDELT failure → empty list", f"Should return empty, got {len(articles)}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 6. CACHING ═══")
    # ═══════════════════════════════════════════════════════════════

    _ingester_cache.clear()

    # First call
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_GDELT_RESPONSE
    mock_response.raise_for_status = MagicMock()
    call_count = 0

    async def counting_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_response

    with patch("app.services.geo_risk.ingester.httpx.AsyncClient") as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = counting_get
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_client_instance

        await ingester.fetch_gdelt("cache test")
        await ingester.fetch_gdelt("cache test")  # Should hit cache
        check(call_count == 1, "Second call uses cache (1 HTTP request)", f"Expected 1 request, got {call_count}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 7. STATUS ═══")
    # ═══════════════════════════════════════════════════════════════

    status = ingester.get_status()
    check("rss_feeds_configured" in status, "Status has rss_feeds_configured", "Missing field")
    check("gdelt_url" in status, "Status has gdelt_url", "Missing field")
    check(status["rss_feeds_configured"] >= 1, f"At least 1 RSS feed configured", "No RSS feeds")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 8. TIMELINE TONE PARSING ═══")
    # ═══════════════════════════════════════════════════════════════

    timeline_data = {
        "timeline": [
            {
                "data": [
                    {"date": "20260401", "value": -3.5},
                    {"date": "20260402", "value": -1.2},
                ]
            }
        ]
    }
    tone_articles = ingester._parse_gdelt_response(timeline_data, "timelinetone")
    check(len(tone_articles) == 2, f"Parsed 2 timeline points ({len(tone_articles)})", f"Expected 2")


def main():
    asyncio.run(run_tests())

    print("\n" + "=" * 60)
    print(f"INGESTER TESTS: {PASSED}/{TOTAL} passed, {FAILED} failed")
    if FAILURES:
        print("\nFailures:")
        for f in FAILURES:
            print(f"  - {f}")
    print("=" * 60)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
