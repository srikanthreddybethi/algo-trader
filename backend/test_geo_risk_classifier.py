"""
Unit tests for GeoEventClassifier — keyword-based event classification.

Tests all 14 event types, multi-label classification, region detection,
severity calculation, edge cases, and batch classification.

Run:  python test_geo_risk_classifier.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from datetime import datetime
from app.services.geo_risk.classifier import GeoEventClassifier, KEYWORD_DICTIONARIES

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


def main():
    global TOTAL, PASSED, FAILED

    classifier = GeoEventClassifier()

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 1. ALL 14 EVENT TYPES — Classification ═══")
    # ═══════════════════════════════════════════════════════════════

    test_cases = {
        "MILITARY_CONFLICT": "Russia launches major military operation with airstrikes and troops in eastern Ukraine war zone",
        "TERRORISM": "ISIS claims responsibility for suicide bomber terrorist attack in capital city",
        "SANCTIONS": "US Treasury imposes sweeping economic sanctions and SWIFT ban on Russian financial institutions",
        "TRADE_WAR": "China retaliates with new tariffs on US imports in escalating trade war and trade dispute",
        "ELECTION": "Presidential election results contested as opposition claims electoral fraud in the referendum",
        "CIVIL_UNREST": "Mass protests and riots erupt across major cities with martial law declared amid civil unrest",
        "DIPLOMATIC_CRISIS": "Ambassador recall and embassy closure mark deepening diplomatic crisis and severed relations",
        "NATURAL_DISASTER": "Massive earthquake and tsunami devastate coastal regions in natural disaster emergency",
        "REGULATORY_CHANGE": "Federal Reserve announces surprise rate hike in major monetary policy regulatory crackdown",
        "ENERGY_CRISIS": "OPEC announces major oil production cut triggering energy crisis fears and pipeline attack concerns",
        "CYBER_ATTACK": "Nation-state ransomware cyber attack targets critical infrastructure and financial systems",
        "REPUTATION_EVENT": "CEO resigns amid accounting fraud scandal and whistleblower allegations of insider trading",
        "COMMODITY_DISRUPTION": "Mining strike and port closure cause severe supply disruption and production cut in chip shortage",
        "CURRENCY_CRISIS": "Currency collapse and hyperinflation force capital controls as sovereign default looms with IMF bailout",
    }

    for expected_type, headline in test_cases.items():
        event = classifier.classify(headline)
        check(
            event is not None and event.event_type == expected_type,
            f"{expected_type} classified correctly",
            f"{expected_type} misclassified as {event.event_type if event else 'None'}: {headline[:60]}",
        )
        if event:
            check(
                0 < event.confidence <= 1.0,
                f"{expected_type} confidence {event.confidence:.2f} in range",
                f"{expected_type} confidence {event.confidence:.2f} out of range",
            )

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 2. MULTI-LABEL CLASSIFICATION ═══")
    # ═══════════════════════════════════════════════════════════════

    multi_label_text = "New economic sanctions and embargo imposed amid trade war tariffs and retaliatory tariff trade dispute protectionism"
    event = classifier.classify(multi_label_text)
    check(event is not None, "Multi-label event classified", "Multi-label event not classified")
    if event:
        all_types = [event.event_type] + event.secondary_types
        check(
            "SANCTIONS" in all_types and "TRADE_WAR" in all_types,
            f"Multi-label: SANCTIONS + TRADE_WAR detected ({all_types})",
            f"Multi-label missed: got {all_types}",
        )

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 3. REGION DETECTION ═══")
    # ═══════════════════════════════════════════════════════════════

    region_tests = [
        ("Military war airstrike bombing conflict escalates in Syria as Iran backs militia in middle east", "middle_east"),
        ("Beijing Washington economic sanctions embargo trade war tariffs Taiwan US-China retaliatory tariff protectionism trade dispute", "us_china"),
        ("European Union Brussels ECB eurozone regulatory crackdown rate hike new regulation monetary policy", "europe"),
        ("Russia Moscow Kremlin Putin military troops war airstrike escalates Ukraine conflict Kyiv", "russia"),
        ("Japan South Korea tariffs trade war protectionism retaliatory duty in Asia-Pacific region", "asia_pacific"),
    ]

    for text, expected_region in region_tests:
        event = classifier.classify(text)
        if event:
            check(
                expected_region in event.regions,
                f"Region '{expected_region}' detected in: {text[:50]}...",
                f"Region '{expected_region}' NOT detected, got: {event.regions}",
            )
        else:
            check(False, "", f"Event not classified for region test: {text[:50]}")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 4. SEVERITY CALCULATION ═══")
    # ═══════════════════════════════════════════════════════════════

    # Negative tone should increase severity
    event_neg = classifier.classify("Major military war airstrike bombing", tone_score=-20)
    event_pos = classifier.classify("Major military war airstrike bombing", tone_score=10)
    if event_neg and event_pos:
        check(
            event_neg.severity > event_pos.severity,
            f"Negative tone ({event_neg.severity:.2f}) > positive tone ({event_pos.severity:.2f})",
            f"Tone severity not working: neg={event_neg.severity:.2f}, pos={event_pos.severity:.2f}",
        )

    # High article count should increase severity
    event_low = classifier.classify("Major military war airstrike", article_count=1)
    event_high = classifier.classify("Major military war airstrike", article_count=200)
    if event_low and event_high:
        check(
            event_high.severity > event_low.severity,
            f"High article count ({event_high.severity:.2f}) > low ({event_low.severity:.2f})",
            f"Article count severity not working",
        )

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 5. EDGE CASES ═══")
    # ═══════════════════════════════════════════════════════════════

    # Empty input
    check(classifier.classify("") is None, "Empty string returns None", "Empty string should return None")
    check(classifier.classify("   ") is None, "Whitespace returns None", "Whitespace should return None")

    # Unrelated text
    result = classifier.classify("The weather today is sunny and warm with clear skies")
    check(result is None, "Unrelated text returns None", f"Unrelated text classified as: {result.event_type if result else 'None'}")

    # Very short text — single keyword alone doesn't meet confidence threshold
    result = classifier.classify("war")
    check(result is None, "Single keyword 'war' below threshold", "Single 'war' should be below threshold")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 6. BATCH CLASSIFICATION ═══")
    # ═══════════════════════════════════════════════════════════════

    articles = [
        {"title": "Military conflict war escalates with airstrikes and bombing troops invasion", "source": "test"},
        {"title": "New economic sanctions imposed embargo SWIFT ban asset freeze Russian banks", "source": "test"},
        {"title": "Weather is nice today", "source": "test"},  # Should be filtered
        {"title": "Earthquake tsunami flood devastate coastal region in natural disaster emergency", "source": "test"},
    ]
    batch_results = classifier.classify_batch(articles)
    check(
        len(batch_results) == 3,
        f"Batch: 3 of 4 classified (filtered 1 unrelated)",
        f"Batch: expected 3, got {len(batch_results)}",
    )

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 7. EVENT ID GENERATION ═══")
    # ═══════════════════════════════════════════════════════════════

    e1 = classifier.classify("War military conflict airstrike", source="test1")
    e2 = classifier.classify("War military conflict airstrike", source="test1")
    e3 = classifier.classify("War military conflict airstrike", source="test2")
    if e1 and e2 and e3:
        check(e1.event_id == e2.event_id, "Same input → same event_id", "IDs should match for same input")
        check(e1.event_id != e3.event_id, "Different source → different event_id", "IDs should differ for different sources")

    # ═══════════════════════════════════════════════════════════════
    print("\n═══ 8. KEYWORD DICTIONARY COVERAGE ═══")
    # ═══════════════════════════════════════════════════════════════

    all_types = classifier.get_all_event_types()
    check(len(all_types) == 14, f"14 event types defined ({len(all_types)})", f"Expected 14 types, got {len(all_types)}")

    for event_type in all_types:
        kw_dict = classifier.get_keyword_dict(event_type)
        check(len(kw_dict) >= 10, f"{event_type}: {len(kw_dict)} keywords", f"{event_type}: only {len(kw_dict)} keywords (need >= 10)")

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print(f"CLASSIFIER TESTS: {PASSED}/{TOTAL} passed, {FAILED} failed")
    if FAILURES:
        print("\nFailures:")
        for f in FAILURES:
            print(f"  - {f}")
    print("=" * 60)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
