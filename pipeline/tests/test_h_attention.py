from pipeline.h_attention import (
    SCAN_ONLY_SECTIONS,
    SEC_BOD,
    SEC_ENTRY,
    SEC_EXITS,
    SEC_LEASE_ACQUIRE,
    SEC_PATTERNS,
    after_classify,
    in_scope_sections,
    leftover_take_profit_allowed,
    may_execute_section,
    place_authority,
)
from pipeline.h_budget import FLATTEN_FLAT, MANAGE, OUTSIDE_RTH, PRE_WINDOW, SCAN, allows
from pipeline.h_closer import ORDERS_INCOMPLETE, decide_emergency_close
from pipeline.h_gates import RemoteLease


OWNED = RemoteLease(owned_by_this_run=True, expired=False, other_unexpired_holder=False)
EXPIRED = RemoteLease(owned_by_this_run=True, expired=True, other_unexpired_holder=False)
OTHER = RemoteLease(owned_by_this_run=False, expired=False, other_unexpired_holder=True)


def test_manage_fire_cannot_execute_scan_or_entry_sections():
    for section in SCAN_ONLY_SECTIONS:
        assert may_execute_section(MANAGE, section) is False
    assert may_execute_section(MANAGE, SEC_EXITS) is True
    assert may_execute_section(MANAGE, SEC_PATTERNS) is False
    assert may_execute_section(MANAGE, SEC_ENTRY) is False
    assert may_execute_section(MANAGE, SEC_BOD) is False
    assert after_classify(MANAGE) == "execute_continuity_and_section_8_only"
    assert leftover_take_profit_allowed(MANAGE, other_holder=False) is True
    assert leftover_take_profit_allowed(MANAGE, other_holder=True) is False
    assert leftover_take_profit_allowed(SCAN, other_holder=False) is False
    ok, reason = place_authority(kind="take_profit", lease=EXPIRED)
    assert ok is True and reason == "manage_exit_without_owned_lease"
    assert place_authority(kind="take_profit", lease=EXPIRED, git_status="outage")[0] is False
    assert place_authority(kind="take_profit", lease=OTHER)[0] is False
    assert place_authority(
        kind="take_profit", lease=EXPIRED, permissions_status="INACTIVE"
    )[0] is True
    assert place_authority(kind="stop_market", lease=EXPIRED)[0] is True


def test_scan_only_and_outside_rth_scopes():
    assert SEC_LEASE_ACQUIRE in in_scope_sections(SCAN)
    assert SEC_LEASE_ACQUIRE not in in_scope_sections(PRE_WINDOW)
    assert SEC_LEASE_ACQUIRE not in in_scope_sections(FLATTEN_FLAT)
    assert in_scope_sections(OUTSIDE_RTH) == frozenset({"A"})
    assert after_classify(PRE_WINDOW) == "exposure_only_no_scan"
    assert after_classify(SCAN) == "acquire_then_scan"
    assert allows(MANAGE, "take_profit") is True
    assert allows(PRE_WINDOW, "take_profit") is False


def test_place_authority_schema_and_helper_and_incomplete_orders():
    assert place_authority(kind="flatten", lease=EXPIRED, schema_ok=False) == (
        False,
        "rules_prompt_mismatch",
    )
    assert place_authority(kind="flatten", lease=EXPIRED, helper_available=False) == (
        False,
        "emergency_ref_id_unavailable",
    )
    assert place_authority(kind="flatten", lease=EXPIRED, orders_complete=False) == (
        False,
        "orders_incomplete",
    )
    ok, reason = place_authority(kind="flatten", lease=EXPIRED, git_status="ok")
    assert ok is True and reason == "emergency_protection_without_owned_lease"
    assert place_authority(kind="flatten", lease=OTHER)[0] is False
    assert place_authority(kind="entry", lease=OWNED) == (True, "ok")
    assert place_authority(kind="entry", lease=EXPIRED)[0] is False
    assert place_authority(kind="protect", lease=OWNED, automation_enabled=False)[0] is False


def test_incomplete_orders_do_not_place_a_closer():
    plan = decide_emergency_close(
        option_id="opt-a",
        position_quantity=1,
        option_orders=[],
        session_date_et="2026-09-08",
        orders_complete=False,
    )
    assert plan["action"] == "skip" and plan["reason"] == ORDERS_INCOMPLETE
    complete = decide_emergency_close(
        option_id="opt-a",
        position_quantity=1,
        option_orders=[],
        session_date_et="2026-09-08",
        orders_complete=True,
    )
    assert complete["action"] == "place"
