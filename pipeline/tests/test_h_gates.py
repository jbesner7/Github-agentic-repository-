from pipeline.h_gates import (
    RemoteLease,
    attempt_gtc_stop,
    may_place_option_order,
    may_try_one_otm,
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
    for lease in (EXPIRED_UNOWNED, EXPIRED_OWN_STALE):
        ok, reason = may_place_option_order(lease, kind="protect")
        assert ok is False
        assert reason == "lease_must_reacquire_before_place"
    ok, reason = may_place_option_order(OTHER_HOLDER, kind="protect")
    assert ok is False and reason == "lease_held_after_fill"
    ok, reason = may_place_option_order(UNREADABLE, kind="flatten")
    assert ok is False and reason == "lease_unreadable"


def test_recovery_never_places_from_momentary_absent_other_lease():
    assert recovery_action(EXPIRED_UNOWNED) == "reacquire_then_recover"
    assert recovery_action(EXPIRED_OWN_STALE) == "reacquire_then_recover"
    assert recovery_action(OTHER_HOLDER) == "place_nothing_new_owner_manages"
    assert recovery_action(OWNED) == "recover_now"


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


def test_new_owner_exposure_blocks_scan():
    assert post_lease_priority(has_option_position=True, has_working_order=False) == "exposure_only_no_scan"
    assert post_lease_priority(has_option_position=False, has_working_order=True) == "exposure_only_no_scan"
    assert post_lease_priority(has_option_position=False, has_working_order=False) == "may_scan_if_other_gates_pass"


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
