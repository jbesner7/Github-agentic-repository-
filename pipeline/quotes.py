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


def extract_bod_nlv(portfolio: dict[str, Any] | None) -> tuple[float | None, str | None]:
    """Return a broker beginning-of-day NLV if a known field is present. Never invent it."""
    if not isinstance(portfolio, dict):
        return None, None
    mappings = [portfolio]
    nested = portfolio.get("equity")
    if isinstance(nested, dict):
        mappings.append(nested)
    for mapping in mappings:
        for key in BOD_NLV_FIELD_CANDIDATES:
            if key in mapping:
                amount = _positive_money(mapping.get(key))
                if amount is None:
                    return None, key
                return amount, key
    return None, None
