"""Single emergency closer for leftover option exposure.

Git does not serialize overlapping stateless fires. The broker does:
working-order occupancy plus a deterministic `place_option_order` `ref_id`.
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable

from pipeline.h_gates import EMERGENCY_KINDS
from pipeline.orders import is_working_option_state, normalize_state


# Locked UUID5 namespace. Changing it is a schema bump.
EMERGENCY_REF_NAMESPACE = uuid.UUID("9af478e7-a454-51f1-87d1-d6b4613131ce")
EMERGENCY_REF_NAME_PREFIX = "h-emergency-close"

PLACE = "place_with_deterministic_ref_id"
MONITOR = "already_covered_monitor_only"
REUSE = "duplicate_ref_id_retry"
NO_POSITION = "no_position_to_close"

REPLACEMENT_TERMINAL_STATES = frozenset(
    {"cancelled", "canceled", "rejected", "failed", "voided"}
)
CLOSE_KINDS = EMERGENCY_KINDS | {
    "stop",
    "stop_market",
    "stop_limit",
    "sell_to_close",
    "close",
}


def _int_qty(value: Any) -> int:
    try:
        return max(0, int(float(str(value).strip())))
    except (TypeError, ValueError):
        return 0


def emergency_close_ref_id(
    *,
    option_id: str,
    session_date_et: str,
    generation: int = 0,
) -> str:
    """Same leftover + same ET date + same generation → same UUID. Two fires retry one order."""
    oid = (option_id or "").strip()
    day = (session_date_et or "").strip()
    if not oid or not day:
        raise ValueError("option_id and session_date_et are required")
    name = f"{EMERGENCY_REF_NAME_PREFIX}|{oid}|{day}|{int(generation)}"
    return str(uuid.uuid5(EMERGENCY_REF_NAMESPACE, name))


def order_option_ids(order: dict[str, Any] | None) -> frozenset[str]:
    row = order or {}
    found: set[str] = set()
    for key in ("option_id", "instrument_id"):
        value = str(row.get(key) or "").strip()
        if value:
            found.add(value)
    nested = row.get("option")
    if isinstance(nested, dict):
        value = str(nested.get("id") or nested.get("option_id") or "").strip()
        if value:
            found.add(value)
    for leg in row.get("legs") or []:
        value = str(leg.get("option_id") or leg.get("instrument_id") or "").strip()
        if value:
            found.add(value)
        nested_leg = leg.get("option")
        if isinstance(nested_leg, dict):
            value = str(nested_leg.get("id") or nested_leg.get("option_id") or "").strip()
            if value:
                found.add(value)
    return frozenset(found)


def is_sell_to_close(order: dict[str, Any] | None) -> bool:
    row = order or {}
    kind = normalize_state(row.get("kind") or row.get("intent") or row.get("type"))
    if kind in CLOSE_KINDS:
        return True
    side = normalize_state(row.get("side"))
    effect = normalize_state(row.get("position_effect"))
    if side == "sell" and effect == "close":
        return True
    if side == "sell" and kind in {"stop_market", "stop_limit"}:
        return True
    for leg in row.get("legs") or []:
        if normalize_state(leg.get("side")) == "sell" and normalize_state(
            leg.get("position_effect")
        ) == "close":
            return True
    return False


def remaining_close_quantity(order: dict[str, Any] | None) -> int:
    row = order or {}
    requested = _int_qty(row.get("quantity") if row.get("quantity") is not None else row.get("requested_quantity"))
    filled = _int_qty(row.get("filled_quantity"))
    return max(0, requested - filled)


def working_close_quantity(
    option_orders: Iterable[dict[str, Any]] | None,
    *,
    option_id: str,
) -> int:
    oid = (option_id or "").strip()
    total = 0
    for row in option_orders or []:
        if not is_working_option_state(row.get("state") or row.get("status")):
            continue
        if oid not in order_option_ids(row):
            continue
        if not is_sell_to_close(row):
            continue
        total += remaining_close_quantity(row)
    return total


def filled_close_quantity(
    option_orders: Iterable[dict[str, Any]] | None,
    *,
    option_id: str,
) -> int:
    """Filled sell-to-close contracts. A stale position after a fill is not uncovered."""
    oid = (option_id or "").strip()
    total = 0
    for row in option_orders or []:
        if oid not in order_option_ids(row):
            continue
        if not is_sell_to_close(row):
            continue
        total += _int_qty(row.get("filled_quantity"))
    return total


def emergency_close_generation(
    option_orders: Iterable[dict[str, Any]] | None,
    *,
    option_id: str,
) -> int:
    """Cancelled/rejected closer count. A fill does not mint a new ref_id."""
    oid = (option_id or "").strip()
    count = 0
    for row in option_orders or []:
        if oid not in order_option_ids(row):
            continue
        if not is_sell_to_close(row):
            continue
        if normalize_state(row.get("state") or row.get("status")) in REPLACEMENT_TERMINAL_STATES:
            count += 1
    return count


def decide_emergency_close(
    *,
    option_id: str,
    position_quantity: int,
    option_orders: Iterable[dict[str, Any]] | None,
    session_date_et: str,
) -> dict[str, Any]:
    """Occupy one closer per leftover. Place and reuse share one deterministic ref_id."""
    qty = _int_qty(position_quantity)
    oid = (option_id or "").strip()
    if qty <= 0 or not oid:
        return {"action": "skip", "reason": NO_POSITION, "ref_id": None, "uncovered": 0}
    covered = working_close_quantity(option_orders, option_id=oid) + filled_close_quantity(
        option_orders, option_id=oid
    )
    uncovered = max(0, qty - covered)
    generation = emergency_close_generation(option_orders, option_id=oid)
    ref_id = emergency_close_ref_id(
        option_id=oid,
        session_date_et=session_date_et,
        generation=generation,
    )
    if uncovered <= 0:
        return {"action": "monitor", "reason": MONITOR, "ref_id": ref_id, "uncovered": 0}
    for row in option_orders or []:
        if str(row.get("ref_id") or "").strip() == ref_id:
            return {"action": "reuse", "reason": REUSE, "ref_id": ref_id, "uncovered": uncovered}
    return {"action": "place", "reason": PLACE, "ref_id": ref_id, "uncovered": uncovered}
