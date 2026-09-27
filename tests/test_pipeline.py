from jev_trader.arb import ArbDirection, CexDexOpportunity
from jev_trader.models import Action, JevDecision, MarketState, Regime, RiskLimits
from jev_trader.pipeline import evaluate_with_jev


class FakePolicy:
    def __init__(self):
        self.state = None

    def decide(self, state):
        self.state = state
        return JevDecision(
            action=Action.OPEN_LONG,
            venue="binance",
            regime=Regime.RANGE,
            action_probability=0.9,
            confidence=0.9,
            setup_score=0.8,
            execution_score=0.8,
            risk_score=0.8,
            expected_edge_bps=0,
            holding_period_seconds=30,
            requested_leverage=1,
        )


def state():
    return MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1,
        estimated_fee_bps=4,
        estimated_slippage_bps=2,
        estimated_gas_bps=0,
        data_age_ms=10,
    )


def opportunity(executable=True):
    return CexDexOpportunity(
        symbol="BTCUSDT",
        direction=ArbDirection.BUY_CEX_SELL_DEX,
        quantity=1,
        buy_price=100,
        sell_price=100.2,
        gross_edge_bps=20,
        total_cost_bps=8,
        net_edge_bps=12,
        executable=executable,
        reasons=("net_edge_above_threshold",),
    )


def test_executable_opportunity_is_presented_to_jev_and_risk_checked():
    policy = FakePolicy()
    result = evaluate_with_jev(state(), opportunity(), policy, RiskLimits())
    assert result.approved is True
    assert result.decision.expected_edge_bps == 12
    assert policy.state.arbitrage.direction == "buy_cex_sell_dex"


def test_non_executable_opportunity_never_calls_jev():
    policy = FakePolicy()
    result = evaluate_with_jev(state(), opportunity(False), policy, RiskLimits())
    assert result.approved is False
    assert result.decision is None
    assert policy.state is None
