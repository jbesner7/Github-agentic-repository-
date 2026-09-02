from pipeline.bars import aggregate_to_minutes, bars_for_timeframe, extract_rh_historicals_bars, normalize_bars
from pipeline.charts import ascii_chart
from pipeline.io_util import load_rules


def _bar(ts: str, o: float, h: float, l: float, c: float, v: float = 10) -> dict:
    return {
        "begins_at": ts,
        "open_price": str(o),
        "high_price": str(h),
        "low_price": str(l),
        "close_price": str(c),
        "volume": v,
        "interpolated": False,
    }


def test_normalize_rh_keys_and_drop_interpolated():
    bars = normalize_bars(
        [
            _bar("2026-09-01T13:30:00Z", 1, 2, 0.5, 1.5, 100),
            {
                "begins_at": "2026-09-01T13:31:00Z",
                "open_price": "1",
                "high_price": "1",
                "low_price": "1",
                "close_price": "1",
                "volume": 1,
                "interpolated": True,
            },
        ]
    )
    assert len(bars) == 1
    assert bars[0]["open"] == 1.0
    assert bars[0]["close"] == 1.5


def test_aggregate_three_minute_from_one_minute():
    # AVGO 2026-09-01 first three RTH 1-minute bars (live RH dump).
    minute = [
        _bar("2026-09-01T13:30:00Z", 364.49, 365.10, 363.36, 364.015, 369411),
        _bar("2026-09-01T13:31:00Z", 364.15, 364.21, 362.55, 362.7262, 41993),
        _bar("2026-09-01T13:32:00Z", 362.56, 363.7399, 362.265, 363.49, 46068),
        _bar("2026-09-01T13:33:00Z", 363.55, 364.50, 362.90, 364.04, 26954),
        _bar("2026-09-01T13:34:00Z", 363.9143, 364.3259, 363.37, 363.37, 18451),
        _bar("2026-09-01T13:35:00Z", 363.35, 364.2381, 363.25, 363.69, 33091),
    ]
    three = aggregate_to_minutes(minute, 3)
    assert [b["begins_at"] for b in three] == [
        "2026-09-01T13:30:00Z",
        "2026-09-01T13:33:00Z",
    ]
    first = three[0]
    assert first["open"] == 364.49
    assert first["high"] == 365.10
    assert first["low"] == 362.265
    assert first["close"] == 363.49
    assert first["volume"] == 369411 + 41993 + 46068


def test_aggregate_five_minute_matches_live_rh_first_bar():
    # Same AVGO session; native RH 5-minute open bar was O 364.49 H 365.10 L 362.265 C 363.37 V 502877.
    minute = [
        _bar("2026-09-01T13:30:00Z", 364.49, 365.10, 363.36, 364.015, 369411),
        _bar("2026-09-01T13:31:00Z", 364.15, 364.21, 362.55, 362.7262, 41993),
        _bar("2026-09-01T13:32:00Z", 362.56, 363.7399, 362.265, 363.49, 46068),
        _bar("2026-09-01T13:33:00Z", 363.55, 364.50, 362.90, 364.04, 26954),
        _bar("2026-09-01T13:34:00Z", 363.9143, 364.3259, 363.37, 363.37, 18451),
    ]
    five = aggregate_to_minutes(minute, 5)
    assert five[0]["begins_at"] == "2026-09-01T13:30:00Z"
    assert five[0]["open"] == 364.49
    assert five[0]["high"] == 365.10
    assert five[0]["low"] == 362.265
    assert five[0]["close"] == 363.37
    assert five[0]["volume"] == 502877


def test_bars_for_timeframe_synthesizes_3minute():
    minute = [
        _bar("2026-09-01T13:30:00Z", 10, 11, 9, 10.5, 1),
        _bar("2026-09-01T13:31:00Z", 10.5, 10.6, 10.4, 10.4, 1),
        _bar("2026-09-01T13:32:00Z", 10.4, 10.8, 10.3, 10.7, 1),
    ]
    out = bars_for_timeframe({"minute": minute}, "3minute")
    assert len(out) == 1
    assert out[0]["close"] == 10.7


def test_extract_rh_historicals_unwraps_results():
    payload = {
        "data": {
            "results": [
                {
                    "symbol": "AVGO",
                    "interval": "minute",
                    "bars": [_bar("2026-09-01T13:30:00Z", 1, 2, 1, 1.5, 9)],
                }
            ]
        }
    }
    bars = extract_rh_historicals_bars(payload)
    assert len(bars) == 1
    assert bars[0]["close_price"] == "1.5"


def test_ascii_chart_contains_title_and_last_close():
    bars = [
        {"begins_at": f"2026-09-01T13:{i:02d}:00Z", "open": 10 + i * 0.1, "high": 11, "low": 9, "close": 10.2 + i * 0.1, "volume": 1}
        for i in range(12)
    ]
    text = ascii_chart(bars, title="AVGO 1m")
    assert text.startswith("AVGO 1m")
    assert "last O=" in text
    assert "C=11.30" in text


def test_rules_use_live_1m_3m_5m():
    rules = load_rules()
    assert rules["patterns"]["timeframes"] == ["minute", "3minute", "5minute", "hour", "day"]
    hist = rules["historicals"]
    assert hist["live"] == "get_equity_quotes"
    assert hist["intraday_interval"] == "minute"
    assert hist["synthetic_intervals"]["3minute"]["source"] == "minute"
    assert "15minute" not in rules["patterns"]["timeframes"]
    assert "3minute" not in hist["rh_native_intervals"]

# hash-pad 1
