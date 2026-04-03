"""
Geopolitical Risk configuration — all weights, thresholds, and parameters.

Every tunable value lives here so behaviour can be changed without touching
logic code.
"""

GEO_RISK_CONFIG = {
    # ── Polling intervals ────────────────────────────────────────────────
    "gdelt_poll_interval_minutes": 15,
    "rss_poll_interval_minutes": 5,

    # ── Recency decay half-lives (hours) ─────────────────────────────────
    "event_half_life_hours": {
        "acute": 24,       # wars, terrorism, cyber attacks
        "structural": 168,  # 7 days — sanctions, regulatory change, trade war
    },

    # ── Risk thresholds ──────────────────────────────────────────────────
    "risk_thresholds": {
        "low": 0.3,
        "moderate": 0.5,
        "high": 0.7,
        "extreme": 0.85,
    },

    # ── Trust layer integration ──────────────────────────────────────────
    "trust_layer_weight": 0.10,
    "high_risk_trade_block_threshold": 0.8,
    "opportunity_boost_threshold": 0.7,

    # ── Event management ─────────────────────────────────────────────────
    "max_events_tracked": 500,
    "min_confidence_threshold": 0.3,
    "event_window_days": 30,

    # ── GDELT query settings ─────────────────────────────────────────────
    "gdelt_max_records": 250,
    "gdelt_source_lang": "English",
    "gdelt_base_url": "https://api.gdeltproject.org/api/v2/doc/doc",

    # ── RSS feed sources ─────────────────────────────────────────────────
    "rss_feeds": [
        {"name": "Reuters World", "url": "https://feeds.reuters.com/Reuters/worldNews"},
        {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    ],

    # ── Geographic amplifiers ────────────────────────────────────────────
    "geographic_amplifiers": {
        "middle_east": {
            "regions": ["middle east", "iran", "iraq", "syria", "yemen", "saudi",
                        "israel", "palestine", "gaza", "lebanon", "qatar", "uae",
                        "bahrain", "oman", "kuwait", "jordan"],
            "amplifiers": {
                "commodities_oil": 1.5,
                "commodities_gold": 1.3,
                "commodities_gas": 1.4,
                "energy": 1.5,
            },
        },
        "us_china": {
            "regions": ["united states", "china", "beijing", "washington",
                        "taiwan", "us-china", "sino-american"],
            "amplifiers": {
                "equities": 1.4,
                "forex": 1.5,
                "commodities_agriculture": 1.6,
                "commodities_metals": 1.4,
                "crypto": 1.2,
            },
        },
        "europe": {
            "regions": ["europe", "eu", "european union", "germany", "france",
                        "italy", "spain", "netherlands", "brussels", "ecb",
                        "eurozone", "uk", "britain"],
            "amplifiers": {
                "forex_eur": 1.4,
                "equities_europe": 1.3,
                "commodities_gas": 1.3,
            },
        },
        "russia": {
            "regions": ["russia", "moscow", "kremlin", "putin", "ukraine",
                        "gazprom", "nord stream"],
            "amplifiers": {
                "commodities_oil": 1.4,
                "commodities_gas": 1.8,
                "commodities_wheat": 1.5,
                "energy": 1.6,
                "equities_europe": 1.3,
            },
        },
        "asia_pacific": {
            "regions": ["japan", "south korea", "north korea", "india",
                        "australia", "asean", "singapore", "indonesia",
                        "vietnam", "philippines", "asia-pacific"],
            "amplifiers": {
                "equities_tech": 1.3,
                "commodities_shipping": 1.4,
                "forex_jpy": 1.3,
            },
        },
    },

    # ── Event type classification — acute vs structural ──────────────────
    "acute_event_types": [
        "MILITARY_CONFLICT", "TERRORISM", "CYBER_ATTACK",
        "NATURAL_DISASTER", "CIVIL_UNREST",
    ],
    "structural_event_types": [
        "SANCTIONS", "TRADE_WAR", "ELECTION", "DIPLOMATIC_CRISIS",
        "REGULATORY_CHANGE", "ENERGY_CRISIS", "REPUTATION_EVENT",
        "COMMODITY_DISRUPTION", "CURRENCY_CRISIS",
    ],

    # ── Signal strength labels ───────────────────────────────────────────
    "signal_strength_thresholds": {
        "weak": 0.25,
        "moderate": 0.50,
        "strong": 0.75,
        "extreme": 0.90,
    },

    # ── Recommended action mapping ───────────────────────────────────────
    "action_thresholds": {
        "reduce_exposure": 0.6,
        "hedge": 0.4,
        "hold": 0.2,
        "increase_exposure": -0.3,  # negative net_signal = bullish opportunity
    },
}
