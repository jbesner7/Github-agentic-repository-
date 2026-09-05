from __future__ import annotations

import re
from math import floor
from typing import Any

from pipeline.risk import equity_risk_plan

# Inverse / leveraged-short ETFs. Long index ETFs (SPY, VTI, QQQ) are allowed.
INVERSE_ETF_SYMBOLS = frozenset(
    {
        "SH",
        "SDS",
        "SPXU",
        "SPXS",
        "SPDN",
        "PSQ",
        "QID",
        "SQQQ",
        "DOG",
        "DXD",
        "SDOW",
        "TZA",
        "FAZ",
        "SOXS",
        "LABD",
        "YANG",
        "SCO",
        "DUG",
        "DUST",
        "JDST",
        "WEBS",
        "HIBS",
        "SARK",
        "RWM",
        "TWM",
        "HDGE",
        "EFZ",
        "EPV",
        "MYY",
        "MZZ",
        "BIS",
        "SRTY",
        "TYO",
        "KOLD",
        "SBB",
        "SEF",
        "SIJ",
        "SKF",
    }
)


# One-word UltraShort / Inverse names. Do not match "ultra short" (short-duration bond funds).
_INVERSE_NAME_RE = re.compile(
    r"\b(?:inverse|ultrashort|ultrapro\s+short|leveraged\s+inverse)\b",
    re.IGNORECASE,
)


def is_inverse_etf(symbol: str, fundamentals: dict[str, Any] | None = None) -> bool:
    if (symbol or "").strip().upper() in INVERSE_ETF_SYMBOLS:
        return True
    fund = fundamentals or {}
    blob = " ".join(
        str(fund.get(k) or "")
        for k in ("description", "name", "security_name", "instrument_name")
    )
    return bool(_INVERSE_NAME_RE.search(blob))


def parse_bid_ask(quote: dict[str, Any] | None) -> tuple[float | None, float | None]:
    if not quote:
        return None, None

    def _num(*keys: str) -> float | None:
        for key in keys:
            if key in quote and quote[key] not in (None, ""):
                try:
                    return float(quote[key])
                except (TypeError, ValueError):
                    continue
        return None

    bid = _num("bid_price", "bid", "bid_last")
    ask = _num("ask_price", "ask", "ask_last")
    return bid, ask


def equity_quote_ok(
    quote: dict[str, Any] | None,
    *,
    reject_one_sided: bool = True,
) -> tuple[bool, str | None, dict[str, Any]]:
    bid, ask = parse_bid_ask(quote)
    metrics: dict[str, Any] = {"bid": bid, "ask": ask}
    if bid is None or ask is None:
        return False, "missing_bid_ask", metrics
    if reject_one_sided and (bid <= 0 or ask <= 0):
        return False, "one_sided_or_missing_quote", metrics
    if ask < bid:
        return False, "crossed_quote", metrics
    mid = (bid + ask) / 2.0
    metrics["mid"] = mid
    metrics["spread"] = ask - bid
    return True, None, metrics


def regular_hours_buy_ok(tradability: dict[str, Any] | None) -> tuple[bool, str | None]:
    if not tradability:
        return False, "missing_tradability"
    if tradability.get("halted") is True:
        return False, "halted"
    rh = (
        tradability.get("regular_hours")
        or tradability.get("session_regular_hours")
        or tradability.get("regular")
        or {}
    )
    if isinstance(rh, dict) and rh:
        buy = rh.get("buy")
        if buy is False:
            return False, "regular_hours_buy_false"
        if buy is True:
            return True, None
        tradable = rh.get("tradable")
        if tradable is False:
            return False, "regular_hours_not_tradable"
        if tradable is True:
            return True, None
    for key in ("tradable", "is_tradable", "can_trade"):
        if tradability.get(key) is False:
            return False, "not_tradable"
        if tradability.get(key) is True:
            return True, None
    return False, "regular_hours_buy_not_confirmed"


def whole_share_size(buying_power: float, limit_price: float) -> dict[str, Any]:
    """shares = floor(buying_power / limit). Notional must be ≤ buying power."""
    if buying_power is None or limit_price is None:
        return {"ok": False, "shares": 0, "notional": 0.0, "reason": "invalid_price_or_buying_power"}
    try:
        bp = float(buying_power)
        limit = float(limit_price)
    except (TypeError, ValueError):
        return {"ok": False, "shares": 0, "notional": 0.0, "reason": "invalid_price_or_buying_power"}
    if bp <= 0 or limit <= 0:
        return {"ok": False, "shares": 0, "notional": 0.0, "reason": "invalid_price_or_buying_power"}
    shares = int(floor(bp / limit))
    notional = shares * limit
    if shares < 1:
        return {"ok": False, "shares": 0, "notional": 0.0, "reason": "cannot_afford_one_share"}
    if notional > bp + 1e-9:
        return {"ok": False, "shares": shares, "notional": notional, "reason": "notional_exceeds_buying_power"}
    return {"ok": True, "shares": shares, "notional": notional, "reason": None}


def buying_power_from_raw(raw: dict[str, Any]) -> float | None:
    portfolio = raw.get("portfolio") if isinstance(raw.get("portfolio"), dict) else {}
    for value in (
        raw.get("buying_power"),
        portfolio.get("buying_power"),
        portfolio.get("buying_power_usd"),
    ):
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def select_equity_day_trade_candidates(
    *,
    symbols: list[str],
    technicals_by_symbol: dict[str, Any],
    option_candidate_symbols: set[str],
    quotes_by_symbol: dict[str, Any],
    tradability_by_symbol: dict[str, Any],
    fundamentals_by_symbol: dict[str, Any],
    buying_power: float | None,
    playbook_status: str,
    take_profit_pct: float,
    stop_loss_pct: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Bullish long-share day-trade candidates. Never shorts. Options-first skip."""
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for symbol in symbols:
        bias = (technicals_by_symbol.get(symbol) or {}).get("dominant_bias")
        fund = fundamentals_by_symbol.get(symbol) or {}
        if is_inverse_etf(symbol, fund):
            rejected.append({"symbol": symbol, "reason": "inverse_etf", "bias": bias})
            continue
        if symbol in option_candidate_symbols:
            rejected.append({"symbol": symbol, "reason": "options_priority", "bias": bias})
            continue
        if bias != "bullish":
            rejected.append({"symbol": symbol, "reason": "equity_long_only_requires_bullish", "bias": bias})
            continue
        ok_tr, tr_reason = regular_hours_buy_ok(tradability_by_symbol.get(symbol))
        if not ok_tr:
            rejected.append({"symbol": symbol, "reason": tr_reason, "bias": bias})
            continue
        ok_q, q_reason, q_metrics = equity_quote_ok(quotes_by_symbol.get(symbol))
        if not ok_q:
            rejected.append({"symbol": symbol, "reason": q_reason, "bias": bias, **q_metrics})
            continue
        if buying_power is None:
            rejected.append({"symbol": symbol, "reason": "missing_buying_power", "bias": bias})
            continue
        limit = float(q_metrics["ask"])
        size = whole_share_size(buying_power, limit)
        if not size["ok"]:
            rejected.append({"symbol": symbol, "reason": size["reason"], "bias": bias, "limit": limit, "buying_power": buying_power})
            continue
        plan = equity_risk_plan(
            cost_basis=float(size["notional"]),
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            shares=size["shares"],
            limit_price=limit,
        )
        candidates.append(
            {
                "symbol": symbol,
                "structure": "long_shares",
                "side": "buy",
                "bias": bias,
                "quantity": size["shares"],
                "limit_price": limit,
                "notional": size["notional"],
                "buying_power": buying_power,
                "bid": q_metrics["bid"],
                "ask": q_metrics["ask"],
                "order_type": "limit",
                "time_in_force": "gfd",
                "market_hours": "regular_hours",
                "playbook_status": playbook_status,
                "risk": plan,
            }
        )
    return candidates, rejected
