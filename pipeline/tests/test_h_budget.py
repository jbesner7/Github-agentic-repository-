from datetime import time

from pipeline.h_budget import (
    FLATTEN_FLAT,
    MANAGE,
    OUTSIDE_RTH,
    PRE_WINDOW,
    SCAN,
    WORK_LEASE_ACQUIRE,
    WORK_SCAN,
    allows,
    classify_fire_mode,
    executable_quote_may_be_reused_from_scan,
    historical_budget,
    may_fetch_historicals,
    may_fetch_option_chain,
    may_journal,
    must_acquire_lease,
    on_rate_limit,
    pagination_policy,
)


def test_outside_rth_is_clock_only():
    assert classify_fire_mode(weekday=5, et_time="10:00") == OUTSIDE_RTH
    assert classify_fire_mode(weekday=0, et_time="09:29:59") == OUTSIDE_RTH
    assert classify_fire_mode(weekday=0, et_time="16:00") == OUTSIDE_RTH
    assert allows(OUTSIDE_RTH, WORK_SCAN) is False
    assert must_acquire_lease(OUTSIDE_RTH) is False
    assert may_journal(OUTSIDE_RTH) is False


def test_manage_and_windows_skip_scan_and_lease_acquire():
    assert (
        classify_fire_mode(weekday=0, et_time="10:00", has_option_position=True) == MANAGE
    )
    assert classify_fire_mode(weekday=0, et_time="10:00") == PRE_WINDOW
    assert classify_fire_mode(weekday=0, et_time="09:44") == FLATTEN_FLAT
    assert classify_fire_mode(weekday=0, et_time="15:45") == FLATTEN_FLAT
    for mode in (MANAGE, PRE_WINDOW, FLATTEN_FLAT):
        assert allows(mode, WORK_SCAN) is False
        assert must_acquire_lease(mode) is False
        assert allows(mode, WORK_LEASE_ACQUIRE) is False


def test_leftover_at_flatten_deadline_is_manage_after_exposure():
    assert (
        classify_fire_mode(weekday=0, et_time="15:45", has_option_position=True) == MANAGE
    )
    assert allows(MANAGE, "protect_or_flatten") is True
    assert allows(MANAGE, "take_profit") is True
    assert must_acquire_lease(MANAGE) is False


def test_scan_window_requires_flat_rth_after_1310():
    assert classify_fire_mode(weekday=0, et_time="13:10") == SCAN
    assert classify_fire_mode(weekday=0, et_time=time(15, 44, 59)) == SCAN
    assert classify_fire_mode(weekday=0, et_time="13:10", has_working_order=True) == MANAGE
    assert must_acquire_lease(SCAN) is True
    assert allows(SCAN, WORK_SCAN) is True
    assert may_journal(SCAN) is True


def test_historicals_waterfall_and_budgets():
    assert may_fetch_historicals(MANAGE, "day") is False
    assert may_fetch_historicals(SCAN, "day") is True
    assert may_fetch_historicals(SCAN, "hour", daily_setup=False) is False
    assert may_fetch_historicals(SCAN, "hour", daily_setup=True) is True
    assert may_fetch_historicals(SCAN, "10minute", daily_setup=True, hour_confirmed=False) is False
    assert may_fetch_historicals(SCAN, "10minute", daily_setup=True, hour_confirmed=True) is True
    assert may_fetch_option_chain(live_trigger_ok=False) is False
    assert may_fetch_option_chain(live_trigger_ok=True) is True
    assert historical_budget("day") == 8
    assert historical_budget("hour") == 3
    assert historical_budget("10minute") == 2


def test_pagination_and_quotes_and_rate_limits():
    assert pagination_policy("working_order", found_positive=True) == "stop_after_positive"
    assert pagination_policy("working_order", found_positive=False) == "exhaust_to_conclude_negative"
    assert pagination_policy("account", found_positive=True) == "exhaust_to_conclude_unique"
    assert executable_quote_may_be_reused_from_scan() is False
    assert on_rate_limit(kind="entry") == "journal_rate_limited_no_new_entry"
    assert on_rate_limit(kind="protect") == "retry_once_then_journal_rate_limited"
    assert may_journal(MANAGE, placed_or_cancelled=True) is True
    assert may_journal(MANAGE) is False
