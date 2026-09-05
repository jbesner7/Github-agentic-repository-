"""Normalize Robinhood OHLCV bars and build custom intervals.

Robinhood MCP `get_equity_historicals` fixed intervals:
  15second, 30second, minute, 5minute, 10minute, 30minute, hour, 4hour, day, ...
The 1-minute bar is named `minute` (not `1minute`). There is no `3minute`
and no `15minute`. For 3-minute graphs, fetch `minute` and aggregate here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _as_float(value: Any, default: float | None = None) -> float:
    if value is None or value == "":
        if default is None:
            raise ValueError("missing numeric bar field")
        return default
    return float(value)


def _begins_at(bar: dict[str, Any]) -> str:
    raw = bar.get("begins_at") or bar.get("timestamp") or bar.get("start") or bar.get("time") or ""
    return str(raw)


def _parse_utc(ts: str) -> datetime:
    text = ts.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_bar(bar: dict[str, Any]) -> dict[str, Any]:
    """Accept RH (`open_price`) or pipeline (`open`) keys. Skip nothing here."""
    open_px = bar.get("open", bar.get("open_price"))
    high_px = bar.get("high", bar.get("high_price"))
    low_px = bar.get("low", bar.get("low_price"))
    close_px = bar.get("close", bar.get("close_price"))
    return {
        "begins_at": _begins_at(bar),
        "open": _as_float(open_px),
        "high": _as_float(high_px),
        "low": _as_float(low_px),
        "close": _as_float(close_px),
        "volume": _as_float(bar.get("volume"), default=0.0),
        "interpolated": bool(bar.get("interpolated")),
        "session": bar.get("session"),
    }


def normalize_bars(bars: list[dict[str, Any]] | None, *, drop_interpolated: bool = True) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for bar in bars or []:
        try:
            row = normalize_bar(bar)
        except (TypeError, ValueError):
            continue
        if drop_interpolated and row["interpolated"]:
            continue
        out.append(row)
    out.sort(key=lambda b: b["begins_at"])
    return out


def extract_rh_historicals_bars(payload: Any) -> list[dict[str, Any]]:
    """Unwrap `get_equity_historicals` MCP JSON to a flat bar list."""
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and (
            "open" in payload[0] or "open_price" in payload[0] or "close" in payload[0]
        ):
            return payload
    data = payload
    if isinstance(payload, dict) and "data" in payload:
        data = payload["data"]
    results = []
    if isinstance(data, dict):
        results = data.get("results") or data.get("historicals") or []
        if isinstance(data.get("bars"), list):
            return data["bars"]
    bars: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        chunk = row.get("bars") or row.get("historicals") or []
        bars.extend(chunk)
    return bars


def aggregate_to_minutes(bars: list[dict[str, Any]] | None, minutes: int) -> list[dict[str, Any]]:
    """Build N-minute OHLCV from 1-minute (or finer) left-edge bars.

    Buckets align to UTC clock minutes (RTH 09:30 ET = 13:30 UTC, which is
    divisible by 3). Partial last buckets are kept (live in-progress bar).
    """
    if minutes < 1:
        raise ValueError("minutes must be >= 1")
    norm = normalize_bars(bars)
    if minutes == 1:
        return norm
    buckets: dict[datetime, list[dict[str, Any]]] = {}
    order: list[datetime] = []
    for bar in norm:
        if not bar["begins_at"]:
            continue
        dt = _parse_utc(bar["begins_at"]).replace(second=0, microsecond=0)
        minute_of_day = dt.hour * 60 + dt.minute
        aligned = minute_of_day - (minute_of_day % minutes)
        key = dt.replace(hour=aligned // 60, minute=aligned % 60)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(bar)
    out: list[dict[str, Any]] = []
    for key in order:
        group = buckets[key]
        out.append(
            {
                "begins_at": key.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open": group[0]["open"],
                "high": max(b["high"] for b in group),
                "low": min(b["low"] for b in group),
                "close": group[-1]["close"],
                "volume": sum(b["volume"] for b in group),
                "interpolated": False,
                "session": group[0].get("session"),
            }
        )
    return out


def bars_for_timeframe(
    historicals_for_symbol: dict[str, Any] | None,
    timeframe: str,
) -> list[dict[str, Any]]:
    """Resolve bars for a rules.json timeframe, synthesizing 3-minute from 1-minute."""
    by_tf = historicals_for_symbol or {}
    if timeframe == "3minute":
        existing = normalize_bars(by_tf.get("3minute") or [])
        if existing:
            return existing
        return aggregate_to_minutes(by_tf.get("minute") or by_tf.get("1minute") or [], 3)
    return normalize_bars(by_tf.get(timeframe) or [])
