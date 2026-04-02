"""
AlgoTrader — Autonomous Algorithmic Trading Platform
Main FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import init_db
from app.api import exchanges, portfolio, trading, websocket, backtesting, alerts, analytics, signals, auto_trader, live_trading, optimizer, system_alerts, spread_betting, asset_trading, trust_score
from app.exchanges.manager import exchange_manager
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    await exchange_manager.disconnect_all()
    logger.info("All exchanges disconnected")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(exchanges.router)
app.include_router(portfolio.router)
app.include_router(trading.router)
app.include_router(websocket.router)
app.include_router(backtesting.router)
app.include_router(alerts.router)
app.include_router(analytics.router)
app.include_router(signals.router)
app.include_router(auto_trader.router)
app.include_router(live_trading.router)
app.include_router(optimizer.router)
app.include_router(system_alerts.router)
app.include_router(spread_betting.router)
app.include_router(asset_trading.router)
app.include_router(trust_score.router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# Serve static frontend files if they exist
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
