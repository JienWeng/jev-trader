from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from .paper import Side


class FillEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp_ms: int = Field(gt=0)
    side: Side
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    fee_bps: float = Field(ge=0)


class FundingEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp_ms: int = Field(gt=0)
    mark_price: float = Field(gt=0)
    funding_rate: float


class EquityPoint(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp_ms: int = Field(gt=0)
    equity: float
    position_quantity: float
    mark_price: float = Field(gt=0)


@dataclass
class BacktestPortfolio:
    """Simple isolated linear-perpetual portfolio for deterministic replay."""

    initial_cash: float
    cash: float | None = None
    position_quantity: float = 0.0
    mark_price: float | None = None
    equity_curve: list[EquityPoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if self.cash is None:
            self.cash = self.initial_cash

    def apply_fill(self, fill: FillEvent) -> EquityPoint:
        assert self.cash is not None
        signed_quantity = fill.quantity if fill.side is Side.BUY else -fill.quantity
        notional = fill.quantity * fill.price
        fee = notional * fill.fee_bps / 10_000
        self.cash -= signed_quantity * fill.price + fee
        self.position_quantity += signed_quantity
        self.mark_price = fill.price
        return self._record(fill.timestamp_ms)

    def apply_funding(self, event: FundingEvent) -> EquityPoint:
        assert self.cash is not None
        if self.mark_price is None:
            self.mark_price = event.mark_price
        payment = self.position_quantity * event.mark_price * event.funding_rate
        # Positive funding is paid by longs and received by shorts.
        self.cash -= payment
        self.mark_price = event.mark_price
        return self._record(event.timestamp_ms)

    def mark(self, timestamp_ms: int, mark_price: float) -> EquityPoint:
        if mark_price <= 0:
            raise ValueError("mark_price must be positive")
        self.mark_price = mark_price
        return self._record(timestamp_ms)

    @property
    def equity(self) -> float:
        if self.mark_price is None:
            assert self.cash is not None
            return self.cash
        assert self.cash is not None
        return self.cash + self.position_quantity * self.mark_price

    @property
    def max_drawdown(self) -> float:
        peak = self.initial_cash
        largest = 0.0
        for point in self.equity_curve:
            peak = max(peak, point.equity)
            largest = max(largest, (peak - point.equity) / peak if peak else 0.0)
        return largest

    def _record(self, timestamp_ms: int) -> EquityPoint:
        assert self.mark_price is not None
        point = EquityPoint(
            timestamp_ms=timestamp_ms,
            equity=self.equity,
            position_quantity=self.position_quantity,
            mark_price=self.mark_price,
        )
        self.equity_curve.append(point)
        return point
