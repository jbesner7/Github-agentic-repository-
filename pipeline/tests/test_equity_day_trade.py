from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pipeline.equity_day_trade import (
    equity_quote_ok,
    is_inverse_etf,
    regular_hours_buy_ok,
    select_equity_day_trade_candidates,
    whole_share_size,
)
from pipeline.execution import build_equity_entry_proposal, can_place_live
from pipeline.risk import equity_risk_plan
from pipeline.session import (
    ET,
    entries_open,
    flatten_window,
    is_rth,
    option_entries_open,
    session_gate,
)


def test_session_rth_and_1545_cutoff():
    sunday_noon = datetime(2026, 8, 30, 12, 0, tzinfo=ET)
    monday_open = datetime(2026, 8, 31, 9, 30, tzinfo=ET)
    monday_morning = datetime(2026, 8, 31, 10, 0, tzinfo=ET)
    monday_1545 = datetime(2026, 8, 31, 15, 45, tzinfo=ET)
    monday_close = datetime(2026, 8, 31, 16, 0, tzinfo=ET)
    monday_pre = datetime(2026, 8, 31, 9, 29, tzinfo=ET)

    assert not is_rth(sunday_noon)
    assert is_rth(monday_open)
    assert is_rth(monday_morning)
    assert entries_open(monday_open)
    assert not option_entries_open(monday_open)
    assert entries_open(monday_morning)
    assert option_entries_open(monday_morning)
    assert is_rth(monday_1545)
    assert not entries_open(monday_1545)
    assert not option_entries_open(monday_1545)
    assert flatten_window(monday_1545)
    assert not is_rth(monday_close)
    assert not is_rth(monday_pre)
    gate = session_gate(monday_1545)
    assert gate["reason"] == "no_new_entries_after_1545"
    assert gate["option_reason"] == "no_new_entries_after_1545"
    open_gate = session_gate(monday_open)
    assert open_gate["entries_open"] is True
    assert open_gate["option_entries_open"] is False
    assert open_gate["option_reason"] == "no_new_option_entries_before_0945"


def test_whole_share_size_uses_floor_and_buying_power_cap():
    sized = whole_share_size(1500.0, 347.5)
    assert sized["ok"] is True
    assert sized["shares"] == 4
    assert sized["notional"] == 1390.0
    unaffordable = whole_share_size(1500.0, 1975.0)
    assert unaffordable["ok"] is False
    assert unaffordable["reason"] == "cannot_afford_one_share"
    assert whole_share_size(0, 10)["ok"] is False


def test_no_shorting_skips_bearish_and_inverse_etfs():
    assert is_inverse_etf("SQQQ") is True
    assert is_inverse_etf("SPY") is False
    assert is_inverse_etf("XYZ", {"description": "ProShares UltraShort Inverse"}) is True
    assert is_inverse_etf("QID", {"name": "ProShares UltraShort QQQ"}) is True
    assert is_inverse_etf("BIL", {"description": "SPDR Bloomberg 1-3 Month T-Bill Ultra Short Duration"}) is False

    cands, rejected = select_equity_day_trade_candidates(
        symbols=["SQQQ", "AMD", "AAPL"],
        technicals_by_symbol={
            "SQQQ": {"dominant_bias": "bullish"},
            "AMD": {"dominant_bias": "bearish"},
            "AAPL": {"dominant_bias": "bullish"},
        },
        option_candidate_symbols=set(),
        quotes_by_symbol={
            "AAPL": {"bid_price": "100", "ask_price": "100.10"},
            "AMD": {"bid_price": "50", "ask_price": "50.05"},
            "SQQQ": {"bid_price": "10", "ask_price": "10.02"},
        },
        tradability_by_symbol={
            "AAPL": {"regular_hours": {"buy": True}},
            "AMD": {"regular_hours": {"buy": True}},
            "SQQQ": {"regular_hours": {"buy": True}},
        },
        fundamentals_by_symbol={},
        buying_power=1500.0,
        playbook_status="RELEASED",
        take_profit_pct=0.25,
        stop_loss_pct=0.2,
    )
    reasons = {row["symbol"]: row["reason"] for row in rejected}
    assert reasons["SQQQ"] == "inverse_etf"
    assert reasons["AMD"] == "equity_long_only_requires_bullish"
    assert [c["symbol"] for c in cands] == ["AAPL"]
    assert cands[0]["side"] == "buy"
    assert cands[0]["quantity"] == 14  # floor(1500 / 100.10)


def test_options_priority_and_quote_gates():
    cands, rejected = select_equity_day_trade_candidates(
        symbols=["GOOGL", "META"],
        technicals_by_symbol={
            "GOOGL": {"dominant_bias": "bullish"},
            "META": {"dominant_bias": "bullish"},
        },
        option_candidate_symbols={"GOOGL"},
        quotes_by_symbol={"META": {"bid_price": "0", "ask_price": "350"}},
        tradability_by_symbol={
            "GOOGL": {"regular_hours": {"buy": True}},
            "META": {"regular_hours": {"buy": True}},
        },
        fundamentals_by_symbol={},
        buying_power=1500.0,
        playbook_status="RELEASED",
        take_profit_pct=0.25,
        stop_loss_pct=0.2,
    )
    reasons = {row["symbol"]: row["reason"] for row in rejected}
    assert reasons["GOOGL"] == "options_priority"
    assert reasons["META"] == "one_sided_or_missing_quote"
    assert cands == []


def test_equity_quote_and_tradability_parsers():
    ok, reason, metrics = equity_quote_ok({"bid_price": "10", "ask_price": "10.05"})
    assert ok and reason is None and metrics["ask"] == 10.05
    bad, bad_reason, _ = equity_quote_ok({"bid_price": "10", "ask_price": "0"})
    assert not bad and bad_reason == "one_sided_or_missing_quote"
    assert regular_hours_buy_ok({"regular_hours": {"buy": True}}) == (True, None)
    assert regular_hours_buy_ok(None)[0] is False
    assert regular_hours_buy_ok({"halted": True})[0] is False


def test_equity_risk_prices_from_limit():
    plan = equity_risk_plan(cost_basis=1000.0, shares=10, limit_price=100.0)
    assert plan["take_profit_value"] == 1250.0
    assert plan["stop_loss_value"] == 800.0
    assert plan["stop_price"] == 80.0
    assert plan["take_profit_price"] == 125.0
    assert plan["side"] == "long_only"


def test_equity_place_gate_and_proposal_is_buy_only():
    sunday = datetime(2026, 8, 30, 12, 0, tzinfo=ZoneInfo("America/New_York"))
    monday = datetime(2026, 8, 31, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    ok, reason = can_place_live(
        explicit_confirm=True,
        playbook_released=False,
        playbook_kind="equity",
        h_enabled=False,
        now=sunday,
    )
    assert not ok and reason == "equity_playbook_still_draft"
    ok2, reason2 = can_place_live(
        explicit_confirm=False,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=False,
        now=sunday,
    )
    assert not ok2 and reason2 == "missing_explicit_user_confirm"
    sunday_blocked, sunday_reason = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=False,
        now=sunday,
    )
    assert not sunday_blocked and sunday_reason == "outside_rth"
    ok3, reason3 = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=False,
        now=monday,
    )
    assert ok3 and reason3 is None
    blocked, blocked_reason = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=True,
        now=monday,
    )
    assert not blocked and blocked_reason == "h_owns_rth_while_enabled"

    proposal = build_equity_entry_proposal(
        {
            "symbol": "AAPL",
            "quantity": 4,
            "limit_price": 100.0,
            "playbook_status": "RELEASED",
            "risk": {"stop_loss_pct": 0.2, "take_profit_pct": 0.25},
        }
    )
    assert proposal["side"] == "buy"
    assert proposal["action"] == "buy_to_open"
    assert proposal["quantity"] == "4"
    assert proposal["places_order"] is False
    assert proposal["market_hours"] == "regular_hours"
    assert proposal["stop_price_after_fill"] == 80.0
    assert proposal["take_profit_price"] == 125.0


def test_pipeline_writes_equity_candidate_without_placing(tmp_path, monkeypatch):
    import json

    import pipeline.orchestrator as orch

    signals = tmp_path / "signals"
    journal = tmp_path / "journal"
    signals.mkdir()
    journal.mkdir()
    monkeypatch.setattr(orch, "SIGNALS", signals)
    monkeypatch.setattr(orch, "JOURNAL", journal)

    prices = [6, 6, 6, 5, 4, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6] + [6.2 + i * 0.05 for i in range(20)]
    bars = [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"day": bars}},
        "buying_power": 1500.0,
        "equity_quotes_by_symbol": {"AAPL": {"bid_price": "100.00", "ask_price": "100.10"}},
        "equity_tradability_by_symbol": {"AAPL": {"regular_hours": {"buy": True}}},
    }
    summary = orch.run_pipeline(raw)
    assert summary["places_orders"] is False
    assert summary["option_candidate_count"] == 0
    assert summary["equity_candidate_count"] == 1
    payload = json.loads((signals / "equity_candidates.json").read_text())
    assert payload["do_not_place"] is True
    assert payload["h_entry_ready"] is False
    assert payload["agent_h_may_use"] is False
    assert summary["h_entry_ready"] is False
    cand = payload["candidates"][0]
    assert cand["symbol"] == "AAPL"
    assert cand["side"] == "buy"
    assert cand["structure"] == "long_shares"
    assert cand["quantity"] == 14
    assert cand["playbook_status"] == "RELEASED"


def _double_bottom_bars():
    prices = [6, 6, 6, 5, 4, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6] + [6.2 + i * 0.05 for i in range(20)]
    return [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]


def _pipeline_dirs(tmp_path, monkeypatch):
    import pipeline.orchestrator as orch

    signals = tmp_path / "signals"
    journal = tmp_path / "journal"
    signals.mkdir()
    journal.mkdir()
    monkeypatch.setattr(orch, "SIGNALS", signals)
    monkeypatch.setattr(orch, "JOURNAL", journal)
    return orch, signals, journal


def test_intraday_only_bars_do_not_create_equity_bias(tmp_path, monkeypatch):
    import json

    orch, signals, _journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"10minute": bars}},
        "buying_power": 1500.0,
        "equity_quotes_by_symbol": {"AAPL": {"bid_price": "100.00", "ask_price": "100.10"}},
        "equity_tradability_by_symbol": {"AAPL": {"regular_hours": {"buy": True}}},
    }
    summary = orch.run_pipeline(raw)
    assert summary["equity_candidate_count"] == 0
    payload = json.loads((signals / "equity_candidates.json").read_text())
    reasons = {row["symbol"]: row["reason"] for row in payload["rejected"]}
    assert reasons["AAPL"] == "equity_long_only_requires_bullish"


def test_option_candidate_uses_mid_and_falls_back_to_one_otm(tmp_path, monkeypatch):
    import json
    from datetime import timedelta

    from pipeline.session import today_et

    orch, signals, journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    exp = (today_et() + timedelta(days=3)).isoformat()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"day": bars}},
        "buying_power": 1500.0,
        "spots_by_symbol": {"AAPL": 100.0},
        "option_chains_by_symbol": {"AAPL": {"expiration_dates": [exp]}},
        "option_instruments_by_symbol_exp": {
            f"AAPL|{exp}": [
                {"id": "atm", "type": "call", "strike_price": "100"},
                {"id": "otm", "type": "call", "strike_price": "105"},
                {"id": "itm", "type": "call", "strike_price": "95"},
            ]
        },
        "option_quotes_by_id": {
            "atm": {
                "bid_price": "2.00",
                "ask_price": "2.10",
                "delta": "0.55",
                "mark_price": "9.99",
            },
            "otm": {
                "bid_price": "1.00",
                "ask_price": "1.05",
                "delta": "0.45",
                "mark_price": "9.99",
            },
        },
        "equity_quotes_by_symbol": {"AAPL": {"bid_price": "100.00", "ask_price": "100.10"}},
        "equity_tradability_by_symbol": {"AAPL": {"regular_hours": {"buy": True}}},
    }
    summary = orch.run_pipeline(raw)
    assert summary["option_candidate_count"] == 1
    assert summary["equity_candidate_count"] == 0
    payload = json.loads((signals / "option_candidates.json").read_text())
    cand = payload["candidates"][0]
    assert cand["option_id"] == "otm"
    assert cand["selection"] == "one_otm"
    assert cand["premium_mark"] == pytest.approx(1.025)
    assert cand["premium_source"] == "mid"
    assert cand["cash_debit"] == pytest.approx(102.5)
    assert payload["do_not_place"] is True
    assert payload["h_entry_ready"] is False
    assert "hour_confirm" in payload["h_still_requires"]
    assert (journal / f"{today_et().isoformat()}.md").exists()


def test_inverse_etf_never_becomes_option_candidate(tmp_path, monkeypatch):
    import json
    from datetime import timedelta

    from pipeline.session import today_et

    orch, signals, _journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    exp = (today_et() + timedelta(days=3)).isoformat()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "SQQQ"}]},
        "fundamentals_by_symbol": {
            "SQQQ": {"average_volume": 20_000_000, "name": "ProShares UltraPro Short QQQ"}
        },
        "historicals_by_symbol_timeframe": {"SQQQ": {"day": bars}},
        "buying_power": 1500.0,
        "spots_by_symbol": {"SQQQ": 10.0},
        "option_chains_by_symbol": {"SQQQ": {"expiration_dates": [exp]}},
        "option_instruments_by_symbol_exp": {
            f"SQQQ|{exp}": [
                {"id": "atm", "type": "call", "strike_price": "10"},
                {"id": "otm", "type": "call", "strike_price": "11"},
            ]
        },
        "option_quotes_by_id": {
            "atm": {"bid_price": "1.00", "ask_price": "1.05", "delta": "0.45"},
        },
        "portfolio": {"start_of_day_equity": "1500.00", "total_value": "1512"},
    }
    summary = orch.run_pipeline(raw)
    assert summary["option_candidate_count"] == 0
    assert summary["equity_candidate_count"] == 0
    assert "SQQQ" not in summary["eligible_equities"]
    assert summary["bod_nlv"] == 1500.0
    assert summary["bod_nlv_field"] == "start_of_day_equity"
    universe = json.loads((signals / "universe.json").read_text())
    reasons = {row["symbol"]: row["reason"] for row in universe["liquidity"]["rejected"]}
    assert reasons["SQQQ"] == "inverse_etf"


def test_option_candidate_rejects_debit_above_buying_power(tmp_path, monkeypatch):
    import json
    from datetime import timedelta

    from pipeline.session import today_et

    orch, signals, _journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    exp = (today_et() + timedelta(days=3)).isoformat()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"day": bars}},
        "buying_power": 1500.0,
        "spots_by_symbol": {"AAPL": 100.0},
        "option_chains_by_symbol": {"AAPL": {"expiration_dates": [exp]}},
        "option_instruments_by_symbol_exp": {
            f"AAPL|{exp}": [
                {"id": "atm", "type": "call", "strike_price": "100"},
            ]
        },
        "option_quotes_by_id": {
            "atm": {"bid_price": "19.50", "ask_price": "20.50", "delta": "0.45"},
        },
        "equity_quotes_by_symbol": {"AAPL": {"bid_price": "100.00", "ask_price": "100.10"}},
        "equity_tradability_by_symbol": {"AAPL": {"regular_hours": {"buy": True}}},
    }
    summary = orch.run_pipeline(raw)
    assert summary["option_candidate_count"] == 0
    payload = json.loads((signals / "option_candidates.json").read_text())
    reasons = {row["symbol"]: row["reason"] for row in payload["equity_fallbacks"]}
    assert reasons["AAPL"] == "exceeds_buying_power"


def test_incomplete_option_page_is_rejected(tmp_path, monkeypatch):
    import json
    from datetime import timedelta

    from pipeline.session import today_et

    orch, signals, _journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    exp = (today_et() + timedelta(days=3)).isoformat()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"day": bars}},
        "buying_power": 1500.0,
        "spots_by_symbol": {"AAPL": 200.0},
        "option_chains_by_symbol": {"AAPL": {"expiration_dates": [exp]}},
        "option_instruments_by_symbol_exp": {
            f"AAPL|{exp}": [{"id": "far", "type": "call", "strike_price": "100"}]
        },
        "option_quotes_by_id": {
            "far": {"bid_price": "1.00", "ask_price": "1.05", "delta": "0.45"},
        },
    }
    summary = orch.run_pipeline(raw)
    assert summary["option_candidate_count"] == 0
    payload = json.loads((signals / "option_candidates.json").read_text())
    reasons = {row["symbol"]: row["reason"] for row in payload["equity_fallbacks"]}
    assert reasons["AAPL"] == "option_chain_incomplete_atm_not_in_page"
