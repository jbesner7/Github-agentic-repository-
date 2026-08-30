from __future__ import annotations

from typing import Any

import numpy as np


def _local_extrema(prices: np.ndarray, order: int = 3) -> tuple[list[int], list[int]]:
    """Simple peak/trough detection with `order` bars on each side."""
    peaks: list[int] = []
    troughs: list[int] = []
    n = len(prices)
    for i in range(order, n - order):
        window = prices[i - order : i + order + 1]
        if prices[i] == window.max() and np.sum(window == prices[i]) == 1:
            peaks.append(i)
        if prices[i] == window.min() and np.sum(window == prices[i]) == 1:
            troughs.append(i)
    return peaks, troughs


def _nearly_equal(a: float, b: float, tol_pct: float = 0.015) -> bool:
    base = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / base <= tol_pct


def detect_patterns(ohlc: list[dict[str, Any]], *, timeframe: str) -> list[dict[str, Any]]:
    """
    Deterministic pattern heuristics on close prices.
    Returns pattern hits with indices; empty if insufficient bars.
    """
    if len(ohlc) < 30:
        return []

    closes = np.array([float(b["close"]) for b in ohlc], dtype=float)
    highs = np.array([float(b.get("high", b["close"])) for b in ohlc], dtype=float)
    lows = np.array([float(b.get("low", b["close"])) for b in ohlc], dtype=float)
    peaks, troughs = _local_extrema(closes, order=3)
    hits: list[dict[str, Any]] = []

    # Double / triple tops
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if _nearly_equal(closes[p1], closes[p2]):
            neck = float(closes[p1:p2].min()) if p2 > p1 else float(closes[p2])
            hits.append(
                {
                    "pattern": "double_top",
                    "timeframe": timeframe,
                    "indices": [p1, p2],
                    "prices": [float(closes[p1]), float(closes[p2])],
                    "neckline": neck,
                    "bias": "bearish",
                }
            )
    if len(peaks) >= 3:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        if _nearly_equal(closes[p1], closes[p2]) and _nearly_equal(closes[p2], closes[p3]):
            hits.append(
                {
                    "pattern": "triple_top",
                    "timeframe": timeframe,
                    "indices": [p1, p2, p3],
                    "prices": [float(closes[p1]), float(closes[p2]), float(closes[p3])],
                    "bias": "bearish",
                }
            )

    # Double / triple bottoms
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        if _nearly_equal(closes[t1], closes[t2]):
            neck = float(closes[t1:t2].max()) if t2 > t1 else float(closes[t2])
            hits.append(
                {
                    "pattern": "double_bottom",
                    "timeframe": timeframe,
                    "indices": [t1, t2],
                    "prices": [float(closes[t1]), float(closes[t2])],
                    "neckline": neck,
                    "bias": "bullish",
                }
            )
    if len(troughs) >= 3:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        if _nearly_equal(closes[t1], closes[t2]) and _nearly_equal(closes[t2], closes[t3]):
            hits.append(
                {
                    "pattern": "triple_bottom",
                    "timeframe": timeframe,
                    "indices": [t1, t2, t3],
                    "prices": [float(closes[t1]), float(closes[t2]), float(closes[t3])],
                    "bias": "bullish",
                }
            )

    # Head and shoulders / inverse (last three extrema of opposite type)
    if len(peaks) >= 3:
        l, h, r = peaks[-3], peaks[-2], peaks[-1]
        if closes[h] > closes[l] and closes[h] > closes[r] and _nearly_equal(closes[l], closes[r], tol_pct=0.025):
            hits.append(
                {
                    "pattern": "head_and_shoulders",
                    "timeframe": timeframe,
                    "indices": [l, h, r],
                    "prices": [float(closes[l]), float(closes[h]), float(closes[r])],
                    "bias": "bearish",
                }
            )
    if len(troughs) >= 3:
        l, h, r = troughs[-3], troughs[-2], troughs[-1]
        if closes[h] < closes[l] and closes[h] < closes[r] and _nearly_equal(closes[l], closes[r], tol_pct=0.025):
            hits.append(
                {
                    "pattern": "inverse_head_and_shoulders",
                    "timeframe": timeframe,
                    "indices": [l, h, r],
                    "prices": [float(closes[l]), float(closes[h]), float(closes[r])],
                    "bias": "bullish",
                }
            )

    # Triangles on recent 40 bars: converging highs/lows
    window = min(40, len(closes))
    seg_high = highs[-window:]
    seg_low = lows[-window:]
    x = np.arange(window, dtype=float)
    if window >= 20:
        high_slope = float(np.polyfit(x, seg_high, 1)[0])
        low_slope = float(np.polyfit(x, seg_low, 1)[0])
        high_range = float(seg_high.max() - seg_high.min())
        low_range = float(seg_low.max() - seg_low.min())
        flat_high = abs(high_slope) < (high_range / window) * 0.15
        flat_low = abs(low_slope) < (low_range / window) * 0.15
        rising_low = low_slope > 0
        falling_high = high_slope < 0
        if flat_high and rising_low:
            hits.append(
                {
                    "pattern": "ascending_triangle",
                    "timeframe": timeframe,
                    "high_slope": high_slope,
                    "low_slope": low_slope,
                    "bias": "bullish",
                }
            )
        elif flat_low and falling_high:
            hits.append(
                {
                    "pattern": "descending_triangle",
                    "timeframe": timeframe,
                    "high_slope": high_slope,
                    "low_slope": low_slope,
                    "bias": "bearish",
                }
            )
        elif falling_high and rising_low:
            hits.append(
                {
                    "pattern": "symmetrical_triangle",
                    "timeframe": timeframe,
                    "high_slope": high_slope,
                    "low_slope": low_slope,
                    "bias": "neutral",
                }
            )

    return hits
