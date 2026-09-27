from __future__ import annotations

from .jev_policy import JevPolicy
from .models import Action, JevDecision, MarketState, Regime, Venue


class RuleBasedPolicy(JevPolicy):
    """Transparent benchmark policy; intentionally not an execution authority."""

    def __init__(self, *, min_edge_bps: float = 12.0, min_abs_z_score: float = 2.0):
        self.min_edge_bps = min_edge_bps
        self.min_abs_z_score = min_abs_z_score

    def decide(self, state: MarketState) -> JevDecision:
        arb = state.arbitrage
        z_score = state.z_score or 0.0
        eligible = (
            arb is not None
            and arb.net_edge_bps >= self.min_edge_bps
            and abs(z_score) >= self.min_abs_z_score
        )
        return JevDecision(
            action=Action.OPEN_LONG if eligible else Action.NO_TRADE,
            venue=Venue.BINANCE if state.cex is not None else Venue.DEX,
            regime=Regime.RANGE if eligible else Regime.UNKNOWN,
            action_probability=1.0 if eligible else 0.0,
            confidence=0.8 if eligible else 1.0,
            setup_score=0.8 if eligible else 0.0,
            execution_score=0.8 if eligible else 0.0,
            risk_score=0.8 if eligible else 1.0,
            expected_edge_bps=arb.net_edge_bps if arb is not None else 0.0,
            holding_period_seconds=60 if eligible else 0,
            requested_leverage=0.0,
            reason_codes=("rule_baseline_eligible",) if eligible else ("rule_baseline_reject",),
        )
