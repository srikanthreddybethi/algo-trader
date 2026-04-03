"""
Integration tests for the full Geopolitical Risk pipeline.

Tests the complete flow: news → classification → scoring → trust layer,
plus API endpoint coverage against a running backend.

Run:  python test_geo_risk_integration.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from typing import Any, List, Optional
import httpx

BASE = "http://localhost:8000"
TOTAL = 0
PASSED = 0
FAILED = 0
FAILURES: List[str] = []


async def api(
    method: str, path: str, json_data: Any = None,
    expect_fail: bool = False, label: str = "", timeout: int = 30,
) -> Optional[Any]:
    global TOTAL, PASSED, FAILED
    TOTAL += 1
    tag = label or f"{method} {path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                r = await client.get(f"{BASE}{path}")
            elif method == "POST":
                r = await client.post(f"{BASE}{path}", json=json_data)
            elif method == "PUT":
                r = await client.put(f"{BASE}{path}", json=json_data)
            elif method == "DELETE":
                r = await client.delete(f"{BASE}{path}")
            else:
                raise ValueError(f"Unknown method: {method}")
            if r.status_code >= 500:
                FAILED += 1
                FAILURES.append(f"500: {tag}")
                print(f"  ✗ {tag} → {r.status_code}")
                return None
            PASSED += 1
            ct = r.headers.get("content-type", "")
            data = r.json() if "json" in ct else r.text
            print(f"  ✓ {tag} → {r.status_code}")
            return data
    except Exception as e:
        FAILED += 1
        FAILURES.append(f"EXC: {tag} → {e}")
        print(f"  ✗ {tag} → {e}")
        return None


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


async def run_tests():
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 1. UNIT: Full Pipeline (classify → score) ═══")
    # ═══════════════════════════════════════════════════════════════

    from app.services.geo_risk.classifier import GeoEventClassifier
    from app.services.geo_risk.scorer import GeoRiskScorer, AssetImpactScorer
    from app.services.geo_risk.monitor import GeoMonitor
    from app.services.geo_risk.impact_matrix import IMPACT_MATRIX

    classifier = GeoEventClassifier()
    scorer = GeoRiskScorer()

    # Simulate articles
    articles = [
        {"title": "Russia launches major military operation with airstrikes and bombing in Ukraine war", "source": "test"},
        {"title": "US Treasury announces new sanctions and SWIFT ban on Russian financial institutions", "source": "test"},
        {"title": "China retaliates with tariffs in escalating trade war and protectionism dispute", "source": "test"},
        {"title": "Major earthquake and tsunami devastate Japan coastal region in natural disaster", "source": "test"},
        {"title": "OPEC announces oil production cut triggering energy crisis fears", "source": "test"},
    ]

    events = classifier.classify_batch(articles)
    check(len(events) == 5, f"5 articles classified ({len(events)})", f"Expected 5, got {len(events)}")

    # Score multiple assets
    assets = {"BTC/USDT": "crypto", "AAPL": "equities", "GOLD": "commodities", "EUR/USD": "forex"}
    all_scores = scorer.score_all_assets(assets, events, data_freshness_minutes=5)
    check(len(all_scores) == 4, f"4 assets scored", f"Expected 4 scores, got {len(all_scores)}")

    for symbol, score in all_scores.items():
        check(0 <= score.geo_risk_score <= 1.0, f"{symbol} risk in [0,1]: {score.geo_risk_score:.3f}", f"{symbol} risk out of range")
        check(score.recommended_action != "", f"{symbol} has action: {score.recommended_action}", f"{symbol} missing action")
        check(score.confidence > 0, f"{symbol} confidence > 0: {score.confidence:.3f}", f"{symbol} no confidence")

    # Trust layer integration
    news_risk = scorer.get_news_risk_level(events, "equities")
    check(news_risk in ("none", "low", "medium", "high"), f"News risk level valid: {news_risk}", f"Invalid: {news_risk}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 2. UNIT: GeoMonitor Pipeline ═══")
    # ═══════════════════════════════════════════════════════════════

    monitor = GeoMonitor()

    # Manual evaluation
    event = monitor.evaluate_event(
        "Iran launches missile strikes amid military conflict and war escalation",
        "Major escalation in Middle East military operations"
    )
    check(event is not None, "Monitor evaluate_event works", "Evaluation failed")
    if event:
        check(event.event_type == "MILITARY_CONFLICT", f"Classified as {event.event_type}", "Wrong type")
        check("middle_east" in event.regions, f"Detected middle_east region", f"Region missing: {event.regions}")

    # Score after evaluation
    score = monitor.score_asset("GOLD", "commodities")
    check(score is not None, "Score available after evaluation", "Score failed")

    # Timeline
    timeline = monitor.get_risk_timeline("equities", hours=168)
    check(isinstance(timeline, list), "Timeline returns list", "Timeline wrong type")

    # Heatmap
    heatmap = monitor.get_heatmap()
    check(isinstance(heatmap, list), "Heatmap returns list", "Heatmap wrong type")

    # Alerts
    alert = monitor.create_alert(
        asset_class="crypto",
        event_types=["SANCTIONS"],
        threshold=0.7,
        description="Test alert"
    )
    check(alert.alert_id != "", "Alert created with ID", "Alert has no ID")
    check(len(monitor.get_alerts()) >= 1, "Alerts list has entries", "No alerts")

    # Analytics
    analytics = monitor.get_analytics()
    check("total_active_events" in analytics, "Analytics has total_active_events", "Missing field")
    check("events_by_type" in analytics, "Analytics has events_by_type", "Missing field")
    check("ingester_status" in analytics, "Analytics has ingester_status", "Missing field")

    # Status
    status = monitor.get_status()
    check("total_events" in status, "Status has total_events", "Missing field")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 3. API: Geo Risk Endpoints ═══")
    # ═══════════════════════════════════════════════════════════════

    # Status
    data = await api("GET", "/api/v1/geo-risk/status", label="Geo risk status")
    if data:
        check("total_events" in data, "Status response has total_events", "Missing field")

    # Analytics
    data = await api("GET", "/api/v1/geo-risk/analytics", label="Geo risk analytics")
    if data:
        check("total_active_events" in data, "Analytics has total_active_events", "Missing field")

    # Events list
    data = await api("GET", "/api/v1/geo-risk/events", label="List events")
    check(isinstance(data, list), "Events returns list", f"Expected list, got {type(data)}")

    # Manual evaluation
    data = await api("POST", "/api/v1/geo-risk/evaluate", json_data={
        "title": "US imposes new economic sanctions and embargo on Iran nuclear program",
        "description": "Treasury department blacklists financial institutions with SWIFT ban"
    }, label="Evaluate event")
    if data:
        check(data.get("classified") == True, "Event classified successfully", "Classification failed")
        if data.get("event"):
            check(data["event"]["event_type"] == "SANCTIONS", f"Type: {data['event']['event_type']}", "Wrong type")

    # Score single asset
    data = await api("GET", "/api/v1/geo-risk/score/BTC%2FUSDT?asset_class=crypto", label="Score BTC")
    if data:
        check("geo_risk_score" in data, "Score has geo_risk_score", "Missing field")
        check("recommended_action" in data, "Score has recommended_action", "Missing field")

    # Score all assets
    data = await api("GET", "/api/v1/geo-risk/scores?asset_class=crypto", label="Score all crypto")
    if data:
        check(isinstance(data, dict), "Scores returns dict", "Wrong type")

    # Timeline
    data = await api("GET", "/api/v1/geo-risk/timeline?hours=168", label="Risk timeline")
    check(isinstance(data, list), "Timeline returns list", "Wrong type")

    # Heatmap
    data = await api("GET", "/api/v1/geo-risk/heatmap", label="Risk heatmap")
    check(isinstance(data, list), "Heatmap returns list", "Wrong type")

    # Impact matrix
    data = await api("GET", "/api/v1/geo-risk/impact-matrix", label="Impact matrix")
    if data:
        check("event_types" in data, "Matrix has event_types", "Missing field")
        check("matrix" in data, "Matrix has matrix data", "Missing field")
        check(len(data.get("event_types", [])) == 14, f"14 event types ({len(data.get('event_types', []))})", "Wrong count")

    # Update impact matrix
    data = await api("PUT", "/api/v1/geo-risk/impact-matrix", json_data={
        "event_type": "SANCTIONS",
        "asset_class": "crypto",
        "updates": {"magnitude": 0.45}
    }, label="Update impact matrix")
    if data:
        check(data.get("updated") == True, "Matrix update succeeded", "Update failed")

    # Alerts
    data = await api("GET", "/api/v1/geo-risk/alerts", label="Get alerts")
    check(isinstance(data, list), "Alerts returns list", "Wrong type")

    data = await api("POST", "/api/v1/geo-risk/alerts", json_data={
        "asset_class": "equities",
        "event_types": ["MILITARY_CONFLICT", "SANCTIONS"],
        "threshold": 0.75,
        "description": "Alert for high-risk military/sanctions events"
    }, label="Create alert")
    if data:
        check("alert_id" in data, "Alert has alert_id", "Missing alert_id")

    # Event detail (with the event we evaluated earlier)
    events_data = await api("GET", "/api/v1/geo-risk/events?limit=1", label="Get latest event for detail")
    if events_data and len(events_data) > 0:
        eid = events_data[0]["event_id"]
        detail = await api("GET", f"/api/v1/geo-risk/events/{eid}", label=f"Event detail {eid}")
        if detail:
            check("impact_breakdown" in detail, "Detail has impact_breakdown", "Missing impact_breakdown")
            check("equities" in detail.get("impact_breakdown", {}), "Breakdown has equities", "Missing equities")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 4. API: Validation / Error Handling ═══")
    # ═══════════════════════════════════════════════════════════════

    # Empty title
    data = await api("POST", "/api/v1/geo-risk/evaluate", json_data={"title": ""}, label="Empty title → 400", expect_fail=True)

    # Nonexistent event
    data = await api("GET", "/api/v1/geo-risk/events/nonexistent123", label="Nonexistent event → 404", expect_fail=True)

    # Invalid matrix update
    data = await api("PUT", "/api/v1/geo-risk/impact-matrix", json_data={"event_type": "FAKE"}, label="Invalid matrix update", expect_fail=True)

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 5. API: Trust Score Integration ═══")
    # ═══════════════════════════════════════════════════════════════

    data = await api("GET", "/api/trust-score/evaluate?symbol=BTC/USDT&direction=buy&exchange=binance",
                     label="Trust score with geo risk integration")
    if data:
        check("trust_score" in data, "Trust score returned", "Missing trust_score")
        check("components" in data, "Components returned", "Missing components")
        if "components" in data:
            check("news_safety" in data["components"], "news_safety component present", "Missing news_safety")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 6. UNIT: All 14 Event Types Sample Articles ═══")
    # ═══════════════════════════════════════════════════════════════

    sample_articles = [
        {"title": "Military airstrike and bombing raids escalate war conflict", "expected": "MILITARY_CONFLICT"},
        {"title": "Terrorist suicide bomber attacks crowded market in terror attack", "expected": "TERRORISM"},
        {"title": "Treasury imposes economic sanctions and asset freeze embargo", "expected": "SANCTIONS"},
        {"title": "New tariffs imposed as trade war tariff protectionism escalates", "expected": "TRADE_WAR"},
        {"title": "Presidential election and referendum voters head to polls", "expected": "ELECTION"},
        {"title": "Riots and protests erupt in civil unrest with martial law", "expected": "CIVIL_UNREST"},
        {"title": "Ambassador recall marks diplomatic crisis as embassy closes", "expected": "DIPLOMATIC_CRISIS"},
        {"title": "Earthquake tsunami flood devastate region in natural disaster", "expected": "NATURAL_DISASTER"},
        {"title": "Central bank rate hike regulatory crackdown new regulation", "expected": "REGULATORY_CHANGE"},
        {"title": "Oil supply pipeline attack causes energy crisis power outage", "expected": "ENERGY_CRISIS"},
        {"title": "Ransomware cyber attack targets critical infrastructure systems", "expected": "CYBER_ATTACK"},
        {"title": "CEO resigns amid scandal fraud whistleblower insider trading", "expected": "REPUTATION_EVENT"},
        {"title": "Mining strike port closure cause supply disruption production cut", "expected": "COMMODITY_DISRUPTION"},
        {"title": "Currency collapse hyperinflation capital controls debt default", "expected": "CURRENCY_CRISIS"},
    ]

    for article in sample_articles:
        event = classifier.classify(article["title"])
        check(
            event is not None and event.event_type == article["expected"],
            f"Sample: {article['expected']} ✓",
            f"Sample: expected {article['expected']}, got {event.event_type if event else 'None'}",
        )


def main():
    asyncio.run(run_tests())

    print("\n" + "=" * 60)
    print(f"GEO RISK INTEGRATION TESTS: {PASSED}/{TOTAL} passed, {FAILED} failed")
    if FAILURES:
        print("\nFailures:")
        for f in FAILURES:
            print(f"  - {f}")
    print("=" * 60)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
