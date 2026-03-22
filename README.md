# AlgoTrader

Autonomous algorithmic trading platform built for the UK market. Supports 18 exchanges across crypto, forex, stocks, indices, and commodities — with dedicated spread betting support for tax-free trading via IG Group, Capital.com, and CMC Markets.

## What It Does

- **Trades autonomously** using a 10-step decision pipeline with 32 intelligence modules
- **Adapts per asset class** — different strategies, risk parameters, and data sources for crypto vs forex vs stocks vs indices vs commodities
- **Spread betting engine** with £/point sizing, FCA margin rates, gap protection, guaranteed stops, and tax-free routing
- **Self-improving** — learns from every trade, adjusts strategy weights, optimises parameters, tracks AI accuracy

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| Backend | FastAPI (Python 3.11+) + async throughout |
| Database | SQLite + SQLAlchemy (async) |
| Exchanges | CCXT (9 crypto) + 8 custom connectors + Alpaca |
| AI | Claude / Gemini (with rule-based fallback) |
| Real-time | WebSocket price feeds |

## Exchanges (18)

| Category | Exchanges | FCA Status |
|---|---|---|
| Crypto (9) | Binance, Bybit, Kraken, Coinbase, OKX, Crypto.com, Bitstamp, Gate.io, Gemini | Mixed (Kraken, Coinbase, Bitstamp, Gemini = FCA-registered) |
| Spread Betting (3) | IG Group, Capital.com, CMC Markets | All FCA-regulated. **Tax-free profits** |
| Multi-Asset (3) | Interactive Brokers, eToro, Saxo Bank | All FCA-regulated |
| Forex (1) | OANDA | FCA-regulated |
| Stocks (2) | Alpaca, Trading 212 | US-regulated / FCA-regulated |

## Strategies (16)

**Quantitative (11):** SMA Crossover, EMA Crossover, RSI, MACD, Bollinger Bands, Mean Reversion, Momentum, VWAP, DCA, Grid Trading, Pure AI

**Spread Betting (5):** SB Trend Rider, SB Mean Reversion, SB Momentum Scalper, SB Breakout (Guaranteed Stop), SB Index Surfer

## Intelligence (32 modules)

| Subsystem | Modules |
|---|---|
| Core Intelligence | Strategy Scoreboard, Multi-Timeframe Consensus, Correlation Guard, Kelly Criterion, Market Memory |
| Adaptive Intelligence | Adaptive Exit Levels, Symbol Discovery, AI Accuracy Tracker, Walk-Forward Validator, Adaptive Frequency, Time-of-Day Profiler |
| Instrument Intelligence | Instrument Selector, Smart Exit Decision, Trade Worthiness Filter, Liquidation Calculator |
| AI Decision Layer | News Impact Assessment, Smart Exit Reasoning, Loss Pattern Analysis, AI Strategy Selection |
| Asset Trading Rules | Crypto Rules, Forex Rules, Stock Rules, Index Rules, Commodity Rules |
| Spread Betting Engine | Position Sizer (£/pt), Margin Monitor, Overnight Funding, Spread Monitor, Market Hours, Gap Protection, Tax Router |
| Continuous Improver | Regime-Specific Optimisation, Parameter Mutation, Live+Backtest Blending |
| Self-Optimizer | Grid-Search Backtesting, Trade Journal Analysis, Strategy Ranking |

## Quick Start

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the app starts in paper trading mode with $10,000 virtual balance. No exchange connection required.

### Docker

```bash
docker build -t algotrader .
docker run -p 8000:8000 -v $(pwd)/data:/app/data algotrader
```

### Environment Variables

```bash
# AI (optional — falls back to rule-based)
ANTHROPIC_API_KEY=sk-ant-...        # Claude
GOOGLE_API_KEY=...                   # Gemini

# Email alerts (optional)
SMTP_USER=your@email.com
SMTP_PASS=app-password
ALERT_TO_EMAIL=your@email.com

# Webhook alerts (optional)
ALERT_WEBHOOK_URL=https://hooks.slack.com/...
```

Exchange API keys are configured in the UI (Settings page or Exchanges page).

## Testing

```bash
cd backend

# API endpoint tests (331 tests)
python test_complete.py

# Integration tests — intelligence, strategies, E2E (517 tests)
python test_integration.py

# Per-asset trading logic (389 tests)
python test_asset_trading.py
```

**1,237 total tests, 100% pass rate.**

## Project Structure

```
algo-trader/
├── backend/
│   ├── app/
│   │   ├── api/                  # 14 API routers (79 endpoints)
│   │   ├── core/                 # Config, database
│   │   ├── exchanges/
│   │   │   ├── connectors/       # 8 custom exchange connectors
│   │   │   └── manager.py        # Unified exchange manager
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/             # Business logic
│   │   │   ├── orchestrator.py   # Auto-trader brain (10-step pipeline)
│   │   │   ├── intelligence.py   # 5 core intelligence modules
│   │   │   ├── adaptive_intelligence.py
│   │   │   ├── instrument_intelligence.py
│   │   │   ├── ai_decision_layer.py
│   │   │   ├── spread_betting.py # 7 SB components
│   │   │   ├── asset_trading_rules.py # 5 asset-specific engines
│   │   │   ├── paper_trading.py  # Fee-aware paper trading
│   │   │   ├── live_trading.py   # Live trading bridge
│   │   │   ├── signals/          # Data feeds, AI engine, regime detector
│   │   │   └── ...
│   │   └── strategies/           # 16 trading strategies
│   ├── test_complete.py          # 331 API tests
│   ├── test_integration.py       # 517 integration tests
│   └── test_asset_trading.py     # 389 per-asset tests
├── frontend/
│   └── client/src/
│       ├── pages/                # 15 pages
│       ├── components/           # Layout, UI components
│       └── hooks/                # WebSocket, toast
├── docs/
│   ├── architecture-and-systems.md
│   ├── intelligence-and-self-improvement.md
│   └── user-guide.md
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## UI Pages (15)

| Page | Purpose |
|---|---|
| Dashboard | Portfolio overview, intelligence status, quick actions |
| Smart Trading | Adaptive analysis — changes based on instrument type |
| Trading | Manual trading with candlestick chart and order book |
| Exchanges | Connect/manage all 18 exchanges |
| Trade History | Full trade log with filters |
| Backtesting | Strategy backtester |
| Analytics | Performance, risk metrics, trade analysis |
| Signals & AI | Market sentiment, news, regime detection |
| Auto-Trader | Autonomous trading with asset-aware config |
| Optimizer | Strategy rankings, self-improvement |
| Alerts | Price and condition alerts |
| System Alerts | Failure monitoring, notification plugins |
| Spread Betting | £/point calculator, margin, funding, tax router |
| Settings | All configuration (exchanges, AI keys, notifications) |

## UK Tax Advantage

When trading through IG Group, Capital.com, or CMC Markets as spread bets:
- **Profits are tax-free** (no Capital Gains Tax, no Stamp Duty)
- The app automatically detects spread betting exchanges and routes through the SB engine
- Tax Efficiency Router recommends spread bet for profits, CFD for losses (to offset gains)

## Documentation

- [Architecture & Systems](docs/architecture-and-systems.md) — full technical architecture (1,016 lines)
- [Intelligence & Self-Improvement](docs/intelligence-and-self-improvement.md) — all 32 modules detailed (1,308 lines)
- [User Guide](docs/user-guide.md) — complete feature guide (1,402 lines)

## License

Private. All rights reserved.
