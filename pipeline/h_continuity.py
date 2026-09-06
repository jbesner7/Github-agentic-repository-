"""Formal continuity for a stateless Agent H fire.

Each Automation fire starts with no chat memory. Continuous position
management is reconstructed from the broker every run. Git/lease is the
concurrency gate for new entries, not the position store.
"""

from __future__ import annotations

from typing import Any

from pipeline.h_gates import GIT_UNAVAILABLE, RemoteLease, is_emergency_kind, is_git_unavailable


CONTINUITY_STORE = "broker_positions_and_working_orders"
MANAGE_EXISTING = "manage_existing"
SCAN_IF_FLAT = "scan_if_gates_pass"


def chat_is_not_continuity_store() -> bool:
    return True


def reconstruct_run_mode(
    *,
    has_option_position: bool,
    has_working_order: bool,
) -> str:
    """Brokerage state, not prior chat, decides whether this fire manages or scans."""
    if has_option_position or has_working_order:
        return MANAGE_EXISTING
    return SCAN_IF_FLAT


def next_fire_must_reconstruct_from_broker() -> bool:
    return True


def handoff_after_lease_loss(
    lease: RemoteLease,
    *,
    git_status: str = "ok",
    this_run_filled: bool = False,
    kind: str = "protect",
) -> str:
    """What the current fire does when the lease is gone or Git cannot be reached.

    Git outage on an emergency kind: manage from broker state.
    Another unexpired holder while Git is reachable: that owner manages.
    This-run fill with Git up and no other holder: reacquire, then recover.
    """
    if is_emergency_kind(kind) and is_git_unavailable(git_status):
        return "emergency_protect_from_broker_state"
    if lease.other_unexpired_holder:
        return "place_nothing_new_owner_manages"
    if this_run_filled and (not lease.readable or lease.expired or not lease.owned_by_this_run):
        return "reacquire_then_recover"
    if git_status in GIT_UNAVAILABLE:
        return "emergency_protect_from_broker_state" if is_emergency_kind(kind) else "place_nothing_git_unavailable"
    return "reacquire_then_recover"


def session_counters_are_advisory_if_git_unreadable() -> bool:
    """h_session.json is used when Git is readable. Broker fills still govern protection."""
    return True


def exposure_fields(position: dict[str, Any] | None) -> dict[str, Any]:
    """Minimum identity a later fire needs. No chat transcript required."""
    pos = position or {}
    return {
        "option_id": pos.get("option_id") or pos.get("id"),
        "quantity": pos.get("quantity") or pos.get("filled_quantity"),
        "average_fill": pos.get("average_price") or pos.get("average_fill_price"),
        "chain_symbol": pos.get("chain_symbol") or pos.get("symbol"),
        "expiration_date": pos.get("expiration_date"),
    }
