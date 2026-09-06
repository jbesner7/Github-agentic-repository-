"""Combined Agent H strategy backtest.

This is not a per-threshold unit check. One session walks:

daily winner → hour confirm (pattern + trend) → 20 completed 10m lookback
→ breakout close + volume → retest → live trigger → modeled fill
→ stop 80% / take-profit 140% / flatten-by-deadline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.patterns import (
    BREAKOUT_CLOSE_BEYOND_PCT,
    BREAKOUT_VOLUME_MULTIPLE,
    HOUR_TREND_LOOKBACK,
    LIVE_TRIGGER_BEYOND_PCT,
    RETEST_TOLERANCE_PCT,
    breakout_confirms,
    breakout_volume_ok,
    hour_confirms_daily,
    live_trigger_confirms,
    rank_daily_setups,
    retest_confirms,
)


STOP_FRACTION = 0.80
TAKE_PROFIT_MULTIPLE = 1.40


@dataclass(frozen=True)
class CombinedSession:
    daily_hits: list[dict[str, Any]]
    hour_hits: list[dict[str, Any]]
    hour_bars: list[dict[str, Any]]
    ten_min_bars: list[dict[str, Any]]
    live_executable: float
    premium_path: list[float]
    flatten_index: int | None = None
    entry_premium: float = 1.00


@dataclass
class CombinedResult:
    outcome: str
    reason: str
    pnl: float = 0.0
    daily_bias: str | None = None


@dataclass
class CombinedMetrics:
    trades: list[CombinedResult] = field(default_factory=list)
    modeled_nlv: float = 1500.0
    contract_multiplier: float = 100.0

    @property
    def trade_count(self) -> int:
        return sum(1 for row in self.trades if row.outcome in {"take_profit", "stop", "flatten"})

    @property
    def skip_count(self) -> int:
        return sum(1 for row in self.trades if row.outcome == "skip")

    @property
    def cash_pnls(self) -> list[float]:
        return [row.pnl * self.contract_multiplier for row in self.trades if row.outcome != "skip"]

    @property
    def gross_profit(self) -> float:
        return sum(pnl for pnl in self.cash_pnls if pnl > 0)

    @property
    def gross_loss(self) -> float:
        return abs(sum(pnl for pnl in self.cash_pnls if pnl < 0))

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return self.gross_profit / self.gross_loss

    @property
    def max_drawdown_pct(self) -> float:
        """Peak-to-trough cash drawdown as a fraction of modeled NLV."""
        equity = 0.0
        peak = 0.0
        worst_drop = 0.0
        for pnl in self.cash_pnls:
            equity += pnl
            peak = max(peak, equity)
            worst_drop = max(worst_drop, peak - equity)
        if self.modeled_nlv <= 0:
            return 0.0
        return worst_drop / self.modeled_nlv


def evaluate_combined_setup(session: CombinedSession) -> CombinedResult:
    ranked = rank_daily_setups(session.daily_hits)
    if not ranked:
        return CombinedResult("skip", "no_daily_setup")
    winner = ranked[0]
    daily_bias = str(winner.get("bias"))
    level = float(winner["neckline"])
    ok, reason = hour_confirms_daily(
        daily_bias,
        session.hour_hits,
        session.hour_bars,
        lookback=HOUR_TREND_LOOKBACK,
    )
    if not ok:
        return CombinedResult("skip", reason, daily_bias=daily_bias)
    bars = list(session.ten_min_bars)
    if len(bars) < 22:
        return CombinedResult("skip", "ten_min_lookback_short", daily_bias=daily_bias)
    lookback = bars[-22:-2]
    breakout = bars[-2]
    retest = bars[-1]
    prior_volumes = [float(bar.get("volume") or 0.0) for bar in lookback]
    if not breakout_confirms(breakout, level, bias=daily_bias, beyond_pct=BREAKOUT_CLOSE_BEYOND_PCT):
        return CombinedResult("skip", "breakout_close_not_beyond", daily_bias=daily_bias)
    if not breakout_volume_ok(
        float(breakout.get("volume") or 0.0),
        prior_volumes,
        multiple=BREAKOUT_VOLUME_MULTIPLE,
    ):
        return CombinedResult("skip", "breakout_volume", daily_bias=daily_bias)
    retest_ok, retest_reason = retest_confirms(
        retest,
        level,
        bias=daily_bias,
        tolerance_pct=RETEST_TOLERANCE_PCT,
    )
    if not retest_ok:
        return CombinedResult("skip", retest_reason or "retest_failed", daily_bias=daily_bias)
    if not live_trigger_confirms(
        session.live_executable,
        float(breakout["close"]),
        bias=daily_bias,
        beyond_pct=LIVE_TRIGGER_BEYOND_PCT,
    ):
        return CombinedResult("skip", "live_trigger", daily_bias=daily_bias)
    return simulate_open_trade(session, daily_bias=daily_bias)


def simulate_open_trade(session: CombinedSession, *, daily_bias: str) -> CombinedResult:
    entry = float(session.entry_premium)
    stop = entry * STOP_FRACTION
    take = entry * TAKE_PROFIT_MULTIPLE
    for idx, px in enumerate(session.premium_path):
        price = float(px)
        if price <= stop:
            return CombinedResult("stop", "stop_hit", pnl=stop - entry, daily_bias=daily_bias)
        if price >= take:
            return CombinedResult("take_profit", "tp_hit", pnl=take - entry, daily_bias=daily_bias)
        if session.flatten_index is not None and idx >= session.flatten_index:
            return CombinedResult("flatten", "session_flatten", pnl=price - entry, daily_bias=daily_bias)
    last = float(session.premium_path[-1]) if session.premium_path else entry
    return CombinedResult("flatten", "path_end", pnl=last - entry, daily_bias=daily_bias)


def run_combined_backtest(sessions: list[CombinedSession]) -> CombinedMetrics:
    metrics = CombinedMetrics()
    for session in sessions:
        metrics.trades.append(evaluate_combined_setup(session))
    return metrics
