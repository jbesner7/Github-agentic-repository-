from __future__ import annotations

from typing import Any


def extract_greeks(quote: dict[str, Any]) -> dict[str, Any]:
    """Copy Greeks only from Robinhood quote fields; never invent values."""
    fields = (
        "delta",
        "gamma",
        "theta",
        "vega",
        "rho",
        "implied_volatility",
    )
    out: dict[str, Any] = {}
    missing: list[str] = []
    for f in fields:
        if f in quote and quote[f] not in (None, ""):
            try:
                out[f] = float(quote[f])
            except (TypeError, ValueError):
                missing.append(f)
        else:
            missing.append(f)
    return {"greeks": out, "missing_fields": missing, "source": "robinhood_get_option_quotes"}


def delta_in_band(
    delta: float | None,
    *,
    option_type: str,
    lo: float = 0.4,
    hi: float = 0.5,
) -> tuple[bool, str | None]:
    """Signed long-option bands. Do not accept absolute-only or sign-inverted values."""
    if delta is None:
        return False, "delta_missing_from_quote"
    ot = (option_type or "").strip().lower()
    if ot in ("put", "p"):
        lo_signed, hi_signed = -abs(hi), -abs(lo)
        if lo_signed <= delta <= hi_signed:
            return True, None
        return False, f"put_delta_{delta:.4f}_outside_{lo_signed}_{hi_signed}"
    if ot in ("call", "c"):
        lo_signed, hi_signed = abs(lo), abs(hi)
        if lo_signed <= delta <= hi_signed:
            return True, None
        return False, f"call_delta_{delta:.4f}_outside_{lo_signed}_{hi_signed}"
    return False, "delta_option_type_required"
