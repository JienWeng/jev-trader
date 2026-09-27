import json

from jev_trader.backtest import BacktestPortfolio
from jev_trader.datasets import read_backtest_ticks_jsonl
from jev_trader.models import MarketState, OrderBookLevel, OrderBookSnapshot, Venue
from jev_trader.report import build_report, write_report
from jev_trader.runner import BacktestSummary, BacktestTick


def make_tick():
    book = OrderBookSnapshot(
        venue=Venue.BINANCE,
        symbol="BTCUSDT",
        sequence=1,
        timestamp_ms=1,
        bids=(OrderBookLevel(price=99, quantity=1),),
        asks=(OrderBookLevel(price=100, quantity=1),),
    )
    dex = book.model_copy(update={"venue": Venue.DEX})
    return BacktestTick(
        timestamp_ms=1,
        cex_book=book,
        dex_book=dex,
        market_state=MarketState(
            symbol="BTCUSDT",
            timestamp_ms=1,
            estimated_fee_bps=1,
            estimated_slippage_bps=1,
            estimated_gas_bps=0,
            data_age_ms=1,
        ),
        dex_fee_bps=1,
        dex_gas_bps=1,
        cex_fee_bps=1,
        quantity=1,
    )


def test_dataset_reader_streams_normalized_ticks(tmp_path):
    path = tmp_path / "ticks.jsonl"
    path.write_text(make_tick().model_dump_json() + "\n", encoding="utf-8")
    loaded = list(read_backtest_ticks_jsonl(path))
    assert len(loaded) == 1
    assert loaded[0].market_state.symbol == "BTCUSDT"


def test_report_persists_summary_and_equity_curve(tmp_path):
    summary = BacktestSummary(
        initial_cash=1000,
        final_equity=1010,
        return_fraction=0.01,
        max_drawdown=0.02,
        ticks_processed=1,
        opportunities_seen=2,
        trades_approved=1,
    )
    portfolio = BacktestPortfolio(initial_cash=1000)
    portfolio.mark(1, 100)
    path = tmp_path / "reports" / "run.json"
    write_report(path, build_report(summary, portfolio.equity_curve))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["trades_approved"] == 1
    assert len(payload["equity_curve"]) == 1
