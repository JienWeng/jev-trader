from __future__ import annotations

import argparse
from pathlib import Path

from .backtest import BacktestPortfolio
from .datasets import read_backtest_ticks_jsonl
from .jev_policy import UnconfiguredJevPolicy
from .models import RiskLimits
from .report import build_report, write_report
from .runner import BacktestRunner
from .typesafe_policy import TypeSafeClient, TypeSafeJevPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jev-trader")
    commands = parser.add_subparsers(dest="command", required=True)
    backtest = commands.add_parser("backtest", help="replay a normalized JSONL dataset")
    backtest.add_argument("dataset", type=Path)
    backtest.add_argument("--report", type=Path, required=True)
    backtest.add_argument("--initial-cash", type=float, default=10_000)
    backtest.add_argument("--policy", choices=("safe", "typesafe"), default="safe")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "backtest":
        return 2
    if args.initial_cash <= 0:
        raise SystemExit("--initial-cash must be positive")

    policy = UnconfiguredJevPolicy()
    if args.policy == "typesafe":
        policy = TypeSafeJevPolicy(TypeSafeClient.from_environment())

    ticks = list(read_backtest_ticks_jsonl(args.dataset))
    portfolio = BacktestPortfolio(initial_cash=args.initial_cash)
    summary = BacktestRunner(policy, RiskLimits(), portfolio).run(ticks)
    write_report(args.report, build_report(summary, portfolio.equity_curve))
    print(
        f"ticks={summary.ticks_processed} trades={summary.trades_approved} "
        f"final_equity={summary.final_equity:.2f} drawdown={summary.max_drawdown:.4f}"
    )
    return 0
