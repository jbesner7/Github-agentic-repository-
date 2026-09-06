"""Mode-gated attention for a long Agent H prompt.

The prompt interlocks clock → Git → lease → account → exposure → mode →
gates → scan → options → order machine. A leftover fire must not execute
scan/entry sections. This module is the lock: prompt text must match.
"""

from __future__ import annotations

from pipeline.h_budget import (
    FLATTEN_FLAT,
    MANAGE,
    OUTSIDE_RTH,
    PRE_WINDOW,
    SCAN,
)
from pipeline.h_gates import (
    RemoteLease,
    is_emergency_kind,
    is_manage_exit_kind,
    may_place_option_order,
    permissions_allow,
)


SEC_CLOCK = "A"
SEC_GIT = "A2"
SEC_SESSION = "A3"
SEC_LEASE_READ = "A4_read"
SEC_LEASE_ACQUIRE = "A4_acquire"
SEC_ACCOUNT = "A4.5"
SEC_FILES = "C"
SEC_EXPOSURE = "1"
SEC_CONTINUITY = "continuity"
SEC_EXITS = "8"
SEC_JOURNAL = "9"
SEC_BOD = "0"
SEC_UNIVERSE = "2"
SEC_LIQUIDITY = "3"
SEC_EVENTS = "4"
SEC_PATTERNS = "5"
SEC_OPTIONS = "6"
SEC_ENTRY = "7"
SEC_CAPABILITY = "A5"

COMMON_RTH = frozenset(
    {
        SEC_CLOCK,
        SEC_GIT,
        SEC_SESSION,
        SEC_LEASE_READ,
        SEC_ACCOUNT,
        SEC_FILES,
        SEC_EXPOSURE,
        SEC_JOURNAL,
    }
)

SCAN_ONLY_SECTIONS = frozenset(
    {
        SEC_LEASE_ACQUIRE,
        SEC_CAPABILITY,
        SEC_BOD,
        SEC_UNIVERSE,
        SEC_LIQUIDITY,
        SEC_EVENTS,
        SEC_PATTERNS,
        SEC_OPTIONS,
        SEC_ENTRY,
    }
)

IN_SCOPE = {
    OUTSIDE_RTH: frozenset({SEC_CLOCK}),
    MANAGE: COMMON_RTH | {SEC_CONTINUITY, SEC_EXITS},
    PRE_WINDOW: COMMON_RTH,
    FLATTEN_FLAT: COMMON_RTH,
    SCAN: COMMON_RTH | SCAN_ONLY_SECTIONS | {SEC_CONTINUITY, SEC_EXITS},
}

AFTER_CLASSIFY = {
    OUTSIDE_RTH: "exit_clock_only",
    MANAGE: "execute_continuity_and_section_8_only",
    PRE_WINDOW: "exposure_only_no_scan",
    FLATTEN_FLAT: "exposure_only_no_scan",
    SCAN: "acquire_then_scan",
}

RUN_ORDER = (
    "clock",
    "git_main_checkout",
    "session_clocks_no_rh",
    "lease_read_only",
    "account_selection",
    "core_recovery_capability",
    "read_rules_permissions_playbook",
    "exposure_and_working_orders",
    "classify_fire_mode_from_clock_and_exposure",
    "run_h_dispatch_print_card",
    "mode_gated_work",
)


def in_scope_sections(mode: str) -> frozenset[str]:
    return IN_SCOPE.get(mode, frozenset())


def may_execute_section(mode: str, section: str) -> bool:
    return section in in_scope_sections(mode)


def after_classify(mode: str) -> str:
    return AFTER_CLASSIFY.get(mode, "place_nothing")


def leftover_take_profit_allowed(mode: str, *, other_holder: bool) -> bool:
    """§8 take-profit is manage work. Other holder still owns the book."""
    return mode == MANAGE and not other_holder


def place_authority(
    *,
    kind: str,
    lease: RemoteLease,
    git_status: str = "ok",
    schema_ok: bool = True,
    automation_enabled: bool = True,
    owner_stop_all: bool = False,
    permissions_status: str = "ACTIVE",
    orders_complete: bool = True,
    helper_available: bool = True,
) -> tuple[bool, str]:
    """Single place table. Schema and other-holder beat emergency carve-outs."""
    if owner_stop_all:
        return False, "owner_revoked_all_order_activity"
    if not automation_enabled:
        return False, "automation_disabled"
    if not schema_ok:
        return False, "rules_prompt_mismatch"
    exit_intent = is_emergency_kind(kind) or is_manage_exit_kind(kind)
    allowed, reason = permissions_allow(
        status=permissions_status,
        owner_stop_all_including_exits=owner_stop_all,
        intent="close" if exit_intent else "new_entry",
    )
    if not allowed:
        return False, reason
    if is_emergency_kind(kind):
        if not helper_available:
            return False, "emergency_ref_id_unavailable"
        if not orders_complete:
            return False, "orders_incomplete"
    return may_place_option_order(lease, kind=kind, git_status=git_status)
