"""Single fire card for Agent H.

H does not hold clock → Git → lease → account → exposure → mode →
attention → gates in working memory. After clock and exposure, it runs
`print_card` and executes only that output.
"""

from __future__ import annotations

import json
from typing import Any

from pipeline.h_attention import (
    after_classify,
    in_scope_sections,
    leftover_take_profit_allowed,
    place_authority,
)
from pipeline.h_budget import SCAN, classify_fire_mode, may_journal, must_acquire_lease
from pipeline.h_continuity import leftover_close_plan
from pipeline.h_gates import RemoteLease
from pipeline.quotes import resolve_bod_nlv


HELPER_UNAVAILABLE = "helper_unavailable_fail_closed"


def fire_card(
    *,
    weekday: int,
    et_time: Any,
    leftover: bool,
    other_holder: bool = False,
    helper_ok: bool = True,
) -> dict[str, Any]:
    """Classify the fire. Helper failure is fail-closed: no scan."""
    if not helper_ok:
        return {
            "mode": HELPER_UNAVAILABLE,
            "next": "continuity_and_section_8_if_leftover_else_exit",
            "sections": ("continuity", "8") if leftover else ("A",),
            "acquire_lease": False,
            "scan": False,
            "take_profit": False,
            "journal": bool(leftover),
        }
    mode = classify_fire_mode(
        weekday=weekday,
        et_time=et_time,
        has_option_position=leftover,
        has_working_order=leftover,
    )
    return {
        "mode": mode,
        "next": after_classify(mode),
        "sections": tuple(sorted(in_scope_sections(mode))),
        "acquire_lease": must_acquire_lease(mode),
        "scan": mode == SCAN,
        "take_profit": leftover_take_profit_allowed(mode, other_holder=other_holder),
        "journal": may_journal(mode, placed_or_cancelled=leftover),
    }


def format_card(card: dict[str, Any]) -> str:
    """One key=value line per field. H copies these; it does not reinterpret."""
    sections = card.get("sections") or ()
    if isinstance(sections, (list, tuple, frozenset, set)):
        section_text = ",".join(sorted(str(item) for item in sections))
    else:
        section_text = str(sections)
    lines = [
        f"mode={card['mode']}",
        f"next={card['next']}",
        f"sections={section_text}",
        f"acquire_lease={'true' if card['acquire_lease'] else 'false'}",
        f"scan={'true' if card['scan'] else 'false'}",
        f"take_profit={'true' if card['take_profit'] else 'false'}",
        f"journal={'true' if card['journal'] else 'false'}",
    ]
    return "\n".join(lines)


def print_card(
    *,
    weekday: int,
    et_time: Any,
    leftover: bool,
    other_holder: bool = False,
    helper_ok: bool = True,
) -> str:
    text = format_card(
        fire_card(
            weekday=weekday,
            et_time=et_time,
            leftover=leftover,
            other_holder=other_holder,
            helper_ok=helper_ok,
        )
    )
    print(text)
    return text


def may_place(
    *,
    kind: str,
    owned: bool,
    expired: bool,
    other_holder: bool,
    git_status: str = "ok",
    readable: bool = True,
    schema_ok: bool = True,
    automation_enabled: bool = True,
    owner_stop_all: bool = False,
    permissions_status: str = "ACTIVE",
    orders_complete: bool = True,
    helper_available: bool = True,
) -> tuple[bool, str]:
    """Place table H must run before every place_option_order."""
    lease = RemoteLease(
        owned_by_this_run=owned,
        expired=expired,
        other_unexpired_holder=other_holder,
        readable=readable,
    )
    return place_authority(
        kind=kind,
        lease=lease,
        git_status=git_status,
        schema_ok=schema_ok,
        automation_enabled=automation_enabled,
        owner_stop_all=owner_stop_all,
        permissions_status=permissions_status,
        orders_complete=orders_complete,
        helper_available=helper_available,
    )


def _extract_order_rows(payload: Any) -> list[dict[str, Any]] | None:
    """List of order dicts, or None when the payload is not usable occupancy."""
    if payload is None:
        return []
    if isinstance(payload, list):
        if all(item is None or isinstance(item, dict) for item in payload):
            return [item for item in payload if isinstance(item, dict)]
        return None
    if not isinstance(payload, dict):
        return None
    for key in ("orders", "results", "items"):
        nested = payload.get(key)
        if isinstance(nested, list):
            return _extract_order_rows(nested)
    data = payload.get("data")
    if isinstance(data, (dict, list)):
        nested = _extract_order_rows(data)
        if nested is not None:
            return nested
    if any(key in payload for key in ("id", "option_id", "legs", "state", "side")):
        return [payload]
    return None


def coerce_option_orders(
    option_orders: list[dict[str, Any]] | str | dict[str, Any] | None,
) -> tuple[list[dict[str, Any]] | None, bool]:
    """Parse leftover occupancy. Unknown or invalid JSON is incomplete, not empty."""
    payload: Any = option_orders
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None, False
    rows = _extract_order_rows(payload)
    if rows is None:
        return None, False
    return rows, True


def leftover_card(
    *,
    option_id: str,
    position_quantity: int,
    option_orders: list[dict[str, Any]] | str | dict[str, Any] | None,
    session_date_et: str,
    orders_complete: bool = True,
) -> dict[str, Any]:
    """Broker occupancy. H does not subtract fills itself."""
    rows, parsed = coerce_option_orders(option_orders)
    plan = leftover_close_plan(
        option_id=option_id,
        position_quantity=position_quantity,
        option_orders=rows or [],
        session_date_et=session_date_et,
        orders_complete=bool(orders_complete and parsed),
    )
    print(
        "\n".join(
            [
                f"action={plan.get('action')}",
                f"reason={plan.get('reason')}",
                f"ref_id={plan.get('ref_id')}",
                f"uncovered={plan.get('uncovered')}",
            ]
        )
    )
    return plan


def coerce_portfolio(portfolio: dict[str, Any] | str | None) -> dict[str, Any] | None:
    """Parse get_portfolio JSON. Unknown or invalid JSON is missing, not empty."""
    payload: Any = portfolio
    if payload is None:
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    if isinstance(payload, dict):
        return payload
    return None


def bod_card(
    *,
    portfolio: dict[str, Any] | str | None,
    leftover: bool,
    fills_today: bool,
) -> dict[str, Any]:
    """Session-start NLV. H does not treat midday total_value as BOD after a fill."""
    parsed = coerce_portfolio(portfolio)
    amount, field, reason = resolve_bod_nlv(
        parsed,
        leftover=bool(leftover),
        fills_today=bool(fills_today),
    )
    if parsed is None and portfolio not in (None, "", {}, []):
        amount, field, reason = None, None, "bod_nlv_unavailable"
    card = {
        "bod_nlv": amount,
        "bod_nlv_field": field,
        "reason": reason,
    }
    nlv_text = "" if amount is None else f"{amount:.2f}"
    print(
        "\n".join(
            [
                f"bod_nlv={nlv_text}",
                f"bod_nlv_field={field or ''}",
                f"reason={reason}",
            ]
        )
    )
    return card
