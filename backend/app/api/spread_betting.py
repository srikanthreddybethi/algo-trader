"""Spread Betting API — position sizing, margin, funding, market hours, tax routing."""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.spread_betting import spread_bet_engine
from app.strategies.spread_betting_strategies import list_sb_strategies

router = APIRouter(prefix="/api/spread-betting", tags=["spread-betting"])


@router.get("/evaluate")
async def evaluate_spread_bet(
    symbol: str = Query(..., description="Instrument symbol"),
    direction: str = Query(..., description="buy or sell"),
    account_balance: float = Query(..., description="Account balance in GBP"),
    risk_pct: float = Query(1.0, description="Risk percentage per trade"),
    stop_distance: float = Query(20.0, description="Stop distance in points"),
    asset_class: Optional[str] = Query(None, description="Override asset class"),
    current_price: float = Query(0.0, description="Current price for margin calc"),
):
    """Evaluate a potential spread bet with full sizing, margin, and risk analysis."""
    return spread_bet_engine.evaluate_spread_bet(
        symbol=symbol,
        direction=direction,
        account_balance=account_balance,
        risk_pct=risk_pct,
        stop_distance=stop_distance,
        asset_class=asset_class,
        current_price=current_price,
    )


@router.get("/position-size")
async def calculate_position_size(
    account_balance: float = Query(...),
    risk_pct: float = Query(1.0),
    stop_distance: float = Query(..., description="Stop distance in points"),
    asset_class: str = Query("forex_major"),
    symbol: str = Query("", description="Symbol for classification fallback"),
    current_price: float = Query(0.0),
):
    """Calculate optimal £/point stake for a spread bet."""
    return spread_bet_engine.sizer.calculate_stake(
        account_balance=account_balance,
        risk_pct=risk_pct,
        stop_distance_points=stop_distance,
        asset_class=asset_class,
        symbol=symbol,
        current_price=current_price,
    )


@router.get("/margin-status")
async def get_margin_status():
    """Get current margin utilisation from the margin monitor."""
    return spread_bet_engine.margin.get_margin_utilisation()


@router.get("/funding-cost")
async def calculate_funding_cost(
    stake_per_point: float = Query(...),
    current_price: float = Query(...),
    asset_class: str = Query("forex_major"),
    direction: str = Query("buy"),
    days: int = Query(1, ge=1, le=365),
):
    """Calculate overnight funding cost for a spread bet position."""
    daily = spread_bet_engine.funding.calculate_daily_funding(
        stake_per_point, current_price, asset_class, direction,
    )
    total_cost = spread_bet_engine.funding.calculate_holding_cost(
        stake_per_point, current_price, asset_class, days, direction,
    )
    return {
        "daily_cost": daily["daily_cost"],
        "weekly_cost": daily["weekly_cost"],
        "total_cost": total_cost,
        "annual_rate_pct": daily["annual_rate_pct"],
        "days": days,
    }


@router.get("/market-hours/{symbol}")
async def get_market_hours(symbol: str):
    """Check market status, session type, and gap risk for a symbol."""
    hours = spread_bet_engine.market_hours.is_market_open(symbol)
    gap = spread_bet_engine.gap_protection.assess_gap_risk(symbol)
    close_warning = spread_bet_engine.market_hours.should_close_before_gap(symbol)
    windows = spread_bet_engine.market_hours.get_optimal_trading_windows(symbol)
    return {
        **hours,
        "gap_risk": gap["risk_level"],
        "gap_reasons": gap["reasons"],
        "should_close_before_gap": close_warning["should_close"],
        "close_warning_reason": close_warning["reason"],
        "optimal_windows": windows,
    }


@router.get("/spread-stats/{symbol}")
async def get_spread_stats(symbol: str):
    """Get spread statistics for a symbol."""
    stats = spread_bet_engine.spread_monitor.get_spread_stats(symbol)
    current = spread_bet_engine.spread_monitor.get_current_spread(symbol)
    return {
        **stats,
        "is_normal": current["is_normal"],
        "vs_average": current["vs_average"],
    }


@router.get("/tax-route")
async def get_tax_route(
    symbol: str = Query(...),
    direction: str = Query("buy"),
    hold_duration_days: int = Query(1, ge=1),
    expected_pnl: float = Query(100.0),
):
    """Get tax-efficient venue recommendation (spread bet vs CFD vs stock)."""
    return spread_bet_engine.tax_router.recommend_venue(
        symbol=symbol,
        direction=direction,
        hold_duration_days=hold_duration_days,
        expected_pnl=expected_pnl,
    )


@router.get("/strategies")
async def get_sb_strategies():
    """List all spread-betting-specific strategies."""
    return list_sb_strategies()


@router.post("/simulate")
async def simulate_spread_bet(body: dict):
    """Simulate the full economics of a spread bet trade."""
    symbol = body.get("symbol", "EURUSD")
    direction = body.get("direction", "buy")
    stake_per_point = body.get("stake_per_point", 1.0)
    stop_distance = body.get("stop_distance", 20.0)
    take_profit_distance = body.get("take_profit_distance", 40.0)
    guaranteed_stop = body.get("guaranteed_stop", False)
    hold_days = body.get("hold_days", 0)

    asset_class = spread_bet_engine.sizer.classify_asset(symbol)
    margin_rate = spread_bet_engine.sizer.calculate_margin_required(
        stake_per_point, max(stop_distance * 50, 1.0), asset_class,
    ) if stake_per_point > 0 else {"margin_required": 0}

    max_loss = round(stake_per_point * stop_distance, 2)
    max_profit = round(stake_per_point * take_profit_distance, 2)
    risk_reward = round(take_profit_distance / stop_distance, 2) if stop_distance > 0 else 0

    overnight_cost = 0.0
    if hold_days > 0:
        overnight_cost = spread_bet_engine.funding.calculate_holding_cost(
            stake_per_point, max(stop_distance * 50, 1.0), asset_class, hold_days, direction,
        )

    gs_cost = 0.0
    if guaranteed_stop:
        from app.services.spread_betting import MARGIN_RATES as _MR
        # Typical GS premium ~0.3-1% of stop distance in cost
        gs_premium_rate = 0.008  # ~0.8%
        gs_cost = round(stake_per_point * stop_distance * gs_premium_rate, 2)

    net_profit_if_target = round(max_profit - overnight_cost - gs_cost, 2)

    return {
        "symbol": symbol,
        "direction": direction,
        "stake_per_point": stake_per_point,
        "margin_required": margin_rate.get("margin_required", 0),
        "max_loss": max_loss,
        "max_profit": max_profit,
        "overnight_cost": round(overnight_cost, 2),
        "guaranteed_stop_cost": gs_cost,
        "net_profit_if_target_hit": net_profit_if_target,
        "risk_reward_ratio": risk_reward,
        "hold_days": hold_days,
        "asset_class": asset_class,
    }


@router.get("/dashboard")
async def get_sb_dashboard():
    """Get spread betting dashboard data: margin, funding, positions overview."""
    margin = spread_bet_engine.margin.get_margin_utilisation()
    margin_call = spread_bet_engine.margin.check_margin_call_risk()

    return {
        "open_sb_positions": len(spread_bet_engine.margin._open_positions),
        "total_margin_used": margin["used"],
        "margin_utilisation": margin["utilisation_pct"],
        "margin_warning_level": margin["warning_level"],
        "margin_call_risk": margin_call["at_risk"],
        "margin_level_pct": margin_call["margin_level_pct"],
        "daily_funding_costs": 0.0,  # Would sum from active positions
        "todays_pnl": 0.0,  # Would come from portfolio
        "active_guaranteed_stops": 0,  # Would track from broker
        "spread_alerts": [],  # Would come from spread monitor
    }
