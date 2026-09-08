"""Single fire card for Agent H.

H does not hold clock → Git → lease → account → exposure → mode →
attention → gates in working memory. After clock and exposure, it runs
`print_card` and executes only that output.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

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


_FILL_QTY_KEYS = ("filled_quantity", "processed_quantity", "cumulative_quantity")
_FILL_STATES = frozenset({"filled", "partially_filled"})
_ORDER_DATE_KEYS = (
    "created_at",
    "updated_at",
    "last_transaction_at",
    "filled_at",
    "executed_at",
    "timestamp",
)


def _order_day(row: Mapping[str, Any]) -> str:
    for key in _ORDER_DATE_KEYS:
        text = str(row.get(key) or "").strip()
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return text[:10]
    return ""


def _fill_qty(row: Mapping[str, Any]) -> float:
    for key in _FILL_QTY_KEYS:
        raw = row.get(key)
        if raw in (None, ""):
            continue
        try:
            qty = float(str(raw).replace(",", ""))
        except (TypeError, ValueError):
            continue
        if qty > 0:
            return qty
    return 0.0


def _row_has_fill(row: Mapping[str, Any]) -> bool:
    if _fill_qty(row) > 0:
        return True
    state = str(row.get("state") or row.get("status") or "").strip().lower()
    return state in _FILL_STATES


def session_has_fills(payload: Any, session_date_et: str) -> tuple[bool | None, str]:
    """True if this payload has a same-day fill. None if the payload is unusable."""
    if payload is None:
        return None, "orders_missing"
    day = (session_date_et or "").strip()
    if not day:
        return None, "session_date_missing"
    rows, parsed = coerce_option_orders(payload)
    if not parsed or rows is None:
        return None, "orders_unparseable"
    for row in rows:
        if not _row_has_fill(row):
            continue
        stamped = _order_day(row)
        if not stamped or stamped == day:
            return True, "fill_present"
    return False, "no_fills"


def resolve_fills_today(
    *,
    option_orders: Any,
    equity_orders: Any,
    session_date_et: str,
    orders_complete: bool = True,
) -> tuple[bool | None, str]:
    """Fills from broker option + equity orders. Incomplete payloads are not 'no fills'."""
    if not orders_complete:
        return None, "orders_incomplete"
    if not (session_date_et or "").strip():
        return None, "session_date_missing"
    option_has, option_reason = session_has_fills(option_orders, session_date_et)
    if option_has is None:
        return None, option_reason
    equity_has, equity_reason = session_has_fills(equity_orders, session_date_et)
    if equity_has is None:
        return None, equity_reason
    if option_has or equity_has:
        return True, "fill_present"
    return False, "no_fills"


def bod_card(
    *,
    portfolio: dict[str, Any] | str | None,
    leftover: bool,
    option_orders: list[dict[str, Any]] | str | dict[str, Any] | None,
    equity_orders: list[dict[str, Any]] | str | dict[str, Any] | None,
    session_date_et: str,
    orders_complete: bool = True,
) -> dict[str, Any]:
    """Session-start NLV. H does not treat midday total_value as BOD after a fill."""
    parsed = coerce_portfolio(portfolio)
    fills_today, _fill_reason = resolve_fills_today(
        option_orders=option_orders,
        equity_orders=equity_orders,
        session_date_et=session_date_et,
        orders_complete=orders_complete,
    )
    # Incomplete or missing order pages block the cash==total fallback only.
    # A broker BOD field is still usable.
    amount, field, reason = resolve_bod_nlv(
        parsed,
        leftover=bool(leftover),
        fills_today=True if fills_today is None else bool(fills_today),
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
