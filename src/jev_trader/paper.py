from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderBookSnapshot


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class PaperFill(BaseModel):
    model_config = ConfigDict(frozen=True)
    side: Side
    requested_quantity: float = Field(gt=0)
    filled_quantity: float = Field(ge=0)
    average_price: float | None = Field(default=None, gt=0)
    notional: float = Field(ge=0)
    fully_filled: bool
    levels_consumed: int = Field(ge=0)


def simulate_market_order(
    snapshot: OrderBookSnapshot,
    *,
    side: Side,
    quantity: float,
) -> PaperFill:
    """Consume visible L2 liquidity; this never submits a real order."""
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    levels = snapshot.asks if side is Side.BUY else snapshot.bids
    remaining = quantity
    notional = 0.0
    filled = 0.0
    consumed = 0

    for level in levels:
        amount = min(remaining, level.quantity)
        filled += amount
        notional += amount * level.price
        remaining -= amount
        consumed += 1
        if remaining <= 0:
            break

    return PaperFill(
        side=side,
        requested_quantity=quantity,
        filled_quantity=filled,
        average_price=notional / filled if filled else None,
        notional=notional,
        fully_filled=remaining <= 0,
        levels_consumed=consumed,
    )
