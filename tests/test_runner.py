from jev_trader.backtest import BacktestPortfolio
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
from jev_trader.runner import BacktestRunner, BacktestTick


class FakePolicy:
    def decide(self, state):
        return JevDecision(
            action=Action.OPEN_LONG,
            venue=Venue.BINANCE,
            regime=Regime.RANGE,
            action_probability=0.9,
            confidence=0.9,
            setup_score=0.9,
            execution_score=0.9,
            risk_score=0.9,
            expected_edge_bps=0,
            holding_period_seconds=30,
            requested_leverage=0,
        )


def book(timestamp=1_000):
    return OrderBookSnapshot(
        venue=Venue.BINANCE,
        symbol="BTCUSDT",
        sequence=1,
        timestamp_ms=timestamp,
        bids=(OrderBookLevel(price=99, quantity=2),),
        asks=(OrderBookLevel(price=100, quantity=2),),
    )


def state():
    return MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1_000,
        estimated_fee_bps=2,
        estimated_slippage_bps=1,
        estimated_gas_bps=0,
        data_age_ms=10,
    )


def tick():
    return BacktestTick(
        timestamp_ms=1_000,
        cex_book=book(),
        dex_book=OrderBookSnapshot(
            venue=Venue.DEX,
            symbol="BTCUSDT",
            sequence=1,
            timestamp_ms=1_000,
            bids=(OrderBookLevel(price=101, quantity=2),),
            asks=(OrderBookLevel(price=102, quantity=2),),
        ),
        market_state=state(),
        dex_fee_bps=5,
        dex_gas_bps=2,
        cex_fee_bps=5,
        quantity=1,
        mark_price=100,
    )


def test_runner_executes_one_best_direction_and_records_pnl():
    portfolio = BacktestPortfolio(initial_cash=1_000)
    summary = BacktestRunner(FakePolicy(), RiskLimits(), portfolio).run([tick()])
    assert summary.ticks_processed == 1
    assert summary.opportunities_seen == 2
    assert summary.trades_approved == 1
    assert summary.final_equity > summary.initial_cash


def test_runner_rejects_unordered_ticks():
    portfolio = BacktestPortfolio(initial_cash=1_000)
    later = tick()
    earlier = tick().model_copy(update={"timestamp_ms": 999})
    try:
        BacktestRunner(FakePolicy(), RiskLimits(), portfolio).run([later, earlier])
    except ValueError as exc:
        assert "ordered" in str(exc)
    else:
        raise AssertionError("expected timestamp ordering error")
