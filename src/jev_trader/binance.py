from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderBookLevel, OrderBookSnapshot, Venue


class BinanceDepthEvent(BaseModel):
    """Binance diff-depth event after JSON decoding."""

    model_config = ConfigDict(populate_by_name=True, frozen=True)
    event_time: int = Field(alias="E", gt=0)
    symbol: str = Field(alias="s", min_length=1)
    first_update_id: int = Field(alias="U", ge=0)
    final_update_id: int = Field(alias="u", ge=0)
    bids: tuple[tuple[str, str], ...] = Field(alias="b")
    asks: tuple[tuple[str, str], ...] = Field(alias="a")


class OrderBookGapError(ValueError):
    """The event stream cannot be safely applied without a fresh snapshot."""


class BinanceOrderBook:
    """Apply Binance diff-depth events to a previously synchronized snapshot."""

    def __init__(
        self,
        *,
        symbol: str,
        bids: dict[float, float],
        asks: dict[float, float],
        last_update_id: int,
    ) -> None:
        self.symbol = symbol.upper()
        self._bids = bids
        self._asks = asks
        self._last_update_id = last_update_id

    @classmethod
    def from_snapshot(
        cls,
        *,
        symbol: str,
        bids: list[tuple[str, str]],
        asks: list[tuple[str, str]],
        last_update_id: int,
    ) -> BinanceOrderBook:
        return cls(
            symbol=symbol,
            bids=_levels_to_map(bids),
            asks=_levels_to_map(asks),
            last_update_id=last_update_id,
        )

    def apply(self, event: BinanceDepthEvent) -> OrderBookSnapshot:
        if event.symbol.upper() != self.symbol:
            raise ValueError(f"event symbol {event.symbol} does not match {self.symbol}")
        if event.final_update_id <= self._last_update_id:
            return self.snapshot(event.event_time)
        if event.first_update_id > self._last_update_id + 1:
            raise OrderBookGapError(
                f"expected update {self._last_update_id + 1}, received {event.first_update_id}"
            )

        _apply_levels(self._bids, event.bids)
        _apply_levels(self._asks, event.asks)
        self._last_update_id = event.final_update_id
        return self.snapshot(event.event_time)

    def snapshot(self, timestamp_ms: int) -> OrderBookSnapshot:
        bids = tuple(
            OrderBookLevel(price=price, quantity=quantity)
            for price, quantity in sorted(self._bids.items(), reverse=True)
            if quantity > 0
        )
        asks = tuple(
            OrderBookLevel(price=price, quantity=quantity)
            for price, quantity in sorted(self._asks.items())
            if quantity > 0
        )
        if not bids or not asks:
            raise OrderBookGapError("order book has no executable bid or ask")
        return OrderBookSnapshot(
            venue=Venue.BINANCE,
            symbol=self.symbol,
            sequence=self._last_update_id,
            timestamp_ms=timestamp_ms,
            bids=bids,
            asks=asks,
        )


def _levels_to_map(levels: list[tuple[str, str]]) -> dict[float, float]:
    result: dict[float, float] = {}
    _apply_levels(result, levels)
    return result


def _apply_levels(
    book: dict[float, float], levels: tuple[tuple[str, str], ...] | list[tuple[str, str]]
) -> None:
    for raw_price, raw_quantity in levels:
        price = float(raw_price)
        quantity = float(raw_quantity)
        if price <= 0 or quantity < 0:
            raise ValueError("Binance levels must have positive price and non-negative quantity")
        if quantity == 0:
            book.pop(price, None)
        else:
            book[price] = quantity
