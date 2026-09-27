from jev_trader.models import MarketState, OrderBookLevel, OrderBookSnapshot, Venue
from jev_trader.signal import build_mean_reversion_candidate, estimate_costs


def make_state(**overrides):
    values = {
        "symbol": "BTCUSDT",
        "timestamp_ms": 1,
        "cex": OrderBookSnapshot(
            venue=Venue.BINANCE,
            symbol="BTCUSDT",
            sequence=1,
            timestamp_ms=1,
            bids=(OrderBookLevel(price=100, quantity=1),),
            asks=(OrderBookLevel(price=101, quantity=1),),
        ),
        "z_score": -2.5,
        "estimated_fee_bps": 4,
        "estimated_slippage_bps": 2,
        "estimated_gas_bps": 1,
        "funding_rate_bps": 1,
        "data_age_ms": 10,
    }
    values.update(overrides)
    return MarketState(**values)


def test_costs_include_all_explicit_cost_components():
    costs = estimate_costs(make_state(), gross_edge_bps=20)
    assert costs.net_edge_bps == 12


def test_negative_z_score_produces_long_candidate():
    candidate = build_mean_reversion_candidate(make_state())
    assert candidate.action == "open_long"
    assert candidate.venue == Venue.BINANCE
    assert candidate.net_edge_bps > 0


def test_positive_z_score_produces_short_candidate():
    candidate = build_mean_reversion_candidate(make_state(z_score=2.5))
    assert candidate.action == "open_short"


def test_costs_can_turn_a_signal_into_no_trade():
    candidate = build_mean_reversion_candidate(
        make_state(estimated_fee_bps=20, estimated_slippage_bps=20), gross_edge_bps=20
    )
    assert candidate.action == "no_trade"
    assert "edge_does_not_cover_costs" in candidate.reason_codes
