# AlgoTrader — Intelligence & Self-Improvement

> **Last updated:** April 2026 — reflects the live codebase at ~40,000 lines of code.

---

## Table of Contents

1. [Intelligence Architecture Overview](#1-intelligence-architecture-overview)
2. [Core Intelligence Pipeline (6 modules)](#2-core-intelligence-pipeline-6-modules)
3. [Adaptive Intelligence (7 modules)](#3-adaptive-intelligence-7-modules)
4. [Instrument Intelligence (4 modules)](#4-instrument-intelligence-4-modules)
5. [AI Decision Layer (4 use cases)](#5-ai-decision-layer-4-use-cases)
6. [Asset-Specific Trading Rules (5 engines)](#6-asset-specific-trading-rules-5-engines)
7. [Spread Betting Engine (7 components)](#7-spread-betting-engine-7-components)
8. [Continuous Improvement Engine](#8-continuous-improvement-engine)
9. [Self-Optimizer](#9-self-optimizer)
10. [Feedback Loop](#10-feedback-loop)
11. [Alerting System](#11-alerting-system)
12. [Geopolitical Risk & Sentiment Intelligence](#12-geopolitical-risk--sentiment-intelligence)
13. [Execution Trust Layer](#13-execution-trust-layer)

---

## 1. Intelligence Architecture Overview

AlgoTrader contains **42 intelligence and analysis modules** across **10 subsystems**. Together they form a self-improving system — each module feeds outcomes back into the others, compounding over time.

### The 10 Subsystems

| Subsystem | Source File | Modules | Purpose |
|-----------|------------|---------|---------|
| Core Intelligence | `services/intelligence.py` | 6 | Pre-trade pipeline, scoring, sizing |
| Adaptive Intelligence | `services/adaptive_intelligence.py` | 7 | Learns from outcomes, adjusts behaviour |
| Instrument Intelligence | `services/instrument_intelligence.py` | 4 | What to trade, when to exit, trade worthiness |
| AI Decision Layer | `services/ai_decision_layer.py` | 4 | Claude/Gemini for reasoning tasks |
| Asset Trading Rules | `services/asset_trading_rules.py` | 5 | Per-asset-class constraints |
| Spread Betting Engine | `services/spread_betting.py` | 7 | SB-specific sizing and risk |
| Geopolitical Risk | `services/geo_risk/` | 7 | Real-time geopolitical event monitoring, classification, and impact scoring |
| Position Manager | `services/position_manager.py` | 3 | Stop/TP/trailing, streak detection |
| Alerting | `services/alerting.py` | 4 | Multi-channel alert routing |
| Execution Trust | `services/execution_trust.py` | 3 | Unified trade confidence scoring |

### All 42 Modules at a Glance

| # | Module | Subsystem | Core Function |
|---|--------|-----------|--------------|
| 1 | StrategyScoreboard | Core Intelligence | Live P&L tracking per strategy |
| 2 | MultiTimeframeConsensus | Core Intelligence | 15m/1h/4h signal alignment |
| 3 | CorrelationGuard | Core Intelligence | Prevents correlated overexposure |
| 4 | KellyCriterion | Core Intelligence | Optimal position sizing |
| 5 | MarketMemory | Core Intelligence | Learns from similar past conditions |
| 6 | IntelligencePipeline | Core Intelligence | Orchestrates modules 1–5 |
| 7 | AdaptiveExitLevels | Adaptive Intelligence | Dynamic SL/TP from trade history |
| 8 | SymbolDiscovery | Adaptive Intelligence | Finds new opportunities |
| 9 | AIAccuracyTracker | Adaptive Intelligence | Scores AI predictions |
| 10 | WalkForwardValidator | Adaptive Intelligence | Prevents overfitting |
| 11 | AdaptiveFrequency | Adaptive Intelligence | Adjusts trading frequency |
| 12 | TimeOfDayProfiler | Adaptive Intelligence | Profiles profitable hours |
| 13 | PredictionTracker | Adaptive Intelligence | Signal accuracy over time |
| 14 | InstrumentSelector | Instrument Intelligence | Spot vs perpetual selection |
| 15 | SmartExitDecision | Instrument Intelligence | AI-powered exit timing |
| 16 | TradeWorthinessFilter | Instrument Intelligence | Filters unprofitable setups |
| 17 | LiquidationCalculator | Instrument Intelligence | Calculates liquidation prices |
| 18 | NewsImpactAssessor | AI Decision Layer | Assesses headline impact |
| 19 | SmartExitAdvisor | AI Decision Layer | AI exit reasoning |
| 20 | LossPatternAnalyzer | AI Decision Layer | Root-cause loss analysis |
| 21 | AIStrategySelector | AI Decision Layer | AI strategy selection |
| 22 | CryptoTradingRules | Asset Trading Rules | Crypto-specific gates |
| 23 | ForexTradingRules | Asset Trading Rules | Forex session/event filters |
| 24 | StockTradingRules | Asset Trading Rules | Earnings/hours/P-E checks |
| 25 | IndexTradingRules | Asset Trading Rules | VIX/breadth/gap checks |
| 26 | CommodityTradingRules | Asset Trading Rules | Seasonal/geopolitical filters |
| 27 | SpreadBetPositionSizer | Spread Betting Engine | £/point calculation |
| 28 | MarginMonitor | Spread Betting Engine | Real-time margin utilisation |
| 29 | OvernightFundingCalculator | Spread Betting Engine | SONIA-based funding costs |
| 30 | SpreadMonitor | Spread Betting Engine | Bid-ask anomaly detection |
| 31 | MarketHoursFilter | Spread Betting Engine | Session awareness |
| 32 | GapProtectionManager | Spread Betting Engine | Weekend/close gap risk |
| 33 | GeoEventClassifier | Geopolitical Risk | 14-type keyword event classification |
| 34 | GeoImpactMatrix | Geopolitical Risk | 14×4 event-to-asset impact profiles |
| 35 | GeoRiskScorer | Geopolitical Risk | Composite risk scoring with recency decay |
| 36 | AssetImpactScorer | Geopolitical Risk | Per-asset risk/opportunity scoring |
| 37 | GeoNewsIngester | Geopolitical Risk | GDELT + RSS real-time data ingestion |
| 38 | GeoMonitor | Geopolitical Risk | Central orchestrator and query interface |
| 39 | GeoAlertManager | Geopolitical Risk | User-configured geopolitical alerts |
| 40 | ExecutionTrustScorer | Execution Trust | Weighted composite scoring across 10 dimensions |
| 41 | VenueQualityTracker | Execution Trust | Per-exchange execution quality tracking |
| 42 | TrustScoreHistory | Execution Trust | Records evaluations and correlates with outcomes |

---

## 2. Core Intelligence Pipeline (6 modules)

Source: `backend/app/services/intelligence.py` (632 lines)

The core pipeline runs on every potential trade entry as a final pre-execution gate. All 5 scoring modules are checked in sequence; if any module blocks, the trade is cancelled.

```
Pre-trade signal received
         │
         ▼
  ┌──────────────────┐
  │ StrategyScoreboard│  Is this strategy winning lately?
  └────────┬─────────┘
           │ pass
           ▼
  ┌──────────────────────┐
  │ MultiTimeframeConsens│  Do all timeframes agree?
  └────────┬─────────────┘
           │ pass
           ▼
  ┌──────────────────┐
  │ CorrelationGuard │  Is portfolio already too correlated?
  └────────┬─────────┘
           │ pass
           ▼
  ┌──────────────────┐
  │ KellyCriterion   │  How much should we size?
  └────────┬─────────┘
           │ sizing
           ▼
  ┌──────────────────┐
  │ MarketMemory     │  Has this setup failed before?
  └────────┬─────────┘
           │ approved
           ▼
      Execute Trade
```

### 2.1 StrategyScoreboard

**File:** `services/intelligence.py` → class `StrategyScoreboard`

Tracks the live P&L of every strategy in real-time. Unlike backtesting (which is backward-looking on historical data), this scores what is working **right now** in current market conditions.

**Data structure:**

```python
_outcomes: Dict[str, List[Dict]] = {
    "strategy_name": [
        { "pnl": 45.20, "pnl_pct": 1.8, "symbol": "BTC/USDT",
          "regime": "trending_up", "timestamp": "...", "won": True },
        ...
    ]
}
# Rolling window: last 100 trades per strategy
_max_history = 100
```

**Composite score formula:**

```
composite_score = (win_rate × 0.50) + (avg_pnl_normalised × 0.30) + (streak_score × 0.20)

Where:
  win_rate        = wins / total (last 20 trades)
  avg_pnl_normalised = min(1, max(-1, avg_pnl_pct / 5))
  streak_score    = sum(+1 for win, -1 for loss over last 5 trades) / 5
```

**Score range:** −0.2 to 1.0 (0.5 = neutral / no data)

**Weight adjustment:** Strategy selection weights are blended 60/40:
```
adjusted_weight = original_weight × 0.6 + live_score × 0.4
```

**Score decay:** Stale strategies (no trades in 7 days) decay toward neutral (0.5) to prevent old good data from over-influencing current decisions.

**Usage in orchestrator:**
```python
live_scores = intelligence.scoreboard.get_live_scores()
# → { "Momentum": { "score": 0.78, "win_rate": 0.70, "trades": 18 }, ... }
```

---

### 2.2 MultiTimeframeConsensus

**File:** `services/intelligence.py` → class `MultiTimeframeConsensus`

Runs the selected strategy signal across three timeframes simultaneously. A trade is only approved if at least 2 out of 3 timeframes agree on direction.

**Timeframes analysed:**

| Timeframe | Candle Count | Purpose |
|-----------|-------------|---------|
| 15m | 96 candles | Short-term signal confirmation |
| 1h | 100 candles | Medium-term trend |
| 4h | 50 candles | Long-term regime confirmation |

**Consensus logic:**

```python
agree_count = sum(1 for sig in [sig_15m, sig_1h, sig_4h] if sig == target_signal)

if agree_count >= 2:
    approved = True
elif regime in ("trending_up", "trending_down") and agree_count >= 1:
    # Strong trend regime override: 1/3 sufficient
    approved = True
    confidence_boost = True
else:
    approved = False  # Block trade
```

**Impact:** Filters approximately 40–50% of false signals that fire on a single timeframe but reverse quickly.

**Confidence modifier:**
- 3/3 agreement → confidence × 1.2
- 2/3 agreement → confidence unchanged
- 1/3 (trend override) → confidence × 0.85

---

### 2.3 CorrelationGuard

**File:** `services/intelligence.py` → class `CorrelationGuard`

Prevents overconcentration in correlated assets. Many crypto assets move together — buying both BTC and ETH is not true diversification.

**Correlation map (hardcoded + learnable):**

| Asset Pair | Correlation | Default Action |
|-----------|------------|---------------|
| BTC / ETH | 0.85 | Reduce size |
| BTC / SOL | 0.75 | Allow (warn) |
| BTC / ADA | 0.70 | Allow (warn) |
| EUR/USD / GBP/USD | 0.80 | Reduce size |
| Gold / Silver | 0.75 | Allow (warn) |
| US500 / NAS100 | 0.90 | Block |

**Decision rules:**

```
Correlation > 0.85 → BLOCK new position entirely
Correlation 0.70–0.85 → REDUCE position size by 50%
Correlation < 0.70 → ALLOW full position
No existing correlated position → ALLOW full position
```

**Example:**
```
Scenario: Holding ETH/USDT, signal fires for SOL/USDT
  BTC dominance → ETH corr=0.85, SOL corr=0.75
  Action: SOL allowed but size reduced to 50%
  Reasoning: "SOL correlates 0.75 with existing ETH — reducing size"
```

---

### 2.4 KellyCriterion

**File:** `services/intelligence.py` → class `KellyCriterion`

Calculates the mathematically optimal position size using actual historical win rates and average returns.

**Kelly formula:**

```
f* = (b × p − q) / b

Where:
  f* = fraction of capital to bet
  b  = average win / average loss ratio (odds)
  p  = probability of winning (win rate)
  q  = probability of losing (1 − p)
```

**Safety modifications:**
1. **Half-Kelly**: Use `f*/2` to halve the recommended fraction — reduces risk of ruin
2. **Minimum trades**: If strategy has fewer than 5 trades, default to minimum position size (1% of portfolio)
3. **Hard clamp**: Final fraction clamped to 1%–20% of portfolio regardless of formula output

**Example calculation:**
```
Strategy outcomes: 65% win rate, avg win = 2.1%, avg loss = 1.3%
  b = 2.1 / 1.3 = 1.615
  p = 0.65, q = 0.35
  f* = (1.615 × 0.65 − 0.35) / 1.615 = 0.432 = 43.2%
  half_kelly = 21.6%
  clamped = 20%   ← hard cap prevents over-betting
```

**Output:** `position_pct` (1–20), passed to the position sizing step of the orchestrator.

---

### 2.5 MarketMemory

**File:** `services/intelligence.py` → class `MarketMemory`

Stores the system's trading history as structured memories and uses similarity scoring to prevent repeating past mistakes.

**Memory structure (max 500 entries):**

```python
{
    "conditions": {
        "regime": "ranging",
        "fear_greed_bucket": "fear",  # extreme_fear/fear/neutral/greed/extreme_greed
        "social_sentiment": "bearish",
    },
    "strategy": "Momentum",
    "symbol": "BTC/USDT",
    "outcome": "win" | "loss",
    "pnl_pct": -2.3,
    "timestamp": "2026-01-15T14:22:00"
}
```

**Similarity scoring** (used when evaluating a new potential trade):

| Condition Match | Points Awarded |
|----------------|---------------|
| Same regime | 3 points |
| Same Fear & Greed bucket | 2 points |
| Same social sentiment direction | 1 point |
| Maximum similarity score | 6 points |

**Decision thresholds:**

```
Similar memories (score ≥ 4):
  Win rate < 30%  → BLOCK trade ("Historically poor setup")
  Win rate 30–65% → ALLOW but reduce size by 20%
  Win rate > 65%  → ALLOW and BOOST size +20% ("Strong historical setup")

No similar memories (score < 4) → ALLOW with neutral sizing
```

---

### 2.6 IntelligencePipeline.pre_trade_check()

**File:** `services/intelligence.py` → class `IntelligencePipeline`

The master method that orchestrates all 5 modules and returns a single go/no-go decision.

```python
result = await intelligence.pre_trade_check(
    exchange="binance",
    symbol="BTC/USDT",
    strategy_name="Momentum",
    strategy_params={"lookback": 14},
    signal=1,           # 1=buy, -1=sell
    conditions={
        "regime": "trending_up",
        "fear_greed": 35,
        "social_bullish": 62,
        "volatility": 28.5,
    },
    existing_positions=[...],
    portfolio_value=12500.00,
    max_position_pct=20,
)

# Returns:
{
    "approved": True,
    "position_pct": 12.5,     # Kelly-adjusted sizing
    "reasons": [],            # List of block reasons (empty if approved)
    "memory_matches": 3,      # How many similar historical setups found
    "confidence_modifier": 1.1,
    "modules_passed": ["scoreboard", "mtf_consensus", "correlation", "kelly", "memory"]
}
```

**record_trade_outcome()** is called after every closed position, feeding results back into the scoreboard and memory:
```python
intelligence.record_trade_outcome(
    strategy="Momentum", symbol="BTC/USDT",
    pnl=45.20, regime="trending_up",
    entry_price=67200.0, exit_price=68410.0,
)
```

---

## 3. Adaptive Intelligence (7 modules)

Source: `backend/app/services/adaptive_intelligence.py` (467 lines)

The adaptive layer focuses on continuously improving system behaviour based on observed outcomes — not static parameters.

### 3.1 AdaptiveExitLevels

**Purpose:** Replaces fixed 5% stop-loss / 10% take-profit with levels learned from actual trade outcomes.

**Learning mechanism:**
- Stores last 200 trade exits (pnl_pct, regime, volatility, hold_hours)
- Analyses winning trades → sets take-profit just below average win size
- Analyses losing trades → sets stop-loss just beyond average loss size
- Applies volatility scaling: wider in volatile markets, tighter in quiet ones

**Algorithm:**
```python
wins = [t for t in outcomes if t["pnl_pct"] > 0]
losses = [t for t in outcomes if t["pnl_pct"] < 0]

avg_win = mean(wins) * 0.80      # TP at 80% of historical average win
avg_loss = abs(mean(losses)) * 1.20  # SL at 120% of historical average loss

# Volatility scaling
vol_factor = current_vol / baseline_vol  # ~20% as baseline
stop_loss_pct = avg_loss * vol_factor
take_profit_pct = avg_win * vol_factor
trailing_stop_pct = stop_loss_pct * 0.60  # 60% of stop
```

**Default fallback** (fewer than 10 trades): `SL=5%, TP=10%, trailing=3%`

---

### 3.2 SymbolDiscovery

**Purpose:** Automatically discovers new trading opportunities by scanning volume leaders, rather than trading only a static watchlist.

**Mechanism:**
- Periodically queries CoinGecko for top-volume assets
- Filters by minimum 24h volume threshold
- Tracks performance of "discovered" symbols
- Promotes high-performing discovered symbols to the active watchlist
- Demotes symbols that generate repeated losses

---

### 3.3 AIAccuracyTracker

**Purpose:** Measures how accurate AI analysis has been, and adjusts the confidence modifier applied to AI recommendations.

**Tracking per AI provider:**
```python
_predictions: Dict[str, List[Dict]] = {
    "claude": [
        { "symbol": "BTC/USDT", "predicted_sentiment": "bullish",
          "confidence": 0.75, "actual_outcome": "win",
          "timestamp": "...", "was_correct": True }
    ]
}
```

**Accuracy adjustment:**
- AI accuracy > 65%: confidence multiplier = 1.15 (trust AI more)
- AI accuracy 50–65%: confidence multiplier = 1.0 (baseline)
- AI accuracy < 50%: confidence multiplier = 0.85 (discount AI signals)
- Fewer than 10 predictions: no adjustment

**record_prediction() / record_outcome()** are called before/after each trade.

---

### 3.4 WalkForwardValidator

**Purpose:** Prevents the optimizer from finding parameters that work only on historical data (overfitting). Validates parameter stability across rolling time windows.

**Methodology:**
- Splits historical data into rolling windows (e.g. 90-day in-sample, 30-day out-of-sample)
- Optimises parameters on in-sample period
- Tests those parameters on the subsequent out-of-sample period
- Accepts parameter set only if performance holds across multiple windows
- Rejects parameter sets that are profitable in-sample but fail out-of-sample

---

### 3.5 AdaptiveFrequency

**Purpose:** Adjusts how often the orchestrator cycles based on current market conditions.

**Rules:**
```
High volatility (ATR > 2× baseline) → shorter intervals (trade more)
Low volatility (ATR < 0.5× baseline) → longer intervals (be patient)
Trending regime → maintain or increase frequency
Ranging regime → reduce frequency
After 3 consecutive losses → double interval (cool-off period)
```

Prevents over-trading in flat markets and under-trading during high-opportunity windows.

---

### 3.6 TimeOfDayProfiler

**Purpose:** Learns which hours of the day generate the best trade outcomes, and adjusts position sizes accordingly.

**Data structure:**
```python
_hourly_outcomes: Dict[int, List[Dict]] = {
    0:  [{"won": True, "pnl_pct": 1.2}, ...],   # Midnight UTC
    9:  [{"won": True, "pnl_pct": 2.1}, ...],   # London open
    14: [{"won": True, "pnl_pct": 1.8}, ...],   # NY open overlap
    ...
}
```

**Position size modifier by hour:**
- Hours with win rate > 65%: size multiplier = 1.15
- Hours with win rate 45–65%: multiplier = 1.0
- Hours with win rate < 45%: multiplier = 0.75
- Hours with fewer than 5 trades: multiplier = 1.0 (no adjustment)

The time multiplier is applied in Step 10 of the orchestrator: `raw_position_value *= time_size_mult`

---

### 3.7 PredictionTracker

**Purpose:** Measures the accuracy of every individual signal type over time, not just AI predictions.

Tracks accuracy per signal source:
- Fear & Greed index (at each bucket: extreme_fear, fear, neutral, greed, extreme_greed)
- Social sentiment bullish/bearish calls
- Regime detection accuracy
- Individual strategy signals

Used by the optimizer to identify which signals are genuinely predictive vs noise.

---

## 4. Instrument Intelligence (4 modules)

Source: `backend/app/services/instrument_intelligence.py` (490 lines)

The instrument intelligence layer answers the most practical trading questions: what exactly to trade, which direction, at what leverage, and whether to exit now.

### 4.1 InstrumentSelector

**Purpose:** Decides whether to use spot, perpetual futures, or margin for a given trade.

**Decision matrix:**

| Condition | Recommended Instrument | Max Leverage |
|-----------|----------------------|-------------|
| Trending strongly, bullish | Perpetual long | 3–5× |
| Trending strongly, bearish | Perpetual short | 3–5× |
| Ranging / uncertain | Spot only | 1× |
| High volatility | Spot or reduced leverage | 1–2× |
| Small portfolio (<$1,000) | Spot only | 1× |
| Conservative risk setting | Spot only | 1× |
| Moderate risk setting | Up to 3× | 3× |
| Aggressive risk setting | Up to 5× | 5× |

**Typical funding rates:**
```python
TYPICAL_FUNDING_RATES = {
    "perpetual": 0.0001,  # 0.01% per 8h = ~0.1% daily
}
```

**Maximum leverage by risk tolerance:**
```python
MAX_LEVERAGE = {
    "conservative": 1.0,   # No leverage (spot only)
    "moderate": 3.0,       # Up to 3×
    "aggressive": 5.0,     # Up to 5× (never more for autonomous trading)
}
```

---

### 4.2 SmartExitDecision

**Purpose:** Decides whether an open position should be exited now, based on factors beyond mechanical stops.

**Inputs:**
- Current unrealised P&L %
- Holding duration (hours)
- Current regime (may have changed since entry)
- AI sentiment analysis
- Upcoming high-impact events

**Decision outputs:**
- `hold` — continue holding, no action
- `sell` — exit now (with reasoning)
- `add` — add to the position (scale in)
- `scale_out` — reduce position size by 50%

**Rule-based fallback triggers:**
```
P&L > +15% AND regime changed to "ranging" → sell (lock in profits)
P&L between −3% and 0% AND held > 48 hours → sell (dead money)
P&L < −8% AND regime = "trending_down" against position → sell (regime shift)
```

---

### 4.3 TradeWorthinessFilter

**Purpose:** Filters out trades where the expected profit does not justify the costs — even if the signal is technically valid.

**Cost components:**
```python
round_trip_fee_pct = fee_rate × 2 × 100   # Both buy and sell legs
slippage_pct = 0.10                         # ~0.05% per side
funding_pct = 0.03 if perpetual else 0     # ~0.03% per day

total_cost_pct = round_trip_fee_pct + slippage_pct + funding_pct
```

**Worthiness formula:**
```python
expected_profit_pct = expected_move_pct × leverage × confidence
profit_to_cost_ratio = expected_profit_pct / total_cost_pct

is_worthy = profit_to_cost_ratio >= 1.2   # Must expect 20% more than costs
```

**Example:**
```
Exchange: Kraken (0.26% taker)
Instrument: Spot (no funding)
Expected move: 1.5%, Leverage: 1×, Confidence: 0.60

round_trip_fee_pct = 0.26% × 2 = 0.52%
slippage_pct = 0.10%
total_cost = 0.62%

expected_profit = 1.5% × 1 × 0.60 = 0.90%
ratio = 0.90 / 0.62 = 1.45× → IS WORTHY ✓
```

```
Exchange: Coinbase (0.60% taker)
Expected move: 0.8%, Leverage: 1×, Confidence: 0.55

round_trip_fee = 1.20%, total_cost = 1.30%
expected_profit = 0.8 × 1 × 0.55 = 0.44%
ratio = 0.44 / 1.30 = 0.34× → NOT WORTHY ✗ (need 1.2×)
```

---

### 4.4 LiquidationCalculator

**Purpose:** Computes liquidation prices for leveraged positions so the system never enters a trade where normal market moves could trigger liquidation.

**Formula:**
```python
# Long position
liquidation_price = entry_price × (1 - (1 / leverage) + maintenance_margin)

# Short position
liquidation_price = entry_price × (1 + (1 / leverage) - maintenance_margin)
```

**Safety gate:** If the current price is within 20% of the calculated liquidation price, the trade is blocked regardless of other signals.

---

## 5. AI Decision Layer (4 use cases)

Source: `backend/app/services/ai_decision_layer.py` (370 lines)

Claude/Gemini are integrated at four specific decision points where LLM reasoning genuinely outperforms hard-coded rules. All four functions fall back to deterministic rule-based logic when no API key is configured.

### AI Provider Selection

```python
# ai_engine.py
provider = _get_ai_provider()  # Returns "claude", "gemini", or None

if provider == "claude":
    response = await anthropic_client.messages.create(...)
elif provider == "gemini":
    response = await gemini_model.generate_content_async(...)
else:
    return rule_based_fallback(...)
```

---

### 5.1 NewsImpactAssessor — assess_news_impact()

**When called:** After fetching RSS news feeds for each symbol, if any headlines are found.

**Input:** List of news headlines + asset name (e.g. "Bitcoin")

**AI prompt structure:**
- Provides 5–10 most recent headlines
- Asks AI to classify impact: `bullish`, `bearish`, or `neutral`
- Asks for impact score (−1.0 to +1.0)
- Asks whether trading should be halted

**Output:**
```python
{
    "impact": "bearish",
    "impact_score": -0.8,
    "should_halt_trading": True,
    "key_headline": "Regulator announces emergency crypto trading ban",
    "reasoning": "Major regulatory announcement creates extreme uncertainty",
    "provider": "claude"
}
```

**Orchestrator actions:**
- `should_halt_trading = True` → skip symbol for this cycle entirely
- `impact = "bearish"` and `impact_score < -0.7` → reduce position size 25%

**Rule-based fallback:** Keywords scan for "ban", "hack", "crash", "seized" → halt; "ETF approved", "adoption" → bullish boost.

---

### 5.2 SmartExitAdvisor — advise_exit()

**When called:** During position review phase (Step 4 of orchestrator) for each open position.

**Input:**
```python
{
    "symbol": "ETH/USDT",
    "entry_price": 3450.0,
    "current_price": 3820.0,
    "pnl_pct": 10.7,
    "hold_hours": 18,
    "regime": "ranging",      # Changed since entry
    "fear_greed": 72,
    "recent_news": ["Ethereum faces scaling criticism..."],
    "strategy": "EMA Crossover"
}
```

**Output:**
```python
{
    "action": "sell",
    "confidence": 0.80,
    "reasoning": "Regime shifted to ranging after entry in trending_up. At +10.7% with 18h hold, prudent to lock in gains before mean reversion.",
    "provider": "claude"
}
```

**Rule-based fallback:**
- P&L > 15% → suggest sell
- Holding > 72 hours with P&L < 2% → suggest sell
- P&L < −5% → suggest sell (stop-loss supplementary)

---

### 5.3 LossPatternAnalyzer — analyze_loss_pattern()

**When called:** When losing streak reaches 3 or more consecutive losses.

**Input:** Last 10 trade records (strategy, symbol, regime, pnl_pct, hold_hours, entry/exit prices)

**AI prompt:** Asks the LLM to identify the root cause pattern from:
- Wrong strategy for current regime
- Entering too late in the move
- Holding too long through reversals
- Market regime shifted mid-trade
- Over-trading correlated assets
- Fee drag eroding marginal wins

**Output:**
```python
{
    "root_cause": "regime_mismatch",
    "description": "Using trend-following strategies in a ranging market. EMA Crossover and Momentum both fail when price oscillates in a tight band.",
    "suggestions": [
        "Switch to Mean Reversion or Grid Trading for ranging conditions",
        "Reduce position size until regime confirms trending",
        "Add ADX filter (>25) before running trend strategies"
    ],
    "provider": "claude"
}
```

The suggestions are logged to the decision log and surfaced in the Auto-Trader UI.

---

### 5.4 AIStrategySelector — ai_select_strategies()

**When called:** During strategy selection (Step 8), when AI is available and conditions are complex.

**Inputs:**
- Current regime and confidence level
- AI sentiment analysis
- Available strategy list (with weights)
- Recent strategy performance (last 30 days)
- Fear & Greed level
- News impact summary

**AI reasoning process:**
Unlike the hardcoded regime→strategy map, the AI considers combinations: e.g. trending regime + extreme greed + bad recent news might suggest a defensive Mean Reversion rather than Momentum.

**Output:**
```python
[
    {"name": "Mean Reversion", "params": {"window": 20}, "weight": 0.45,
     "reasoning": "Trending up but extreme greed (F&G=88) suggests exhaustion"},
    {"name": "MACD", "params": {"fast": 12, "slow": 26}, "weight": 0.35,
     "reasoning": "Strong trend still active on 4H — MACD confirms"},
    {"name": "RSI", "params": {"period": 14}, "weight": 0.20,
     "reasoning": "RSI divergence visible — useful timing signal"}
]
```

**Fallback:** Returns the asset-routing strategy list unchanged if AI is unavailable.

---

## 6. Asset-Specific Trading Rules (5 engines)

Source: `backend/app/services/asset_trading_rules.py` (920 lines)

Each asset class has fundamentally different market dynamics. The `AssetTradingRouter` classifies every symbol and delegates to the correct rules engine. The router returns `validate=True/False`, a `size_multiplier` (0–1.5), and a list of `warnings`.

### 6.1 CryptoTradingRules

**Class:** `CryptoTradingRules` — handles all cryptocurrency pairs.

**Strategy maps by regime:**

| Regime | Top Strategies |
|--------|---------------|
| `trending_up` | Momentum (0.30), EMA Crossover (0.25), Pure AI (0.20), MACD (0.15), Bollinger (0.10) |
| `trending_down` | DCA (0.30), Mean Reversion (0.25), RSI (0.20), Grid Trading (0.15) |
| `ranging` | Grid Trading (0.35), Mean Reversion (0.30), RSI (0.25) |
| `volatile` | DCA (0.40), Grid Trading (0.30), RSI (0.20) |

**Validation checks:**

| Check | Condition | Action |
|-------|-----------|--------|
| Fear & Greed gate | F&G between 20–80 | Allow |
| Fear & Greed gate | F&G < 20 | Contrarian buy signal only |
| Fear & Greed gate | F&G > 80 | Reduce size by 30% |
| Weekend liquidity | Saturday/Sunday UTC | Reduce size by 20% |
| BTC dominance | BTC.D > 60% | Altcoin size reduced |
| Extreme fear | F&G ≤ 10 | Boost buy size +10% (contrarian) |

**Risk parameters:**
```python
{
    "max_position_pct": 15,
    "stop_distance_pct": 5.0,
    "max_leverage": 5,   # Aggressive setting
    "session_24_7": True,
}
```

---

### 6.2 ForexTradingRules

**Class:** `ForexTradingRules` — handles all currency pairs.

**Session-based trading:** Forex has four major sessions with distinct liquidity windows:

| Session | UTC Hours | Characteristics |
|---------|-----------|----------------|
| Sydney | 22:00–07:00 | Thin liquidity, avoid majors |
| Tokyo | 00:00–09:00 | JPY and AUD pairs most active |
| London | 08:00–17:00 | Highest volume — preferred for entries |
| New York | 13:00–22:00 | High volume, USD pairs |
| London/NY Overlap | 13:00–17:00 | Peak liquidity |

**Validation checks:**

| Check | Condition | Action |
|-------|-----------|--------|
| Weekend block | Saturday/Sunday | Block all forex trades |
| High-impact events | NFP, FOMC, CPI within 2h | Block or reduce 50% |
| Carry trade | Interest rate differential | Adjust direction |
| Retail contrarian | Majority long → slight short bias | Size adjustment |
| Session hours | Outside all sessions | Reduce size 40% |

**Strategy maps by regime:**

| Regime | Top Strategies |
|--------|---------------|
| `trending_up` | EMA Crossover, MACD, Momentum |
| `trending_down` | EMA Crossover, MACD, SMA Crossover |
| `ranging` | Bollinger Bands, Mean Reversion, RSI |
| `volatile` | RSI, Grid Trading, DCA |

---

### 6.3 StockTradingRules

**Class:** `StockTradingRules` — handles individual equities (UK and US).

**Validation checks:**

| Check | Condition | Action |
|-------|-----------|--------|
| Earnings proximity | Earnings < 3 days away | Block position (gap risk) |
| Market hours | Outside exchange hours | Block trades |
| P/E validation | P/E > 50 (growth overextension) | Reduce size 30% |
| Sector rotation | Sector lagging rotation | Reduce size 20% |
| Penny stock | Price < $1 | Block (regulatory/liquidity) |

**Market hours by exchange:**

| Exchange | Trading Hours (UTC) |
|----------|-------------------|
| LSE (UK) | 08:00–16:30 |
| NYSE/NASDAQ | 14:30–21:00 |

**Risk parameters:**
```python
{
    "max_position_pct": 15,
    "stop_distance_pct": 3.0,     # Tighter than crypto
    "earnings_blackout_days": 3,
}
```

---

### 6.4 IndexTradingRules

**Class:** `IndexTradingRules` — handles stock indices (FTSE, S&P 500, DAX, etc.)

**Validation checks:**

| Check | Condition | Action |
|-------|-----------|--------|
| VIX level | VIX > 30 | Reduce size 40% (high fear) |
| VIX level | VIX > 40 | Block new longs |
| Market breadth | < 40% stocks above 200MA | Reduce size 30% |
| Gap risk | First 15 min after open | Reduce size 50% |
| Gap risk | Last 15 min before close | Block new positions |
| Economic calendar | Major data release within 1h | Reduce size 30% |

**Key indices tracked:**
- UK: UK100 (FTSE 100)
- US: US500 (S&P 500), US30 (Dow Jones), NAS100 (Nasdaq 100)
- Europe: GER40 (DAX), CAC40, STOXX50
- Asia: JPN225 (Nikkei 225), AUS200

---

### 6.5 CommodityTradingRules

**Class:** `CommodityTradingRules` — handles metals, energy, and agricultural commodities.

**Validation checks:**

| Check | Condition | Action |
|-------|-----------|--------|
| Seasonal patterns | Agricultural harvest/planting periods | Adjust direction bias |
| Geopolitical risk | OPEC meeting, supply disruptions | Reduce size 30% |
| Safe-haven dynamics | Risk-off environment | Gold size boost |
| Storage/supply reports | EIA weekly (oil), USDA (crops) | Avoid entries ±2h |
| Roll cost | Near contract expiry | Warning issued |

**Asset-specific behaviour:**
- **Gold (XAUUSD)**: Safe-haven; in risk-off conditions (high VIX, market crash), size multiplier increases to 1.3×
- **Oil (USOIL/UKOIL)**: Sensitive to EIA weekly reports; size reduced near report times
- **Agricultural**: Strong seasonal patterns; DCA strategy weighted higher for volatility management

---

## 7. Spread Betting Engine (7 components)

Source: `backend/app/services/spread_betting.py` (1,011 lines)

Spread betting is fundamentally different from quantity-based trading. Positions are sized in £ per point of price movement, leverage is built-in via FCA-regulated margin requirements, and profits are tax-free in the UK. The engine handles all the unique mechanics.

### FCA Margin Rates

```python
MARGIN_RATES = {
    "forex_major":  0.0333,  # 3.33% margin = 30:1 leverage
    "forex_minor":  0.05,    # 5% margin = 20:1 leverage
    "indices":      0.05,    # 5% margin = 20:1 leverage
    "commodities":  0.10,    # 10% margin = 10:1 leverage
    "metals":       0.05,    # 5% margin = 20:1 leverage
    "shares_uk":    0.20,    # 20% margin = 5:1 leverage
    "shares_us":    0.20,    # 20% margin = 5:1 leverage
    "crypto":       0.50,    # 50% margin = 2:1 leverage (FCA restricted)
}
```

### Overnight Funding Rate

```python
_BENCHMARK_RATE = 0.045   # SONIA 4.5%
_BROKER_MARKUP = 0.025    # 2.5% broker markup
# Total overnight rate = 7.0% annualised
# Daily cost on a £10,000 notional position ≈ £1.92/day
```

### 7.1 SpreadBetPositionSizer

**Purpose:** Calculates the £/point stake size for a spread bet.

**Formula:**
```python
# 1. Get margin rate for asset class
margin_rate = MARGIN_RATES[classify_asset(symbol)]

# 2. Risk amount (£) = account balance × risk_pct / 100
risk_amount = account_balance * risk_pct / 100

# 3. £/point = risk_amount / stop_distance_in_points
stake_per_point = risk_amount / stop_distance_points

# 4. Margin required = stake × current_price × margin_rate
margin_required = stake_per_point * current_price * margin_rate

# 5. Check margin_required <= available_capital × 0.90
if margin_required > available_capital * 0.90:
    # Reduce stake proportionally
    stake_per_point = (available_capital * 0.90) / (current_price * margin_rate)
```

**Output:**
```python
{
    "stake_per_point": 2.50,       # £2.50 per point
    "margin_required": 1250.00,    # £1,250 collateral required
    "max_loss": 500.00,            # £500 at stop distance
    "stop_distance": 200,          # 200 points to stop
    "guaranteed_stop_recommended": True,  # If volatile/gap risk
    "market_open": True,
    "approved": True,
    "warnings": []
}
```

---

### 7.2 MarginMonitor

**Purpose:** Tracks real-time margin utilisation across all open spread bet positions.

**Monitoring levels:**

| Utilisation | Status | Action |
|-------------|--------|--------|
| < 50% | Safe | No action |
| 50–70% | Caution | Warning logged |
| 70–85% | High | Block new positions |
| > 85% | Critical | Alert fired (HIGH severity) |
| > 95% | Margin Call Risk | Alert fired (CRITICAL), suggest close |

---

### 7.3 OvernightFundingCalculator

**Purpose:** Calculates the daily funding cost for holding spread bet positions overnight.

**Formula:**
```python
def calculate_daily_funding(symbol, stake_per_point, current_price, direction):
    notional = stake_per_point * current_price
    annual_rate = _BENCHMARK_RATE + _BROKER_MARKUP   # 7.0%
    daily_rate = annual_rate / 365
    
    if direction == "long":
        daily_cost = notional * daily_rate   # Longs PAY funding
    else:
        # Shorts may RECEIVE funding (if benchmark > markup)
        daily_cost = -notional * max(0, _BENCHMARK_RATE - _BROKER_MARKUP)
    
    return daily_cost
```

**Annual cost example:** £10/point stake on UK100 at 8,000 points:
- Notional = £80,000
- Daily cost = £80,000 × 7% / 365 = £15.34/day
- Monthly cost = ~£460

---

### 7.4 SpreadMonitor

**Purpose:** Detects abnormally wide bid-ask spreads that would make a trade uneconomical.

**Mechanism:**
- Maintains rolling 50-reading average of typical spreads per symbol
- Triggers warning if current spread > 2× typical spread
- Triggers block if current spread > 3× typical spread (e.g. during news events)

---

### 7.5 MarketHoursFilter

**Purpose:** Ensures spread bets are only opened during appropriate market hours, avoiding gap risk at open/close.

**Hour rules per asset:**

| Asset Class | Trading Hours | Gap Risk Window |
|-------------|--------------|----------------|
| Forex (major) | 24/5 (Sun 22 – Fri 22 UTC) | Weekend open (Sun 22:00) |
| Indices | Exchange hours ±30min buffer | First 15min + last 15min |
| Shares | Exchange hours | Earnings announcements |
| Commodities | Near 24/5 | EIA/USDA report windows |

---

### 7.6 GapProtectionManager

**Purpose:** Assesses gap risk (price jumps that skip over stop-loss levels) and recommends guaranteed stops when gap risk is elevated.

**Guaranteed stop recommendation triggers:**
- Weekend hold (price can gap Sunday open)
- Approaching exchange close with open position
- High-impact economic event within 4 hours
- Recent history of large gaps on this instrument

**Guaranteed stop premium:** Approximately 0.3–0.5% of notional position. The engine factors this into the worthiness calculation.

---

### 7.7 TaxEfficiencyRouter

**Purpose:** Routes trades to the most tax-efficient instrument type for UK traders.

**UK tax summary:**

| Instrument | CGT | Stamp Duty | Offset Losses | Status |
|------------|-----|-----------|--------------|--------|
| Spread Bet | None | None | No | **Tax-free** |
| CFD | Yes (CGT rate) | No | Yes (vs gains) | Taxable |
| Shares | Yes (CGT rate) | 0.5% (UK shares) | Yes | Taxable |
| Crypto | Yes (CGT rate) | No | Yes | Taxable |

**Routing logic:**
- If trader is UK resident and in profit → recommend Spread Bet (tax-free)
- If trader has existing CGT losses → recommend CFD (losses can offset future CGT)
- For non-UK residents → route to standard exchange

---

## 8. Continuous Improvement Engine

Source: `services/adaptive_intelligence.py`

The improvement engine operates on a per-regime basis, ensuring parameters are appropriate for the current market environment rather than optimised for all-time averages.

### Regime-Specific Parameter Optimisation

```
Detected regime: "trending_up"
  → Load trending_up parameter space
  → Run grid search on last 30 days of trending data
  → Accept new params if Sharpe ratio improves
  → Store as current_params[regime]["trending_up"]

Detected regime: "ranging"
  → Separate parameter space
  → Different optimal periods (shorter for ranging)
  → Accept if expectancy improves
```

### Parameter Mutation

```python
def mutate_params(current_params, mutation_rate=0.15):
    """Randomly perturb parameters within valid ranges."""
    new_params = {}
    for key, value in current_params.items():
        if random.random() < mutation_rate:
            # Perturb by ±15%
            new_params[key] = value * (1 + random.uniform(-0.15, 0.15))
        else:
            new_params[key] = value
    return new_params
```

Mutations are tested against both in-sample (backtest) and out-of-sample (walk-forward) before adoption.

### Live + Backtest Blending

The optimizer blends live performance (recent 30 days) with backtest results to avoid over-weighting short-term noise:
```
final_score = live_score × 0.6 + backtest_score × 0.4
```

---

## 9. Self-Optimizer

Source: `services/` (optimizer-related functions)

### Grid-Search Backtesting

For each strategy, the optimizer runs a grid search across the parameter space:

```python
# Example: RSI period search
for period in range(10, 30, 2):      # 10, 12, 14, ... 28
    for oversold in range(20, 40, 5): # 20, 25, 30, 35
        for overbought in range(60, 80, 5):
            result = backtest(strategy, params, historical_data)
            score_matrix[(period, oversold, overbought)] = result.sharpe_ratio
```

Best parameters are saved per (strategy, regime, asset_class) combination.

### Trade Journal Analysis

After each completed trade, the journal records:
- Entry/exit conditions (regime, F&G, sentiment, strategy)
- Strategy parameters used
- Outcome (won/lost, P&L %)
- Whether the trade was blocked by any intelligence module

The journal is periodically analysed to find systematic patterns: "momentum strategy fails in ranging markets", "Coinbase fees make small trades unprofitable", etc.

### Strategy Ranking and Auto-Rebalancing

```
Monthly review:
  1. Rank all strategies by composite score (risk-adjusted return + win rate)
  2. Top 3 strategies get boosted initial weights (+10% each)
  3. Bottom 2 strategies get reduced weights (−10% each)
  4. Strategies with 0 trades in 30 days are flagged for review
  5. Weights are normalised to sum to 100% per regime
```

---

## 10. Feedback Loop

The feedback loop is the mechanism that ties all intelligence modules together into a learning system. It is triggered every time a position is closed.

### Data Flow

```
Position closed (sell order filled)
         │
         ▼
  Calculate net P&L
  (raw P&L − round-trip fees)
         │
         ├──► StrategyScoreboard.record_outcome()
         │    → Updates win/loss, P&L history for strategy
         │
         ├──► MarketMemory.record_outcome()
         │    → Stores conditions + result as memory
         │
         ├──► LosingStreak.record_outcome()
         │    → Updates streak counter, triggers loss analysis
         │
         ├──► AdaptiveExitLevels.record_exit()
         │    → Updates SL/TP calibration data
         │
         ├──► AIAccuracyTracker.record_outcome()
         │    → Scores AI prediction vs actual result
         │
         └──► TimeOfDayProfiler.record_outcome()
              → Updates hour-of-day performance
```

### State Persistence

All learning module state is persisted to the `/data/` directory as JSON files, surviving restarts:

```
/data/
├── strategy_scores.json      # StrategyScoreboard state
├── market_memory.json        # MarketMemory entries (500 max)
├── adaptive_exits.json       # Exit level history (200 max)
├── ai_accuracy.json          # AI prediction accuracy
├── time_profiler.json        # Hourly outcome data
└── correlation_map.json      # Updated correlation estimates
```

### Score Decay

To prevent stale data from influencing current decisions, scores decay toward neutral:

```python
# Applied on each scoreboard read
days_since_last_trade = (now - strategy.last_trade_at).days
if days_since_last_trade > 7:
    decay_factor = 0.95 ** (days_since_last_trade - 7)  # 5% decay per day
    strategy.score = 0.5 + (strategy.score - 0.5) * decay_factor
```

---

## 11. Alerting System

Source: `backend/app/services/alerting.py`

### Alert Plugins (4)

| Plugin | Description | Configuration |
|--------|-------------|--------------|
| In-App | Stores to `system_alerts` DB table, shown in UI | Always active |
| Console | Logs to Python logger (visible in terminal/CloudWatch) | Always active |
| Email (SMTP) | Sends email via configured SMTP server | Requires SMTP config |
| Webhook | HTTP POST to any URL (Slack, Teams, Discord, PagerDuty) | Requires webhook URL |

### Alert Severity Levels

| Level | Colour | Use Cases |
|-------|--------|----------|
| `critical` | Red | Kill switch triggered, liquidation risk, margin call |
| `high` | Orange | Max drawdown breached, 5+ consecutive losses, daily loss limit |
| `medium` | Yellow | Risk limit warnings, strategy performance degradation |
| `low` | Blue | Trade executed, regime change, daily summary |

### Rate Limiting

Alerts are rate-limited per category to prevent notification spam:
- Minimum 5-minute cooldown per alert category
- Critical alerts bypass cooldown (always sent)
- Daily digest mode: low-severity alerts batched into one daily email

### Price Alerts

User-configured price alerts trigger via the `/api/alerts` router:
```python
# Alert fires when:
if condition == "above" and current_price >= target_price:
    alert_manager.fire(severity="medium", message=f"{symbol} crossed above ${target_price}")
elif condition == "below" and current_price <= target_price:
    alert_manager.fire(severity="medium", message=f"{symbol} dropped below ${target_price}")
```

---

## 12. Geopolitical Risk & Sentiment Intelligence (7 modules)

Source: `backend/app/services/geo_risk/` (7 files)

The Geopolitical Risk module monitors real-time global news and events, classifies them into 14 event types, scores their impact per asset class, and feeds risk levels into the Execution Trust Layer. It uses free data sources (GDELT DOC 2.0 API + RSS feeds) with zero API costs.

### 12.1 GeoEventClassifier

**File:** `services/geo_risk/classifier.py` → class `GeoEventClassifier`

Fast, deterministic keyword-based geopolitical event classification. Each article is scored against 14 event type keyword dictionaries (10–30+ weighted keywords per type).

**14 event types:**

| Category | Event Types | Half-Life |
|----------|-----------|-----------|
| Acute (fast decay) | MILITARY_CONFLICT, TERRORISM, CYBER_ATTACK, NATURAL_DISASTER, CIVIL_UNREST | 24 hours |
| Structural (slow decay) | SANCTIONS, TRADE_WAR, ELECTION, DIPLOMATIC_CRISIS, REGULATORY_CHANGE, ENERGY_CRISIS, REPUTATION_EVENT, COMMODITY_DISRUPTION, CURRENCY_CRISIS | 168 hours (7 days) |

**Region detection:** 5 geographic regions — Middle East, US/China, Europe, Russia/Ukraine, Asia Pacific.

**Classification output:**
```python
{
    "event_type": "MILITARY_CONFLICT",
    "secondary_types": ["ENERGY_CRISIS"],
    "confidence": 0.82,
    "severity": 0.75,
    "regions": ["middle_east"],
    "tone_score": -0.6
}
```

**Minimum confidence threshold:** 0.3 — articles below this are discarded.

---

### 12.2 GeoImpactMatrix

**File:** `services/geo_risk/impact_matrix.py`

A 14×4 matrix mapping each event type to its expected impact on equities, crypto, forex, and commodities. Each cell contains direction (bearish/bullish/neutral/varies), magnitude (0–1), affected sectors, safe havens, and risk currencies.

**Sample matrix entries:**

| Event Type | Equities | Crypto | Forex | Commodities |
|-----------|----------|--------|-------|-------------|
| MILITARY_CONFLICT | Bearish (0.8) | Bullish (0.5) | Varies | Bullish (0.9) |
| SANCTIONS | Bearish (0.6) | Bullish (0.4) | Bearish (0.5) | Bullish (0.7) |
| ENERGY_CRISIS | Bearish (0.7) | Bearish (0.4) | Varies | Bullish (0.9) |
| NATURAL_DISASTER | Bearish (0.5) | Neutral (0.2) | Varies | Bullish (0.6) |
| TRADE_WAR | Bearish (0.7) | Bullish (0.4) | Bearish (0.6) | Bullish (0.5) |

The matrix is updatable at runtime via the `PUT /api/v1/geo-risk/impact-matrix` endpoint.

---

### 12.3 GeoRiskScorer & AssetImpactScorer

**File:** `services/geo_risk/scorer.py`

**AssetImpactScorer** maps a single event to per-asset impacts using:
- **Recency decay:** Exponential decay with half-lives (acute=24h, structural=168h)
- **Geographic amplifier:** Key region/asset pairs amplified 1.2×–1.8× (e.g., Middle East + commodities_oil = 1.5×, US/China + forex = 1.5×)
- **Confidence weighting:** Event classifier confidence applied

**GeoRiskScorer** aggregates across all active events for a composite score:

```python
score = scorer.score_asset("BTC/USDT", "crypto")
# Returns:
{
    "geo_risk_score": 0.45,          # 0–1 aggregated downside risk
    "geo_opportunity_score": 0.30,   # 0–1 aggregated upside potential
    "net_signal": -0.15,             # −1 to +1 (negative = net risk)
    "signal_strength": "moderate",   # weak/moderate/strong/extreme
    "recommended_action": "hedge",   # reduce_exposure/hedge/hold/increase_exposure
    "position_size_modifier": 0.7,   # 0.2–1.2×
    "confidence": 0.65,
    "dominant_events": ["SANCTIONS", "TRADE_WAR"],
    "sources_analyzed": 42
}
```

**Risk thresholds:** low=0.3, moderate=0.5, high=0.7, extreme=0.85

**Position size modifier:** 0.2× at extreme risk, 1.0× at no risk, up to 1.2× at high opportunity.

---

### 12.4 GeoNewsIngester

**File:** `services/geo_risk/ingester.py` → class `GeoNewsIngester`

Ingests news from two free data sources:

**GDELT DOC 2.0 API** (polled every 15 minutes):
- Queries across 7 curated geopolitical themes
- Max 250 records per query
- Supports article list, timeline tone, and timeline volume modes
- No API key required

**RSS Feeds** (polled every 5 minutes):
- Reuters World News
- BBC World News
- Al Jazeera
- Max 50 entries per feed per poll

Both sources are cached with TTLs matching their poll intervals to avoid redundant requests.

---

### 12.5 GeoMonitor

**File:** `services/geo_risk/monitor.py` → class `GeoMonitor`

The central orchestrator that ties all components together. Runs as a background service with async lifecycle management.

**Key responsibilities:**
- Polls GDELT (every 15min) and RSS (every 5min) via the ingester
- Classifies all fetched articles via the classifier
- Maintains a rolling 30-day event window (max 500 events)
- Exposes query methods for events, scores, timelines, and heatmaps
- Provides `get_news_risk_level()` for trust layer integration
- Manages user-configured geo alerts

**Global singleton:** `geo_monitor` instance, available to all services.

---

### 12.6 GeoAlertManager

**File:** `services/geo_risk/monitor.py` (integrated into GeoMonitor)

Users can configure alerts that trigger when geopolitical risk crosses thresholds for specific asset classes or event types.

```python
alert = {
    "asset_class": "commodities",
    "event_types": ["MILITARY_CONFLICT", "ENERGY_CRISIS"],
    "threshold": 0.7,
    "description": "Alert on high commodity risk from conflict or energy crisis"
}
```

---

### 12.7 Trust Layer Integration

The GeoMonitor feeds directly into the ExecutionTrustScorer's News Safety component via `get_news_risk_level()`:

| Risk Level | News Safety Score | Position Impact |
|-----------|-------------------|-----------------|
| `none` | 1.0 | Full confidence |
| `low` | 0.8 | Minor reduction |
| `medium` | 0.5 | Significant caution |
| `high` | 0.1 | Near-block |

The trust scorer's API (`/api/trust-score/evaluate`) checks the geo monitor before every evaluation. When geopolitical risk is elevated, the News Safety component score drops, which lowers the overall trust score and can reduce position size or block trades entirely.

**Config:** Trust layer weight = 10% (news_safety), high risk block threshold = 0.8, opportunity boost threshold = 0.7.

---

## 13. Execution Trust Layer

The Execution Trust Layer is the unified confidence scoring system that replaces fragmented trade gates. It consumes ALL signal sources and produces a single composite trust score.

### ExecutionTrustScorer

The main engine evaluates 10 signal dimensions with asset-specific weight profiles:

1. **Signal Strength** — Direct strategy confidence (0-1)
2. **Timeframe Agreement** — MTF consensus level (0=none, 0.33=1/3, 0.67=2/3, 1.0=3/3)
3. **Regime Confidence** — Market regime detection confidence, penalized if direction conflicts
4. **Sentiment Alignment** — Whether market sentiment supports the trade direction
5. **Strategy Track Record** — Win rate from scoreboard (neutral 0.5 if <5 trades)
6. **Spread Quality** — Current spread vs average (1.0=normal, 2.0+=dangerous)
7. **Data Freshness** — Age of latest OHLCV candle (<60s=1.0, >15min=0.2)
8. **Venue Quality** — Per-exchange execution quality from VenueQualityTracker
9. **News Safety** — Proximity and severity of upcoming news events
10. **Risk Headroom** — Distance from max drawdown limit

### VenueQualityTracker

Tracks per-exchange execution quality over a rolling window of 100 trades:
- Fill rate (% of orders that execute)
- Average slippage (expected vs actual fill price)
- Success rate (% without errors)
- New exchanges start at 0.7 score until enough data accumulates (5+ trades)

### TrustScoreHistory

Records every trust evaluation and correlates with trade outcomes:
- Groups results by grade (A/B/C/D/F)
- Tracks average P&L and win rate per grade
- Answers: “Do high-trust trades actually perform better?”
- Max 1000 entries in rolling window

### Asset-Specific Weights

Each asset class has a different weight profile reflecting what matters most:
- **Crypto**: Sentiment (15%) and news (10%) weighted high — crypto is sentiment-driven
- **Forex**: MTF agreement (15%) and spread quality (10%) weighted high — technical and cost-sensitive
- **Stocks**: Track record (15%) and risk headroom (15%) weighted high — capital preservation
- **Indices**: Regime confidence (15%) weighted high — indices are macro-driven
- **Commodities**: Sentiment (15%) and news (12%) weighted high — supply/demand/geopolitical
- **Spread Betting**: Spread quality (12%) and venue quality (8%) elevated — execution costs matter with leverage

---

*Intelligence document generated from codebase audit — April 2026.*
