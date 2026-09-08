import json

from pipeline.h_attention import after_classify, in_scope_sections
from pipeline.h_budget import MANAGE, OUTSIDE_RTH, SCAN
from pipeline.h_dispatch import (
    HELPER_UNAVAILABLE,
    bod_card,
    fire_card,
    format_card,
    leftover_card,
    may_place,
    resolve_fills_today,
)


def test_manage_card_forbids_scan_and_acquire():
    card = fire_card(weekday=0, et_time="14:00", leftover=True, other_holder=False)
    assert card["mode"] == MANAGE
    assert card["next"] == "execute_continuity_and_section_8_only"
    assert card["scan"] is False
    assert card["acquire_lease"] is False
    assert card["take_profit"] is True
    assert "7" not in card["sections"]
    assert "8" in card["sections"]
    text = format_card(card)
    assert "scan=false" in text
    assert "acquire_lease=false" in text


def test_scan_card_only_when_flat_in_window():
    card = fire_card(weekday=0, et_time="13:15", leftover=False)
    assert card["mode"] == SCAN
    assert card["scan"] is True
    assert card["acquire_lease"] is True
    assert card["next"] == after_classify(SCAN)
    assert set(card["sections"]) == in_scope_sections(SCAN)


def test_outside_rth_is_clock_only():
    card = fire_card(weekday=6, et_time="14:00", leftover=True)
    assert card["mode"] == OUTSIDE_RTH
    assert card["next"] == "exit_clock_only"
    assert card["scan"] is False
    assert card["sections"] == ("A",)


def test_helper_failure_is_fail_closed():
    leftover = fire_card(weekday=0, et_time="14:00", leftover=True, helper_ok=False)
    assert leftover["mode"] == HELPER_UNAVAILABLE
    assert leftover["scan"] is False
    assert leftover["take_profit"] is False
    assert leftover["next"] == "continuity_and_section_8_if_leftover_else_exit"
    flat = fire_card(weekday=0, et_time="14:00", leftover=False, helper_ok=False)
    assert flat["scan"] is False
    assert flat["sections"] == ("A",)


def test_other_holder_blocks_take_profit_on_card():
    card = fire_card(weekday=0, et_time="14:00", leftover=True, other_holder=True)
    assert card["take_profit"] is False


def test_may_place_matches_attention_table():
    ok, reason = may_place(
        kind="take_profit",
        owned=False,
        expired=True,
        other_holder=False,
    )
    assert ok is True and reason == "manage_exit_without_owned_lease"
    assert may_place(kind="take_profit", owned=False, expired=True, other_holder=True)[0] is False
    assert may_place(
        kind="take_profit",
        owned=False,
        expired=True,
        other_holder=False,
        git_status="outage",
    )[0] is False
    assert may_place(kind="entry", owned=False, expired=True, other_holder=False)[0] is False
    assert may_place(
        kind="take_profit",
        owned=False,
        expired=True,
        other_holder=False,
        orders_complete=False,
    ) == (False, "orders_incomplete")
    assert may_place(
        kind="entry",
        owned=True,
        expired=False,
        other_holder=False,
        orders_complete=False,
    ) == (False, "orders_incomplete")


def test_leftover_card_uses_closer():
    plan = leftover_card(
        option_id="opt-a",
        position_quantity=1,
        option_orders=[],
        session_date_et="2026-09-08",
    )
    assert plan["action"] == "place"
    blocked = leftover_card(
        option_id="opt-a",
        position_quantity=1,
        option_orders=[],
        session_date_et="2026-09-08",
        orders_complete=False,
    )
    assert blocked["action"] == "skip"
    covering = {
        "option_id": "opt-a",
        "state": "queued",
        "side": "sell",
        "position_effect": "close",
        "quantity": 1,
        "filled_quantity": 0,
    }
    wrapped = leftover_card(
        option_id="opt-a",
        position_quantity=1,
        option_orders=json.dumps({"data": {"orders": [covering]}}),
        session_date_et="2026-09-08",
    )
    assert wrapped["action"] == "monitor"
    single = leftover_card(
        option_id="opt-a",
        position_quantity=1,
        option_orders=json.dumps(covering),
        session_date_et="2026-09-08",
    )
    assert single["action"] == "monitor"
    unknown = leftover_card(
        option_id="opt-a",
        position_quantity=1,
        option_orders=json.dumps({"next": "cursor"}),
        session_date_et="2026-09-08",
    )
    assert unknown["action"] == "skip"
    broken = leftover_card(
        option_id="opt-a",
        position_quantity=1,
        option_orders="{not-json",
        session_date_et="2026-09-08",
    )
    assert broken["action"] == "skip"


def test_bod_card_accepts_live_mcp_flat_cash_when_no_fills():
    payload = {
        "data": {
            "total_value": "1500",
            "cash": "1500",
            "pending_deposits": "0",
            "buying_power": {"buying_power": "1500.0000"},
        }
    }
    empty = {"data": {"orders": []}}
    session = "2026-09-08"
    ok = bod_card(
        portfolio=payload,
        leftover=False,
        option_orders=empty,
        equity_orders=[],
        session_date_et=session,
    )
    assert ok["reason"] == "ok"
    assert ok["bod_nlv"] == 1500.0
    assert ok["bod_nlv_field"] == "flat_no_fills_cash_equals_total_value"
    leftover = bod_card(
        portfolio=payload,
        leftover=True,
        option_orders=[],
        equity_orders=[],
        session_date_et=session,
    )
    assert leftover["reason"] == "bod_nlv_unavailable"
    mismatch = bod_card(
        portfolio={"cash": "1500", "total_value": "1512"},
        leftover=False,
        option_orders=[],
        equity_orders=[],
        session_date_et=session,
    )
    assert mismatch["reason"] == "bod_nlv_unavailable"
    broker = bod_card(
        portfolio={"data": {"start_of_day_equity": "1490.00", "total_value": "1512"}},
        leftover=False,
        option_orders=[],
        equity_orders=[],
        session_date_et=session,
        orders_complete=False,
    )
    assert broker["bod_nlv"] == 1490.0
    assert broker["bod_nlv_field"] == "start_of_day_equity"
    broken = bod_card(
        portfolio="{not-json",
        leftover=False,
        option_orders=[],
        equity_orders=[],
        session_date_et=session,
    )
    assert broken["reason"] == "bod_nlv_unavailable"


def test_bod_card_derives_fills_from_broker_orders():
    payload = {"cash": "1540", "total_value": "1540", "pending_deposits": "0"}
    session = "2026-09-08"
    filled_option = {
        "id": "opt-fill",
        "state": "filled",
        "filled_quantity": 1,
        "created_at": "2026-09-08T14:22:00Z",
    }
    winner = bod_card(
        portfolio=payload,
        leftover=False,
        option_orders=json.dumps({"data": {"orders": [filled_option]}}),
        equity_orders=[],
        session_date_et=session,
    )
    assert winner["reason"] == "bod_nlv_unavailable"
    equity_fill = {
        "id": "eq-fill",
        "state": "filled",
        "processed_quantity": "1",
        "created_at": "2026-09-08T15:01:00Z",
    }
    shares = bod_card(
        portfolio=payload,
        leftover=False,
        option_orders=[],
        equity_orders=[equity_fill],
        session_date_et=session,
    )
    assert shares["reason"] == "bod_nlv_unavailable"
    cancelled = {
        "id": "opt-cxl",
        "state": "cancelled",
        "filled_quantity": 0,
        "created_at": "2026-09-08T14:00:00Z",
    }
    no_fill = bod_card(
        portfolio=payload,
        leftover=False,
        option_orders=[cancelled],
        equity_orders=[],
        session_date_et=session,
    )
    assert no_fill["reason"] == "ok"
    yesterday = {
        "id": "opt-old",
        "state": "filled",
        "filled_quantity": 1,
        "created_at": "2026-09-07T20:00:00Z",
    }
    prior = bod_card(
        portfolio=payload,
        leftover=False,
        option_orders=[yesterday],
        equity_orders=[],
        session_date_et=session,
    )
    assert prior["reason"] == "ok"
    incomplete = bod_card(
        portfolio=payload,
        leftover=False,
        option_orders=[],
        equity_orders=[],
        session_date_et=session,
        orders_complete=False,
    )
    assert incomplete["reason"] == "bod_nlv_unavailable"
    missing = bod_card(
        portfolio=payload,
        leftover=False,
        option_orders=None,
        equity_orders=[],
        session_date_et=session,
    )
    assert missing["reason"] == "bod_nlv_unavailable"
    unknown = bod_card(
        portfolio=payload,
        leftover=False,
        option_orders=json.dumps({"next": "cursor"}),
        equity_orders=[],
        session_date_et=session,
    )
    assert unknown["reason"] == "bod_nlv_unavailable"
    broker_after_fill = bod_card(
        portfolio={"start_of_day_equity": "1500.00", "total_value": "1540"},
        leftover=False,
        option_orders=[filled_option],
        equity_orders=[],
        session_date_et=session,
    )
    assert broker_after_fill["bod_nlv"] == 1500.0
    assert broker_after_fill["bod_nlv_field"] == "start_of_day_equity"
    fills, reason = resolve_fills_today(
        option_orders=[filled_option],
        equity_orders=[],
        session_date_et=session,
    )
    assert fills is True and reason == "fill_present"
