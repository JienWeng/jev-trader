from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from .runner import BacktestTick


def read_backtest_ticks_jsonl(path: str | Path) -> Iterator[BacktestTick]:
    """Stream normalized replay ticks from newline-delimited JSON."""
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                yield BacktestTick.model_validate_json(line)
            except (ValueError, ValidationError) as exc:
                raise ValueError(f"invalid backtest tick at line {line_number}") from exc
