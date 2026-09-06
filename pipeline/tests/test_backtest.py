from pipeline.backtest import CombinedSession, evaluate_combined_setup, run_combined_backtest


def _daily(bias: str = "bullish", neckline: float = 100.0) -> list[dict]:
    return [
        {
            "pattern": "inverse_head_and_shoulders" if bias == "bullish" else "head_and_shoulders",
            "timeframe": "day",
            "bias": bias,
            "neckline": neckline,
            "last_pivot": 40,
            "prominence": 0.05,
            "indices": [10, 20, 40],
        }
    ]


def _hour_hits(bias: str = "bullish") -> list[dict]:
    return [{"pattern": "double_bottom", "timeframe": "hour", "bias": bias, "last_pivot": 12}]


def _hour_bars(bias: str = "bullish") -> list[dict]:
    if bias == "bullish":
        closes = [90.0] * 10 + [110.0] * 10
    else:
        closes = [110.0] * 10 + [90.0] * 10
    return [{"close": close} for close in closes]


def _ten_min(level: float = 100.0) -> list[dict]:
    lookback = [{"close": 99.5, "high": 99.8, "low": 99.2, "volume": 1000} for _ in range(20)]
    breakout = {"close": level * 1.002, "high": level * 1.003, "low": level * 0.999, "volume": 2000}
    retest = {"close": level * 1.0015, "high": level * 1.002, "low": level * 0.999, "volume": 1200}
    return lookback + [breakout, retest]


def _valid_session(*, path: list[float], flatten_index: int | None = None) -> CombinedSession:
    return CombinedSession(
        daily_hits=_daily(),
        hour_hits=_hour_hits(),
        hour_bars=_hour_bars(),
        ten_min_bars=_ten_min(),
        live_executable=100.40,
        premium_path=path,
        flatten_index=flatten_index,
    )


def test_combined_strategy_take_profit_and_stop():
    win = evaluate_combined_setup(_valid_session(path=[1.05, 1.20, 1.45]))
    assert win.outcome == "take_profit"
    assert abs(win.pnl - 0.40) < 1e-9
    loss = evaluate_combined_setup(_valid_session(path=[0.95, 0.79]))
    assert loss.outcome == "stop"
    assert abs(loss.pnl + 0.20) < 1e-9


def test_combined_strategy_skips_hour_conflict_and_missing_retest():
    conflict = CombinedSession(
        daily_hits=_daily("bullish"),
        hour_hits=_hour_hits("bearish"),
        hour_bars=_hour_bars("bearish"),
        ten_min_bars=_ten_min(),
        live_executable=100.40,
        premium_path=[1.45],
    )
    assert evaluate_combined_setup(conflict).outcome == "skip"
    assert evaluate_combined_setup(conflict).reason == "hour_daily_pattern_conflict"

    no_retest_bars = _ten_min()
    no_retest_bars[-1] = {"close": 99.50, "high": 99.70, "low": 99.20, "volume": 1200}
    missed = CombinedSession(
        daily_hits=_daily(),
        hour_hits=_hour_hits(),
        hour_bars=_hour_bars(),
        ten_min_bars=no_retest_bars,
        live_executable=100.40,
        premium_path=[1.45],
    )
    assert evaluate_combined_setup(missed).outcome == "skip"


def test_combined_strategy_two_hundred_trades_have_edge():
    sessions: list[CombinedSession] = []
    for i in range(240):
        if i % 6 == 0:
            sessions.append(
                CombinedSession(
                    daily_hits=_daily(),
                    hour_hits=_hour_hits("bearish"),
                    hour_bars=_hour_bars("bearish"),
                    ten_min_bars=_ten_min(),
                    live_executable=100.40,
                    premium_path=[1.45],
                )
            )
            continue
        if i % 5 == 0:
            sessions.append(_valid_session(path=[0.95, 0.78]))
        else:
            sessions.append(_valid_session(path=[1.10, 1.42]))
    metrics = run_combined_backtest(sessions)
    assert metrics.trade_count >= 200
    assert metrics.skip_count >= 30
    assert metrics.profit_factor >= 1.3
    assert metrics.max_drawdown_pct <= 0.05
