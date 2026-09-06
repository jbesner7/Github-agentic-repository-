from pipeline.h_gates import (
    CORE_RECOVERY_TOOLS,
    RUN_ORDER_AFTER_LEASE,
    RemoteLease,
    attempt_gtc_stop,
    core_recovery_tools_present,
    may_place_option_order,
    may_try_one_otm,
    must_renew_lease,
    must_reverify_remote_lease_before_place,
    permissions_allow,
    post_lease_priority,
    recovery_action,
    replacement_policy,
    required_stop_time_in_force,
)
from pipeline.patterns import retest_confirms, retest_invalidated


OWNED = RemoteLease(owned_by_this_run=True, expired=False, other_unexpired_holder=False)
EXPIRED_UNOWNED = RemoteLease(owned_by_this_run=False, expired=True, other_unexpired_holder=False)
EXPIRED_OWN_STALE = RemoteLease(owned_by_this_run=True, expired=True, other_unexpired_holder=False)
OTHER_HOLDER = RemoteLease(owned_by_this_run=False, expired=False, other_unexpired_holder=True)
UNREADABLE = RemoteLease(owned_by_this_run=False, expired=True, other_unexpired_holder=False, readable=False)


def test_every_place_requires_valid_remote_lease():
    assert may_place_option_order(OWNED, kind="entry") == (True, "ok")
    assert may_place_option_order(OWNED, kind="protect") == (True, "ok")
    assert may_place_option_order(OWNED, kind="flatten") == (True, "ok")
    assert may_place_option_order(OWNED, kind="take_profit") == (True, "ok")
    assert may_place_option_order(EXPIRED_UNOWNED, kind="take_profit") == (
        True,
        "manage_exit_without_owned_lease",
    )
    assert may_place_option_order(EXPIRED_UNOWNED, kind="take_profit", git_status="outage")[0] is False
    assert may_place_option_order(EXPIRED_UNOWNED, kind="stop_market")[0] is True
    for lease in (EXPIRED_UNOWNED, EXPIRED_OWN_STALE, UNREADABLE):
        ok, reason = may_place_option_order(lease, kind="protect")
        assert ok is True
        assert reason == "emergency_protection_without_owned_lease"
        ok, reason = may_place_option_order(lease, kind="entry")
        assert ok is False
    ok, reason = may_place_option_order(OTHER_HOLDER, kind="protect")
    assert ok is False and reason == "lease_held_after_fill"
    ok, reason = may_place_option_order(OTHER_HOLDER, kind="entry")
    assert ok is False and reason == "lease_held"


def test_recovery_never_places_from_momentary_absent_other_lease():
    assert recovery_action(EXPIRED_UNOWNED, kind="entry") == "reacquire_then_recover"
    assert recovery_action(EXPIRED_OWN_STALE, kind="protect") == "emergency_protect_without_owned_lease"
    assert recovery_action(OTHER_HOLDER) == "place_nothing_new_owner_manages"
    assert recovery_action(OWNED) == "recover_now"
    ok, _reason = may_place_option_order(OTHER_HOLDER, kind="protect")
    assert ok is False


def test_atm_fallback_is_any_contract_rule_but_not_order_checks():
    for reason in (
        "quote_age",
        "bid_ask",
        "sizes",
        "spread",
        "delta",
        "iv",
        "volume",
        "open_interest",
        "tick_validity",
        "debit_cap",
        "fee_cap",
        "buying_power",
    ):
        assert may_try_one_otm(reason) is True
    assert may_try_one_otm("review_order_checks") is False
    assert may_try_one_otm("order_checks") is False


def test_one_replacement_does_not_apply_to_mandatory_liquidation():
    entry = replacement_policy("entry")
    assert entry["max_replacements"] == 1
    tp = replacement_policy("take_profit")
    assert tp["max_replacements"] == 1
    assert tp["interval_seconds"] == 15
    forced = replacement_policy("forced_liquidation")
    assert forced["max_replacements"] is None
    assert forced["interval_seconds"] == 15
    assert forced["until"] == "flat_or_order_entry_close"
    assert replacement_policy("protection_failed")["max_replacements"] is None


def test_inactive_permissions_allow_exits_not_new_entries():
    assert permissions_allow(status="ACTIVE", owner_stop_all_including_exits=False, intent="new_entry")[0] is True
    ok, reason = permissions_allow(status="INACTIVE", owner_stop_all_including_exits=False, intent="new_entry")
    assert ok is False and reason == "inactive_permissions_block_new_entry"
    for intent in ("cancel", "protect", "reduce", "close"):
        ok, reason = permissions_allow(status="INACTIVE", owner_stop_all_including_exits=False, intent=intent)
        assert ok is True and reason == "inactive_permissions_exits_only"
    ok, reason = permissions_allow(status="ACTIVE", owner_stop_all_including_exits=True, intent="close")
    assert ok is False and reason == "owner_revoked_all_order_activity"
    ok, reason = permissions_allow(status="INACTIVE", owner_stop_all_including_exits=False, intent="increase")
    assert ok is False and reason == "inactive_permissions_block_new_entry"
    ok, reason = permissions_allow(status="INACTIVE", owner_stop_all_including_exits=False, intent="unknown")
    assert ok is False and reason == "inactive_permissions_block_increase"


def test_new_owner_exposure_blocks_scan():
    assert post_lease_priority(has_option_position=True, has_working_order=False) == "exposure_only_no_scan"
    assert post_lease_priority(has_option_position=False, has_working_order=True) == "exposure_only_no_scan"
    assert post_lease_priority(has_option_position=False, has_working_order=False) == "may_scan_if_other_gates_pass"
    assert RUN_ORDER_AFTER_LEASE[0] == "account_selection"
    assert RUN_ORDER_AFTER_LEASE[1] == "core_recovery_capability"
    assert RUN_ORDER_AFTER_LEASE[2] == "read_rules_permissions_playbook"
    assert RUN_ORDER_AFTER_LEASE[3] == "exposure_and_working_orders"
    assert RUN_ORDER_AFTER_LEASE[4] == "classify_fire_mode_from_clock_and_exposure"
    assert RUN_ORDER_AFTER_LEASE[5] == "if_exposure_continuity_and_section_8_only"


def test_renew_lease_before_entry_unless_six_minutes_remain():
    assert must_renew_lease(minutes_remaining=6.0, before_entry=True) is False
    assert must_renew_lease(minutes_remaining=5.9, before_entry=True) is True
    assert must_renew_lease(minutes_remaining=5.0, before_entry=False) is False
    assert must_renew_lease(minutes_remaining=2.9, before_entry=False) is True


def test_emergency_protection_does_not_require_git():
    ok, reason = may_place_option_order(UNREADABLE, kind="protect", git_status="outage")
    assert ok is True and reason == "emergency_protection_without_git"
    ok, reason = may_place_option_order(EXPIRED_OWN_STALE, kind="flatten", git_status="timeout")
    assert ok is True
    ok, reason = may_place_option_order(UNREADABLE, kind="entry", git_status="outage")
    assert ok is False
    assert must_reverify_remote_lease_before_place(kind="protect", git_status="outage") is False
    assert must_reverify_remote_lease_before_place(kind="entry", git_status="outage") is True
    assert must_reverify_remote_lease_before_place(kind="protect", git_status="ok") is False
    assert recovery_action(UNREADABLE, git_status="outage", kind="protect") == "emergency_protect_without_owned_lease"
    assert recovery_action(OTHER_HOLDER, git_status="ok", kind="protect") == "place_nothing_new_owner_manages"
    ok, reason = may_place_option_order(OTHER_HOLDER, kind="protect", git_status="outage")
    assert ok is False and reason == "lease_held_after_fill"
    assert recovery_action(OTHER_HOLDER, git_status="outage", kind="protect") == "place_nothing_new_owner_manages"


def test_core_recovery_tools_are_checked_before_full_required_list():
    ok, missing = core_recovery_tools_present(CORE_RECOVERY_TOOLS)
    assert ok is True and missing == ()
    ok, missing = core_recovery_tools_present(["get_accounts", "get_option_positions"])
    assert ok is False
    assert "cancel_option_order" in missing
    assert "get_realized_pnl" not in CORE_RECOVERY_TOOLS


def test_do_not_attempt_gtc_on_this_connection():
    assert attempt_gtc_stop() is False
    assert required_stop_time_in_force() == "gfd"
    assert attempt_gtc_stop(schema_confirms_gtc=True) is True


def test_bullish_retest_requires_low_in_zone_and_close_above():
    level = 100.0
    ok, reason = retest_confirms(
        {"high": 100.40, "low": 99.90, "close": 100.20},
        level,
        bias="bullish",
    )
    assert ok is True and reason is None
    miss_low, miss_reason = retest_confirms(
        {"high": 101.00, "low": 100.50, "close": 100.80},
        level,
        bias="bullish",
    )
    assert miss_low is False and miss_reason == "retest_low_missed_zone"
    through, through_reason = retest_confirms(
        {"high": 100.10, "low": 99.80, "close": 99.70},
        level,
        bias="bullish",
    )
    assert through is False and through_reason == "retest_invalidated_close_through_level"
    assert retest_invalidated({"close": 99.90}, level, bias="bullish") is True


def test_bearish_retest_requires_high_in_zone_and_close_below():
    level = 100.0
    ok, reason = retest_confirms(
        {"high": 100.10, "low": 99.60, "close": 99.80},
        level,
        bias="bearish",
    )
    assert ok is True and reason is None
    miss_high, miss_reason = retest_confirms(
        {"high": 99.50, "low": 99.10, "close": 99.20},
        level,
        bias="bearish",
    )
    assert miss_high is False and miss_reason == "retest_high_missed_zone"
    through, through_reason = retest_confirms(
        {"high": 100.40, "low": 99.90, "close": 100.20},
        level,
        bias="bearish",
    )
    assert through is False and through_reason == "retest_invalidated_close_through_level"
