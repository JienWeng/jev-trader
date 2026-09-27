from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderBookSnapshot


class OrderBookFeatures(BaseModel):
    """Deterministic features derived from one L2 snapshot."""

    model_config = ConfigDict(frozen=True)
    mid_price: float = Field(gt=0)
    spread_bps: float = Field(ge=0)
    microprice: float = Field(gt=0)
    imbalance_1: float = Field(ge=-1, le=1)
    imbalance_5: float = Field(ge=-1, le=1)
    bid_depth_5: float = Field(ge=0)
    ask_depth_5: float = Field(ge=0)


def _depth(snapshot: OrderBookSnapshot, *, side: str, levels: int = 5) -> float:
    book = snapshot.bids if side == "bid" else snapshot.asks
    return sum(level.quantity for level in book[:levels])


def _imbalance(bid_depth: float, ask_depth: float) -> float:
    total = bid_depth + ask_depth
    return 0.0 if total == 0 else (bid_depth - ask_depth) / total


def calculate_features(snapshot: OrderBookSnapshot) -> OrderBookFeatures:
    """Calculate bounded L2 features without making a trading decision."""
    bid_1 = _depth(snapshot, side="bid", levels=1)
    ask_1 = _depth(snapshot, side="ask", levels=1)
    bid_5 = _depth(snapshot, side="bid", levels=5)
    ask_5 = _depth(snapshot, side="ask", levels=5)
    best_bid = snapshot.best_bid
    best_ask = snapshot.best_ask
    top_total = bid_1 + ask_1

    return OrderBookFeatures(
        mid_price=snapshot.mid_price,
        spread_bps=snapshot.spread_bps,
        microprice=(best_ask * bid_1 + best_bid * ask_1) / top_total,
        imbalance_1=_imbalance(bid_1, ask_1),
        imbalance_5=_imbalance(bid_5, ask_5),
        bid_depth_5=bid_5,
        ask_depth_5=ask_5,
    )
