"""
Unit tests for GeoRiskScorer + AssetImpactScorer.

Tests impact matrix lookups, geographic amplification, recency decay math,
composite scoring, multi-event aggregation, and trust layer integration.

Run:  python test_geo_risk_scorer.py
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from datetime import datetime, timedelta
from app.services.geo_risk.scorer import AssetImpactScorer, GeoRiskScorer
from app.services.geo_risk.models import GeoEvent
from app.services.geo_risk.impact_matrix import IMPACT_MATRIX, get_impact, get_all_event_types, update_impact

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


def make_event(event_type="MILITARY_CONFLICT", severity=0.8, confidence=0.9,
               regions=None, hours_ago=0) -> GeoEvent:
    ts = datetime.utcnow() - timedelta(hours=hours_ago)
    return GeoEvent(
        event_id="test_" + event_type.lower()[:8],
        event_type=event_type,
        title=f"Test {event_type} event",
        description="Test event for scoring",
        source="test",
        confidence=confidence,
        severity=severity,
        regions=regions or [],
        timestamp=ts,
    )


def main():
    global TOTAL, PASSED, FAILED

    impact_scorer = AssetImpactScorer()
    risk_scorer = GeoRiskScorer()

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 1. IMPACT MATRIX COMPLETENESS ═══")
    # ═══════════════════════════════════════════════════════════════

    all_types = get_all_event_types()
    check(len(all_types) == 14, f"14 event types in matrix ({len(all_types)})", f"Expected 14, got {len(all_types)}")

    asset_classes = ["equities", "crypto", "commodities", "forex"]
    for event_type in all_types:
        for ac in asset_classes:
            impact = get_impact(event_type, ac)
            check(
                "direction" in impact and "magnitude" in impact,
                f"{event_type}/{ac} has direction+magnitude",
                f"{event_type}/{ac} missing fields",
            )

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 2. RECENCY DECAY MATH ═══")
    # ═══════════════════════════════════════════════════════════════

    # Acute event: half-life 24 hours
    event_fresh = make_event("MILITARY_CONFLICT", hours_ago=0)
    event_1day = make_event("MILITARY_CONFLICT", hours_ago=24)
    event_2days = make_event("MILITARY_CONFLICT", hours_ago=48)

    r_fresh = impact_scorer._recency_factor(event_fresh)
    r_1day = impact_scorer._recency_factor(event_1day)
    r_2days = impact_scorer._recency_factor(event_2days)

    check(abs(r_fresh - 1.0) < 0.05, f"Fresh event recency ≈ 1.0 ({r_fresh:.3f})", f"Fresh recency wrong: {r_fresh}")
    check(abs(r_1day - 0.5) < 0.05, f"1-day acute recency ≈ 0.5 ({r_1day:.3f})", f"1-day recency wrong: {r_1day}")
    check(r_2days < r_1day, f"2-day recency ({r_2days:.3f}) < 1-day ({r_1day:.3f})", "Decay not monotonic")

    # Structural event: half-life 7 days — should decay slower
    struct_1day = make_event("SANCTIONS", hours_ago=24)
    r_struct = impact_scorer._recency_factor(struct_1day)
    check(r_struct > r_1day, f"Structural 1-day ({r_struct:.3f}) > acute 1-day ({r_1day:.3f})", "Structural should decay slower")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 3. GEOGRAPHIC AMPLIFICATION ═══")
    # ═══════════════════════════════════════════════════════════════

    event_no_region = make_event("MILITARY_CONFLICT", regions=[])
    event_mideast = make_event("MILITARY_CONFLICT", regions=["middle_east"])

    score_no_region = impact_scorer.score_event(event_no_region, "commodities")
    score_mideast = impact_scorer.score_event(event_mideast, "commodities")

    check(
        score_mideast["geo_amplifier"] > score_no_region["geo_amplifier"],
        f"Middle East amplifies commodities ({score_mideast['geo_amplifier']} > {score_no_region['geo_amplifier']})",
        f"Geo amplification not working",
    )
    check(
        score_no_region["geo_amplifier"] == 1.0,
        "No region → amplifier = 1.0",
        f"No region amplifier should be 1.0, got {score_no_region['geo_amplifier']}",
    )

    # US-China should amplify equities
    event_uscn = make_event("TRADE_WAR", regions=["us_china"])
    score_uscn = impact_scorer.score_event(event_uscn, "equities")
    check(
        score_uscn["geo_amplifier"] > 1.0,
        f"US-China amplifies equities ({score_uscn['geo_amplifier']})",
        f"US-China equities amplifier should be > 1.0",
    )

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 4. SINGLE EVENT SCORING ═══")
    # ═══════════════════════════════════════════════════════════════

    # Bearish events should produce risk contribution
    event = make_event("MILITARY_CONFLICT", severity=0.8, confidence=0.9)
    result = impact_scorer.score_event(event, "equities")
    check(result["direction"] == "bearish", "Military conflict is bearish for equities", "Wrong direction")
    check(result["risk_contribution"] > 0, f"Risk contribution > 0 ({result['risk_contribution']:.3f})", "Should have risk contribution")
    check(result["opportunity_contribution"] == 0.0, "No opportunity from bearish event", "Bearish should have no opportunity")

    # Bullish events should produce opportunity contribution
    event_bull = make_event("MILITARY_CONFLICT", severity=0.8, confidence=0.9)
    result_bull = impact_scorer.score_event(event_bull, "crypto")
    check(result_bull["direction"] == "bullish", "Military conflict is bullish for crypto", "Wrong direction")
    check(result_bull["opportunity_contribution"] > 0, "Opportunity > 0 for bullish", "Should have opportunity")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 5. COMPOSITE ASSET SCORING ═══")
    # ═══════════════════════════════════════════════════════════════

    events = [
        make_event("MILITARY_CONFLICT", severity=0.8, confidence=0.9, regions=["middle_east"]),
        make_event("SANCTIONS", severity=0.7, confidence=0.8, regions=["russia"]),
        make_event("TRADE_WAR", severity=0.6, confidence=0.7, regions=["us_china"]),
    ]

    score = risk_scorer.score_asset("AAPL", "equities", events, data_freshness_minutes=5)
    check(score.geo_risk_score > 0, f"Composite risk > 0 ({score.geo_risk_score:.3f})", "Should have risk")
    check(0 <= score.geo_risk_score <= 1.0, "Risk score in [0, 1]", f"Risk score out of range: {score.geo_risk_score}")
    check(0 <= score.geo_opportunity_score <= 1.0, "Opportunity score in [0, 1]", f"Opp score out of range")
    check(score.signal_strength in ("weak", "moderate", "strong", "extreme"), f"Signal strength valid: {score.signal_strength}", "Invalid signal strength")
    check(score.recommended_action in ("hold", "hedge", "reduce_exposure", "increase_exposure"), f"Action valid: {score.recommended_action}", "Invalid action")
    check(0 < score.position_size_modifier <= 1.5, f"Position modifier valid: {score.position_size_modifier}", "Invalid modifier")
    check(len(score.dominant_events) > 0, f"Has dominant events ({len(score.dominant_events)})", "Should have dominant events")
    check(score.sources_analyzed == 3, f"Sources analyzed = 3", f"Expected 3 sources, got {score.sources_analyzed}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 6. NO-DATA EDGE CASE ═══")
    # ═══════════════════════════════════════════════════════════════

    empty_score = risk_scorer.score_asset("BTC/USDT", "crypto", [], data_freshness_minutes=0)
    check(empty_score.geo_risk_score == 0.0, "No events → risk = 0", f"Expected 0 risk, got {empty_score.geo_risk_score}")
    check(empty_score.geo_opportunity_score == 0.0, "No events → opportunity = 0", f"Expected 0 opp")
    check(empty_score.recommended_action == "hold", "No events → hold", f"Expected hold, got {empty_score.recommended_action}")
    check(empty_score.position_size_modifier == 1.0, "No events → size mod = 1.0", f"Expected 1.0 modifier")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 7. STALE DATA ═══")
    # ═══════════════════════════════════════════════════════════════

    old_events = [make_event("MILITARY_CONFLICT", hours_ago=72)]
    fresh_events = [make_event("MILITARY_CONFLICT", hours_ago=0)]
    score_old = risk_scorer.score_asset("BTC", "crypto", old_events)
    score_fresh = risk_scorer.score_asset("BTC", "crypto", fresh_events)
    check(
        score_fresh.geo_risk_score >= score_old.geo_risk_score,
        f"Fresh events have more impact ({score_fresh.geo_risk_score:.3f} >= {score_old.geo_risk_score:.3f})",
        "Fresh events should have more impact than stale",
    )

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 8. NEWS RISK LEVEL (Trust Layer Integration) ═══")
    # ═══════════════════════════════════════════════════════════════

    check(risk_scorer.get_news_risk_level([], "crypto") == "none", "No events → none", "Should be none")

    mild = [make_event("ELECTION", severity=0.3, confidence=0.4)]
    level = risk_scorer.get_news_risk_level(mild, "equities")
    check(level in ("none", "low"), f"Mild event → {level}", f"Mild event risk too high: {level}")

    severe = [
        make_event("MILITARY_CONFLICT", severity=0.9, confidence=0.95, regions=["middle_east"]),
        make_event("ENERGY_CRISIS", severity=0.85, confidence=0.9, regions=["russia"]),
        make_event("SANCTIONS", severity=0.8, confidence=0.85),
    ]
    # Equities get bearish direction from all three event types → higher risk
    level_severe = risk_scorer.get_news_risk_level(severe, "equities")
    check(level_severe in ("medium", "high"), f"Severe events (equities) → {level_severe}", f"Severe events risk too low: {level_severe}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 9. MULTI-ASSET SCORING ═══")
    # ═══════════════════════════════════════════════════════════════

    assets = {"BTC/USDT": "crypto", "AAPL": "equities", "GOLD": "commodities", "EUR/USD": "forex"}
    events = [make_event("MILITARY_CONFLICT", severity=0.8, confidence=0.9, regions=["middle_east"])]
    all_scores = risk_scorer.score_all_assets(assets, events)
    check(len(all_scores) == 4, f"Scored 4 assets ({len(all_scores)})", f"Expected 4, got {len(all_scores)}")
    for symbol, s in all_scores.items():
        check(s.asset == symbol, f"{symbol} score has correct asset", f"Wrong asset in score")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 10. IMPACT MATRIX OPERATIONS ═══")
    # ═══════════════════════════════════════════════════════════════

    # Update
    ok = update_impact("SANCTIONS", "crypto", {"magnitude": 0.99})
    check(ok, "Impact matrix update succeeded", "Update should succeed")
    updated = get_impact("SANCTIONS", "crypto")
    check(updated.get("magnitude") == 0.99, "Updated magnitude = 0.99", f"Got {updated.get('magnitude')}")
    # Restore
    update_impact("SANCTIONS", "crypto", {"magnitude": 0.4})

    # Unknown type
    ok = update_impact("NONEXISTENT", "crypto", {"magnitude": 0.5})
    check(not ok, "Unknown event type returns False", "Should fail for unknown type")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 11. CONFLICTING SIGNALS ═══")
    # ═══════════════════════════════════════════════════════════════

    # Military conflict: bearish equities but bullish crypto
    events = [make_event("MILITARY_CONFLICT", severity=0.8, confidence=0.9)]
    eq_score = risk_scorer.score_asset("SPY", "equities", events)
    cr_score = risk_scorer.score_asset("BTC", "crypto", events)
    check(
        eq_score.geo_risk_score > cr_score.geo_risk_score,
        f"Military conflict: equities risk ({eq_score.geo_risk_score:.3f}) > crypto risk ({cr_score.geo_risk_score:.3f})",
        "Equities should have higher risk from military conflict",
    )

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print(f"SCORER TESTS: {PASSED}/{TOTAL} passed, {FAILED} failed")
    if FAILURES:
        print("\nFailures:")
        for f in FAILURES:
            print(f"  - {f}")
    print("=" * 60)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
