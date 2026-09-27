from __future__ import annotations

from collections.abc import Callable, Sequence

from .backtest import BacktestPortfolio
from .jev_policy import JevPolicy
from .models import RiskLimits
from .runner import BacktestRunner, BacktestSummary, BacktestTick

PolicyFactory = Callable[[], JevPolicy]


def compare_policies(
    ticks: Sequence[BacktestTick],
    policies: dict[str, PolicyFactory],
    *,
    initial_cash: float = 10_000,
    limits: RiskLimits | None = None,
) -> dict[str, BacktestSummary]:
    """Run each policy against identical immutable ticks and risk limits."""
    if not policies:
        raise ValueError("at least one policy is required")
    if initial_cash <= 0:
        raise ValueError("initial_cash must be positive")
    risk_limits = limits or RiskLimits()
    results: dict[str, BacktestSummary] = {}
    for name, factory in policies.items():
        portfolio = BacktestPortfolio(initial_cash=initial_cash)
        results[name] = BacktestRunner(factory(), risk_limits, portfolio).run(list(ticks))
    return results
