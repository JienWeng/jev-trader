from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .models import Action, MarketState, Venue


class CostEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)
    gross_edge_bps: float
    fees_bps: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)
    gas_bps: float = Field(ge=0)
    funding_bps: float
    net_edge_bps: float


class MeanReversionCandidate(BaseModel):
    """A deterministic candidate that Jev must accept, reject, or modify."""

    model_config = ConfigDict(frozen=True)
    action: Action
    venue: Venue | None = None
    gross_edge_bps: float
    net_edge_bps: float
    z_score: float | None
    reason_codes: tuple[str, ...] = ()


def estimate_costs(state: MarketState, gross_edge_bps: float) -> CostEstimate:
    funding = abs(state.funding_rate_bps or 0.0)
    net = (
        gross_edge_bps
        - state.estimated_fee_bps
        - state.estimated_slippage_bps
        - state.estimated_gas_bps
        - funding
    )
    return CostEstimate(
        gross_edge_bps=gross_edge_bps,
        fees_bps=state.estimated_fee_bps,
        slippage_bps=state.estimated_slippage_bps,
        gas_bps=state.estimated_gas_bps,
        funding_bps=funding,
        net_edge_bps=net,
    )


def build_mean_reversion_candidate(
    state: MarketState,
    *,
    entry_z_score: float = 2.0,
    gross_edge_bps: float | None = None,
) -> MeanReversionCandidate:
    """Create a candidate from divergence; Jev remains the policy authority."""
    z_score = state.z_score
    if z_score is None or abs(z_score) < entry_z_score:
        return MeanReversionCandidate(
            action=Action.NO_TRADE,
            venue=None,
            gross_edge_bps=0.0,
            net_edge_bps=0.0,
            z_score=z_score,
            reason_codes=("z_score_below_entry_threshold",),
        )

    estimated_gross = gross_edge_bps if gross_edge_bps is not None else abs(z_score) * 10.0
    costs = estimate_costs(state, estimated_gross)
    action = Action.OPEN_SHORT if z_score > 0 else Action.OPEN_LONG
    venue = Venue.BINANCE if state.cex is not None else Venue.DEX
    reasons = ("positive_net_edge",) if costs.net_edge_bps > 0 else ("edge_does_not_cover_costs",)

    return MeanReversionCandidate(
        action=action if costs.net_edge_bps > 0 else Action.NO_TRADE,
        venue=venue if costs.net_edge_bps > 0 else None,
        gross_edge_bps=costs.gross_edge_bps,
        net_edge_bps=costs.net_edge_bps,
        z_score=z_score,
        reason_codes=reasons,
    )
