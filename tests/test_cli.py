import json

from jev_trader.cli import main
from jev_trader.models import MarketState, OrderBookLevel, OrderBookSnapshot, Venue
from jev_trader.runner import BacktestTick


def test_safe_cli_runs_and_writes_report(tmp_path, capsys):
    book = OrderBookSnapshot(
        venue=Venue.BINANCE,
        symbol="BTCUSDT",
        sequence=1,
        timestamp_ms=1,
        bids=(OrderBookLevel(price=99, quantity=1),),
        asks=(OrderBookLevel(price=100, quantity=1),),
    )
    tick = BacktestTick(
        timestamp_ms=1,
        cex_book=book,
        dex_book=book.model_copy(update={"venue": Venue.DEX}),
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
    dataset = tmp_path / "ticks.jsonl"
    report = tmp_path / "report.json"
    dataset.write_text(tick.model_dump_json() + "\n", encoding="utf-8")

    assert main(["backtest", str(dataset), "--report", str(report)]) == 0
    assert report.exists()
    assert json.loads(report.read_text())["summary"]["trades_approved"] == 0
    assert "ticks=1" in capsys.readouterr().out
