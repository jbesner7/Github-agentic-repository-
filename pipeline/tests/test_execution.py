from datetime import datetime
from zoneinfo import ZoneInfo

from pipeline.execution import (
    build_option_entry_proposal,
    can_place_live,
    load_latest_equity_candidates,
    load_latest_option_candidates,
)

ET = ZoneInfo("America/New_York")
SUNDAY = datetime(2026, 8, 30, 12, 0, tzinfo=ET)
MONDAY_RTH = datetime(2026, 8, 31, 10, 0, tzinfo=ET)


def test_place_blocked_when_playbook_draft():
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=False, h_enabled=False, now=SUNDAY
    )
    assert not ok
    assert reason == "options_playbook_still_draft"


def test_place_blocked_without_confirm():
    ok, reason = can_place_live(
        explicit_confirm=False, playbook_released=True, h_enabled=False, now=SUNDAY
    )
    assert not ok
    assert reason == "missing_explicit_user_confirm"


def test_place_blocked_outside_rth_even_with_confirm():
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=True, now=SUNDAY
    )
    assert not ok
    assert reason == "outside_rth"


def test_place_blocked_after_1545_even_if_h_disabled():
    monday_1545 = datetime(2026, 8, 31, 15, 45, tzinfo=ET)
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=monday_1545
    )
    assert not ok
    assert reason == "no_new_entries_after_1545"


def test_place_blocked_while_h_owns_rth():
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=True, now=MONDAY_RTH
    )
    assert not ok
    assert reason == "h_owns_rth_while_enabled"


def test_place_blocked_before_0945_for_options_even_if_h_disabled():
    monday_0930 = datetime(2026, 8, 31, 9, 30, tzinfo=ET)
    monday_0944 = datetime(2026, 8, 31, 9, 44, 59, tzinfo=ET)
    monday_0945 = datetime(2026, 8, 31, 9, 45, tzinfo=ET)
    blocked, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=monday_0930
    )
    assert not blocked and reason == "no_new_option_entries_before_0945"
    blocked2, reason2 = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=monday_0944
    )
    assert not blocked2 and reason2 == "no_new_option_entries_before_0945"
    ok, ok_reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=monday_0945
    )
    assert ok and ok_reason is None


def test_equity_place_allowed_at_open_if_h_disabled():
    monday_0930 = datetime(2026, 8, 31, 9, 30, tzinfo=ET)
    ok, reason = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=False,
        now=monday_0930,
    )
    assert ok and reason is None


def test_place_allowed_during_rth_if_h_disabled():
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=MONDAY_RTH
    )
    assert ok and reason is None


def test_place_allowed_during_rth_with_override():
    ok, reason = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        h_enabled=True,
        now=MONDAY_RTH,
        h_rth_override=True,
    )
    assert ok and reason is None


def test_proposal_is_one_contract_buy_to_open():
    cand = {
        "symbol": "SOFI",
        "structure": "long_put",
        "expiration": "2026-09-04",
        "option_type": "put",
        "strike": "18.0",
        "option_id": "abc",
        "playbook_status": "DRAFT_NOT_RELEASED",
    }
    p = build_option_entry_proposal(cand, limit_price="0.43")
    assert p["quantity"] == "1"
    assert p["places_order"] is False
    assert p["legs"][0]["side"] == "buy"
    assert p["legs"][0]["position_effect"] == "open"


def test_load_latest_skips_historical_do_not_place(tmp_path, monkeypatch):
    import json

    import pipeline.execution as execution

    monkeypatch.setattr(execution, "SIGNALS", tmp_path)
    (tmp_path / "option_candidates.json").write_text(
        json.dumps(
            {
                "historical": True,
                "do_not_place": True,
                "candidates": [{"symbol": "SOFI"}],
            }
        )
    )
    (tmp_path / "equity_candidates.json").write_text(
        json.dumps({"do_not_place": True, "candidates": [{"symbol": "AAPL"}]})
    )
    assert load_latest_option_candidates() == []
    assert load_latest_equity_candidates() == []

    (tmp_path / "option_candidates.json").write_text(
        json.dumps({"candidates": [{"symbol": "NU"}]})
    )
    assert load_latest_option_candidates()[0]["symbol"] == "NU"
