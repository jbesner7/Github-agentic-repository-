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


PATTERN_PRIORITY = (
    "inverse_head_and_shoulders",
    "head_and_shoulders",
    "double_bottom",
    "double_top",
    "triple_bottom",
    "triple_top",
    "ascending_triangle",
    "descending_triangle",
)

HEAD_PROMINENCE_PCT = 0.015
MIN_PIVOT_SEPARATION_BARS = 3
MAX_PATTERN_BARS = {
    "day": 60,
    "daily": 60,
    "hour": 40,
    "10minute": 30,
}
TRIANGLE_TOUCH_PCT = 0.005
TRIANGLE_MIN_TOUCHES_PER_SIDE = 2


def _max_pattern_bars(timeframe: str) -> int:
    return MAX_PATTERN_BARS.get(timeframe, 60)


def _pivots_separated(indices: list[int], *, min_gap: int = MIN_PIVOT_SEPARATION_BARS) -> bool:
    ordered = sorted(indices)
    return all(b - a >= min_gap for a, b in zip(ordered, ordered[1:]))


def _count_line_touches(prices: np.ndarray, slope: float, intercept: float, *, tol_pct: float) -> int:
    touches = 0
    for i, price in enumerate(prices):
        fitted = intercept + slope * float(i)
        base = max(abs(fitted), abs(float(price)), 1e-9)
        if abs(float(price) - fitted) / base <= tol_pct:
            touches += 1
    return touches


def rank_daily_setups(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One deterministic winner among overlapping daily setups. Neutral triangles never rank."""
    daily = [
        hit
        for hit in hits
        if hit.get("timeframe") in ("day", "daily") and hit.get("bias") not in (None, "neutral", "none")
    ]
    priority = {name: i for i, name in enumerate(PATTERN_PRIORITY)}

    def sort_key(hit: dict[str, Any]) -> tuple[int, int, float]:
        last_idx = max(hit.get("indices") or [0])
        prominence = float(hit.get("prominence") or 0.0)
        return (-last_idx, priority.get(str(hit.get("pattern")), 99), -prominence)

    return sorted(daily, key=sort_key)


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

    # Head and shoulders / inverse: time-ordered LS → head → RS, intervening opposite pivots.
    max_span = _max_pattern_bars(timeframe)
    if len(peaks) >= 3:
        l, h, r = peaks[-3], peaks[-2], peaks[-1]
        left_troughs = [t for t in troughs if l < t < h]
        right_troughs = [t for t in troughs if h < t < r]
        head_vs_left = (closes[h] - closes[l]) / max(abs(closes[l]), 1e-9)
        head_vs_right = (closes[h] - closes[r]) / max(abs(closes[r]), 1e-9)
        if (
            l < h < r
            and (r - l) <= max_span
            and _pivots_separated([l, h, r])
            and left_troughs
            and right_troughs
            and closes[h] > closes[l]
            and closes[h] > closes[r]
            and head_vs_left >= HEAD_PROMINENCE_PCT
            and head_vs_right >= HEAD_PROMINENCE_PCT
            and _nearly_equal(closes[l], closes[r], tol_pct=0.025)
        ):
            neck = float((closes[left_troughs[-1]] + closes[right_troughs[0]]) / 2.0)
            hits.append(
                {
                    "pattern": "head_and_shoulders",
                    "timeframe": timeframe,
                    "indices": [l, h, r],
                    "prices": [float(closes[l]), float(closes[h]), float(closes[r])],
                    "neckline": neck,
                    "prominence": float(min(head_vs_left, head_vs_right)),
                    "bias": "bearish",
                }
            )
    if len(troughs) >= 3:
        l, h, r = troughs[-3], troughs[-2], troughs[-1]
        left_peaks = [p for p in peaks if l < p < h]
        right_peaks = [p for p in peaks if h < p < r]
        head_vs_left = (closes[l] - closes[h]) / max(abs(closes[l]), 1e-9)
        head_vs_right = (closes[r] - closes[h]) / max(abs(closes[r]), 1e-9)
        if (
            l < h < r
            and (r - l) <= max_span
            and _pivots_separated([l, h, r])
            and left_peaks
            and right_peaks
            and closes[h] < closes[l]
            and closes[h] < closes[r]
            and head_vs_left >= HEAD_PROMINENCE_PCT
            and head_vs_right >= HEAD_PROMINENCE_PCT
            and _nearly_equal(closes[l], closes[r], tol_pct=0.025)
        ):
            neck = float((closes[left_peaks[-1]] + closes[right_peaks[0]]) / 2.0)
            hits.append(
                {
                    "pattern": "inverse_head_and_shoulders",
                    "timeframe": timeframe,
                    "indices": [l, h, r],
                    "prices": [float(closes[l]), float(closes[h]), float(closes[r])],
                    "neckline": neck,
                    "prominence": float(min(head_vs_left, head_vs_right)),
                    "bias": "bullish",
                }
            )

    # Triangles on recent 40 bars: converging highs/lows
    window = min(40, len(closes))
    seg_high = highs[-window:]
    seg_low = lows[-window:]
    x = np.arange(window, dtype=float)
    if window >= 20:
        high_fit = np.polyfit(x, seg_high, 1)
        low_fit = np.polyfit(x, seg_low, 1)
        high_slope = float(high_fit[0])
        low_slope = float(low_fit[0])
        high_range = float(seg_high.max() - seg_high.min())
        low_range = float(seg_low.max() - seg_low.min())
        # Flat side: abs(OLS slope) < 15% of (side range / window bars).
        flat_high = abs(high_slope) < (high_range / window) * 0.15
        flat_low = abs(low_slope) < (low_range / window) * 0.15
        rising_low = low_slope > 0
        falling_high = high_slope < 0
        high_touches = _count_line_touches(seg_high, high_slope, float(high_fit[1]), tol_pct=TRIANGLE_TOUCH_PCT)
        low_touches = _count_line_touches(seg_low, low_slope, float(low_fit[1]), tol_pct=TRIANGLE_TOUCH_PCT)
        enough_touches = (
            high_touches >= TRIANGLE_MIN_TOUCHES_PER_SIDE
            and low_touches >= TRIANGLE_MIN_TOUCHES_PER_SIDE
        )
        start_idx = len(closes) - window
        triangle_meta = {
            "timeframe": timeframe,
            "indices": [start_idx, len(closes) - 1],
            "high_slope": high_slope,
            "low_slope": low_slope,
            "high_touches": high_touches,
            "low_touches": low_touches,
            "prominence": float(min(high_range, low_range)),
        }
        if enough_touches and flat_high and rising_low:
            hits.append({"pattern": "ascending_triangle", "bias": "bullish", **triangle_meta})
        elif enough_touches and flat_low and falling_high:
            hits.append({"pattern": "descending_triangle", "bias": "bearish", **triangle_meta})
        elif enough_touches and falling_high and rising_low:
            hits.append({"pattern": "symmetrical_triangle", "bias": "neutral", **triangle_meta})

    return hits


def collect_pattern_hits(
    historicals_for_symbol: dict[str, Any],
    timeframes: list[str],
) -> list[dict[str, Any]]:
    """Daily first. 10-minute / hour only on names with a daily pattern hit."""
    daily_bars = list(historicals_for_symbol.get("day") or historicals_for_symbol.get("daily") or [])
    daily_hits = detect_patterns(daily_bars, timeframe="day")
    hits = list(daily_hits)
    if not daily_hits:
        return hits
    for tf in timeframes:
        if tf in ("day", "daily"):
            continue
        bars = historicals_for_symbol.get(tf) or []
        hits.extend(detect_patterns(list(bars), timeframe=tf))
    return hits
