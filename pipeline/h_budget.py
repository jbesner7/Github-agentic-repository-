"""Per-fire work budget for Agent H.

A 15-minute cadence is allowed. Most fires must not pay for a full Git
lease cycle, watchlist pagination, multi-timeframe historicals, or option
review. New-entry safety and leftover protection stay intact.
"""

from __future__ import annotations

from datetime import time
from typing import Any

from pipeline.h_gates import is_emergency_kind


OUTSIDE_RTH = "outside_rth_clock_only"
MANAGE = "manage_exposure"
PRE_WINDOW = "pre_entry_window_no_scan"
FLATTEN_FLAT = "flatten_deadline_flat"
SCAN = "scan_if_flat"

RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)
NO_ENTRY_BEFORE = time(9, 45)
NO_ENTRY_AFTER = time(15, 45)
SCAN_BEGIN = time(13, 10)

MAX_DAILY_HISTORICALS_PER_FIRE = 8
MAX_HOUR_HISTORICALS_PER_FIRE = 3
MAX_TEN_MINUTE_HISTORICALS_PER_FIRE = 2
MAX_OPTION_CHAINS_PER_FIRE = 1

WORK_CLOCK = "clock"
WORK_GIT_LOCK_FILES = "git_lock_files"
WORK_LEASE_READ = "lease_read_only"
WORK_LEASE_ACQUIRE = "lease_acquire"
WORK_ACCOUNT = "account"
WORK_CORE_RECOVERY = "core_recovery"
WORK_FILES = "files"
WORK_EXPOSURE = "exposure"
WORK_PROTECT = "protect_or_flatten"
WORK_BOD = "bod_session"
WORK_REQUIRED_TOOLS = "required_tools"
WORK_SCAN = "waterfall_scan"
WORK_REVIEW_PLACE = "review_place"

_SCAN_WORK = frozenset(
    {
        WORK_CLOCK,
        WORK_GIT_LOCK_FILES,
        WORK_LEASE_READ,
        WORK_LEASE_ACQUIRE,
        WORK_ACCOUNT,
        WORK_CORE_RECOVERY,
        WORK_FILES,
        WORK_EXPOSURE,
        WORK_PROTECT,
        WORK_BOD,
        WORK_REQUIRED_TOOLS,
        WORK_SCAN,
        WORK_REVIEW_PLACE,
    }
)
_MANAGE_WORK = frozenset(
    {
        WORK_CLOCK,
        WORK_GIT_LOCK_FILES,
        WORK_LEASE_READ,
        WORK_ACCOUNT,
        WORK_CORE_RECOVERY,
        WORK_FILES,
        WORK_EXPOSURE,
        WORK_PROTECT,
    }
)
_WATCH_WORK = frozenset(
    {
        WORK_CLOCK,
        WORK_GIT_LOCK_FILES,
        WORK_LEASE_READ,
        WORK_ACCOUNT,
        WORK_CORE_RECOVERY,
        WORK_FILES,
        WORK_EXPOSURE,
    }
)

ALLOWED_WORK = {
    OUTSIDE_RTH: frozenset({WORK_CLOCK}),
    MANAGE: _MANAGE_WORK,
    PRE_WINDOW: _WATCH_WORK,
    FLATTEN_FLAT: _WATCH_WORK,
    SCAN: _SCAN_WORK,
}


def parse_et_time(value: Any) -> time:
    if isinstance(value, time):
        return value
    parts = str(value).strip().split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = int(float(parts[2])) if len(parts) > 2 else 0
    return time(hour, minute, second)


def is_rth(*, weekday: int, et_time: Any) -> bool:
    """weekday is Monday=0, matching datetime.date.weekday()."""
    if int(weekday) >= 5:
        return False
    clock = parse_et_time(et_time)
    return RTH_OPEN <= clock < RTH_CLOSE


def classify_fire_mode(
    *,
    weekday: int,
    et_time: Any,
    has_option_position: bool = False,
    has_working_order: bool = False,
) -> str:
    if not is_rth(weekday=weekday, et_time=et_time):
        return OUTSIDE_RTH
    if has_option_position or has_working_order:
        return MANAGE
    clock = parse_et_time(et_time)
    if clock < NO_ENTRY_BEFORE or clock >= NO_ENTRY_AFTER:
        return FLATTEN_FLAT
    if clock < SCAN_BEGIN:
        return PRE_WINDOW
    return SCAN


def allows(mode: str, work: str) -> bool:
    return work in ALLOWED_WORK.get(mode, frozenset())


def must_acquire_lease(mode: str) -> bool:
    return mode == SCAN


def may_journal(mode: str, *, placed_or_cancelled: bool = False, mismatch: bool = False) -> bool:
    if mode == OUTSIDE_RTH:
        return False
    if placed_or_cancelled or mismatch:
        return True
    return mode == SCAN


def may_fetch_historicals(
    mode: str,
    timeframe: str,
    *,
    daily_setup: bool = False,
    hour_confirmed: bool = False,
) -> bool:
    if mode != SCAN:
        return False
    tf = (timeframe or "").strip().lower()
    if tf in {"day", "daily"}:
        return True
    if tf == "hour":
        return daily_setup
    if tf in {"10minute", "10m"}:
        return daily_setup and hour_confirmed
    return False


def may_fetch_option_chain(*, live_trigger_ok: bool) -> bool:
    return bool(live_trigger_ok)


def historical_budget(timeframe: str) -> int:
    tf = (timeframe or "").strip().lower()
    if tf in {"day", "daily"}:
        return MAX_DAILY_HISTORICALS_PER_FIRE
    if tf == "hour":
        return MAX_HOUR_HISTORICALS_PER_FIRE
    if tf in {"10minute", "10m"}:
        return MAX_TEN_MINUTE_HISTORICALS_PER_FIRE
    return 0


def pagination_policy(kind: str, *, found_positive: bool) -> str:
    """Exhaust only to conclude a negative, or to prove account uniqueness."""
    key = (kind or "").strip().lower()
    if key in {"account", "account_uniqueness", "no_duplicate_account_match"}:
        return "exhaust_to_conclude_unique"
    if found_positive:
        return "stop_after_positive"
    return "exhaust_to_conclude_negative"


def executable_quote_may_be_reused_from_scan() -> bool:
    return False


def on_rate_limit(*, kind: str) -> str:
    if is_emergency_kind(kind):
        return "retry_once_then_journal_rate_limited"
    return "journal_rate_limited_no_new_entry"
