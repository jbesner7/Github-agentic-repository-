"""Deterministic Agent H transactional gates.

Grok may decide only: pattern → direction → candidate.
This module, with `config/rules.json`, owns:

lease → account → risk → review → placement → cancellation
→ fill reconciliation → stop → liquidation → journaling

H cannot import this at Automation runtime. The prompt and rules must match
these functions exactly. Tests fail closed if they drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REVIEW_ORDER_CHECK_FAILURES = frozenset(
    {
        "review_order_checks",
        "order_checks",
    }
)

ONE_REPLACEMENT_INTENTS = frozenset({"entry", "take_profit"})
UNLIMITED_REPLACEMENT_INTENTS = frozenset(
    {
        "forced_liquidation",
        "protection_failed",
        "mandatory_liquidation",
    }
)

EXIT_INTENTS = frozenset({"cancel", "protect", "reduce", "close"})
INCREASE_INTENTS = frozenset({"new_entry", "increase"})


@dataclass(frozen=True)
class RemoteLease:
    owned_by_this_run: bool
    expired: bool
    other_unexpired_holder: bool
    readable: bool = True


GIT_UNAVAILABLE = frozenset({"unavailable", "timeout", "outage"})
EMERGENCY_KINDS = frozenset(
    {
        "protect",
        "flatten",
        "forced_liquidation",
        "protection_failed",
        "emergency_exit",
        "missing_stop_flatten",
    }
)


def is_emergency_kind(kind: str) -> bool:
    return (kind or "").strip().lower() in EMERGENCY_KINDS


def is_git_unavailable(git_status: str) -> bool:
    return (git_status or "").strip().lower() in GIT_UNAVAILABLE


def may_place_option_order(
    lease: RemoteLease,
    *,
    kind: str = "any",
    git_status: str = "ok",
) -> tuple[bool, str]:
    """New entries always need a live lease. Emergency protection does not need Git.

    A known other lease holder still blocks. Emergency place is still subject
    to `pipeline.h_closer.decide_emergency_close`.
    """
    if lease.other_unexpired_holder:
        return False, "lease_held_after_fill" if kind != "entry" else "lease_held"
    if is_emergency_kind(kind):
        if lease.readable and lease.owned_by_this_run and not lease.expired:
            return True, "ok"
        if is_git_unavailable(git_status):
            return True, "emergency_protection_without_git"
        return True, "emergency_protection_without_owned_lease"
    if not lease.readable:
        return False, "lease_unreadable"
    if lease.expired or not lease.owned_by_this_run:
        return False, "lease_must_reacquire_before_place"
    return True, "ok"


def recovery_action(lease: RemoteLease, *, git_status: str = "ok", kind: str = "protect") -> str:
    """What a filled run may do after its lease expires, another run appears, or Git is down."""
    if lease.other_unexpired_holder:
        return "place_nothing_new_owner_manages"
    if is_emergency_kind(kind):
        if lease.readable and lease.owned_by_this_run and not lease.expired:
            return "recover_now"
        return "emergency_protect_without_owned_lease"
    if not lease.readable or lease.expired or not lease.owned_by_this_run:
        return "reacquire_then_recover"
    return "recover_now"


ENTRY_LEASE_RENEW_MINUTES = 6
MIDRUN_LEASE_RENEW_MINUTES = 3

CORE_RECOVERY_TOOLS = (
    "get_accounts",
    "get_option_positions",
    "get_option_orders",
    "get_option_quotes",
    "review_option_order",
    "place_option_order",
    "cancel_option_order",
)

RUN_ORDER_AFTER_LEASE = (
    "account_selection",
    "core_recovery_capability",
    "read_rules_permissions_playbook",
    "exposure_and_working_orders",
    "classify_fire_mode_from_clock_and_exposure",
    "if_exposure_continuity_and_section_8_only",
    "if_flat_before_scan_window_no_scan",
    "if_scan_acquire_lease_then_permissions_bod_session_full_capability_scan",
)


def must_reverify_remote_lease_before_place(*, kind: str, git_status: str = "ok") -> bool:
    """Emergency protection does not wait on Git fetch/push/lease verify."""
    return not is_emergency_kind(kind)


def must_renew_lease(*, minutes_remaining: float, before_entry: bool) -> bool:
    """Renew before entry unless at least 6 minutes remain. Always renew under 3."""
    if minutes_remaining < MIDRUN_LEASE_RENEW_MINUTES:
        return True
    if before_entry and minutes_remaining < ENTRY_LEASE_RENEW_MINUTES:
        return True
    return False


def core_recovery_tools_present(available: set[str] | list[str] | tuple[str, ...]) -> tuple[bool, tuple[str, ...]]:
    have = {str(name) for name in available}
    missing = tuple(name for name in CORE_RECOVERY_TOOLS if name not in have)
    return (not missing, missing)


def may_try_one_otm(atm_failure: str) -> bool:
    """ATM may fall back to one OTM except after a broker `order_checks` block."""
    return (atm_failure or "").strip().lower() not in REVIEW_ORDER_CHECK_FAILURES


def replacement_policy(intent: str) -> dict[str, Any]:
    """One-replace applies to entries and take-profit only."""
    kind = (intent or "").strip().lower()
    if kind in ONE_REPLACEMENT_INTENTS:
        interval = 15 if kind == "take_profit" else 30
        return {
            "max_replacements": 1,
            "interval_seconds": interval,
            "new_ref_id_each": True,
        }
    if kind in UNLIMITED_REPLACEMENT_INTENTS:
        return {
            "max_replacements": None,
            "interval_seconds": 15,
            "until": "flat_or_order_entry_close",
            "new_ref_id_each": True,
        }
    return {"max_replacements": 0, "interval_seconds": None, "new_ref_id_each": True}


def permissions_allow(
    *,
    status: str | None,
    owner_stop_all_including_exits: bool,
    intent: str,
) -> tuple[bool, str]:
    """Inactive permissions block new entries; existing exposure may only shrink.

    An explicit owner instruction to stop all order activity, including exits,
    revokes recovery as well.
    """
    if owner_stop_all_including_exits:
        return False, "owner_revoked_all_order_activity"
    kind = (intent or "").strip().lower()
    active = (status or "").strip().upper() == "ACTIVE"
    if active:
        return True, "ok"
    if kind in INCREASE_INTENTS:
        return False, "inactive_permissions_block_new_entry"
    if kind in EXIT_INTENTS:
        return True, "inactive_permissions_exits_only"
    return False, "inactive_permissions_block_increase"


def post_lease_priority(*, has_option_position: bool, has_working_order: bool) -> str:
    """After files: exposure beats scan, BOD, and new-entry checks. Files still precede any place."""
    if has_option_position or has_working_order:
        return "exposure_only_no_scan"
    return "may_scan_if_other_gates_pass"


def attempt_gtc_stop(*, schema_confirms_gtc: bool = False) -> bool:
    """This connection documents option stop_market as GFD-only."""
    return bool(schema_confirms_gtc)


def required_stop_time_in_force(*, schema_confirms_gtc: bool = False) -> str:
    return "gtc" if attempt_gtc_stop(schema_confirms_gtc=schema_confirms_gtc) else "gfd"
