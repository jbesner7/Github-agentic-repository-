from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _parse_ymd(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def dte(expiration: str, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    return (_parse_ymd(expiration) - as_of).days


def pick_atm_or_one_otm(
    spot: float,
    instruments: list[dict[str, Any]],
    *,
    option_type: str,
) -> dict[str, Any] | None:
    """Prefer ATM strike; fallback one strike OTM for calls/puts."""
    typed = [i for i in instruments if (i.get("type") or "").lower() == option_type.lower()]
    if not typed or spot <= 0:
        return None
    typed = sorted(typed, key=lambda i: abs(float(i["strike_price"]) - spot))
    atm = typed[0]
    atm_strike = float(atm["strike_price"])
    if abs(atm_strike - spot) / spot <= 0.01:
        return {"selection": "atm", "instrument": atm}

    if option_type.lower() == "call":
        otm = [i for i in typed if float(i["strike_price"]) > spot]
        otm = sorted(otm, key=lambda i: float(i["strike_price"]))
    else:
        otm = [i for i in typed if float(i["strike_price"]) < spot]
        otm = sorted(otm, key=lambda i: float(i["strike_price"]), reverse=True)

    if otm:
        return {"selection": "one_otm", "instrument": otm[0]}
    return {"selection": "atm_fallback", "instrument": atm}


def choose_structure_from_bias(bias: str | None) -> str | None:
    if bias == "bullish":
        return "long_call"
    if bias == "bearish":
        return "long_put"
    return None


def filter_expirations(expiration_dates: list[str], *, max_dte: int, as_of: date | None = None) -> list[str]:
    as_of = as_of or date.today()
    out = []
    for exp in expiration_dates:
        days = dte(exp, as_of=as_of)
        if 0 <= days <= max_dte:
            out.append(exp)
    return sorted(out)
