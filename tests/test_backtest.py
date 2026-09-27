from pytest import approx

from jev_trader.backtest import BacktestPortfolio, FillEvent, FundingEvent
from jev_trader.paper import Side


def test_perpetual_portfolio_tracks_fills_and_funding():
    portfolio = BacktestPortfolio(initial_cash=1_000)
    portfolio.apply_fill(
        FillEvent(timestamp_ms=1, side=Side.BUY, quantity=1, price=100, fee_bps=10)
    )
    assert portfolio.cash == approx(899.9)
    portfolio.mark(timestamp_ms=2, mark_price=110)
    assert portfolio.equity == approx(1009.9)
    portfolio.apply_funding(FundingEvent(timestamp_ms=3, mark_price=110, funding_rate=0.001))
    assert portfolio.equity == approx(1009.79)


def test_short_receives_positive_funding_and_drawdown_is_recorded():
    portfolio = BacktestPortfolio(initial_cash=1_000)
    portfolio.apply_fill(
        FillEvent(timestamp_ms=1, side=Side.SELL, quantity=1, price=100, fee_bps=0)
    )
    portfolio.mark(timestamp_ms=2, mark_price=110)
    assert portfolio.equity == approx(990)
    portfolio.apply_funding(FundingEvent(timestamp_ms=3, mark_price=110, funding_rate=0.001))
    assert portfolio.equity == approx(990.11)
    assert portfolio.max_drawdown == approx(0.01)
