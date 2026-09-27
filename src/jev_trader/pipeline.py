from __future__ import annotations

from dataclasses import dataclass

from .arb import CexDexOpportunity
from .jev_policy import JevPolicy
from .models import ArbitrageContext, JevDecision, MarketState, RiskLimits
from .risk import evaluate_risk


@dataclass(frozen=True)
class PolicyEvaluation:
    opportunity: CexDexOpportunity
    decision: JevDecision | None
    approved: bool
    reasons: tuple[str, ...]


def evaluate_with_jev(
    state: MarketState,
    opportunity: CexDexOpportunity,
    policy: JevPolicy,
    limits: RiskLimits,
) -> PolicyEvaluation:
    """Use Jev as strategy authority, then enforce local hard risk limits."""
    if not opportunity.executable:
        return PolicyEvaluation(
            opportunity=opportunity,
            decision=None,
            approved=False,
            reasons=opportunity.reasons or ("opportunity_not_executable",),
        )

    enriched_state = state.model_copy(
        update={
            "arbitrage": ArbitrageContext(
                direction=opportunity.direction.value,
                buy_price=opportunity.buy_price,
                sell_price=opportunity.sell_price,
                gross_edge_bps=opportunity.gross_edge_bps,
                net_edge_bps=opportunity.net_edge_bps,
                quantity=opportunity.quantity,
            )
        }
    )
    proposed = policy.decide(enriched_state)
    # Expected edge is measured deterministically from executable venue quotes,
    # not hallucinated or estimated by the model.
    decision = proposed.model_copy(update={"expected_edge_bps": opportunity.net_edge_bps})
    risk = evaluate_risk(enriched_state, decision, limits)
    return PolicyEvaluation(
        opportunity=opportunity,
        decision=decision,
        approved=risk.approved,
        reasons=risk.reasons,
    )
