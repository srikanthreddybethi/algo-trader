# AlgoTrader — Architecture & Systems

> **Last updated:** March 2026 — reflects the live codebase at 38,000 lines of code.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Backend Architecture](#3-backend-architecture)
4. [Database Schema](#4-database-schema)
5. [Exchange Integration Layer](#5-exchange-integration-layer)
6. [Trading Strategy Engine](#6-trading-strategy-engine)
7. [Orchestrator — 10-Step Decision Pipeline](#7-orchestrator--10-step-decision-pipeline)
8. [Data Pipeline](#8-data-pipeline)
9. [Risk Management](#9-risk-management)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Fee Structure](#11-fee-structure)
12. [Testing](#12-testing)
13. [Deployment](#13-deployment)

---

## 1. System Overview

AlgoTrader is a full-stack autonomous trading platform built for retail traders who want algorithmic execution with real-time intelligence. The system combines quantitative strategies with AI-powered decision-making across 18 exchanges, 5 asset classes, and 16 trading strategies.

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend framework | React | 18.x |
| Frontend language | TypeScript | 5.x |
| Frontend bundler | Vite | 5.x |
| Frontend styling | Tailwind CSS + shadcn/ui | — |
| Backend framework | FastAPI | 0.111+ |
| Backend language | Python | 3.11 |
| Database ORM | SQLAlchemy (async) | 2.x |
| Database engine | SQLite | 3.x |
| Exchange library | CCXT async | Latest |
| AI providers | Claude (Anthropic) / Gemini (Google) | — |
| Real-time | WebSockets (native FastAPI) | — |
| Server state | TanStack Query | v5 |

### Scale Metrics

| Metric | Count |
|--------|-------|
| Total lines of code | 38,000 |
| Backend Python LOC | 16,650 |
| Frontend TypeScript/React LOC | ~21,350 |
| Exchanges supported | 18 |
| Trading strategies | 16 |
| Intelligence/analysis modules | 32 |
| Frontend pages | 15 |
| API routers | 14 |
| API endpoints | 79 |
| Test cases | 1,237 |
| Test pass rate | 100% |

### Deployment Targets

- **Local** — Development mode with hot reload
- **Docker** — Multi-stage containerised build
- **AWS** — EC2, ECS, or App Runner

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ALGOTRADER SYSTEM                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────┐         ┌──────────────────────────────┐  │
│  │   FRONTEND (React)   │  HTTP   │     FASTAPI BACKEND          │  │
│  │                      │ ──────► │                              │  │
│  │  React 18 + Vite     │  WS     │  main.py                     │  │
│  │  TypeScript          │ ◄────── │    ├── 14 API Routers        │  │
│  │  Tailwind + shadcn   │         │    ├── WebSocket endpoint     │  │
│  │  TanStack Query      │         │    └── Lifespan events        │  │
│  │  15 Pages            │         │                              │  │
│  └──────────────────────┘         └──────────┬───────────────────┘  │
│                                              │                      │
│                         ┌────────────────────┼─────────────────┐    │
│                         │                    │                 │    │
│                         ▼                    ▼                 ▼    │
│              ┌────────────────┐  ┌────────────────┐  ┌──────────┐  │
│              │  SERVICES      │  │  EXCHANGE      │  │ DATABASE │  │
│              │  LAYER         │  │  LAYER         │  │          │  │
│              │                │  │                │  │ SQLite   │  │
│              │ Orchestrator   │  │ ExchangeManager│  │ + SQLAlch│  │
│              │ Intelligence   │  │  ├─ CCXT (9)   │  │          │  │
│              │ AdaptiveIntel  │  │  ├─ Custom (8) │  │ portfoli │  │
│              │ InstrumentIntel│  │  └─ Alpaca (1) │  │ position │  │
│              │ SpreadBetting  │  │                │  │ orders   │  │
│              │ AssetRules     │  │ Data Feeds:    │  │ trades   │  │
│              │ PaperTrading   │  │  Fear & Greed  │  │ alerts   │  │
│              │ AIDecisionLayer│  │  CoinGecko     │  │ snapshots│  │
│              │ Alerting       │  │  RSS News      │  │ exchanges│  │
│              └────────────────┘  │  Econ Calendar │  └──────────┘  │
│                                  │  Fundamentals  │                 │
│                                  └────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
Browser Request
      │
      ▼
FastAPI Router (async handler)
      │
      ├──► Service Layer (business logic)
      │         │
      │         ├──► Exchange Manager (market data / order execution)
      │         ├──► Intelligence Pipeline (pre-trade checks)
      │         ├──► Paper Trading Engine (simulated orders)
      │         └──► Database (SQLAlchemy async session)
      │
      ▼
JSON Response (or WebSocket message)
```

---

## 3. Backend Architecture

### Application Entry Point

The backend starts from `backend/app/main.py`, which:
1. Creates the FastAPI application instance
2. Registers all 14 API routers with their URL prefixes
3. Configures CORS for the frontend (Vite dev server + production)
4. Opens a WebSocket endpoint at `/ws/prices`
5. Initialises the database on startup via lifespan context

### 14 API Routers

| Router Module | URL Prefix | Approximate Endpoints | Purpose |
|--------------|------------|----------------------|---------|
| `portfolio` | `/api/portfolio` | 8 | Portfolio CRUD, snapshots, balance |
| `trading` | `/api/trading` | 10 | Manual buy/sell, order management |
| `strategies` | `/api/strategies` | 6 | Strategy list, backtest, params |
| `exchanges` | `/api/exchanges` | 8 | Exchange list, connect, test keys |
| `signals` | `/api/signals` | 7 | Fear & Greed, regime, AI analysis |
| `auto_trader` | `/api/auto-trader` | 8 | Start/stop orchestrator, config |
| `intelligence` | `/api/intelligence` | 6 | Scores, memory, adaptive status |
| `backtest` | `/api/backtest` | 4 | Run backtests, results |
| `analytics` | `/api/analytics` | 6 | Performance metrics, risk stats |
| `alerts` | `/api/alerts` | 6 | Price alert CRUD |
| `system_alerts` | `/api/system-alerts` | 5 | System monitoring, unread counts |
| `optimizer` | `/api/optimizer` | 4 | Strategy rankings, run optimizer |
| `spread_betting` | `/api/spread-betting` | 6 | SB sizing, margin, funding |
| `smart_trading` | `/api/smart-trading` | 5 | Asset classification, validation |

**Total: 79 endpoints**

### Async Architecture

The entire backend is async-first:

```python
# All route handlers use async/def
@router.get("/portfolio")
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    ...

# Exchange calls are fully async (ccxt.async_support)
import ccxt.async_support as ccxt

# Database operations use AsyncSession
async with async_session() as db:
    result = await db.execute(select(Portfolio))
```

### Service Layer Pattern

```
app/
├── main.py                     # FastAPI app + router registration
├── core/
│   ├── database.py             # SQLAlchemy engine + session factory
│   └── config.py               # Environment variable loading
├── models/
│   ├── portfolio.py            # SQLAlchemy ORM models
│   ├── position.py
│   ├── order.py
│   └── trade.py
├── routers/                    # 14 FastAPI routers
├── services/
│   ├── orchestrator.py         # 10-step autonomous trading loop (1,081 lines)
│   ├── intelligence.py         # 5 self-learning modules (632 lines)
│   ├── adaptive_intelligence.py# 7 adaptive modules (467 lines)
│   ├── instrument_intelligence.py # 4 instrument modules (490 lines)
│   ├── ai_decision_layer.py    # Claude/Gemini integration (370 lines)
│   ├── spread_betting.py       # 7 SB components (1,011 lines)
│   ├── asset_trading_rules.py  # 5 asset rules engines (920 lines)
│   ├── paper_trading.py        # Simulated order execution (508 lines)
│   ├── position_manager.py     # Stop/TP/trailing management
│   └── alerting.py             # 4-plugin alert system
├── exchanges/
│   ├── manager.py              # Unified exchange interface (755 lines)
│   └── connectors/
│       ├── base.py             # BaseConnector interface
│       ├── ig_connector.py
│       ├── ibkr_connector.py
│       ├── oanda_connector.py
│       ├── trading212_connector.py
│       ├── etoro_connector.py
│       ├── saxo_connector.py
│       ├── capital_connector.py
│       └── cmc_connector.py
├── strategies/
│   ├── base.py                 # BaseStrategy interface
│   ├── builtin.py              # 11 quantitative strategies (310 lines)
│   ├── spread_betting_strategies.py # 5 SB strategies (585 lines)
│   └── pure_ai.py              # AI-driven strategy
└── services/signals/
    ├── data_feeds.py           # Fear & Greed, news, social
    ├── ai_engine.py            # Claude/Gemini AI wrapper
    └── regime_detector.py      # Market regime classification
```

---

## 4. Database Schema

The database uses SQLite with SQLAlchemy async ORM. All tables are created via `Base.metadata.create_all()` on startup.

### Table: `portfolios`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment primary key |
| `name` | String | Portfolio display name |
| `exchange_name` | String | Associated exchange ID |
| `initial_balance` | Float | Starting capital (default $10,000) |
| `cash_balance` | Float | Available cash for new trades |
| `total_value` | Float | cash + open position value |
| `created_at` | DateTime | Creation timestamp (UTC) |
| `updated_at` | DateTime | Last modification timestamp |

### Table: `positions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `portfolio_id` | Integer (FK→portfolios) | Owning portfolio |
| `symbol` | String | Trading pair (e.g. `BTC/USDT`) |
| `exchange_name` | String | Exchange where position lives |
| `quantity` | Float | Units held (or £/point for SB) |
| `avg_entry_price` | Float | Volume-weighted average entry |
| `current_price` | Float | Latest mark-to-market price |
| `is_open` | Boolean | True if position is active |
| `stop_loss` | Float (nullable) | Stop-loss price level |
| `take_profit` | Float (nullable) | Take-profit price level |
| `trailing_stop_pct` | Float (nullable) | Trailing stop % distance |
| `strategy_name` | String | Strategy that opened it |
| `opened_at` | DateTime | Entry timestamp |
| `closed_at` | DateTime (nullable) | Exit timestamp |

### Table: `orders`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `portfolio_id` | Integer (FK→portfolios) | Owning portfolio |
| `symbol` | String | Trading pair |
| `exchange_name` | String | Exchange |
| `side` | String | `buy` or `sell` |
| `order_type` | String | `market` or `limit` |
| `quantity` | Float | Order size |
| `price` | Float (nullable) | Limit price (null for market) |
| `status` | String | `pending`, `filled`, `cancelled` |
| `strategy_name` | String (nullable) | Originating strategy |
| `created_at` | DateTime | Order placement time |
| `filled_at` | DateTime (nullable) | Execution time |

### Table: `trades`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `portfolio_id` | Integer (FK→portfolios) | Owning portfolio |
| `symbol` | String | Trading pair |
| `exchange_name` | String | Exchange |
| `side` | String | `buy` or `sell` |
| `quantity` | Float | Executed size |
| `price` | Float | Execution price |
| `fee` | Float | Commission paid |
| `pnl` | Float (nullable) | Realised P&L (on close) |
| `strategy_name` | String (nullable) | Strategy used |
| `executed_at` | DateTime | Trade execution timestamp |

### Table: `alerts`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `symbol` | String | Asset to monitor |
| `exchange_name` | String | Exchange |
| `condition` | String | `above` or `below` |
| `target_price` | Float | Trigger price |
| `is_active` | Boolean | Whether alert is armed |
| `triggered_at` | DateTime (nullable) | When it fired |
| `created_at` | DateTime | Creation time |

### Table: `portfolio_snapshots`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `portfolio_id` | Integer (FK→portfolios) | Owning portfolio |
| `total_value` | Float | Portfolio value at snapshot time |
| `cash_balance` | Float | Cash component |
| `open_positions_value` | Float | Unrealised position value |
| `snapshot_at` | DateTime | Snapshot timestamp |

### Table: `exchanges` (configuration store)

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `name` | String (unique) | Exchange identifier (e.g. `binance`) |
| `api_key` | String (encrypted) | API key |
| `api_secret` | String (encrypted) | API secret |
| `is_testnet` | Boolean | Use testnet endpoint |
| `is_active` | Boolean | Exchange is enabled |
| `extra_config` | JSON | Exchange-specific extras (e.g. passphrase) |

---

## 5. Exchange Integration Layer

### 5.1 Unified Exchange Manager

`backend/app/exchanges/manager.py` provides a single interface for all 18 exchanges. Every service in the system calls `exchange_manager.*` without needing to know whether the underlying exchange uses CCXT, a custom connector, or Alpaca.

**Routing logic:**

```python
# manager.py routing
EXCHANGE_CONFIGS = { ... }  # Registry of all 18 exchanges

async def get_ticker(exchange: str, symbol: str) -> Dict:
    if exchange in CCXT_EXCHANGES:      # binance, bybit, kraken, ...
        return await _ccxt_ticker(exchange, symbol)
    elif exchange in CONNECTOR_EXCHANGES:  # ig, ibkr, oanda, ...
        return await ALL_CONNECTORS[exchange].get_ticker(symbol)
    elif exchange == "alpaca":
        return await _alpaca_ticker(symbol)

async def place_order(exchange: str, order: Dict) -> Dict:
    # Same pattern — routes to correct backend
```

**Key manager methods:**

| Method | Description |
|--------|-------------|
| `get_ticker(exchange, symbol)` | Latest bid/ask/last price |
| `get_ohlcv(exchange, symbol, timeframe, limit)` | Candlestick data |
| `place_order(exchange, order_dict)` | Execute market or limit order |
| `get_balance(exchange)` | Account balance |
| `get_open_positions(exchange)` | Current live positions |
| `test_connection(exchange, keys)` | Validate API credentials |

---

### 5.2 CCXT Crypto Exchanges (9)

All nine crypto exchanges use `ccxt.async_support` under the hood. The exchange manager initialises them lazily from stored API keys.

| Exchange | Display Name | FCA Status | Taker Fee | Maker Fee | Min Order | Testnet |
|----------|-------------|-----------|-----------|-----------|-----------|---------|
| `binance` | Binance | Not FCA regulated | 0.10% | 0.10% | $10 | Yes |
| `bybit` | Bybit | FCA-approved (via Archax) | 0.10% | 0.10% | $5 | Yes |
| `kraken` | Kraken | FCA-registered + EMI | 0.26% | 0.16% | $10 | No |
| `coinbase` | Coinbase | FCA-registered | 0.60% | 0.40% | $10 | No |
| `okx` | OKX | Not FCA regulated | 0.08% | 0.05% | $10 | No |
| `cryptocom` | Crypto.com | Not FCA regulated | 0.075% | 0.05% | $10 | No |
| `bitstamp` | Bitstamp | FCA-registered | 0.40% | 0.30% | $25 | No |
| `gate` | Gate.io | Not FCA regulated | 0.10% | 0.10% | $10 | No |
| `gemini` | Gemini | Not FCA regulated | 0.35% | 0.20% | $10 | No |

**CCXT exchange instantiation:**

```python
# From exchanges/manager.py
import ccxt.async_support as ccxt

exchange_instance = ccxt.binance({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True,
    "options": {"defaultType": "spot"},
})
```

---

### 5.3 Custom Connector Exchanges (8)

Each non-CCXT exchange implements the `BaseConnector` interface from `connectors/base.py`.

**BaseConnector interface:**

```python
class BaseConnector:
    async def get_ticker(self, symbol: str) -> Dict: ...
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List: ...
    async def place_order(self, order: Dict) -> Dict: ...
    async def get_balance(self) -> Dict: ...
    async def get_open_positions(self) -> List: ...
    async def test_connection(self) -> bool: ...
    def set_credentials(self, api_key: str, api_secret: str, **kwargs): ...
```

| Exchange | Key | Category | API Type | Auth Method | FCA Status | Min Order |
|----------|-----|----------|----------|-------------|-----------|-----------|
| IG Group | `ig` | Spread Betting | REST + Lightstreamer | Username/Password/API key | FCA authorised | £50 |
| Capital.com | `capital` | Spread Betting | REST | API key + password | FCA authorised | £20 |
| CMC Markets | `cmc` | Spread Betting | REST | API key + secret | FCA authorised | £20 |
| Interactive Brokers | `ibkr` | Multi-Asset | Client Portal API | TWS/Gateway session | FCA authorised | $100 |
| eToro | `etoro` | Multi-Asset | REST | OAuth2 | FCA authorised | $50 |
| Saxo Bank | `saxo` | Multi-Asset | OpenAPI | OAuth2 | FCA authorised | $100 |
| OANDA | `oanda` | Forex | v20 REST | Bearer token | FCA authorised | $1 |
| Trading 212 | `trading212` | Stocks | REST | API key | FCA authorised | £1 |

**Connector specifics:**

- **IG Group**: Uses the IG REST API for order management, with Lightstreamer for real-time price streaming. Supports CFDs, spread bets, and options. Requires username + password + API key.
- **Capital.com**: Full REST API with session-based auth. Supports forex, indices, stocks, crypto CFDs.
- **CMC Markets**: REST API with market-maker pricing. CFDs and spread betting across 12,000+ instruments.
- **Interactive Brokers**: Client Portal Web API, routed through a locally running IBKR Gateway session. Supports stocks, options, futures, forex, bonds globally.
- **OANDA**: The fxTrade v20 API is the industry standard for retail forex. Supports fractional pips and micro-lots ($1 minimum).
- **Saxo Bank**: SaxoOpenAPI covers equities, forex, options, futures, bonds. Uses OAuth2 for token-based authentication.
- **eToro**: Social trading platform with REST API. 1% spread on most instruments.
- **Trading 212**: Commission-free UK broker with fractional shares. REST API with simple key-based auth.

---

### 5.4 Alpaca

Alpaca (`alpaca`) is handled directly by the exchange manager without a custom connector, using the `alpaca-trade-api` or `alpaca-py` library.

| Feature | Detail |
|---------|--------|
| Asset classes | US Stocks, ETFs, Options, Crypto |
| Commission | Free (stocks/ETFs) |
| Min order | $1 |
| Taker fee | 0.00% |
| API type | REST + WebSocket |
| Paper trading | Built-in paper account |
| Market data | IEX, SIP feeds |

---

## 6. Trading Strategy Engine

### 6.1 Quantitative Strategies (11)

All quantitative strategies extend `BaseStrategy` from `strategies/base.py` and implement `generate_signals(df, params) -> DataFrame`. The output DataFrame must include a `signal` column: `1` = buy, `-1` = sell, `0` = hold.

| # | Strategy Name | Category | Description | Key Parameters |
|---|--------------|----------|-------------|----------------|
| 1 | SMA Crossover | Trend | Buy when short SMA crosses above long SMA | short_window=20, long_window=50 |
| 2 | EMA Crossover | Trend | Exponential MA crossover — more reactive than SMA | short_window=9, long_window=21 |
| 3 | RSI | Mean Reversion | Buy oversold, sell overbought via Relative Strength Index | period=14, oversold=30, overbought=70 |
| 4 | MACD | Trend/Momentum | Signal line crossover on MACD histogram | fast=12, slow=26, signal=9 |
| 5 | Bollinger Bands | Mean Reversion | Trade price touching/crossing standard deviation bands | window=20, std_dev=2.0 |
| 6 | Mean Reversion | Mean Reversion | Fade moves beyond Z-score threshold | window=20, std_dev=2.5 |
| 7 | Momentum | Momentum | Buy assets with strong recent returns | lookback=14, threshold=0.03 |
| 8 | VWAP | Intraday | Trade mean reversion around Volume-Weighted Avg Price | deviation=0.5 |
| 9 | DCA | Accumulation | Dollar-cost average on regular intervals | interval_bars=12, amount_pct=3 |
| 10 | Grid Trading | Range | Place buy/sell grids at regular price intervals | grid_size=10, grid_spacing=1.5 |
| 11 | Pure AI | AI-Driven | Delegates signal generation entirely to Claude/Gemini | aggression=moderate |

### 6.2 Spread Betting Strategies (5)

Spread betting strategies are defined in `strategies/spread_betting_strategies.py` and differ from quantitative strategies in three key ways:
1. They compute ATR-based stop distances (not fixed percentages)
2. They are market-hours aware and avoid entering near session close
3. They signal in terms of direction (`long`/`short`) rather than quantity

| # | Strategy Name | Type | Best For | Stop Method | Typical Hold |
|---|--------------|------|----------|-------------|-------------|
| 1 | SB Trend Rider | Trend-following | Trending indices & forex | 1.5× ATR trailing | Hours to days |
| 2 | SB Mean Reversion | Mean reversion | Range-bound forex pairs | 2× ATR fixed | Hours |
| 3 | SB Momentum Scalper | Momentum scalping | Volatile session opens | ADX > 25, 1× ATR | Minutes to hours |
| 4 | SB Breakout (Guaranteed Stop) | Breakout | Major news events | Guaranteed stop | Hours |
| 5 | SB Index Surfer | Index-specific | UK100, US500, GER40 | ATR-adjusted | Intraday |

### 6.3 Strategy Registry and Selection

All strategies are registered in `STRATEGY_REGISTRY` (a dict of name → class), loaded at startup:

```python
STRATEGY_REGISTRY = {
    "SMA Crossover": SMA_Crossover,
    "EMA Crossover": EMA_Crossover,
    "RSI": RSI_Strategy,
    "MACD": MACD_Strategy,
    "Bollinger Bands": BollingerBands_Strategy,
    "Mean Reversion": MeanReversion_Strategy,
    "Momentum": Momentum_Strategy,
    "VWAP": VWAP_Strategy,
    "DCA": DCA_Strategy,
    "Grid Trading": GridTrading_Strategy,
    "Pure AI": PureAI_Strategy,
    # Spread betting strategies registered separately
    "SB Trend Rider": SBTrendRider,
    "SB Mean Reversion": SBMeanReversion,
    "SB Momentum Scalper": SBMomentumScalper,
    "SB Breakout": SBBreakout,
    "SB Index Surfer": SBIndexSurfer,
}
```

**Per-asset strategy selection** is handled by `AssetTradingRouter.get_optimal_strategies(symbol, regime)` — each asset class has its own ranked strategy map for each market regime (trending_up, trending_down, ranging, volatile).

**AI strategy selection** can override the ranked list via `ai_select_strategies()` in `ai_decision_layer.py`, which uses Claude/Gemini to reason about current conditions and recent performance.

**Scoreboard adjustment**: strategy weights are dynamically adjusted based on recent live performance scores from `StrategyScoreboard` — a 60%/40% blend of original weight and live score.

---

## 7. Orchestrator — 10-Step Decision Pipeline

The orchestrator (`services/orchestrator.py`) is the autonomous brain. When started, it runs a continuous loop for each configured symbol, executing these 10 steps in order.

```
╔══════════════════════════════════════════════════════════════╗
║            ORCHESTRATOR DECISION PIPELINE                    ║
╠══════════════════════════════════════════════════════════════╣
║  Step 1  │ Losing Streak Check                              ║
║  Step 2  │ Adaptive Exit Level Update                        ║
║  Step 3  │ Position Management (SL / TP / Trailing)          ║
║  Step 4  │ Smart Exit Intelligence (AI + rule-based)         ║
║  Step 5  │ Data Gathering (signals + regime + AI + news)     ║
║  Step 6  │ Portfolio Risk Check                              ║
║  Step 7  │ Asset-Specific Validation                         ║
║  Step 8  │ Strategy Selection (asset-aware + AI + scoreboard)║
║  Step 9  │ Intelligence Pipeline (5 pre-trade checks)        ║
║  Step 10 │ Position Sizing + Trade Execution + Feedback Loop ║
╚══════════════════════════════════════════════════════════════╝
```

### Step 1 — Losing Streak Check

`losing_streak.get_streak()` returns the current consecutive loss count. The position size multiplier is reduced proportionally:

```python
if streak >= 5:
    streak_size_mult = 0.25   # 75% size reduction after 5+ losses
elif streak >= 3:
    streak_size_mult = 0.50   # 50% reduction after 3+ losses
elif streak >= 2:
    streak_size_mult = 0.75   # 25% reduction after 2+ losses
```

A loss analysis is also triggered via `analyze_loss_pattern()` (AI Decision Layer) to identify root causes.

### Step 2 — Adaptive Exit Level Update

`adaptive.exit_levels.get_optimal_levels(current_volatility)` recalculates stop-loss, take-profit, and trailing stop percentages based on the last 200 historical trade outcomes. In volatile markets, wider stops are set; in quiet markets, tighter levels are used. Falls back to `5% SL / 10% TP / 3% trailing` when fewer than 10 historical trades exist.

### Step 3 — Position Management

For every open position, the position manager checks:
- **Stop-loss**: If `current_price <= stop_loss`, close position immediately
- **Take-profit**: If `current_price >= take_profit`, close position
- **Trailing stop**: Ratchets the stop level upward as price rises; triggers when price drops by the trailing distance

### Step 4 — Smart Exit Intelligence

`advise_exit()` from `ai_decision_layer.py` is called for each open position that hasn't been closed by mechanical stops. It considers:
- Current unrealised P&L percentage
- Holding duration
- Current regime and sentiment
- Recent news headlines

Returns: `hold`, `sell`, or `add` with a reasoning string.

### Step 5 — Data Gathering

For each symbol in the watchlist, the orchestrator gathers:

```python
signals_data = await get_all_signals_data(base_currency)
# Returns: fear_greed, social_sentiment, news, economic_calendar, fundamentals

ohlcv_1h = await exchange_manager.get_ohlcv(exchange, symbol, "1h", limit=100)
regime_1h = detect_regime(ohlcv_1h)

ohlcv_4h = await exchange_manager.get_ohlcv(exchange, symbol, "4h", limit=50)
regime_4h = detect_regime(ohlcv_4h)
# If regimes disagree, reduce confidence by 30%

analysis = await get_ai_analysis(signals_data, base_currency)
```

**Step 5B — News Impact Assessment**: If news is present, `assess_news_impact()` is called. If the AI returns `should_halt_trading=True`, the symbol is skipped for this cycle.

**Step 5C — Contrarian Sentiment**:
- Fear & Greed ≤ 10 (extreme fear): +10% position size boost
- Fear & Greed ≥ 90 (extreme greed): −25% position size reduction

### Step 6 — Portfolio Risk Check

`RiskManager.check_portfolio_risk(portfolio_data)` enforces:

| Check | Default Limit | Action if Breached |
|-------|-------------|-------------------|
| Max drawdown | 10% | Block all new trades |
| Daily loss limit | 3% | Block all new trades |
| Max total exposure | 60% | Block new trades |
| Max open positions | 5 | Block new trades |
| Kill switch | n/a | Block all trades |

### Step 7 — Asset-Specific Validation

`asset_router.validate_trade(symbol, direction, **conditions)` routes to the correct rules engine:

| Symbol Pattern | Rules Engine | Key Checks |
|---------------|-------------|-----------|
| BTC, ETH, SOL… | `CryptoTradingRules` | F&G gate, weekend liquidity, BTC dominance |
| EUR/USD, GBP/USD… | `ForexTradingRules` | Session hours, high-impact events, retail sentiment |
| AAPL, MSFT… | `StockTradingRules` | Earnings proximity, market hours, P/E validation |
| FTSE, S&P 500… | `IndexTradingRules` | VIX level, breadth checks, gap risk |
| GOLD, OIL, WHEAT | `CommodityTradingRules` | Seasonal patterns, geopolitical risk |

Returns a `size_multiplier` (0.0 to 1.5) and a list of warnings/blocks.

### Step 8 — Strategy Selection

```python
# 1. Get asset-optimised strategy list
strategies = asset_router.get_optimal_strategies(symbol, regime)

# 2. Adjust weights using live scoreboard
for candidate in strategies:
    live_score = scoreboard.get_live_scores().get(candidate["name"], {}).get("score", 0.5)
    # 60/40 blend: original weight vs live performance
    adjusted_weight = candidate["weight"] * 0.6 + live_score * 0.4

# 3. Optionally override with AI strategy selection
if ai_available:
    strategies = await ai_select_strategies(regime, analysis, strategies, ...)

# 4. Try top 5 candidates, use first that generates a signal
for candidate in strategies[:5]:
    signals = strategy.generate_signals(ohlcv_df, params)
    sig = signals["signal"].tail(3)  # Check last 3 candles
    if sig != 0:
        break
```

### Step 9 — Intelligence Pipeline (5 Pre-Trade Checks)

`intelligence.pre_trade_check(...)` runs all 5 modules in sequence:

```
StrategyScoreboard   → Is this strategy performing well recently?
MultiTimeframeConsensus → Do 15m + 1h + 4h all agree on direction?
CorrelationGuard     → Does this add too much correlated exposure?
KellyCriterion       → What's the optimal position size?
MarketMemory         → Have similar conditions led to losses before?
```

If any check blocks the trade, the cycle logs an `intelligence_block` decision and moves to the next symbol.

### Step 10 — Position Sizing + Execution + Feedback

**Fee-aware position sizing:**
```python
raw_position_value = portfolio.cash_balance * (kelly_position_pct / 100)
# Apply multipliers
raw_position_value *= streak_size_mult * time_size_mult * asset_size_mult
# Deduct estimated round-trip fee
round_trip_cost = estimate_round_trip_cost(exchange, raw_position_value)
position_value = raw_position_value - round_trip_cost
```

**Spread betting path** (IG, Capital, CMC):
- `spread_bet_engine.evaluate_spread_bet(...)` calculates `£/point` stake
- FCA margin requirements applied (3.33%–50% depending on asset)
- Guaranteed stop recommended flag can be set

**Trade execution:**
```python
order = await paper_engine.place_order(db, {
    "exchange_name": exchange,
    "symbol": symbol,
    "side": "buy" | "sell",
    "order_type": "market",
    "quantity": quantity,   # or £/point for SB
    "strategy_name": strategy_name,
})
```

**Feedback loop** (on position close):
```python
intelligence.record_trade_outcome(strategy, symbol, net_pnl, regime, entry, exit)
losing_streak.record_outcome(won)
adaptive.exit_levels.record_exit(pnl_pct, regime, volatility, hold_hours)
adaptive.ai_accuracy.record_outcome(prediction, actual)
adaptive.time_profiler.record_outcome(hour, won)
```

---

## 8. Data Pipeline

### Signal Sources

| Source | Data Type | Asset Relevance | Endpoint |
|--------|-----------|----------------|----------|
| Fear & Greed API | Crypto market sentiment (0–100) | Crypto | `alternative.me` |
| CoinGecko | Social volume, dev activity | Crypto | `coingecko.com/api/v3` |
| RSS News Feeds | Headline news | All | Multiple RSS sources |
| Economic Calendar | Upcoming macro events | Forex, Indices | Calendar API |
| Stock Fundamentals | P/E, earnings dates, sector | Stocks | Data provider API |
| Social Sentiment | Bullish/bearish % | Crypto | Social aggregator |

### Asset-Specific Data Routing

```
Symbol classified as CRYPTO?
  → Fear & Greed, CoinGecko social, crypto news RSS
  
Symbol classified as FOREX?
  → Economic calendar (NFP, CPI, FOMC), retail positioning data
  
Symbol classified as STOCK?
  → Earnings calendar, P/E ratio, sector rotation data
  
Symbol classified as INDEX?
  → VIX level, advance/decline breadth, economic macro

Symbol classified as COMMODITY?
  → Seasonal commodity calendar, geopolitical risk feeds, EIA reports
```

### Universal Sentiment Aggregator

All data sources feed into a unified sentiment score (0–100, 50 = neutral):

```
final_sentiment = (
    fear_greed_score * 0.35 +
    social_bullish_pct * 0.25 +
    ai_sentiment_score * 0.30 +
    news_sentiment * 0.10
)
```

---

## 9. Risk Management

### RiskManager Class

Defined inline in `orchestrator.py`. Configurable per auto-trader run.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_drawdown_pct` | 10.0% | Max portfolio drawdown before halting |
| `max_position_pct` | 20.0% | Max single position as % of portfolio |
| `max_total_exposure_pct` | 60.0% | Max total invested capital |
| `max_positions` | 5 | Maximum simultaneous open positions |
| `stop_loss_pct` | 5.0% | Default stop-loss (overridden by adaptive) |
| `daily_loss_limit_pct` | 3.0% | Max daily loss before halt |

### Circuit Breaker

The orchestrator maintains a consecutive failure counter. After repeated exchange errors or trade failures, trading is paused for the current cycle and an alert is fired.

### Rate Limiter

All exchange API calls are rate-limited using CCXT's built-in `enableRateLimit=True`, with additional per-exchange delays to avoid bans.

### Per-Asset Risk Parameters

`asset_router.get_risk_params(symbol, regime)` returns asset-specific risk settings:

| Asset Class | Default Max Position | Leverage Limit | Stop Distance |
|-------------|---------------------|---------------|--------------|
| Crypto | 15% | 5× (aggressive) | Volatility-adjusted |
| Forex | 20% | 30:1 (FCA limit) | ATR-based |
| Stocks | 15% | 5:1 | Earnings-gap-aware |
| Indices | 20% | 20:1 (FCA limit) | VIX-adjusted |
| Commodities | 10% | 10:1 (FCA limit) | Seasonal-adjusted |

---

## 10. Frontend Architecture

### Technology Stack

| Package | Purpose |
|---------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool + dev server |
| Tailwind CSS | Utility-first styling |
| shadcn/ui | Component library (Radix UI primitives) |
| TanStack Query v5 | Server state, caching, background refresh |
| Wouter | Lightweight client-side routing |
| Recharts | Charts and data visualisation |
| TradingView Widget | Candlestick chart (embedded) |
| Lucide React | Icon system |

### 15 Frontend Pages

| # | Path | Label | Description |
|---|------|-------|-------------|
| 1 | `/` | Dashboard | Portfolio value, P&L, intelligence status, risk metrics, recent trades |
| 2 | `/smart-trading` | Smart Trading | Adaptive analysis page — auto-detects asset class, shows tailored intelligence |
| 3 | `/trading` | Trading | Manual order entry, TradingView chart, order book |
| 4 | `/exchanges` | Exchanges | Connect/manage all 18 exchanges, test credentials |
| 5 | `/history` | Trade History | Full trade log with filters, P&L breakdown |
| 6 | `/backtest` | Backtesting | Run strategy backtests, view equity curves |
| 7 | `/analytics` | Analytics | Performance metrics, risk stats, drawdown chart |
| 8 | `/signals` | Signals & AI | Fear & Greed, sentiment, regime, AI analysis |
| 9 | `/auto-trader` | Auto-Trader | Configure and control the orchestrator |
| 10 | `/optimizer` | Optimizer | Strategy rankings, parameter optimisation |
| 11 | `/alerts` | Alerts | Price alert management |
| 12 | `/system-alerts` | System Alerts | System-level failure monitoring with unread badge |
| 13 | `/spread-betting` | Spread Betting | SB calculator, margin monitor, funding costs |
| 14 | `/settings` | Settings | API keys, appearance, AI config, portfolio reset |
| 15 | *(404 / other)* | Not Found | Fallback route |

### Real-Time WebSocket Feed

```typescript
// useWebSocket hook connects to /ws/prices
const { prices, connected } = useWebSocket();

// Server pushes: { symbol: "BTC/USDT", price: 67540.25, change_24h: 2.3 }
```

### TanStack Query Pattern

```typescript
// All API calls go through TanStack Query for caching + background refresh
const { data: portfolio } = useQuery({
  queryKey: ["/api/portfolio"],
  queryFn: () => apiRequest("GET", "/api/portfolio").then(r => r.json()),
  refetchInterval: 5000,   // auto-refresh every 5s
});
```

---

## 11. Fee Structure

Full fee table sourced from `backend/app/services/paper_trading.py`:

| Exchange | Category | Taker Fee | Maker Fee | Min Order (USD) | Notes |
|----------|----------|-----------|-----------|----------------|-------|
| Binance | Crypto | 0.10% | 0.10% | $10 | BNB discount available |
| Bybit | Crypto | 0.10% | 0.10% | $5 | FCA-approved via Archax |
| Kraken | Crypto | 0.26% | 0.16% | $10 | FCA-registered + EMI |
| Coinbase | Crypto | 0.60% | 0.40% | $10 | Advanced Trade API |
| OKX | Crypto | 0.08% | 0.05% | $10 | — |
| Crypto.com | Crypto | 0.075% | 0.05% | $10 | — |
| Bitstamp | Crypto | 0.40% | 0.30% | $25 | Oldest FCA exchange |
| Gate.io | Crypto | 0.10% | 0.10% | $10 | — |
| Gemini | Crypto | 0.35% | 0.20% | $10 | — |
| IG Group | Spread Betting | ~0.06% (spread) | ~0.06% (spread) | £50 | FCA authorised |
| Capital.com | Spread Betting | ~0.06% (spread) | ~0.06% (spread) | £20 | FCA authorised |
| CMC Markets | Spread Betting | ~0.07% (spread) | ~0.07% (spread) | £20 | FCA authorised |
| Interactive Brokers | Multi-Asset | ~0.05% | ~0.03% | $100 | FCA authorised |
| eToro | Multi-Asset | ~1.00% (spread) | ~1.00% (spread) | $50 | FCA authorised |
| Saxo Bank | Multi-Asset | ~0.10% | ~0.08% | $100 | FCA authorised |
| OANDA | Forex | ~0.03% (spread) | ~0.02% (spread) | $1 | FCA authorised |
| Alpaca | Stocks | 0.00% | 0.00% | $1 | Commission-free |
| Trading 212 | Stocks | 0.00% | 0.00% | £1 | Commission-free, FCA authorised |

---

## 12. Testing

### Test Suites

| Suite | File | Tests | Focus |
|-------|------|-------|-------|
| Complete | `test_complete.py` | 331 | All 79 API endpoints — request/response validation |
| Integration | `test_integration.py` | 517 | Intelligence modules, strategy logic, end-to-end flows |
| Asset Trading | `test_asset_trading.py` | 389 | Per-asset full pipeline: classify → validate → execute |
| **Total** | | **1,237** | **100% pass rate** |

### test_complete.py (331 tests)

Tests every API endpoint with:
- Valid request → 200 response with expected schema
- Invalid request → 422 Unprocessable Entity
- Missing auth → 401 Unauthorized
- Portfolio state consistency after trades

### test_integration.py (517 tests)

- `StrategyScoreboard`: record outcomes, score calculation, weight adjustment
- `MultiTimeframeConsensus`: agreement logic, regime override
- `CorrelationGuard`: correlation map, block/reduce/allow thresholds
- `KellyCriterion`: formula correctness, half-Kelly, clamping
- `MarketMemory`: similarity scoring, block/boost logic
- `AdaptiveExitLevels`: optimal level calculation per volatility regime
- Full orchestrator cycle in isolation (mocked exchanges)
- Paper trading engine accuracy

### test_asset_trading.py (389 tests)

Each test runs:
```
classify(symbol) → validate_trade(symbol, direction) → get_optimal_strategies(symbol, regime) → get_risk_params(symbol)
```

For each of the 5 asset classes across multiple regimes, symbols, and edge cases.

### Running Tests

```bash
cd backend
pytest tests/test_complete.py -v
pytest tests/test_integration.py -v
pytest tests/test_asset_trading.py -v

# All tests
pytest tests/ -v --tb=short
```

---

## 13. Deployment

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend/client
npm install
npm run dev                       # Starts on http://localhost:5173
```

The Vite dev server proxies all `/api/*` requests to `http://localhost:8000`.

### Docker Deployment

```dockerfile
# Multi-stage build
FROM python:3.11-slim AS backend
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker compose up --build
```

The `docker-compose.yml` runs frontend and backend as separate services with a shared volume for the SQLite database.

### AWS Deployment

**Option 1: EC2**
```bash
# On EC2 instance (Ubuntu 22.04)
sudo apt install python3.11 nodejs npm
git clone <repo> && cd algo-trader
# Configure env vars, run with screen/systemd
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Option 2: ECS (Fargate)**
- Build Docker images, push to ECR
- Create ECS task definition with both containers
- Attach EFS for persistent SQLite volume

**Option 3: App Runner**
- Build frontend static files
- Deploy backend container to App Runner
- Serve frontend via CloudFront + S3

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Optional | Claude API key for AI decisions |
| `GOOGLE_API_KEY` | Optional | Gemini API key (fallback AI) |
| `DATABASE_URL` | Optional | SQLAlchemy URL (default: sqlite:///./data/trading.db) |
| `SECRET_KEY` | Recommended | JWT secret for session signing |
| `CORS_ORIGINS` | Optional | Comma-separated allowed origins |
| `ENVIRONMENT` | Optional | `development` or `production` |
| `LOG_LEVEL` | Optional | Python logging level (default: INFO) |
| `FRONTEND_URL` | Optional | Production frontend URL for CORS |

All exchange API keys are stored encrypted in the `exchanges` database table, not in environment variables.

---

*Architecture document generated from codebase audit — March 2026.*
