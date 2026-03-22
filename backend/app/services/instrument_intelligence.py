"""
Instrument Intelligence — decides WHAT to trade, HOW to trade it, and WHEN to exit.

This is the "brain" that answers:
1. Should I go spot, perpetual, or margin for this trade?
2. Should I go long or short? (not just follow strategy blindly)
3. What leverage is appropriate? (if any)
4. Is this specific trade worth the fees/risk?
5. Should I exit this position NOW? (beyond just stop-loss)
6. Should I NOT trade at all right now?

Key principle: the smartest trade is often NO trade.
"""
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# INSTRUMENT SELECTOR — chooses spot vs futures vs margin
# ═══════════════════════════════════════════════════════════════
class InstrumentSelector:
    """
    Decides which instrument type is optimal for current conditions.
    
    Rules:
    - Trending strongly? → Futures/perpetual (leverage amplifies)
    - Ranging/uncertain? → Spot only (no leverage risk)
    - Bearish conviction? → Short perpetual (profit from decline)
    - High volatility? → Reduce leverage or stay spot
    - Low capital? → Spot only (can't afford liquidation risk)
    """

    # Funding rates per 8h (approximate, for fee calculation)
    TYPICAL_FUNDING_RATES = {
        "perpetual": 0.0001,  # 0.01% per 8h = ~0.1% daily
    }

    # Max leverage by risk tolerance
    MAX_LEVERAGE = {
        "conservative": 1.0,    # No leverage
        "moderate": 3.0,        # Up to 3x
        "aggressive": 5.0,      # Up to 5x (never more for autonomous)
    }

    def select_instrument(
        self,
        signal: int,  # 1=buy, -1=sell
        regime: str,
        confidence: float,
        risk_level: str,
        volatility: float,
        portfolio_value: float,
        fear_greed: int,
        ai_sentiment: str,
        existing_positions: List[Dict],
    ) -> Dict:
        """
        Decide the optimal instrument type, direction, and leverage.
        Returns: { instrument, side, leverage, reasoning }
        """
        reasoning = []

        # ─── Direction Decision ───
        # Don't blindly follow signal — cross-check with regime + AI
        direction = "long" if signal == 1 else "short"

        # Override: if signal says buy but regime is trending_down + AI says bearish, flip
        if signal == 1 and regime == "trending_down" and ai_sentiment == "bearish":
            direction = "short"
            reasoning.append("Signal said buy but regime + AI both bearish → flipped to short")
        elif signal == -1 and regime == "trending_up" and ai_sentiment == "bullish":
            direction = "long"
            reasoning.append("Signal said sell but regime + AI both bullish → flipped to long")

        # ─── Instrument Type Decision ───
        instrument = "spot"
        leverage = 1.0

        # Rule 1: Small portfolio → always spot (can't afford liquidation)
        if portfolio_value < 1000:
            instrument = "spot"
            direction = "long"  # Can't short on spot
            reasoning.append(f"Portfolio ${portfolio_value:.0f} too small for derivatives → spot only")

        # Rule 2: High volatility → spot or very low leverage
        elif volatility > 40:
            instrument = "spot"
            direction = "long" if direction == "long" else "long"  # Too risky to short in high vol
            reasoning.append(f"Volatility {volatility:.0f}% too high for leverage → spot only")

        # Rule 3: Strong trend + high confidence → perpetual with moderate leverage
        elif regime in ("trending_up", "trending_down") and confidence > 0.65:
            instrument = "perpetual"
            max_lev = self.MAX_LEVERAGE.get(
                "conservative" if risk_level == "high" else "moderate" if risk_level == "medium" else "aggressive",
                3.0
            )
            # Scale leverage with confidence: 60% conf = 1x, 80% conf = 2x, 95% conf = max
            leverage = max(1.0, min(max_lev, 1.0 + (confidence - 0.6) * max_lev / 0.4))
            leverage = round(leverage, 1)
            reasoning.append(f"Strong {regime} + {confidence:.0%} confidence → perpetual {leverage}x")

        # Rule 4: Bearish signal → short perpetual (only way to profit from decline)
        elif direction == "short" and confidence > 0.55:
            instrument = "perpetual"
            leverage = min(2.0, self.MAX_LEVERAGE.get("moderate", 3.0))
            reasoning.append(f"Short signal with {confidence:.0%} confidence → short perpetual {leverage}x")

        # Rule 5: Extreme fear → contrarian spot buy (greed → don't long)
        elif fear_greed < 20:
            instrument = "spot"
            direction = "long"
            reasoning.append(f"Extreme fear (F&G={fear_greed}) → contrarian spot buy")

        elif fear_greed > 80:
            instrument = "spot"
            direction = "long"  # Stay spot, reduce size elsewhere
            reasoning.append(f"Extreme greed (F&G={fear_greed}) → spot only, caution")

        # Rule 6: Ranging market → spot, no leverage
        else:
            instrument = "spot"
            reasoning.append(f"Ranging/unclear conditions → spot, no leverage")

        # ─── Safety: Can we actually short? ───
        if direction == "short" and instrument == "spot":
            # Can't short on spot — need perpetual
            instrument = "perpetual"
            leverage = min(1.0, self.MAX_LEVERAGE.get("conservative", 1.0))
            reasoning.append("Short requires perpetual (can't short spot)")

        # ─── Final leverage safety clamp ───
        if instrument == "perpetual":
            # Never exceed 5x for autonomous trading
            leverage = min(5.0, leverage)
            # In high risk, cap at 2x
            if risk_level == "high":
                leverage = min(2.0, leverage)
                reasoning.append(f"High risk → leverage capped at {leverage}x")

        return {
            "instrument": instrument,
            "direction": direction,
            "leverage": leverage,
            "reasoning": reasoning,
            "signal_original": signal,
        }


# ═══════════════════════════════════════════════════════════════
# SMART EXIT DECISION — knows WHEN and WHY to sell
# ═══════════════════════════════════════════════════════════════
class SmartExitDecision:
    """
    Goes beyond simple stop-loss. Analyzes whether to exit based on:
    - Has the regime changed since entry?
    - Is the position's original thesis still valid?
    - Is there a better opportunity to deploy this capital?
    - Are we approaching a high-risk event?
    - Is the risk/reward ratio still favorable?
    """

    def should_exit(
        self,
        position: Dict,
        current_regime: str,
        entry_regime: Optional[str],
        fear_greed: int,
        ai_sentiment: str,
        portfolio_positions: List[Dict],
        volatility: float,
    ) -> Dict:
        """
        Intelligent exit analysis for an open position.
        Returns: { should_exit, urgency, reasoning, action }
        """
        pnl_pct = position.get("unrealized_pnl_pct", 0)
        side = position.get("side", "long")
        instrument = position.get("instrument_type", "spot")
        leverage = position.get("leverage", 1.0)
        hold_hours = 0

        if position.get("opened_at"):
            try:
                opened = datetime.fromisoformat(str(position["opened_at"]))
                hold_hours = (datetime.utcnow() - opened).total_seconds() / 3600
            except Exception:
                pass

        reasons = []
        should_exit = False
        urgency = "low"

        # ─── Rule 1: Regime changed since entry ───
        if entry_regime and current_regime != entry_regime:
            if side == "long" and current_regime == "trending_down":
                should_exit = True
                urgency = "high"
                reasons.append(f"Regime shifted from {entry_regime} to {current_regime} — long position at risk")
            elif side == "short" and current_regime == "trending_up":
                should_exit = True
                urgency = "high"
                reasons.append(f"Regime shifted to {current_regime} — short position at risk")

        # ─── Rule 2: Leveraged position losing → urgent exit ───
        if leverage > 1.0 and pnl_pct < -3:
            should_exit = True
            urgency = "critical"
            reasons.append(f"Leveraged position ({leverage}x) down {pnl_pct:.1f}% → exit before liquidation")

        # ─── Rule 3: AI sentiment flipped against position ───
        if side == "long" and ai_sentiment == "bearish" and pnl_pct < 2:
            should_exit = True
            urgency = "medium"
            reasons.append(f"AI turned bearish while holding long with only {pnl_pct:+.1f}% gain")
        elif side == "short" and ai_sentiment == "bullish" and pnl_pct < 2:
            should_exit = True
            urgency = "medium"
            reasons.append(f"AI turned bullish while holding short with only {pnl_pct:+.1f}% gain")

        # ─── Rule 4: Extreme fear + long = hold (contrarian) ───
        if fear_greed < 15 and side == "long" and pnl_pct > -5:
            # Don't exit in extreme fear — this is often the bottom
            should_exit = False
            reasons.append(f"Extreme fear (F&G={fear_greed}) — holding long (contrarian patience)")

        # ─── Rule 5: Extreme greed + long with profit → take profit ───
        if fear_greed > 80 and side == "long" and pnl_pct > 3:
            should_exit = True
            urgency = "medium"
            reasons.append(f"Extreme greed (F&G={fear_greed}) + {pnl_pct:+.1f}% profit → taking profits")

        # ─── Rule 6: Perpetual funding eating profits ───
        if instrument == "perpetual":
            funding_cost_daily = position.get("quantity", 0) * position.get("current_price", 0) * 0.0003
            if hold_hours > 24 and funding_cost_daily > abs(position.get("unrealized_pnl", 0)) * 0.5:
                should_exit = True
                urgency = "medium"
                reasons.append(f"Funding costs exceeding 50% of unrealized P&L — close perpetual")

        # ─── Rule 7: Winning position held too long → diminishing returns ───
        if pnl_pct > 5 and hold_hours > 48:
            urgency = "low"
            reasons.append(f"Consider partial take-profit: +{pnl_pct:.1f}% over {hold_hours:.0f}h")

        # ─── Rule 8: Volatility spike on leveraged position ───
        if leverage > 1.0 and volatility > 50:
            should_exit = True
            urgency = "high"
            reasons.append(f"Volatility spike ({volatility:.0f}%) with {leverage}x leverage → deleverage")

        if not reasons:
            reasons.append("No exit triggers — position is healthy")

        return {
            "should_exit": should_exit,
            "urgency": urgency,
            "reasons": reasons,
            "pnl_pct": round(pnl_pct, 2),
            "hold_hours": round(hold_hours, 1),
        }


# ═══════════════════════════════════════════════════════════════
# TRADE WORTHINESS FILTER — is this trade even worth it?
# ═══════════════════════════════════════════════════════════════
class TradeWorthinessFilter:
    """
    Answers: "Even if the signal is correct, is this trade profitable
    after fees, slippage, and risk?"
    
    A trade that wins 55% of the time with 0.5% avg profit but costs
    0.3% in fees per round trip is barely worth it.
    """

    def is_trade_worthy(
        self,
        exchange: str,
        instrument: str,
        leverage: float,
        expected_move_pct: float,
        confidence: float,
        position_value: float,
    ) -> Dict:
        """Check if the expected profit exceeds the expected cost."""
        from app.services.paper_trading import FEE_RATES

        # Costs
        fee_rate = FEE_RATES.get(exchange, 0.001)
        round_trip_fee_pct = fee_rate * 2 * 100  # Both legs as percentage
        slippage_pct = 0.1  # ~0.05% per side

        # Funding cost for perpetuals (estimated 1 day hold)
        funding_pct = 0.03 if instrument == "perpetual" else 0  # ~0.03% per day

        total_cost_pct = round_trip_fee_pct + slippage_pct + funding_pct

        # Expected profit (leveraged)
        expected_profit_pct = expected_move_pct * leverage * confidence

        # Risk-adjusted: must expect at least 2x the cost to be worth it
        profit_to_cost_ratio = expected_profit_pct / total_cost_pct if total_cost_pct > 0 else 0

        is_worthy = profit_to_cost_ratio >= 1.2  # 1.2x = profit exceeds cost by 20%

        return {
            "is_worthy": is_worthy,
            "expected_profit_pct": round(expected_profit_pct, 3),
            "total_cost_pct": round(total_cost_pct, 3),
            "profit_to_cost_ratio": round(profit_to_cost_ratio, 2),
            "breakdown": {
                "fees_pct": round(round_trip_fee_pct, 3),
                "slippage_pct": round(slippage_pct, 3),
                "funding_pct": round(funding_pct, 3),
                "leverage": leverage,
                "confidence": round(confidence, 3),
            },
            "reason": f"Expected {expected_profit_pct:.2f}% vs cost {total_cost_pct:.2f}% (ratio: {profit_to_cost_ratio:.1f}x)"
                      if is_worthy else
                      f"NOT WORTH IT: Expected {expected_profit_pct:.2f}% barely covers cost {total_cost_pct:.2f}% (ratio: {profit_to_cost_ratio:.1f}x, need 1.2x+)",
        }


# ═══════════════════════════════════════════════════════════════
# LIQUIDATION CALCULATOR — protection for leveraged positions
# ═══════════════════════════════════════════════════════════════
class LiquidationCalculator:
    """Calculates and monitors liquidation prices for leveraged positions."""

    @staticmethod
    def calculate_liquidation_price(entry_price: float, leverage: float, side: str,
                                     maintenance_margin_pct: float = 0.5) -> Optional[float]:
        """
        Calculate the price at which a leveraged position gets liquidated.
        maintenance_margin_pct: exchange maintenance margin (typically 0.5% for crypto)
        """
        if leverage <= 1.0:
            return None  # No liquidation for spot

        if side == "long":
            # Liquidation = entry * (1 - 1/leverage + maintenance_margin)
            liq_price = entry_price * (1 - (1 / leverage) + (maintenance_margin_pct / 100))
        else:
            # Short liquidation = entry * (1 + 1/leverage - maintenance_margin)
            liq_price = entry_price * (1 + (1 / leverage) - (maintenance_margin_pct / 100))

        return round(liq_price, 2)

    @staticmethod
    def is_near_liquidation(current_price: float, liquidation_price: float,
                             side: str, buffer_pct: float = 5.0) -> bool:
        """Check if current price is dangerously close to liquidation."""
        if liquidation_price is None:
            return False

        if side == "long":
            distance_pct = ((current_price - liquidation_price) / current_price) * 100
        else:
            distance_pct = ((liquidation_price - current_price) / current_price) * 100

        return distance_pct < buffer_pct


# ═══════════════════════════════════════════════════════════════
# UNIFIED INSTRUMENT INTELLIGENCE
# ═══════════════════════════════════════════════════════════════
class InstrumentIntelligence:
    """Coordinates all instrument-level intelligence."""

    def __init__(self):
        self.selector = InstrumentSelector()
        self.exit_brain = SmartExitDecision()
        self.worthiness = TradeWorthinessFilter()
        self.liquidation = LiquidationCalculator()

    def decide_trade(
        self,
        signal: int,
        regime: str,
        confidence: float,
        risk_level: str,
        volatility: float,
        portfolio_value: float,
        fear_greed: int,
        ai_sentiment: str,
        existing_positions: List[Dict],
        exchange: str,
    ) -> Dict:
        """
        Full trade decision: what instrument, direction, leverage, and is it worth it.
        """
        # Step 1: Select instrument
        selection = self.selector.select_instrument(
            signal=signal, regime=regime, confidence=confidence,
            risk_level=risk_level, volatility=volatility,
            portfolio_value=portfolio_value, fear_greed=fear_greed,
            ai_sentiment=ai_sentiment, existing_positions=existing_positions,
        )

        # Step 2: Check trade worthiness
        # Estimate expected move based on regime and volatility
        expected_move = min(5.0, volatility / 10)  # Rough estimate
        worthiness = self.worthiness.is_trade_worthy(
            exchange=exchange,
            instrument=selection["instrument"],
            leverage=selection["leverage"],
            expected_move_pct=expected_move,
            confidence=confidence,
            position_value=portfolio_value * 0.05,  # Assume 5% position
        )

        # Step 3: Calculate liquidation price if leveraged
        liq_price = None
        if selection["leverage"] > 1.0:
            liq_price = self.liquidation.calculate_liquidation_price(
                entry_price=0,  # Will be calculated at execution time
                leverage=selection["leverage"],
                side=selection["direction"],
            )

        approved = worthiness["is_worthy"]
        all_reasoning = selection["reasoning"] + [worthiness["reason"]]

        return {
            "approved": approved,
            "instrument": selection["instrument"],
            "direction": selection["direction"],
            "leverage": selection["leverage"],
            "worthiness": worthiness,
            "reasoning": all_reasoning,
            "signal_original": signal,
        }

    def evaluate_exits(
        self,
        positions: List[Dict],
        current_regime: str,
        fear_greed: int,
        ai_sentiment: str,
        volatility: float,
    ) -> List[Dict]:
        """Evaluate all open positions for intelligent exit decisions."""
        exit_decisions = []

        for pos in positions:
            if not pos.get("is_open"):
                continue

            decision = self.exit_brain.should_exit(
                position=pos,
                current_regime=current_regime,
                entry_regime=pos.get("entry_regime"),
                fear_greed=fear_greed,
                ai_sentiment=ai_sentiment,
                portfolio_positions=positions,
                volatility=volatility,
            )

            # Also check liquidation proximity for leveraged positions
            leverage = pos.get("leverage", 1.0)
            if leverage > 1.0 and pos.get("liquidation_price"):
                near_liq = self.liquidation.is_near_liquidation(
                    current_price=pos.get("current_price", 0),
                    liquidation_price=pos["liquidation_price"],
                    side=pos.get("side", "long"),
                )
                if near_liq:
                    decision["should_exit"] = True
                    decision["urgency"] = "critical"
                    decision["reasons"].append(
                        f"LIQUIDATION WARNING: price near liquidation level ${pos['liquidation_price']:.2f}"
                    )

            if decision["should_exit"]:
                exit_decisions.append({
                    "position": pos,
                    "decision": decision,
                })

        return exit_decisions


# Singleton
instrument_intel = InstrumentIntelligence()
