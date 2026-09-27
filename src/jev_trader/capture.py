from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

from websockets.asyncio.client import connect

from .binance import BinanceDepthEvent, BinanceOrderBook, OrderBookGapError
from .hyperliquid import HyperliquidL2Book
from .models import MarketState, Venue
from .runner import BacktestTick


@dataclass
class CaptureConfig:
    symbol: str = "BTCUSDT"
    hyperliquid_coin: str = "BTC"
    duration_seconds: int = 60
    output: Path = Path("data/capture.jsonl")
    cex_fee_bps: float = 5.0
    dex_fee_bps: float = 3.0
    dex_gas_bps: float = 1.0
    quantity: float = 0.001


@asynccontextmanager
async def _open_text(path: Path):
    with path.open("w", encoding="utf-8") as stream:
        yield stream


async def capture_market(config: CaptureConfig) -> int:
    """Capture synchronized public Binance and Hyperliquid snapshots."""
    if config.duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    config.output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = await asyncio.to_thread(_binance_snapshot, config.symbol)
    book = BinanceOrderBook.from_snapshot(
        symbol=config.symbol,
        bids=snapshot["bids"],
        asks=snapshot["asks"],
        last_update_id=snapshot["lastUpdateId"],
    )
    count = 0
    deadline = time.monotonic() + config.duration_seconds
    async with (
        connect(_binance_url(config.symbol)) as cex_ws,
        connect("wss://api.hyperliquid.xyz/ws") as dex_ws,
        _open_text(config.output) as output,
    ):
        await dex_ws.send(
            json.dumps(
                {
                    "method": "subscribe",
                    "subscription": {"type": "l2Book", "coin": config.hyperliquid_coin},
                }
            )
        )
        cex_task = asyncio.create_task(cex_ws.recv())
        dex_task = asyncio.create_task(dex_ws.recv())
        latest_dex = None
        latest_context = None
        while time.monotonic() < deadline:
            done, _ = await asyncio.wait(
                (cex_task, dex_task),
                timeout=max(0.1, deadline - time.monotonic()),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                break
            for task in done:
                raw = json.loads(task.result())
                if task is cex_task:
                    event = BinanceDepthEvent.model_validate(raw)
                    try:
                        cex_snapshot = book.apply(event)
                    except OrderBookGapError:
                        refreshed = await asyncio.to_thread(_binance_snapshot, config.symbol)
                        book = BinanceOrderBook.from_snapshot(
                            symbol=config.symbol,
                            bids=refreshed["bids"],
                            asks=refreshed["asks"],
                            last_update_id=refreshed["lastUpdateId"],
                        )
                        try:
                            cex_snapshot = book.apply(event)
                        except ValueError:
                            cex_task = asyncio.create_task(cex_ws.recv())
                            continue
                    except ValueError:
                        cex_task = asyncio.create_task(cex_ws.recv())
                        continue
                    cex_task = asyncio.create_task(cex_ws.recv())
                    if latest_dex is not None:
                        count += _write_tick(
                            output, config, cex_snapshot, latest_dex, latest_context
                        )
                else:
                    if raw.get("channel") == "l2Book":
                        latest_dex = HyperliquidL2Book.from_websocket(raw).snapshot(
                            book._last_update_id
                        )
                        latest_dex = latest_dex.model_copy(update={"symbol": config.symbol})
                    if raw.get("channel") == "activeAssetCtx" and raw.get("data"):
                        latest_context = raw["data"]
                    dex_task = asyncio.create_task(dex_ws.recv())
        for task in (cex_task, dex_task):
            task.cancel()
    return count


def _write_tick(output, config, cex, dex, context) -> int:
    mark = float(context["markPx"]) if context and context.get("markPx") else cex.mid_price
    tick = BacktestTick(
        timestamp_ms=max(cex.timestamp_ms, dex.timestamp_ms),
        cex_book=cex,
        dex_book=dex.model_copy(update={"venue": Venue.DEX}),
        market_state=MarketState(
            symbol=config.symbol,
            timestamp_ms=max(cex.timestamp_ms, dex.timestamp_ms),
            dex_price=dex.mid_price,
            funding_rate_bps=float(context["funding"]) * 10_000
            if context and context.get("funding")
            else 0,
            estimated_fee_bps=config.cex_fee_bps,
            estimated_slippage_bps=cex.spread_bps / 2,
            estimated_gas_bps=config.dex_gas_bps,
            data_age_ms=0,
        ),
        dex_fee_bps=config.dex_fee_bps,
        dex_gas_bps=config.dex_gas_bps,
        cex_fee_bps=config.cex_fee_bps,
        quantity=config.quantity,
        mark_price=mark,
    )
    output.write(tick.model_dump_json() + "\n")
    output.flush()
    return 1


def _binance_url(symbol: str) -> str:
    return f"wss://stream.binance.com:9443/ws/{symbol.lower()}@depth@100ms"


def _binance_snapshot(symbol: str) -> dict:
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol.upper()}&limit=1000"
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read())
