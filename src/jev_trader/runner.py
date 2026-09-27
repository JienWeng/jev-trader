from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from .arb import ArbDirection, DexQuote, evaluate_cex_dex
from .backtest import BacktestPortfolio, FillEvent, FundingEvent
from .jev_policy import JevPolicy
from .models import MarketState, OrderBookSnapshot, RiskLimits
from .pipeline import evaluate_with_jev


class BacktestTick(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp_ms: int = Field(gt=0)
    cex_book: OrderBookSnapshot
    dex_book: OrderBookSnapshot
    market_state: MarketState
    dex_fee_bps: float = Field(ge=0)
    dex_gas_bps: float = Field(ge=0)
    cex_fee_bps: float = Field(ge=0)
    quantity: float = Field(gt=0)
    funding_rate: float | None = None
    mark_price: float | None = Field(default=None, gt=0)


class BacktestSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    initial_cash: float
    final_equity: float
    return_fraction: float
    max_drawdown: float
    ticks_processed: int
    opportunities_seen: int
    trades_approved: int


@dataclass
class BacktestRunner:
    policy: JevPolicy
    limits: RiskLimits
    portfolio: BacktestPortfolio

    def run(self, ticks: list[BacktestTick]) -> BacktestSummary:
        previous_time = 0
        opportunities_seen = 0
        trades_approved = 0

        for tick in ticks:
            if tick.timestamp_ms < previous_time:
                raise ValueError("backtest ticks must be ordered by timestamp")
            previous_time = tick.timestamp_ms
            cex = tick.cex_book
            dex = tick.dex_book
            quote = DexQuote(
                symbol=cex.symbol,
                timestamp_ms=dex.timestamp_ms,
                bid_price=dex.best_bid,
                ask_price=dex.best_ask,
                max_quantity=min(
                    sum(level.quantity for level in dex.bids),
                    sum(level.quantity for level in dex.asks),
                ),
                fee_bps=tick.dex_fee_bps,
                gas_bps=tick.dex_gas_bps,
            )
            opportunities = evaluate_cex_dex(
                cex,
                quote,
                quantity=tick.quantity,
                cex_fee_bps=tick.cex_fee_bps,
            )
            opportunities_seen += len(opportunities)
            executable = sorted(
                (item for item in opportunities if item.executable),
                key=lambda item: item.net_edge_bps,
                reverse=True,
            )
            # The two directions are mutually exclusive; Jev evaluates only the
            # strongest executable candidate for this market tick.
            for opportunity in executable[:1]:
                evaluation = evaluate_with_jev(
                    tick.market_state, opportunity, self.policy, self.limits
                )
                if evaluation.approved and evaluation.decision is not None:
                    self._apply_arb_fill(tick, opportunity)
                    trades_approved += 1

            if tick.funding_rate is not None and tick.mark_price is not None:
                self.portfolio.apply_funding(
                    FundingEvent(
                        timestamp_ms=tick.timestamp_ms,
                        mark_price=tick.mark_price,
                        funding_rate=tick.funding_rate,
                    )
                )
            elif tick.mark_price is not None:
                self.portfolio.mark(tick.timestamp_ms, tick.mark_price)

        final_equity = self.portfolio.equity
        return BacktestSummary(
            initial_cash=self.portfolio.initial_cash,
            final_equity=final_equity,
            return_fraction=(final_equity / self.portfolio.initial_cash) - 1,
            max_drawdown=self.portfolio.max_drawdown,
            ticks_processed=len(ticks),
            opportunities_seen=opportunities_seen,
            trades_approved=trades_approved,
        )

    def _apply_arb_fill(self, tick: BacktestTick, opportunity) -> None:
        from .paper import Side

        if opportunity.direction is ArbDirection.BUY_CEX_SELL_DEX:
            first_side, first_price = Side.BUY, opportunity.buy_price
            second_side, second_price = Side.SELL, opportunity.sell_price
        else:
            first_side, first_price = Side.BUY, opportunity.buy_price
            second_side, second_price = Side.SELL, opportunity.sell_price
        self.portfolio.apply_fill(
            FillEvent(
                timestamp_ms=tick.timestamp_ms,
                side=first_side,
                quantity=opportunity.quantity,
                price=first_price,
                fee_bps=tick.cex_fee_bps
                if opportunity.direction is ArbDirection.BUY_DEX_SELL_CEX
                else tick.dex_fee_bps + tick.dex_gas_bps,
            )
        )
        self.portfolio.apply_fill(
            FillEvent(
                timestamp_ms=tick.timestamp_ms,
                side=second_side,
                quantity=opportunity.quantity,
                price=second_price,
                fee_bps=tick.cex_fee_bps
                if opportunity.direction is ArbDirection.BUY_CEX_SELL_DEX
                else tick.dex_fee_bps + tick.dex_gas_bps,
            )
        )
