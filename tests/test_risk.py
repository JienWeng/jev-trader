from jev_trader.models import (
    Action,
    JevDecision,
    MarketState,
    OrderBookLevel,
    OrderBookSnapshot,
    Regime,
    RiskLimits,
    Venue,
)
from jev_trader.risk import evaluate_risk


def state(**overrides):
    values = {
        "symbol": "BTCUSDT",
        "timestamp_ms": 1,
        "cex": OrderBookSnapshot(
            venue=Venue.BINANCE,
            symbol="BTCUSDT",
            sequence=1,
            timestamp_ms=1,
            bids=(OrderBookLevel(price=100.0, quantity=1.0),),
            asks=(OrderBookLevel(price=100.01, quantity=1.0),),
        ),
        "z_score": -2.2,
        "volatility_bps": 20,
        "estimated_fee_bps": 4,
        "estimated_slippage_bps": 2,
        "estimated_gas_bps": 0,
        "data_age_ms": 100,
    }
    values.update(overrides)
    return MarketState(**values)


def decision(**overrides):
    values = {
        "action": Action.OPEN_LONG,
        "venue": Venue.BINANCE,
        "regime": Regime.RANGE,
        "action_probability": 0.87,
        "confidence": 0.82,
        "setup_score": 0.8,
        "execution_score": 0.8,
        "risk_score": 0.8,
        "expected_edge_bps": 15,
        "holding_period_seconds": 120,
        "requested_leverage": 1.5,
    }
    values.update(overrides)
    return JevDecision(**values)


def test_profitable_decision_is_approved():
    result = evaluate_risk(state(), decision(), RiskLimits())
    assert result.approved is True
    assert result.allowed_leverage == 1.5


def test_stale_data_vetoes_trade():
    result = evaluate_risk(state(data_age_ms=2_000), decision(), RiskLimits())
    assert result.approved is False
    assert "market_data_stale" in result.reasons


def test_leverage_is_vetoed_not_clamped_into_live_trade():
    result = evaluate_risk(state(), decision(requested_leverage=10), RiskLimits())
    assert result.approved is False
    assert "leverage_limit_exceeded" in result.reasons
    assert result.allowed_leverage == 2


def test_no_trade_is_not_blocked_by_market_conditions():
    result = evaluate_risk(
        state(data_age_ms=99_999),
        decision(action=Action.NO_TRADE, requested_leverage=0),
        RiskLimits(),
    )
    assert result.approved is True
