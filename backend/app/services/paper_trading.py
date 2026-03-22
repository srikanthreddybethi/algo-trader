"""
Paper Trading Engine — simulates order execution against real-time prices.
Supports market orders, limit orders, stop-loss, and take-profit.
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.portfolio import Portfolio, Position, PortfolioSnapshot
from app.models.order import Order
from app.models.trade import Trade
from app.exchanges.manager import exchange_manager

logger = logging.getLogger(__name__)


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol format to CCXT standard (BASE/QUOTE)."""
    # Replace common separators with /
    for sep in ["-", "_"]:
        if sep in symbol and "/" not in symbol:
            symbol = symbol.replace(sep, "/")
    return symbol.upper()


# Realistic fee structure per exchange (taker fees — market orders)
FEE_RATES = {
    "binance": 0.001,       # 0.10% taker
    "bybit": 0.001,         # 0.10% taker
    "kraken": 0.0026,       # 0.26% taker
    "coinbase": 0.006,      # 0.60% taker (Advanced Trade)
    "okx": 0.0008,          # 0.08% taker
    "cryptocom": 0.00075,   # 0.075% taker
    "bitstamp": 0.004,      # 0.40% taker
    "gate": 0.001,          # 0.10% taker
    "gemini": 0.0035,       # 0.35% taker
    "alpaca": 0.0,          # Commission-free
    "ig": 0.0006,           # Spread-based (~6bps effective)
    "ibkr": 0.0005,         # ~5bps commission
    "oanda": 0.0003,        # Spread-based (~3bps)
    "trading212": 0.0,      # Commission-free
    "etoro": 0.01,          # ~1% spread
    "saxo": 0.001,          # ~10bps commission
    "capital": 0.0006,      # Spread-based (~6bps)
    "cmc": 0.0007,          # Spread-based (~7bps)
}

# Maker fees (limit orders) — lower than taker
MAKER_FEE_RATES = {
    "binance": 0.001,       # 0.10%
    "bybit": 0.001,         # 0.10%
    "kraken": 0.0016,       # 0.16%
    "coinbase": 0.004,      # 0.40%
    "okx": 0.0005,          # 0.05%
    "cryptocom": 0.0005,    # 0.05%
    "bitstamp": 0.003,      # 0.30%
    "gate": 0.001,          # 0.10%
    "gemini": 0.002,        # 0.20%
    "alpaca": 0.0,          # Commission-free
    "ig": 0.0006,           # Spread-based (same)
    "ibkr": 0.0003,         # ~3bps commission
    "oanda": 0.0002,        # Spread-based (~2bps)
    "trading212": 0.0,      # Commission-free
    "etoro": 0.01,          # ~1% spread (same)
    "saxo": 0.0008,         # ~8bps commission
    "capital": 0.0006,      # Spread-based (same)
    "cmc": 0.0007,          # Spread-based (same)
}

# Minimum order sizes (in USD equivalent)
MIN_ORDER_USD = {
    "binance": 10.0,
    "bybit": 5.0,
    "kraken": 10.0,
    "coinbase": 10.0,
    "okx": 10.0,
    "cryptocom": 10.0,
    "bitstamp": 25.0,
    "gate": 10.0,
    "gemini": 10.0,
    "alpaca": 1.0,
    "ig": 50.0,
    "ibkr": 100.0,
    "oanda": 1.0,
    "trading212": 1.0,
    "etoro": 50.0,
    "saxo": 100.0,
    "capital": 20.0,
    "cmc": 50.0,
}

# Cumulative fee tracker
_fee_tracker = {
    "total_fees_paid": 0.0,
    "total_slippage_cost": 0.0,
    "trades_count": 0,
    "fees_by_exchange": {},
}


def get_fee_stats() -> Dict:
    """Get cumulative fee statistics."""
    return {**_fee_tracker}


def reset_fee_stats():
    """Reset fee tracking (called on portfolio reset)."""
    _fee_tracker["total_fees_paid"] = 0.0
    _fee_tracker["total_slippage_cost"] = 0.0
    _fee_tracker["trades_count"] = 0
    _fee_tracker["fees_by_exchange"] = {}


def estimate_round_trip_cost(exchange_name: str, order_value: float) -> float:
    """Estimate the total cost of a round-trip trade (buy + sell) including fees and slippage."""
    fee_rate = FEE_RATES.get(exchange_name, 0.001)
    slippage_rate = 0.001  # ~0.1% estimated slippage per side
    # Round trip = 2x fees + 2x slippage
    return order_value * (2 * fee_rate + 2 * slippage_rate)


class PaperTradingEngine:
    """Simulates trading with virtual money against real market prices."""

    def __init__(self):
        self._pending_orders: Dict[int, Order] = {}

    async def create_portfolio(self, db: AsyncSession, name: str = "Default Portfolio",
                                initial_balance: float = 10000.0, currency: str = "USD") -> Portfolio:
        """Create a new paper trading portfolio."""
        portfolio = Portfolio(
            name=name,
            is_paper=True,
            initial_balance=initial_balance,
            cash_balance=initial_balance,
            total_value=initial_balance,
            currency=currency,
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

        # Take initial snapshot
        await self._take_snapshot(db, portfolio)
        return portfolio

    async def get_portfolio(self, db: AsyncSession, portfolio_id: int = 1) -> Optional[Portfolio]:
        """Get portfolio by ID."""
        result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
        return result.scalar_one_or_none()

    async def get_or_create_default_portfolio(self, db: AsyncSession) -> Portfolio:
        """Get the default portfolio or create one."""
        result = await db.execute(select(Portfolio).where(Portfolio.id == 1))
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            portfolio = await self.create_portfolio(db)
        return portfolio

    async def place_order(self, db: AsyncSession, order_data: Dict) -> Order:
        """Place a paper trading order."""
        portfolio = await self.get_portfolio(db, order_data.get("portfolio_id", 1))
        if not portfolio:
            raise ValueError("Portfolio not found")

        # Normalize symbol to CCXT format (BASE/QUOTE)
        normalized_symbol = normalize_symbol(order_data["symbol"])

        order = Order(
            portfolio_id=portfolio.id,
            exchange_name=order_data["exchange_name"],
            symbol=normalized_symbol,
            order_type=order_data.get("order_type", "market"),
            side=order_data["side"],
            quantity=order_data["quantity"],
            price=order_data.get("price"),
            stop_price=order_data.get("stop_price"),
            status="pending",
            is_paper="true",
            strategy_name=order_data.get("strategy_name"),
            notes=order_data.get("notes"),
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        # For market orders, execute immediately
        if order.order_type == "market":
            await self._execute_market_order(db, order, portfolio)
        else:
            # Store for monitoring (limit/stop orders)
            self._pending_orders[order.id] = order
            order.status = "open"
            await db.commit()

        return order

    async def _execute_market_order(self, db: AsyncSession, order: Order, portfolio: Portfolio):
        """Execute a market order at current price."""
        ticker = await exchange_manager.get_ticker(order.exchange_name, order.symbol)
        if not ticker:
            order.status = "rejected"
            order.notes = "Could not fetch price"
            await db.commit()
            return

        exec_price = ticker["last_price"]

        # Realistic slippage: scales with order size relative to volume
        # Base: 0.05%, larger orders get more slippage (up to 0.3%)
        base_slippage = 0.0005
        order_value = order.quantity * exec_price
        # Assume daily volume of ~$50M for major pairs
        size_impact = min(0.003, (order_value / 50_000_000) * 0.1)
        total_slippage = base_slippage + size_impact

        if order.side == "buy":
            slippage_cost = exec_price * total_slippage
            exec_price *= (1 + total_slippage)
        else:
            slippage_cost = exec_price * total_slippage
            exec_price *= (1 - total_slippage)

        # Fee calculation (taker for market, maker for limit)
        fee_rate = FEE_RATES.get(order.exchange_name, 0.001)
        fee = order.quantity * exec_price * fee_rate
        total_cost = order.quantity * exec_price

        # Minimum order size check
        min_usd = MIN_ORDER_USD.get(order.exchange_name, 10.0)
        if total_cost < min_usd:
            order.status = "rejected"
            order.notes = f"Order value ${total_cost:.2f} below minimum ${min_usd:.2f} for {order.exchange_name}"
            await db.commit()
            return

        # Track fees
        _fee_tracker["total_fees_paid"] += fee
        _fee_tracker["total_slippage_cost"] += slippage_cost * order.quantity
        _fee_tracker["trades_count"] += 1
        exch = order.exchange_name
        if exch not in _fee_tracker["fees_by_exchange"]:
            _fee_tracker["fees_by_exchange"][exch] = 0.0
        _fee_tracker["fees_by_exchange"][exch] += fee

        if order.side == "buy":
            required = total_cost + fee
            if portfolio.cash_balance < required:
                order.status = "rejected"
                order.notes = f"Insufficient funds. Required: ${required:.2f}, Available: ${portfolio.cash_balance:.2f}"
                await db.commit()
                return

            portfolio.cash_balance -= required
        else:
            # For sell, check position
            position = await self._get_position(db, portfolio.id, order.symbol, order.exchange_name)
            if not position or position.quantity < order.quantity:
                order.status = "rejected"
                order.notes = "Insufficient position to sell"
                await db.commit()
                return

            portfolio.cash_balance += total_cost - fee

        # Update order
        order.filled_quantity = order.quantity
        order.filled_price = round(exec_price, 8)
        order.status = "filled"
        order.filled_at = datetime.utcnow()

        # Create trade record
        trade = Trade(
            portfolio_id=portfolio.id,
            order_id=order.id,
            exchange_name=order.exchange_name,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=round(exec_price, 8),
            fee=round(fee, 8),
            total_cost=round(total_cost, 8),
            is_paper="true",
            strategy_name=order.strategy_name,
        )
        db.add(trade)

        # Update position
        await self._update_position(db, portfolio, order, exec_price)

        # Update portfolio totals
        await self._update_portfolio_totals(db, portfolio)

        await db.commit()
        logger.info(
            f"Paper trade executed: {order.side} {order.quantity} {order.symbol} @ {exec_price:.2f}"
        )

    async def _get_position(self, db: AsyncSession, portfolio_id: int,
                             symbol: str, exchange_name: str) -> Optional[Position]:
        """Get an open position."""
        result = await db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.symbol == symbol,
                    Position.exchange_name == exchange_name,
                    Position.is_open == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _update_position(self, db: AsyncSession, portfolio: Portfolio,
                                order: Order, exec_price: float):
        """Update or create position based on trade."""
        position = await self._get_position(db, portfolio.id, order.symbol, order.exchange_name)

        if order.side == "buy":
            if position:
                # Add to existing position (average up/down)
                total_cost = (position.avg_entry_price * position.quantity) + (exec_price * order.quantity)
                position.quantity = round(position.quantity + order.quantity, 8)  # Fix float precision
                position.avg_entry_price = total_cost / position.quantity if position.quantity > 0 else exec_price
                position.current_price = exec_price
            else:
                # New position
                position = Position(
                    portfolio_id=portfolio.id,
                    symbol=order.symbol,
                    exchange_name=order.exchange_name,
                    side="long",
                    quantity=order.quantity,
                    avg_entry_price=exec_price,
                    current_price=exec_price,
                )
                db.add(position)
        elif order.side == "sell":
            if position:
                realized = (exec_price - position.avg_entry_price) * order.quantity
                position.realized_pnl += realized
                position.quantity = round(position.quantity - order.quantity, 8)  # Fix float precision
                position.current_price = exec_price

                if position.quantity <= 0.000001:
                    position.is_open = False
                    position.closed_at = datetime.utcnow()
                    position.quantity = 0

        # Update unrealized P&L
        if position and position.is_open and position.quantity > 0:
            position.unrealized_pnl = (exec_price - position.avg_entry_price) * position.quantity
            if position.avg_entry_price > 0:
                position.unrealized_pnl_pct = (
                    (exec_price - position.avg_entry_price) / position.avg_entry_price * 100
                )

    async def _update_portfolio_totals(self, db: AsyncSession, portfolio: Portfolio):
        """Recalculate portfolio total value."""
        result = await db.execute(
            select(Position).where(
                and_(Position.portfolio_id == portfolio.id, Position.is_open == True)
            )
        )
        positions = result.scalars().all()

        positions_value = sum(p.current_price * p.quantity for p in positions)
        portfolio.total_value = portfolio.cash_balance + positions_value
        portfolio.total_pnl = portfolio.total_value - portfolio.initial_balance
        if portfolio.initial_balance > 0:
            portfolio.total_pnl_pct = (portfolio.total_pnl / portfolio.initial_balance) * 100

    async def update_positions_prices(self, db: AsyncSession, portfolio_id: int = 1):
        """Update all open position prices from current market data."""
        result = await db.execute(
            select(Position).where(
                and_(Position.portfolio_id == portfolio_id, Position.is_open == True)
            )
        )
        positions = result.scalars().all()

        # Collect symbols to fetch, then fetch outside of DB context
        price_requests = [(p.id, p.exchange_name, p.symbol) for p in positions]

        # Fetch prices first (separate from DB operations)
        prices = {}
        for pid, exchange_name, symbol in price_requests:
            try:
                ticker = await exchange_manager.get_ticker(exchange_name, symbol)
                if ticker:
                    prices[pid] = ticker["last_price"]
            except Exception:
                pass

        # Now apply prices to positions
        for position in positions:
            if position.id in prices:
                price = prices[position.id]
                position.current_price = price
                position.unrealized_pnl = (price - position.avg_entry_price) * position.quantity
                if position.avg_entry_price > 0:
                    position.unrealized_pnl_pct = (
                        (price - position.avg_entry_price) / position.avg_entry_price * 100
                    )

        portfolio = await self.get_portfolio(db, portfolio_id)
        if portfolio:
            await self._update_portfolio_totals(db, portfolio)
            await db.commit()

    async def _take_snapshot(self, db: AsyncSession, portfolio: Portfolio):
        """Take a portfolio value snapshot."""
        snapshot = PortfolioSnapshot(
            portfolio_id=portfolio.id,
            total_value=portfolio.total_value,
            cash_balance=portfolio.cash_balance,
            positions_value=portfolio.total_value - portfolio.cash_balance,
            total_pnl=portfolio.total_pnl,
        )
        db.add(snapshot)
        await db.commit()

    async def get_positions(self, db: AsyncSession, portfolio_id: int = 1,
                             open_only: bool = True) -> List[Position]:
        """Get all positions for a portfolio."""
        query = select(Position).where(Position.portfolio_id == portfolio_id)
        if open_only:
            query = query.where(Position.is_open == True)
        result = await db.execute(query.order_by(Position.opened_at.desc()))
        return list(result.scalars().all())

    async def get_orders(self, db: AsyncSession, portfolio_id: int = 1,
                          limit: int = 50) -> List[Order]:
        """Get orders for a portfolio."""
        result = await db.execute(
            select(Order)
            .where(Order.portfolio_id == portfolio_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_trades(self, db: AsyncSession, portfolio_id: int = 1,
                          limit: int = 50) -> List[Trade]:
        """Get trades for a portfolio."""
        result = await db.execute(
            select(Trade)
            .where(Trade.portfolio_id == portfolio_id)
            .order_by(Trade.executed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_snapshots(self, db: AsyncSession, portfolio_id: int = 1,
                             limit: int = 100) -> List[PortfolioSnapshot]:
        """Get portfolio snapshots for charts."""
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshot.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def reset_portfolio(self, db: AsyncSession, portfolio_id: int = 1,
                               new_balance: float = 10000.0):
        """Reset a paper portfolio to starting state."""
        # Reset fee tracker
        reset_fee_stats()
        # Close all positions
        result = await db.execute(
            select(Position).where(
                and_(Position.portfolio_id == portfolio_id, Position.is_open == True)
            )
        )
        for pos in result.scalars().all():
            pos.is_open = False
            pos.closed_at = datetime.utcnow()

        # Reset portfolio
        portfolio = await self.get_portfolio(db, portfolio_id)
        if portfolio:
            portfolio.cash_balance = new_balance
            portfolio.initial_balance = new_balance
            portfolio.total_value = new_balance
            portfolio.total_pnl = 0.0
            portfolio.total_pnl_pct = 0.0
            await db.commit()
            await self._take_snapshot(db, portfolio)

        return portfolio

    async def cancel_order(self, db: AsyncSession, order_id: int) -> Optional[Order]:
        """Cancel a pending/open order."""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order and order.status in ("pending", "open"):
            order.status = "cancelled"
            if order.id in self._pending_orders:
                del self._pending_orders[order.id]
            await db.commit()
        return order


# Singleton
paper_engine = PaperTradingEngine()
