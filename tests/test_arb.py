from jev_trader.arb import ArbDirection, DexQuote, evaluate_cex_dex
from jev_trader.models import OrderBookLevel, OrderBookSnapshot, Venue


def cex():
    return OrderBookSnapshot(
        venue=Venue.BINANCE,
        symbol="BTCUSDT",
        sequence=1,
        timestamp_ms=1_000,
        bids=(OrderBookLevel(price=99, quantity=2),),
        asks=(OrderBookLevel(price=100, quantity=2),),
    )


def dex(**overrides):
    values = {
        "symbol": "BTCUSDT",
        "timestamp_ms": 1_000,
        "bid_price": 101,
        "ask_price": 102,
        "max_quantity": 2,
        "fee_bps": 10,
        "gas_bps": 5,
    }
    values.update(overrides)
    return DexQuote(**values)


def test_uses_executable_prices_and_finds_both_directions():
    opportunities = evaluate_cex_dex(cex(), dex(), quantity=1, cex_fee_bps=5, min_net_edge_bps=8)
    assert len(opportunities) == 2
    buy_cex = opportunities[0]
    assert buy_cex.direction == ArbDirection.BUY_CEX_SELL_DEX
    assert buy_cex.executable is True
    assert buy_cex.net_edge_bps > 8


def test_order_book_slippage_can_remove_the_edge():
    opportunities = evaluate_cex_dex(
        cex(),
        dex(bid_price=100.01, ask_price=100.02),
        quantity=1,
        cex_fee_bps=5,
        min_net_edge_bps=8,
    )
    assert all(not opportunity.executable for opportunity in opportunities)


def test_stale_venues_are_rejected():
    opportunities = evaluate_cex_dex(cex(), dex(timestamp_ms=5_000), quantity=1, cex_fee_bps=5)
    assert len(opportunities) == 1
    assert opportunities[0].reasons == ("market_data_time_skew",)


def test_insufficient_cex_depth_is_rejected():
    opportunities = evaluate_cex_dex(cex(), dex(max_quantity=5), quantity=3, cex_fee_bps=5)
    assert opportunities[0].executable is False
    assert opportunities[0].reasons == ("insufficient_cex_depth",)
