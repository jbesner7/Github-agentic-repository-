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


def _atm_sort_key(row: dict[str, Any], spot: float, option_type: str) -> tuple[float, float]:
    strike = _strike(row)
    distance = abs(strike - spot)
    ot = option_type.strip().lower()
    # Tie: lower strike for calls, higher strike for puts.
    if ot in ("put", "p"):
        return (distance, -strike)
    return (distance, strike)


def rank_atm_then_one_otm(
    spot: float,
    instruments: list[dict[str, Any]],
    *,
    option_type: str,
) -> list[dict[str, Any]]:
    """ATM is the nearest strike (no 1% cutoff). Then exactly one listed strike OTM from ATM."""
    typed = _typed_instruments(instruments, option_type)
    if not typed or spot <= 0:
        return []
    typed_sorted = sorted(typed, key=lambda row: _atm_sort_key(row, spot, option_type))
    atm = typed_sorted[0]
    ranked: list[dict[str, Any]] = [{"selection": "atm", "instrument": atm}]
    atm_strike = _strike(atm)
    ot = option_type.strip().lower()
    if ot in ("call", "c"):
        farther = sorted((row for row in typed if _strike(row) > atm_strike), key=_strike)
    else:
        farther = sorted((row for row in typed if _strike(row) < atm_strike), key=_strike, reverse=True)
    if farther and not _same_instrument(farther[0], atm):
        ranked.append({"selection": "one_otm", "instrument": farther[0]})
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
    min_dte: int = 2,
    as_of: date | None = None,
) -> list[str]:
    as_of = as_of or today_et()
    out = []
    for exp in expiration_dates:
        days = dte(exp, as_of=as_of)
        if min_dte <= days <= max_dte:
            out.append(exp)
    return sorted(out)


def rank_expirations(
    expiration_dates: list[str],
    *,
    overnight_holding_enabled: bool,
    as_of: date | None = None,
    same_day_min_dte: int = 2,
    same_day_max_dte: int = 3,
    overnight_min_dte: int = 4,
    overnight_max_dte: int = 7,
    hard_min_dte: int = 2,
    hard_max_dte: int = 7,
) -> list[str]:
    """Deterministic expiration group. Ascending DTE inside the one permitted group."""
    as_of = as_of or today_et()
    if overnight_holding_enabled:
        lo, hi = overnight_min_dte, overnight_max_dte
    else:
        lo, hi = same_day_min_dte, same_day_max_dte
    lo = max(lo, hard_min_dte)
    hi = min(hi, hard_max_dte)
    ranked: list[tuple[int, str]] = []
    for exp in expiration_dates:
        days = dte(exp, as_of=as_of)
        if lo <= days <= hi:
            ranked.append((days, exp))
    return [exp for _, exp in sorted(ranked)]
