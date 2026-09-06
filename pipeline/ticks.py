"""Valid-tick rounding for option and equity prices.

Robinhood option `min_ticks` is typically $0.01 below $3.00 and $0.05 at or
above $3.00. Equity day-trade stops use a $0.01 tick. H and F must round
before review — do not send a raw 80% stop.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN
from typing import Any


OPTION_TICK_CUTOFF = Decimal("3.00")
OPTION_TICK_BELOW = Decimal("0.01")
OPTION_TICK_AT_OR_ABOVE = Decimal("0.05")
EQUITY_TICK = Decimal("0.01")


def _as_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value).replace("$", "").replace(",", "").strip())
    except Exception:
        return None
    if amount != amount or amount <= 0:
        return None
    return amount


def option_tick_size(price: Any, min_ticks: dict[str, Any] | None = None) -> Decimal | None:
    """Tick for a premium. Prefer instrument `min_ticks`; else RH typical."""
    px = _as_decimal(price)
    if px is None:
        return None
    if isinstance(min_ticks, dict):
        try:
            cutoff = Decimal(str(min_ticks.get("cutoff_price", OPTION_TICK_CUTOFF)))
            below = Decimal(str(min_ticks.get("below_tick", OPTION_TICK_BELOW)))
            above = Decimal(str(min_ticks.get("above_tick", OPTION_TICK_AT_OR_ABOVE)))
        except Exception:
            return None
        if below <= 0 or above <= 0:
            return None
        return below if px < cutoff else above
    return OPTION_TICK_BELOW if px < OPTION_TICK_CUTOFF else OPTION_TICK_AT_OR_ABOVE


def _quantize(price: Decimal, tick: Decimal, rounding) -> Decimal:
    steps = (price / tick).quantize(Decimal("1"), rounding=rounding)
    return (steps * tick).quantize(tick)


def round_to_tick(
    price: Any,
    tick: Any,
    *,
    mode: str = "nearest",
) -> Decimal | None:
    """Round `price` onto `tick`.

    mode:
      nearest — half-even
      toward_bid / down — floor (passive buy, or never exceed a cap)
      toward_fill / up — ceil (tighter sell-to-close stop; never widen)
    """
    px = _as_decimal(price)
    step = _as_decimal(tick)
    if px is None or step is None:
        return None
    if mode in {"toward_fill", "up", "ceil"}:
        return _quantize(px, step, ROUND_CEILING)
    if mode in {"toward_bid", "down", "floor"}:
        return _quantize(px, step, ROUND_FLOOR)
    return _quantize(px, step, ROUND_HALF_EVEN)


def entry_limit_from_mid(mid: Any, ask: Any, tick: Any) -> Decimal | None:
    """Nearest tick; exact half-tick toward the bid; never above ask."""
    mid_d = _as_decimal(mid)
    ask_d = _as_decimal(ask)
    step = _as_decimal(tick)
    if mid_d is None or ask_d is None or step is None:
        return None
    steps = mid_d / step
    frac = steps - steps.to_integral_value(rounding=ROUND_FLOOR)
    if frac == Decimal("0.5"):
        rounded = _quantize(mid_d, step, ROUND_FLOOR)
    else:
        rounded = _quantize(mid_d, step, ROUND_HALF_EVEN)
    if rounded > ask_d:
        return ask_d.quantize(step) if ask_d == _quantize(ask_d, step, ROUND_FLOOR) else _quantize(ask_d, step, ROUND_FLOOR)
    return rounded


def max_acceptable_debit_limit(*caps: Any) -> Decimal | None:
    """Independent chase cap: min of positive caps (ask, 2.5% NLV, fee ceiling)."""
    values = [v for v in (_as_decimal(c) for c in caps) if v is not None]
    if not values:
        return None
    return min(values)


def one_tick_replacement(
    first_limit: Any,
    live_ask: Any,
    max_debit: Any,
    tick: Any,
) -> Decimal | None:
    """First limit + 1 tick, or None if that would exceed live ask or max debit."""
    first = _as_decimal(first_limit)
    ask = _as_decimal(live_ask)
    cap = _as_decimal(max_debit)
    step = _as_decimal(tick)
    if first is None or ask is None or cap is None or step is None:
        return None
    candidate = first + step
    if candidate > ask or candidate > cap:
        return None
    return candidate.quantize(step)


def protective_stop_price(
    average_fill: Any,
    tick: Any | None = None,
    *,
    stop_frac: Any = "0.80",
    min_ticks: dict[str, Any] | None = None,
    asset: str = "option",
) -> Decimal | None:
    """80% of fill, rounded toward the fill (tighter). Never widen past 20%."""
    fill = _as_decimal(average_fill)
    frac = _as_decimal(stop_frac)
    if fill is None or frac is None:
        return None
    raw = fill * frac
    step = _as_decimal(tick)
    if step is None:
        if asset == "equity":
            step = EQUITY_TICK
        else:
            step = option_tick_size(raw, min_ticks)
    if step is None:
        return None
    return round_to_tick(raw, step, mode="toward_fill")


def as_price_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text else "0"
