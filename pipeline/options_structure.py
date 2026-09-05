from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pipeline.session import today_et


def _parse_ymd(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def dte(expiration: str, as_of: date | None = None) -> int:
    as_of = as_of or today_et()
    return (_parse_ymd(expiration) - as_of).days


def _instrument_type(row: dict[str, Any]) -> str:
    raw = (row.get("type") or row.get("option_type") or "").strip().lower()
    if raw in ("c", "call"):
        return "call"
    if raw in ("p", "put"):
        return "put"
    return raw


def _strike(row: dict[str, Any]) -> float:
    value = row.get("strike_price")
    if value in (None, ""):
        value = row.get("strike")
    return float(value)


def _instrument_id(row: dict[str, Any]) -> str | None:
    value = row.get("id") or row.get("instrument_id")
    return str(value) if value not in (None, "") else None


def instrument_id(row: dict[str, Any]) -> str | None:
    return _instrument_id(row)


def strike_price(row: dict[str, Any]) -> float:
    return _strike(row)


def _typed_instruments(instruments: list[dict[str, Any]], option_type: str) -> list[dict[str, Any]]:
    want = option_type.strip().lower()
    if want in ("c", "call"):
        want = "call"
    elif want in ("p", "put"):
        want = "put"
    return [row for row in instruments if _instrument_type(row) == want]


def _same_instrument(left: dict[str, Any], right: dict[str, Any]) -> bool:
    lid, rid = _instrument_id(left), _instrument_id(right)
    if lid and rid:
        return lid == rid
    return _strike(left) == _strike(right)


def strikes_bracket_spot(spot: float, instruments: list[dict[str, Any]], *, option_type: str) -> bool:
    """True when the page includes strikes on both sides of spot (ATM is in the set)."""
    typed = _typed_instruments(instruments, option_type)
    if not typed or spot <= 0:
        return False
    strikes = [_strike(row) for row in typed]
    return min(strikes) <= spot <= max(strikes)


def rank_atm_then_one_otm(
    spot: float,
    instruments: list[dict[str, Any]],
    *,
    option_type: str,
) -> list[dict[str, Any]]:
    """ATM is the nearest strike (no 1% cutoff). Then one OTM if it is a different contract."""
    typed = _typed_instruments(instruments, option_type)
    if not typed or spot <= 0:
        return []
    typed_sorted = sorted(typed, key=lambda row: abs(_strike(row) - spot))
    atm = typed_sorted[0]
    ranked: list[dict[str, Any]] = [{"selection": "atm", "instrument": atm}]

    if option_type.strip().lower() in ("call", "c"):
        otm = sorted((row for row in typed if _strike(row) > spot), key=_strike)
    else:
        otm = sorted((row for row in typed if _strike(row) < spot), key=_strike, reverse=True)

    if otm and not _same_instrument(otm[0], atm):
        ranked.append({"selection": "one_otm", "instrument": otm[0]})
    return ranked


def pick_atm_or_one_otm(
    spot: float,
    instruments: list[dict[str, Any]],
    *,
    option_type: str,
) -> dict[str, Any] | None:
    """Prefer ATM (nearest strike); fallback one strike OTM for calls/puts."""
    ranked = rank_atm_then_one_otm(spot, instruments, option_type=option_type)
    return ranked[0] if ranked else None


def choose_structure_from_bias(bias: str | None) -> str | None:
    if bias == "bullish":
        return "long_call"
    if bias == "bearish":
        return "long_put"
    return None


def filter_expirations(
    expiration_dates: list[str],
    *,
    max_dte: int,
    min_dte: int = 0,
    as_of: date | None = None,
) -> list[str]:
    as_of = as_of or today_et()
    out = []
    for exp in expiration_dates:
        days = dte(exp, as_of=as_of)
        if min_dte <= days <= max_dte:
            out.append(exp)
    return sorted(out)
