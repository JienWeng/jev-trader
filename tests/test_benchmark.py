from jev_trader.baseline import RuleBasedPolicy
from jev_trader.benchmark import compare_policies
from jev_trader.models import MarketState, OrderBookLevel, OrderBookSnapshot, RiskLimits, Venue
from jev_trader.runner import BacktestTick


def make_tick():
    cex = OrderBookSnapshot(
        venue=Venue.BINANCE,
        symbol="BTCUSDT",
        sequence=1,
        timestamp_ms=1,
        bids=(OrderBookLevel(price=99, quantity=2),),
        asks=(OrderBookLevel(price=100, quantity=2),),
    )
    dex = OrderBookSnapshot(
        venue=Venue.DEX,
        symbol="BTCUSDT",
        sequence=1,
        timestamp_ms=1,
        bids=(OrderBookLevel(price=102, quantity=2),),
        asks=(OrderBookLevel(price=103, quantity=2),),
    )
    return BacktestTick(
        timestamp_ms=1,
        cex_book=cex,
        dex_book=dex,
        market_state=MarketState(
            symbol="BTCUSDT",
            timestamp_ms=1,
            z_score=-2.5,
            estimated_fee_bps=1,
            estimated_slippage_bps=1,
            estimated_gas_bps=0,
            data_age_ms=1,
        ),
        dex_fee_bps=2,
        dex_gas_bps=1,
        cex_fee_bps=2,
        quantity=1,
        mark_price=100,
    )


def test_policies_are_compared_on_same_replay():
    results = compare_policies(
        [make_tick()],
        {"baseline": lambda: RuleBasedPolicy(min_edge_bps=1)},
        limits=RiskLimits(min_expected_edge_bps=1),
    )
    assert results["baseline"].ticks_processed == 1
    assert results["baseline"].trades_approved == 1
