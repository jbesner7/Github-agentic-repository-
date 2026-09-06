from pipeline.h_attention import after_classify, in_scope_sections
from pipeline.h_budget import MANAGE, OUTSIDE_RTH, SCAN
from pipeline.h_dispatch import (
    HELPER_UNAVAILABLE,
    fire_card,
    format_card,
    leftover_card,
    may_place,
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
