# jev-trader

A paper-trading research system for mean-reversion and CEX–DEX statistical arbitrage, with Jev used as a typed strategy-policy decision layer.

## Safety boundary

Jev proposes a typed strategy decision using Choice, Score, Noul, and confidence outputs. It does not create or submit orders. A deterministic local risk gate can veto every non-`NO_TRADE` decision for stale data, insufficient edge, low confidence, excessive spread, weak risk score, or excessive leverage.

The initial project is paper-trading only. Live credentials and live order submission are intentionally not implemented.

## Initial architecture

- **Market state:** normalized Binance level-2 snapshots and DEX pool state.
- **Policy:** TypeSafe Jev adapter, returning validated `JevDecision` values.
- **Risk:** deterministic hard limits in `jev_trader.risk`.
- **Execution:** planned Hummingbot integration for Binance and DEX connectivity.
- **Research:** planned replay/backtest harness for order-book data.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
```

## Planned milestones

1. Market-state schemas and deterministic risk gates.
2. Binance L2 capture and replay.
3. Hummingbot paper adapters for Binance and one DEX.
4. TypeSafe Jev workflow adapter and confidence calibration.
5. Cost-inclusive mean-reversion backtesting.
6. Paper execution and operational kill switches.

No leverage increase or live trading is planned until replay and paper results demonstrate stable, cost-inclusive behavior.
