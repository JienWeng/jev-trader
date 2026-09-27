import pytest

from jev_trader.binance import BinanceDepthEvent, BinanceOrderBook, OrderBookGapError


def event(**values):
    base = {"E": 1000, "s": "BTCUSDT", "U": 11, "u": 11, "b": [], "a": []}
    base.update(values)
    return BinanceDepthEvent.model_validate(base)


def test_diff_depth_updates_and_deletes_levels():
    book = BinanceOrderBook.from_snapshot(
        symbol="BTCUSDT",
        bids=[("100", "2"), ("99", "1")],
        asks=[("101", "3")],
        last_update_id=10,
    )
    snapshot = book.apply(event(U=11, u=12, b=[["100", "1.5"], ["99", "0"]], a=[["102", "4"]]))
    assert snapshot.sequence == 12
    assert [(level.price, level.quantity) for level in snapshot.bids] == [(100, 1.5)]
    assert [(level.price, level.quantity) for level in snapshot.asks] == [(101, 3), (102, 4)]


def test_gap_requires_resynchronization():
    book = BinanceOrderBook.from_snapshot(
        symbol="BTCUSDT", bids=[("100", "1")], asks=[("101", "1")], last_update_id=10
    )
    with pytest.raises(OrderBookGapError, match="expected update 11"):
        book.apply(event(U=12, u=12))


def test_old_duplicate_events_are_ignored():
    book = BinanceOrderBook.from_snapshot(
        symbol="BTCUSDT", bids=[("100", "1")], asks=[("101", "1")], last_update_id=10
    )
    snapshot = book.apply(event(U=9, u=10, b=[["100", "5"]]))
    assert snapshot.bids[0].quantity == 1
