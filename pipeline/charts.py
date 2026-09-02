"""Compact ASCII candlestick graphs for live / 1m / 3m / 5m bars."""

from __future__ import annotations

from typing import Any

from pipeline.bars import normalize_bars


def ascii_chart(
    bars: list[dict[str, Any]] | None,
    *,
    title: str,
    last_n: int = 48,
    height: int = 10,
) -> str:
    rows = normalize_bars(bars)[-last_n:]
    if not rows:
        return f"{title}: no bars"
    hi = max(b["high"] for b in rows)
    lo = min(b["low"] for b in rows)
    span = hi - lo or 1.0
    grid = [[" " for _ in rows] for _ in range(height)]

    def y_of(price: float) -> int:
        return max(0, min(height - 1, int(round((price - lo) / span * (height - 1)))))

    for i, bar in enumerate(rows):
        y_high = y_of(bar["high"])
        y_low = y_of(bar["low"])
        y_open = y_of(bar["open"])
        y_close = y_of(bar["close"])
        for y in range(min(y_low, y_high), max(y_low, y_high) + 1):
            grid[height - 1 - y][i] = "│"
        body_lo, body_hi = min(y_open, y_close), max(y_open, y_close)
        fill = "█" if bar["close"] >= bar["open"] else "░"
        for y in range(body_lo, body_hi + 1):
            grid[height - 1 - y][i] = fill

    last = rows[-1]
    first_ts = rows[0]["begins_at"]
    last_ts = last["begins_at"]
    lines = [
        title,
        f"{hi:.2f}",
        *["".join(row) for row in grid],
        f"{lo:.2f}  n={len(rows)}  {first_ts} → {last_ts}",
        (
            f"last O={last['open']:.2f} H={last['high']:.2f} "
            f"L={last['low']:.2f} C={last['close']:.2f} V={last['volume']:.0f}"
        ),
    ]
    return "\n".join(lines)


def live_quote_line(quote: dict[str, Any] | None, *, symbol: str) -> str:
    q = quote or {}
    inner = q.get("quote") if isinstance(q.get("quote"), dict) else q
    last = inner.get("last_trade_price") or inner.get("last_non_reg_trade_price") or inner.get("last")
    bid = inner.get("bid_price") or inner.get("bid")
    ask = inner.get("ask_price") or inner.get("ask")
    ts = (
        inner.get("venue_last_trade_time")
        or inner.get("venue_last_non_reg_trade_time")
        or inner.get("updated_at")
        or ""
    )
    return f"{symbol} live last={last} bid={bid} ask={ask} ts={ts}"
