from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .backtest import EquityPoint
from .runner import BacktestSummary


class BacktestReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    summary: BacktestSummary
    equity_curve: tuple[EquityPoint, ...]


def build_report(summary: BacktestSummary, equity_curve: list[EquityPoint]) -> BacktestReport:
    return BacktestReport(summary=summary, equity_curve=tuple(equity_curve))


def write_report(path: str | Path, report: BacktestReport) -> None:
    """Write a stable, human-readable JSON report without secrets."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
