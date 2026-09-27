import pytest

from jev_trader.models import OrderBookLevel, OrderBookSnapshot, Venue
from jev_trader.orderbook import calculate_features
from jev_trader.replay import MarketEvent, replay


def book(bids=((100.0, 2.0),), asks=((100.1, 1.0),)):
    return OrderBookSnapshot(
        venue=Venue.BINANCE,
        symbol="BTCUSDT",
        sequence=1,
        timestamp_ms=1,
        bids=tuple(OrderBookLevel(price=p, quantity=q) for p, q in bids),
        asks=tuple(OrderBookLevel(price=p, quantity=q) for p, q in asks),
    )


def test_features_capture_top_of_book_pressure():
    features = calculate_features(book())
    assert features.mid_price == pytest.approx(100.05)
    assert features.spread_bps == pytest.approx(9.995)
    assert features.imbalance_1 == pytest.approx(1 / 3)
    assert features.microprice == pytest.approx((100.1 * 2 + 100.0 * 1) / 3)


def test_replay_rejects_time_travel():
    events = [
        MarketEvent(event_id=1, timestamp_ms=2, order_book=book()),
        MarketEvent(event_id=2, timestamp_ms=1, order_book=book()),
    ]
    with pytest.raises(ValueError, match="non-decreasing"):
        list(replay(events))
