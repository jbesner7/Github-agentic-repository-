from __future__ import annotations

from typing import Any, Iterable

# Robinhood MCP has no `open=true` filter. Working tickets are these states.
OPTION_WORKING_STATES = frozenset(
    {"queued", "confirmed", "partially_filled", "pending_cancelled"}
)
EQUITY_WORKING_STATES = frozenset(
    {"new", "queued", "confirmed", "unconfirmed", "partially_filled"}
)


def normalize_state(value: Any) -> str:
    return str(value or "").strip().lower()


def is_working_option_state(state: Any) -> bool:
    return normalize_state(state) in OPTION_WORKING_STATES


def is_working_equity_state(state: Any) -> bool:
    return normalize_state(state) in EQUITY_WORKING_STATES


def working_orders(
    option_orders: Iterable[dict[str, Any]] | None = None,
    equity_orders: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for row in option_orders or []:
        if is_working_option_state(row.get("state") or row.get("status")):
            found.append({"asset_class": "option", **row})
    for row in equity_orders or []:
        if is_working_equity_state(row.get("state") or row.get("status")):
            found.append({"asset_class": "equity", **row})
    return found


def has_working_orders(
    option_orders: Iterable[dict[str, Any]] | None = None,
    equity_orders: Iterable[dict[str, Any]] | None = None,
) -> bool:
    return bool(working_orders(option_orders, equity_orders))
