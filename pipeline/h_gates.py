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


CONTRACT_ELIGIBILITY_FAILURES = frozenset(
    {
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
    }
)

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


def may_place_option_order(lease: RemoteLease, *, kind: str = "any") -> tuple[bool, str]:
    """Every place_option_order, including protection and liquidation, needs a live lease."""
    if not lease.readable:
        return False, "lease_unreadable"
    if lease.other_unexpired_holder:
        return False, "lease_held_after_fill" if kind != "entry" else "lease_held"
    if lease.expired or not lease.owned_by_this_run:
        return False, "lease_must_reacquire_before_place"
    return True, "ok"


def recovery_action(lease: RemoteLease) -> str:
    """What a filled run may do after its lease expires or another run appears."""
    if lease.other_unexpired_holder:
        return "place_nothing_new_owner_manages"
    if not lease.readable or lease.expired or not lease.owned_by_this_run:
        return "reacquire_then_recover"
    return "recover_now"


def never_place_from_momentary_absent_other_lease() -> bool:
    return True


def renew_lease_immediately_before_entry_placement() -> bool:
    return True


def may_try_one_otm(atm_failure: str) -> bool:
    """ATM may fall back to exactly one OTM on any contract-level eligibility miss.

    A review `order_checks` block is a broker refusal. Do not try another contract
    to circumvent it.
    """
    reason = (atm_failure or "").strip().lower()
    if reason in REVIEW_ORDER_CHECK_FAILURES:
        return False
    return True


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
    """Exposure reconciliation beats scan, BOD, session counters, and new-entry checks."""
    if has_option_position or has_working_order:
        return "exposure_only_no_scan"
    return "may_scan_if_other_gates_pass"


def attempt_gtc_stop(*, schema_confirms_gtc: bool = False) -> bool:
    """This connection documents option stop_market as GFD-only."""
    return bool(schema_confirms_gtc)


def required_stop_time_in_force(*, schema_confirms_gtc: bool = False) -> str:
    return "gtc" if attempt_gtc_stop(schema_confirms_gtc=schema_confirms_gtc) else "gfd"
