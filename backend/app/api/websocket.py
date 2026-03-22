"""
WebSocket endpoint for real-time price feeds and portfolio updates.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.exchanges.manager import exchange_manager, EXCHANGE_CONFIGS

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._running = False
        self._task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

        if not self._running and len(self.active_connections) > 0:
            self._running = True
            self._task = asyncio.create_task(self._price_feed_loop())

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

        if len(self.active_connections) == 0:
            self._running = False
            if self._task:
                self._task.cancel()

    async def broadcast(self, message: dict):
        dead = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.add(connection)
        for conn in dead:
            self.active_connections.discard(conn)

    async def _price_feed_loop(self):
        """Continuously fetch and broadcast prices."""
        while self._running:
            try:
                all_tickers = []
                # Fetch from all configured exchanges
                for name, config in EXCHANGE_CONFIGS.items():
                    pairs = exchange_manager.get_default_pairs(name)
                    if pairs:
                        tickers = await exchange_manager.get_tickers(name, pairs[:5])
                        all_tickers.extend(tickers)

                if all_tickers:
                    await self.broadcast({
                        "type": "price_update",
                        "data": all_tickers,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                await asyncio.sleep(3)  # Update every 3 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Price feed error: {e}")
                await asyncio.sleep(5)


ws_manager = ConnectionManager()


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """WebSocket endpoint for real-time price feeds."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle client messages
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg.get("type") == "subscribe":
                    # Future: handle symbol-specific subscriptions
                    await websocket.send_json({"type": "subscribed", "symbols": msg.get("symbols", [])})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
