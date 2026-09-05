from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from pipeline.greeks import delta_in_band, extract_greeks
from pipeline.options_structure import (
    filter_expirations,
    pick_atm_or_one_otm,
    rank_atm_then_one_otm,
    rank_expirations,
    strikes_bracket_spot,
)
from pipeline.patterns import rank_daily_setups
from pipeline.quotes import executable_underlying_price, extract_bod_nlv
from pipeline.patterns import collect_pattern_hits, detect_patterns
from pipeline.risk import equity_risk_plan, options_risk_plan
from pipeline.session import today_et
from pipeline.universe import apply_liquidity_filter, extract_watchlist_symbols, option_quote_liquid


def test_extract_excludes_crypto():
    watchlists = [{"id": "1", "display_name": "My First List"}]
    items = {
        "1": [
            {"object_type": "instrument", "symbol": "AAPL"},
            {"object_type": "currency_pair", "symbol": "BTC-USD"},
        ]
    }
    out = extract_watchlist_symbols(watchlists, items, [], include_crypto=False)
    assert out["equity_symbols"] == ["AAPL"]
    assert "BTC-USD" in out["skipped_crypto"]


def test_liquidity_volume_gate():
    fund = {"AAA": {"average_volume": 3_000_000}, "BBB": {"average_volume": 1000}}
    out = apply_liquidity_filter(["AAA", "BBB"], fund, min_average_volume=2_000_000)
    assert out["passed_symbols"] == ["AAA"]
    assert out["rejected"][0]["symbol"] == "BBB"


def test_liquidity_rejects_inverse_etfs_before_volume():
    fund = {
        "AAA": {"average_volume": 3_000_000},
        "SQQQ": {"average_volume": 20_000_000, "name": "ProShares UltraPro Short QQQ"},
        "XYZ": {"average_volume": 5_000_000, "description": "Leveraged inverse daily"},
    }
    out = apply_liquidity_filter(["AAA", "SQQQ", "XYZ"], fund, min_average_volume=2_000_000)
    assert out["passed_symbols"] == ["AAA"]
    reasons = {row["symbol"]: row["reason"] for row in out["rejected"]}
    assert reasons["SQQQ"] == "inverse_etf"
    assert reasons["XYZ"] == "inverse_etf"


def test_option_spread_gate():
    preferred, reason, pref_m = option_quote_liquid(
        {"bid_price": "1.00", "ask_price": "1.05"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert preferred and reason is None
    assert pref_m["spread_quality"] == "preferred"

    acceptable, reason_ok, acc_m = option_quote_liquid(
        {"bid": "1.00", "ask": "1.08"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert acceptable and reason_ok is None
    assert acc_m["spread_quality"] == "acceptable"

    missing, missing_reason, _ = option_quote_liquid(
        {},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert not missing and missing_reason == "missing_bid_ask"

    bad, reason2, _ = option_quote_liquid(
        {"bid_price": "1.00", "ask_price": "1.50"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert not bad and reason2 == "spread_too_wide"

    # $0.10 absolute on a cheap contract is ~22% of mid — reject (no dollar override).
    cheap, cheap_reason, cheap_m = option_quote_liquid(
        {"bid_price": "0.40", "ask_price": "0.50"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert not cheap and cheap_reason == "spread_too_wide"
    assert cheap_m["spread_pct_of_price"] > 0.1


def test_double_bottom_detection():
    # Equal troughs separated by a bounce; pad so extrema order=3 works.
    prices = (
        [6, 6, 6, 5, 4, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6]
        + [6.2 + i * 0.05 for i in range(20)]
    )
    bars = [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]
    hits = detect_patterns(bars, timeframe="day")
    names = {h["pattern"] for h in hits}
    assert "double_bottom" in names


def test_greeks_no_invention():
    q = {"delta": "0.45", "gamma": "0.01"}
    pack = extract_greeks(q)
    assert pack["greeks"]["delta"] == 0.45
    assert "theta" in pack["missing_fields"]
    ok, _ = delta_in_band(0.45, option_type="call", lo=0.4, hi=0.5)
    assert ok
    bad, reason = delta_in_band(0.9, option_type="call", lo=0.4, hi=0.5)
    assert not bad and reason is not None
    put_ok, _ = delta_in_band(-0.45, option_type="put", lo=0.4, hi=0.5)
    assert put_ok
    inverted, inv_reason = delta_in_band(0.45, option_type="put", lo=0.4, hi=0.5)
    assert not inverted and inv_reason is not None
    abs_call, abs_reason = delta_in_band(-0.45, option_type="call", lo=0.4, hi=0.5)
    assert not abs_call and abs_reason is not None


def test_options_risk_math():
    plan = options_risk_plan(premium_per_share=2.0, contracts=1)
    assert plan["cash_risked"] == 200.0
    assert plan["take_profit_pct"] == 0.40
    assert plan["stop_loss_pct"] == 0.20
    assert plan["take_profit_value"] == 280.0
    assert plan["stop_loss_value"] == 160.0
    assert plan["reward_to_risk"] == 2.0
    assert plan["meets_target_rr"] is True


def test_options_risk_bands():
    wide = options_risk_plan(premium_per_share=1.0, stop_loss_pct=0.50, take_profit_pct=1.00)
    assert wide["stop_loss_value"] == 50.0
    assert wide["take_profit_value"] == 200.0
    assert wide["reward_to_risk"] == 2.0
    try:
        options_risk_plan(premium_per_share=1.0, stop_loss_pct=0.07, take_profit_pct=0.50)
        raise AssertionError("expected ValueError for SL below 20%")
    except ValueError as exc:
        assert "stop_loss_pct" in str(exc)
    try:
        options_risk_plan(premium_per_share=1.0, stop_loss_pct=0.25, take_profit_pct=0.20)
        raise AssertionError("expected ValueError for TP below 30%")
    except ValueError as exc:
        assert "take_profit_pct" in str(exc)


def test_equity_risk_math():
    plan = equity_risk_plan(cost_basis=1000.0)
    assert plan["take_profit_value"] == 1250.0
    assert plan["stop_loss_value"] == 800.0


def test_atm_pick_and_dte():
    instruments = [
        {"id": "1", "type": "call", "strike_price": "100"},
        {"id": "2", "type": "call", "strike_price": "105"},
        {"id": "3", "type": "put", "strike_price": "95"},
    ]
    pick = pick_atm_or_one_otm(100.0, instruments, option_type="call")
    assert pick["selection"] == "atm"
    assert pick["instrument"]["id"] == "1"
    exps = filter_expirations(["2099-01-01", "2026-09-02"], max_dte=7, as_of=date(2026, 8, 30))
    assert exps == ["2026-09-02"]
    default_min = filter_expirations(
        ["2026-08-30", "2026-08-31", "2026-09-01", "2026-09-02"],
        max_dte=7,
        as_of=date(2026, 8, 30),
    )
    assert default_min == ["2026-09-01", "2026-09-02"]
    locked = filter_expirations(
        ["2026-08-30", "2026-08-31", "2026-09-02"],
        min_dte=2,
        max_dte=7,
        as_of=date(2026, 8, 30),
    )
    assert locked == ["2026-09-02"]


def test_atm_is_nearest_strike_even_when_more_than_one_percent_away():
    instruments = [
        {"id": "itm", "type": "call", "strike_price": "5.0"},
        {"id": "otm", "type": "call", "strike_price": "5.5"},
    ]
    ranked = rank_atm_then_one_otm(5.10, instruments, option_type="call")
    assert ranked[0]["selection"] == "atm"
    assert ranked[0]["instrument"]["id"] == "itm"
    assert ranked[1]["selection"] == "one_otm"
    assert ranked[1]["instrument"]["id"] == "otm"
    pick = pick_atm_or_one_otm(5.10, instruments, option_type="call")
    assert pick["instrument"]["id"] == "itm"


def test_put_atm_then_distinct_one_otm():
    instruments = [
        {"id": "otm", "option_type": "put", "strike": "18.0"},
        {"id": "atm", "option_type": "put", "strike": "18.5"},
    ]
    ranked = rank_atm_then_one_otm(18.30, instruments, option_type="put")
    assert ranked[0]["instrument"]["id"] == "atm"
    assert ranked[1]["instrument"]["id"] == "otm"


def test_strikes_must_bracket_spot_for_atm_page():
    only_low = [{"id": "1", "type": "call", "strike_price": "100"}]
    assert not strikes_bracket_spot(200.0, only_low, option_type="call")
    assert strikes_bracket_spot(100.0, only_low, option_type="call")
    bracketed = only_low + [{"id": "2", "type": "call", "strike_price": "210"}]
    assert strikes_bracket_spot(200.0, bracketed, option_type="call")


def test_today_et_uses_new_york_calendar_not_utc():
    utc_after_midnight = datetime(2026, 9, 1, 2, 0, tzinfo=timezone.utc)
    assert today_et(utc_after_midnight).isoformat() == "2026-08-31"
    et_evening = datetime(2026, 8, 31, 22, 0, tzinfo=ZoneInfo("America/New_York"))
    assert today_et(et_evening).isoformat() == "2026-08-31"


def test_atm_tie_and_otm_are_measured_from_atm():
    instruments = [
        {"id": "low", "type": "call", "strike_price": "100"},
        {"id": "high", "type": "call", "strike_price": "101"},
        {"id": "higher", "type": "call", "strike_price": "102"},
    ]
    call_ranked = rank_atm_then_one_otm(100.5, instruments, option_type="call")
    assert call_ranked[0]["instrument"]["id"] == "low"
    assert call_ranked[1]["instrument"]["id"] == "high"

    puts = [
        {"id": "low", "option_type": "put", "strike": "100"},
        {"id": "high", "option_type": "put", "strike": "101"},
        {"id": "higher", "option_type": "put", "strike": "102"},
    ]
    put_ranked = rank_atm_then_one_otm(100.5, puts, option_type="put")
    assert put_ranked[0]["instrument"]["id"] == "high"
    assert put_ranked[1]["instrument"]["id"] == "low"

    call_above_spot = rank_atm_then_one_otm(100.6, instruments, option_type="call")
    assert call_above_spot[0]["instrument"]["id"] == "high"
    assert call_above_spot[1]["instrument"]["id"] == "higher"


def test_expiration_rank_uses_same_day_group_when_overnight_off():
    dates = ["2026-09-07", "2026-09-08", "2026-09-09", "2026-09-11"]
    as_of = date(2026, 9, 5)
    same_day = rank_expirations(dates, overnight_holding_enabled=False, as_of=as_of)
    assert same_day == ["2026-09-07", "2026-09-08"]
    overnight = rank_expirations(dates, overnight_holding_enabled=True, as_of=as_of)
    assert overnight == ["2026-09-09", "2026-09-11"]


def test_underlying_quote_and_bod_nlv_helpers():
    now = datetime(2026, 9, 4, 17, 30, tzinfo=timezone.utc)
    fresh = {
        "bid_price": "10.00",
        "ask_price": "10.10",
        "last_trade_price": "10.04",
        "updated_at": "2026-09-04T17:29:58Z",
    }
    price, reason = executable_underlying_price(fresh, now=now)
    assert reason is None
    assert price == 10.04
    outside = dict(fresh, last_trade_price="10.50")
    mid, mid_reason = executable_underlying_price(outside, now=now)
    assert mid_reason is None
    assert mid == 10.05
    stale, stale_reason = executable_underlying_price(
        dict(fresh, updated_at="2026-09-04T17:29:50Z"), now=now
    )
    assert stale is None and stale_reason == "underlying_quote_stale"
    amount, field = extract_bod_nlv({"start_of_day_equity": "1500.00", "total_value": "1512"})
    assert amount == 1500.0 and field == "start_of_day_equity"
    missing, missing_field = extract_bod_nlv({"total_value": "1512"})
    assert missing is None and missing_field is None


def test_daily_setup_rank_is_deterministic():
    hits = [
        {
            "pattern": "ascending_triangle",
            "timeframe": "day",
            "bias": "bullish",
            "indices": [20, 80],
            "last_pivot": 80,
            "prominence": 9.0,
        },
        {
            "pattern": "head_and_shoulders",
            "timeframe": "day",
            "bias": "bearish",
            "indices": [10, 20, 30],
            "last_pivot": 30,
            "prominence": 0.02,
        },
        {
            "pattern": "double_bottom",
            "timeframe": "day",
            "bias": "bullish",
            "indices": [10, 40],
            "last_pivot": 40,
            "prominence": 1.0,
        },
        {
            "pattern": "symmetrical_triangle",
            "timeframe": "day",
            "bias": "neutral",
            "indices": [30, 50],
            "prominence": 9.0,
        },
    ]
    ranked = rank_daily_setups(hits)
    assert [row["pattern"] for row in ranked] == [
        "head_and_shoulders",
        "double_bottom",
        "ascending_triangle",
    ]


def test_double_rejects_span_beyond_max_duration():
    prices = [5.0] * 3 + [3.0] + [5.0] * 70 + [3.0] + [5.0] * 6
    bars = [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]
    hits = detect_patterns(bars, timeframe="day")
    assert "double_bottom" not in {h["pattern"] for h in hits}


def test_intraday_patterns_ignored_without_daily_hit():
    prices = [6, 6, 6, 5, 4, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6] + [6.2 + i * 0.05 for i in range(20)]
    bars = [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]
    hits = collect_pattern_hits({"10minute": bars}, ["10minute", "hour", "day"])
    assert hits == []
    daily_first = collect_pattern_hits({"day": bars, "10minute": bars}, ["10minute", "hour", "day"])
    assert any(h["timeframe"] == "day" for h in daily_first)
    assert any(h["timeframe"] == "10minute" for h in daily_first)
