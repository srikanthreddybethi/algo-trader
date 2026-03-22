# AlgoTrader — Product Requirements

> **Version:** 1.0  
> **Status:** Active  
> **Last Updated:** March 2026  
> **Audience:** Product, Engineering, QA, Stakeholders

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Core Requirements](#2-core-requirements)
   - 2.1 [Autonomous Trading](#21-autonomous-trading)
   - 2.2 [Multi-Exchange Support](#22-multi-exchange-support)
   - 2.3 [Trading Strategies](#23-trading-strategies)
   - 2.4 [Intelligence & Self-Learning](#24-intelligence--self-learning)
   - 2.5 [Risk Management](#25-risk-management)
   - 2.6 [Asset-Specific Trading](#26-asset-specific-trading)
   - 2.7 [Spread Betting](#27-spread-betting)
   - 2.8 [Paper Trading](#28-paper-trading)
   - 2.9 [Live Trading](#29-live-trading)
   - 2.10 [Market Data & Signals](#210-market-data--signals)
3. [User Interface Requirements](#3-user-interface-requirements)
   - 3.1 [Pages](#31-pages)
   - 3.2 [Design](#32-design)
4. [API Requirements](#4-api-requirements)
5. [Testing Requirements](#5-testing-requirements)
6. [Deployment Requirements](#6-deployment-requirements)
7. [Performance Requirements](#7-performance-requirements)
8. [Security Requirements](#8-security-requirements)

---

## 1. Product Overview

### What Is AlgoTrader?

AlgoTrader is an **automated trading platform** that buys and sells financial assets on behalf of the user — without requiring the user to be at a computer or make manual decisions.

The platform connects to real brokerage accounts and cryptocurrency exchanges, analyses market conditions using a combination of mathematical strategies and AI, and places trades automatically according to rules the user sets.

Users can also run the platform in **paper trading mode**, which simulates all trading activity with virtual money so they can test strategies without any financial risk.

### Who Is It For?

| User Type | What They Want |
|---|---|
| Retail traders | Automate a strategy they already use manually |
| Algorithmic traders | Run quantitative strategies across multiple exchanges at once |
| Spread bettors | Automate spread betting with FCA-compliant position sizing |
| Beginners | Test trading ideas safely with virtual money before going live |

### What Problem Does It Solve?

Manual trading is time-consuming, emotionally driven, and limited by human attention span. AlgoTrader removes the human from the execution loop entirely. It:

- Monitors markets 24/7 without fatigue
- Executes trades in milliseconds with no emotional hesitation
- Applies consistent risk rules on every single trade
- Learns from past performance and adjusts automatically
- Lets users trade across 18 different brokers and exchanges from a single interface

### Scale at a Glance

| Metric | Count |
|---|---|
| Lines of code | 38,000 |
| Exchange integrations | 18 |
| Trading strategies | 16 |
| Intelligence modules | 32 |
| UI pages | 15 |
| API endpoints | 79 |
| Automated tests | 1,237 |

---

## 2. Core Requirements

---

### 2.1 Autonomous Trading

The auto-trader is the heart of the system. It runs on a loop and makes trading decisions without any human input.

#### Required Behaviours

- **Must trade automatically** without the user needing to click anything once it is started.
- **Must support configurable run intervals** from 1 minute to 1 hour. The user sets how often the system checks for trading opportunities.
- **Must follow a multi-step decision pipeline** before every trade. A trade is only placed after passing through all checks. If any check fails, the trade is blocked and the reason is recorded.
- **Must log every decision** with full detail — what the market was doing, what signal was generated, what blocked or allowed the trade, and the exact reasoning at each step.
- **Must have a kill switch** that immediately halts all trading activity with a single action.
- **Must support 30 distinct decision outcomes** (see table below). Every outcome of a cycle must be categorised and stored.

#### The Decision Pipeline (in order)

Every potential trade passes through these steps before being executed:

1. Check if the asset is valid and supported
2. Check if market data is fresh (not stale)
3. Check if news events block trading
4. Check market sentiment (Fear & Greed)
5. Check if a similar trade is already open (no duplicates)
6. Run intelligence modules to assess conditions
7. Run the selected trading strategy for a signal
8. Check all risk rules (position size, drawdown, loss streak, etc.)
9. Check if the trade is financially worth making (fees vs expected gain)
10. Size the position correctly
11. Place the order

#### Decision Outcome Types

Every auto-trader cycle produces one of the following 30 outcomes:

| Outcome | What It Means |
|---|---|
| `trade_executed` | A buy or sell order was placed successfully |
| `auto_exit` | The system automatically exited an open position |
| `strategy_sell_exit` | A strategy generated an explicit sell signal |
| `no_signal` | No buy or sell signal was found — nothing to do |
| `intelligence_block` | The intelligence pipeline blocked the trade |
| `not_worth_trading` | The expected profit doesn't cover fees and slippage |
| `risk_block` | A risk rule prevented the trade |
| `asset_validation_block` | The asset failed validation checks |
| `news_halt` | Breaking news caused a full trading halt |
| `news_caution` | News flagged caution — trade size reduced or blocked |
| `extreme_greed` | Market Fear & Greed index is at extreme greed — trade blocked |
| `contrarian_sentiment` | Sentiment is opposite to the trade direction — blocked |
| `duplicate_blocked` | A position in this asset already exists |
| `size_too_small` | Position size is below the exchange's minimum order |
| `stale_data` | Market data is too old to trust |
| `streak_cooldown` | Too many losses in a row — trading paused |
| `time_block` | Outside of allowed trading hours |
| `sb_sized` | Spread bet position has been sized (£/point) |
| `sb_rejected` | Spread bet position was rejected |
| `skip_sell` | A sell was skipped for a valid reason |
| `ai_strategy_selection` | AI chose and switched to a different strategy |
| `auto_improvement` | The system ran a self-improvement cycle |
| `loss_analysis` | The system analysed recent losses and updated its behaviour |
| `kill_switch` | Trading was halted by the kill switch |
| `config_update` | System configuration was updated automatically |
| `cycle_complete` | A full decision cycle completed without placing a trade |
| `cycle_error` | An error occurred during the cycle |
| `trade_failed` | A trade was attempted but the exchange rejected it |
| `error` | A general system error occurred |
| `system` | A system-level event was recorded |

---

### 2.2 Multi-Exchange Support

The platform must connect to **18 exchanges and brokers** across 5 categories.

#### Exchange Categories

| Category | Count | Exchanges |
|---|---|---|
| Cryptocurrency | 9 | Binance, Bybit, Kraken, Coinbase, OKX, Crypto.com, Bitstamp, Gate.io, Gemini |
| Spread Betting | 3 | IG Group, Capital.com, CMC Markets |
| Multi-Asset | 3 | Interactive Brokers, eToro, Saxo Bank |
| Forex | 1 | OANDA |
| Stocks | 2 | Alpaca, Trading 212 |

#### Full Exchange List

| Exchange | Category | Fee (%) | What It's Used For |
|---|---|---|---|
| Binance | Crypto | 0.10 | High-volume crypto trading; largest global exchange |
| Bybit | Crypto | 0.10 | Crypto derivatives and spot trading |
| Kraken | Crypto | 0.26 | Regulated crypto exchange; good for EUR pairs |
| Coinbase | Crypto | 0.60 | US-focused retail crypto trading |
| OKX | Crypto | 0.08 | Low-fee crypto trading with advanced order types |
| Crypto.com | Crypto | 0.075 | Consumer crypto platform; competitive fees |
| Bitstamp | Crypto | 0.40 | One of the oldest regulated crypto exchanges |
| Gate.io | Crypto | 0.10 | Wide range of altcoins |
| Gemini | Crypto | 0.35 | Regulated US crypto exchange |
| IG Group | Spread Betting | 0.06 | UK spread betting; wide range of instruments |
| Capital.com | Spread Betting | 0.06 | AI-enhanced spread betting platform |
| CMC Markets | Spread Betting | 0.07 | UK spread betting; competitive spreads |
| OANDA | Forex | 0.03 | Forex and CFD broker |
| Interactive Brokers | Multi-Asset | 0.05 | Professional multi-asset broker |
| eToro | Multi-Asset | 1.00 | Social trading platform |
| Saxo Bank | Multi-Asset | 0.10 | Professional multi-asset trading |
| Alpaca | Stocks | 0.00 | Commission-free US stock trading |
| Trading 212 | Stocks | 0.00 | Commission-free stock and ETF trading |

#### Requirements for Every Exchange Integration

Each exchange must support the following operations:

- **Connect / Disconnect** — Store and validate API credentials; test the connection before activating
- **Account balance** — Retrieve live portfolio value and available margin
- **Ticker data** — Real-time price for any supported instrument
- **OHLCV candles** — Historical price bars (open, high, low, close, volume) at multiple timeframes
- **Order book** — Current bids and asks to assess liquidity before trading
- **Place orders** — Submit market orders, limit orders, and stop-loss orders
- **Cancel orders** — Cancel any open order on demand
- **Order status** — Track whether an order is open, filled, or cancelled

#### Paper Trading Without Real API Keys

- The system must work in full **paper trading mode** without requiring any real exchange credentials.
- All exchange operations must simulate realistically using live price feeds where available, or generated price data where not.
- Fee simulation must match each exchange's actual fee rate.
- Slippage simulation must reflect realistic market conditions (see Section 2.8).

---

### 2.3 Trading Strategies

The platform must support **16 trading strategies** that can generate buy, sell, or hold signals from price data.

#### Strategy Requirements (All Strategies)

- Every strategy must produce one of three outputs: **BUY**, **SELL**, or **HOLD**
- Every strategy must work from standard OHLCV (candlestick) price data
- Strategies must be selectable manually by the user
- Strategies must also be **selected automatically** by the AI based on current market conditions
- The system must **track the performance of every strategy** over time and adjust how often each is used based on results

#### Quantitative Strategies (11)

These are mathematical/statistical strategies based on price and volume patterns:

| Strategy | What It Does |
|---|---|
| **SMA Crossover** | Compares a fast and slow simple moving average; buys when fast crosses above slow, sells when it crosses below |
| **EMA Crossover** | Same as SMA Crossover but uses exponential moving averages, which react faster to recent price changes |
| **RSI** | Measures whether an asset is overbought or oversold on a 0–100 scale; buys below 30, sells above 70 |
| **MACD** | Tracks the relationship between two moving averages; generates signals when the lines cross |
| **Bollinger Bands** | Detects when price moves outside its normal range; trades the return to normal (mean reversion) |
| **Mean Reversion** | Identifies assets that have moved far from their average price and bets on them returning to it |
| **Momentum** | Buys assets that have been rising and sells assets that have been falling |
| **VWAP** | Compares current price to the volume-weighted average price of the day; used to detect institutional interest |
| **DCA (Dollar Cost Averaging)** | Buys a fixed amount at regular intervals, regardless of price, to average down the cost over time |
| **Grid Trading** | Places multiple buy and sell orders at fixed price intervals around the current price to profit from price oscillation |
| **Pure AI** | Uses an AI model directly to decide whether to buy, sell, or hold based on a summary of all available data |

#### Spread Betting Strategies (5)

These strategies are specifically designed for spread betting instruments (indices, currencies, commodities):

| Strategy | What It Does |
|---|---|
| **SB Trend Rider** | Identifies and follows strong trending markets using spread bet position sizing (£/point) |
| **SB Mean Reversion** | Trades the return to mean on spread betting instruments with overnight funding cost awareness |
| **SB Momentum Scalper** | Captures short-term momentum moves with tight stops and rapid entry/exit |
| **SB Breakout (Guaranteed Stop)** | Trades price breakouts above/below key levels; uses guaranteed stop-losses to cap downside |
| **SB Index Surfer** | Specifically optimised for index products (FTSE, DAX, S&P 500); trades trend and reversion in indices |

---

### 2.4 Intelligence & Self-Learning

The platform includes **32 intelligence modules** that work alongside the trading strategies. These modules don't generate trade signals directly — they assess whether a signal is good enough to act on, how big the position should be, when to exit, and how the system should improve itself.

#### Core Intelligence (6 modules)

These form the central decision-making backbone:

| Module | What It Does |
|---|---|
| **Strategy Scoreboard** | Keeps a running score of how well each strategy is performing; higher-performing strategies are used more often |
| **Multi-Timeframe Consensus** | Checks whether multiple timeframes (e.g., 5-minute, 1-hour, daily) all agree on the direction before a trade is placed |
| **Correlation Guard** | Prevents the system from opening too many positions that move together; avoids hidden concentration risk |
| **Kelly Criterion Position Sizing** | Calculates the mathematically optimal trade size based on the strategy's historical win rate and average profit/loss |
| **Market Memory** | Remembers how the market behaved in similar conditions in the past and uses that to inform current decisions |
| **Intelligence Pipeline** | Orchestrates all other modules in the correct order; decides which modules run and combines their outputs into a final recommendation |

#### Adaptive Intelligence (7 modules)

These modules help the system adapt to changing conditions:

| Module | What It Does |
|---|---|
| **Adaptive Exit Levels** | Adjusts take-profit and stop-loss levels based on recent market volatility rather than using fixed percentages |
| **Symbol Discovery** | Automatically identifies new trading opportunities by scanning for assets showing unusual activity |
| **AI Accuracy Tracker** | Tracks how accurate the AI's past predictions have been and adjusts how much weight AI signals are given |
| **Walk-Forward Validator** | Tests whether a strategy would have worked on recent historical data before allowing it to trade live |
| **Adaptive Frequency** | Adjusts how often the system checks for trades based on how active the market is |
| **Time-of-Day Profiler** | Learns which hours of the day are most and least profitable for each instrument and adjusts activity accordingly |
| **Adaptive Layer** | An overarching module that adjusts the overall system settings based on recent performance trends |

#### Instrument Intelligence (4 modules)

These modules evaluate individual instruments and positions:

| Module | What It Does |
|---|---|
| **Instrument Selector** | Chooses the best instruments to trade at any given moment from all available options |
| **Smart Exit Decision** | Decides whether to hold or close an existing position based on current conditions (not just the original signal) |
| **Trade Worthiness Filter** | Calculates whether a trade is financially viable after accounting for fees, slippage, and expected move size |
| **Liquidation Calculator** | For leveraged positions, calculates the exact price at which the position would be forcibly closed and flags if it's too close |

#### AI Decision Intelligence (4 modules)

These use AI to make higher-level judgements:

| Module | What It Does |
|---|---|
| **News Impact Assessment** | Reads recent news headlines and assesses whether they are likely to move the market; can halt trading if news is very significant |
| **Smart Exit Reasoning** | Uses AI to decide whether it's better to exit now or hold a position longer, given current news and market conditions |
| **Loss Pattern Analysis** | Analyses recent losing trades to find patterns (e.g., "we lose money on Monday mornings") and adjusts rules to avoid repeating them |
| **AI Strategy Selection** | Uses AI to choose which trading strategy is best suited for current market conditions |

#### Asset Rules (5 modules)

These enforce different rules for each type of asset:

| Module | What It Does |
|---|---|
| **Crypto Rules** | Applies cryptocurrency-specific trading rules (24/7 markets, high volatility, low max leverage) |
| **Forex Rules** | Applies forex-specific rules (weekend closures, high leverage limits, pip-based sizing) |
| **Stock Rules** | Applies stock-specific rules (market hours, earnings blackouts, fractional share support) |
| **Index Rules** | Applies index-specific rules (trading hours, roll dates, volatility filters) |
| **Commodity Rules** | Applies commodity-specific rules (contract expiry, session hours, EIA data integration) |

#### Spread Betting Modules (7 modules)

These handle everything specific to spread betting:

| Module | What It Does |
|---|---|
| **Position Sizer** | Converts a desired risk amount into the correct £-per-point bet size for spread betting |
| **Margin Monitor** | Tracks available margin in real time and prevents trades that would exceed FCA-mandated margin requirements |
| **Overnight Funding Calculator** | Calculates the daily cost of holding a spread bet position overnight (SONIA rate plus broker markup) |
| **Spread Monitor** | Tracks the bid-ask spread width in real time and blocks trades when spreads widen beyond acceptable limits |
| **Market Hours Filter** | Prevents spread bets from being opened outside the trading hours for each instrument |
| **Gap Protection Manager** | Detects when markets are about to close and adjusts or closes positions to protect against weekend/session gap risk |
| **Tax Efficiency Router** | Routes trades to the most tax-efficient instrument type — spread bet for profitable trades (tax-free in UK), CFD for losses (where losses can be offset) |

#### Improvement Modules (2 modules)

These make the system smarter over time:

| Module | What It Does |
|---|---|
| **Continuous Improver** | Periodically reviews all strategy and module settings and makes small adjustments to improve performance |
| **Self-Optimizer** | Runs full optimisation cycles using historical data to find better parameter settings for strategies |

#### Alert Manager (1 module with 4 plugins)

| Module | What It Does |
|---|---|
| **Alert Manager** | Sends notifications when important events occur (trade placed, loss limit hit, kill switch triggered, etc.) via 4 configurable delivery channels (e.g., email, SMS, webhook, desktop notification) |

---

### 2.5 Risk Management

Risk management rules are applied on every trade before it is placed. Every rule has a default value that the user can change.

#### Global Risk Controls

| Risk Control | Default Value | What It Prevents |
|---|---|---|
| **Max drawdown** | 10% of portfolio | Stops trading if total portfolio value drops more than 10% from its peak |
| **Max position size** | 20% of portfolio | Prevents any single trade from being too large relative to the total account |
| **Max open positions** | 5 | Limits how many trades can be open at the same time |
| **Stop loss per trade** | 5% | Automatically closes a trade if it loses more than 5% |
| **Daily loss limit** | 3% | Shuts down trading for the rest of the day if total daily losses exceed 3% |
| **Circuit breaker** | 5 consecutive failures | Stops all trading for 5 minutes after 5 trade failures in a row |
| **Rate limiter** | Max 10 trades/minute | Prevents runaway loops from placing excessive orders |
| **Losing streak detector** | Configurable | Pauses trading after a configurable number of consecutive losing trades |

#### How Risk Rules Are Applied

1. Every potential trade is checked against all applicable risk rules before execution.
2. If any rule would be violated, the trade is blocked and the blocking reason is logged.
3. The user can configure all default values through the Settings page.
4. Some rules reset automatically (e.g., the circuit breaker resets after 5 minutes; the daily loss limit resets at midnight).

---

### 2.6 Asset-Specific Trading

Different types of assets trade differently. The platform applies specific rules, data sources, and risk parameters for each asset class.

---

#### Cryptocurrency

| Property | Detail |
|---|---|
| **Markets** | 24/7, 365 days a year |
| **Stop loss** | 3% default |
| **Max position size** | 15% of portfolio |
| **Max leverage** | 2x |
| **Preferred strategies** | All 11 quantitative strategies |
| **Data sources** | CoinGecko (prices, trending, global market data), Fear & Greed Index, crypto news RSS feeds (CoinDesk, CoinTelegraph, Decrypt, Bitcoin Magazine) |
| **Unique rules** | No market hours restrictions; higher volatility tolerance; leverage capped at 2x to limit risk |
| **What can block a trade** | Fear & Greed at Extreme Greed; high-impact crypto news; position already open; max positions reached; drawdown exceeded |

---

#### Forex

| Property | Detail |
|---|---|
| **Markets** | Monday–Friday; closed weekends |
| **Stop loss** | 0.5% default (forex moves in small increments) |
| **Max position size** | 20% of portfolio |
| **Max leverage** | 30x (regulated FCA limit for retail) |
| **Preferred strategies** | SMA/EMA Crossover, MACD, Momentum, Mean Reversion |
| **Data sources** | OANDA price feed; economic calendar (Trading Economics RSS) |
| **Unique rules** | Weekend gap protection; pip-based position sizing; very tight stop losses due to leverage |
| **What can block a trade** | Major economic data releases (e.g., Non-Farm Payrolls); weekend hours; excessive leverage |

---

#### Stocks

| Property | Detail |
|---|---|
| **Markets** | NYSE/NASDAQ: 9:30am–4:00pm ET, Monday–Friday |
| **Stop loss** | 3% default |
| **Max position size** | Configurable |
| **Max leverage** | None (stocks traded on margin separately) |
| **Preferred strategies** | RSI, MACD, Momentum, VWAP, DCA |
| **Data sources** | Yahoo Finance RSS (news), BBC Business RSS, Reuters RSS, yfinance (stock fundamentals and price data) |
| **Unique rules** | Trading only during market hours; earnings announcement blackouts; fundamentals screening via yfinance |
| **What can block a trade** | Pre/post-market hours; negative earnings news; liquidity concerns |

---

#### Indices

| Property | Detail |
|---|---|
| **Examples** | FTSE 100, S&P 500, DAX, Nasdaq 100 |
| **Stop loss** | 2% default |
| **Max leverage** | Per FCA rules for spread betting |
| **Preferred strategies** | SB Index Surfer, SB Trend Rider, Momentum |
| **Data sources** | Index breadth data (simulated); spread betting exchange feeds |
| **Unique rules** | Session hours per index; roll date handling; primarily traded via spread betting |
| **What can block a trade** | Outside trading hours; extreme volatility events; gap risk near close |

---

#### Commodities

| Property | Detail |
|---|---|
| **Examples** | Oil (WTI/Brent), Gold, Natural Gas |
| **Stop loss** | 3% default |
| **Preferred strategies** | SB Trend Rider, SB Breakout, Mean Reversion |
| **Data sources** | EIA (Energy Information Administration) data with fallback; spread betting feeds |
| **Unique rules** | Contract expiry awareness; session hours; EIA inventory report blackouts for energy products |
| **What can block a trade** | Contract rollover periods; major supply data releases; low liquidity sessions |

---

### 2.7 Spread Betting

Spread betting is a specific type of financial product popular in the UK. It works differently from buying stocks or crypto, so the platform has a dedicated set of features for it.

#### What Is Spread Betting?

Instead of buying a share or a coin, the user bets on whether the price will go up or down. The profit/loss is calculated as: **price movement × bet size in £ per point**. In the UK, spread betting profits are tax-free.

#### Position Sizing in £/Point

- All spread betting positions must be sized in **£ per point** (not in shares, coins, or contracts).
- The system must calculate the correct £/point stake based on the user's desired risk amount and the stop-loss distance.
- Formula: `Stake (£/point) = Risk Amount (£) ÷ Stop Distance (points)`
- The system must enforce minimum and maximum stake sizes per broker.

#### Margin Requirements (FCA-Mandated)

The UK's Financial Conduct Authority (FCA) requires minimum margin deposits for spread betting. The platform must enforce these:

| Asset Type | FCA Minimum Margin Rate | What It Means |
|---|---|---|
| Forex (major pairs) | 3.33% | Must deposit £333 to control a £10,000 position |
| Indices | 5% | Must deposit £500 to control a £10,000 position |
| Commodities | 10% | Must deposit £1,000 to control a £10,000 position |
| Individual Shares | 20% | Must deposit £2,000 to control a £10,000 position |
| Cryptocurrency | 50% | Must deposit £5,000 to control a £10,000 position |

#### Guaranteed Stop-Loss Orders

- The platform must support **guaranteed stop-loss orders** through brokers that offer them (e.g., IG Group).
- A guaranteed stop means the position is always closed at exactly the specified price, even if the market gaps overnight. Normal stops can be filled at a worse price.
- Guaranteed stops come with a small premium charged by the broker, which the platform must calculate and display before the trade is placed.
- The **SB Breakout** strategy uses guaranteed stops by default.

#### Overnight Funding Costs

- Holding a spread bet position overnight incurs a daily fee.
- The platform must calculate this cost before placing any trade intended to be held overnight.
- **Formula:** Position Value × (SONIA rate + broker markup) ÷ 365
- The current SONIA (Sterling Overnight Index Average) rate and broker markup must be configured per broker.
- If the overnight cost makes the trade uneconomic over the intended holding period, the trade must be flagged or blocked.

#### Market Hours

- Each spread betting instrument has specific trading hours (e.g., FTSE 100 trades 8:00am–4:30pm UK time).
- The platform must not place spread bets outside these hours.
- Market hours must be maintained per instrument and automatically updated for daylight saving time changes.

#### Gap Protection

- Markets can "gap" — jump from one price to another with no trading in between — typically overnight or over weekends.
- The platform must detect when a market is approaching its close and either:
  - Close the position before the market closes (configurable option), or
  - Reduce position size to limit gap risk

#### Tax-Efficient Routing

- In the UK, spread betting profits are currently exempt from Capital Gains Tax and Income Tax.
- CFD (Contract for Difference) losses, on the other hand, can be offset against other gains.
- The platform must include a **Tax Efficiency Router** that:
  - Routes profitable trades through spread betting instruments (tax-free)
  - Routes trades expected to lose through CFD instruments (losses can be offset)
  - This routing is applied automatically and can be toggled on/off in Settings

---

### 2.8 Paper Trading

Paper trading lets users test strategies with **zero financial risk** using virtual money.

#### Requirements

| Feature | Requirement |
|---|---|
| **Default virtual balance** | $10,000 (configurable by user) |
| **Fee simulation** | Must charge fees matching each exchange's real fee rate (e.g., Binance charges 0.10% per trade) |
| **Slippage simulation** | Must simulate the cost of moving the market when placing an order. Base slippage = 0.05% + additional slippage based on order size relative to volume |
| **Minimum order enforcement** | Must reject paper trades that would be below the real exchange's minimum order size |
| **Balance tracking** | Virtual balance must update in real time after every simulated trade |
| **Trade history** | All paper trades must be stored and displayed identically to live trades |
| **Performance metrics** | Win rate, total P&L, Sharpe ratio, max drawdown, and all other analytics must work in paper mode |
| **Seamless switching** | User must be able to switch between paper and live mode without restarting the system |

#### Why This Matters

Paper trading with realistic fee and slippage simulation means that a strategy performing well in paper mode has a high probability of performing similarly in live mode. This is far more useful than simple backtesting, which uses only historical data.

---

### 2.9 Live Trading

When the user switches from paper to live mode, additional safety controls are enforced.

#### Safety Controls

| Control | What It Does |
|---|---|
| **Paper/Live toggle** | A clear, prominent switch that must be manually toggled. Default is always paper mode. |
| **Circuit breaker** | Stops all live trading automatically after 5 consecutive trade failures and waits 5 minutes before resuming |
| **Rate limiter** | Caps trade execution at a maximum of 10 trades per minute to prevent runaway loops |
| **Max order size cap** | A hard limit on the maximum size of any single live order, configurable per exchange |
| **Allowed exchange whitelist** | Only exchanges that the user has explicitly activated can receive live orders |
| **Full audit trail** | Every live order must be logged with timestamp, exchange, symbol, direction, size, price, fee, and outcome |

#### What Happens When Things Go Wrong

- If an order fails to execute, it is retried once. If it fails again, the circuit breaker count increases.
- If the exchange returns an error, the full error message is logged.
- If the daily loss limit is hit, all live trading stops for the rest of the day and the user is notified.
- If the kill switch is triggered, every open position can optionally be closed immediately (configurable).

---

### 2.10 Market Data & Signals

The platform pulls data from multiple external sources to inform trading decisions.

| Data Source | What It Provides | Which Assets Use It |
|---|---|---|
| **Fear & Greed Index** (alternative.me) | A 0–100 score measuring overall crypto market sentiment. Values below 25 = Extreme Fear (potential buy); above 75 = Extreme Greed (potential sell) | Cryptocurrency |
| **CoinGecko API** | Real-time prices, trending coins, global crypto market capitalisation and dominance data | Cryptocurrency |
| **CoinDesk RSS** | Crypto news headlines and articles in real time | Cryptocurrency |
| **CoinTelegraph RSS** | Crypto news headlines and breaking market news | Cryptocurrency |
| **Decrypt RSS** | Crypto and Web3 news | Cryptocurrency |
| **Bitcoin Magazine RSS** | Bitcoin-specific news and analysis | Bitcoin / Crypto |
| **Trading Economics RSS** | Economic calendar events (e.g., interest rate decisions, inflation data, jobs reports) | Forex, Stocks, Indices |
| **yfinance** | Stock price history, fundamentals (P/E ratio, revenue, earnings), dividends | Stocks |
| **Yahoo Finance RSS** | Stock market news and company-specific news | Stocks |
| **BBC Business RSS** | General UK and global business news | Stocks, Indices |
| **Reuters RSS** | Global financial and business news | All asset types |
| **EIA (Energy Information Administration)** | US energy supply and demand data; weekly oil and gas inventory reports | Commodities |
| **Social Sentiment** | Simulated sentiment data with neutral defaults (real social data integration planned for future) | All asset types |
| **Index Breadth Data** | Simulated data measuring how many stocks within an index are rising vs falling | Indices |

#### How News Affects Trading

1. The **News Impact Assessment** module reads headlines every cycle.
2. Headlines are scored for relevance and likely market impact.
3. If a high-impact event is detected (e.g., a central bank emergency rate change), trading is **halted** for the affected asset.
4. If a medium-impact event is detected, the trade **proceeds with caution** (smaller size, tighter stop).
5. Low-impact news is noted in the log but does not affect trading.

---

## 3. User Interface Requirements

---

### 3.1 Pages

The application has **15 pages**. All pages are accessible from the main navigation.

---

#### Dashboard

The home page. Shows the user a complete overview of their trading activity at a glance.

**User can:**
- See total portfolio value and today's profit/loss
- See a summary of all open positions
- See recent trade history
- See the current status of the auto-trader (running/stopped)
- View key market indicators (Fear & Greed Index, BTC dominance, market trend)
- See alerts and system notifications
- Navigate quickly to any other page

---

#### Smart Trading

An intelligent trade assistant that helps the user find and execute the best trade for a given symbol.

**User can:**
- Enter any trading symbol (e.g., BTC/USDT, AAPL, EUR/USD)
- Get an AI-generated recommendation including: suggested strategy, position size, entry price, stop loss, and take profit
- See a breakdown of all intelligence module outputs for that symbol
- Review the multi-timeframe analysis
- Place the recommended trade with one click, or adjust any parameters before confirming

---

#### Trading

The manual trading interface for users who want direct control.

**User can:**
- Select any connected exchange
- Search for any instrument
- View a live price chart with technical indicators
- Choose a strategy and see its current signal
- Manually set order type (market/limit), size, stop loss, and take profit
- Place buy or sell orders directly
- View and cancel open orders

---

#### Exchanges

Manage all exchange connections.

**User can:**
- See all 18 supported exchanges and their connection status
- Add API keys for any exchange (paper or live)
- Test a connection to verify credentials are working
- Enable or disable individual exchanges
- View the fee rate and supported features for each exchange
- Switch any exchange between paper and live mode

---

#### Trade History

A full record of every trade ever placed.

**User can:**
- Browse all past trades in a sortable, filterable table
- Filter by exchange, symbol, strategy, date range, or outcome (win/loss)
- See the full details of any individual trade including entry, exit, fees, and P&L
- Export trade history to CSV
- See summary statistics (total trades, win rate, average profit/loss)

---

#### Backtesting

Test any strategy against historical price data to see how it would have performed.

**User can:**
- Select any strategy and any symbol
- Choose a historical date range
- Configure the strategy parameters (e.g., RSI period, stop loss %)
- Run the backtest
- See detailed results: total return, win rate, max drawdown, Sharpe ratio, number of trades
- View a chart showing all backtest trades on the price chart
- Compare multiple strategies side by side

---

#### Analytics

Deep performance analysis across all trading activity.

**User can:**
- See portfolio performance over time on a chart
- View performance broken down by exchange, strategy, symbol, or time period
- See key metrics: total P&L, Sharpe ratio, Sortino ratio, max drawdown, win rate, average trade duration
- Identify the best and worst performing strategies and instruments
- View a heatmap of performance by day and hour of the week

---

#### Signals & AI

Real-time view of all signal activity across all strategies and intelligence modules.

**User can:**
- See the current signal (BUY/SELL/HOLD) from every strategy for every monitored symbol
- See the current output of each intelligence module
- View the multi-timeframe consensus for any symbol
- See the AI's current market assessment and strategy recommendation
- View recent news and sentiment data
- Track how signal accuracy changes over time

---

#### Auto-Trader

Control and monitor the fully automated trading system.

**User can:**
- Start and stop the auto-trader
- Set the trading interval (how often it checks for opportunities)
- Configure which exchanges and symbols to include
- Set trading mode (paper or live)
- View a real-time log of every decision made (with full reasoning)
- Use the kill switch to stop all trading immediately
- See counts of each decision type (how many trades executed, how many blocked by risk, etc.)

---

#### Optimizer

Find the best settings for any strategy automatically.

**User can:**
- Select any strategy and optimise its parameters
- Define the parameter ranges to search (e.g., test RSI with periods from 7 to 21)
- Run the optimiser and watch it test thousands of parameter combinations
- See a ranked list of the best-performing parameter sets
- Apply the best settings to the live strategy with one click
- Schedule automatic re-optimisation to run periodically

---

#### Alerts

Configure notifications for important events.

**User can:**
- Create custom alerts triggered by price levels, strategy signals, or system events
- Choose how alerts are delivered (e.g., email, SMS, webhook, in-app notification)
- Set alert conditions: price above/below, % change, specific signal type, loss limit hit
- View a history of all past alerts that were triggered
- Enable/disable individual alerts

---

#### System Alerts

Monitor the health and operational status of the trading system.

**User can:**
- See all system-level warnings and errors (exchange connection failures, data feed issues, etc.)
- View the circuit breaker status
- See if any exchanges are having issues connecting or responding slowly
- View the rate limiter status
- See any configuration problems that need attention
- Clear resolved alerts

---

#### Spread Betting

Dedicated interface for spread betting operations.

**User can:**
- Browse available spread betting instruments (indices, forex, commodities, shares)
- See current spread (bid-ask difference) for any instrument in real time
- Calculate position size in £/point for a given risk amount
- View the estimated overnight funding cost for any position
- Check margin requirements before placing a trade
- Access the tax efficiency routing settings
- View all open spread bet positions with daily funding costs shown

---

#### Settings

Configure every aspect of the platform.

**User can:**
- Set all risk management defaults (max drawdown, position size, stop loss, daily loss limit, etc.)
- Configure asset-specific risk rules per asset class
- Enable or disable individual intelligence modules
- Set the default trading interval for the auto-trader
- Configure the overnight funding rate (SONIA + broker markup) per broker
- Set up notification delivery channels
- Toggle dark/light mode
- Reset all settings to factory defaults
- Export and import the entire configuration as a JSON file

---

#### 404 (Not Found)

Shown when a user navigates to a page that doesn't exist.

**User can:**
- See a clear message that the page doesn't exist
- Navigate back to the Dashboard with one click

---

### 3.2 Design

#### Visual Theme

- **Default theme:** Dark trading terminal — dark backgrounds with bright data highlights, mimicking professional trading platforms (Bloomberg, TradingView)
- **Light mode:** Available as an option in Settings
- All colour choices must maintain sufficient contrast for readability

#### Real-Time Updates

- The interface must update live data **without the user needing to refresh the page**
- Live updates are delivered via **WebSocket connection**
- The following must update in real time: portfolio value, open positions P&L, auto-trader decision log, price charts, signals, system alerts
- If the WebSocket connection is lost, the UI must show a warning and attempt to reconnect automatically

#### Layout & Responsiveness

- The layout must work on desktop screens (primary target: 1440px wide)
- Must be usable on laptop screens (1024px wide) without horizontal scrolling
- Mobile support is a secondary goal; the most important pages (Dashboard, Auto-Trader) must be readable on a phone screen
- Navigation must always be visible; the user should be able to reach any page in one click from any other page

#### Data Tables

- All data tables (trade history, signal table, etc.) must support:
  - Sorting by any column
  - Filtering / searching
  - Pagination for large datasets
  - Column visibility toggles

#### Charts

- Price charts must support standard candlestick (OHLCV) display
- Charts must support adding/removing technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, VWAP)
- Backtest results must be overlaid directly on the price chart (showing entry and exit points)
- All charts must be zoomable and pannable

---

## 4. API Requirements

The platform exposes a REST API that the frontend uses to communicate with the backend. All data flows through this API.

**Total:** 79 endpoints across 14 modules.

| API Module | Endpoint Count | What It Serves |
|---|---|---|
| **Auto-Trader** | ~8 | Start/stop the auto-trader; get current status; retrieve the decision log; trigger the kill switch |
| **Exchanges** | ~10 | List exchanges; connect/disconnect; get balance; fetch ticker and candle data; place and cancel orders |
| **Strategies** | ~6 | List available strategies; get the current signal for a strategy; run a strategy manually on a symbol |
| **Intelligence** | ~8 | Get the current output of any intelligence module; run the full intelligence pipeline on a symbol |
| **Backtesting** | ~4 | Run a backtest; retrieve backtest results; compare multiple strategies |
| **Optimizer** | ~4 | Start an optimisation run; retrieve results; apply best settings |
| **Trade History** | ~4 | Retrieve all trades; filter trades; export to CSV |
| **Analytics** | ~6 | Fetch portfolio performance metrics; strategy performance; time-of-day analysis |
| **Signals** | ~5 | Get current signals across all strategies and symbols; get multi-timeframe consensus |
| **Alerts** | ~6 | Create, update, delete, and list alerts; view alert history |
| **Spread Betting** | ~5 | Spread betting-specific endpoints: calculate position size, overnight cost, margin check |
| **Settings** | ~4 | Read and write all configuration settings |
| **System** | ~5 | Health check; system status; circuit breaker status; version info |
| **Market Data** | ~4 | Fetch news; get Fear & Greed data; get economic calendar |

#### API Standards

- All endpoints return **JSON** responses
- All endpoints use standard HTTP status codes (200 OK, 400 Bad Request, 401 Unauthorised, 500 Server Error)
- Errors always return a JSON object with a `message` field explaining what went wrong
- All list endpoints support pagination via `page` and `limit` query parameters
- Endpoints that trigger long-running operations (backtest, optimiser) return a job ID immediately; the result is polled or delivered via WebSocket

---

## 5. Testing Requirements

The platform maintains **1,237 automated tests** across 3 test suites. All tests must pass before any release.

| Suite | Tests | What It Covers |
|---|---|---|
| **Unit Tests** | ~600 | Tests individual functions in isolation. Covers: every strategy's signal logic, every intelligence module's calculation, all risk rule evaluations, position sizing formulas, fee calculations, overnight funding calculations, Kelly Criterion maths, and all utility functions |
| **Integration Tests** | ~400 | Tests how components work together. Covers: exchange adapter → order placement flow; intelligence pipeline end-to-end; auto-trader decision cycle; data feed ingestion; settings persistence; paper trading simulation accuracy |
| **End-to-End Tests** | ~237 | Tests full user workflows through the API. Covers: complete trade lifecycle (signal → intelligence check → risk check → order → history); backtest run from start to result; optimiser cycle; alert creation and triggering; kill switch behaviour |

#### Test Standards

- Tests must run in under 10 minutes on standard hardware
- Exchange API calls in tests must use mocks (no real API calls during automated testing)
- Test coverage must remain above 80% for all core trading logic
- Any new strategy, intelligence module, or risk rule must be accompanied by tests before merging

---

## 6. Deployment Requirements

The platform can be deployed in three ways.

#### Option 1: Local (Development)

- Run directly with Python and a package manager
- Requires: Python 3.9+, Node.js 18+
- All configuration via environment variables or a local `.env` file
- Suitable for: developers, testing, personal use

#### Option 2: Docker

- Full platform packaged as Docker containers
- A single `docker-compose up` command starts the entire stack
- Includes: backend API, frontend, and any background workers
- Suitable for: self-hosted production use, home servers, VPS deployment

#### Option 3: AWS

- Infrastructure-as-code deployment to Amazon Web Services
- Suitable for: cloud-hosted production, teams, 24/7 uptime requirements

#### Environment Variables

The following must be configurable via environment variables (never hard-coded):

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Application security key for session signing |
| `DATABASE_URL` | Location of the trade history and configuration database |
| `ALLOWED_ORIGINS` | Domains allowed to make API calls (CORS) |
| `PAPER_TRADING_MODE` | Default to paper (true) or live (false) mode |
| `LOG_LEVEL` | Verbosity of system logs (DEBUG, INFO, WARNING, ERROR) |
| Per-exchange API key variables | One pair per exchange: `BINANCE_API_KEY`, `BINANCE_SECRET`, etc. |
| `SONIA_RATE` | Current SONIA rate for overnight funding calculations |

---

## 7. Performance Requirements

#### Auto-Trader

| Metric | Requirement |
|---|---|
| **Full decision cycle time** | Must complete one full cycle (data fetch → all intelligence modules → risk checks → order if needed) in under 30 seconds for a single symbol |
| **Multi-symbol parallelism** | Must be able to run the pipeline for multiple symbols concurrently |
| **Minimum interval** | Must support a 1-minute interval with consistent, on-time execution |

#### API

| Metric | Requirement |
|---|---|
| **Standard endpoints** | Must respond in under 500ms for all standard data retrieval endpoints |
| **Order placement** | Must submit an order to the exchange within 2 seconds of receiving the API request |
| **Backtest** | A 1-year backtest on daily candles must complete in under 60 seconds |

#### WebSocket

| Metric | Requirement |
|---|---|
| **Update frequency** | Portfolio value and P&L must update at least every 5 seconds |
| **Auto-trader log** | Decision log entries must appear in the UI within 1 second of being written |
| **Reconnection** | Must reconnect automatically within 5 seconds of a WebSocket disconnection |

#### Database

| Metric | Requirement |
|---|---|
| **Trade history queries** | Must return up to 10,000 trade records in under 1 second |
| **Analytics aggregation** | Performance analytics for 1 year of trades must calculate in under 5 seconds |

---

## 8. Security Requirements

#### API Key Storage

- Exchange API keys and secrets must **never** be stored in plain text.
- API keys must be encrypted at rest using AES-256 or equivalent.
- Keys must only be decrypted in memory at the moment they are needed for an API call.
- Keys must never appear in logs, error messages, or API responses.

#### CORS (Cross-Origin Resource Sharing)

- The API must reject requests from origins not listed in the `ALLOWED_ORIGINS` environment variable.
- In production, wildcard origins (`*`) must not be permitted.

#### Exchange Credential Handling

- When a user enters API credentials on the Exchanges page, they are submitted over HTTPS only.
- The system must test the credentials before storing them (a failed test rejects the save).
- Read-only API keys must be used wherever possible (e.g., for data-only connections that don't place orders).
- The user must explicitly enable "allow trading" for any API key before the system will place live orders with it.

#### Authentication

- The application must require authentication to access any page or API endpoint.
- Sessions must expire after a configurable period of inactivity.
- API requests must include a valid session token or API bearer token.

#### Audit Logging

- Every live trade placed must be recorded with: timestamp, user session, exchange, symbol, direction, size, price, and outcome.
- Every settings change must be logged with: timestamp, what changed, old value, and new value.
- Audit logs must be read-only and must not be deletable through the normal UI.

#### Data Validation

- All user inputs (strategy parameters, risk settings, API credentials) must be validated server-side before being stored or used.
- Numeric inputs must have enforced minimums and maximums to prevent accidental extreme values.
- The system must reject any order where the calculated position size exceeds the configured maximum, even if a UI bug allows it to be submitted.

---

*End of Product Requirements Document*

---

> **Document Metadata**
>
> | Field | Value |
> |---|---|
> | Product | AlgoTrader |
> | Version | 1.0 |
> | Total codebase | 38,000 lines |
> | Exchanges | 18 |
> | Strategies | 16 |
> | Intelligence modules | 32 |
> | UI pages | 15 |
> | API endpoints | 79 |
> | Automated tests | 1,237 |
