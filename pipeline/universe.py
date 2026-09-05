from __future__ import annotations

from typing import Any

from pipeline.equity_day_trade import is_inverse_etf


CRYPTO_OBJECT_TYPES = {"currency_pair", "tokenized_stock"}
EQUITY_OBJECT_TYPES = {"instrument"}
INDEX_OBJECT_TYPES = {"index"}
OPTION_OBJECT_TYPES = {"option_strategy", "option"}


def _normalize_symbol(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().upper()


def extract_watchlist_symbols(
    watchlists: list[dict[str, Any]],
    items_by_list: dict[str, list[dict[str, Any]]],
    option_watchlist_items: list[dict[str, Any]] | None,
    *,
    include_crypto: bool = False,
    include_options_watchlist: bool = True,
) -> dict[str, Any]:
    """Agent A: union symbols from all lists; exclude crypto unless enabled."""
    equities: dict[str, dict[str, Any]] = {}
    indexes: dict[str, dict[str, Any]] = {}
    skipped_crypto: list[str] = []
    sources: dict[str, list[str]] = {}

    for wl in watchlists:
        list_id = wl.get("id")
        name = wl.get("display_name") or list_id
        for item in items_by_list.get(list_id, []):
            obj_type = (item.get("object_type") or item.get("type") or "").lower()
            symbol = _normalize_symbol(
                item.get("symbol")
                or item.get("display_symbol")
                or item.get("equity_symbol")
                or item.get("chain_symbol")
            )
            if not symbol:
                continue
            sources.setdefault(symbol, [])
            if name not in sources[symbol]:
                sources[symbol].append(str(name))

            if obj_type in CRYPTO_OBJECT_TYPES or (not obj_type and "-" in symbol and symbol.endswith("USD")):
                if not include_crypto:
                    skipped_crypto.append(symbol)
                    continue
            if obj_type in INDEX_OBJECT_TYPES:
                indexes[symbol] = {"symbol": symbol, "object_type": "index", "sources": sources[symbol]}
            elif obj_type in OPTION_OBJECT_TYPES:
                # Options watchlist handled separately; still capture underlying if present.
                und = _normalize_symbol(item.get("chain_symbol") or item.get("underlying_symbol"))
                if und:
                    equities.setdefault(und, {"symbol": und, "object_type": "instrument", "sources": sources.get(und, [str(name)])})
            else:
                # Default: treat as equity/ETF instrument.
                equities[symbol] = {"symbol": symbol, "object_type": "instrument", "sources": sources[symbol]}

    option_underlyings: list[str] = []
    if include_options_watchlist and option_watchlist_items:
        for item in option_watchlist_items:
            und = _normalize_symbol(
                item.get("chain_symbol")
                or item.get("underlying_symbol")
                or item.get("symbol")
            )
            if und:
                option_underlyings.append(und)
                equities.setdefault(
                    und,
                    {"symbol": und, "object_type": "instrument", "sources": ["Options Watchlist"]},
                )

    return {
        "equities": sorted(equities.values(), key=lambda x: x["symbol"]),
        "indexes": sorted(indexes.values(), key=lambda x: x["symbol"]),
        "option_watchlist_underlyings": sorted(set(option_underlyings)),
        "skipped_crypto": sorted(set(skipped_crypto)),
        "equity_symbols": sorted(equities.keys()),
        "index_symbols": sorted(indexes.keys()),
    }


def apply_liquidity_filter(
    symbols: list[str],
    fundamentals_by_symbol: dict[str, dict[str, Any]],
    *,
    min_average_volume: float,
) -> dict[str, Any]:
    """Filter equities by average volume from fundamentals payloads."""
    passed: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for symbol in symbols:
        fund = fundamentals_by_symbol.get(symbol) or {}
        if is_inverse_etf(symbol, fund):
            rejected.append({"symbol": symbol, "reason": "inverse_etf"})
            continue
        # RH fundamentals field names can vary; accept common keys only if present.
        avg_vol = None
        for key in (
            "average_volume",
            "average_volume_2_weeks",
            "avg_volume",
            "volume",
        ):
            if key in fund and fund[key] not in (None, ""):
                try:
                    avg_vol = float(fund[key])
                    break
                except (TypeError, ValueError):
                    continue
        if avg_vol is None:
            rejected.append({"symbol": symbol, "reason": "missing_average_volume", "average_volume": None})
            continue
        if avg_vol < min_average_volume:
            rejected.append(
                {
                    "symbol": symbol,
                    "reason": "below_min_average_volume",
                    "average_volume": avg_vol,
                    "min_average_volume": min_average_volume,
                }
            )
            continue
        passed.append({"symbol": symbol, "average_volume": avg_vol})

    return {
        "passed": passed,
        "rejected": rejected,
        "passed_symbols": [p["symbol"] for p in passed],
    }


def option_quote_liquid(
    quote: dict[str, Any],
    *,
    max_spread_pct_of_price: float,
    preferred_spread_pct_of_price: float = 0.05,
    reject_one_sided: bool = True,
) -> tuple[bool, str | None, dict[str, Any]]:
    """Return (ok, reason, metrics) for an option quote liquidity gate.

    Spread is measured as (ask − bid) / mid. Prefer ≤ 5% of price; reject above 10%.
    There is no absolute-dollar override.
    """
    if not quote:
        return False, "missing_bid_ask", {}

    def _px(*keys: str) -> float | None:
        for key in keys:
            if key in quote and quote[key] not in (None, ""):
                try:
                    return float(quote[key])
                except (TypeError, ValueError):
                    continue
        return None

    bid = _px("bid_price", "bid", "bid_last")
    ask = _px("ask_price", "ask", "ask_last")
    if bid is None or ask is None:
        return False, "missing_bid_ask", {"bid": bid, "ask": ask}

    if reject_one_sided and (bid <= 0 or ask <= 0):
        return False, "one_sided_or_missing_quote", {"bid": bid, "ask": ask}

    mid = (bid + ask) / 2.0
    spread = ask - bid
    spread_pct = (spread / mid) if mid > 0 else None
    metrics: dict[str, Any] = {
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread": spread,
        "spread_pct_of_price": spread_pct,
        "spread_pct_of_mid": spread_pct,
        "preferred_spread_pct_of_price": preferred_spread_pct_of_price,
        "max_spread_pct_of_price": max_spread_pct_of_price,
    }

    if mid <= 0:
        return False, "non_positive_mid", metrics
    if spread_pct is None:
        return False, "spread_too_wide", metrics
    if spread_pct <= preferred_spread_pct_of_price:
        metrics["spread_quality"] = "preferred"
        return True, None, metrics
    if spread_pct <= max_spread_pct_of_price:
        metrics["spread_quality"] = "acceptable"
        return True, None, metrics
    metrics["spread_quality"] = "too_wide"
    return False, "spread_too_wide", metrics
