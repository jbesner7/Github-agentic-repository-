from pipeline.patterns import (
    breakout_confirms,
    breakout_volume_ok,
    classify_hour_bias,
    hour_confirms_daily,
    hour_trend,
    live_trigger_confirms,
)


def test_hour_bias_none_mixed_and_match():
    assert classify_hour_bias([]) == "none"
    assert classify_hour_bias([{"timeframe": "hour", "bias": "neutral"}]) == "none"
    mixed = [
        {"timeframe": "hour", "bias": "bullish"},
        {"timeframe": "hour", "bias": "bearish"},
    ]
    assert classify_hour_bias(mixed) == "mixed"
    assert classify_hour_bias([{"timeframe": "hour", "bias": "bullish"}]) == "bullish"


def test_hour_trend_and_daily_alignment():
    bullish_bars = [{"close": 90.0}] * 10 + [{"close": 110.0}] * 10
    assert hour_trend(bullish_bars) == "bullish"
    bearish_bars = [{"close": 110.0}] * 10 + [{"close": 90.0}] * 10
    assert hour_trend(bearish_bars) == "bearish"
    ok, reason = hour_confirms_daily(
        "bullish",
        [{"timeframe": "hour", "bias": "bullish"}],
        bullish_bars,
    )
    assert ok is True and reason == "ok"
    conflict, conflict_reason = hour_confirms_daily(
        "bullish",
        [{"timeframe": "hour", "bias": "bearish"}],
        bearish_bars,
    )
    assert conflict is False and conflict_reason == "hour_daily_pattern_conflict"
    trend_fail, trend_reason = hour_confirms_daily(
        "bullish",
        [{"timeframe": "hour", "bias": "bullish"}],
        bearish_bars,
    )
    assert trend_fail is False and trend_reason == "hour_trend_conflict"


def test_breakout_volume_and_live_trigger_formulas():
    assert breakout_confirms({"close": 100.10}, 100.0, bias="bullish") is True
    assert breakout_confirms({"close": 100.05}, 100.0, bias="bullish") is False
    assert breakout_confirms({"close": 99.89}, 100.0, bias="bearish") is True
    assert breakout_volume_ok(1500, [1000] * 20) is True
    assert breakout_volume_ok(1400, [1000] * 20) is False
    assert live_trigger_confirms(100.15, 100.0, bias="bullish") is True
    assert live_trigger_confirms(100.05, 100.0, bias="bullish") is False
    assert live_trigger_confirms(99.85, 100.0, bias="bearish") is True
