"""
Impact Matrix — maps geopolitical event types to asset class impacts.

Based on academic GPR literature (Caldara & Iacoviello 2022, Bossman et al. 2023).
Each event type has a pre-defined impact profile per asset class with direction
(bullish/bearish/neutral/varies) and magnitude (0.0–1.0).
"""
from typing import Dict, Any

# ── Full Impact Matrix ───────────────────────────────────────────────────────

IMPACT_MATRIX: Dict[str, Dict[str, Any]] = {
    "MILITARY_CONFLICT": {
        "equities": {
            "direction": "bearish", "magnitude": 0.8,
            "sectors": {"defense": "bullish", "tech": "bearish", "energy": "bullish", "travel": "bearish"},
        },
        "crypto": {
            "direction": "bullish", "magnitude": 0.5,
            "note": "flight to decentralized assets",
        },
        "commodities": {
            "direction": "bullish", "magnitude": 0.9,
            "sub": {"gold": 0.95, "oil": 0.9, "agriculture": 0.6, "silver": 0.7},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.7,
            "safe_havens": ["USD", "CHF", "JPY"],
            "risk_currencies": ["AUD", "NZD", "ZAR"],
        },
    },
    "TERRORISM": {
        "equities": {
            "direction": "bearish", "magnitude": 0.6,
            "sectors": {"defense": "bullish", "travel": "bearish", "insurance": "bearish"},
        },
        "crypto": {"direction": "neutral", "magnitude": 0.3},
        "commodities": {
            "direction": "bullish", "magnitude": 0.5,
            "sub": {"gold": 0.7, "oil": 0.5, "agriculture": 0.2},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.4,
            "safe_havens": ["USD", "CHF", "JPY"],
            "risk_currencies": ["TRY", "ZAR"],
        },
    },
    "SANCTIONS": {
        "equities": {
            "direction": "bearish", "magnitude": 0.6,
            "sectors": {"financials": "bearish", "energy": "varies", "defense": "neutral"},
        },
        "crypto": {
            "direction": "bullish", "magnitude": 0.4,
            "note": "sanctions evasion narrative",
        },
        "commodities": {
            "direction": "bullish", "magnitude": 0.7,
            "sub": {"oil": 0.8, "gas": 0.8, "metals": 0.5, "gold": 0.6},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.6,
            "safe_havens": ["USD", "CHF"],
            "risk_currencies": ["RUB", "IRR"],
        },
    },
    "TRADE_WAR": {
        "equities": {
            "direction": "bearish", "magnitude": 0.7,
            "sectors": {"manufacturing": "bearish", "domestic": "bullish", "tech": "bearish"},
        },
        "crypto": {"direction": "neutral", "magnitude": 0.3},
        "commodities": {
            "direction": "varies", "magnitude": 0.6,
            "sub": {"agriculture": 0.8, "metals": 0.7, "oil": 0.4},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.8,
            "safe_havens": ["USD", "JPY"],
            "risk_currencies": ["CNY", "MXN", "KRW"],
        },
    },
    "ELECTION": {
        "equities": {
            "direction": "varies", "magnitude": 0.5,
            "sectors": {"healthcare": "varies", "energy": "varies", "financials": "varies"},
        },
        "crypto": {"direction": "neutral", "magnitude": 0.2},
        "commodities": {
            "direction": "neutral", "magnitude": 0.3,
            "sub": {"gold": 0.4, "oil": 0.3},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.5,
            "safe_havens": [],
            "risk_currencies": [],
        },
    },
    "CIVIL_UNREST": {
        "equities": {
            "direction": "bearish", "magnitude": 0.5,
            "sectors": {"retail": "bearish", "real_estate": "bearish"},
        },
        "crypto": {"direction": "bullish", "magnitude": 0.3},
        "commodities": {
            "direction": "neutral", "magnitude": 0.3,
            "sub": {"gold": 0.4, "agriculture": 0.3},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.4,
            "safe_havens": ["USD", "CHF"],
            "risk_currencies": [],
        },
    },
    "DIPLOMATIC_CRISIS": {
        "equities": {
            "direction": "bearish", "magnitude": 0.4,
            "sectors": {"defense": "bullish", "trade": "bearish"},
        },
        "crypto": {"direction": "neutral", "magnitude": 0.2},
        "commodities": {
            "direction": "bullish", "magnitude": 0.4,
            "sub": {"gold": 0.5, "oil": 0.4},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.5,
            "safe_havens": ["USD", "CHF", "JPY"],
            "risk_currencies": [],
        },
    },
    "NATURAL_DISASTER": {
        "equities": {
            "direction": "bearish", "magnitude": 0.5,
            "sectors": {"insurance": "bearish", "construction": "bullish", "reinsurance": "bearish"},
        },
        "crypto": {"direction": "neutral", "magnitude": 0.1},
        "commodities": {
            "direction": "bullish", "magnitude": 0.6,
            "sub": {"agriculture": 0.8, "oil": 0.5, "lumber": 0.7},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.3,
            "safe_havens": [],
            "risk_currencies": [],
        },
    },
    "REGULATORY_CHANGE": {
        "equities": {
            "direction": "varies", "magnitude": 0.6,
            "sectors": {"tech": "varies", "financials": "varies", "crypto_related": "bearish"},
        },
        "crypto": {
            "direction": "bearish", "magnitude": 0.7,
            "note": "crypto regulation typically bearish short-term",
        },
        "commodities": {
            "direction": "neutral", "magnitude": 0.2,
            "sub": {"gold": 0.2},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.4,
            "safe_havens": [],
            "risk_currencies": [],
        },
    },
    "ENERGY_CRISIS": {
        "equities": {
            "direction": "bearish", "magnitude": 0.7,
            "sectors": {"energy": "bullish", "utilities": "bearish", "manufacturing": "bearish"},
        },
        "crypto": {
            "direction": "bearish", "magnitude": 0.4,
            "note": "mining cost pressure",
        },
        "commodities": {
            "direction": "bullish", "magnitude": 0.9,
            "sub": {"oil": 0.95, "gas": 0.95, "coal": 0.8, "uranium": 0.6},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.6,
            "safe_havens": ["USD", "NOK", "CAD"],
            "risk_currencies": ["EUR", "JPY"],
        },
    },
    "CYBER_ATTACK": {
        "equities": {
            "direction": "bearish", "magnitude": 0.5,
            "sectors": {"cybersecurity": "bullish", "tech": "varies", "financials": "bearish"},
        },
        "crypto": {
            "direction": "bearish", "magnitude": 0.6,
            "note": "exchange hacks erode confidence",
        },
        "commodities": {
            "direction": "neutral", "magnitude": 0.2,
            "sub": {"gold": 0.3},
        },
        "forex": {
            "direction": "neutral", "magnitude": 0.2,
            "safe_havens": [],
            "risk_currencies": [],
        },
    },
    "REPUTATION_EVENT": {
        "equities": {
            "direction": "bearish", "magnitude": 0.6,
            "sectors": {"affected_company": "bearish", "competitors": "bullish"},
        },
        "crypto": {
            "direction": "bearish", "magnitude": 0.5,
            "note": "project-specific; can be severe for individual tokens",
        },
        "commodities": {
            "direction": "neutral", "magnitude": 0.1,
            "sub": {},
        },
        "forex": {
            "direction": "neutral", "magnitude": 0.1,
            "safe_havens": [],
            "risk_currencies": [],
        },
    },
    "COMMODITY_DISRUPTION": {
        "equities": {
            "direction": "varies", "magnitude": 0.5,
            "sectors": {"mining": "bullish", "manufacturing": "bearish", "energy": "bullish"},
        },
        "crypto": {"direction": "neutral", "magnitude": 0.2},
        "commodities": {
            "direction": "bullish", "magnitude": 0.85,
            "sub": {"oil": 0.8, "metals": 0.8, "agriculture": 0.7, "gold": 0.5},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.4,
            "safe_havens": ["AUD", "CAD", "NOK"],
            "risk_currencies": [],
        },
    },
    "CURRENCY_CRISIS": {
        "equities": {
            "direction": "bearish", "magnitude": 0.7,
            "sectors": {"financials": "bearish", "exporters": "bullish"},
        },
        "crypto": {
            "direction": "bullish", "magnitude": 0.7,
            "note": "fiat devaluation drives crypto adoption narrative",
        },
        "commodities": {
            "direction": "bullish", "magnitude": 0.6,
            "sub": {"gold": 0.8, "silver": 0.6},
        },
        "forex": {
            "direction": "varies", "magnitude": 0.9,
            "safe_havens": ["USD", "CHF", "JPY"],
            "risk_currencies": ["ARS", "TRY", "ZAR", "NGN"],
        },
    },
}


def get_impact(event_type: str, asset_class: str) -> Dict[str, Any]:
    """Look up impact profile for an event type and asset class."""
    event_impacts = IMPACT_MATRIX.get(event_type, {})
    return event_impacts.get(asset_class, {
        "direction": "neutral",
        "magnitude": 0.0,
    })


def get_all_event_types() -> list:
    """Return sorted list of all event types in the matrix."""
    return sorted(IMPACT_MATRIX.keys())


def update_impact(event_type: str, asset_class: str, updates: Dict[str, Any]) -> bool:
    """Update a specific cell in the impact matrix at runtime."""
    if event_type not in IMPACT_MATRIX:
        return False
    if asset_class not in IMPACT_MATRIX[event_type]:
        IMPACT_MATRIX[event_type][asset_class] = {}
    IMPACT_MATRIX[event_type][asset_class].update(updates)
    return True
