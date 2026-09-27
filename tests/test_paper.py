from pytest import approx, raises

from jev_trader.models import OrderBookLevel, OrderBookSnapshot, Venue
from jev_trader.paper import Side, simulate_market_order


def snapshot():
    return OrderBookSnapshot(
        venue=Venue.BINANCE,
        symbol="BTCUSDT",
        sequence=1,
        timestamp_ms=1,
        bids=(
            OrderBookLevel(price=100, quantity=1),
            OrderBookLevel(price=99, quantity=2),
        ),
        asks=(
            OrderBookLevel(price=101, quantity=1),
            OrderBookLevel(price=102, quantity=2),
        ),
    )


def test_buy_consumes_ask_levels_and_calculates_vwap():
    fill = simulate_market_order(snapshot(), side=Side.BUY, quantity=2)
    assert fill.fully_filled is True
    assert fill.filled_quantity == 2
    assert fill.average_price == approx(101.5)
    assert fill.levels_consumed == 2


def test_sell_can_be_partially_filled_when_depth_is_insufficient():
    fill = simulate_market_order(snapshot(), side=Side.SELL, quantity=5)
    assert fill.fully_filled is False
    assert fill.filled_quantity == 3
    assert fill.notional == 298


def test_quantity_must_be_positive():
    with raises(ValueError, match="positive"):
        simulate_market_order(snapshot(), side=Side.BUY, quantity=0)
