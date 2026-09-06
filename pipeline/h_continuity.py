"""Formal continuity for a stateless Agent H fire.

Each fire starts with no chat memory. Reconstruct management from the
broker. Git/lease is the concurrency gate for new entries, not the store.
"""

from __future__ import annotations

from typing import Any

from pipeline.h_gates import RemoteLease, is_emergency_kind, is_git_unavailable


CONTINUITY_STORE = "broker_positions_and_working_orders"
MANAGE_EXISTING = "manage_existing"
SCAN_IF_FLAT = "scan_if_gates_pass"


def reconstruct_run_mode(
    *,
    has_option_position: bool,
    has_working_order: bool,
) -> str:
    """Brokerage state, not prior chat, decides whether this fire manages or scans."""
    if has_option_position or has_working_order:
        return MANAGE_EXISTING
    return SCAN_IF_FLAT


def handoff_after_lease_loss(
    lease: RemoteLease,
    *,
    git_status: str = "ok",
    kind: str = "protect",
) -> str:
    """Current fire action when the lease is gone or Git cannot be reached."""
    if is_emergency_kind(kind) and is_git_unavailable(git_status):
        return "emergency_protect_from_broker_state"
    if lease.other_unexpired_holder:
        return "place_nothing_new_owner_manages"
    if is_git_unavailable(git_status):
        return "place_nothing_git_unavailable"
    return "reacquire_then_recover"


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
