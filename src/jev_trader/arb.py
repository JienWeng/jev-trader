from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderBookSnapshot, Venue
from .paper import Side, simulate_market_order


class ArbDirection(StrEnum):
    BUY_CEX_SELL_DEX = "buy_cex_sell_dex"
    BUY_DEX_SELL_CEX = "buy_dex_sell_cex"


class DexQuote(BaseModel):
    model_config = ConfigDict(frozen=True)
    venue: Venue = Venue.DEX
    symbol: str = Field(min_length=1)
    timestamp_ms: int = Field(gt=0)
    bid_price: float = Field(gt=0)
    ask_price: float = Field(gt=0)
    max_quantity: float = Field(gt=0)
    fee_bps: float = Field(ge=0)
    gas_bps: float = Field(ge=0)


class CexDexOpportunity(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    direction: ArbDirection
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    sell_price: float = Field(gt=0)
    gross_edge_bps: float
    total_cost_bps: float = Field(ge=0)
    net_edge_bps: float
    executable: bool
    reasons: tuple[str, ...] = ()


def evaluate_cex_dex(
    cex: OrderBookSnapshot,
    dex: DexQuote,
    *,
    quantity: float,
    cex_fee_bps: float,
    min_net_edge_bps: float = 8.0,
    max_timestamp_skew_ms: int = 1_000,
) -> tuple[CexDexOpportunity, ...]:
    """Evaluate both directions using paper fills and executable DEX quotes."""
    if cex.symbol != dex.symbol:
        raise ValueError("CEX and DEX symbols must match")
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    opportunities: list[CexDexOpportunity] = []
    skew = abs(cex.timestamp_ms - dex.timestamp_ms)
    if skew > max_timestamp_skew_ms:
        return (_unexecutable(cex.symbol, quantity, "market_data_time_skew"),)

    if quantity > dex.max_quantity:
        return (_unexecutable(cex.symbol, quantity, "insufficient_dex_liquidity"),)

    cex_buy = simulate_market_order(cex, side=Side.BUY, quantity=quantity)
    cex_sell = simulate_market_order(cex, side=Side.SELL, quantity=quantity)
    if cex_buy.fully_filled and cex_sell.fully_filled:
        opportunities.extend(
            [
                _opportunity(
                    symbol=cex.symbol,
                    direction=ArbDirection.BUY_CEX_SELL_DEX,
                    quantity=quantity,
                    buy_price=cex_buy.average_price,
                    sell_price=dex.bid_price,
                    total_cost_bps=cex_fee_bps + dex.fee_bps + dex.gas_bps,
                    min_net_edge_bps=min_net_edge_bps,
                ),
                _opportunity(
                    symbol=cex.symbol,
                    direction=ArbDirection.BUY_DEX_SELL_CEX,
                    quantity=quantity,
                    buy_price=dex.ask_price,
                    sell_price=cex_sell.average_price,
                    total_cost_bps=cex_fee_bps + dex.fee_bps + dex.gas_bps,
                    min_net_edge_bps=min_net_edge_bps,
                ),
            ]
        )
    else:
        opportunities.append(_unexecutable(cex.symbol, quantity, "insufficient_cex_depth"))

    return tuple(opportunities)


def _opportunity(
    *,
    symbol: str,
    direction: ArbDirection,
    quantity: float,
    buy_price: float | None,
    sell_price: float,
    total_cost_bps: float,
    min_net_edge_bps: float,
) -> CexDexOpportunity:
    if buy_price is None:
        return _unexecutable(symbol, quantity, "missing_buy_price")
    gross = (sell_price - buy_price) / buy_price * 10_000
    net = gross - total_cost_bps
    reasons = (
        ("net_edge_above_threshold",) if net >= min_net_edge_bps else ("edge_below_threshold",)
    )
    return CexDexOpportunity(
        symbol=symbol,
        direction=direction,
        quantity=quantity,
        buy_price=buy_price,
        sell_price=sell_price,
        gross_edge_bps=gross,
        total_cost_bps=total_cost_bps,
        net_edge_bps=net,
        executable=net >= min_net_edge_bps,
        reasons=reasons,
    )


def _unexecutable(symbol: str, quantity: float, reason: str) -> CexDexOpportunity:
    return CexDexOpportunity(
        symbol=symbol,
        direction=ArbDirection.BUY_CEX_SELL_DEX,
        quantity=quantity,
        buy_price=1,
        sell_price=1,
        gross_edge_bps=0,
        total_cost_bps=0,
        net_edge_bps=0,
        executable=False,
        reasons=(reason,),
    )
