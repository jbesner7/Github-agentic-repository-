from pipeline.greeks import delta_in_band, extract_greeks
from pipeline.options_structure import filter_expirations, pick_atm_or_one_otm
from pipeline.patterns import detect_patterns
from pipeline.risk import equity_risk_plan, options_risk_plan
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


def test_option_spread_gate():
    preferred, reason, pref_m = option_quote_liquid(
        {"bid_price": "1.00", "ask_price": "1.05"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert preferred and reason is None
    assert pref_m["spread_quality"] == "preferred"

    acceptable, reason_ok, acc_m = option_quote_liquid(
        {"bid_price": "1.00", "ask_price": "1.08"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert acceptable and reason_ok is None
    assert acc_m["spread_quality"] == "acceptable"

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
    ok, _ = delta_in_band(0.45, lo=0.4, hi=0.5)
    assert ok
    bad, reason = delta_in_band(0.9, lo=0.4, hi=0.5)
    assert not bad and reason is not None


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
    exps = filter_expirations(["2099-01-01", "2026-09-02"], max_dte=7, as_of=__import__("datetime").date(2026, 8, 30))
    assert exps == ["2026-09-02"]
