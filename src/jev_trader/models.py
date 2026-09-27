from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Venue(StrEnum):
    BINANCE = "binance"
    DEX = "dex"


class Regime(StrEnum):
    RANGE = "range"
    TREND = "trend"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class Action(StrEnum):
    NO_TRADE = "no_trade"
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    REDUCE = "reduce"
    CLOSE = "close"


class OrderBookLevel(BaseModel):
    model_config = ConfigDict(frozen=True)
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)


class OrderBookSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    venue: Venue
    symbol: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    timestamp_ms: int = Field(gt=0)
    bids: tuple[OrderBookLevel, ...] = Field(min_length=1)
    asks: tuple[OrderBookLevel, ...] = Field(min_length=1)

    @property
    def best_bid(self) -> float:
        return max(level.price for level in self.bids)

    @property
    def best_ask(self) -> float:
        return min(level.price for level in self.asks)

    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread_bps(self) -> float:
        return (self.best_ask - self.best_bid) / self.mid_price * 10_000


class MarketState(BaseModel):
    """Compact, serializable state presented to a Jev workflow."""

    model_config = ConfigDict(frozen=True)
    symbol: str = Field(min_length=1)
    timestamp_ms: int = Field(gt=0)
    cex: OrderBookSnapshot | None = None
    dex_price: float | None = Field(default=None, gt=0)
    z_score: float | None = None
    volatility_bps: float | None = Field(default=None, ge=0)
    funding_rate_bps: float | None = None
    estimated_fee_bps: float = Field(ge=0)
    estimated_slippage_bps: float = Field(ge=0)
    estimated_gas_bps: float = Field(ge=0)
    data_age_ms: int = Field(ge=0)


class JevDecision(BaseModel):
    """Typed output expected from Jev; never an order request."""

    model_config = ConfigDict(frozen=True)
    action: Action
    venue: Venue | None = None
    regime: Regime
    action_probability: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    setup_score: float = Field(ge=0, le=1)
    execution_score: float = Field(ge=0, le=1)
    risk_score: float = Field(ge=0, le=1)
    expected_edge_bps: float
    holding_period_seconds: int = Field(ge=0)
    requested_leverage: float = Field(ge=0)
    reason_codes: tuple[str, ...] = ()


class RiskLimits(BaseModel):
    """Hard local limits that can veto any model decision."""

    model_config = ConfigDict(frozen=True)
    max_data_age_ms: int = Field(default=1_000, gt=0)
    min_expected_edge_bps: float = Field(default=8, ge=0)
    max_leverage: float = Field(default=2, ge=0)
    min_confidence: float = Field(default=0.65, ge=0, le=1)
    min_risk_score: float = Field(default=0.60, ge=0, le=1)
    max_spread_bps: float = Field(default=30, ge=0)


class RiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    approved: bool
    reasons: tuple[str, ...] = ()
    allowed_leverage: float = Field(ge=0)
