"""Valid-tick rounding for option and equity prices.

Parse the broker-returned `min_ticks` structure exactly. Never infer a tick
from the premium. Equity day-trade stops use a $0.01 tick.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN
from typing import Any


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


def _band_bound(row: dict[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            try:
                amount = Decimal(str(row.get(key)).replace("$", "").replace(",", "").strip())
            except Exception:
                return None
            if amount != amount or amount < 0:
                return None
            return amount
    return None


def parse_min_ticks(min_ticks: Any) -> dict[str, Any] | None:
    """Normalize a broker `min_ticks` payload. None if it is missing or ambiguous."""
    if min_ticks in (None, "", {}, []):
        return None
    if isinstance(min_ticks, (int, float, str, Decimal)):
        step = _as_decimal(min_ticks)
        if step is None:
            return None
        return {"kind": "scalar", "tick": step}
    if isinstance(min_ticks, dict):
        cutoff = min_ticks.get("cutoff_price")
        below = min_ticks.get("below_tick")
        above = min_ticks.get("above_tick")
        has_cutoff_shape = any(v not in (None, "") for v in (cutoff, below, above))
        if has_cutoff_shape:
            cutoff_d = _as_decimal(cutoff)
            below_d = _as_decimal(below)
            above_d = _as_decimal(above)
            if cutoff_d is None or below_d is None or above_d is None:
                return None
            return {
                "kind": "cutoff",
                "cutoff_price": cutoff_d,
                "below_tick": below_d,
                "above_tick": above_d,
            }
        scalar = _as_decimal(
            min_ticks.get("increment", min_ticks.get("tick", min_ticks.get("min_tick")))
        )
        extra = {
            key
            for key in min_ticks
            if key not in {"increment", "tick", "min_tick"} and min_ticks.get(key) not in (None, "")
        }
        if scalar is not None and not extra:
            return {"kind": "scalar", "tick": scalar}
        return None
    if isinstance(min_ticks, list):
        bands: list[tuple[Decimal, Decimal, str]] = []
        for row in min_ticks:
            if not isinstance(row, dict):
                return None
            tick = _as_decimal(row.get("tick", row.get("increment", row.get("min_tick"))))
            if tick is None:
                return None
            above = _band_bound(row, "above_price", "min_price", "gte", "from_price")
            below = _band_bound(row, "below_price", "max_price", "lt", "to_price")
            if above is not None and below is None:
                bands.append((above, tick, "gte"))
            elif below is not None and above is None:
                bands.append((below, tick, "lt"))
            else:
                return None
        if not bands:
            return None
        return {"kind": "schedule", "bands": bands}
    return None


def option_tick_size(price: Any, min_ticks: Any = None) -> Decimal | None:
    """Tick for a premium from the parsed broker structure only. Never infer typical RH ticks."""
    px = _as_decimal(price)
    parsed = parse_min_ticks(min_ticks)
    if px is None or parsed is None:
        return None
    kind = parsed["kind"]
    if kind == "scalar":
        return parsed["tick"]
    if kind == "cutoff":
        return parsed["below_tick"] if px < parsed["cutoff_price"] else parsed["above_tick"]
    if kind == "schedule":
        gte = [(bound, tick) for bound, tick, op in parsed["bands"] if op == "gte" and px >= bound]
        lt = [(bound, tick) for bound, tick, op in parsed["bands"] if op == "lt" and px < bound]
        chosen: list[Decimal] = []
        if gte:
            chosen.append(max(gte, key=lambda item: item[0])[1])
        if lt:
            chosen.append(min(lt, key=lambda item: item[0])[1])
        unique = set(chosen)
        if len(unique) != 1:
            return None
        return next(iter(unique))
    return None


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


def max_acceptable_debit_limit(
    *caps: Any,
    min_ticks: Any = None,
    tick: Any = None,
) -> Decimal | None:
    """Independent chase cap: tick-floored min of ask, 2.5% NLV, and fee ceiling.

    Floor so an off-grid NLV or fee cap cannot become the entry limit.
    Requires a parsed broker tick. Never infer one from the premium.
    """
    values = [v for v in (_as_decimal(c) for c in caps) if v is not None]
    if not values:
        return None
    raw = min(values)
    step = _as_decimal(tick)
    if step is None:
        step = option_tick_size(raw, min_ticks)
    if step is None:
        return None
    floored = round_to_tick(raw, step, mode="down")
    if floored is None or floored <= 0:
        return None
    return floored


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
    min_ticks: Any = None,
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


def stop_usable_versus_live_bid(
    raw_stop: Any,
    rounded_stop: Any,
    live_bid: Any,
) -> tuple[bool, str | None]:
    """Rounded stop must stay below the live option bid.

    If the bid is already at or below the raw or rounded threshold, do not
    place a stale stop.
    """
    bid = _as_decimal(live_bid)
    rounded = _as_decimal(rounded_stop)
    raw = _as_decimal(raw_stop)
    if bid is None or rounded is None:
        return False, "stop_or_bid_unreadable"
    if raw is not None and bid <= raw:
        return False, "live_bid_at_or_below_raw_stop"
    if bid <= rounded:
        return False, "live_bid_at_or_below_rounded_stop"
    return True, None


def as_price_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text else "0"
