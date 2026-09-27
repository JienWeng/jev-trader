"""Jev integration boundary.

The provider client is intentionally not coupled to the execution layer. A future
adapter will translate MarketState into TypeSafe questions (Choice, Score, Noul)
and validate the returned typed values into JevDecision.
"""

from collections.abc import Protocol

from .models import JevDecision, MarketState


class JevPolicy(Protocol):
    def decide(self, state: MarketState) -> JevDecision:
        """Return a typed strategy decision, never an exchange order."""


class UnconfiguredJevPolicy:
    """Safe default until a TypeSafe client is configured."""

    def decide(self, state: MarketState) -> JevDecision:
        return JevDecision(
            action="no_trade",
            regime="unknown",
            action_probability=1.0,
            confidence=1.0,
            setup_score=0.0,
            execution_score=0.0,
            risk_score=1.0,
            expected_edge_bps=0.0,
            holding_period_seconds=0,
            requested_leverage=0.0,
            reason_codes=("jev_not_configured",),
        )
