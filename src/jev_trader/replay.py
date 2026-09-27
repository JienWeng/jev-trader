from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderBookSnapshot


class MarketEvent(BaseModel):
    """A replayable event envelope; payload is currently an L2 snapshot."""

    model_config = ConfigDict(frozen=True)
    event_id: int = Field(ge=0)
    timestamp_ms: int = Field(gt=0)
    order_book: OrderBookSnapshot


def replay(events: Iterable[MarketEvent]) -> Iterator[MarketEvent]:
    """Yield events in source order while rejecting time travel."""
    previous_timestamp = 0
    for event in events:
        if event.timestamp_ms < previous_timestamp:
            raise ValueError("market event timestamps must be non-decreasing")
        previous_timestamp = event.timestamp_ms
        yield event


def read_jsonl(path: str | Path) -> Iterator[MarketEvent]:
    """Read newline-delimited MarketEvent JSON without loading the full file."""
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                yield MarketEvent.model_validate(json.loads(line))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"invalid market event at line {line_number}") from exc
