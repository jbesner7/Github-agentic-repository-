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


def delta_in_band(delta: float | None, *, lo: float, hi: float) -> tuple[bool, str | None]:
    if delta is None:
        return False, "delta_missing_from_quote"
    # Calls: positive delta. Puts: negative — compare absolute value for long options band.
    ad = abs(delta)
    if lo <= ad <= hi:
        return True, None
    return False, f"delta_abs_{ad:.4f}_outside_{lo}_{hi}"
