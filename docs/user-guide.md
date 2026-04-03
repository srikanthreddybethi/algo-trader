# AlgoTrader — User Guide

> **Last updated:** March 2026  
> This guide covers every feature available in the current codebase.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard](#2-dashboard)
3. [Smart Trading](#3-smart-trading)
4. [Trading](#4-trading)
5. [Exchanges](#5-exchanges)
6. [Auto-Trader](#6-auto-trader)
7. [Strategies (16 total)](#7-strategies-16-total)
8. [Signals & AI](#8-signals--ai)
9. [Spread Betting](#9-spread-betting)
10. [Backtesting](#10-backtesting)
11. [Analytics](#11-analytics)
12. [Optimizer](#12-optimizer)
13. [Alerts & System Alerts](#13-alerts--system-alerts)
14. [Settings](#14-settings)
15. [Geo Risk](#15-geo-risk)
16. [Trust Score](#16-trust-score)
17. [UK Tax Information](#17-uk-tax-information)
18. [Deployment Guide](#18-deployment-guide)
19. [FAQ](#19-faq)
20. [Glossary](#20-glossary)

---

## 1. Getting Started

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10, macOS 12, Ubuntu 20.04 | Windows 11, macOS 14, Ubuntu 22.04 |
| RAM | 2 GB | 4 GB |
| Storage | 500 MB | 2 GB |
| Python | 3.11 | 3.11 |
| Node.js | 18 | 20 |
| Internet | Required | Stable broadband |

### Installation — Local Development

```bash
# 1. Clone the repository
git clone <repo-url> algo-trader
cd algo-trader

# 2. Set up the backend
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Start the backend
uvicorn app.main:app --reload --port 8000

# 4. Open a new terminal for the frontend
cd frontend/client
npm install
npm run dev
```

The app opens at **http://localhost:5173**. The backend API runs at **http://localhost:8000**.

### Installation — Docker

```bash
# Build and run with Docker Compose
docker compose up --build

# App available at http://localhost:5173
# API available at http://localhost:8000
```

### First-Time Setup

When you open AlgoTrader for the first time:

1. **Paper trading is active by default** — you start with a virtual portfolio worth **$10,000**. No real money is at risk until you explicitly connect a live exchange and switch the Auto-Trader to live mode.

2. **No API keys are required** to explore the platform. You can browse all screens, run backtests, view signals, and simulate trades without any exchange credentials.

3. **To connect your first exchange**, navigate to the **Exchanges** page from the sidebar and enter your API keys. Start with a testnet/paper account to test the integration safely.

4. **To enable AI features**, go to **Settings → AI Configuration** and enter a Claude (Anthropic) or Gemini (Google) API key. AI features fall back gracefully to rule-based logic if no key is set.

### Connecting Your First Exchange

1. Open **Exchanges** in the sidebar
2. Click **Add Exchange** or select an exchange from the list
3. Enter your API key and secret (and any extra fields like passphrase for OKX)
4. Click **Test Connection** — a green tick confirms the credentials work
5. Optionally enable **Testnet** mode to use the exchange's paper trading environment

---

## 2. Dashboard

The Dashboard is your home page — an at-a-glance view of your entire portfolio.

### Portfolio Summary Card

| Field | Description |
|-------|-------------|
| Total Value | Current portfolio value (cash + open positions) |
| Cash Available | Uninvested cash ready to deploy |
| Total P&L | Lifetime profit or loss since portfolio creation |
| Daily P&L | Today's change in portfolio value |
| Open Positions | Number of currently active trades |

### Intelligence Status Card

Shows the health of the 5 core intelligence modules:
- **Strategy Scoreboard** — which strategies are scoring well today
- **Market Memory** — number of relevant historical memories found
- **Correlation Guard** — current portfolio correlation level
- **Kelly Sizing** — current recommended position size %
- **Multi-Timeframe** — how many recent signals passed the consensus check

### Recent Decisions Card

A live feed of the last 30 auto-trader decisions (buy, sell, block, risk check, etc.). Each decision includes timestamp, symbol, reasoning, and which pipeline step made it. This is your transparency window into the autonomous system.

### Quick Action Buttons

- **Run Once** — trigger one auto-trader cycle immediately
- **Start Auto-Trader** — begin continuous autonomous trading
- **Reset Portfolio** — wipe paper portfolio back to $10,000 (confirmation required)

### Portfolio Value Chart

A time-series chart showing portfolio value from inception. The x-axis shows proper UTC timestamps. Hover over any point to see the exact value at that moment. The chart uses portfolio snapshots taken after each trade.

### Risk Metrics

| Metric | Description |
|--------|-------------|
| Annualised Volatility | Rolling standard deviation of returns, annualised |
| Max Drawdown | Largest peak-to-trough decline in portfolio history |
| Value at Risk (VaR 95%) | Estimated maximum loss on a typical day (95th percentile) |
| Diversification Score | How spread your positions are across uncorrelated assets |
| Sharpe Ratio | Risk-adjusted return (return above risk-free rate / volatility) |

### Recent Trades and Active Positions

Two tables at the bottom of the dashboard:
- **Recent Trades** — last 20 completed trades with symbol, side, price, P&L
- **Active Positions** — all currently open positions with unrealised P&L

---

## 3. Smart Trading

**Path:** `/smart-trading` | **Icon:** Crosshair

Smart Trading is the adaptive analysis page. Type any symbol in the search box — the page automatically detects the asset class and reconfigures all panels to show the most relevant information.

### How to Use It

1. Type a symbol in the search bar (e.g. `BTC`, `EUR/USD`, `AAPL`, `FTSE`, `GOLD`)
2. The page detects whether it's crypto, forex, stock, index, or commodity
3. All panels below update automatically

### Asset Intelligence Section

This section changes content based on the detected asset class:

**For Crypto:**
- Fear & Greed Index (0–100)
- BTC Dominance %
- Social Sentiment (bullish %)
- Exchange inflows/outflows

**For Forex:**
- Active trading session (Sydney/Tokyo/London/New York)
- Economic calendar (next high-impact event)
- Retail trader positioning (% long vs short)
- Interest rate differential for carry trades

**For Stocks:**
- Next earnings date
- P/E ratio vs sector average
- Sector rotation indicator
- Short interest %

**For Indices:**
- VIX level (fear gauge)
- Market breadth (% stocks above 200-day MA)
- Put/Call ratio

**For Commodities:**
- Seasonal bias indicator
- Supply/demand imbalance
- Geopolitical risk level

### Trade Validation Panel

Enter a direction (Buy or Sell) and click **Validate**. The system runs the asset-specific rules engine and returns:
- **Approved / Blocked** status
- List of warnings (e.g. "Earnings in 2 days — reduced size", "London session not active")
- Recommended position size multiplier

### Optimal Strategies Panel

Select a market regime (trending up, trending down, ranging, volatile) and the panel shows the optimal strategy ranked list for this specific asset class in this regime, with a brief explanation of why each strategy is recommended.

### Market Status

Shows whether the market is:
- Currently open or closed
- The next open/close time (UTC)
- Any scheduled events (FOMC, NFP, earnings) in the next 24 hours

### Spread Betting Panel

Appears automatically when a symbol that is tradeable via spread betting is detected. Shows:
- Estimated £/point stake for your current balance
- Margin requirement
- Daily overnight funding cost
- Whether a guaranteed stop is recommended

---

## 4. Trading

**Path:** `/trading` | **Icon:** Line Chart

The Trading page provides manual order execution with a full charting interface.

### Candlestick Chart

Powered by the TradingView widget. Supports:
- All major timeframes (1m to 1W)
- Drawing tools (trend lines, Fibonacci retracements, etc.)
- Technical indicators (MA, RSI, MACD, Bollinger Bands within the chart)

### Exchange and Symbol Selection

- Select any connected exchange from the dropdown
- Type any symbol supported by that exchange
- The chart and order book update automatically

### Order Types

| Order Type | Description |
|------------|-------------|
| Market | Execute immediately at current price |
| Limit | Set a specific price — executes only when market reaches it |

### Placing a Manual Order

1. Select your exchange from the dropdown
2. Type the symbol (e.g. `BTC/USDT`)
3. Choose **Buy** or **Sell**
4. Enter the **quantity** (in base currency units) or **value** (USD equivalent)
5. Select **Market** or **Limit** order type
6. For limit orders, enter your target price
7. Click **Place Order** — the order appears in your Open Orders table

### Order Book

The order book (bid/ask ladder) is displayed when the exchange provides this data. It shows current buy and sell pressure at different price levels.

### Open Orders

A table below the chart shows all pending orders (limit orders waiting to fill). You can cancel any unfilled order by clicking the X button.

---

## 5. Exchanges

**Path:** `/exchanges` | **Icon:** Globe

AlgoTrader supports **18 exchanges** across 5 categories. Connect as many as you like — the Auto-Trader can be pointed at any connected exchange.

### 5.1 Crypto Exchanges (9)

These exchanges use the CCXT library for a standardised interface.

| Exchange | FCA Status | Taker Fee | Key Strength | Testnet |
|----------|-----------|-----------|-------------|---------|
| **Binance** | Not FCA regulated | 0.10% | Largest volume, most pairs | Yes |
| **Bybit** | FCA-approved (via Archax) | 0.10% | Perpetuals, good API | Yes |
| **Kraken** | FCA-registered + EMI | 0.26% | Best UK option, GBP pairs | No |
| **Coinbase** | FCA-registered | 0.60% | Most trusted, easiest KYC | No |
| **OKX** | Not FCA regulated | 0.08% | Lowest fees, deep liquidity | No |
| **Crypto.com** | Not FCA regulated | 0.075% | Good mobile + API | No |
| **Bitstamp** | FCA-registered | 0.40% | Oldest EU exchange | No |
| **Gate.io** | Not FCA regulated | 0.10% | Wide altcoin selection | No |
| **Gemini** | Not FCA regulated | 0.35% | US-focused, secure | No |

**How to get API keys (Binance example):**
1. Log in to binance.com → Account → API Management
2. Create a new API key with "Enable Reading" and "Enable Spot & Margin Trading" permissions
3. Do NOT enable withdrawal permissions for trading bots
4. Copy the API key and secret immediately (secret shown only once)
5. Add the IP restriction to your server's IP for extra security

**Testnet setup (Binance):**
1. Register at testnet.binance.vision
2. Generate test API keys there
3. Enable "Testnet" toggle in AlgoTrader's exchange settings

---

### 5.2 Spread Betting (3) — Tax-Free in the UK

Spread betting profits are completely free from UK Capital Gains Tax and Stamp Duty. These three brokers are all FCA-authorised.

#### IG Group

- **Type:** Spread betting + CFDs
- **Instruments:** 17,000+ markets (forex, indices, shares, crypto, commodities)
- **Minimum stake:** £50
- **API:** REST API + Lightstreamer real-time pricing
- **How to connect:** IG API → My Account → API credentials → Create key
- **FCA authorised:** Yes (firm reference 195355)

#### Capital.com

- **Type:** Spread betting + CFDs
- **Instruments:** 3,000+ markets
- **Minimum stake:** £20
- **API:** REST API with session-based authentication
- **How to connect:** Capital.com platform → Settings → API Access → Create key
- **FCA authorised:** Yes

#### CMC Markets

- **Type:** Spread betting + CFDs
- **Instruments:** 12,000+ markets
- **Minimum stake:** £20
- **API:** REST API with market-maker pricing
- **How to connect:** CMC Markets platform → My Account → API Settings
- **FCA authorised:** Yes (firm reference 173730)

---

### 5.3 Stock Brokers (2)

#### Alpaca

- **Type:** Commission-free US stocks, ETFs, options, crypto
- **Commission:** Free
- **Minimum order:** $1
- **API:** REST + WebSocket (well-documented)
- **Paper account:** Built-in paper trading account (separate from live)
- **How to connect:** alpaca.markets → Dashboard → Paper Account → API Keys
- **FCA authorised:** No (US-based, SEC-registered)

#### Trading 212

- **Type:** Commission-free stocks, ETFs, fractional shares (UK-focused)
- **Commission:** Free
- **Minimum order:** £1
- **API:** REST API (requires API key from Trading 212 platform)
- **How to connect:** Trading 212 app → Settings → API → Generate Key
- **FCA authorised:** Yes (firm reference 609146)

---

### 5.4 Forex (1)

#### OANDA

- **Type:** Forex and CFDs
- **Commission:** Spread-based (~0.03% effective)
- **Minimum order:** $1 (micro-lots)
- **API:** v20 REST API with bearer token authentication
- **How to connect:** OANDA account → Manage Funds → API Access → Generate Token
- **FCA authorised:** Yes
- **Best for:** Retail forex traders, tight spreads on majors, excellent API documentation

---

### 5.5 Multi-Asset (3)

#### Interactive Brokers (IBKR)

- **Type:** Stocks, options, futures, forex, bonds (global)
- **Commission:** ~0.05% (tiered pricing)
- **Minimum order:** $100 equivalent
- **API:** Client Portal Web API (requires IBKR Gateway running locally)
- **How to connect:** IBKR Portal → Settings → API → Enable Client Portal API
- **FCA authorised:** Yes

#### eToro

- **Type:** Social trading — stocks, crypto, commodities, forex
- **Commission:** ~1% spread on most instruments
- **Minimum order:** $50
- **API:** REST API with OAuth2 authentication
- **How to connect:** eToro developer portal → Create application → Get client credentials
- **FCA authorised:** Yes

#### Saxo Bank

- **Type:** Professional-grade equities, options, futures, forex
- **Commission:** ~0.10% (equity), ~0.08% (forex)
- **Minimum order:** $100 equivalent
- **API:** SaxoOpenAPI (OAuth2)
- **How to connect:** Saxo developer account → Create app → Get OAuth2 credentials
- **FCA authorised:** Yes

---

## 6. Auto-Trader

**Path:** `/auto-trader` | **Icon:** Bot

The Auto-Trader is AlgoTrader's autonomous trading engine. When running, it continuously analyses markets and executes trades based on the configured strategy and risk parameters — without manual intervention.

### How It Works (10-Step Pipeline)

Each cycle, for every symbol on your watchlist:

| Step | Name | What Happens |
|------|------|-------------|
| 1 | Losing streak check | Reduces position size if you've had 2+ consecutive losses |
| 2 | Adaptive exit update | Recalibrates stop-loss / take-profit based on recent history |
| 3 | Position management | Checks all open positions for stop, take-profit, or trailing stop triggers |
| 4 | Smart exit intelligence | AI advises whether to hold, sell, or add to positions |
| 5 | Data gathering | Fetches signals, regime, AI analysis, and news for each symbol |
| 6 | Portfolio risk check | Verifies drawdown, exposure, and position count limits |
| 7 | Asset-specific validation | Applies rules for this asset class (session, earnings, VIX, etc.) |
| 8 | Strategy selection | Picks optimal strategy for asset + regime, adjusted by live performance |
| 9 | Intelligence pipeline | 5 pre-trade checks: scoring, multi-timeframe, correlation, Kelly, memory |
| 10 | Sizing + execution | Fee-aware position sizing, order placement, and feedback loop |

### Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| Exchange | Which exchange to trade on | — |
| Symbols | Comma-separated list (e.g. BTC/USDT, ETH/USDT) | — |
| Max Drawdown % | Stop all trading if portfolio drops this much | 10% |
| Max Position % | Maximum single position as % of portfolio | 20% |
| Max Total Exposure % | Maximum total invested at once | 60% |
| Max Positions | Maximum simultaneous open positions | 5 |
| Stop Loss % | Default stop-loss (adaptive system overrides this) | 5% |
| Daily Loss Limit % | Maximum daily loss before halt | 3% |
| Cycle Interval | Seconds between trading cycles | 300 (5 min) |

### Paper vs Live Mode

- **Paper Mode** (default): All trades are simulated against your virtual $10,000 portfolio. No real money moves.
- **Live Mode**: Trades are placed as real orders on the connected exchange. Only available if exchange is connected with trading-enabled API keys.

**To switch to live mode:** Settings page → Trading Defaults → toggle "Live Trading". A confirmation dialog explains the risks.

### Run Once vs Start (Continuous)

- **Run Once**: Executes one full pipeline cycle and stops. Useful for testing your configuration before letting it run continuously.
- **Start**: Begins continuous loop. The orchestrator runs every `cycle_interval` seconds until you click Stop or the kill switch triggers.

### Decision Log

Every decision made by the auto-trader is logged with full detail. There are 30 decision types:

| Decision Type | Description |
|--------------|-------------|
| `trade_executed` | A buy or sell order was placed |
| `no_signal` | No strategy generated a signal for this symbol |
| `risk_block` | Portfolio risk limits prevented trading |
| `intelligence_block` | One of the 5 intelligence modules blocked the trade |
| `not_worth_trading` | Trade worthiness filter rejected (fees > expected profit) |
| `position_stopped` | Stop-loss triggered, position closed |
| `position_tp` | Take-profit level hit, position closed |
| `trailing_stop` | Trailing stop triggered, position closed |
| `smart_exit` | AI advised exit, position closed |
| `strategy_sell_exit` | Strategy generated SELL signal on existing position |
| `duplicate_blocked` | Already holding this symbol, blocked duplicate buy |
| `news_halt` | AI assessed breaking news as too risky |
| `news_caution` | Strongly bearish news — position size reduced 25% |
| `contrarian_sentiment` | Extreme fear — contrarian buy boost |
| `extreme_greed` | Fear & Greed ≥ 90 — size reduced 25% |
| `losing_streak` | Consecutive losses detected — position size reduced |
| `loss_analysis` | AI identified root cause of losing streak |
| `asset_block` | Asset-specific rules blocked the trade |
| `asset_reduce` | Asset-specific rules reduced position size |
| `correlation_block` | Portfolio too correlated to add this position |
| `correlation_reduce` | Correlation warning — size reduced |
| `kelly_sizing` | Kelly Criterion set position size |
| `memory_block` | Market memory blocked trade (historically poor setup) |
| `memory_boost` | Market memory boosted size (historically strong setup) |
| `mtf_block` | Multi-timeframe consensus blocked (timeframes disagree) |
| `sb_sized` | Spread bet stake per point calculated |
| `sb_rejected` | Spread bet sizing rejected (insufficient margin or closed market) |
| `size_too_small` | Position value below exchange minimum order size |
| `skip_sell` | Sell signal received but no open position to close |
| `cycle_complete` | Full cycle finished — all symbols processed |

### Kill Switch

The **Kill Switch** button immediately halts all autonomous trading and prevents any new orders from being placed. The state persists until you manually deactivate it. Use this if market conditions are extreme or you need to pause for any reason.

---

## 7. Strategies (16 total)

All 16 strategies are available for manual selection in backtesting and can be recommended by the Auto-Trader based on market conditions.

### 7.1 Quantitative Strategies (11)

---

#### 1. SMA Crossover
**What it does:** Buys when a short-term Simple Moving Average crosses above a long-term SMA. Sells when it crosses below.

**When it works best:** Trending markets with clear directional moves. Struggles in sideways markets (produces many false crossovers).

**Key parameters:**
- `short_window` (default: 20) — period of the fast SMA
- `long_window` (default: 50) — period of the slow SMA

**Risk level:** Medium. Simple and robust, but slow to react to reversals.

---

#### 2. EMA Crossover
**What it does:** Same logic as SMA Crossover, but uses Exponential Moving Averages that weight recent prices more heavily.

**When it works best:** Trending markets. More reactive than SMA — catches moves earlier but also produces more false signals.

**Key parameters:**
- `short_window` (default: 9)
- `long_window` (default: 21)

**Risk level:** Medium. Good for crypto and forex in trending regimes.

---

#### 3. RSI (Relative Strength Index)
**What it does:** Buys when an asset is "oversold" (RSI falls below threshold) and sells when "overbought" (RSI rises above threshold).

**When it works best:** Ranging, sideways markets. In strong trends it can stay oversold/overbought for extended periods.

**Key parameters:**
- `period` (default: 14) — lookback window
- `oversold` (default: 30) — buy trigger level
- `overbought` (default: 70) — sell trigger level

**Risk level:** Low–Medium. Classic indicator, well-understood behaviour.

---

#### 4. MACD
**What it does:** Generates signals from the crossover between the MACD line (fast EMA minus slow EMA) and a signal line (EMA of MACD).

**When it works best:** Trending markets, good at identifying the start of new trends. Also provides histogram for momentum visualisation.

**Key parameters:**
- `fast` (default: 12) — fast EMA period
- `slow` (default: 26) — slow EMA period
- `signal` (default: 9) — signal line period

**Risk level:** Medium. Standard momentum indicator used by professionals globally.

---

#### 5. Bollinger Bands
**What it does:** Calculates a moving average with upper and lower bands at 2 standard deviations. Buys when price touches/crosses the lower band (oversold), sells at upper band.

**When it works best:** Range-bound markets with clear support/resistance. Also useful as a volatility gauge — bands widen in volatile conditions.

**Key parameters:**
- `window` (default: 20) — MA period
- `std_dev` (default: 2.0) — standard deviation multiplier

**Risk level:** Low–Medium. One of the most widely used indicators.

---

#### 6. Mean Reversion
**What it does:** Statistically identifies when a price has deviated significantly from its historical mean (Z-score approach) and bets on reversion to that mean.

**When it works best:** Sideways, range-bound markets where assets regularly oscillate around a stable price level.

**Key parameters:**
- `window` (default: 20) — mean calculation window
- `std_dev` (default: 2.5) — Z-score threshold for signal

**Risk level:** Medium. Can lose significantly if a trend continues rather than reverting.

---

#### 7. Momentum
**What it does:** Buys assets that have been rising strongly (positive momentum) and sells those that have been falling. Based on the principle that "assets in motion tend to stay in motion."

**When it works best:** Strong trending markets, especially in crypto where momentum effects are pronounced.

**Key parameters:**
- `lookback` (default: 14) — momentum measurement period
- `threshold` (default: 0.03) — minimum % move to qualify as momentum

**Risk level:** Medium–High. Works brilliantly in trends, can suffer sharp reversals at tops.

---

#### 8. VWAP (Volume-Weighted Average Price)
**What it does:** Trades mean reversion around the Volume-Weighted Average Price — the true "fair value" price weighting volume at each level.

**When it works best:** Intraday trading on liquid assets. Particularly useful for institutional-grade entry/exit timing. Less useful on illiquid assets or over longer timeframes.

**Key parameters:**
- `deviation` (default: 0.5) — % deviation from VWAP to trigger signal

**Risk level:** Low–Medium. VWAP is a reference price used by professional traders.

---

#### 9. DCA (Dollar-Cost Averaging)
**What it does:** Systematically buys a fixed amount at regular intervals, regardless of price direction. Builds a position over time, averaging out the entry price.

**When it works best:** Accumulation in downtrending or ranging markets where you want to build a long-term position without trying to time the bottom.

**Key parameters:**
- `interval_bars` (default: 12) — how many candles between purchases
- `amount_pct` (default: 3) — % of portfolio to buy each time

**Risk level:** Low. Most conservative strategy — never tries to predict direction.

---

#### 10. Grid Trading
**What it does:** Places a series of buy orders below the current price and sell orders above, in a grid pattern. Profits from price oscillation within the grid.

**When it works best:** Range-bound markets with regular up-and-down oscillation. Can be configured as a one-sided accumulation grid for trending markets.

**Key parameters:**
- `grid_size` (default: 10) — number of grid levels
- `grid_spacing` (default: 1.5) — % distance between levels

**Risk level:** Medium. Loses if price trends strongly in one direction without oscillating.

---

#### 11. Pure AI
**What it does:** Delegates signal generation entirely to Claude or Gemini. The AI analyses current market data, news, regime, and sentiment — and decides whether to buy, sell, or hold with a confidence score.

**When it works best:** Complex market conditions where multiple indicators conflict. The AI can weigh context that rule-based strategies cannot.

**Key parameters:**
- `aggression` (default: moderate) — how bold the AI should be (conservative / moderate / aggressive)

**Risk level:** Variable — depends on market conditions and AI quality. Requires API key.

---

### 7.2 Spread Betting Strategies (5)

These strategies are designed specifically for spread betting. They size positions in £/point, use ATR-based stops instead of fixed percentages, and include market-hours awareness.

---

#### 12. SB Trend Rider
**What it does:** Identifies strong directional trends using EMA crossovers and ADX confirmation. Enters with a 1.5× ATR trailing stop that ratchets up as the trend develops.

**When it works best:** Trending indices and major forex pairs (EUR/USD, GBP/USD) during the London or New York session.

**Stop method:** 1.5× ATR trailing stop — protects profits as the trend matures.

**Typical hold:** Hours to days.

**Risk level:** Medium.

---

#### 13. SB Mean Reversion
**What it does:** Uses Bollinger Band extremes combined with RSI to identify overextended moves in forex ranges. Fades the move with a fixed 2× ATR stop.

**When it works best:** Range-bound forex pairs, particularly during thin Asian session hours.

**Stop method:** 2× ATR fixed (not trailing — assumes reversion happens quickly).

**Typical hold:** Hours.

**Risk level:** Medium.

---

#### 14. SB Momentum Scalper
**What it does:** Uses ADX to confirm strong directional momentum, then enters aggressively on the continuation. Designed for fast, short-duration trades.

**When it works best:** Volatile session opens (London open 08:00 UTC, NY open 14:30 UTC). Requires ADX > 25 to filter weak momentum.

**Stop method:** 1× ATR tight stop.

**Typical hold:** Minutes to hours.

**Risk level:** High. Fast exits required — not suitable for inattentive traders.

---

#### 15. SB Breakout (Guaranteed Stop)
**What it does:** Identifies consolidation ranges and enters on breakout with a guaranteed stop to prevent slippage in fast-moving markets.

**When it works best:** Around major economic announcements (NFP, FOMC, earnings) where price breaks out of a pre-event range.

**Stop method:** Guaranteed stop — absolute protection against gap risk. Premium of ~0.3% applies.

**Typical hold:** Hours.

**Risk level:** Medium — capped downside thanks to guaranteed stop.

---

#### 16. SB Index Surfer
**What it does:** Specifically designed for major stock indices (UK100, US500, GER40). Uses breadth indicators and session timing to ride intraday index trends.

**When it works best:** During exchange trading hours (LSE: 08:00–16:30, NYSE: 14:30–21:00). Works best on trending days confirmed by breadth.

**Stop method:** ATR-adjusted based on index volatility.

**Typical hold:** Intraday only.

**Risk level:** Medium.

---

## 8. Signals & AI

**Path:** `/signals` | **Icon:** Brain

The Signals & AI page gives you a real-time view of all market intelligence inputs.

### Fear & Greed Index

A 0–100 scale measuring crypto market sentiment:

| Score | Label | Implication |
|-------|-------|-------------|
| 0–10 | Extreme Fear | Strong contrarian buy signal |
| 11–25 | Fear | Cautious buying opportunity |
| 26–45 | Mild Fear | Neutral-to-cautious |
| 46–55 | Neutral | No strong signal |
| 56–75 | Greed | Caution — late trend |
| 76–90 | Strong Greed | Reduce new longs |
| 91–100 | Extreme Greed | Strong caution / look for shorts |

The Auto-Trader uses Fear & Greed as a position size modifier:
- ≤ 10 (extreme fear): +10% boost (contrarian)
- ≥ 90 (extreme greed): −25% reduction

### Social Sentiment

Aggregated bullish/bearish sentiment from social media and communities. Shows:
- Bullish % (e.g. 68% bulls)
- Bearish % (e.g. 32% bears)
- Trending keywords in discussion

### Market Regime Detection

The regime detector analyses OHLCV data and classifies the current market state:

| Regime | Characteristics | Best Strategies |
|--------|----------------|----------------|
| `trending_up` | Price above MAs, ADX > 20, strong momentum | Momentum, EMA Crossover, MACD |
| `trending_down` | Price below MAs, ADX > 20, downward momentum | DCA, Mean Reversion, RSI |
| `ranging` | Price oscillating in a band, low ADX | Grid Trading, Bollinger Bands, RSI |
| `volatile` | Large price swings, high ATR | DCA, Grid Trading (wider) |

The 1H and 4H regimes are checked: if they disagree, confidence is reduced by 30%.

### AI Analysis

The AI analysis panel shows Claude's or Gemini's current assessment of the market:
- **Sentiment**: Bullish / Bearish / Neutral
- **Risk Level**: Low / Medium / High
- **Confidence**: 0–100%
- **Key Reasoning**: Plain-language explanation of the AI's view
- **Provider**: Which AI model provided the analysis

When no AI key is configured, the panel shows rule-based analysis instead.

### News Feed

The most recent news headlines relevant to your watched assets. Headlines are scored automatically:
- Positive headlines shown in green
- Negative headlines shown in red
- Neutral in grey

Click any headline to see the full AI assessment of its market impact.

### Multi-Asset Awareness

If you're watching multiple assets, the Signals page shows a correlation matrix indicating how your current watchlist's assets move together. This feeds directly into the Correlation Guard intelligence module.

---

## 9. Spread Betting

**Path:** `/spread-betting` | **Icon:** £

A dedicated control centre for spread betting trades. All components on this page are tailored to UK-regulated spread betting mechanics.

### £/Point Calculator

Enter your inputs to calculate the optimal stake:

| Input | Description |
|-------|-------------|
| Symbol | The instrument (FTSE 100, EUR/USD, etc.) |
| Account Balance | Your available capital in £ |
| Risk % | % of balance to risk on this trade |
| Stop Distance | Distance to stop in points |
| Current Price | Current price of the instrument |

The calculator returns:
- **£/point stake**
- **Margin required** (varies by FCA asset class: 3.33%–50%)
- **Maximum loss** at stop distance
- **Guaranteed stop recommendation** (yes/no)
- **Approval status**

### Margin Monitor

Real-time dashboard showing:
- Total margin committed across all open SB positions
- Available margin remaining
- Utilisation bar (green → yellow → red as utilisation rises)
- Warning levels: caution at 50%, high at 70%, critical at 85%

### Market Hours & Gap Protection

A world clock showing the current status of all major markets:
- Which sessions are currently open
- Time to next open/close
- Gap risk level (low/medium/high/critical) for each instrument type

**Gap protection recommendations:**
- If you're holding a spread bet over the weekend, the system recommends a guaranteed stop to protect against Sunday gap opens
- If a high-impact event is scheduled in the next 4 hours, gap protection warning is shown

### Overnight Funding Calculator

Calculates the daily carry cost of holding spread bet positions:

```
Daily Funding = (Stake × Current Price × (SONIA + 2.5%)) / 365
```

Current benchmark rate: 4.5% SONIA + 2.5% broker markup = 7.0% annualised

**Example:**
- FTSE 100 at 8,200 points
- Stake: £5/point
- Notional: £41,000
- Daily cost: £41,000 × 7% / 365 = **£7.86/day**

### Tax Efficiency Router

Recommends whether to trade via spread bet or CFD based on your tax situation:
- **Spread Bet**: Tax-free profits (no CGT, no Stamp Duty) — recommended for most UK traders
- **CFD**: Taxable gains but losses can offset against other capital gains — useful if you have other realised losses to offset

See [Section 17](#17-uk-tax-information) for full UK tax details.

### Trade Simulator

Before placing any spread bet, simulate the trade to see:
- P&L at different price levels
- Break-even point (accounting for spread)
- Maximum loss (at guaranteed stop)
- Overnight funding accumulation over various holding periods (1 day, 1 week, 1 month)

### Spread Betting Strategies

All 5 SB strategies are available directly from the Spread Betting page:
- SB Trend Rider, SB Mean Reversion, SB Momentum Scalper, SB Breakout, SB Index Surfer
- Each can be run in paper mode via a manual "Run Strategy" button
- Backtesting is available for each strategy

---

## 10. Backtesting

**Path:** `/backtest` | **Icon:** Flask

Test any of the 16 strategies against historical data before deploying them.

### How to Run a Backtest

1. Select an **Exchange** and **Symbol** (historical data will be fetched)
2. Select a **Strategy** from the dropdown
3. Adjust strategy **Parameters** using the sliders
4. Set the **Date Range** (start and end date)
5. Set **Initial Capital** (default $10,000)
6. Set **Commission** (auto-populated from the exchange's real fee rate)
7. Click **Run Backtest**

Results appear within a few seconds.

### Interpreting Results

| Metric | Good | Acceptable | Poor |
|--------|------|-----------|------|
| Total Return | > 20% annually | 5–20% annually | < 5% |
| Win Rate | > 55% | 45–55% | < 45% |
| Sharpe Ratio | > 1.5 | 0.8–1.5 | < 0.8 |
| Max Drawdown | < 10% | 10–25% | > 25% |
| Profit Factor | > 1.5 | 1.1–1.5 | < 1.1 |

**Equity Curve:** The chart shows portfolio value over time. Look for:
- Smooth upward curve — consistent strategy
- Jagged curve with big drawdowns — unstable strategy
- Long flat periods — strategy inactive / missing signals

**Trade Distribution:** Histogram of individual trade P&Ls. A healthy distribution is slightly right-skewed (more small wins than losses, with occasional larger wins).

### Walk-Forward Validation

For a more realistic backtest, enable **Walk-Forward** mode. This splits your date range into rolling windows and validates that optimised parameters actually work out-of-sample — not just on the data they were tuned on.

---

## 11. Analytics

**Path:** `/analytics` | **Icon:** Chart Pie

Comprehensive performance tracking for your portfolio.

### Performance Metrics

| Metric | Description |
|--------|-------------|
| Total Return % | Portfolio growth from inception |
| Annualised Return | Normalised to a 1-year equivalent |
| Sharpe Ratio | Return per unit of risk |
| Sortino Ratio | Like Sharpe, but only penalises downside volatility |
| Calmar Ratio | Annual return / max drawdown |
| Win Rate | % of trades that closed in profit |
| Average Win | Average profit on winning trades |
| Average Loss | Average loss on losing trades |
| Profit Factor | Total wins / total losses |
| Expectancy | Expected P&L per trade |

### Risk Metrics

| Metric | Description |
|--------|-------------|
| Volatility (Ann.) | Annualised standard deviation of daily returns |
| Max Drawdown | Largest peak-to-trough drop |
| Current Drawdown | Distance from recent peak to now |
| VaR (95%) | Maximum likely daily loss (statistical) |
| Beta | Correlation with overall market |
| Diversification Score | How uncorrelated your positions are |

### Trade Analysis

- Best/worst performing strategy
- Best/worst performing symbol
- Average holding time per strategy
- Heatmap of returns by hour of day and day of week

### Intelligence Status

Live snapshot of all 42 intelligence modules:
- Current scores per strategy (StrategyScoreboard)
- Market memory size and recent hit rate
- AI accuracy % (last 30 predictions)
- Walk-forward validation status (pass/fail per strategy)

### Adaptive Status

Shows all adaptive module states:
- Current adaptive SL/TP levels (vs defaults)
- Discovered symbols being monitored
- Current trading frequency setting
- Best/worst performing hours

---

## 12. Optimizer

**Path:** `/optimizer` | **Icon:** CPU

The Optimizer helps you find the best strategy parameters and understand which strategies are working.

### Strategy Rankings

A live ranked table of all 16 strategies by composite performance score:

| Column | Description |
|--------|-------------|
| Rank | Current performance rank |
| Strategy | Strategy name |
| Win Rate | Historical win % |
| Avg P&L % | Average return per trade |
| Sharpe | Risk-adjusted return |
| Trades | Number of trades in the window |
| Score | Composite score (50% win rate + 30% avg P&L + 20% streak) |
| Trend | Improving / Stable / Declining indicator |

### Running Optimisation

1. Select a **Strategy** to optimise
2. Select a **Symbol** and date range
3. Set parameter ranges (the grid search space)
4. Click **Run Optimisation**

The optimizer runs a grid search across all parameter combinations and returns the top 10 parameter sets sorted by Sharpe ratio. You can then apply the best parameters directly to the Auto-Trader.

### Journal Analysis

The journal analysis page shows patterns in your trading history:
- Which strategies are systematically profitable vs unprofitable
- Which market regimes each strategy works best in
- Correlations between intelligence module decisions and outcomes
- Fee drag analysis (how much commission is eating into returns)

---

## 13. Alerts & System Alerts

### Alerts — Price Alerts

**Path:** `/alerts` | **Icon:** Bell

Set price alerts on any symbol:
1. Click **New Alert**
2. Select exchange and symbol
3. Choose condition: **Above** or **Below**
4. Enter target price
5. Click **Save**

When the price condition is met, an alert fires through all configured channels (in-app, console, email, webhook).

### System Alerts

**Path:** `/system-alerts` | **Icon:** Alert Triangle

System Alerts monitor the health of the trading system itself. A red badge on the sidebar icon shows unread alert count, refreshed every 10 seconds.

**Alert severity levels:**

| Level | Badge Colour | Examples |
|-------|-------------|---------|
| Critical | Red | Kill switch triggered, margin call risk, liquidation risk |
| High | Orange | Max drawdown breached, 5+ consecutive losses, daily limit hit |
| Medium | Yellow | Strategy degrading, correlation warning, fee alert |
| Low | Blue | Trade executed, regime change, daily summary |

**Filtering:** Filter system alerts by severity, category, or read/unread status.

**Marking as read:** Click an alert to mark it read. "Mark All Read" clears the badge count.

### Email and Webhook Notifications

Configure in **Settings → Notification Settings**:

**Email (SMTP):**
```
SMTP Host: smtp.gmail.com
SMTP Port: 587
Username: your-email@gmail.com
App Password: (from Google Account settings)
Recipient: any-email@domain.com
Minimum Severity: High (to avoid email spam)
```

**Webhook (Slack example):**
```
Webhook URL: https://hooks.slack.com/services/...
Minimum Severity: Medium
```

Webhooks receive a JSON POST with `{ severity, category, message, timestamp }`.

---

## 14. Settings

**Path:** `/settings` | **Icon:** Settings2

### Appearance

- **Dark Mode / Light Mode** toggle
- Theme preference is saved to local storage

### Trading Defaults

| Setting | Description |
|---------|-------------|
| Default Order Type | Market or Limit for manual orders |
| Default Exchange | Pre-selected exchange in the Trading page |
| Default Symbol | Pre-selected symbol |
| Paper Trading | Toggle real vs paper trading globally |

### Auto-Trader Defaults

Default values for new Auto-Trader configurations:
- Default cycle interval (seconds)
- Default risk parameters (drawdown, exposure, position limits)
- Default strategy preferences

### AI Configuration

| Setting | Description |
|---------|-------------|
| Anthropic API Key | Claude (claude-3-5-sonnet) access key |
| Google API Key | Gemini (gemini-pro) access key |
| Preferred Provider | Which AI to use first (falls back to the other) |

Both keys are stored in the database (not environment variables). If neither key is set, all AI features fall back to rule-based logic automatically.

### Notification Settings

Configure email SMTP and/or webhook URLs for alerts (see [Section 13](#13-alerts--system-alerts)).

### Exchange API Keys (all 18)

Each exchange has its own configuration card showing:
- Connection status (connected / disconnected / error)
- API key (masked, last 4 chars visible)
- Last successful connection time
- Edit / Remove buttons
- **Test Connection** button

### Portfolio Reset

At the bottom of Settings:
- **Reset Paper Portfolio** — clears all paper trades and resets balance to $10,000
- **Clear Decision Log** — removes the auto-trader decision history
- Both actions require confirmation ("Type RESET to confirm")

---

## 15. Geo Risk

**Path:** `/geo-risk` | **Icon:** Globe

The Geo Risk page provides a real-time geopolitical risk intelligence dashboard. It monitors global news events, classifies them by type and region, and shows how they affect your trading across different asset classes.

### Regional Risk Heatmap

The top of the page shows a geographic heatmap with 5 monitored regions:

| Region | Coverage |
|--------|----------|
| Middle East | Oil/energy conflicts, regional tensions |
| US/China | Trade wars, sanctions, tech restrictions |
| Europe | EU policy, energy security, political shifts |
| Russia/Ukraine | Conflict, sanctions, energy supply |
| Asia Pacific | Regional tensions, natural disasters, trade |

Each region card shows:
- **Risk Score** — a colour-coded bar from green (low) to red (extreme)
- **Event Count** — how many active events are tracked for this region
- **Dominant Event Type** — the most significant type of event currently active
- **Trending** — whether risk is rising, falling, or stable

### Event Analytics

A summary panel showing:
- Total active geopolitical events
- Average severity (%) across all events
- Average confidence (%) of event classifications
- Event type distribution (top 8 types shown as badges with counts)

### Asset Impact Grid

The core of the dashboard — tabbed by asset class (Crypto, Equities, Forex, Commodities). For each common asset in the selected class, a card shows:

| Field | What It Shows |
|-------|---------------|
| **Risk Gauge** | Circular progress bar showing geo risk score as a percentage |
| **Opportunity Gauge** | Circular progress bar showing potential upside from events |
| **Net Signal** | −100% (bearish) to +100% (bullish) — risk vs opportunity balance |
| **Position Size Modifier** | How much the system adjusts position size (e.g. 70% = reduce by 30%) |
| **Signal Strength** | Weak / Moderate / Strong / Extreme badge |
| **Recommended Action** | Reduce Exposure / Hedge / Hold / Increase Exposure |
| **Dominant Events** | The top 2 event types driving the score |

### Risk Timeline

A 7-day bar chart showing hourly-bucketed risk scores. Each bar is colour-coded from green (low risk) to red (high risk). Hover over any bar to see the exact timestamp, risk percentage, and event count for that hour.

### Active Events Feed

A live table of the latest 25 geopolitical events with:
- **Time** — when the event was detected
- **Type** — colour-coded badge (e.g. MILITARY_CONFLICT in red, SANCTIONS in orange)
- **Title** — headline summary of the event
- **Severity** — how severe the event is (0–100%)
- **Confidence** — how confident the classifier is (0–100%)
- **Regions** — which geographic regions are affected
- **Source** — GDELT or RSS feed origin

### Event Evaluator

A manual classification tool on the right side of the page. Enter an event title and optional description, click **Classify Event**, and the system returns:
- Detected event type and any secondary types
- Severity and confidence scores
- Affected geographic regions

This is useful for testing "what if" scenarios — for example, entering "OPEC announces emergency production cut" to see how the system would classify and score it.

### How It Connects to Trading

The Geo Risk module feeds directly into the **Trust Score** system:
- The GeoMonitor continuously evaluates overall geopolitical risk levels
- This feeds into the **News Safety** component of the Execution Trust Scorer
- When geo risk is elevated, the Trust Score drops, which can reduce position sizes or block trades entirely
- High-risk events (score ≥ 0.8) can trigger near-blocks on trading activity

You don't need to monitor this page manually — the Auto-Trader automatically incorporates geopolitical risk into every trading decision via the trust score pipeline.

---

## 16. Trust Score

**Path:** `/trust-score` | **Icon:** Shield

The Trust Score page shows you how confident the system is about executing any given trade. Instead of multiple independent safety checks blocking trades in isolation, all signal sources are combined into a single composite trust score — giving you a clear, actionable confidence reading before any trade is placed.

### Live Trust Evaluator

Type any symbol (e.g. BTC/USDT, EUR/USD, AAPL), choose a direction (Buy or Sell), and select an exchange. Click **Evaluate** to get an instant trust assessment:

| Output | What It Means |
|--------|---------------|
| **Trust Score** | A gauge from 0–100% showing overall execution confidence |
| **Grade** | A (excellent ≥80%), B (good 65–80%), C (marginal 50–65%), D (skip 35–50%), F (reject <35%) |
| **Recommendation** | Execute / Reduce Size / Wait / Reject |
| **Size Modifier** | The fraction of normal position size the system will use (100% for A, 70% for B, 40% for C, 0% for D/F) |

### Component Breakdown

Below the gauge you'll see all 10 signal components that feed into the score, each displayed as a labelled progress bar:

| Component | What It Measures |
|-----------|------------------|
| Signal Strength | How confident the underlying strategy signal is (0–1) |
| Timeframe Agreement | How many of the 15m/1h/4h timeframes agree on direction |
| Regime Confidence | Whether the detected market regime supports the trade |
| Sentiment Alignment | Whether market sentiment is pointing in the same direction |
| Strategy Track Record | The strategy's recent win rate from the live scoreboard |
| Spread Quality | Current spread vs the average (a wide spread reduces confidence) |
| Data Freshness | How recently the OHLCV data was last updated |
| Venue Quality | Historical execution quality for the selected exchange |
| News Safety | Proximity and severity of upcoming news events |
| Risk Headroom | How close the portfolio is to its max drawdown limit |

Components are colour-coded: green (>70%) = strong, amber (50–70%) = moderate, red (<50%) = weak. They are sorted by weight so the most impactful factors appear first.

### Weight Profiles

Different asset classes weight the 10 components differently, reflecting what matters most for each market:

- **Crypto** — Sentiment (15%) and news (10%) weighted high, because crypto is heavily sentiment-driven
- **Forex** — Timeframe agreement (15%) and spread quality (10%) weighted high — technical alignment and cost sensitivity matter most
- **Stocks** — Strategy track record (15%) and risk headroom (15%) weighted high — capital preservation is the priority
- **Indices** — Regime confidence (15%) weighted high — indices are macro-driven
- **Commodities** — Sentiment (15%) and news (12%) weighted high — supply/demand and geopolitical factors dominate
- **Spread Betting** — Spread quality (12%) and venue quality (8%) elevated — execution costs amplified by leverage

Use the asset-class tabs on the Trust Score page to see the full weight table for any category.

### Venue Quality

The Venue Quality tab shows execution quality scores for all exchanges based on historical trade data:

| Metric | What It Tracks |
|--------|----------------|
| Fill Rate | Percentage of orders that executed successfully |
| Avg Slippage | Average difference between expected and actual fill price |
| Success Rate | Percentage of trades completed without errors |

New exchanges start at a neutral 0.7 score until at least 5 trades have been recorded. Scores update automatically after every trade.

### Trust Score Analytics

The Analytics tab answers the question: **do high-trust trades actually perform better?**

- Compares average P&L and win rate across each grade (A through F)
- Shows how trust scores have evolved over time
- Lets you validate that the scoring system is predictive in your specific trading environment
- Based on the last 1,000 trust evaluations in the rolling history window

---

## 17. UK Tax Information

This section covers the UK tax treatment of trading through AlgoTrader. **This is not financial or tax advice — consult a qualified accountant for your specific situation.**

### Spread Betting — TAX FREE

Spread betting is **completely free from UK taxes**:
- No Capital Gains Tax (CGT) on profits
- No Income Tax on profits
- No Stamp Duty
- Losses **cannot** be offset against other gains (the trade-off for tax-free status)

This makes spread betting (via IG Group, Capital.com, or CMC Markets) the most tax-efficient instrument for UK retail traders who are making money.

### CFD Trading — Capital Gains Tax Applies

CFDs (Contracts for Difference) are taxed differently:
- Profits are subject to **Capital Gains Tax** at your marginal rate (18% basic rate, 24% higher rate from April 2024)
- **Losses can be offset** against other capital gains in the same tax year or carried forward
- If you have existing CGT losses from other investments, CFDs can be useful to realise profits efficiently

### Crypto Trading — Capital Gains Tax

Crypto is treated as a capital asset by HMRC:
- Profits are subject to **CGT** at the same rates as CFDs
- Each disposal is a taxable event (selling, swapping, or using crypto to buy goods)
- The CGT Annual Exempt Amount can shelter up to £3,000 (2024/25) of gains per year
- Record-keeping is essential — AlgoTrader's Trade History page exports all trades

### Stock Trading — Stamp Duty + CGT

- **Stamp Duty Reserve Tax**: 0.5% on purchases of UK shares
- **Capital Gains Tax**: On profits when shares are sold
- ISA and SIPP wrappers are CGT-free — AlgoTrader does not currently integrate with these

### Summary Table

| Asset / Instrument | CGT | Stamp Duty | Income Tax | Losses Offset |
|-------------------|-----|-----------|-----------|--------------|
| Spread Betting (UK resident) | None | None | None | No |
| CFD | Yes | No | No | Yes |
| Crypto | Yes | No | No | Yes |
| UK Shares (direct) | Yes | 0.5% on buy | No | Yes |
| US Shares (direct) | Yes | No | No | Yes |

The **Tax Efficiency Router** on the Spread Betting page automatically recommends the most tax-efficient instrument type based on your situation.

---

## 18. Deployment Guide

### Local Development Setup

```bash
# Full setup from scratch

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Optional: create .env file with API keys
cp .env.example .env
# Edit .env with your keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend/client
npm install
npm run dev
# Opens at http://localhost:5173
```

### Docker Deployment

```yaml
# docker-compose.yml (simplified)
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data    # Persistent SQLite + JSON state
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}

  frontend:
    build: ./frontend/client
    ports:
      - "5173:80"
    depends_on:
      - backend
```

```bash
# Build and run
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f backend

# Stop
docker compose down
```

### AWS Cloud Deployment

#### Option 1: EC2 (Simplest)

```bash
# 1. Launch Ubuntu 22.04 EC2 instance (t3.small or larger)
# 2. SSH in and install dependencies
sudo apt update && sudo apt install -y python3.11 python3.11-venv nodejs npm nginx

# 3. Clone and set up
git clone <repo> /opt/algo-trader
cd /opt/algo-trader

# Backend setup (same as local)
cd backend && python3.11 -m venv venv && ...

# 4. Run backend with systemd service
sudo nano /etc/systemd/system/algotrader.service
# [Unit]
# Description=AlgoTrader Backend
# [Service]
# ExecStart=/opt/algo-trader/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# WorkingDirectory=/opt/algo-trader/backend
# Restart=always
# [Install]
# WantedBy=multi-user.target

sudo systemctl enable algotrader && sudo systemctl start algotrader

# 5. Build frontend and serve via nginx
cd /opt/algo-trader/frontend/client
npm install && npm run build
# Copy dist/ to nginx web root
```

#### Option 2: App Runner

```bash
# Build Docker image and push to ECR
aws ecr create-repository --repository-name algo-trader
docker build -t algo-trader ./backend
docker tag algo-trader:latest <ecr-uri>:latest
docker push <ecr-uri>:latest

# Create App Runner service via AWS Console
# → Source: Container registry → ECR
# → Port: 8000
# → Environment variables: set API keys
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Optional | None | Claude API key |
| `GOOGLE_API_KEY` | Optional | None | Gemini API key |
| `DATABASE_URL` | Optional | `sqlite:///./data/trading.db` | SQLAlchemy connection string |
| `SECRET_KEY` | Recommended | Random | JWT session signing key |
| `CORS_ORIGINS` | Optional | `http://localhost:5173` | Comma-separated allowed origins |
| `ENVIRONMENT` | Optional | `development` | `development` or `production` |
| `LOG_LEVEL` | Optional | `INFO` | Python logging: DEBUG/INFO/WARNING/ERROR |
| `FRONTEND_URL` | Optional | None | Production frontend URL for CORS |
| `SMTP_HOST` | Optional | None | Email alerts SMTP host |
| `SMTP_PORT` | Optional | `587` | SMTP port |
| `SMTP_USERNAME` | Optional | None | SMTP authentication username |
| `SMTP_PASSWORD` | Optional | None | SMTP app password |
| `SMTP_RECIPIENT` | Optional | None | Alert recipient email |
| `WEBHOOK_URL` | Optional | None | Webhook URL for alerts |

---

## 19. FAQ

**Q: Is my money safe in paper trading mode?**
A: Yes — paper trading is entirely simulated. No real funds leave your account. The default $10,000 is virtual money and cannot be withdrawn.

**Q: Can I use the Auto-Trader without entering API keys?**
A: Yes. Paper trading mode works with no exchange credentials. The system uses simulated prices for paper orders.

**Q: What happens if the Auto-Trader loses more than the max drawdown limit?**
A: Trading halts automatically. A CRITICAL alert is fired. You must manually review the situation and reset the kill switch to resume.

**Q: How do I stop the Auto-Trader immediately?**
A: Click the **Kill Switch** button on the Auto-Trader page. Trading stops instantly and cannot resume until you deactivate it.

**Q: Are spread betting profits really tax-free?**
A: For UK residents, yes — spread betting profits are exempt from CGT and Income Tax under UK law. This is a key advantage for UK traders. Non-UK residents should check their local tax rules.

**Q: Can AlgoTrader trade on my behalf while I sleep?**
A: Yes. The Auto-Trader runs continuously when started, with configurable risk limits. The risk management system (max drawdown, daily loss limit, kill switch) protects your portfolio from extreme losses.

**Q: What AI models does AlgoTrader use?**
A: The primary model is Claude (Anthropic) — specifically claude-3-5-sonnet. Gemini (Google) is the fallback. If neither key is configured, all AI features fall back to rule-based logic with no degradation in core functionality.

**Q: How is position sizing calculated?**
A: The Kelly Criterion calculates the mathematically optimal fraction, then half-Kelly is applied for safety, clamped to 1–20% of portfolio. This is further adjusted by the losing streak multiplier, time-of-day profiler, and asset-specific rules.

**Q: Can I run multiple exchanges simultaneously?**
A: The current Auto-Trader runs one exchange per session. You can start separate Auto-Trader sessions in different browser tabs or configure multiple symbols on the same exchange.

**Q: My exchange connection shows an error — what should I do?**
A: Check that your API key has "spot trading" permissions enabled, is not IP-restricted to a different address, and has not expired. Click "Test Connection" to see the specific error message.

**Q: How do I reset my portfolio to start fresh?**
A: Go to Settings → Portfolio Reset → Reset Paper Portfolio. This wipes all trades and positions and resets balance to $10,000. Decision log is cleared separately.

**Q: Does AlgoTrader support live trading or only paper trading?**
A: Both are supported. Paper trading is the default for safety. To switch to live trading, go to Settings → Trading Defaults → toggle "Paper Trading" off. This requires connected exchange API keys with trading permissions.

---

## 20. Glossary

| Term | Definition |
|------|-----------|
| **ADX** | Average Directional Index — measures trend strength (>25 = strong trend) |
| **ATR** | Average True Range — measures market volatility over N periods |
| **Backtest** | Testing a trading strategy on historical data to evaluate performance |
| **Bid/Ask Spread** | The difference between the highest buy price and lowest sell price |
| **Bull/Bear** | Bull = rising market, Bear = falling market |
| **Capital Gains Tax (CGT)** | UK tax on profits from selling assets |
| **CFD** | Contract for Difference — a derivative tracking asset price movement |
| **Commission** | Fee charged per trade by the exchange |
| **Correlation** | How closely two assets move together (1.0 = perfectly correlated) |
| **DCA** | Dollar-Cost Averaging — buying fixed amounts at regular intervals |
| **Drawdown** | Percentage decline from a portfolio's peak value |
| **EMA** | Exponential Moving Average — weighted to give more importance to recent prices |
| **Equity Curve** | Chart of portfolio value over time |
| **FCA** | Financial Conduct Authority — UK financial regulator |
| **Fear & Greed Index** | 0–100 sentiment index for crypto markets (0=extreme fear, 100=extreme greed) |
| **Funding Rate** | Periodic payment on perpetual futures contracts |
| **Guaranteed Stop** | A stop-loss that cannot be skipped even in a gap event (costs a premium) |
| **Kelly Criterion** | Mathematical formula for optimal position sizing based on win rate |
| **Leverage** | Borrowing to amplify trade size (3× leverage = 3× gain or loss) |
| **Limit Order** | An order to buy/sell only at a specific price or better |
| **Liquidation** | Forced close of a leveraged position when margin is exhausted |
| **MACD** | Moving Average Convergence Divergence — momentum indicator |
| **Maker/Taker** | Maker adds liquidity (limit order), Taker removes it (market order) |
| **Margin** | Capital held as collateral for leveraged positions |
| **Market Order** | An order executed immediately at the current best available price |
| **MTF** | Multi-Timeframe — analysing signals on multiple chart periods simultaneously |
| **Paper Trading** | Simulated trading with virtual money — no real funds at risk |
| **Perpetual** | A futures contract with no expiry date (common in crypto) |
| **P&L** | Profit and Loss |
| **Regime** | Current market state: trending_up, trending_down, ranging, or volatile |
| **RSI** | Relative Strength Index — measures overbought/oversold conditions (0–100) |
| **Sharpe Ratio** | Risk-adjusted return (higher = better risk/reward) |
| **Slippage** | The difference between expected execution price and actual fill price |
| **SMA** | Simple Moving Average — unweighted average of closing prices |
| **SONIA** | Sterling Overnight Index Average — UK benchmark interest rate |
| **Spread Betting** | A leveraged, tax-free (UK) derivative product sized in £/point |
| **Stop-Loss** | An automatic order to close a position when price reaches a set level |
| **Take-Profit** | An automatic order to close a position when a profit target is reached |
| **Trailing Stop** | A stop-loss that moves upward as price rises, locking in profits |
| **VWAP** | Volume-Weighted Average Price — the "fair value" price weighted by volume |
| **Walk-Forward** | Out-of-sample validation technique that prevents overfitting |
| **Webhook** | An HTTP callback URL that receives alert notifications automatically |

---

*User guide generated from codebase audit — April 2026. All feature descriptions reflect the live AlgoTrader codebase.*
