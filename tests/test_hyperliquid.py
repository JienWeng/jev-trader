from pytest import approx, raises

from jev_trader.hyperliquid import HyperliquidL2Book, HyperliquidMarketContext


def test_parses_l2_book_into_normalized_snapshot():
    message = {
        "channel": "l2Book",
        "data": {
            "coin": "BTC",
            "time": 1000,
            "levels": [
                [{"px": "100", "sz": "2"}],
                [{"px": "101", "sz": "3"}],
            ],
        },
    }
    snapshot = HyperliquidL2Book.from_websocket(message).snapshot(sequence=7)
    assert snapshot.venue == "dex"
    assert snapshot.best_bid == 100
    assert snapshot.best_ask == 101
    assert snapshot.sequence == 7


def test_parses_perpetual_market_context():
    context = HyperliquidMarketContext.from_asset_context(
        "BTC",
        {"markPx": "100", "oraclePx": "99.5", "funding": "0.0001", "openInterest": "12"},
        1000,
    )
    assert context.mark_price == 100
    assert context.funding_rate == approx(0.0001)
    assert context.open_interest == 12


def test_rejects_invalid_book_shape():
    with raises(ValueError, match="bid and ask"):
        HyperliquidL2Book.from_websocket({"data": {"coin": "BTC", "time": 1, "levels": [[]]}})
