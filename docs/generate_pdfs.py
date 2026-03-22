"""
Generate all 3 AlgoTrader documentation PDFs.
"""
import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, Flowable, ListFlowable, ListItem,
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# ─── Font Registration ──────────────────────────────────────────
FONT_DIR = Path("/tmp/fonts")
pdfmetrics.registerFont(TTFont("Inter", str(FONT_DIR / "Inter.ttf")))
pdfmetrics.registerFont(TTFont("DMSans", str(FONT_DIR / "DMSans.ttf")))
pdfmetrics.registerFont(TTFont("JetBrainsMono", str(FONT_DIR / "JetBrainsMono.ttf")))

# ─── Color Palette ──────────────────────────────────────────────
DARK_BG = HexColor("#0F1419")
DARK_SURFACE = HexColor("#1A1F2E")
ACCENT = HexColor("#1A9B8C")  # Teal
ACCENT_LIGHT = HexColor("#E8F5F3")
TEXT_PRIMARY = HexColor("#1A1F2E")
TEXT_SECONDARY = HexColor("#4A5568")
TEXT_MUTED = HexColor("#718096")
BORDER = HexColor("#E2E8F0")
TABLE_HEADER = HexColor("#1A2332")
TABLE_ALT_ROW = HexColor("#F7FAFC")
WHITE = white
PAGE_W, PAGE_H = A4

# ─── Styles ─────────────────────────────────────────────────────
def get_styles():
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        'DocTitle', fontName='DMSans', fontSize=28, leading=34,
        textColor=WHITE, alignment=TA_LEFT, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'DocSubtitle', fontName='Inter', fontSize=13, leading=18,
        textColor=HexColor("#A0AEC0"), alignment=TA_LEFT, spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        'H1', fontName='DMSans', fontSize=20, leading=26,
        textColor=ACCENT, spaceBefore=24, spaceAfter=10,
        borderPadding=(0, 0, 4, 0),
    ))
    styles.add(ParagraphStyle(
        'H2', fontName='DMSans', fontSize=15, leading=20,
        textColor=TEXT_PRIMARY, spaceBefore=18, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        'H3', fontName='DMSans', fontSize=12, leading=16,
        textColor=TEXT_SECONDARY, spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'Body', fontName='Inter', fontSize=9.5, leading=14.5,
        textColor=TEXT_PRIMARY, spaceAfter=6, alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        'BodySmall', fontName='Inter', fontSize=8.5, leading=13,
        textColor=TEXT_SECONDARY, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        'CodeBlock', fontName='JetBrainsMono', fontSize=8, leading=11,
        textColor=HexColor("#2D3748"), spaceAfter=4,
        backColor=HexColor("#F0F4F8"), borderPadding=(4, 4, 4, 4),
    ))
    styles.add(ParagraphStyle(
        'BulletItem', fontName='Inter', fontSize=9.5, leading=14,
        textColor=TEXT_PRIMARY, spaceAfter=3,
        leftIndent=18, bulletIndent=6, bulletFontSize=9,
    ))
    styles.add(ParagraphStyle(
        'BulletSub', fontName='Inter', fontSize=9, leading=13,
        textColor=TEXT_SECONDARY, spaceAfter=2,
        leftIndent=36, bulletIndent=24, bulletFontSize=8,
    ))
    styles.add(ParagraphStyle(
        'TOCEntry', fontName='Inter', fontSize=10, leading=18,
        textColor=TEXT_PRIMARY, leftIndent=12,
    ))
    styles.add(ParagraphStyle(
        'TOCSection', fontName='DMSans', fontSize=11, leading=20,
        textColor=ACCENT, spaceBefore=8,
    ))
    styles.add(ParagraphStyle(
        'Footer', fontName='Inter', fontSize=7, leading=9,
        textColor=TEXT_MUTED,
    ))
    styles.add(ParagraphStyle(
        'TableCell', fontName='Inter', fontSize=8, leading=11,
        textColor=TEXT_PRIMARY,
    ))
    styles.add(ParagraphStyle(
        'TableHeader', fontName='DMSans', fontSize=8, leading=11,
        textColor=WHITE,
    ))
    styles.add(ParagraphStyle(
        'CoverVersion', fontName='Inter', fontSize=10, leading=14,
        textColor=HexColor("#718096"), alignment=TA_LEFT,
    ))
    return styles


# ─── Custom Flowables ───────────────────────────────────────────
class HorizontalLine(Flowable):
    def __init__(self, width=None, thickness=0.5, color=BORDER):
        Flowable.__init__(self)
        self.width_val = width
        self.thickness = thickness
        self.color = color
        self.height = thickness + 4

    def wrap(self, availWidth, availHeight):
        self.width_val = self.width_val or availWidth
        return (self.width_val, self.height)

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 2, self.width_val, 2)


class AccentBar(Flowable):
    def __init__(self, width=None, thickness=3, color=ACCENT):
        Flowable.__init__(self)
        self.width_val = width
        self.thickness = thickness
        self.color = color
        self.height = thickness + 6

    def wrap(self, availWidth, availHeight):
        self.width_val = self.width_val or availWidth
        return (self.width_val, self.height)

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 3, self.width_val * 0.15, self.thickness, fill=1, stroke=0)


class CoverPage(Flowable):
    def __init__(self, title, subtitle, version="v1.0", date="March 2026"):
        Flowable.__init__(self)
        self.title = title
        self.subtitle = subtitle
        self.version = version
        self.date = date
        self.width = PAGE_W
        self.height = PAGE_H

    def wrap(self, availWidth, availHeight):
        return (availWidth, availHeight)

    def draw(self):
        c = self.canv
        w = PAGE_W
        h = PAGE_H
        margin = 60

        # Dark background
        c.setFillColor(DARK_BG)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # Accent stripe at top
        c.setFillColor(ACCENT)
        c.rect(0, h - 8, w, 8, fill=1, stroke=0)

        # Geometric decoration
        c.setFillColor(HexColor("#1E2A3A"))
        c.rect(w - 180, 0, 180, 180, fill=1, stroke=0)
        c.setFillColor(HexColor("#162030"))
        c.rect(w - 120, 0, 120, 120, fill=1, stroke=0)

        # Logo area
        c.setFillColor(ACCENT)
        c.roundRect(margin, h - 140, 48, 48, 10, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("DMSans", 22)
        c.drawString(margin + 12, h - 128, "AT")

        # App name
        c.setFont("DMSans", 14)
        c.setFillColor(HexColor("#A0AEC0"))
        c.drawString(margin + 60, h - 120, "AlgoTrader")

        # Title
        c.setFont("DMSans", 32)
        c.setFillColor(WHITE)
        # Word wrap title
        words = self.title.split()
        lines = []
        current_line = ""
        for word in words:
            test = current_line + " " + word if current_line else word
            if c.stringWidth(test, "DMSans", 32) < (w - 2 * margin):
                current_line = test
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        y_title = h - 240
        for line in lines:
            c.drawString(margin, y_title, line)
            y_title -= 42

        # Accent bar under title
        c.setFillColor(ACCENT)
        c.rect(margin, y_title + 6, 80, 3, fill=1, stroke=0)

        # Subtitle
        c.setFont("Inter", 12)
        c.setFillColor(HexColor("#A0AEC0"))
        y_sub = y_title - 20
        sub_words = self.subtitle.split()
        sub_lines = []
        current_line = ""
        for word in sub_words:
            test = current_line + " " + word if current_line else word
            if c.stringWidth(test, "Inter", 12) < (w - 2 * margin):
                current_line = test
            else:
                sub_lines.append(current_line)
                current_line = word
        if current_line:
            sub_lines.append(current_line)
        for line in sub_lines:
            c.drawString(margin, y_sub, line)
            y_sub -= 18

        # Version and date at bottom
        c.setFont("Inter", 10)
        c.setFillColor(HexColor("#4A5568"))
        c.drawString(margin, 60, f"{self.version}  |  {self.date}")
        c.drawString(margin, 44, "Autonomous Algorithmic Trading Platform")

        # Bottom accent line
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1)
        c.line(margin, 30, w - margin, 30)


# ─── Page Templates ─────────────────────────────────────────────
def header_footer(canvas, doc):
    canvas.saveState()
    w, h = PAGE_W, PAGE_H
    # Header line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(50, h - 40, w - 50, h - 40)
    # Header text
    canvas.setFont("Inter", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(50, h - 36, "AlgoTrader Documentation")
    canvas.drawRightString(w - 50, h - 36, doc.title if hasattr(doc, 'title') and doc.title else "")
    # Footer
    canvas.setStrokeColor(BORDER)
    canvas.line(50, 38, w - 50, 38)
    canvas.setFont("Inter", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(50, 26, "AlgoTrader — Autonomous Algorithmic Trading Platform")
    canvas.drawRightString(w - 50, 26, f"Page {doc.page}")
    # Accent line at top
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.5)
    canvas.line(50, h - 41, 110, h - 41)
    canvas.restoreState()


def make_doc(filename, title):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        title=title,
        author="Perplexity Computer",
        topMargin=56,
        bottomMargin=50,
        leftMargin=50,
        rightMargin=50,
    )
    return doc


def make_table(headers, rows, col_widths=None):
    """Create a styled table."""
    styles = get_styles()
    data = [[Paragraph(h, styles['TableHeader']) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), styles['TableCell']) for c in row])

    avail_w = PAGE_W - 100
    if col_widths is None:
        n = len(headers)
        col_widths = [avail_w / n] * n

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'DMSans'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
    ]
    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), TABLE_ALT_ROW))

    t.setStyle(TableStyle(style_cmds))
    return t


def toc_section(title, items, styles):
    """Create a TOC section."""
    elements = []
    elements.append(Paragraph(title, styles['TOCSection']))
    for item in items:
        elements.append(Paragraph(f"&bull; {item}", styles['TOCEntry']))
    return elements


def bullet(text, styles, level=0):
    style_name = 'BulletSub' if level > 0 else 'BulletItem'
    return Paragraph(f"&bull;&nbsp;&nbsp;{text}", styles[style_name])


# ═══════════════════════════════════════════════════════════════════
# DOCUMENT 1: Architecture & Systems
# ═══════════════════════════════════════════════════════════════════
def build_architecture_doc():
    filename = "/home/user/workspace/algo-trader/docs/architecture-and-systems.pdf"
    doc = make_doc(filename, "Architecture & Systems")
    styles = get_styles()
    story = []

    # Cover
    story.append(CoverPage(
        "Architecture & Systems",
        "Complete technical architecture documentation for the AlgoTrader autonomous trading platform. Covers backend services, exchange integrations, strategy engine, data pipeline, API layer, and deployment.",
        "v1.0", "March 2026"
    ))
    story.append(PageBreak())

    # Table of Contents
    story.append(Paragraph("Table of Contents", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 8))
    toc_items = [
        ("1. System Overview", ["Full-Stack Architecture", "Deployment Options", "High-Level Architecture Diagram"]),
        ("2. Backend Architecture", ["FastAPI Application Structure", "Database Schema", "Service Layer Design", "Async Architecture"]),
        ("3. Exchange Integration Layer", ["Unified Exchange Manager", "CCXT Crypto Exchanges (9)", "Custom Connector Exchanges (8)", "Alpaca Stock Broker", "BaseConnector Interface", "Connection Lifecycle"]),
        ("4. Trading Strategy Engine", ["11 Built-in Strategies", "Strategy Registry", "Strategy Scoreboard"]),
        ("5. Data Pipeline", ["Market Data Feeds", "OHLCV Candle Data", "Real-time Price Feeds", "Data Caching"]),
        ("6. API Layer", ["12 Router Modules", "Request/Response Formats", "Authentication Patterns"]),
        ("7. Frontend Architecture", ["React + Vite Stack", "12 Pages", "WebSocket Integration"]),
        ("8. Deployment Architecture", ["Docker Build", "Environment Variables", "Cloud Deployment"]),
    ]
    for section_title, items in toc_items:
        story.append(Paragraph(section_title, styles['TOCSection']))
        for item in items:
            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&bull;&nbsp;{item}", styles['TOCEntry']))
    story.append(PageBreak())

    # ── Section 1: System Overview ──
    story.append(Paragraph("1. System Overview", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.1 Full-Stack Architecture", styles['H2']))
    story.append(Paragraph(
        "AlgoTrader is a full-stack autonomous algorithmic trading platform built with a modern technology stack. "
        "The system comprises a React frontend for the user interface, a FastAPI backend for business logic and API services, "
        "and a SQLite database for persistent storage. The platform supports 18 exchanges across 5 categories (crypto, forex, "
        "stocks, spread betting, and multi-asset), 11 quantitative trading strategies, and a comprehensive intelligence layer "
        "with 20+ self-learning modules.", styles['Body']))

    story.append(Paragraph(
        "The architecture follows a service-oriented design where the backend is organized into discrete service modules "
        "(orchestrator, intelligence, position manager, alerting, etc.) that communicate through well-defined interfaces. "
        "The entire backend is asynchronous, using Python asyncio for non-blocking I/O across exchange connections, "
        "database operations, and AI API calls.", styles['Body']))

    story.append(Paragraph("Technology Stack", styles['H3']))
    story.append(make_table(
        ["Layer", "Technology", "Purpose"],
        [
            ["Frontend", "React 18 + TypeScript + Vite", "Single-page application with real-time updates"],
            ["UI Framework", "Tailwind CSS + shadcn/ui", "Component library with dark theme"],
            ["Data Fetching", "TanStack Query (React Query)", "Server state management with caching"],
            ["Backend", "FastAPI (Python 3.11+)", "High-performance async REST API"],
            ["Database", "SQLite + SQLAlchemy (async)", "Lightweight persistent storage"],
            ["Exchange Lib", "CCXT (async) + Custom Connectors", "Unified multi-exchange interface"],
            ["AI Integration", "Anthropic Claude / Google Gemini", "LLM-powered analysis and decisions"],
            ["Data Science", "NumPy + Pandas", "Technical analysis and signal generation"],
            ["Real-time", "WebSocket (FastAPI)", "Live price updates and notifications"],
        ],
        col_widths=[90, 160, 245]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1.2 Deployment Options", styles['H2']))
    story.append(Paragraph(
        "AlgoTrader supports three deployment modes: local development, Docker containerized, and AWS cloud deployment. "
        "All modes use the same codebase and configuration through environment variables.", styles['Body']))
    story.append(bullet("Local: Run backend with <font face='JetBrainsMono' size=8>uvicorn</font> and frontend with <font face='JetBrainsMono' size=8>npm run dev</font>", styles))
    story.append(bullet("Docker: Multi-stage build with a single Dockerfile serving both frontend and backend", styles))
    story.append(bullet("AWS: Deploy via Docker on EC2, ECS, or App Runner with environment variable configuration", styles))

    story.append(Paragraph("1.3 High-Level Architecture Diagram", styles['H2']))
    story.append(Paragraph(
        "The following textual diagram shows the system's high-level component architecture:", styles['Body']))

    arch_diagram = """<font face="JetBrainsMono" size="7.5">
+------------------------------------------------------------------+<br/>
|                        FRONTEND (React)                          |<br/>
|  Dashboard | Trading | Exchanges | Auto-Trader | Analytics | ... |<br/>
|                    TanStack Query + WebSocket                    |<br/>
+-------------------------------+----------------------------------+<br/>
                                |  HTTP/WS<br/>
+-------------------------------v----------------------------------+<br/>
|                     FASTAPI BACKEND                              |<br/>
|  +------------------+  +------------------+  +----------------+  |<br/>
|  |   API Routers    |  |  Service Layer   |  |   Data Layer   |  |<br/>
|  |  (12 modules)    |  |  Orchestrator    |  |  SQLAlchemy    |  |<br/>
|  |  exchanges       |  |  Intelligence    |  |  SQLite DB     |  |<br/>
|  |  portfolio       |  |  Position Mgr    |  |  portfolios    |  |<br/>
|  |  trading         |  |  Alerting        |  |  positions     |  |<br/>
|  |  auto_trader     |  |  Self-Optimizer  |  |  orders        |  |<br/>
|  |  signals         |  |  Cont. Improver  |  |  trades        |  |<br/>
|  |  analytics       |  |  Adaptive Intel  |  |  alerts        |  |<br/>
|  |  backtesting     |  |  AI Decision     |  |  snapshots     |  |<br/>
|  |  optimizer       |  |  Instrument Intel|  |                |  |<br/>
|  |  alerts          |  |  Paper Trading   |  |                |  |<br/>
|  |  live_trading    |  |  Live Trading    |  |                |  |<br/>
|  |  system_alerts   |  |  Backtesting     |  |                |  |<br/>
|  +------------------+  +------------------+  +----------------+  |<br/>
+----------+-------------------+-------------------+---------------+<br/>
           |                   |                   |<br/>
+----------v--------+ +-------v--------+ +--------v---------+<br/>
| Exchange Manager  | |  AI Providers  | |  Data Feeds      |<br/>
| 9x CCXT Crypto    | |  Claude API    | |  Fear &amp; Greed    |<br/>
| 8x Custom Connect | |  Gemini API    | |  CoinGecko       |<br/>
| 1x Alpaca Stocks  | |  (fallback:    | |  RSS News         |<br/>
| Simulated Data    | |   rule-based)  | |  Social Sentiment |<br/>
+-------------------+ +----------------+ +------------------+</font>"""
    story.append(Paragraph(arch_diagram, styles['Body']))
    story.append(Spacer(1, 6))

    # ── Section 2: Backend Architecture ──
    story.append(PageBreak())
    story.append(Paragraph("2. Backend Architecture", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("2.1 FastAPI Application Structure", styles['H2']))
    story.append(Paragraph(
        "The backend follows a layered architecture: main.py initializes the FastAPI app, registers 12 router modules, "
        "configures CORS middleware, and manages the application lifecycle (database initialization on startup, exchange "
        "disconnection on shutdown). Each router module maps to a specific domain (exchanges, portfolio, trading, etc.) "
        "and delegates business logic to the service layer.", styles['Body']))

    story.append(Paragraph("Application Entry Point (main.py)", styles['H3']))
    story.append(bullet("FastAPI app with CORS middleware (all origins allowed for development)", styles))
    story.append(bullet("Lifespan context manager: init_db() on startup, disconnect_all() on shutdown", styles))
    story.append(bullet("12 API router modules registered via app.include_router()", styles))
    story.append(bullet("Health check endpoint at /api/health", styles))
    story.append(bullet("Static file serving for production frontend build", styles))

    story.append(Paragraph("Project Structure", styles['H3']))
    proj_struct = """<font face="JetBrainsMono" size="7">
backend/app/<br/>
  main.py               # FastAPI entry point<br/>
  core/<br/>
    config.py            # Settings (env vars)<br/>
    database.py          # SQLAlchemy async engine<br/>
  api/<br/>
    exchanges.py         # Exchange management endpoints<br/>
    portfolio.py         # Portfolio CRUD<br/>
    trading.py           # Order placement<br/>
    auto_trader.py       # Autonomous trader control<br/>
    signals.py           # Market signals &amp; AI<br/>
    backtesting.py       # Strategy backtesting<br/>
    analytics.py         # Performance metrics<br/>
    optimizer.py         # Strategy optimization<br/>
    alerts.py            # Price alerts<br/>
    system_alerts.py     # System failure alerts<br/>
    live_trading.py      # Live mode control<br/>
    websocket.py         # Real-time updates<br/>
  services/<br/>
    orchestrator.py      # Autonomous trading brain<br/>
    intelligence.py      # 5 intelligence modules<br/>
    adaptive_intelligence.py  # 6 adaptive modules<br/>
    instrument_intelligence.py # 4 instrument modules<br/>
    ai_decision_layer.py # Claude/Gemini integration<br/>
    continuous_improver.py # Regime-specific optimization<br/>
    self_optimizer.py    # Grid-search optimization<br/>
    position_manager.py  # Stop-loss/take-profit<br/>
    alerting.py          # 4 notification plugins<br/>
    paper_trading.py     # Fee-aware paper trading<br/>
    live_trading.py      # Live bridge with safety<br/>
    backtesting.py       # Backtest engine<br/>
    signals/<br/>
      data_feeds.py      # F&amp;G, CoinGecko, RSS<br/>
      ai_engine.py       # LLM analysis<br/>
      regime_detector.py # Market regime detection<br/>
  strategies/<br/>
    base.py              # BaseStrategy interface<br/>
    builtin.py           # 10 quant strategies<br/>
    pure_ai.py           # LLM-powered strategy<br/>
  exchanges/<br/>
    manager.py           # Unified exchange manager<br/>
    connectors/<br/>
      base.py            # BaseConnector interface<br/>
      ig_connector.py    # IG Group<br/>
      ibkr_connector.py  # Interactive Brokers<br/>
      ... (8 connectors total)<br/>
  models/                # SQLAlchemy ORM models<br/>
  schemas/               # Pydantic request/response schemas</font>"""
    story.append(Paragraph(proj_struct, styles['Body']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2.2 Database Schema", styles['H2']))
    story.append(Paragraph(
        "The database uses SQLite via SQLAlchemy's async ORM. The schema tracks portfolios, positions, orders, "
        "trades, price alerts, and portfolio snapshots for historical charting.", styles['Body']))
    story.append(make_table(
        ["Table", "Key Fields", "Purpose"],
        [
            ["portfolios", "id, name, is_paper, initial_balance, cash_balance, total_value, total_pnl", "Paper/live portfolio state"],
            ["positions", "id, portfolio_id, symbol, exchange, side, quantity, avg_entry_price, unrealized_pnl", "Open and closed trading positions"],
            ["orders", "id, portfolio_id, symbol, exchange, side, order_type, quantity, price, status", "Order lifecycle tracking"],
            ["trades", "id, order_id, symbol, side, quantity, price, fee, strategy_name", "Executed trade records with fees"],
            ["alerts", "id, symbol, condition, target_price, is_active, triggered_at", "User-defined price alerts"],
            ["portfolio_snapshots", "id, portfolio_id, total_value, cash_balance, positions_value, timestamp", "Time-series snapshots for charts"],
            ["exchanges", "id, name, exchange_type, api_key, is_testnet, status, supported_pairs", "Persisted exchange connections"],
        ],
        col_widths=[100, 220, 175]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2.3 Service Layer Design Pattern", styles['H2']))
    story.append(Paragraph(
        "Each service module follows the Singleton pattern, instantiated once at module load and imported by other "
        "modules as needed. The orchestrator acts as the central coordinator, calling intelligence, position management, "
        "and alerting services in sequence during each trading cycle. Services communicate through direct function calls "
        "and shared data structures rather than message queues, keeping the architecture simple and debuggable.", styles['Body']))

    story.append(Paragraph("2.4 Async Architecture", styles['H2']))
    story.append(Paragraph(
        "The entire backend is built on Python's asyncio. All I/O-bound operations are non-blocking: exchange API calls "
        "via CCXT async, database queries via SQLAlchemy AsyncSession, HTTP requests to data feeds via httpx.AsyncClient, "
        "and AI API calls via async Anthropic/Gemini SDKs. The auto-trader runs as an asyncio.Task that executes trading "
        "cycles at configurable intervals (default 300 seconds) without blocking the API server.", styles['Body']))

    # ── Section 3: Exchange Integration Layer ──
    story.append(PageBreak())
    story.append(Paragraph("3. Exchange Integration Layer", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.1 Unified Exchange Manager", styles['H2']))
    story.append(Paragraph(
        "The ExchangeManager class provides a single interface for all 18 exchanges. Every call (get_ticker, get_ohlcv, "
        "get_order_book) is routed transparently to the correct backend: CCXT for crypto exchanges, custom connectors "
        "for traditional brokers, or the Alpaca SDK for US stocks. When an exchange is not connected or API calls fail, "
        "the manager falls back to simulated data for paper trading mode.", styles['Body']))

    story.append(Paragraph("Exchange Categories", styles['H3']))
    story.append(make_table(
        ["Category", "Exchanges", "Type", "Notes"],
        [
            ["Crypto (CCXT)", "Binance, Bybit, Kraken, Coinbase, OKX, Crypto.com, Bitstamp, Gate.io, Gemini", "ccxt", "9 exchanges via CCXT async library"],
            ["Spread Betting", "IG Group, Capital.com, CMC Markets", "connector", "Tax-free in UK, FCA-regulated"],
            ["Stock Brokers", "Alpaca, Trading 212, Interactive Brokers", "connector/alpaca", "Commission-free (Alpaca, T212)"],
            ["Forex", "OANDA", "connector", "FCA-regulated, spread-based"],
            ["Multi-Asset", "eToro, Saxo Bank", "connector", "FCA-regulated, wide asset coverage"],
        ],
        col_widths=[80, 225, 60, 130]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.2 CCXT-Based Crypto Exchanges", styles['H2']))
    story.append(Paragraph(
        "Nine cryptocurrency exchanges are integrated via the CCXT (CryptoCurrency eXchange Trading) library. "
        "Each exchange is configured in EXCHANGE_CONFIGS with its CCXT class, category, display name, FCA regulatory "
        "status, testnet URLs (where available), and default trading pairs.", styles['Body']))

    story.append(make_table(
        ["Exchange", "FCA Status", "Testnet", "Default Pairs"],
        [
            ["Binance", "Not FCA regulated", "Yes", "BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, +6 more"],
            ["Bybit", "FCA-approved (Archax)", "Yes", "BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, DOGE/USDT"],
            ["Kraken", "FCA-registered + EMI", "No", "BTC/USD, ETH/USD, SOL/USD, BTC/GBP, +6 more"],
            ["Coinbase", "FCA-registered", "No", "BTC/USD, ETH/USD, SOL/USD, BTC/GBP, ETH/GBP"],
            ["OKX", "Operating in UK", "No", "BTC/USDT, ETH/USDT, SOL/USDT, OKB/USDT"],
            ["Crypto.com", "FCA-registered", "No", "BTC/USDT, ETH/USDT, SOL/USDT, CRO/USDT"],
            ["Bitstamp", "FCA-registered", "No", "BTC/USD, ETH/USD, BTC/GBP, ETH/GBP"],
            ["Gate.io", "Operating in UK", "No", "BTC/USDT, ETH/USDT, SOL/USDT, DOGE/USDT"],
            ["Gemini", "FCA-registered", "No", "BTC/USD, ETH/USD, SOL/USD"],
        ],
        col_widths=[75, 110, 40, 270]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.3 Custom Connector-Based Exchanges", styles['H2']))
    story.append(Paragraph(
        "Eight traditional brokers use custom connector classes that implement the BaseConnector interface. "
        "These brokers have proprietary REST APIs that don't follow the CCXT standard. Each connector handles "
        "authentication, session management, and data normalization specific to its platform.", styles['Body']))

    story.append(make_table(
        ["Exchange", "Connector Class", "Category", "FCA Status", "Tax-Free"],
        [
            ["IG Group", "IGConnector", "Spread Betting", "FCA-regulated", "Yes"],
            ["Interactive Brokers", "IBKRConnector", "Multi-Asset", "FCA-regulated", "No"],
            ["OANDA", "OandaConnector", "Forex", "FCA-regulated", "No"],
            ["Trading 212", "Trading212Connector", "Stocks", "FCA-regulated", "No"],
            ["eToro", "EToroConnector", "Multi-Asset", "FCA-regulated", "No"],
            ["Saxo Bank", "SaxoConnector", "Multi-Asset", "FCA-authorized", "No"],
            ["Capital.com", "CapitalConnector", "Spread Betting", "FCA-regulated", "Yes"],
            ["CMC Markets", "CMCConnector", "Spread Betting", "FCA-regulated", "Yes"],
        ],
        col_widths=[90, 115, 85, 95, 50]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.4 BaseConnector Interface", styles['H2']))
    story.append(Paragraph(
        "All custom connectors inherit from BaseConnector, an abstract base class that defines the required interface. "
        "The interface includes 9 abstract methods that each connector must implement:", styles['Body']))
    methods = [
        ("connect(credentials)", "Authenticate and establish a session"),
        ("disconnect()", "Close the session and clean up resources"),
        ("get_account_info()", "Retrieve account balance, margin, and equity"),
        ("get_ticker(symbol)", "Get current price data for a symbol"),
        ("get_ohlcv(symbol, timeframe, limit)", "Get OHLCV candle data"),
        ("place_order(symbol, side, qty, type, price)", "Place a buy/sell order"),
        ("cancel_order(order_id)", "Cancel an open order"),
        ("get_positions()", "Return all open positions"),
        ("get_order_book(symbol, limit)", "Get order book depth"),
    ]
    for method, desc in methods:
        story.append(bullet(f"<font face='JetBrainsMono' size=8>{method}</font> — {desc}", styles))

    story.append(Paragraph(
        "BaseConnector also provides built-in rate limiting via asyncio.Semaphore, simulated data fallback methods "
        "for paper trading (ticker, OHLCV, order book, account), and a timeframe-to-seconds converter.", styles['Body']))

    story.append(Paragraph("3.5 Connection Lifecycle", styles['H2']))
    story.append(Paragraph(
        "The connection flow varies by exchange type. For CCXT exchanges, the manager creates an exchange instance with "
        "credentials, optionally enables sandbox/testnet mode, and calls load_markets(). For connectors, it instantiates "
        "the connector class, passes credentials, and calls connect(). For Alpaca, it creates a TradingClient. All connections "
        "are stored in internal dictionaries (_exchanges for CCXT/Alpaca, _connectors for custom) and tracked with metadata "
        "(connected_at, is_testnet, status).", styles['Body']))

    story.append(Paragraph("3.6 Simulated Data Fallback", styles['H2']))
    story.append(Paragraph(
        "When no exchange is connected or API calls fail, the manager generates realistic simulated data for paper trading. "
        "Base prices are maintained for 50+ instruments across crypto, forex, stocks, indices, and commodities. Simulated "
        "tickers include bid/ask spread, 24h highs/lows, and random volume. OHLCV candles use random walk from base prices "
        "with realistic volatility. This ensures the platform is fully functional for testing without any API credentials.", styles['Body']))

    # ── Section 4: Trading Strategy Engine ──
    story.append(PageBreak())
    story.append(Paragraph("4. Trading Strategy Engine", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.1 Built-in Strategies", styles['H2']))
    story.append(Paragraph(
        "AlgoTrader includes 11 pre-built trading strategies spanning trend-following, mean-reversion, momentum, "
        "passive, and AI categories. Each strategy inherits from BaseStrategy and implements generate_signals(), "
        "which takes a pandas DataFrame of OHLCV data and strategy parameters, returning the DataFrame with a "
        "'signal' column (1=buy, -1=sell, 0=hold).", styles['Body']))

    story.append(make_table(
        ["#", "Strategy", "Category", "Description", "Key Parameters"],
        [
            ["1", "SMA Crossover", "Trend", "Buy when short SMA crosses above long SMA", "short_window (20), long_window (50)"],
            ["2", "EMA Crossover", "Trend", "Exponential moving average crossover (faster)", "short_window (12), long_window (26)"],
            ["3", "RSI Reversal", "Mean Rev.", "Buy below oversold, sell above overbought", "period (14), oversold (30), overbought (70)"],
            ["4", "MACD Momentum", "Trend", "Buy on bullish MACD crossover", "fast (12), slow (26), signal (9)"],
            ["5", "Bollinger Bounce", "Mean Rev.", "Buy at lower band, sell at upper band", "period (20), std_dev (2.0)"],
            ["6", "VWAP", "Trend", "Buy above VWAP, sell below VWAP", "threshold (0.5%)"],
            ["7", "Mean Reversion", "Mean Rev.", "Buy when price deviates below MA", "period (30), threshold (2.0%)"],
            ["8", "Momentum", "Momentum", "Buy on positive rate of change", "period (14), threshold (2.0%)"],
            ["9", "DCA", "Passive", "Buy at regular intervals regardless of price", "interval (24 candles), dip_multiplier"],
            ["10", "Grid Trading", "Market Making", "Buy/sell at fixed grid price intervals", "grid_size (2.0%), num_grids (5)"],
            ["11", "Pure AI", "AI", "LLM reasons about technicals to generate signals", "aggression (conservative/moderate/aggressive)"],
        ],
        col_widths=[16, 75, 50, 180, 174]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.2 Pure AI Strategy (Strategy #11)", styles['H2']))
    story.append(Paragraph(
        "The Pure AI strategy is unique: instead of following fixed rules, it sends OHLCV data plus computed technical "
        "indicators (RSI, MACD, Bollinger Bands, volume trends, volatility) to Claude or Gemini and asks the LLM to "
        "reason from first principles about whether to buy, sell, or hold. The LLM returns a JSON response with signal, "
        "confidence score (0-1), and reasoning. A minimum confidence threshold is applied based on the aggression parameter. "
        "When no AI API key is configured, the strategy falls back to a multi-factor scoring model that combines RSI, MACD, "
        "Bollinger Band position, trend, and volume into a composite score.", styles['Body']))

    story.append(Paragraph("4.3 Strategy Registry and Selection", styles['H2']))
    story.append(Paragraph(
        "All strategies are registered in STRATEGY_REGISTRY (a dictionary mapping keys to classes). The orchestrator "
        "selects strategies based on the detected market regime via REGIME_STRATEGY_MAP, which maps each regime "
        "(trending_up, trending_down, ranging, volatile, breakout) to a weighted list of suitable strategies. "
        "Strategy weights are dynamically adjusted by the intelligence layer's live scoreboard.", styles['Body']))

    # ── Section 5: Data Pipeline ──
    story.append(PageBreak())
    story.append(Paragraph("5. Data Pipeline", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("5.1 Market Data Feeds", styles['H2']))
    story.append(Paragraph(
        "AlgoTrader aggregates data from multiple free sources to build a comprehensive market picture. "
        "All data feed functions are async and implement a 5-minute cache to avoid rate limiting on free APIs.", styles['Body']))

    story.append(make_table(
        ["Data Feed", "Source", "Data Points", "Frequency"],
        [
            ["Fear &amp; Greed Index", "alternative.me API", "Value (0-100), classification, 7-day history", "Every 5 min (cached)"],
            ["Trending Coins", "CoinGecko API", "Top trending coins, market cap rank, BTC price", "Every 5 min (cached)"],
            ["Global Market Data", "CoinGecko API", "Total market cap, BTC dominance, 24h volume", "Every 5 min (cached)"],
            ["Crypto News", "RSS (CoinDesk, CoinTelegraph, Bitcoin Magazine, Decrypt)", "Headlines, source, published date, summary", "Every 5 min (cached)"],
            ["Social Sentiment", "Simulated (seed-based)", "Bullish/bearish %, mentions, trending keywords", "Per request"],
        ],
        col_widths=[90, 135, 175, 95]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("5.2 Market Regime Detection", styles['H2']))
    story.append(Paragraph(
        "The regime detector analyzes OHLCV data using multiple technical metrics to classify market conditions into "
        "one of five regimes: trending_up, trending_down, ranging, volatile, or breakout. Metrics include linear regression "
        "slope, ADX-approximation (trend strength), ATR-based volatility, Bollinger Band width, and volume trends. "
        "Each regime classification includes a confidence score (0-0.95) and recommended strategies.", styles['Body']))

    story.append(Paragraph("5.3 AI Analysis Engine", styles['H2']))
    story.append(Paragraph(
        "The AI engine synthesizes all data feeds into a comprehensive market analysis. It builds a structured prompt "
        "with Fear &amp; Greed data, social sentiment, global market metrics, regime classification, and news headlines, "
        "then sends it to Claude or Gemini for analysis. The LLM returns a JSON response with market brief, sentiment "
        "assessment, confidence, key factors, risk level, recommended action, and warnings. AI responses are cached for "
        "15 minutes to minimize API costs. When no AI API key is available, the engine falls back to a rule-based "
        "composite scoring system.", styles['Body']))

    # ── Section 6: API Layer ──
    story.append(PageBreak())
    story.append(Paragraph("6. API Layer", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "The API layer consists of 12 FastAPI router modules, all prefixed with /api/. Each router handles a specific "
        "domain and delegates to the corresponding service layer module.", styles['Body']))

    story.append(make_table(
        ["Router Module", "Prefix", "Key Endpoints", "Description"],
        [
            ["exchanges", "/api/exchanges", "GET /supported, POST /connect/{name}, GET /ticker/{name}/{sym}", "Exchange management, market data"],
            ["portfolio", "/api/portfolio", "GET /, GET /positions, POST /reset", "Portfolio state and positions"],
            ["trading", "/api/trading", "POST /order, DELETE /order/{id}", "Order placement and cancellation"],
            ["auto_trader", "/api/auto-trader", "GET /status, POST /start, POST /stop, POST /config", "Autonomous trader control"],
            ["signals", "/api/signals", "GET /analysis, GET /fear-greed, GET /news", "Market signals and AI analysis"],
            ["backtesting", "/api/backtest", "POST /run", "Strategy backtesting"],
            ["analytics", "/api/analytics", "GET /performance, GET /risk", "Performance and risk metrics"],
            ["optimizer", "/api/optimizer", "POST /run, GET /rankings, POST /journal", "Strategy optimization"],
            ["alerts", "/api/alerts", "GET /, POST /, DELETE /{id}", "Price alert management"],
            ["system_alerts", "/api/system-alerts", "GET /, GET /unread, POST /read/{id}", "System failure alerts"],
            ["live_trading", "/api/live-trading", "GET /status, POST /mode, POST /validate", "Live trading mode control"],
            ["websocket", "/api/ws", "WS /", "Real-time price and event updates"],
        ],
        col_widths=[70, 100, 175, 150]
    ))

    # ── Section 7: Frontend Architecture ──
    story.append(PageBreak())
    story.append(Paragraph("7. Frontend Architecture", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "The frontend is a React 18 single-page application built with TypeScript, Vite, and Tailwind CSS. "
        "It uses shadcn/ui for the component library, providing a dark-themed professional trading interface. "
        "Routing is handled by Wouter with hash-based navigation. Data fetching uses TanStack Query (React Query) "
        "with automatic refetching intervals for real-time updates.", styles['Body']))

    story.append(Paragraph("7.1 Application Pages", styles['H2']))
    story.append(make_table(
        ["Page", "Route", "Description"],
        [
            ["Dashboard", "/", "Portfolio value, P&amp;L, asset allocation, risk metrics, recent trades"],
            ["Trading", "/trading", "Manual trading: order placement, candlestick chart, order book"],
            ["Exchanges", "/exchanges", "Connect/manage all 18 exchanges, view status and credentials"],
            ["Trade History", "/history", "Historical trade records with filtering and sorting"],
            ["Backtesting", "/backtest", "Run backtests, compare strategies, view equity curves"],
            ["Analytics", "/analytics", "Performance metrics, risk analysis, intelligence status"],
            ["Signals &amp; AI", "/signals", "Fear &amp; Greed, regime detection, AI analysis, news"],
            ["Auto-Trader", "/auto-trader", "Start/stop autonomous trading, decision log, configuration"],
            ["Optimizer", "/optimizer", "Strategy rankings, run optimization, trade journal"],
            ["Alerts", "/alerts", "Create and manage price alerts"],
            ["System Alerts", "/system-alerts", "System failure monitoring, unread count badge"],
            ["Settings", "/settings", "Paper trading balance, exchange keys, notification config"],
        ],
        col_widths=[90, 80, 325]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("7.2 Real-time WebSocket Integration", styles['H2']))
    story.append(Paragraph(
        "The frontend maintains a WebSocket connection to the backend for real-time updates. The connection status "
        "is displayed in the sidebar (green 'Connected' or red 'Disconnected'). Real-time events include price "
        "ticker updates, trade execution notifications, auto-trader decision events, and system alerts. The sidebar "
        "also displays a live badge with unread system alert count, polled every 10 seconds.", styles['Body']))

    # ── Section 8: Deployment ──
    story.append(PageBreak())
    story.append(Paragraph("8. Deployment Architecture", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("8.1 Docker Deployment", styles['H2']))
    story.append(Paragraph(
        "The Dockerfile uses a multi-stage build: the first stage builds the React frontend with npm, the second "
        "stage installs Python dependencies and copies the built frontend into the backend's static file directory. "
        "The final image runs uvicorn on port 5000, serving both the API and the frontend SPA.", styles['Body']))

    story.append(Paragraph("8.2 Environment Variables", styles['H2']))
    story.append(make_table(
        ["Variable", "Required", "Default", "Description"],
        [
            ["ANTHROPIC_API_KEY", "No", "None", "Claude API key for AI analysis"],
            ["GEMINI_API_KEY", "No", "None", "Google Gemini API key (fallback AI)"],
            ["DATABASE_URL", "No", "sqlite+aiosqlite:///./data/algo_trader.db", "Database connection string"],
            ["SMTP_HOST / SMTP_PORT", "No", "smtp.gmail.com / 587", "Email alert SMTP server"],
            ["SMTP_USER / SMTP_PASS", "No", "None", "Email alert credentials"],
            ["ALERT_WEBHOOK_URL", "No", "None", "Slack/Discord webhook for alerts"],
            ["ALERT_TO_EMAIL", "No", "None", "Recipient email for alerts"],
        ],
        col_widths=[110, 50, 140, 195]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("8.3 Database Persistence", styles['H2']))
    story.append(Paragraph(
        "The SQLite database file is stored at /data/algo_trader.db by default. For Docker deployments, mount "
        "a volume to /app/data to persist data across container restarts. Intelligence state (market memory, "
        "scoreboard outcomes, losing streak data) is also persisted to /data/*.json files via the "
        "IntelligencePersistence class.", styles['Body']))

    # ── Additional Section: Fee Structure ──
    story.append(PageBreak())
    story.append(Paragraph("9. Fee Structure and Order Handling", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The paper trading engine simulates realistic trading costs including exchange-specific fees, slippage, "
        "and minimum order size enforcement. This ensures backtest and paper trading results closely approximate "
        "live trading performance.", styles['Body']))

    story.append(Paragraph("9.1 Exchange Fee Rates", styles['H2']))
    story.append(make_table(
        ["Exchange", "Taker Fee", "Maker Fee", "Min Order (USD)", "Notes"],
        [
            ["Binance", "0.10%", "0.10%", "$10", "Largest crypto exchange by volume"],
            ["Bybit", "0.10%", "0.10%", "$5", "Popular derivatives exchange"],
            ["Kraken", "0.26%", "0.16%", "$10", "Higher fees, strong security"],
            ["Coinbase", "0.60%", "0.40%", "$10", "Highest crypto fees"],
            ["OKX", "0.08%", "0.05%", "$10", "Lowest crypto fees"],
            ["Crypto.com", "0.075%", "0.05%", "$10", "Competitive fee tiers"],
            ["Bitstamp", "0.40%", "0.30%", "$25", "Higher minimum order"],
            ["Gate.io", "0.10%", "0.10%", "$10", "Wide altcoin selection"],
            ["Gemini", "0.35%", "0.20%", "$10", "US-regulated"],
            ["Alpaca", "0.00%", "0.00%", "$1", "Commission-free stocks"],
            ["IG Group", "0.06%", "0.06%", "$50", "Spread-based pricing"],
            ["IBKR", "0.05%", "0.03%", "$100", "Low commissions, high min"],
            ["OANDA", "0.03%", "0.02%", "$1", "Lowest forex spreads"],
            ["Trading 212", "0.00%", "0.00%", "$1", "Commission-free"],
            ["eToro", "1.00%", "1.00%", "$50", "Highest overall costs"],
            ["Saxo Bank", "0.10%", "0.08%", "$100", "Professional platform"],
            ["Capital.com", "0.06%", "0.06%", "$20", "Spread-based"],
            ["CMC Markets", "0.07%", "0.07%", "$50", "Spread-based"],
        ],
        col_widths=[80, 60, 60, 70, 225]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("9.2 Slippage Simulation", styles['H2']))
    story.append(Paragraph(
        "Market orders include realistic slippage simulation. Base slippage is 0.05% per side, with an additional "
        "size impact component proportional to order value relative to estimated daily volume (~$50M for major pairs). "
        "This means larger orders experience slightly more slippage, mimicking real market conditions. The total "
        "slippage cost is tracked cumulatively and can be viewed via the /api/auto-trader/fees endpoint.", styles['Body']))

    story.append(Paragraph("9.3 Round-Trip Cost Estimation", styles['H2']))
    story.append(Paragraph(
        "Before executing trades, the system can estimate the total round-trip cost (buy + sell) including fees and "
        "slippage. For a $1,000 trade on Binance, the estimated round-trip cost is approximately $4.00 (0.4%). This "
        "information is used by the Trade Worthiness Filter in the instrument intelligence layer to reject trades "
        "where the expected profit margin is too thin to cover costs.", styles['Body']))

    # ── Additional Section: Live Trading Safety ──
    story.append(PageBreak())
    story.append(Paragraph("10. Live Trading Safety Architecture", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The LiveTradingBridge provides a unified interface for both paper and live execution with multiple "
        "safety layers. Switching from paper to live mode requires passing all safety checks.", styles['Body']))

    story.append(Paragraph("10.1 Safety Checks", styles['H2']))
    story.append(Paragraph(
        "Every trade execution passes through five sequential safety checks before being routed to the exchange:", styles['Body']))
    story.append(bullet("Circuit Breaker: Checks if the circuit breaker is open (too many recent failures). If open, the trade is blocked until the 5-minute cooldown expires.", styles))
    story.append(bullet("Rate Limiter: Enforces a maximum of 10 calls per 60-second window. Excess calls are blocked with a 'slow down' message.", styles))
    story.append(bullet("Exchange Allowlist: Verifies the target exchange is in the allowed list (all 18 exchanges by default).", styles))
    story.append(bullet("Daily Trade Limit: Maximum 50 trades per day. Resets at midnight UTC.", styles))
    story.append(bullet("Order Size Limit: Maximum $1,000 per order (configurable). Orders exceeding this are blocked.", styles))

    story.append(Paragraph("10.2 Live Execution Flow", styles['H2']))
    story.append(Paragraph(
        "For live trades, the bridge first checks if the exchange uses a custom connector or CCXT. For connector-based "
        "exchanges (IG, IBKR, etc.), it calls connector.place_order() directly. For CCXT exchanges, it calls the "
        "exchange's create_market_buy_order/create_market_sell_order or create_limit_buy_order/create_limit_sell_order "
        "methods. Every live trade is logged with full details (timestamp, exchange, symbol, side, quantity, price, value, "
        "status, result) for audit trail purposes.", styles['Body']))

    story.append(Paragraph("10.3 Exchange Validation", styles['H2']))
    story.append(Paragraph(
        "Before enabling live mode, the validate_exchange_connection() method checks that the exchange is properly "
        "connected by attempting to fetch account information. For CCXT exchanges, it calls fetch_balance(). For "
        "connector-based exchanges, it calls get_account_info(). This ensures API keys are valid and have the "
        "required permissions before any real money is at risk.", styles['Body']))

    story.append(Paragraph("10.4 Daily Loss Tracking", styles['H2']))
    story.append(Paragraph(
        "The bridge tracks daily P&amp;L and trade count. Both counters reset at midnight UTC. If the daily loss "
        "limit is exceeded (default $500), all further trades are blocked for the day. This provides a hard safety "
        "boundary against catastrophic daily losses.", styles['Body']))

    # ── Additional Section: Orchestrator Deep Dive ──
    story.append(PageBreak())
    story.append(Paragraph("11. Orchestrator Deep Dive", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The AI Strategy Orchestrator (orchestrator.py) is the autonomous brain of the trading system. It coordinates "
        "all components during each trading cycle.", styles['Body']))

    story.append(Paragraph("11.1 Trading Cycle Flow", styles['H2']))
    story.append(Paragraph(
        "Each autonomous trading cycle follows a deterministic sequence of 12 steps:", styles['Body']))
    story.append(bullet("1. Portfolio Risk Check: Verify drawdown, exposure, and kill switch status", styles))
    story.append(bullet("2. Losing Streak Check: Verify streak detector allows trading", styles))
    story.append(bullet("3. Time-of-Day Check: Verify current hour is historically profitable", styles))
    story.append(bullet("4. Data Collection: Fetch Fear &amp; Greed, news, social sentiment, market data", styles))
    story.append(bullet("5. Regime Detection: Analyze OHLCV data to classify market conditions", styles))
    story.append(bullet("6. AI Analysis: Get Claude/Gemini analysis of aggregated data", styles))
    story.append(bullet("7. News Impact: Assess news headlines for trading impact", styles))
    story.append(bullet("8. Strategy Selection: Choose strategies based on regime + AI + performance", styles))
    story.append(bullet("9. Signal Generation: Run selected strategies on each configured symbol", styles))
    story.append(bullet("10. Intelligence Pipeline: Multi-timeframe consensus, correlation, Kelly sizing, memory", styles))
    story.append(bullet("11. Trade Execution: Execute approved trades via paper or live engine", styles))
    story.append(bullet("12. Position Management: Check existing positions for exit signals", styles))

    story.append(Paragraph("11.2 Regime-Strategy Mapping", styles['H2']))
    story.append(Paragraph(
        "The orchestrator maintains a REGIME_STRATEGY_MAP that defines which strategies are appropriate for each "
        "market regime. Each entry includes the strategy name, parameters, and weight (allocation percentage). "
        "This map is continuously updated by the continuous improvement engine and self-optimizer based on live "
        "performance and backtest results.", styles['Body']))

    story.append(Paragraph("11.3 Decision Logging", styles['H2']))
    story.append(Paragraph(
        "Every decision is logged to an in-memory list (capped at 200 entries) with a timestamp, decision type, and "
        "relevant context. Decision types include: cycle_complete, trade_executed, no_signal, risk_block, "
        "intelligence_reject, exit_triggered, position_check, news_impact, strategy_selection, "
        "continuous_improvement, error, trade_failed, cycle_error, and more. This log is exposed via the "
        "/api/auto-trader/decisions endpoint and displayed on the Auto-Trader page.", styles['Body']))

    story.append(Paragraph("11.4 Risk Manager Configuration", styles['H2']))
    story.append(make_table(
        ["Parameter", "Default", "Description"],
        [
            ["max_drawdown_pct", "10.0%", "Halt all trading if portfolio drops this much from initial balance"],
            ["max_position_pct", "20.0%", "Maximum single position as percentage of portfolio"],
            ["max_total_exposure_pct", "60.0%", "Maximum total invested capital as percentage of portfolio"],
            ["max_positions", "5", "Maximum number of concurrent open positions"],
            ["stop_loss_pct", "5.0%", "Automatic exit threshold for losing positions"],
            ["daily_loss_limit_pct", "3.0%", "Halt trading if daily losses exceed this percentage"],
        ],
        col_widths=[125, 60, 310]
    ))

    # Build PDF
    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=header_footer)
    print(f"Built: {filename}")


# ═══════════════════════════════════════════════════════════════════
# DOCUMENT 2: Intelligence & Self-Improvement
# ═══════════════════════════════════════════════════════════════════
def build_intelligence_doc():
    filename = "/home/user/workspace/algo-trader/docs/intelligence-and-self-improvement.pdf"
    doc = make_doc(filename, "Intelligence & Self-Improvement")
    styles = get_styles()
    story = []

    # Cover
    story.append(CoverPage(
        "Intelligence & Self-Improvement",
        "Comprehensive documentation of every intelligence module, self-learning system, risk protection mechanism, and feedback loop in the AlgoTrader platform.",
        "v1.0", "March 2026"
    ))
    story.append(PageBreak())

    # Table of Contents
    story.append(Paragraph("Table of Contents", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 8))
    toc_items = [
        ("1. Intelligence Overview", ["Module Summary", "Architecture"]),
        ("2. Core Intelligence (5 Modules)", ["Strategy Scoreboard", "Multi-Timeframe Consensus", "Correlation Guard", "Kelly Criterion", "Market Memory"]),
        ("3. Adaptive Intelligence (6 Modules)", ["Adaptive Exit Levels", "Symbol Discovery", "AI Accuracy Tracker", "Walk-Forward Validator", "Adaptive Frequency", "Time-of-Day Profiler"]),
        ("4. Instrument Intelligence (4 Modules)", ["Instrument Selector", "Smart Exit Decision", "Trade Worthiness Filter", "Liquidation Calculator"]),
        ("5. AI Decision Layer (4 Use Cases)", ["News Impact Assessment", "Smart Exit Advisor", "Loss Pattern Analyzer", "AI Strategy Selection"]),
        ("6. Continuous Improvement Engine", ["Regime-Specific Optimization", "Parameter Mutation", "Live + Backtest Blending"]),
        ("7. Self-Optimizer", ["Grid-Search Backtesting", "Trade Journal Analysis", "Strategy Ranking"]),
        ("8. Risk Protection Mechanisms", ["Position Manager", "Losing Streak Detector", "Circuit Breaker", "Daily Loss Limits"]),
        ("9. Feedback Loop", ["Trade Outcome Wiring", "Score Decay", "Persistence"]),
        ("10. Alerting System", ["4 Notification Plugins", "Severity Levels", "Rate Limiting"]),
    ]
    for section_title, items in toc_items:
        story.append(Paragraph(section_title, styles['TOCSection']))
        for item in items:
            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&bull;&nbsp;{item}", styles['TOCEntry']))
    story.append(PageBreak())

    # ── Section 1: Intelligence Overview ──
    story.append(Paragraph("1. Intelligence Overview", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "AlgoTrader's intelligence layer comprises 20+ self-learning modules organized into five subsystems. "
        "Together, they form a pre-trade intelligence pipeline that evaluates every potential trade through multiple "
        "lenses before approving execution. The system continuously learns from outcomes, adapts to changing market "
        "conditions, and self-optimizes strategy parameters.", styles['Body']))

    story.append(make_table(
        ["Subsystem", "Modules", "Purpose"],
        [
            ["Core Intelligence", "5 modules", "Strategy scoring, multi-timeframe consensus, correlation guard, Kelly sizing, market memory"],
            ["Adaptive Intelligence", "6 modules", "Dynamic exits, symbol discovery, AI accuracy tracking, walk-forward validation, frequency adaptation, time profiling"],
            ["Instrument Intelligence", "4 modules", "Instrument selection (spot vs futures), smart exits, trade worthiness, liquidation calculation"],
            ["AI Decision Layer", "4 use cases", "News impact assessment, exit reasoning, loss pattern analysis, AI strategy selection"],
            ["Continuous Improver", "1 engine", "Regime-specific backtest optimization with parameter mutation and live/backtest blending"],
            ["Self-Optimizer", "1 engine", "Grid-search backtesting, trade journal analysis, strategy ranking and auto-rebalancing"],
        ],
        col_widths=[100, 60, 335]
    ))

    # ── Section 2: Core Intelligence ──
    story.append(PageBreak())
    story.append(Paragraph("2. Core Intelligence", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The IntelligencePipeline class orchestrates all 5 core modules. It runs a pre_trade_check() before every "
        "trade, returning an approval decision with position sizing and detailed reasoning.", styles['Body']))

    story.append(Paragraph("2.1 Strategy Scoreboard", styles['H2']))
    story.append(Paragraph(
        "The StrategyScoreboard tracks live P&amp;L per strategy in real-time, unlike backtesting which is backward-looking. "
        "For each strategy, it records trade outcomes (P&amp;L, symbol, regime, win/loss) and maintains a rolling window "
        "of the last 100 outcomes. Live scores are computed from the most recent 20 trades using a composite formula: "
        "50% win rate + 30% average P&amp;L percentage + 20% recent streak score. Strategy weights are dynamically "
        "adjusted by blending 60% original weight with 40% live score. Strategies with fewer than 3 live trades retain "
        "their original weights.", styles['Body']))

    story.append(Paragraph("2.2 Multi-Timeframe Consensus", styles['H2']))
    story.append(Paragraph(
        "Before approving a trade, the system runs the selected strategy across three timeframes: 15-minute, 1-hour, "
        "and 4-hour. A trade is only approved when at least 2 of 3 timeframes agree on direction. This filter "
        "eliminates 40-50% of false signals by requiring alignment across multiple time horizons. If the consensus "
        "direction conflicts with the original signal, the trade is rejected.", styles['Body']))

    story.append(Paragraph("2.3 Correlation Guard", styles['H2']))
    story.append(Paragraph(
        "The CorrelationGuard prevents overexposure to correlated assets. It maintains a correlation map for major "
        "crypto pairs (e.g., BTC/ETH = 0.85, BTC/SOL = 0.75). When a new trade is proposed, it checks correlation "
        "with all existing open positions. If correlation exceeds 0.85, the trade is blocked entirely. Between 0.70 "
        "and 0.85, position size is reduced proportionally. Below 0.70, the trade proceeds at full size.", styles['Body']))

    story.append(Paragraph("2.4 Kelly Criterion Position Sizing", styles['H2']))
    story.append(Paragraph(
        "The Kelly Criterion module calculates optimal position size based on each strategy's actual win rate and "
        "payoff ratio. The Kelly formula (f* = (bp - q) / b) determines the mathematically optimal fraction of capital "
        "to risk. AlgoTrader uses half-Kelly (f*/2) for safety, as full Kelly is too aggressive. Position sizes are "
        "clamped between 1% and 20% of portfolio value. Strategies with fewer than 5 live trades default to the "
        "minimum position size.", styles['Body']))

    story.append(Paragraph("2.5 Market Memory", styles['H2']))
    story.append(Paragraph(
        "MarketMemory stores every trading decision with its conditions (regime, Fear &amp; Greed bucket, sentiment bucket) "
        "and outcome (P&amp;L, win/loss). When making new decisions, it queries for similar past conditions using a "
        "weighted similarity score: 3 points for matching regime, 2 for matching Fear &amp; Greed bucket, 1 for matching "
        "sentiment. If similar conditions show a strategy with less than 30% win rate, the trade is blocked. If the "
        "best strategy for these conditions has over 65% win rate, the system boosts its position size by 20%. "
        "Memory capacity is 500 entries.", styles['Body']))

    # ── Section 3: Adaptive Intelligence ──
    story.append(PageBreak())
    story.append(Paragraph("3. Adaptive Intelligence", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The AdaptiveLayer coordinates six modules that close remaining gaps in the system's intelligence.", styles['Body']))

    story.append(Paragraph("3.1 Adaptive Exit Levels", styles['H2']))
    story.append(Paragraph(
        "Instead of fixed stop-loss/take-profit percentages, this module learns optimal exit levels from historical "
        "trade outcomes. Take-profit is set at 80% of the average winning trade size (capturing most of a typical gain). "
        "Stop-loss is set at 120% of the average losing trade size (giving slightly more room than typical loss). Both "
        "levels are adjusted by current volatility: wider in volatile markets (up to 1.5x), tighter in quiet markets "
        "(down to 0.7x). Trailing stop is set at 40% of take-profit. Requires at least 10 trade outcomes before "
        "switching from default values (5% SL, 10% TP, 3% trailing).", styles['Body']))

    story.append(Paragraph("3.2 Symbol Discovery", styles['H2']))
    story.append(Paragraph(
        "Scans for profitable trading opportunities beyond the default BTC/USDT and ETH/USDT. Uses CoinGecko trending "
        "data and volatility analysis to score candidate symbols (SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, MATIC). "
        "Trending coins get a bonus score of 3, and higher volatility adds up to 5 points. The top-scoring candidates "
        "are added to the active symbol list (up to 4 total).", styles['Body']))

    story.append(Paragraph("3.3 AI Accuracy Tracker", styles['H2']))
    story.append(Paragraph(
        "Tracks whether AI predictions (sentiment, action, regime) were correct by comparing predictions against actual "
        "price movements. If the AI predicted 'bullish' and the market moved up more than 0.5%, the prediction is marked "
        "correct. After 10+ evaluated predictions, the system determines a trust level: trustworthy (60%+ accuracy), "
        "mediocre (45-60%), or unreliable (below 45%). An AI weight modifier is applied: 1.3x for trustworthy, 1.0x for "
        "mediocre, 0.7x for somewhat unreliable, and 0.4x for very unreliable.", styles['Body']))

    story.append(Paragraph("3.4 Walk-Forward Validator", styles['H2']))
    story.append(Paragraph(
        "Prevents overfitting by validating backtest results on unseen data. Standard backtesting optimizes on all "
        "historical data, which risks curve-fitting. Walk-forward splits the data: optimize parameters on days 1-40, "
        "then validate on days 41-60. Parameters are only accepted if the test period Sharpe ratio is positive, "
        "degradation is less than 60% (test/train Sharpe ratio above 0.4), and test return exceeds -2%.", styles['Body']))

    story.append(Paragraph("3.5 Adaptive Trading Frequency", styles['H2']))
    story.append(Paragraph(
        "Adjusts the trading check interval based on market conditions. High volatility or breakout regime: check every "
        "2-3 minutes. Normal conditions: every 5 minutes (default). Low volatility ranging market: every 15 minutes. "
        "After executing a trade, a 10-minute cooldown is applied to prevent overtrading.", styles['Body']))

    story.append(Paragraph("3.6 Time-of-Day Profiler", styles['H2']))
    story.append(Paragraph(
        "Learns which hours of the day (UTC) are most profitable for trading. Tracks trades, wins, losses, and total "
        "P&amp;L per hour. If the current hour has a win rate below 25% over 10+ trades, trading is blocked (or reduced "
        "to 30% size if forced). Hours with below 40% win rate get reduced to 60% size. This captures patterns like "
        "the London open (08:00-12:00 UTC) typically having higher volume and the Asian session (00:00-08:00 UTC) "
        "being quieter.", styles['Body']))

    # ── Section 4: Instrument Intelligence ──
    story.append(PageBreak())
    story.append(Paragraph("4. Instrument Intelligence", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.1 Instrument Selector", styles['H2']))
    story.append(Paragraph(
        "Decides whether to use spot, perpetual futures, or margin for each trade. Decision rules: small portfolio "
        "(below $1,000) always uses spot. High volatility (over 40%) stays in spot. Strong trend with high confidence "
        "(over 65%) uses perpetual with up to 5x leverage. Bearish signals with confidence above 55% use short perpetual "
        "(only way to profit from decline). Extreme fear suggests contrarian spot buy. The selector can override the "
        "strategy's signal direction if regime + AI sentiment both contradict it.", styles['Body']))

    story.append(Paragraph("4.2 Smart Exit Decision", styles['H2']))
    story.append(Paragraph(
        "Goes beyond simple stop-loss with 8 exit rules: (1) Regime changed since entry (e.g., shifted to trending_down "
        "while holding long). (2) Leveraged position losing more than 3% requires urgent exit. (3) AI sentiment flipped "
        "against position. (4) Extreme fear while holding long is actually a hold signal (contrarian patience). (5) Extreme "
        "greed with profit above 3% triggers take-profit. (6) Perpetual funding costs exceeding 50% of unrealized P&amp;L. "
        "(7) Winning position held over 48 hours suggests partial take-profit. (8) Volatility spike with leverage.", styles['Body']))

    story.append(Paragraph("4.3 Trade Worthiness Filter", styles['H2']))
    story.append(Paragraph(
        "Answers whether a trade is profitable after costs. Calculates round-trip fees (per exchange), slippage "
        "(~0.1% per side), and funding costs for perpetuals (~0.03% per day). The expected profit must be at least "
        "2x the total cost for the trade to be considered 'worthy'. This prevents trades where the edge is so thin "
        "that fees eat all the profit.", styles['Body']))

    story.append(Paragraph("4.4 Liquidation Calculator", styles['H2']))
    story.append(Paragraph(
        "For leveraged positions, calculates the price at which liquidation occurs based on entry price, leverage, "
        "side (long/short), and maintenance margin (typically 0.5% for crypto). Monitors positions and triggers a "
        "critical exit warning when price is within 5% of the liquidation level.", styles['Body']))

    # ── Section 5: AI Decision Layer ──
    story.append(PageBreak())
    story.append(Paragraph("5. AI Decision Layer", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The AI Decision Layer integrates Claude or Gemini at four specific decision points where LLM reasoning "
        "genuinely outperforms rules. Each function falls back to rule-based logic when no API key is configured.", styles['Body']))

    story.append(Paragraph("5.1 News Impact Assessment", styles['H2']))
    story.append(Paragraph(
        "Reads up to 10 recent news headlines and assesses their impact on a specific asset. The AI determines impact "
        "(bullish/bearish/neutral), assigns a score (-1 to +1), decides whether to halt trading (major negative event) "
        "or accelerate (major positive catalyst), and identifies the key headline. This is where AI excels — understanding "
        "that 'SEC sues exchange' is bearish but 'SEC approves ETF' is bullish requires language comprehension that rules "
        "cannot match. Fallback: keyword scanning for bullish/bearish terms.", styles['Body']))

    story.append(Paragraph("5.2 Smart Exit Advisor", styles['H2']))
    story.append(Paragraph(
        "Given full context about a position (entry price, current price, P&amp;L, leverage, regime, Fear &amp; Greed, news), "
        "the AI reasons about whether to HOLD, SELL, or ADD. The AI can weigh conflicting signals: 'Position is down 3% "
        "but regime just shifted bullish and F&amp;G is at extreme fear (historically a bottom signal) — HOLD with conviction.' "
        "Returns action, confidence, reasoning, and urgency.", styles['Body']))

    story.append(Paragraph("5.3 Loss Pattern Analyzer", styles['H2']))
    story.append(Paragraph(
        "After consecutive losses, the AI analyzes the pattern to identify root causes. It examines recent losses, "
        "strategy usage, and regime history to detect patterns like: 'All losses happened during Asian session,' "
        "'Momentum strategy keeps losing in ranging market,' or 'Wins are small but losses are large.' Returns "
        "specific fixes (reduce strategy weight, increase interval, tighten stop-loss).", styles['Body']))

    story.append(Paragraph("5.4 AI Strategy Selection", styles['H2']))
    story.append(Paragraph(
        "Instead of a hardcoded regime-to-strategy map, the AI reasons about which strategies to use and why. It "
        "considers regime type and confidence, AI sentiment, recent strategy performance, Fear &amp; Greed level, and "
        "news impact. Returns a ranked list of 3-5 strategies with weights summing to 1.0 and reasoning for each pick.", styles['Body']))

    # ── Section 6: Continuous Improvement ──
    story.append(PageBreak())
    story.append(Paragraph("6. Continuous Improvement Engine", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The continuous improvement engine runs on a schedule and performs a full optimization cycle:", styles['Body']))

    story.append(Paragraph("6.1 Regime-Specific Optimization", styles['H2']))
    story.append(Paragraph(
        "Detects the current market regime, then backtests all regime-appropriate strategies using both baseline "
        "parameters and 5 mutations per strategy. Mutations nudge parameters by 1-2 steps in the search space, "
        "exploring the neighborhood of known-good configurations. Results are scored by a composite metric: "
        "40% Sharpe ratio + 30% return + 20% win rate - 10% drawdown penalty.", styles['Body']))

    story.append(Paragraph("6.2 Live + Backtest Blending", styles['H2']))
    story.append(Paragraph(
        "The key insight: backtesting alone is backward-looking, and live performance alone has small sample size. "
        "The engine blends both: 40% backtest score + 60% live scoreboard score (when available with 5+ trades). "
        "Live data is weighted more because it reflects real market conditions and execution quality.", styles['Body']))

    story.append(Paragraph("6.3 Applying Improvements", styles['H2']))
    story.append(Paragraph(
        "Blended scores are used to update the REGIME_STRATEGY_MAP: parameters are replaced with the best-found values, "
        "strategy weights are recalculated from blended scores, and strategies are sorted by weight (best first). "
        "All changes are logged for auditability.", styles['Body']))

    # ── Section 7: Self-Optimizer ──
    story.append(Paragraph("7. Self-Optimizer", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("7.1 Grid-Search Backtesting", styles['H2']))
    story.append(Paragraph(
        "The self-optimizer exhaustively tests all strategies across their parameter grids. For each strategy, it "
        "generates all parameter combinations (capped at 20 to keep it fast), runs backtests for each combination "
        "across configured symbols, and scores results. The composite score formula: Sharpe x 40 + return x 0.3 + "
        "win_rate x 20 - drawdown x 0.1. Strategies with fewer than 3 trades score -100.", styles['Body']))

    story.append(Paragraph("7.2 Trade Journal Analysis", styles['H2']))
    story.append(Paragraph(
        "The AI-powered journal reviews recent trading decisions, summarizes activity (trades executed, no-signal events, "
        "risk blocks, errors, cycles), strategy usage, and regime frequency. The AI provides a performance assessment, "
        "identifies strengths and weaknesses, and generates actionable recommendations categorized by priority (high/"
        "medium/low) and type (parameters, strategy_selection, risk_management, timing).", styles['Body']))

    story.append(Paragraph("7.3 Applying Optimization Results", styles['H2']))
    story.append(Paragraph(
        "Optimization results can be applied to the live orchestrator, updating strategy parameters and weights across "
        "all regimes in the REGIME_STRATEGY_MAP. Changes are tracked with old vs new values for transparency.", styles['Body']))

    # ── Section 8: Risk Protection ──
    story.append(PageBreak())
    story.append(Paragraph("8. Risk Protection Mechanisms", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("8.1 Position Manager", styles['H2']))
    story.append(Paragraph(
        "The PositionManager checks all open positions every auto-trader cycle against four exit rules:", styles['Body']))
    story.append(bullet("Stop-Loss: Close if position is down past threshold (default 5%)", styles))
    story.append(bullet("Take-Profit: Close if position is up past threshold (default 10%)", styles))
    story.append(bullet("Trailing Stop: After position is profitable, close if price drops 3% from peak", styles))
    story.append(bullet("Stale Exit: Close if held over 168 hours (7 days) with less than 0.5% movement", styles))

    story.append(Paragraph("8.2 Losing Streak Detector", styles['H2']))
    story.append(Paragraph(
        "Tracks win/loss outcomes and reduces exposure after consecutive losses. After 3 consecutive losses, position "
        "size is reduced by 50%. After 5 consecutive losses (severe), position size is reduced by 80% and trading "
        "is paused for 3 cycles. This prevents drawdown spirals where a bad streak compounds into catastrophic loss.", styles['Body']))

    story.append(Paragraph("8.3 Circuit Breaker", styles['H2']))
    story.append(Paragraph(
        "The CircuitBreaker stops trade execution after 5 consecutive API failures. Once open, it blocks all trades "
        "for 5 minutes (300 seconds cooldown) before auto-resetting. This prevents cascading failures when an exchange "
        "is down or experiencing issues.", styles['Body']))

    story.append(Paragraph("8.4 Portfolio-Level Risk Controls", styles['H2']))
    story.append(Paragraph(
        "The orchestrator's RiskManager enforces portfolio-level limits:", styles['Body']))
    story.append(bullet("Max Drawdown: Halt all trading if portfolio drops more than 10% from initial balance", styles))
    story.append(bullet("Max Positions: Limit to 5 concurrent open positions", styles))
    story.append(bullet("Max Position Size: No single position exceeds 20% of portfolio", styles))
    story.append(bullet("Max Total Exposure: Total invested capital capped at 60% of portfolio value", styles))
    story.append(bullet("Daily Loss Limit: Halt trading if daily losses exceed 3% of portfolio", styles))
    story.append(bullet("Kill Switch: Emergency manual halt that overrides all other controls", styles))

    story.append(Paragraph("8.5 Fee-Aware Position Sizing", styles['H2']))
    story.append(Paragraph(
        "The paper trading engine maintains realistic fee structures for all 18 exchanges. Taker fees range from "
        "0% (Alpaca, Trading 212) to 1% (eToro). The system deducts round-trip fees (buy + sell) before sizing "
        "positions. Minimum order sizes are enforced per exchange (e.g., $10 for Binance, $100 for IBKR, $50 for IG). "
        "Slippage is simulated realistically based on order size relative to volume.", styles['Body']))

    # ── Section 9: Feedback Loop ──
    story.append(PageBreak())
    story.append(Paragraph("9. Feedback Loop", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "AlgoTrader implements a closed-loop learning system where trade outcomes feed back into every intelligence module:", styles['Body']))

    story.append(bullet("When a trade closes, the P&amp;L is recorded in the Strategy Scoreboard (per strategy, per symbol, per regime)", styles))
    story.append(bullet("Market Memory updates the outcome for the matching decision entry", styles))
    story.append(bullet("Adaptive Exit Levels record the exit data (P&amp;L percentage, regime, volatility, hold time)", styles))
    story.append(bullet("AI Accuracy Tracker records whether AI predictions were correct", styles))
    story.append(bullet("Time-of-Day Profiler records the trade hour and outcome", styles))
    story.append(bullet("Losing Streak Detector records the win/loss outcome", styles))
    story.append(bullet("Intelligence state is persisted to disk (/data/ directory) so it survives restarts", styles))

    story.append(Paragraph(
        "This continuous feedback means the system gets smarter over time: strategies that perform well in specific "
        "conditions are weighted higher, poorly performing strategies are demoted, exit levels adapt to actual volatility, "
        "and the system learns to avoid trading during historically unprofitable hours.", styles['Body']))

    # ── Section 10: Alerting System ──
    story.append(Paragraph("10. Alerting System", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("10.1 Notification Plugins", styles['H2']))
    story.append(make_table(
        ["Plugin", "Always On", "Min. Severity", "Configuration"],
        [
            ["In-App", "Yes", "Low", "Stores up to 500 alerts, shown in UI with unread badges"],
            ["Console", "Yes", "Low", "Logs to server output for monitoring"],
            ["Email (SMTP)", "No", "High", "Requires SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_TO_EMAIL"],
            ["Webhook", "No", "Medium", "Requires ALERT_WEBHOOK_URL (Slack, Discord, Telegram)"],
        ],
        col_widths=[70, 55, 75, 295]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("10.2 Alert Categories and Severity", styles['H2']))
    story.append(Paragraph(
        "The system defines 25+ alert categories spanning exchange failures, AI service issues, trading failures, "
        "risk events, performance alerts, and system health. Each category has a default severity level:", styles['Body']))
    story.append(bullet("CRITICAL: System cannot trade (exchange_connection_failed, kill_switch_activated, max_drawdown_breached, liquidation_warning, database_error, circuit_breaker_triggered)", styles))
    story.append(bullet("HIGH: Major issue needing attention (trade_execution_failed, order_rejected, losing_streak_detected, daily_loss_limit_hit, cycle_error, exchange_timeout, portfolio_new_low)", styles))
    story.append(bullet("MEDIUM: Notable issue to monitor (ai_api_failed, strategy_underperforming, extreme_sentiment, memory_persistence_failed, exchange_rate_limited)", styles))
    story.append(bullet("LOW: Informational (config_changed, startup_complete, no_trades_24h, portfolio_new_high, news_feed_failed)", styles))

    story.append(Paragraph("10.3 Rate Limiting", styles['H2']))
    story.append(Paragraph(
        "The AlertRateLimiter prevents alert spam by enforcing a 300-second (5-minute) cooldown per alert category. "
        "If the same alert category fires within the cooldown period, it is suppressed. CRITICAL alerts bypass rate "
        "limiting and always fire immediately.", styles['Body']))

    # ── Additional: Intelligence Pipeline Deep Dive ──
    story.append(PageBreak())
    story.append(Paragraph("11. Intelligence Pipeline Sequence", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The intelligence pipeline runs as a sequential pre-trade check. Each module can approve, reduce, or reject "
        "a proposed trade. The pipeline short-circuits on rejection — later modules are skipped if an earlier one blocks "
        "the trade.", styles['Body']))

    story.append(Paragraph("11.1 Pipeline Execution Order", styles['H2']))
    story.append(bullet("Step 1 — Market Memory Query: Check what happened in similar past conditions. If the proposed strategy has a historically poor win rate in these conditions, BLOCK. If the best strategy matches, BOOST position by 20%.", styles))
    story.append(bullet("Step 2 — Multi-Timeframe Consensus: Run the strategy across 15m, 1h, and 4h timeframes. Require at least 2 of 3 to agree on direction. REJECT if consensus fails or conflicts with signal.", styles))
    story.append(bullet("Step 3 — Correlation Check: Verify the new position doesn't create dangerous correlation with existing holdings. BLOCK if correlation exceeds 0.85, REDUCE size if above 0.70.", styles))
    story.append(bullet("Step 4 — Kelly Criterion Sizing: Calculate mathematically optimal position size from strategy's actual win rate. Use the SMALLER of Kelly-optimal and current position percentage.", styles))
    story.append(bullet("Step 5 — Scoreboard Verification: If the strategy has 5+ live trades with below 35% win rate, BLOCK the trade regardless of other signals.", styles))
    story.append(bullet("Step 6 — Memory Storage: Record the current conditions and decision in Market Memory for future reference.", styles))
    story.append(bullet("Step 7 — Final Clamp: Position size is clamped to between 1% and max_position_pct of portfolio.", styles))

    story.append(Paragraph("11.2 Pipeline Return Value", styles['H2']))
    story.append(Paragraph(
        "The pipeline returns a structured result: approved (boolean), position_pct (final recommended size), "
        "reasons (list of human-readable explanations from each module), memory_matches (number of similar past "
        "conditions found), and intelligence_modules (detailed output from memory and scoreboard). This full "
        "context is logged in the decision log for auditability.", styles['Body']))

    # ── Additional: Parameter Ranges ──
    story.append(Paragraph("12. Parameter Optimization Ranges", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Both the continuous improver and self-optimizer search across defined parameter ranges for each strategy. "
        "The self-optimizer uses a standard grid, while the continuous improver uses extended ranges with mutation.", styles['Body']))

    story.append(make_table(
        ["Strategy", "Parameter", "Grid Values", "Extended Range"],
        [
            ["SMA Crossover", "short_window", "8, 12, 15, 20", "5 to 28 (step 2)"],
            ["SMA Crossover", "long_window", "30, 40, 50, 60", "20 to 75 (step 5)"],
            ["EMA Crossover", "short_window", "8, 10, 12, 15", "5 to 23 (step 2)"],
            ["EMA Crossover", "long_window", "21, 26, 30, 40", "15 to 47 (step 3)"],
            ["RSI", "period", "10, 14, 20", "7 to 25 (step 3)"],
            ["RSI", "oversold", "25, 30, 35", "20 to 37 (step 3)"],
            ["RSI", "overbought", "65, 70, 75", "60 to 82 (step 3)"],
            ["MACD", "fast", "8, 12, 16", "6 to 18 (step 2)"],
            ["MACD", "slow", "21, 26, 30", "18 to 33 (step 3)"],
            ["MACD", "signal", "7, 9, 11", "5 to 12 (step 2)"],
            ["Bollinger Bands", "window", "15, 20, 25", "10 to 32 (step 3)"],
            ["Bollinger Bands", "std_dev", "1.5, 2.0, 2.5", "1.0 to 3.0 (step 0.25)"],
            ["Momentum", "lookback", "10, 14, 20, 30", "7 to 32 (step 3)"],
            ["Momentum", "threshold", "0.01, 0.02, 0.03", "0.005 to 0.05 (8 values)"],
            ["Pure AI", "aggression", "conservative, moderate, aggressive", "Same 3 options"],
        ],
        col_widths=[90, 75, 145, 185]
    ))

    story.append(Paragraph("12.1 Scoring Formula", styles['H2']))
    story.append(Paragraph(
        "Backtest results are scored using a composite formula designed to balance return, risk, and statistical significance:", styles['Body']))
    story.append(Paragraph(
        "<font face='JetBrainsMono' size=8>Score = Sharpe x 40 + Return% x 0.3 + WinRate x 20 - MaxDrawdown% x 0.1</font>", styles['Body']))
    story.append(Paragraph(
        "Strategies with fewer than 3 trades score -100 (insufficient data). This formula heavily weights the Sharpe "
        "ratio (40x multiplier) because risk-adjusted returns are more reliable than raw returns. Win rate gets a 20x "
        "multiplier as a consistency measure, while raw return is weighted less (0.3x) to avoid favoring lucky outlier "
        "runs. Drawdown acts as a penalty (-0.1x) to penalize strategies that achieve returns through excessive risk.", styles['Body']))

    # Build PDF
    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=header_footer)
    print(f"Built: {filename}")


# ═══════════════════════════════════════════════════════════════════
# DOCUMENT 3: User Guide
# ═══════════════════════════════════════════════════════════════════
def build_user_guide():
    filename = "/home/user/workspace/algo-trader/docs/user-guide.pdf"
    doc = make_doc(filename, "User Guide")
    styles = get_styles()
    story = []

    # Cover
    story.append(CoverPage(
        "User Guide",
        "Complete guide to every feature of the AlgoTrader autonomous trading platform. From initial setup to advanced autonomous trading, backtesting, and optimization.",
        "v1.0", "March 2026"
    ))
    story.append(PageBreak())

    # Table of Contents
    story.append(Paragraph("Table of Contents", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 8))
    toc_items = [
        ("1. Getting Started", ["System Requirements", "Installation", "First-Time Setup"]),
        ("2. Dashboard", ["Portfolio Overview", "Risk Metrics", "Recent Activity"]),
        ("3. Trading", ["Manual Trading", "Order Types", "Charts"]),
        ("4. Exchanges", ["18 Supported Exchanges", "Connecting Exchanges", "Demo vs Live Mode"]),
        ("5. Auto-Trader", ["How It Works", "Configuration", "Decision Log"]),
        ("6. Strategies", ["11 Trading Strategies", "Strategy Selection", "Scoring"]),
        ("7. Signals & AI", ["Fear & Greed", "Regime Detection", "AI Analysis"]),
        ("8. Backtesting", ["Running Backtests", "Interpreting Results"]),
        ("9. Analytics", ["Performance Metrics", "Risk Metrics", "Intelligence Status"]),
        ("10. Optimizer", ["Strategy Rankings", "Running Optimization"]),
        ("11. Alerts & System Alerts", ["Price Alerts", "System Monitoring"]),
        ("12. Settings", ["Configuration Options"]),
        ("13. UK Tax Information", ["Spread Betting", "CFD Trading", "Crypto", "Stocks"]),
        ("14. Deployment Guide", ["Local", "Docker", "AWS", "Environment Variables"]),
    ]
    for section_title, items in toc_items:
        story.append(Paragraph(section_title, styles['TOCSection']))
        for item in items:
            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&bull;&nbsp;{item}", styles['TOCEntry']))
    story.append(PageBreak())

    # ── Section 1: Getting Started ──
    story.append(Paragraph("1. Getting Started", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.1 System Requirements", styles['H2']))
    story.append(bullet("Python 3.11 or higher", styles))
    story.append(bullet("Node.js 18+ and npm (for frontend development)", styles))
    story.append(bullet("Docker (optional, for containerized deployment)", styles))
    story.append(bullet("2GB RAM minimum, 4GB recommended", styles))
    story.append(bullet("Internet connection for exchange API access and AI features", styles))

    story.append(Paragraph("1.2 Installation", styles['H2']))
    story.append(Paragraph("Option A: Local Development", styles['H3']))
    story.append(Paragraph(
        "Clone the repository, install backend dependencies with pip, install frontend dependencies with npm, "
        "and start both servers. The backend runs on port 5000 and the frontend on port 5173 (Vite dev server).", styles['Body']))
    code_local = """<font face="JetBrainsMono" size="7.5">
# Backend<br/>
cd backend<br/>
pip install -r requirements.txt<br/>
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload<br/>
<br/>
# Frontend (separate terminal)<br/>
cd frontend/client<br/>
npm install<br/>
npm run dev</font>"""
    story.append(Paragraph(code_local, styles['Body']))

    story.append(Paragraph("Option B: Docker", styles['H3']))
    story.append(Paragraph(
        "Build and run with Docker. The container serves both backend and frontend on port 5000.", styles['Body']))
    code_docker = """<font face="JetBrainsMono" size="7.5">
docker build -t algotrader .<br/>
docker run -p 5000:5000 -v $(pwd)/data:/app/data algotrader</font>"""
    story.append(Paragraph(code_docker, styles['Body']))

    story.append(Paragraph("1.3 First-Time Setup", styles['H2']))
    story.append(Paragraph(
        "When you first open AlgoTrader, the system creates a default paper trading portfolio with $10,000 virtual "
        "balance. No exchange connection is required for paper trading — the system uses simulated market data. "
        "You can immediately explore the dashboard, run backtests, and start the auto-trader.", styles['Body']))
    story.append(bullet("Step 1: Open the application in your browser (http://localhost:5000)", styles))
    story.append(bullet("Step 2: Explore the Dashboard to see your virtual portfolio", styles))
    story.append(bullet("Step 3: Go to Exchanges to optionally connect a real exchange", styles))
    story.append(bullet("Step 4: Try the Auto-Trader page to start autonomous trading", styles))

    # ── Section 2: Dashboard ──
    story.append(PageBreak())
    story.append(Paragraph("2. Dashboard", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The Dashboard is your command center, providing a real-time overview of your portfolio's health and "
        "recent activity.", styles['Body']))

    story.append(Paragraph("2.1 Portfolio Summary", styles['H2']))
    story.append(bullet("Total Value: Current total portfolio value (cash + positions)", styles))
    story.append(bullet("Cash Balance: Available cash for new trades", styles))
    story.append(bullet("Total P&amp;L: Profit or loss since inception (dollar amount and percentage)", styles))
    story.append(bullet("Portfolio Value Chart: Historical time series of portfolio value from snapshots", styles))

    story.append(Paragraph("2.2 Asset Allocation", styles['H2']))
    story.append(Paragraph(
        "A pie chart showing how your portfolio is distributed across different assets. This helps you see "
        "at a glance whether you're over-concentrated in any single asset.", styles['Body']))

    story.append(Paragraph("2.3 Risk Metrics", styles['H2']))
    story.append(bullet("Volatility: How much your portfolio value fluctuates", styles))
    story.append(bullet("Max Drawdown: The largest peak-to-trough decline", styles))
    story.append(bullet("Value at Risk (VaR): Maximum expected loss at a given confidence level", styles))
    story.append(bullet("Diversification: How well-spread your positions are across assets", styles))

    story.append(Paragraph("2.4 Recent Activity", styles['H2']))
    story.append(Paragraph(
        "The dashboard displays your most recent trades and currently active (open) positions with real-time "
        "P&amp;L updates.", styles['Body']))

    # ── Section 3: Trading ──
    story.append(PageBreak())
    story.append(Paragraph("3. Trading", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.1 Manual Trading", styles['H2']))
    story.append(Paragraph(
        "The Trading page allows you to place buy and sell orders manually. Select an exchange and trading pair, "
        "choose your order type, enter the quantity, and submit the order.", styles['Body']))

    story.append(Paragraph("3.2 Order Types", styles['H2']))
    story.append(bullet("Market Order: Executes immediately at the current market price. Includes simulated slippage and exchange-specific fees.", styles))
    story.append(bullet("Limit Order: Sets a target price. The order executes only when the market reaches your price.", styles))

    story.append(Paragraph("3.3 Candlestick Chart", styles['H2']))
    story.append(Paragraph(
        "The Trading page displays a candlestick chart with configurable timeframes (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w). "
        "Green candles indicate price went up, red candles indicate price went down.", styles['Body']))

    story.append(Paragraph("3.4 Order Book", styles['H2']))
    story.append(Paragraph(
        "The order book shows current bid (buy) and ask (sell) prices with quantities. This helps you understand "
        "market depth and liquidity before placing an order.", styles['Body']))

    story.append(Paragraph("3.5 Paper Trading vs Live Trading", styles['H2']))
    story.append(Paragraph(
        "By default, all trading is in paper mode — using virtual money against real (or simulated) market prices. "
        "To switch to live trading, go to Settings and change the trading mode. Live trading requires a connected "
        "exchange with valid API credentials and has additional safety checks (order size limits, daily trade limits, "
        "circuit breaker).", styles['Body']))

    # ── Section 4: Exchanges ──
    story.append(PageBreak())
    story.append(Paragraph("4. Exchanges", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.1 Supported Exchanges", styles['H2']))
    story.append(Paragraph(
        "AlgoTrader supports 18 exchanges across 5 categories. Each exchange card on the Exchanges page shows "
        "the exchange name, category, FCA regulatory status, connection status, and supported trading pairs.", styles['Body']))

    story.append(make_table(
        ["Category", "Exchanges", "Asset Types"],
        [
            ["Crypto", "Binance, Bybit, Kraken, Coinbase, OKX, Crypto.com, Bitstamp, Gate.io, Gemini", "Cryptocurrencies (BTC, ETH, SOL, etc.)"],
            ["Spread Betting", "IG Group, Capital.com, CMC Markets", "Indices, forex, commodities, shares (tax-free UK)"],
            ["Stock Brokers", "Alpaca, Trading 212, Interactive Brokers", "US stocks, ETFs, some crypto"],
            ["Forex", "OANDA", "Currency pairs (EUR/USD, GBP/USD, etc.)"],
            ["Multi-Asset", "eToro, Saxo Bank", "Stocks, crypto, forex, commodities"],
        ],
        col_widths=[80, 225, 190]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.2 Connecting an Exchange", styles['H2']))
    story.append(Paragraph(
        "To connect an exchange, click its card on the Exchanges page. Each exchange requires different credentials:", styles['Body']))
    story.append(bullet("Crypto exchanges: API Key and API Secret (optionally a passphrase for Coinbase/OKX)", styles))
    story.append(bullet("Traditional brokers (IG, IBKR, etc.): Specific credentials vary — the form adapts to show the required fields", styles))
    story.append(bullet("Alpaca: API Key and API Secret from your Alpaca account", styles))
    story.append(Paragraph(
        "You can also connect without any credentials for paper trading — the system will use simulated data.", styles['Body']))

    story.append(Paragraph("4.3 Demo/Paper Mode vs Live Mode", styles['H2']))
    story.append(Paragraph(
        "Each exchange connection has a 'Testnet/Paper' toggle. When enabled, the system uses the exchange's sandbox "
        "environment (where available) or simulated data. This is the recommended starting point. Switch to live mode "
        "only after thorough testing with paper trading.", styles['Body']))

    # ── Section 5: Auto-Trader ──
    story.append(PageBreak())
    story.append(Paragraph("5. Auto-Trader", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("5.1 How the Autonomous Trading System Works", styles['H2']))
    story.append(Paragraph(
        "The Auto-Trader is the autonomous brain of AlgoTrader. When started, it runs continuous trading cycles "
        "(every 5 minutes by default). Each cycle:", styles['Body']))
    story.append(bullet("1. Fetches market data (Fear &amp; Greed, news, social sentiment)", styles))
    story.append(bullet("2. Detects the current market regime (trending, ranging, volatile, breakout)", styles))
    story.append(bullet("3. Gets AI analysis of market conditions (if API key configured)", styles))
    story.append(bullet("4. Selects optimal strategies for the current regime", styles))
    story.append(bullet("5. Runs selected strategies on each configured symbol", styles))
    story.append(bullet("6. Passes signals through the intelligence pipeline (consensus, correlation, Kelly sizing, memory)", styles))
    story.append(bullet("7. Checks instrument intelligence (spot vs futures, trade worthiness)", styles))
    story.append(bullet("8. Executes approved trades via paper or live trading engine", styles))
    story.append(bullet("9. Manages existing positions (stop-loss, take-profit, trailing stops, smart exits)", styles))
    story.append(bullet("10. Logs every decision for transparency", styles))

    story.append(Paragraph("5.2 Configuration", styles['H2']))
    story.append(make_table(
        ["Setting", "Default", "Description"],
        [
            ["Symbols", "BTC/USDT, ETH/USDT", "Trading pairs to monitor"],
            ["Exchange", "binance", "Which exchange to trade on"],
            ["Interval", "300 seconds", "Time between trading cycles"],
            ["Max Drawdown %", "10%", "Halt trading if portfolio drops this much"],
            ["Max Position %", "20%", "Maximum size of any single position"],
            ["Max Total Exposure %", "60%", "Maximum total invested as % of portfolio"],
            ["Max Positions", "5", "Maximum concurrent open positions"],
            ["Stop Loss %", "5%", "Automatic position exit on this much loss"],
            ["Daily Loss Limit %", "3%", "Halt trading if daily losses exceed this"],
        ],
        col_widths=[120, 80, 295]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("5.3 Starting and Stopping", styles['H2']))
    story.append(Paragraph(
        "Click the Start button on the Auto-Trader page to begin autonomous trading. The system displays its status "
        "(running/stopped), cycle count, active strategies, and last analysis results. Click Stop to halt trading. "
        "The Kill Switch button immediately halts all trading and blocks new trades until manually deactivated.", styles['Body']))

    story.append(Paragraph("5.4 Decision Log", styles['H2']))
    story.append(Paragraph(
        "Every decision is logged with full details: timestamp, decision type, strategy, symbol, regime, signal "
        "direction, confidence, risk level, and reasoning. Decision types include: cycle_complete, trade_executed, "
        "no_signal, risk_block, intelligence_reject, exit_triggered, position_check, and more. This provides "
        "complete auditability of all autonomous actions.", styles['Body']))

    # ── Section 6: Strategies ──
    story.append(PageBreak())
    story.append(Paragraph("6. Strategies", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("6.1 All 11 Trading Strategies Explained", styles['H2']))

    strategy_explanations = [
        ("SMA Crossover", "Uses two Simple Moving Averages (one short, one long). When the short-term average crosses above the long-term average, it signals a buy. When it crosses below, it signals a sell. Best for trending markets."),
        ("EMA Crossover", "Similar to SMA Crossover but uses Exponential Moving Averages, which react faster to recent price changes. Better for catching trends early."),
        ("RSI Reversal", "The Relative Strength Index measures if an asset is 'oversold' (too cheap) or 'overbought' (too expensive). Buys when RSI drops below 30, sells when it rises above 70."),
        ("MACD Momentum", "Moving Average Convergence Divergence tracks the relationship between two moving averages. Buys on bullish crossovers (MACD rises above signal line), sells on bearish crossovers."),
        ("Bollinger Bounce", "Uses bands around a moving average based on volatility. Buys when price touches the lower band (oversold), sells when it touches the upper band (overbought)."),
        ("VWAP", "Volume-Weighted Average Price — buys when price crosses above the average weighted by volume, sells when it crosses below. Best for intraday trading."),
        ("Mean Reversion", "Assumes prices tend to return to their average. Buys when price drops far below the moving average, sells when it rises far above."),
        ("Momentum", "Measures the rate of price change. Buys when upward momentum exceeds a threshold, sells when downward momentum exceeds it."),
        ("DCA (Dollar Cost Averaging)", "Buys at regular intervals regardless of price, reducing the impact of volatility. The simplest and most passive strategy."),
        ("Grid Trading", "Places buy and sell orders at fixed price intervals. Profits from price oscillations in sideways markets."),
        ("Pure AI", "Sends market data to Claude or Gemini AI, which reasons about whether to buy, sell, or hold. The only strategy that uses no fixed rules — the AI decides everything from first principles."),
    ]
    for name, explanation in strategy_explanations:
        story.append(Paragraph(f"<b>{name}</b>", styles['H3']))
        story.append(Paragraph(explanation, styles['Body']))

    story.append(Paragraph("6.2 How Strategy Selection Works", styles['H2']))
    story.append(Paragraph(
        "The system does not use a single strategy — it selects the best strategies for current market conditions. "
        "A market regime is detected (trending up, trending down, ranging, volatile, breakout), and each regime has "
        "a preset map of suitable strategies with weights. For example, a trending-up market might favor Momentum (30%), "
        "SMA Crossover (25%), and EMA Crossover (25%). These weights are continuously adjusted by the live scoreboard "
        "based on actual trading performance.", styles['Body']))

    # ── Section 7: Signals & AI ──
    story.append(PageBreak())
    story.append(Paragraph("7. Signals &amp; AI", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("7.1 Fear &amp; Greed Index", styles['H2']))
    story.append(Paragraph(
        "A score from 0 (Extreme Fear) to 100 (Extreme Greed) that measures overall crypto market sentiment. "
        "Extreme fear (below 20) often signals buying opportunities, while extreme greed (above 80) may signal "
        "overextension risk. The index updates daily and includes a 7-day history chart.", styles['Body']))

    story.append(Paragraph("7.2 Market Regime Detection", styles['H2']))
    story.append(Paragraph(
        "The system automatically classifies the market into one of five regimes: Trending Up (strong uptrend), "
        "Trending Down (strong downtrend), Ranging (sideways), Volatile (high volatility, no direction), or "
        "Breakout (potential regime change). Each regime comes with a confidence score and recommended strategies.", styles['Body']))

    story.append(Paragraph("7.3 AI Analysis", styles['H2']))
    story.append(Paragraph(
        "When a Claude or Gemini API key is configured, the Signals page shows AI-generated market analysis including "
        "a market brief, sentiment assessment (bullish/bearish/neutral), confidence score, key factors, risk level, "
        "recommended action (accumulate/hold/reduce/wait), and warnings. Without an API key, the system uses a "
        "rule-based analysis based on Fear &amp; Greed, social sentiment, and regime data.", styles['Body']))

    story.append(Paragraph("7.4 Social Sentiment", styles['H2']))
    story.append(Paragraph(
        "Displays bullish vs bearish sentiment percentages, trending keywords, and mention counts for each symbol. "
        "Social sentiment is one input to the overall trading decision, alongside technicals and AI analysis.", styles['Body']))

    # ── Section 8: Backtesting ──
    story.append(PageBreak())
    story.append(Paragraph("8. Backtesting", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("8.1 How to Run a Backtest", styles['H2']))
    story.append(bullet("Select a strategy from the dropdown (e.g., RSI Reversal)", styles))
    story.append(bullet("Choose a trading pair (e.g., BTC/USDT) and exchange", styles))
    story.append(bullet("Set the timeframe (e.g., 1h) and number of days to test (e.g., 60)", styles))
    story.append(bullet("Configure strategy parameters or use defaults", styles))
    story.append(bullet("Set initial balance and position size percentage", styles))
    story.append(bullet("Click Run Backtest", styles))

    story.append(Paragraph("8.2 Interpreting Results", styles['H2']))
    story.append(Paragraph(
        "The backtest results show: total return percentage, Sharpe ratio (risk-adjusted return), maximum drawdown, "
        "total trades, win rate, average profit per trade, and an equity curve chart. A Sharpe ratio above 1.0 is "
        "good, above 2.0 is excellent. Win rate above 50% combined with positive average P&amp;L indicates a viable strategy.", styles['Body']))

    # ── Section 9: Analytics ──
    story.append(Paragraph("9. Analytics", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The Analytics page provides deep insights into your trading performance:", styles['Body']))

    story.append(bullet("Performance Metrics: Total return, Sharpe ratio, Sortino ratio, win/loss ratio", styles))
    story.append(bullet("Risk Metrics: Maximum drawdown, Value at Risk, volatility, beta", styles))
    story.append(bullet("Trade Analysis: Average hold time, best/worst trades, profit factor", styles))
    story.append(bullet("Intelligence Status: Scoreboard stats, market memory size, correlation threshold", styles))
    story.append(bullet("Adaptive Intelligence Status: AI accuracy, time-of-day profile, active symbols, exit levels", styles))

    # ── Section 10: Optimizer ──
    story.append(Paragraph("10. Optimizer", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("10.1 Strategy Rankings", styles['H2']))
    story.append(Paragraph(
        "The Optimizer page shows all strategies ranked by their composite score (Sharpe, return, win rate, drawdown). "
        "Each strategy displays its best parameters, score, and performance metrics.", styles['Body']))

    story.append(Paragraph("10.2 Running Optimization", styles['H2']))
    story.append(Paragraph(
        "Click 'Run Optimization' to start a grid-search across all strategy parameter combinations. The optimizer "
        "tests each combination via backtesting and ranks results. This typically runs dozens of backtests and may "
        "take a few minutes.", styles['Body']))

    story.append(Paragraph("10.3 Trade Journal", styles['H2']))
    story.append(Paragraph(
        "The trade journal uses AI to analyze recent trading decisions and generate actionable improvement recommendations. "
        "It summarizes activity, identifies strengths/weaknesses, and suggests parameter tweaks or strategy adjustments.", styles['Body']))

    # ── Section 11: Alerts ──
    story.append(PageBreak())
    story.append(Paragraph("11. Alerts &amp; System Alerts", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("11.1 Price Alerts", styles['H2']))
    story.append(Paragraph(
        "Create custom price alerts for any symbol. Set a target price and condition (above or below), and the system "
        "will notify you when the condition is met. Alerts are displayed on the Alerts page and can be configured to "
        "send email or webhook notifications.", styles['Body']))

    story.append(Paragraph("11.2 System Alerts", styles['H2']))
    story.append(Paragraph(
        "The System Alerts page shows all system-generated alerts: exchange connection failures, trade execution errors, "
        "risk limit breaches, AI service issues, and more. Alerts are color-coded by severity (Critical = red, "
        "High = orange, Medium = yellow, Low = blue). Unread alerts are counted and shown as a badge on the sidebar.", styles['Body']))

    story.append(Paragraph("11.3 Notification Plugins", styles['H2']))
    story.append(bullet("Email: Configure SMTP settings in environment variables to receive email alerts for HIGH and CRITICAL events", styles))
    story.append(bullet("Webhook: Set ALERT_WEBHOOK_URL to send alerts to Slack, Discord, or Telegram channels", styles))
    story.append(bullet("In-App: Always active, shown in the System Alerts page with filtering by severity", styles))

    # ── Section 12: Settings ──
    story.append(Paragraph("12. Settings", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The Settings page provides configuration options for:", styles['Body']))
    story.append(bullet("Paper Trading Balance: Reset your virtual portfolio with a custom starting balance", styles))
    story.append(bullet("Exchange API Keys: Manage credentials for connected exchanges", styles))
    story.append(bullet("Auto-Trader Configuration: Symbols, interval, risk limits", styles))
    story.append(bullet("Notification Settings: Email and webhook configuration", styles))
    story.append(bullet("Trading Mode: Switch between paper and live trading", styles))

    # ── Section 13: UK Tax Information ──
    story.append(PageBreak())
    story.append(Paragraph("13. UK-Specific Tax Information", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Important: This information is provided for general guidance only and does not constitute tax advice. "
        "Consult a qualified tax professional for your specific situation.", styles['BodySmall']))
    story.append(Spacer(1, 4))

    story.append(make_table(
        ["Trading Type", "Exchanges", "Tax Treatment", "Details"],
        [
            ["Spread Betting", "IG Group, Capital.com, CMC Markets", "TAX-FREE", "Profits from spread betting are exempt from Capital Gains Tax and Stamp Duty in the UK. This is why spread betting platforms are popular among UK traders."],
            ["CFD Trading", "IG Group, eToro, Capital.com, CMC, IBKR", "Capital Gains Tax", "Profits from Contracts for Difference (CFDs) are subject to Capital Gains Tax. Annual allowance applies (currently \u00a33,000)."],
            ["Crypto Trading", "Binance, Bybit, Kraken, Coinbase, etc.", "Capital Gains Tax", "Cryptocurrency disposals (selling, exchanging, spending) are subject to Capital Gains Tax. Each disposal is a taxable event."],
            ["Stock Trading", "Alpaca, Trading 212, IBKR, Saxo", "CGT + Stamp Duty", "Stock purchases may incur 0.5% Stamp Duty (UK shares). Profits are subject to Capital Gains Tax."],
            ["Forex Trading", "OANDA, Saxo, IG (if not spread bet)", "Capital Gains Tax", "Forex profits are subject to CGT unless structured as spread bets."],
        ],
        col_widths=[80, 120, 85, 210]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "Key point: If you are a UK-based trader looking to minimize tax, consider using IG Group, Capital.com, or "
        "CMC Markets for spread betting, where profits are completely tax-free. AlgoTrader supports all three platforms.", styles['Body']))

    # ── Section 14: Deployment Guide ──
    story.append(PageBreak())
    story.append(Paragraph("14. Deployment Guide", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    story.append(Paragraph("14.1 Local Deployment", styles['H2']))
    story.append(Paragraph(
        "For development and testing, run the backend and frontend separately. The backend serves the API on port 5000, "
        "and the Vite dev server runs the frontend on port 5173 with hot module replacement for fast development.", styles['Body']))

    story.append(Paragraph("14.2 Docker Deployment", styles['H2']))
    story.append(Paragraph(
        "The included Dockerfile builds a production-ready container. The multi-stage build first compiles the React "
        "frontend, then packages it with the Python backend. Mount a volume to /app/data for database and intelligence "
        "state persistence across container restarts.", styles['Body']))

    story.append(Paragraph("14.3 AWS Cloud Deployment", styles['H2']))
    story.append(Paragraph(
        "Deploy the Docker container to AWS using EC2, ECS (Elastic Container Service), or App Runner. Set environment "
        "variables (ANTHROPIC_API_KEY, SMTP settings, etc.) through your deployment service's configuration. For "
        "persistent storage, mount an EBS volume or use an external database.", styles['Body']))

    story.append(Paragraph("14.4 Environment Variables Reference", styles['H2']))
    story.append(make_table(
        ["Variable", "Required", "Description"],
        [
            ["ANTHROPIC_API_KEY", "No", "Enables Claude AI for market analysis and strategy selection"],
            ["GEMINI_API_KEY", "No", "Alternative AI provider (Google Gemini)"],
            ["DATABASE_URL", "No", "SQLite connection string (default: sqlite+aiosqlite:///./data/algo_trader.db)"],
            ["SMTP_HOST", "No", "SMTP server for email alerts (default: smtp.gmail.com)"],
            ["SMTP_PORT", "No", "SMTP port (default: 587)"],
            ["SMTP_USER", "No", "SMTP authentication username"],
            ["SMTP_PASS", "No", "SMTP authentication password"],
            ["ALERT_FROM_EMAIL", "No", "Sender email for alerts"],
            ["ALERT_TO_EMAIL", "No", "Recipient email for alerts"],
            ["ALERT_WEBHOOK_URL", "No", "Webhook URL for Slack/Discord/Telegram alerts"],
        ],
        col_widths=[110, 50, 335]
    ))

    # ── Additional: FAQ ──
    story.append(PageBreak())
    story.append(Paragraph("15. Frequently Asked Questions", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    faqs = [
        ("Do I need API keys to use AlgoTrader?",
         "No. AlgoTrader works fully in paper trading mode without any API keys. It uses simulated market data that "
         "closely mirrors real prices. You only need exchange API keys if you want to connect to a real exchange for "
         "live data or live trading. AI features (Claude/Gemini analysis) require an API key but the system falls back "
         "to rule-based analysis without one."),
        ("Is my money at risk?",
         "By default, AlgoTrader operates in paper trading mode with virtual money. No real money is ever at risk unless "
         "you explicitly switch to live trading mode, connect a real exchange with funded API keys, and confirm the switch. "
         "Multiple safety layers (circuit breaker, order limits, daily loss limits, kill switch) protect against excessive losses."),
        ("Which exchange should I start with?",
         "For crypto: Binance (lowest fees, most pairs) or Kraken (FCA-registered, good security). For UK spread betting "
         "(tax-free): IG Group is the most established. For US stocks: Alpaca is commission-free. Start with paper/demo "
         "mode regardless of which exchange you choose."),
        ("How does the auto-trader make decisions?",
         "The auto-trader follows a systematic process: detect market regime, get AI analysis, select appropriate strategies, "
         "generate signals, validate through the intelligence pipeline (multi-timeframe consensus, correlation check, Kelly "
         "sizing, market memory), check trade worthiness, and execute if all checks pass. Every decision is logged with "
         "full reasoning."),
        ("Can I run AlgoTrader 24/7?",
         "Yes. The auto-trader is designed for continuous operation. Deploy via Docker on a cloud server (AWS, DigitalOcean, etc.) "
         "for uninterrupted trading. The system automatically adapts its trading frequency based on market volatility and "
         "takes cooldown breaks after trades and losing streaks."),
        ("What happens if the internet connection drops?",
         "The circuit breaker detects consecutive failures and pauses trading. When connection is restored, the system "
         "automatically resumes. Intelligence state is persisted to disk, so no learning data is lost during outages. "
         "Open positions remain managed by the exchange\'s own stop-loss orders."),
        ("How do I get AI analysis working?",
         "Set either ANTHROPIC_API_KEY (for Claude) or GEMINI_API_KEY (for Gemini) as an environment variable. Claude "
         "is preferred for more nuanced analysis. The AI is used for market analysis, news impact assessment, exit reasoning, "
         "loss pattern analysis, and strategy selection. Without an API key, all features fall back to rule-based logic."),
        ("Can I create my own trading strategy?",
         "Yes. Create a new class that inherits from BaseStrategy in the strategies/ directory. Implement the get_params() "
         "class method and the generate_signals() method. Register your strategy in the STRATEGY_REGISTRY dictionary in "
         "builtin.py. Your strategy will automatically appear in the backtesting, optimization, and auto-trader interfaces."),
        ("How does the system learn and improve over time?",
         "AlgoTrader uses multiple feedback loops: the Strategy Scoreboard tracks real P&amp;L per strategy, Market Memory "
         "remembers what worked in similar conditions, the AI Accuracy Tracker evaluates AI prediction quality, and the "
         "Time-of-Day Profiler learns profitable trading hours. The continuous improver periodically backtests and updates "
         "strategy parameters. All learning data persists across restarts."),
        ("What is spread betting and why is it tax-free?",
         "Spread betting is a derivative product offered by UK-regulated brokers (IG, Capital.com, CMC Markets) where you "
         "bet on the direction of an asset\'s price without owning it. In the UK, spread betting profits are exempt from "
         "Capital Gains Tax and Stamp Duty. This makes it highly advantageous for UK-based traders. AlgoTrader fully "
         "supports automated spread betting through its connector framework."),
    ]

    for question, answer in faqs:
        story.append(Paragraph(f"<b>Q: {question}</b>", styles['H3']))
        story.append(Paragraph(answer, styles['Body']))
        story.append(Spacer(1, 4))

    # ── Additional: Glossary ──
    story.append(PageBreak())
    story.append(Paragraph("16. Glossary", styles['H1']))
    story.append(AccentBar())
    story.append(Spacer(1, 6))

    glossary = [
        ("ATR", "Average True Range — a volatility indicator measuring the average range of price bars"),
        ("Bollinger Bands", "A volatility indicator with an upper and lower band plotted 2 standard deviations from a moving average"),
        ("CCXT", "CryptoCurrency eXchange Trading — open-source library for connecting to crypto exchanges"),
        ("CGT", "Capital Gains Tax — UK tax on profits from disposing of assets"),
        ("Circuit Breaker", "Safety mechanism that halts trading after consecutive failures"),
        ("DCA", "Dollar Cost Averaging — investing fixed amounts at regular intervals"),
        ("Drawdown", "Peak-to-trough decline in portfolio value, measuring downside risk"),
        ("EMA", "Exponential Moving Average — a moving average giving more weight to recent prices"),
        ("Fear &amp; Greed Index", "Sentiment indicator from 0 (extreme fear) to 100 (extreme greed)"),
        ("FCA", "Financial Conduct Authority — UK financial services regulator"),
        ("Kelly Criterion", "Formula for optimal bet sizing based on edge and payoff ratio"),
        ("MACD", "Moving Average Convergence Divergence — trend-following momentum indicator"),
        ("OHLCV", "Open, High, Low, Close, Volume — standard candle data format"),
        ("Paper Trading", "Simulated trading with virtual money against real market prices"),
        ("Regime", "Classification of market conditions (trending, ranging, volatile, breakout)"),
        ("RSI", "Relative Strength Index — momentum oscillator measuring overbought/oversold conditions"),
        ("Sharpe Ratio", "Risk-adjusted return metric; above 1.0 is good, above 2.0 is excellent"),
        ("SMA", "Simple Moving Average — arithmetic mean of prices over a specified period"),
        ("Spread Betting", "UK derivative product where profits are tax-free"),
        ("VWAP", "Volume-Weighted Average Price — average price weighted by trading volume"),
        ("Walk-Forward", "Optimization technique that validates parameters on unseen data to prevent overfitting"),
    ]

    story.append(make_table(
        ["Term", "Definition"],
        [[term, defn] for term, defn in glossary],
        col_widths=[100, 395]
    ))

    # Build PDF
    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=header_footer)
    print(f"Built: {filename}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating AlgoTrader documentation PDFs...")
    build_architecture_doc()
    build_intelligence_doc()
    build_user_guide()
    print("All 3 PDFs generated successfully!")
