from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderBookLevel, OrderBookSnapshot, Venue


class HyperliquidL2Book(BaseModel):
    """Normalized Hyperliquid L2 book message."""

    model_config = ConfigDict(frozen=True)
    coin: str = Field(min_length=1)
    time: int = Field(gt=0)
    levels: tuple[tuple[tuple[str, str], ...], ...]

    @classmethod
    def from_websocket(cls, payload: dict) -> HyperliquidL2Book:
        data = payload.get("data", payload)
        raw_levels = data.get("levels", [])
        if len(raw_levels) != 2:
            raise ValueError("Hyperliquid l2Book must contain bid and ask levels")
        return cls(
            coin=data["coin"],
            time=data["time"],
            levels=tuple(
                tuple((str(level["px"]), str(level["sz"])) for level in side) for side in raw_levels
            ),
        )

    def snapshot(self, sequence: int) -> OrderBookSnapshot:
        bids, asks = self.levels
        return OrderBookSnapshot(
            venue=Venue.DEX,
            symbol=self.coin,
            sequence=sequence,
            timestamp_ms=self.time,
            bids=tuple(OrderBookLevel(price=float(px), quantity=float(sz)) for px, sz in bids),
            asks=tuple(OrderBookLevel(price=float(px), quantity=float(sz)) for px, sz in asks),
        )


class HyperliquidMarketContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    coin: str = Field(min_length=1)
    time: int = Field(gt=0)
    mark_price: float = Field(gt=0)
    oracle_price: float = Field(gt=0)
    funding_rate: float
    open_interest: float = Field(ge=0)

    @classmethod
    def from_asset_context(cls, coin: str, payload: dict, time: int) -> HyperliquidMarketContext:
        return cls(
            coin=coin,
            time=time,
            mark_price=float(payload["markPx"]),
            oracle_price=float(payload["oraclePx"]),
            funding_rate=float(payload["funding"]),
            open_interest=float(payload["openInterest"]),
        )
