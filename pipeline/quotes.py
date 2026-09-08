from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


UNDERLYING_MAX_AGE_SECONDS = 5
BOD_NLV_FIELD_CANDIDATES = (
    "start_of_day_equity",
    "beginning_of_day_equity",
    "bod_equity",
    "bod_nlv",
    "equity_start_of_day",
    "start_of_day_portfolio_value",
    "beginning_of_day_portfolio_value",
    "last_core_portfolio_equity",
    "last_core_equity",
)

_CALL_DIRECTIONS = frozenset({"call", "calls", "bullish", "long_call"})
_PUT_DIRECTIONS = frozenset({"put", "puts", "bearish", "long_put"})


def _parse_ts(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _positive_money(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        amount = float(str(value).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None
    if amount != amount or amount <= 0:
        return None
    return amount


def executable_underlying_price(
    quote: dict[str, Any] | None,
    *,
    direction: str,
    now: datetime | None = None,
    max_age_seconds: int = UNDERLYING_MAX_AGE_SECONDS,
) -> tuple[float | None, str | None]:
    """Live trigger price. Never treat last or midpoint as executable.

    Bullish / call: live underlying ask.
    Bearish / put: live underlying bid.
    Regular-session quote, no older than five seconds, positive bid and ask,
    bid ≤ ask.
    """
    side = (direction or "").strip().lower()
    if side not in _CALL_DIRECTIONS and side not in _PUT_DIRECTIONS:
        return None, "underlying_direction_missing"
    if not isinstance(quote, dict):
        return None, "underlying_quote_missing"
    bid = _positive_money(quote.get("bid_price", quote.get("bid")))
    ask = _positive_money(quote.get("ask_price", quote.get("ask")))
    if bid is None or ask is None:
        return None, "underlying_bid_ask_missing"
    if bid > ask:
        return None, "underlying_bid_above_ask"
    ts = _parse_ts(
        quote.get("updated_at")
        or quote.get("updated_at_utc")
        or quote.get("ask_time")
        or quote.get("bid_time")
        or quote.get("last_trade_time")
    )
    now = now or datetime.now(timezone.utc)
    if ts is None:
        return None, "underlying_quote_timestamp_missing"
    if now - ts > timedelta(seconds=max_age_seconds):
        return None, "underlying_quote_stale"
    if side in _CALL_DIRECTIONS:
        return ask, None
    return bid, None


FLAT_NO_FILLS_BOD_FIELD = "flat_no_fills_cash_equals_total_value"


def _money_allow_zero(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        amount = float(str(value).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None
    if amount != amount or amount < 0:
        return None
    return amount


def _cents(amount: float) -> int:
    return int(round(amount * 100))


def _portfolio_mappings(portfolio: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Unwrap MCP `data` / nested `equity` without inventing fields."""
    if not isinstance(portfolio, dict):
        return []
    mappings = [portfolio]
    data = portfolio.get("data")
    if isinstance(data, dict):
        mappings.append(data)
    extra: list[dict[str, Any]] = []
    for mapping in mappings:
        nested = mapping.get("equity")
        if isinstance(nested, dict):
            extra.append(nested)
    mappings.extend(extra)
    return mappings


def extract_bod_nlv(portfolio: dict[str, Any] | None) -> tuple[float | None, str | None]:
    """Return a broker beginning-of-day NLV if a known field is present. Never invent it."""
    mappings = _portfolio_mappings(portfolio)
    if not mappings:
        return None, None
    for mapping in mappings:
        for key in BOD_NLV_FIELD_CANDIDATES:
            if key in mapping:
                amount = _positive_money(mapping.get(key))
                if amount is None:
                    return None, key
                return amount, key
    return None, None


def resolve_bod_nlv(
    portfolio: dict[str, Any] | None,
    *,
    leftover: bool,
    fills_today: bool,
) -> tuple[float | None, str | None, str]:
    """BOD for a new entry. Broker field first; else flat cash==total_value with no fills.

    Midday `total_value` after a fill or leftover is not session-start NLV.
    `fills_today` must come from broker option and equity orders, not a model boolean.
    """
    amount, field = extract_bod_nlv(portfolio)
    if amount is not None and field:
        return amount, field, "ok"
    if leftover or fills_today:
        return None, None, "bod_nlv_unavailable"
    mappings = _portfolio_mappings(portfolio)
    if not mappings:
        return None, None, "bod_nlv_unavailable"
    cash = total = None
    pending: float | None = 0.0
    pending_seen = False
    for mapping in mappings:
        if cash is None and "cash" in mapping:
            cash = _positive_money(mapping.get("cash"))
        if total is None and "total_value" in mapping:
            total = _positive_money(mapping.get("total_value"))
        if not pending_seen and "pending_deposits" in mapping:
            pending_seen = True
            pending = _money_allow_zero(mapping.get("pending_deposits"))
    if cash is None or total is None:
        return None, None, "bod_nlv_unavailable"
    if pending_seen and pending is None:
        return None, None, "bod_nlv_unavailable"
    if pending is not None and pending > 0:
        return None, None, "bod_nlv_unavailable"
    if _cents(cash) != _cents(total):
        return None, None, "bod_nlv_unavailable"
    return cash, FLAT_NO_FILLS_BOD_FIELD, "ok"
