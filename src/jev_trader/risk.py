from .models import Action, JevDecision, MarketState, RiskDecision, RiskLimits


def evaluate_risk(
    state: MarketState,
    decision: JevDecision,
    limits: RiskLimits,
) -> RiskDecision:
    """Apply deterministic safety and profitability vetoes to Jev's proposal."""
    reasons: list[str] = []

    if decision.action is not Action.NO_TRADE:
        if state.data_age_ms > limits.max_data_age_ms:
            reasons.append("market_data_stale")
        if decision.expected_edge_bps < limits.min_expected_edge_bps:
            reasons.append("edge_below_cost_threshold")
        if decision.confidence < limits.min_confidence:
            reasons.append("confidence_below_threshold")
        if decision.risk_score < limits.min_risk_score:
            reasons.append("risk_score_below_threshold")
        if decision.requested_leverage > limits.max_leverage:
            reasons.append("leverage_limit_exceeded")
        if state.cex is not None and state.cex.spread_bps > limits.max_spread_bps:
            reasons.append("spread_too_wide")

    return RiskDecision(
        approved=not reasons,
        reasons=tuple(reasons),
        allowed_leverage=min(decision.requested_leverage, limits.max_leverage),
    )
