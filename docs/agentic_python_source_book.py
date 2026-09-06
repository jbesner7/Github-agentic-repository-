# ruff: noqa
# pylint: skip-file
"""PRINTABLE SOURCE BOOK — do not import or execute this file.

Agentic trading program: Agent F (supervised Cursor chat) and
Agent H (autonomous Agentic bot) share this Python pipeline.
Live place_* is Robinhood MCP, not a side effect of this code.
H's standing prompt is playbooks/agent_h_autonomous.PROMPT.md (not Python).

Generated: 2026-09-06T00:02:28+00:00
Print companion: docs/agentic-python-source-printable.html
"""

# ========================================================================
# pipeline/__init__.py
# Part: 0 · Package
# Used by: F + H
# Pipeline package marker
# ========================================================================

"""Phase 2 read-only signal pipeline (Agents A–E + I)."""

__version__ = "0.2.0"

# ========================================================================
# pipeline/io_util.py
# Part: 1 · Shared
# Used by: F + H
# Paths, rules.json loader, journal helpers
# ========================================================================

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SIGNALS = ROOT / "signals"
JOURNAL = ROOT / "journal"
DATA_RAW = ROOT / "data" / "raw"
CONFIG = ROOT / "config" / "rules.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_rules() -> dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def append_jsonl(path: Path, row: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=False) + "\n")
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

# ========================================================================
# pipeline/session.py
# Part: 1 · Shared
# Used by: F + H
# RTH clock; option entries 09:45–15:45; equity entries to 15:45
# ========================================================================

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from typing import Any

ET = ZoneInfo("America/New_York")
RTH_START = time(9, 30)
RTH_END = time(16, 0)
NO_NEW_OPTION_ENTRIES_BEFORE = time(9, 45)
NO_NEW_ENTRIES_AFTER = time(15, 45)


def now_et(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(ET)
    if now.tzinfo is None:
        return now.replace(tzinfo=ET)
    return now.astimezone(ET)


def today_et(now: datetime | None = None) -> date:
    """Calendar date in America/New_York. Do not use UTC date.today() for DTE or journals."""
    return now_et(now).date()


def is_weekday(now: datetime | None = None) -> bool:
    return now_et(now).weekday() < 5


def is_rth(now: datetime | None = None) -> bool:
    """Mon–Fri 09:30 inclusive through 16:00 exclusive America/New_York."""
    dt = now_et(now)
    if not is_weekday(dt):
        return False
    t = dt.time()
    return RTH_START <= t < RTH_END


def entries_open(now: datetime | None = None) -> bool:
    """Equity / generic new entries: RTH before 15:45 ET."""
    dt = now_et(now)
    if not is_rth(dt):
        return False
    return dt.time() < NO_NEW_ENTRIES_AFTER


def option_entries_open(now: datetime | None = None) -> bool:
    """New option entries: RTH from 09:45 inclusive through 15:45 exclusive ET."""
    dt = now_et(now)
    if not entries_open(dt):
        return False
    return dt.time() >= NO_NEW_OPTION_ENTRIES_BEFORE


def flatten_window(now: datetime | None = None) -> bool:
    """Still RTH, but new entries are closed (15:45–16:00 ET)."""
    dt = now_et(now)
    if not is_rth(dt):
        return False
    return dt.time() >= NO_NEW_ENTRIES_AFTER


def session_gate(now: datetime | None = None) -> dict[str, Any]:
    dt = now_et(now)
    rth = is_rth(dt)
    open_for_entry = entries_open(dt)
    option_open = option_entries_open(dt)
    reason = None
    if not rth:
        reason = "outside_rth"
    elif not open_for_entry:
        reason = "no_new_entries_after_1545"
    option_reason = None
    if not rth:
        option_reason = "outside_rth"
    elif dt.time() < NO_NEW_OPTION_ENTRIES_BEFORE:
        option_reason = "no_new_option_entries_before_0945"
    elif not open_for_entry:
        option_reason = "no_new_entries_after_1545"
    return {
        "timezone": "America/New_York",
        "now_et": dt.isoformat(),
        "is_rth": rth,
        "entries_open": open_for_entry,
        "option_entries_open": option_open,
        "flatten_window": flatten_window(dt),
        "reason": reason,
        "option_reason": option_reason,
    }

# ========================================================================
# pipeline/orders.py
# Part: 1 · Shared
# Used by: F + H
# Working-order states for Robinhood MCP (no open=true)
# ========================================================================

from __future__ import annotations

from typing import Any, Iterable

# Robinhood MCP has no `open=true` filter. Working tickets are these states.
OPTION_WORKING_STATES = frozenset(
    {"queued", "confirmed", "partially_filled", "pending_cancelled"}
)
EQUITY_WORKING_STATES = frozenset(
    {"new", "queued", "confirmed", "unconfirmed", "partially_filled"}
)


def normalize_state(value: Any) -> str:
    return str(value or "").strip().lower()


def is_working_option_state(state: Any) -> bool:
    return normalize_state(state) in OPTION_WORKING_STATES


def is_working_equity_state(state: Any) -> bool:
    return normalize_state(state) in EQUITY_WORKING_STATES


def working_orders(
    option_orders: Iterable[dict[str, Any]] | None = None,
    equity_orders: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for row in option_orders or []:
        if is_working_option_state(row.get("state") or row.get("status")):
            found.append({"asset_class": "option", **row})
    for row in equity_orders or []:
        if is_working_equity_state(row.get("state") or row.get("status")):
            found.append({"asset_class": "equity", **row})
    return found


def has_working_orders(
    option_orders: Iterable[dict[str, Any]] | None = None,
    equity_orders: Iterable[dict[str, Any]] | None = None,
) -> bool:
    return bool(working_orders(option_orders, equity_orders))

# ========================================================================
# pipeline/quotes.py
# Part: 1 · Shared
# Used by: F + H
# 5s underlying executable price; BOD NLV field extract
# ========================================================================

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
    now: datetime | None = None,
    max_age_seconds: int = UNDERLYING_MAX_AGE_SECONDS,
) -> tuple[float | None, str | None]:
    """Regular-session executable price for the live breakout trigger."""
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
    last = _positive_money(quote.get("last_trade_price", quote.get("last_price", quote.get("last"))))
    if last is not None and bid <= last <= ask:
        return last, None
    return (bid + ask) / 2.0, None


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

# ========================================================================
# pipeline/fees.py
# Part: 1 · Shared
# Used by: F + H
# Dual fee ceilings: 0.49% planned loss and 0.50% with fees
# ========================================================================

from __future__ import annotations

from typing import Any

# Named leaf fees. Do not include totals or group subtotals here.
COMPONENT_KEYS = frozenset(
    {
        "commission",
        "commissions",
        "regulatory_fee",
        "regulatory_fees",
        "regulatory",
        "sec_fee",
        "sec_fees",
        "taf_fee",
        "taf_fees",
        "option_regulatory_fee",
        "orf",
        "orf_fee",
        "contract_fee",
        "contract_fees",
        "per_contract_fee",
        "exchange_fee",
        "exchange_fees",
        "clearing_fee",
        "clearing_fees",
    }
)

# Group keys that likely already include one or more COMPONENT_KEYS.
COMPONENT_FAMILIES: tuple[frozenset[str], ...] = (
    frozenset({"commission", "commissions"}),
    frozenset(
        {
            "regulatory_fee",
            "regulatory_fees",
            "regulatory",
            "sec_fee",
            "sec_fees",
            "taf_fee",
            "taf_fees",
            "option_regulatory_fee",
            "orf",
            "orf_fee",
        }
    ),
    frozenset({"contract_fee", "contract_fees", "per_contract_fee"}),
    frozenset({"exchange_fee", "exchange_fees"}),
    frozenset({"clearing_fee", "clearing_fees"}),
)

# Alternate totals / rolled-up fees that must not be added to their parts.
SUBTOTAL_KEYS = frozenset(
    {"fee", "estimated_fee", "estimated_fees", "fee_total", "fees_total"}
)

PLANNED_LOSS_CEILING_WITH_QUOTED_FEE = 0.005
PLANNED_LOSS_CEILING_IF_FEE_UNAVAILABLE_OR_ZERO = 0.0049


def parse_money(value: Any) -> tuple[float | None, bool]:
    """Return (amount, readable). readable is False when the field cannot be used."""
    if value is None:
        return None, True
    if isinstance(value, bool):
        return None, False
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):  # NaN / inf
            return None, False
        return float(value), True
    if isinstance(value, str):
        text = value.strip().replace("$", "").replace(",", "")
        if text == "":
            return None, True
        try:
            amount = float(text)
        except ValueError:
            return None, False
        if amount != amount or amount in (float("inf"), float("-inf")):
            return None, False
        return amount, True
    return None, False


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "fee_status": "unavailable",
        "entry_fee": None,
        "journal": "fee_unavailable",
        "source": reason,
        "apply_049_ceiling": True,
        "estimated_exit_fee": None,
        "estimated_round_trip_fees": None,
    }


def _explicit_zero(source: str) -> dict[str, Any]:
    return {
        "fee_status": "explicit_zero",
        "entry_fee": 0.0,
        "journal": "fee_explicit_zero",
        "source": source,
        "apply_049_ceiling": True,
        "estimated_exit_fee": None,
        "estimated_round_trip_fees": None,
    }


def _quoted(entry_fee: float, source: str) -> dict[str, Any]:
    return {
        "fee_status": "quoted",
        "entry_fee": entry_fee,
        "journal": source,
        "source": source,
        "apply_049_ceiling": True,
        "estimated_exit_fee": 2.0 * entry_fee,
        "estimated_round_trip_fees": 3.0 * entry_fee,
    }


def _conflict(source: str) -> dict[str, Any]:
    return {
        "fee_status": "ambiguous",
        "entry_fee": None,
        "journal": "fee_conflict",
        "source": source,
        "apply_049_ceiling": True,
        "estimated_exit_fee": None,
        "estimated_round_trip_fees": None,
    }


def _fee_mappings(review: Any) -> list[dict[str, Any]]:
    if not isinstance(review, dict):
        return []
    mappings = [review]
    nested = review.get("fees")
    if isinstance(nested, dict):
        mappings.append(nested)
    return mappings


def _list_components(review: Any) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if not isinstance(review, dict):
        return rows
    nested = review.get("fees")
    if not isinstance(nested, list):
        return rows
    for item in nested:
        if not isinstance(item, dict):
            continue
        name = str(
            item.get("type")
            or item.get("name")
            or item.get("label")
            or item.get("key")
            or ""
        ).strip().lower()
        amount = item.get("amount", item.get("fee", item.get("value")))
        if name:
            rows.append((name, amount))
    return rows


def _first_total(mappings: list[dict[str, Any]]) -> tuple[Any, bool]:
    """Return (raw_value, present). Prefer total_fee over aliases."""
    present = False
    raw: Any = None
    for mapping in mappings:
        if "total_fee" in mapping:
            return mapping["total_fee"], True
        if "total_fees" in mapping and not present:
            raw = mapping["total_fees"]
            present = True
        if mapping.get("total") is not None and "commission" in mapping and not present:
            # Nested RH-style {total, commission, ...}
            raw = mapping["total"]
            present = True
    return raw, present


def _component_values(mappings: list[dict[str, Any]], extra: list[tuple[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for mapping in mappings:
        for key in COMPONENT_KEYS:
            if key in mapping:
                values[key] = mapping[key]
    for name, amount in extra:
        if name in COMPONENT_KEYS:
            values[name] = amount
        elif name in {"sec", "taf", "orf"}:
            values[f"{name}_fee"] = amount
    return values


def _subtotal_values(mappings: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for mapping in mappings:
        for key in SUBTOTAL_KEYS:
            if key in mapping:
                values[key] = mapping[key]
    return values


def _parsed_items(raw_items: dict[str, Any]) -> tuple[dict[str, float], str | None]:
    parsed: dict[str, float] = {}
    for key, raw in raw_items.items():
        amount, readable = parse_money(raw)
        if not readable:
            return {}, "unreadable"
        if amount is None:
            continue
        if amount < 0:
            return {}, "negative"
        parsed[key] = amount
    return parsed, None


def _components_overlap(keys: set[str]) -> bool:
    for family in COMPONENT_FAMILIES:
        hit = keys & family
        if len(hit) <= 1:
            continue
        group = hit & {
            "commission",
            "commissions",
            "regulatory_fee",
            "regulatory_fees",
            "regulatory",
            "contract_fee",
            "contract_fees",
            "exchange_fee",
            "exchange_fees",
            "clearing_fee",
            "clearing_fees",
        }
        parts = hit - group
        if group and parts:
            return True
        if len(hit & {"commission", "commissions"}) == 2:
            return True
        if len(hit & {"contract_fee", "contract_fees", "per_contract_fee"}) > 1 and not parts:
            # two names for the same contract fee
            if len(hit & {"contract_fee", "contract_fees"}) == 2:
                return True
    return False


def classify_review_fees(review: Any) -> dict[str, Any]:
    """Parse review_option_order fees. Never trust $0.00 total with positive parts."""
    if review is None or not isinstance(review, dict):
        return _unavailable("review_unreadable")

    mappings = _fee_mappings(review)
    raw_total, total_present = _first_total(mappings)
    components_raw = _component_values(mappings, _list_components(review))
    subtotals_raw = _subtotal_values(mappings)

    if total_present:
        total, readable = parse_money(raw_total)
        if not readable or total is None or total < 0:
            return _unavailable("total_fee_unreadable")

        components, error = _parsed_items(components_raw)
        if error:
            return _unavailable(f"component_{error}")

        if total > 0:
            return _quoted(total, "total_fee")

        positive = {key: amount for key, amount in components.items() if amount > 0}
        if positive:
            return _conflict(
                "zero_total_plus_positive_component:" + ",".join(sorted(positive))
            )
        return _explicit_zero("total_fee_and_components_zero_or_absent")

    components, error = _parsed_items(components_raw)
    if error:
        return _unavailable(f"component_{error}")
    subtotals, error = _parsed_items(subtotals_raw)
    if error:
        return _unavailable(f"subtotal_{error}")

    if subtotals and components:
        return _unavailable("subtotal_plus_parts")
    if _components_overlap(set(components)):
        return _unavailable("overlapping_components")

    if subtotals:
        values = list(subtotals.values())
        if len(set(values)) > 1:
            return _unavailable("duplicated_subtotals")
        amount = values[0]
        source = next(iter(subtotals))
        if amount > 0:
            return _quoted(amount, source)
        return _explicit_zero(source)

    if components:
        amount = sum(components.values())
        source = "components:" + ",".join(sorted(components))
        if amount > 0:
            return _quoted(amount, source)
        return _explicit_zero(source)

    return _unavailable("no_fee_fields")


def fee_aware_planned_loss_ok(
    *,
    planned_loss: float,
    current_nlv: float,
    classification: dict[str, Any],
) -> bool:
    """Both ceilings apply on every trade. Missing fees count as $0 in the 0.50% sum."""
    if current_nlv <= 0 or planned_loss < 0:
        return False
    if planned_loss > PLANNED_LOSS_CEILING_IF_FEE_UNAVAILABLE_OR_ZERO * current_nlv + 1e-12:
        return False
    round_trip = classification.get("estimated_round_trip_fees")
    if not isinstance(round_trip, (int, float)):
        round_trip = 0.0
    if float(round_trip) < 0:
        return False
    return (
        planned_loss + float(round_trip)
        <= PLANNED_LOSS_CEILING_WITH_QUOTED_FEE * current_nlv + 1e-12
    )

# ========================================================================
# pipeline/universe.py
# Part: 2 · Agent A
# Used by: F + H
# Watchlist extract, crypto drop, inverse-ETF reject, ADV ≥ 2,000,000
# ========================================================================

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

# ========================================================================
# pipeline/patterns.py
# Part: 3 · Agent B
# Used by: F + H
# Daily-first H&S / double-triple / triangle; no 1m/3m/5m
# ========================================================================

from __future__ import annotations

from typing import Any

import numpy as np


def _local_extrema(prices: np.ndarray, order: int = 3) -> tuple[list[int], list[int]]:
    """Simple peak/trough detection with `order` bars on each side."""
    peaks: list[int] = []
    troughs: list[int] = []
    n = len(prices)
    for i in range(order, n - order):
        window = prices[i - order : i + order + 1]
        if prices[i] == window.max() and np.sum(window == prices[i]) == 1:
            peaks.append(i)
        if prices[i] == window.min() and np.sum(window == prices[i]) == 1:
            troughs.append(i)
    return peaks, troughs


def _nearly_equal(a: float, b: float, tol_pct: float = 0.015) -> bool:
    base = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / base <= tol_pct


PATTERN_PRIORITY = (
    "inverse_head_and_shoulders",
    "head_and_shoulders",
    "double_bottom",
    "double_top",
    "triple_bottom",
    "triple_top",
    "ascending_triangle",
    "descending_triangle",
)
PATTERN_FAMILY = {
    "inverse_head_and_shoulders": 0,
    "head_and_shoulders": 0,
    "double_bottom": 1,
    "double_top": 1,
    "triple_bottom": 1,
    "triple_top": 1,
    "ascending_triangle": 2,
    "descending_triangle": 2,
}

HEAD_PROMINENCE_PCT = 0.015
MIN_PIVOT_SEPARATION_BARS = 3
MAX_PATTERN_BARS = {
    "day": 60,
    "daily": 60,
    "hour": 40,
    "10minute": 30,
}
TRIANGLE_TOUCH_PCT = 0.005
TRIANGLE_MIN_TOUCHES_PER_SIDE = 2


def _max_pattern_bars(timeframe: str) -> int:
    return MAX_PATTERN_BARS.get(timeframe, 60)


def _pivots_separated(indices: list[int], *, min_gap: int = MIN_PIVOT_SEPARATION_BARS) -> bool:
    ordered = sorted(indices)
    return all(b - a >= min_gap for a, b in zip(ordered, ordered[1:]))


def _count_line_touches(prices: np.ndarray, slope: float, intercept: float, *, tol_pct: float) -> int:
    touches = 0
    for i, price in enumerate(prices):
        fitted = intercept + slope * float(i)
        base = max(abs(fitted), abs(float(price)), 1e-9)
        if abs(float(price) - fitted) / base <= tol_pct:
            touches += 1
    return touches


def _last_touch_offset(prices: np.ndarray, slope: float, intercept: float, *, tol_pct: float) -> int | None:
    last: int | None = None
    for i, price in enumerate(prices):
        fitted = intercept + slope * float(i)
        base = max(abs(fitted), abs(float(price)), 1e-9)
        if abs(float(price) - fitted) / base <= tol_pct:
            last = i
    return last


def _span_ok(indices: list[int], *, max_span: int) -> bool:
    return (max(indices) - min(indices)) <= max_span


def _last_pivot(hit: dict[str, Any]) -> int:
    if hit.get("last_pivot") is not None:
        return int(hit["last_pivot"])
    indices = hit.get("indices") or [0]
    return int(max(indices))


def rank_daily_setups(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One deterministic winner among overlapping daily setups. Neutral triangles never rank."""
    daily = [
        hit
        for hit in hits
        if hit.get("timeframe") in ("day", "daily") and hit.get("bias") not in (None, "neutral", "none")
    ]
    priority = {name: i for i, name in enumerate(PATTERN_PRIORITY)}

    def sort_key(hit: dict[str, Any]) -> tuple[int, int, float, int]:
        name = str(hit.get("pattern"))
        family = PATTERN_FAMILY.get(name, 99)
        prominence = float(hit.get("prominence") or 0.0)
        # Family first so a triangle window-end cannot leapfrog H&S or double/triple.
        return (family, -_last_pivot(hit), -prominence, priority.get(name, 99))

    return sorted(daily, key=sort_key)


def detect_patterns(ohlc: list[dict[str, Any]], *, timeframe: str) -> list[dict[str, Any]]:
    """
    Deterministic pattern heuristics on close prices.
    Returns pattern hits with indices; empty if insufficient bars.
    """
    if len(ohlc) < 30:
        return []

    closes = np.array([float(b["close"]) for b in ohlc], dtype=float)
    highs = np.array([float(b.get("high", b["close"])) for b in ohlc], dtype=float)
    lows = np.array([float(b.get("low", b["close"])) for b in ohlc], dtype=float)
    peaks, troughs = _local_extrema(closes, order=3)
    hits: list[dict[str, Any]] = []
    max_span = _max_pattern_bars(timeframe)

    # Double / triple tops
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if (
            _nearly_equal(closes[p1], closes[p2])
            and _pivots_separated([p1, p2])
            and _span_ok([p1, p2], max_span=max_span)
        ):
            neck = float(closes[p1:p2].min()) if p2 > p1 else float(closes[p2])
            prominence = abs(float(closes[p2]) - neck) / max(abs(neck), 1e-9)
            hits.append(
                {
                    "pattern": "double_top",
                    "timeframe": timeframe,
                    "indices": [p1, p2],
                    "last_pivot": p2,
                    "prices": [float(closes[p1]), float(closes[p2])],
                    "neckline": neck,
                    "prominence": prominence,
                    "bias": "bearish",
                }
            )
    if len(peaks) >= 3:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        if (
            _nearly_equal(closes[p1], closes[p2])
            and _nearly_equal(closes[p2], closes[p3])
            and _pivots_separated([p1, p2, p3])
            and _span_ok([p1, p3], max_span=max_span)
        ):
            neck = float(closes[p1:p3].min())
            prominence = abs(float(closes[p3]) - neck) / max(abs(neck), 1e-9)
            hits.append(
                {
                    "pattern": "triple_top",
                    "timeframe": timeframe,
                    "indices": [p1, p2, p3],
                    "last_pivot": p3,
                    "prices": [float(closes[p1]), float(closes[p2]), float(closes[p3])],
                    "neckline": neck,
                    "prominence": prominence,
                    "bias": "bearish",
                }
            )

    # Double / triple bottoms
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        if (
            _nearly_equal(closes[t1], closes[t2])
            and _pivots_separated([t1, t2])
            and _span_ok([t1, t2], max_span=max_span)
        ):
            neck = float(closes[t1:t2].max()) if t2 > t1 else float(closes[t2])
            prominence = abs(neck - float(closes[t2])) / max(abs(neck), 1e-9)
            hits.append(
                {
                    "pattern": "double_bottom",
                    "timeframe": timeframe,
                    "indices": [t1, t2],
                    "last_pivot": t2,
                    "prices": [float(closes[t1]), float(closes[t2])],
                    "neckline": neck,
                    "prominence": prominence,
                    "bias": "bullish",
                }
            )
    if len(troughs) >= 3:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        if (
            _nearly_equal(closes[t1], closes[t2])
            and _nearly_equal(closes[t2], closes[t3])
            and _pivots_separated([t1, t2, t3])
            and _span_ok([t1, t3], max_span=max_span)
        ):
            neck = float(closes[t1:t3].max())
            prominence = abs(neck - float(closes[t3])) / max(abs(neck), 1e-9)
            hits.append(
                {
                    "pattern": "triple_bottom",
                    "timeframe": timeframe,
                    "indices": [t1, t2, t3],
                    "last_pivot": t3,
                    "prices": [float(closes[t1]), float(closes[t2]), float(closes[t3])],
                    "neckline": neck,
                    "prominence": prominence,
                    "bias": "bullish",
                }
            )

    # Head and shoulders / inverse: time-ordered LS → head → RS, intervening opposite pivots.
    if len(peaks) >= 3:
        l, h, r = peaks[-3], peaks[-2], peaks[-1]
        left_troughs = [t for t in troughs if l < t < h]
        right_troughs = [t for t in troughs if h < t < r]
        head_vs_left = (closes[h] - closes[l]) / max(abs(closes[l]), 1e-9)
        head_vs_right = (closes[h] - closes[r]) / max(abs(closes[r]), 1e-9)
        if (
            l < h < r
            and (r - l) <= max_span
            and _pivots_separated([l, h, r])
            and left_troughs
            and right_troughs
            and closes[h] > closes[l]
            and closes[h] > closes[r]
            and head_vs_left >= HEAD_PROMINENCE_PCT
            and head_vs_right >= HEAD_PROMINENCE_PCT
            and _nearly_equal(closes[l], closes[r], tol_pct=0.025)
        ):
            neck = float((closes[left_troughs[-1]] + closes[right_troughs[0]]) / 2.0)
            hits.append(
                {
                    "pattern": "head_and_shoulders",
                    "timeframe": timeframe,
                    "indices": [l, h, r],
                    "last_pivot": r,
                    "prices": [float(closes[l]), float(closes[h]), float(closes[r])],
                    "neckline": neck,
                    "prominence": float(min(head_vs_left, head_vs_right)),
                    "bias": "bearish",
                }
            )
    if len(troughs) >= 3:
        l, h, r = troughs[-3], troughs[-2], troughs[-1]
        left_peaks = [p for p in peaks if l < p < h]
        right_peaks = [p for p in peaks if h < p < r]
        head_vs_left = (closes[l] - closes[h]) / max(abs(closes[l]), 1e-9)
        head_vs_right = (closes[r] - closes[h]) / max(abs(closes[r]), 1e-9)
        if (
            l < h < r
            and (r - l) <= max_span
            and _pivots_separated([l, h, r])
            and left_peaks
            and right_peaks
            and closes[h] < closes[l]
            and closes[h] < closes[r]
            and head_vs_left >= HEAD_PROMINENCE_PCT
            and head_vs_right >= HEAD_PROMINENCE_PCT
            and _nearly_equal(closes[l], closes[r], tol_pct=0.025)
        ):
            neck = float((closes[left_peaks[-1]] + closes[right_peaks[0]]) / 2.0)
            hits.append(
                {
                    "pattern": "inverse_head_and_shoulders",
                    "timeframe": timeframe,
                    "indices": [l, h, r],
                    "last_pivot": r,
                    "prices": [float(closes[l]), float(closes[h]), float(closes[r])],
                    "neckline": neck,
                    "prominence": float(min(head_vs_left, head_vs_right)),
                    "bias": "bullish",
                }
            )

    # Triangles on recent 40 bars: converging highs/lows
    window = min(40, len(closes))
    seg_high = highs[-window:]
    seg_low = lows[-window:]
    x = np.arange(window, dtype=float)
    if window >= 20:
        high_fit = np.polyfit(x, seg_high, 1)
        low_fit = np.polyfit(x, seg_low, 1)
        high_slope = float(high_fit[0])
        low_slope = float(low_fit[0])
        high_range = float(seg_high.max() - seg_high.min())
        low_range = float(seg_low.max() - seg_low.min())
        # Flat side: abs(OLS slope) < 15% of (side range / window bars).
        flat_high = abs(high_slope) < (high_range / window) * 0.15
        flat_low = abs(low_slope) < (low_range / window) * 0.15
        rising_low = low_slope > 0
        falling_high = high_slope < 0
        high_touches = _count_line_touches(seg_high, high_slope, float(high_fit[1]), tol_pct=TRIANGLE_TOUCH_PCT)
        low_touches = _count_line_touches(seg_low, low_slope, float(low_fit[1]), tol_pct=TRIANGLE_TOUCH_PCT)
        enough_touches = (
            high_touches >= TRIANGLE_MIN_TOUCHES_PER_SIDE
            and low_touches >= TRIANGLE_MIN_TOUCHES_PER_SIDE
        )
        start_idx = len(closes) - window
        high_last = _last_touch_offset(seg_high, high_slope, float(high_fit[1]), tol_pct=TRIANGLE_TOUCH_PCT)
        low_last = _last_touch_offset(seg_low, low_slope, float(low_fit[1]), tol_pct=TRIANGLE_TOUCH_PCT)
        touch_offsets = [idx for idx in (high_last, low_last) if idx is not None]
        last_pivot = start_idx + max(touch_offsets) if touch_offsets else start_idx
        triangle_meta = {
            "timeframe": timeframe,
            "indices": [start_idx, last_pivot],
            "last_pivot": last_pivot,
            "high_slope": high_slope,
            "low_slope": low_slope,
            "high_touches": high_touches,
            "low_touches": low_touches,
            "prominence": float(min(high_range, low_range)),
        }
        if enough_touches and flat_high and rising_low:
            hits.append({"pattern": "ascending_triangle", "bias": "bullish", **triangle_meta})
        elif enough_touches and flat_low and falling_high:
            hits.append({"pattern": "descending_triangle", "bias": "bearish", **triangle_meta})
        elif enough_touches and falling_high and rising_low:
            hits.append({"pattern": "symmetrical_triangle", "bias": "neutral", **triangle_meta})

    return hits


def collect_pattern_hits(
    historicals_for_symbol: dict[str, Any],
    timeframes: list[str],
) -> list[dict[str, Any]]:
    """Daily first. 10-minute / hour only on names with a daily pattern hit."""
    daily_bars = list(historicals_for_symbol.get("day") or historicals_for_symbol.get("daily") or [])
    daily_hits = detect_patterns(daily_bars, timeframe="day")
    ranked = rank_daily_setups(daily_hits)
    if not ranked:
        return []
    winner = ranked[0]
    hits = [winner]
    for tf in timeframes:
        if tf in ("day", "daily"):
            continue
        bars = historicals_for_symbol.get(tf) or []
        hits.extend(detect_patterns(list(bars), timeframe=tf))
    return hits

# ========================================================================
# pipeline/news.py
# Part: 4 · Agent C
# Used by: F + H
# Factual RH news/earnings pack; no invented sentiment
# ========================================================================

from __future__ import annotations

from typing import Any

from pipeline.io_util import utc_now_iso


def build_news_signal(
    symbol: str,
    articles: list[dict[str, Any]],
    earnings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Agent C: factual packaging of RH news/earnings payloads only."""
    headlines = []
    for a in articles[:10]:
        headlines.append(
            {
                "title": a.get("title") or a.get("headline"),
                "published_at": a.get("published_at") or a.get("updated_at") or a.get("created_at"),
                "source": a.get("source") or a.get("author"),
                "url": a.get("url") or a.get("link"),
            }
        )
    return {
        "symbol": symbol,
        "as_of": utc_now_iso(),
        "headline_count": len(headlines),
        "headlines": headlines,
        "earnings": earnings,
        "notes": "Read-only catalyst pack; no sentiment scores invented.",
    }

# ========================================================================
# pipeline/options_structure.py
# Part: 5 · Agent D
# Used by: F + H
# Long call/put; ATM/OTM; 2–3 DTE while overnight off
# ========================================================================

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

# ========================================================================
# pipeline/equity_day_trade.py
# Part: 5 · Agent D
# Used by: F only
# Long shares only; inverse-ETF denylist; H has no equity fallback
# ========================================================================

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

# ========================================================================
# pipeline/greeks.py
# Part: 6 · Agent I
# Used by: F + H
# Copy RH Greeks only; signed call +0.40–+0.50 / put −0.50–−0.40
# ========================================================================

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

# ========================================================================
# pipeline/risk.py
# Part: 7 · Agent E
# Used by: F + H
# Options −20%/+40%; equity −20%/+25%; stop first until OCO
# ========================================================================

from __future__ import annotations

from typing import Any

OPTIONS_SL_PCT_MIN = 0.20
OPTIONS_SL_PCT_MAX = 0.50
OPTIONS_TP_PCT_MIN = 0.30
OPTIONS_TARGET_REWARD_TO_RISK = 2.0
OPTIONS_DEFAULT_SL_PCT = 0.20
OPTIONS_DEFAULT_TP_PCT = 0.40


def options_risk_plan(
    *,
    premium_per_share: float,
    contracts: int = 1,
    multiplier: float = 100.0,
    take_profit_pct: float = OPTIONS_DEFAULT_TP_PCT,
    stop_loss_pct: float = OPTIONS_DEFAULT_SL_PCT,
) -> dict[str, Any]:
    """Cash-risked plan for long options. Does not invent prices beyond inputs.

    Locked bands: SL 20–50% of premium; TP 30–100%+ of premium; aim 1:2 R:R.
    Owner-locked working pair is −20% / +40% (1:2, inside the bands).
    """
    if contracts != 1:
        raise ValueError("Phase rules require max 1 contract")
    if stop_loss_pct < OPTIONS_SL_PCT_MIN or stop_loss_pct > OPTIONS_SL_PCT_MAX:
        raise ValueError(
            f"options stop_loss_pct must be in [{OPTIONS_SL_PCT_MIN}, {OPTIONS_SL_PCT_MAX}], got {stop_loss_pct}"
        )
    if take_profit_pct < OPTIONS_TP_PCT_MIN:
        raise ValueError(
            f"options take_profit_pct must be >= {OPTIONS_TP_PCT_MIN}, got {take_profit_pct}"
        )
    cash = premium_per_share * multiplier * contracts
    reward_to_risk = take_profit_pct / stop_loss_pct if stop_loss_pct else None
    return {
        "asset_class": "option",
        "contracts": contracts,
        "premium_per_share": premium_per_share,
        "multiplier": multiplier,
        "cash_risked": cash,
        "take_profit_pct": take_profit_pct,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_value": cash * (1.0 + take_profit_pct),
        "stop_loss_value": cash * (1.0 - stop_loss_pct),
        "take_profit_premium": premium_per_share * (1.0 + take_profit_pct),
        "stop_loss_premium": premium_per_share * (1.0 - stop_loss_pct),
        "stop_loss_pct_band": {"min": OPTIONS_SL_PCT_MIN, "max": OPTIONS_SL_PCT_MAX},
        "take_profit_pct_band": {"min": OPTIONS_TP_PCT_MIN, "uncapped": True},
        "target_reward_to_risk": OPTIONS_TARGET_REWARD_TO_RISK,
        "reward_to_risk": reward_to_risk,
        "meets_target_rr": reward_to_risk is not None
        and reward_to_risk + 1e-12 >= OPTIONS_TARGET_REWARD_TO_RISK,
        "broker_exit": "stop_first_until_oco",
        "monitor_take_profit_in_loop": True,
    }


def equity_risk_plan(
    *,
    cost_basis: float,
    take_profit_pct: float = 0.25,
    stop_loss_pct: float = 0.2,
    shares: int | None = None,
    limit_price: float | None = None,
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "asset_class": "equity",
        "cost_basis": cost_basis,
        "take_profit_pct": take_profit_pct,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_value": cost_basis * (1.0 + take_profit_pct),
        "stop_loss_value": cost_basis * (1.0 - stop_loss_pct),
        "broker_exit": "stop_first_until_oco",
        "monitor_take_profit_in_loop": True,
        "flatten_before_close": True,
        "side": "long_only",
    }
    if shares is not None:
        plan["shares"] = int(shares)
    if limit_price is not None:
        plan["limit_price"] = limit_price
        plan["stop_price"] = limit_price * (1.0 - stop_loss_pct)
        plan["take_profit_price"] = limit_price * (1.0 + take_profit_pct)
    return plan

# ========================================================================
# pipeline/orchestrator.py
# Part: 8 · Agent G
# Used by: F + H
# Phase 2 read-only snapshot; h_entry_ready is always false
# ========================================================================

from __future__ import annotations

from collections import Counter
from typing import Any

from pipeline.equity_day_trade import buying_power_from_raw, select_equity_day_trade_candidates
from pipeline.greeks import delta_in_band, extract_greeks
from pipeline.io_util import append_jsonl, load_rules, utc_now_iso, write_json, SIGNALS, JOURNAL
from pipeline.news import build_news_signal
from pipeline.options_structure import (
    choose_structure_from_bias,
    instrument_id,
    rank_atm_then_one_otm,
    rank_expirations,
    strikes_bracket_spot,
)
from pipeline.patterns import collect_pattern_hits
from pipeline.quotes import extract_bod_nlv
from pipeline.risk import equity_risk_plan, options_risk_plan
from pipeline.session import today_et
from pipeline.universe import apply_liquidity_filter, extract_watchlist_symbols, option_quote_liquid

PHASE2_SNAPSHOT_NOTE = (
    "Pipeline snapshot. Daily-pattern screen only. Not H-entry-ready: "
    "does not confirm hour alignment, 10m breakout/retest, live trigger, "
    "IV, volume/OI, quote age, event blackout, BOD NLV, or dual fee ceilings. "
    "Re-quote live. Never place from this file. Agent H must ignore equity_candidates."
)


def dominant_bias(pattern_hits: list[dict[str, Any]]) -> str | None:
    for hit in pattern_hits:
        if hit.get("timeframe") in ("day", "daily") and hit.get("bias") in ("bullish", "bearish"):
            return str(hit["bias"])
    biases = [p.get("bias") for p in pattern_hits if p.get("bias") in ("bullish", "bearish")]
    if not biases:
        return None
    counts = Counter(biases)
    top, n = counts.most_common(1)[0]
    if n > len(biases) / 2:
        return top
    return None


def _snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "do_not_place": True,
        "h_entry_ready": False,
        "snapshot_note": PHASE2_SNAPSHOT_NOTE,
    }


def _option_premium(quote: dict[str, Any], liq_metrics: dict[str, Any]) -> tuple[float | None, str | None]:
    """Playbook premium is bid/ask mid. Do not require mark_price."""
    mid = liq_metrics.get("mid")
    if mid not in (None, ""):
        try:
            value = float(mid)
            if value > 0:
                return value, "mid"
        except (TypeError, ValueError):
            pass
    for key in ("mark_price", "adjusted_mark_price"):
        if quote.get(key) not in (None, ""):
            try:
                value = float(quote[key])
                if value > 0:
                    return value, key
            except (TypeError, ValueError):
                continue
    return None, None


def run_pipeline(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Phase 2 orchestrator.
    `raw` is assembled by the Cursor agent from RH MCP responses (read-only).
    Never places orders.
    """
    rules = load_rules()
    as_of = utc_now_iso()
    assert rules["execution"]["phase2_places_orders"] is False

    # --- Agent A ---
    universe_extract = extract_watchlist_symbols(
        raw.get("watchlists", []),
        raw.get("watchlist_items_by_id", {}),
        raw.get("option_watchlist_items"),
        include_crypto=rules["universe"]["include_crypto"],
        include_options_watchlist=rules["universe"]["include_options_watchlist"],
    )
    liq = apply_liquidity_filter(
        universe_extract["equity_symbols"],
        raw.get("fundamentals_by_symbol", {}),
        min_average_volume=float(rules["liquidity"]["min_average_volume"]),
    )
    universe_signal = {
        "agent": "A_scanner",
        "as_of": as_of,
        "mode": "read_only",
        "extract": universe_extract,
        "liquidity": liq,
        "index_symbols": universe_extract["index_symbols"],
        "eligible_equities": liq["passed_symbols"],
    }
    write_json(SIGNALS / "universe.json", _snapshot(universe_signal))

    # --- Agent B ---
    technicals: dict[str, Any] = {"agent": "B_patterns", "as_of": as_of, "symbols": {}}
    historicals = raw.get("historicals_by_symbol_timeframe", {})
    for symbol in liq["passed_symbols"]:
        symbol_hits = collect_pattern_hits(
            historicals.get(symbol) or {},
            list(rules["patterns"]["timeframes"]),
        )
        technicals["symbols"][symbol] = {
            "pattern_hits": symbol_hits,
            "dominant_bias": dominant_bias(symbol_hits),
        }
    write_json(SIGNALS / "technicals.json", _snapshot(technicals))

    # --- Agent C ---
    news_signal = {"agent": "C_news", "as_of": as_of, "symbols": {}}
    news_raw = raw.get("news_by_symbol", {})
    earnings_raw = raw.get("earnings_by_symbol", {})
    for symbol in liq["passed_symbols"]:
        news_signal["symbols"][symbol] = build_news_signal(
            symbol,
            news_raw.get(symbol) or [],
            earnings_raw.get(symbol),
        )
    write_json(SIGNALS / "news.json", _snapshot(news_signal))

    # --- Agents D + I ---
    option_candidates: list[dict[str, Any]] = []
    greeks_rows: list[dict[str, Any]] = []
    equity_fallbacks: list[dict[str, Any]] = []
    spots = raw.get("spots_by_symbol", {})
    chains = raw.get("option_chains_by_symbol", {})
    instruments_by_key = raw.get("option_instruments_by_symbol_exp", {})
    quotes_by_id = raw.get("option_quotes_by_id", {})
    quotes_by_id = {str(k): v for k, v in quotes_by_id.items()}
    buying_power = buying_power_from_raw(raw)
    delta_lo = float(rules["options"]["strike"]["delta_min"])
    delta_hi = float(rules["options"]["strike"]["delta_max"])
    max_spread = float(rules["liquidity"]["option_max_spread_pct_of_price"])
    pref_spread = float(rules["liquidity"]["option_preferred_spread_pct_of_price"])
    reject_one_sided = bool(rules["liquidity"]["reject_one_sided_quotes"])
    multiplier = 100.0
    min_dte = int(rules["options"].get("min_dte", 0))
    max_dte = int(rules["options"]["max_dte"])
    overnight_holding = bool(rules["agent_h"].get("overnight_holding_enabled", False))

    for symbol in liq["passed_symbols"]:
        bias = technicals["symbols"].get(symbol, {}).get("dominant_bias")
        structure = choose_structure_from_bias(bias)
        spot = spots.get(symbol)
        if structure is None or spot is None:
            equity_fallbacks.append(
                {
                    "symbol": symbol,
                    "reason": "no_directional_bias_or_spot" if structure is None else "missing_spot",
                    "bias": bias,
                }
            )
            continue

        chain = chains.get(symbol) or {}
        expirations = rank_expirations(
            chain.get("expiration_dates") or [],
            overnight_holding_enabled=overnight_holding,
            hard_min_dte=min_dte,
            hard_max_dte=max_dte,
        )
        if not expirations:
            equity_fallbacks.append({"symbol": symbol, "reason": "no_expiration_within_max_dte", "bias": bias})
            continue

        option_type = "call" if structure == "long_call" else "put"
        passed: dict[str, Any] | None = None
        last_reject: dict[str, Any] | None = None
        for exp in expirations:
            instruments = instruments_by_key.get(f"{symbol}|{exp}") or instruments_by_key.get(symbol) or []
            if not strikes_bracket_spot(float(spot), instruments, option_type=option_type):
                last_reject = {
                    "symbol": symbol,
                    "reason": "option_chain_incomplete_atm_not_in_page",
                    "bias": bias,
                    "expiration": exp,
                }
                continue

            ranked = rank_atm_then_one_otm(float(spot), instruments, option_type=option_type)
            if not ranked:
                last_reject = {"symbol": symbol, "reason": "no_instrument_match", "bias": bias, "expiration": exp}
                continue

            for pick in ranked:
                inst = pick["instrument"]
                oid = instrument_id(inst)
                if not oid:
                    last_reject = {"symbol": symbol, "reason": "missing_option_id", "bias": bias, "expiration": exp}
                    continue
                quote = quotes_by_id.get(oid) or quotes_by_id.get(str(inst.get("id"))) or {}
                ok_liq, liq_reason, liq_metrics = option_quote_liquid(
                    quote,
                    max_spread_pct_of_price=max_spread,
                    preferred_spread_pct_of_price=pref_spread,
                    reject_one_sided=reject_one_sided,
                )
                gpack = extract_greeks(quote)
                greeks_rows.append(
                    {
                        "symbol": symbol,
                        "option_id": oid,
                        "expiration": exp,
                        "type": option_type,
                        "strike": inst.get("strike_price", inst.get("strike")),
                        "selection": pick["selection"],
                        **gpack,
                        "liquidity": {"ok": ok_liq, "reason": liq_reason, **liq_metrics},
                    }
                )
                if not ok_liq:
                    last_reject = {
                        "symbol": symbol,
                        "reason": f"option_illiquid:{liq_reason}",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                    }
                    continue
                ok_delta, delta_reason = delta_in_band(
                    gpack["greeks"].get("delta"),
                    option_type=option_type,
                    lo=delta_lo,
                    hi=delta_hi,
                )
                if not ok_delta:
                    last_reject = {
                        "symbol": symbol,
                        "reason": f"greeks_filter:{delta_reason}",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                    }
                    continue
                premium, premium_source = _option_premium(quote, liq_metrics)
                if premium is None:
                    last_reject = {
                        "symbol": symbol,
                        "reason": "missing_bid_ask_mid",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                    }
                    continue
                cash = premium * multiplier
                if buying_power is None:
                    last_reject = {
                        "symbol": symbol,
                        "reason": "missing_buying_power",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                    }
                    continue
                if cash > buying_power + 1e-9:
                    last_reject = {
                        "symbol": symbol,
                        "reason": "exceeds_buying_power",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                        "cash_debit": cash,
                        "buying_power": buying_power,
                    }
                    continue
                passed = {
                    "symbol": symbol,
                    "structure": structure,
                    "bias": bias,
                    "expiration": exp,
                    "option_type": option_type,
                    "strike": inst.get("strike_price", inst.get("strike")),
                    "option_id": oid,
                    "selection": pick["selection"],
                    "premium_mark": premium,
                    "premium_source": premium_source,
                    "greeks": gpack["greeks"],
                    "liquidity": liq_metrics,
                    "contracts": 1,
                    "cash_debit": cash,
                    "playbook_status": rules["options"]["playbook_status"],
                }
                break
            if passed is not None:
                break

        if passed is None:
            equity_fallbacks.append(last_reject or {"symbol": symbol, "reason": "no_instrument_match", "bias": bias})
            continue
        option_candidates.append(passed)

    write_json(
        SIGNALS / "option_candidates.json",
        _snapshot(
            {
                "agent": "D_option_structure",
                "as_of": as_of,
                "mode": "read_only",
                "candidates": option_candidates,
                "equity_fallbacks": equity_fallbacks,
                "max_contracts": rules["options"]["max_contracts"],
                "phase2_checks": [
                    "daily_pattern",
                    "expiration_group",
                    "atm_otm",
                    "signed_delta",
                    "spread",
                    "buying_power",
                ],
                "h_still_requires": [
                    "hour_confirm",
                    "10m_breakout_retest",
                    "live_trigger",
                    "iv",
                    "volume_oi",
                    "quote_age",
                    "event_blackout",
                    "bod_nlv",
                    "dual_fee_ceilings",
                ],
            }
        ),
    )
    write_json(
        SIGNALS / "greeks.json",
        _snapshot({"agent": "I_greeks", "as_of": as_of, "source": "robinhood_get_option_quotes", "rows": greeks_rows}),
    )

    equity_candidates, equity_rejects = select_equity_day_trade_candidates(
        symbols=liq["passed_symbols"],
        technicals_by_symbol=technicals["symbols"],
        option_candidate_symbols={c["symbol"] for c in option_candidates},
        quotes_by_symbol=raw.get("equity_quotes_by_symbol") or {},
        tradability_by_symbol=raw.get("equity_tradability_by_symbol") or {},
        fundamentals_by_symbol=raw.get("fundamentals_by_symbol") or {},
        buying_power=buying_power,
        playbook_status=str(rules["risk"]["equity"]["playbook_status"]),
        take_profit_pct=float(rules["risk"]["equity"]["take_profit_pct_of_cost"]),
        stop_loss_pct=float(rules["risk"]["equity"]["stop_loss_pct_of_cost"]),
    )
    write_json(
        SIGNALS / "equity_candidates.json",
        _snapshot(
            {
                "agent": "D_equity_day_trade",
                "as_of": as_of,
                "mode": "read_only",
                "playbook_status": rules["risk"]["equity"]["playbook_status"],
                "playbook_path": rules["risk"]["equity"]["playbook_path"],
                "side": "long_only",
                "no_shorting": True,
                "priority": "options_first",
                "agent_h_may_use": False,
                "agent_h_equity_fallback": False,
                "candidates": equity_candidates,
                "rejected": equity_rejects,
                "option_fallback_notes": equity_fallbacks,
            }
        ),
    )

    # --- Agent E ---
    risk_plans: list[dict[str, Any]] = []
    for cand in option_candidates:
        plan = options_risk_plan(
            premium_per_share=float(cand["premium_mark"]),
            contracts=1,
            take_profit_pct=float(rules["risk"]["options"]["take_profit_pct_of_cash"]),
            stop_loss_pct=float(rules["risk"]["options"]["stop_loss_pct_of_cash"]),
        )
        risk_plans.append({"symbol": cand["symbol"], "option_id": cand["option_id"], **plan})

    # Equity fallback risk plans only when explicitly provided cost basis in raw (optional)
    for fb in raw.get("equity_fallback_costs", []) or []:
        plan = equity_risk_plan(
            cost_basis=float(fb["cost_basis"]),
            take_profit_pct=float(rules["risk"]["equity"]["take_profit_pct_of_cost"]),
            stop_loss_pct=float(rules["risk"]["equity"]["stop_loss_pct_of_cost"]),
        )
        risk_plans.append({"symbol": fb["symbol"], **plan})

    for cand in equity_candidates:
        risk_plans.append({"symbol": cand["symbol"], **cand["risk"]})

    write_json(
        SIGNALS / "risk_plan.json",
        _snapshot(
            {
                "agent": "E_risk",
                "as_of": as_of,
                "mode": "read_only",
                "max_open_positions": rules["risk"]["max_open_positions"],
                "plans": risk_plans,
                "notes": "Stop-first until OCO; TP monitored in loop. Phase 2 does not place orders.",
            }
        ),
    )

    bod_nlv, bod_field = extract_bod_nlv(raw.get("portfolio"))
    summary = {
        "as_of": as_of,
        "phase": 2,
        "places_orders": False,
        "h_entry_ready": False,
        "eligible_equities": liq["passed_symbols"],
        "option_candidate_count": len(option_candidates),
        "equity_candidate_count": len(equity_candidates),
        "equity_fallback_count": len(equity_fallbacks),
        "risk_plan_count": len(risk_plans),
        "bod_nlv": bod_nlv,
        "bod_nlv_field": bod_field,
        "open_questions": rules.get("open_questions", []),
    }
    write_json(SIGNALS / "phase2_summary.json", _snapshot(summary))
    append_jsonl(
        JOURNAL / "loop_runs.jsonl",
        {"event": "phase2_cycle", "mode": "read_only", **summary},
    )
    journal_day = today_et().isoformat()
    append_jsonl(
        JOURNAL / f"{journal_day}.md.jsonl",
        {"type": "markdown_seed", "text": f"# {journal_day} Phase 2 cycle\n\n- options candidates: {len(option_candidates)}\n- eligible equities: {len(liq['passed_symbols'])}\n"},
    )
    md_path = JOURNAL / f"{journal_day}.md"
    prev = md_path.read_text(encoding="utf-8") if md_path.exists() else f"# Trading journal {journal_day}\n\n"
    prev += f"\n## Phase 2 read-only cycle ({as_of})\n"
    prev += f"- Eligible equities: {', '.join(liq['passed_symbols']) or '(none)'}\n"
    prev += f"- Option candidates: {len(option_candidates)}\n"
    prev += f"- Equity day-trade candidates: {len(equity_candidates)}\n"
    prev += f"- Equity fallbacks (option miss): {len(equity_fallbacks)}\n"
    prev += "- Orders placed: **none** (Phase 2 read-only)\n"
    md_path.write_text(prev, encoding="utf-8")

    return summary

# ========================================================================
# pipeline/execution.py
# Part: 9 · Agent F
# Used by: F (chat)
# Supervised place-gate: confirm, RTH, 09:45 options, H-owns-RTH
# ========================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any

from pipeline.io_util import JOURNAL, SIGNALS, append_jsonl, load_rules, read_json, utc_now_iso, write_json
from pipeline.session import (
    NO_NEW_OPTION_ENTRIES_BEFORE,
    entries_open,
    is_rth,
    now_et,
    option_entries_open,
)


def load_latest_option_candidates() -> list[dict[str, Any]]:
    path = SIGNALS / "option_candidates.json"
    if not path.exists():
        return []
    payload = read_json(path)
    if payload.get("do_not_place") or payload.get("historical"):
        return []
    return list(payload.get("candidates") or [])


def load_latest_equity_candidates() -> list[dict[str, Any]]:
    path = SIGNALS / "equity_candidates.json"
    if not path.exists():
        return []
    payload = read_json(path)
    if payload.get("do_not_place") or payload.get("historical"):
        return []
    return list(payload.get("candidates") or [])


def can_place_live(
    *,
    explicit_confirm: bool,
    playbook_released: bool,
    playbook_kind: str = "options",
    h_enabled: bool | None = None,
    now: datetime | None = None,
    h_rth_override: bool = False,
) -> tuple[bool, str | None]:
    """Agent F place-gate. Never invent a confirm. H owns RTH while enabled."""
    if not playbook_released:
        return False, f"{playbook_kind}_playbook_still_draft"
    if not explicit_confirm:
        return False, "missing_explicit_user_confirm"
    if not is_rth(now):
        return False, "outside_rth"
    if playbook_kind == "options" and not option_entries_open(now):
        if now_et(now).time() < NO_NEW_OPTION_ENTRIES_BEFORE:
            return False, "no_new_option_entries_before_0945"
        return False, "no_new_entries_after_1545"
    if not entries_open(now):
        return False, "no_new_entries_after_1545"
    if h_enabled is None:
        h_enabled = load_rules().get("execution", {}).get("unsupervised_agent_h") == "enabled"
    if h_enabled and not h_rth_override:
        return False, "h_owns_rth_while_enabled"
    return True, None


def build_option_entry_proposal(
    candidate: dict[str, Any],
    *,
    limit_price: str,
    account_last4: str = "2907",
) -> dict[str, Any]:
    """Build a supervised review/place payload. Does not call the broker."""
    return {
        "agent": "F_supervised_execution",
        "mode": "dry_review_until_confirm",
        "as_of": utc_now_iso(),
        "account_last4": account_last4,
        "asset_class": "option",
        "action": "buy_to_open",
        "symbol": candidate.get("symbol"),
        "structure": candidate.get("structure"),
        "expiration": candidate.get("expiration"),
        "option_type": candidate.get("option_type"),
        "strike": candidate.get("strike"),
        "option_id": candidate.get("option_id"),
        "quantity": "1",
        "order_type": "limit",
        "price": limit_price,
        "time_in_force": "gfd",
        "market_hours": "regular_hours",
        "chain_symbol": candidate.get("symbol"),
        "underlying_type": "equity",
        "legs": [
            {
                "option_id": candidate.get("option_id"),
                "side": "buy",
                "position_effect": "open",
                "ratio_quantity": 1,
            }
        ],
        "playbook_status": candidate.get("playbook_status"),
        "places_order": False,
    }


def build_equity_entry_proposal(
    candidate: dict[str, Any],
    *,
    limit_price: str | None = None,
    quantity: int | None = None,
    account_last4: str = "2907",
) -> dict[str, Any]:
    """Long-only equity day-trade proposal. Never sell-to-open. Does not call the broker."""
    shares = int(quantity if quantity is not None else candidate.get("quantity") or 0)
    if shares < 1:
        raise ValueError("equity day trade requires at least 1 whole share")
    price = str(limit_price if limit_price is not None else candidate.get("limit_price"))
    fill = float(price)
    stop_pct = float((candidate.get("risk") or {}).get("stop_loss_pct") or 0.2)
    tp_pct = float((candidate.get("risk") or {}).get("take_profit_pct") or 0.25)
    return {
        "agent": "F_supervised_execution",
        "mode": "dry_review_until_confirm",
        "as_of": utc_now_iso(),
        "account_last4": account_last4,
        "asset_class": "equity",
        "action": "buy_to_open",
        "side": "buy",
        "symbol": candidate.get("symbol"),
        "structure": "long_shares",
        "quantity": str(shares),
        "order_type": "limit",
        "price": price,
        "time_in_force": "gfd",
        "market_hours": "regular_hours",
        "stop_loss_pct": stop_pct,
        "take_profit_pct": tp_pct,
        "stop_price_after_fill": fill * (1.0 - stop_pct),
        "take_profit_price": fill * (1.0 + tp_pct),
        "playbook_status": candidate.get("playbook_status"),
        "places_order": False,
    }


def record_review(proposal: dict[str, Any], review_response: dict[str, Any] | None, *, error: str | None = None) -> dict[str, Any]:
    rules = load_rules()
    asset = proposal.get("asset_class") or "option"
    if asset == "equity":
        released = rules["risk"]["equity"]["playbook_status"] == "RELEASED"
        kind = "equity"
        status = rules["risk"]["equity"]["playbook_status"]
    else:
        released = rules["options"]["playbook_status"] == "RELEASED"
        kind = "options"
        status = rules["options"]["playbook_status"]
    allowed, reason = can_place_live(
        explicit_confirm=False,
        playbook_released=released,
        playbook_kind=kind,
        h_enabled=rules.get("execution", {}).get("unsupervised_agent_h") == "enabled",
    )
    record = {
        "event": "phase3_dry_review",
        "as_of": utc_now_iso(),
        "proposal": proposal,
        "review": review_response,
        "error": error,
        "places_order": False,
        "playbook_status": status,
        "place_gate": {"allowed": allowed, "reason": reason},
    }
    write_json(SIGNALS / "execution_review.json", record)
    append_jsonl(JOURNAL / "reviews.jsonl", record)
    return record

# ========================================================================
# scripts/run_phase2_cycle.py
# Part: 10 · CLI
# Used by: F + H
# Load data/raw/latest_raw.json and run the orchestrator
# ========================================================================

#!/usr/bin/env python3
"""Run Phase 2 pipeline from a raw MCP dump JSON file (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.io_util import DATA_RAW
from pipeline.orchestrator import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2 read-only signal pipeline")
    parser.add_argument(
        "--raw",
        type=Path,
        default=DATA_RAW / "latest_raw.json",
        help="Path to RH MCP assembled raw JSON",
    )
    args = parser.parse_args()
    if not args.raw.exists():
        print(f"Raw file not found: {args.raw}", file=sys.stderr)
        return 1
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    summary = run_pipeline(raw)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ========================================================================
# scripts/build_python_source_book.py
# Part: 10 · CLI
# Used by: docs
# This generator — rebuilds the printable source book
# ========================================================================

#!/usr/bin/env python3
"""Build a printable HTML + concatenated Python source book of this repo.

Covers every .py module used by Agent F (this Cursor chat) and Agent H
(the autonomous Agentic bot). H's place-permission prompt is not Python
and is listed only as a pointer.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# (path, part, used_by, one-line role)
CATALOG: list[tuple[str, str, str, str]] = [
    ("pipeline/__init__.py", "0 · Package", "F + H", "Pipeline package marker"),
    ("pipeline/io_util.py", "1 · Shared", "F + H", "Paths, rules.json loader, journal helpers"),
    ("pipeline/session.py", "1 · Shared", "F + H", "RTH clock; option entries 09:45–15:45; equity entries to 15:45"),
    ("pipeline/orders.py", "1 · Shared", "F + H", "Working-order states for Robinhood MCP (no open=true)"),
    ("pipeline/quotes.py", "1 · Shared", "F + H", "5s underlying executable price; BOD NLV field extract"),
    ("pipeline/fees.py", "1 · Shared", "F + H", "Dual fee ceilings: 0.49% planned loss and 0.50% with fees"),
    ("pipeline/universe.py", "2 · Agent A", "F + H", "Watchlist extract, crypto drop, inverse-ETF reject, ADV ≥ 2,000,000"),
    ("pipeline/patterns.py", "3 · Agent B", "F + H", "Daily-first H&S / double-triple / triangle; no 1m/3m/5m"),
    ("pipeline/news.py", "4 · Agent C", "F + H", "Factual RH news/earnings pack; no invented sentiment"),
    ("pipeline/options_structure.py", "5 · Agent D", "F + H", "Long call/put; ATM/OTM; 2–3 DTE while overnight off"),
    ("pipeline/equity_day_trade.py", "5 · Agent D", "F only", "Long shares only; inverse-ETF denylist; H has no equity fallback"),
    ("pipeline/greeks.py", "6 · Agent I", "F + H", "Copy RH Greeks only; signed call +0.40–+0.50 / put −0.50–−0.40"),
    ("pipeline/risk.py", "7 · Agent E", "F + H", "Options −20%/+40%; equity −20%/+25%; stop first until OCO"),
    ("pipeline/orchestrator.py", "8 · Agent G", "F + H", "Phase 2 read-only snapshot; h_entry_ready is always false"),
    ("pipeline/execution.py", "9 · Agent F", "F (chat)", "Supervised place-gate: confirm, RTH, 09:45 options, H-owns-RTH"),
    ("scripts/run_phase2_cycle.py", "10 · CLI", "F + H", "Load data/raw/latest_raw.json and run the orchestrator"),
    ("scripts/build_python_source_book.py", "10 · CLI", "docs", "This generator — rebuilds the printable source book"),
    ("pipeline/tests/test_phase2.py", "11 · Tests", "CI / F", "Universe, liquidity, signed delta, ATM/OTM, expiration rank"),
    ("pipeline/tests/test_orders.py", "11 · Tests", "CI / F", "Working states and locked agent_h schema"),
    ("pipeline/tests/test_fees.py", "11 · Tests", "CI / F", "Dual NLV fee ceilings"),
    ("pipeline/tests/test_session.py", "11 · Tests", "CI / F", "ET calendar date and flatten window"),
    ("pipeline/tests/test_equity_day_trade.py", "11 · Tests", "CI / F", "Long-only equity selection and Phase 2 snapshots"),
    ("pipeline/tests/test_execution.py", "11 · Tests", "CI / F", "F place-gate including 09:45 option lock"),
]


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _banner(rel: str, part: str, used_by: str, role: str) -> str:
    line = "=" * 72
    return (
        f"# {line}\n"
        f"# {rel}\n"
        f"# Part: {part}\n"
        f"# Used by: {used_by}\n"
        f"# {role}\n"
        f"# {line}\n\n"
    )


def _catalog() -> list[tuple[str, str, str, str]]:
    return [row for row in CATALOG if (ROOT / row[0]).exists() and _read(row[0]).strip()]


def build_python_book() -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    chunks: list[str] = [
        "# ruff: noqa\n",
        "# pylint: skip-file\n",
        '"""PRINTABLE SOURCE BOOK — do not import or execute this file.\n',
        "\n",
        "Agentic trading program: Agent F (supervised Cursor chat) and\n",
        "Agent H (autonomous Agentic bot) share this Python pipeline.\n",
        "Live place_* is Robinhood MCP, not a side effect of this code.\n",
        "H's standing prompt is playbooks/agent_h_autonomous.PROMPT.md (not Python).\n",
        "\n",
        f"Generated: {now}\n",
        "Print companion: docs/agentic-python-source-printable.html\n",
        '"""\n\n',
    ]
    for rel, part, used_by, role in _catalog():
        chunks.append(_banner(rel, part, used_by, role))
        chunks.append(_read(rel).rstrip() + "\n\n")
    return "".join(chunks)


def build_html(py_book: str) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M UTC")
    toc_rows = []
    sections = []
    total_lines = 0
    for rel, part, used_by, role in _catalog():
        src = _read(rel)
        n = src.count("\n") + (0 if src.endswith("\n") or not src else 1)
        total_lines += n
        anchor = rel.replace("/", "-").replace(".", "-")
        toc_rows.append(
            f"<tr><td>{html.escape(part)}</td><td><a href='#{anchor}'>"
            f"<code>{html.escape(rel)}</code></a></td>"
            f"<td>{html.escape(used_by)}</td><td>{n}</td>"
            f"<td>{html.escape(role)}</td></tr>"
        )
        numbered = []
        lines = src.splitlines()
        width = max(3, len(str(len(lines))))
        for i, line in enumerate(lines, 1):
            numbered.append(
                f"<span class='ln'>{i:{width}d}</span> {html.escape(line)}"
            )
        sections.append(
            f"<section class='file' id='{anchor}'>"
            f"<h2>{html.escape(rel)}</h2>"
            f"<p class='meta'><strong>{html.escape(part)}</strong> · {html.escape(used_by)}"
            f" · {n} lines · {html.escape(role)}</p>"
            f"<pre class='source'>{chr(10).join(numbered)}\n</pre>"
            f"</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Agentic Python Source Book (Printable)</title>
  <style>
    :root {{ --ink:#111; --muted:#333; --line:#222; --bg:#fff; --box:#f4f4f4; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; color: var(--ink); background: var(--bg);
      font-family: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 10.4pt; line-height: 1.35;
    }}
    .toolbar {{
      position: sticky; top: 0; z-index: 20; display: flex; gap: 12px;
      align-items: center; background: #111; color: #fff;
      padding: 10px 16px; font-size: 13px;
    }}
    .toolbar button {{
      background: #fff; color: #111; border: 0; padding: 8px 14px;
      font-weight: 700; cursor: pointer;
    }}
    .page {{ max-width: 8.5in; margin: 0 auto; padding: 0.5in 0.55in 0.65in; }}
    h1 {{ font-size: 20pt; margin: 0 0 0.08in; letter-spacing: -0.02em; }}
    h2 {{
      font-size: 12pt; margin: 0.28in 0 0.08in; padding-bottom: 0.04in;
      border-bottom: 1.5pt solid var(--line); page-break-after: avoid;
    }}
    h3 {{ font-size: 11pt; margin: 0.16in 0 0.06in; page-break-after: avoid; }}
    .kicker {{ font-size: 9.5pt; letter-spacing: 0.08em; text-transform: uppercase; }}
    .rule {{ width: 1.3in; height: 3px; background: #111; margin: 0.12in 0 0.18in; }}
    .meta, .note, .footer {{ font-size: 9.3pt; color: var(--muted); }}
    .meta strong {{ color: var(--ink); }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0.1in 0 0.16in; }}
    .badge {{
      border: 1pt solid var(--line); padding: 3px 8px; font-size: 8.4pt; background: var(--box);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 8.8pt; margin: 0 0 0.14in; }}
    th, td {{ border: 1pt solid var(--line); padding: 0.045in 0.06in; vertical-align: top; text-align: left; }}
    th {{ background: #e8e8e8; font-weight: 700; }}
    .card {{
      border: 1pt solid var(--line); padding: 0.1in 0.12in; background: var(--box);
      page-break-inside: avoid; margin-bottom: 0.1in;
    }}
    ul {{ margin: 0.04in 0 0.08in; padding-left: 0.2in; }}
    li {{ margin: 0.03in 0; }}
    code {{ font-family: "IBM Plex Mono", Consolas, "Courier New", monospace; font-size: 8.8pt; }}
    pre.source {{
      font-family: "IBM Plex Mono", Consolas, "Courier New", monospace;
      font-size: 7.15pt; line-height: 1.28; white-space: pre-wrap; word-break: break-word;
      background: var(--box); border: 1pt solid var(--line); padding: 0.09in 0.1in;
      margin: 0 0 0.08in;
    }}
    pre.source .ln {{ color: #888; margin-right: 0.12in; user-select: none; }}
    .file {{ page-break-before: always; }}
    .footer {{ margin-top: 0.18in; padding-top: 0.08in; border-top: 1pt solid #999; font-size: 8.2pt; }}
    @media print {{
      .no-print {{ display: none !important; }}
      .page {{ max-width: none; padding: 0; }}
      a {{ color: inherit; text-decoration: none; }}
      h2, table, .card {{ break-inside: avoid; }}
      pre.source {{ font-size: 7pt; }}
    }}
    @page {{ size: Letter portrait; margin: 0.45in; }}
  </style>
</head>
<body>
  <div class="toolbar no-print">
    <button type="button" onclick="window.print()">Print / Save as PDF</button>
    <span>Agentic Python source — Letter portrait · {total_lines} lines · {len(CATALOG)} files</span>
  </div>
  <div class="page">
    <p class="kicker">Jarrod Besner · Agentic ••••2907</p>
    <h1>Python source book</h1>
    <div class="rule"></div>
    <p class="meta">Chat agent <strong>F</strong> and autonomous bot <strong>H</strong> share this pipeline.
    Generated {html.escape(now)}. Companion file: <code>docs/agentic_python_source_book.py</code>.</p>
    <div class="badge-row">
      <span class="badge">{len(CATALOG)} Python files</span>
      <span class="badge">{total_lines} lines</span>
      <span class="badge">Language: Python 3</span>
      <span class="badge">Does not place orders</span>
    </div>

    <h3>Who uses which code</h3>
    <div class="card">
      <ul>
        <li><strong>Agent F (this Cursor chat)</strong> — supervised. Reads the pipeline, reviews tickets via
            <code>pipeline/execution.py</code>, and only calls Robinhood <code>place_*</code> after an explicit
            confirm of a specific order. Blocked during RTH while H is enabled.</li>
        <li><strong>Agent H (Agentic AI Bot)</strong> — unsupervised Cursor Automation. The standing prompt is
            <code>playbooks/agent_h_autonomous.PROMPT.md</code> (markdown, not Python). On each fire H checks out
            <code>main</code>, reads <code>config/rules.json</code> → <code>agent_h</code>, and uses
            daily → 1-hour → completed 10-minute → live quote only (no 1m / 3m / 5m).
            Live <code>place_*</code> is Robinhood MCP from that prompt, not a pipeline side effect.
            H is options-only; it must ignore equity candidates.</li>
        <li><strong>Not in this book:</strong> lock JSON, playbooks, and the H prompt. Those are not Python.</li>
      </ul>
    </div>

    <h3>Contents</h3>
    <table>
      <thead><tr><th>Part</th><th>File</th><th>Used by</th><th>Lines</th><th>Role</th></tr></thead>
      <tbody>
        {''.join(toc_rows)}
      </tbody>
    </table>
    <p class="note">Each file starts on a new printed page. Source is verbatim Python from the repo.</p>
    {''.join(sections)}
    <p class="footer">Agentic Python source book · {html.escape(now)} · {total_lines} lines in {len(CATALOG)} files ·
    print from this HTML or open <code>docs/agentic_python_source_book.py</code>.</p>
  </div>
</body>
</html>
"""


def build_pdf(path: Path) -> None:
    import pymupdf

    page_w, page_h = 612, 792
    margin = 36
    body_font = 7.2
    header_font = 9.5
    cover_title = 22
    line_h = 9.4
    usable_h = page_h - margin * 2 - 18
    max_lines = int(usable_h / line_h)
    max_chars = 108

    doc = pymupdf.open()
    now = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M UTC")

    def new_page():
        return doc.new_page(width=page_w, height=page_h)

    def footer(page, label: str) -> None:
        page.insert_text(
            pymupdf.Point(margin, page_h - 18),
            f"Agentic Python source  ·  {label}  ·  {now}  ·  page {page.number + 1}",
            fontname="helv",
            fontsize=7,
            color=(0.25, 0.25, 0.25),
        )

    def wrap(text: str, width: int) -> list[str]:
        if len(text) <= width:
            return [text]
        words = text.replace("\t", "    ").split(" ")
        lines: list[str] = []
        cur = ""
        for word in words:
            trial = word if not cur else f"{cur} {word}"
            if len(trial) <= width:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            while len(word) > width:
                lines.append(word[:width])
                word = word[width:]
            cur = word
        if cur:
            lines.append(cur)
        return lines or [""]

    # Cover
    page = new_page()
    y = 72
    page.insert_text(pymupdf.Point(margin, y), "JARROD BESNER  ·  AGENTIC", fontname="helv", fontsize=10)
    y += 36
    page.insert_text(pymupdf.Point(margin, y), "Python source book", fontname="helv", fontsize=cover_title)
    y += 28
    page.draw_rect(pymupdf.Rect(margin, y, margin + 90, y + 3), fill=(0, 0, 0), width=0)
    y += 28
    cover_lines = [
        "All Python used by Agent F (supervised Cursor chat) and Agent H",
        "(autonomous Agentic bot). Live place_* is Robinhood MCP, not a",
        "side effect of this code. H's standing prompt is markdown:",
        "playbooks/agent_h_autonomous.PROMPT.md — not included here.",
        "",
        f"{len(CATALOG)} files  ·  generated {now}",
        "Language: Python 3  ·  Letter portrait",
    ]
    for line in cover_lines:
        page.insert_text(pymupdf.Point(margin, y), line, fontname="helv", fontsize=11)
        y += 16
    y += 10
    page.insert_text(pymupdf.Point(margin, y), "Contents", fontname="helv", fontsize=13)
    y += 18
    for rel, part, used_by, role in _catalog():
        n = _read(rel).count("\n") + 1
        row = f"{part:16s}  {rel:42s}  {used_by:10s}  {n:4d}  {role}"
        for w in wrap(row, 98):
            if y > page_h - 48:
                footer(page, "cover")
                page = new_page()
                y = margin + 12
            page.insert_text(pymupdf.Point(margin, y), w, fontname="cour", fontsize=7)
            y += 10
    footer(page, "cover")

    for rel, part, used_by, role in _catalog():
        src_lines = _read(rel).splitlines()
        page = new_page()
        header = f"{rel}   ·   {part}   ·   {used_by}   ·   {role}"
        page.insert_text(pymupdf.Point(margin, margin + 4), header[:110], fontname="helv", fontsize=header_font)
        y = margin + 18
        page.draw_line(pymupdf.Point(margin, y), pymupdf.Point(page_w - margin, y), color=(0, 0, 0), width=0.8)
        y += 12
        used = 0
        width = max(3, len(str(len(src_lines))))
        for i, raw in enumerate(src_lines, 1):
            prefix = f"{i:{width}d}  "
            wrapped = wrap(raw.replace("\t", "    "), max_chars - len(prefix)) or [""]
            for j, chunk in enumerate(wrapped):
                if used >= max_lines:
                    footer(page, rel)
                    page = new_page()
                    page.insert_text(
                        pymupdf.Point(margin, margin + 4),
                        f"{rel}  (continued)",
                        fontname="helv",
                        fontsize=header_font,
                    )
                    y = margin + 18
                    page.draw_line(
                        pymupdf.Point(margin, y),
                        pymupdf.Point(page_w - margin, y),
                        color=(0, 0, 0),
                        width=0.8,
                    )
                    y += 12
                    used = 0
                line = prefix + chunk if j == 0 else (" " * len(prefix)) + chunk
                page.insert_text(pymupdf.Point(margin, y), line, fontname="cour", fontsize=body_font)
                y += line_h
                used += 1
        footer(page, rel)

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    py_book = build_python_book()
    html_doc = build_html(py_book)
    py_path = DOCS / "agentic_python_source_book.py"
    html_path = DOCS / "agentic-python-source-printable.html"
    py_path.write_text(py_book, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")
    print(f"wrote {py_path} ({py_path.stat().st_size} bytes)")
    print(f"wrote {html_path} ({html_path.stat().st_size} bytes)")
    pdf_candidates = [Path("/dev/shm/agentic-python-source.pdf"), DOCS / "agentic-python-source.pdf"]
    pdf_path = pdf_candidates[0]
    try:
        build_pdf(pdf_path)
        print(f"wrote {pdf_path} ({pdf_path.stat().st_size} bytes)")
        dest = DOCS / "agentic-python-source.pdf"
        if pdf_path != dest:
            dest.write_bytes(pdf_path.read_bytes())
            print(f"copied {dest} ({dest.stat().st_size} bytes)")
    except OSError as exc:
        print(f"pdf write skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ========================================================================
# pipeline/tests/test_phase2.py
# Part: 11 · Tests
# Used by: CI / F
# Universe, liquidity, signed delta, ATM/OTM, expiration rank
# ========================================================================

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from pipeline.greeks import delta_in_band, extract_greeks
from pipeline.options_structure import (
    filter_expirations,
    pick_atm_or_one_otm,
    rank_atm_then_one_otm,
    rank_expirations,
    strikes_bracket_spot,
)
from pipeline.patterns import rank_daily_setups
from pipeline.quotes import executable_underlying_price, extract_bod_nlv
from pipeline.patterns import collect_pattern_hits, detect_patterns
from pipeline.risk import equity_risk_plan, options_risk_plan
from pipeline.session import today_et
from pipeline.universe import apply_liquidity_filter, extract_watchlist_symbols, option_quote_liquid


def test_extract_excludes_crypto():
    watchlists = [{"id": "1", "display_name": "My First List"}]
    items = {
        "1": [
            {"object_type": "instrument", "symbol": "AAPL"},
            {"object_type": "currency_pair", "symbol": "BTC-USD"},
        ]
    }
    out = extract_watchlist_symbols(watchlists, items, [], include_crypto=False)
    assert out["equity_symbols"] == ["AAPL"]
    assert "BTC-USD" in out["skipped_crypto"]


def test_liquidity_volume_gate():
    fund = {"AAA": {"average_volume": 3_000_000}, "BBB": {"average_volume": 1000}}
    out = apply_liquidity_filter(["AAA", "BBB"], fund, min_average_volume=2_000_000)
    assert out["passed_symbols"] == ["AAA"]
    assert out["rejected"][0]["symbol"] == "BBB"


def test_liquidity_rejects_inverse_etfs_before_volume():
    fund = {
        "AAA": {"average_volume": 3_000_000},
        "SQQQ": {"average_volume": 20_000_000, "name": "ProShares UltraPro Short QQQ"},
        "XYZ": {"average_volume": 5_000_000, "description": "Leveraged inverse daily"},
    }
    out = apply_liquidity_filter(["AAA", "SQQQ", "XYZ"], fund, min_average_volume=2_000_000)
    assert out["passed_symbols"] == ["AAA"]
    reasons = {row["symbol"]: row["reason"] for row in out["rejected"]}
    assert reasons["SQQQ"] == "inverse_etf"
    assert reasons["XYZ"] == "inverse_etf"


def test_option_spread_gate():
    preferred, reason, pref_m = option_quote_liquid(
        {"bid_price": "1.00", "ask_price": "1.05"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert preferred and reason is None
    assert pref_m["spread_quality"] == "preferred"

    acceptable, reason_ok, acc_m = option_quote_liquid(
        {"bid": "1.00", "ask": "1.08"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert acceptable and reason_ok is None
    assert acc_m["spread_quality"] == "acceptable"

    missing, missing_reason, _ = option_quote_liquid(
        {},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert not missing and missing_reason == "missing_bid_ask"

    bad, reason2, _ = option_quote_liquid(
        {"bid_price": "1.00", "ask_price": "1.50"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert not bad and reason2 == "spread_too_wide"

    # $0.10 absolute on a cheap contract is ~22% of mid — reject (no dollar override).
    cheap, cheap_reason, cheap_m = option_quote_liquid(
        {"bid_price": "0.40", "ask_price": "0.50"},
        max_spread_pct_of_price=0.1,
        preferred_spread_pct_of_price=0.05,
    )
    assert not cheap and cheap_reason == "spread_too_wide"
    assert cheap_m["spread_pct_of_price"] > 0.1


def test_double_bottom_detection():
    # Equal troughs separated by a bounce; pad so extrema order=3 works.
    prices = (
        [6, 6, 6, 5, 4, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6]
        + [6.2 + i * 0.05 for i in range(20)]
    )
    bars = [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]
    hits = detect_patterns(bars, timeframe="day")
    names = {h["pattern"] for h in hits}
    assert "double_bottom" in names


def test_greeks_no_invention():
    q = {"delta": "0.45", "gamma": "0.01"}
    pack = extract_greeks(q)
    assert pack["greeks"]["delta"] == 0.45
    assert "theta" in pack["missing_fields"]
    ok, _ = delta_in_band(0.45, option_type="call", lo=0.4, hi=0.5)
    assert ok
    bad, reason = delta_in_band(0.9, option_type="call", lo=0.4, hi=0.5)
    assert not bad and reason is not None
    put_ok, _ = delta_in_band(-0.45, option_type="put", lo=0.4, hi=0.5)
    assert put_ok
    inverted, inv_reason = delta_in_band(0.45, option_type="put", lo=0.4, hi=0.5)
    assert not inverted and inv_reason is not None
    abs_call, abs_reason = delta_in_band(-0.45, option_type="call", lo=0.4, hi=0.5)
    assert not abs_call and abs_reason is not None


def test_options_risk_math():
    plan = options_risk_plan(premium_per_share=2.0, contracts=1)
    assert plan["cash_risked"] == 200.0
    assert plan["take_profit_pct"] == 0.40
    assert plan["stop_loss_pct"] == 0.20
    assert plan["take_profit_value"] == 280.0
    assert plan["stop_loss_value"] == 160.0
    assert plan["reward_to_risk"] == 2.0
    assert plan["meets_target_rr"] is True


def test_options_risk_bands():
    wide = options_risk_plan(premium_per_share=1.0, stop_loss_pct=0.50, take_profit_pct=1.00)
    assert wide["stop_loss_value"] == 50.0
    assert wide["take_profit_value"] == 200.0
    assert wide["reward_to_risk"] == 2.0
    try:
        options_risk_plan(premium_per_share=1.0, stop_loss_pct=0.07, take_profit_pct=0.50)
        raise AssertionError("expected ValueError for SL below 20%")
    except ValueError as exc:
        assert "stop_loss_pct" in str(exc)
    try:
        options_risk_plan(premium_per_share=1.0, stop_loss_pct=0.25, take_profit_pct=0.20)
        raise AssertionError("expected ValueError for TP below 30%")
    except ValueError as exc:
        assert "take_profit_pct" in str(exc)


def test_equity_risk_math():
    plan = equity_risk_plan(cost_basis=1000.0)
    assert plan["take_profit_value"] == 1250.0
    assert plan["stop_loss_value"] == 800.0


def test_atm_pick_and_dte():
    instruments = [
        {"id": "1", "type": "call", "strike_price": "100"},
        {"id": "2", "type": "call", "strike_price": "105"},
        {"id": "3", "type": "put", "strike_price": "95"},
    ]
    pick = pick_atm_or_one_otm(100.0, instruments, option_type="call")
    assert pick["selection"] == "atm"
    assert pick["instrument"]["id"] == "1"
    exps = filter_expirations(["2099-01-01", "2026-09-02"], max_dte=7, as_of=date(2026, 8, 30))
    assert exps == ["2026-09-02"]
    default_min = filter_expirations(
        ["2026-08-30", "2026-08-31", "2026-09-01", "2026-09-02"],
        max_dte=7,
        as_of=date(2026, 8, 30),
    )
    assert default_min == ["2026-09-01", "2026-09-02"]
    locked = filter_expirations(
        ["2026-08-30", "2026-08-31", "2026-09-02"],
        min_dte=2,
        max_dte=7,
        as_of=date(2026, 8, 30),
    )
    assert locked == ["2026-09-02"]


def test_atm_is_nearest_strike_even_when_more_than_one_percent_away():
    instruments = [
        {"id": "itm", "type": "call", "strike_price": "5.0"},
        {"id": "otm", "type": "call", "strike_price": "5.5"},
    ]
    ranked = rank_atm_then_one_otm(5.10, instruments, option_type="call")
    assert ranked[0]["selection"] == "atm"
    assert ranked[0]["instrument"]["id"] == "itm"
    assert ranked[1]["selection"] == "one_otm"
    assert ranked[1]["instrument"]["id"] == "otm"
    pick = pick_atm_or_one_otm(5.10, instruments, option_type="call")
    assert pick["instrument"]["id"] == "itm"


def test_put_atm_then_distinct_one_otm():
    instruments = [
        {"id": "otm", "option_type": "put", "strike": "18.0"},
        {"id": "atm", "option_type": "put", "strike": "18.5"},
    ]
    ranked = rank_atm_then_one_otm(18.30, instruments, option_type="put")
    assert ranked[0]["instrument"]["id"] == "atm"
    assert ranked[1]["instrument"]["id"] == "otm"


def test_strikes_must_bracket_spot_for_atm_page():
    only_low = [{"id": "1", "type": "call", "strike_price": "100"}]
    assert not strikes_bracket_spot(200.0, only_low, option_type="call")
    assert strikes_bracket_spot(100.0, only_low, option_type="call")
    bracketed = only_low + [{"id": "2", "type": "call", "strike_price": "210"}]
    assert strikes_bracket_spot(200.0, bracketed, option_type="call")


def test_today_et_uses_new_york_calendar_not_utc():
    utc_after_midnight = datetime(2026, 9, 1, 2, 0, tzinfo=timezone.utc)
    assert today_et(utc_after_midnight).isoformat() == "2026-08-31"
    et_evening = datetime(2026, 8, 31, 22, 0, tzinfo=ZoneInfo("America/New_York"))
    assert today_et(et_evening).isoformat() == "2026-08-31"


def test_atm_tie_and_otm_are_measured_from_atm():
    instruments = [
        {"id": "low", "type": "call", "strike_price": "100"},
        {"id": "high", "type": "call", "strike_price": "101"},
        {"id": "higher", "type": "call", "strike_price": "102"},
    ]
    call_ranked = rank_atm_then_one_otm(100.5, instruments, option_type="call")
    assert call_ranked[0]["instrument"]["id"] == "low"
    assert call_ranked[1]["instrument"]["id"] == "high"

    puts = [
        {"id": "low", "option_type": "put", "strike": "100"},
        {"id": "high", "option_type": "put", "strike": "101"},
        {"id": "higher", "option_type": "put", "strike": "102"},
    ]
    put_ranked = rank_atm_then_one_otm(100.5, puts, option_type="put")
    assert put_ranked[0]["instrument"]["id"] == "high"
    assert put_ranked[1]["instrument"]["id"] == "low"

    call_above_spot = rank_atm_then_one_otm(100.6, instruments, option_type="call")
    assert call_above_spot[0]["instrument"]["id"] == "high"
    assert call_above_spot[1]["instrument"]["id"] == "higher"


def test_expiration_rank_uses_same_day_group_when_overnight_off():
    dates = ["2026-09-07", "2026-09-08", "2026-09-09", "2026-09-11"]
    as_of = date(2026, 9, 5)
    same_day = rank_expirations(dates, overnight_holding_enabled=False, as_of=as_of)
    assert same_day == ["2026-09-07", "2026-09-08"]
    overnight = rank_expirations(dates, overnight_holding_enabled=True, as_of=as_of)
    assert overnight == ["2026-09-09", "2026-09-11"]


def test_underlying_quote_and_bod_nlv_helpers():
    now = datetime(2026, 9, 4, 17, 30, tzinfo=timezone.utc)
    fresh = {
        "bid_price": "10.00",
        "ask_price": "10.10",
        "last_trade_price": "10.04",
        "updated_at": "2026-09-04T17:29:58Z",
    }
    price, reason = executable_underlying_price(fresh, now=now)
    assert reason is None
    assert price == 10.04
    outside = dict(fresh, last_trade_price="10.50")
    mid, mid_reason = executable_underlying_price(outside, now=now)
    assert mid_reason is None
    assert mid == 10.05
    stale, stale_reason = executable_underlying_price(
        dict(fresh, updated_at="2026-09-04T17:29:50Z"), now=now
    )
    assert stale is None and stale_reason == "underlying_quote_stale"
    amount, field = extract_bod_nlv({"start_of_day_equity": "1500.00", "total_value": "1512"})
    assert amount == 1500.0 and field == "start_of_day_equity"
    missing, missing_field = extract_bod_nlv({"total_value": "1512"})
    assert missing is None and missing_field is None


def test_daily_setup_rank_is_deterministic():
    hits = [
        {
            "pattern": "ascending_triangle",
            "timeframe": "day",
            "bias": "bullish",
            "indices": [20, 80],
            "last_pivot": 80,
            "prominence": 9.0,
        },
        {
            "pattern": "head_and_shoulders",
            "timeframe": "day",
            "bias": "bearish",
            "indices": [10, 20, 30],
            "last_pivot": 30,
            "prominence": 0.02,
        },
        {
            "pattern": "double_bottom",
            "timeframe": "day",
            "bias": "bullish",
            "indices": [10, 40],
            "last_pivot": 40,
            "prominence": 1.0,
        },
        {
            "pattern": "symmetrical_triangle",
            "timeframe": "day",
            "bias": "neutral",
            "indices": [30, 50],
            "prominence": 9.0,
        },
    ]
    ranked = rank_daily_setups(hits)
    assert [row["pattern"] for row in ranked] == [
        "head_and_shoulders",
        "double_bottom",
        "ascending_triangle",
    ]


def test_double_rejects_span_beyond_max_duration():
    prices = [5.0] * 3 + [3.0] + [5.0] * 70 + [3.0] + [5.0] * 6
    bars = [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]
    hits = detect_patterns(bars, timeframe="day")
    assert "double_bottom" not in {h["pattern"] for h in hits}


def test_intraday_patterns_ignored_without_daily_hit():
    prices = [6, 6, 6, 5, 4, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6] + [6.2 + i * 0.05 for i in range(20)]
    bars = [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]
    hits = collect_pattern_hits({"10minute": bars}, ["10minute", "hour", "day"])
    assert hits == []
    daily_first = collect_pattern_hits({"day": bars, "10minute": bars}, ["10minute", "hour", "day"])
    assert any(h["timeframe"] == "day" for h in daily_first)
    assert any(h["timeframe"] == "10minute" for h in daily_first)

# ========================================================================
# pipeline/tests/test_orders.py
# Part: 11 · Tests
# Used by: CI / F
# Working states and locked agent_h schema
# ========================================================================

from pipeline.equity_day_trade import INVERSE_ETF_SYMBOLS
from pipeline.orders import (
    EQUITY_WORKING_STATES,
    OPTION_WORKING_STATES,
    has_working_orders,
    working_orders,
)
from pipeline.io_util import load_rules


def test_working_option_and_equity_states():
    rows = working_orders(
        option_orders=[
            {"id": "o1", "state": "queued"},
            {"id": "o2", "state": "filled"},
            {"id": "o3", "status": "pending_cancelled"},
        ],
        equity_orders=[
            {"id": "e1", "state": "new"},
            {"id": "e2", "state": "cancelled"},
            {"id": "e3", "state": "unconfirmed"},
        ],
    )
    ids = {row["id"] for row in rows}
    assert ids == {"o1", "o3", "e1", "e3"}
    assert has_working_orders([{"state": "confirmed"}], [])
    assert not has_working_orders([{"state": "rejected"}], [{"state": "filled"}])


def test_rules_json_matches_working_states_and_10minute():
    rules = load_rules()
    assert set(rules["orders"]["option_working_states"]) == set(OPTION_WORKING_STATES)
    assert set(rules["orders"]["equity_working_states"]) == set(EQUITY_WORKING_STATES)
    assert rules["patterns"]["timeframes"] == ["10minute", "hour", "day"]
    assert rules["historicals"]["intraday_interval"] == "10minute"
    assert "15minute" not in rules["patterns"]["timeframes"]
    assert rules["options"]["may_hold_overnight_with_stop"] is False
    assert rules["options"]["flatten_at_close"] is True
    assert rules["options"]["overnight_lock_confirmed"] == "2026-09-05"
    assert rules["loop"]["flatten_equity_before_close"] is True
    assert rules["loop"]["options_may_hold_overnight_with_stop"] is False
    assert "flatten_before_close" not in rules["loop"]
    assert rules["git"]["work_on"] == "main"
    assert rules["git"]["open_pull_request"] is False
    assert rules["git"]["create_feature_branch"] is False
    assert rules["agent_h"]["equity_fallback"] is False
    assert rules["agent_h"]["min_dte"] == 2
    assert rules["agent_h"]["max_dte"] == 7
    assert rules["agent_h"]["allow_0dte"] is False
    assert rules["agent_h"]["allow_1dte"] is False
    assert rules["agent_h"]["no_new_entries_before"] == "09:45"
    assert rules["agent_h"]["same_day_expiry_target_flatten_by"] == "15:30"
    assert rules["agent_h"]["same_day_expiry_absolute_deadline"] == "15:45"
    assert rules["agent_h"]["max_new_entries_per_day"] == 2
    assert rules["agent_h"]["max_planned_loss_pct_of_current_nlv"] == 0.005
    assert rules["agent_h"]["max_debit_pct_of_current_nlv"] == 0.025
    assert rules["agent_h"]["max_daily_realized_loss_pct_of_session_start_nlv"] == 0.01
    assert rules["agent_h"]["option_quote"]["min_open_interest"] == 500
    assert rules["agent_h"]["option_quote"]["max_quote_age_seconds"] == 5
    assert rules["agent_h"]["intraday_timeframes"] == ["10minute", "hour", "day"]
    assert rules["agent_h"]["forbidden_timeframes"] == [
        "1minute",
        "3minute",
        "5minute",
        "15minute",
    ]
    assert rules["agent_h"]["chart_hierarchy"] == [
        "daily_setup",
        "hour_confirmation",
        "completed_10minute_trigger",
        "live_quote",
        "option_review",
    ]
    assert rules["agent_h"]["chart_roles"]["day"] == "major_trend_support_resistance_and_chart_pattern"
    assert rules["agent_h"]["chart_roles"]["hour"] == "confirm_direction_reject_conflict_with_broader_intraday_trend"
    assert rules["agent_h"]["chart_roles"]["10minute"] == "confirm_breakout_volume_retest_and_entry_trigger"
    assert rules["agent_h"]["chart_roles"]["live_quote"] == "validate_underlying_trigger_and_price_option_immediately_before_order"
    assert rules["agent_h"]["no_1m_3m_autonomous_noise"] is True
    assert rules["agent_h"]["no_5m_stateless_inconsistency"] is True
    assert rules["agent_h"]["include_index_options"] is False
    assert rules["agent_h"]["schema_version"] == "2026-09-05.3"
    assert rules["agent_h"]["overnight"]["evaluate"] == "current_dte_each_run"
    assert rules["agent_h"]["overnight"]["current_dte_lte_3_flatten_by"] == "15:45"
    assert rules["agent_h"]["overnight"]["current_dte_gte_4_overnight_with_stop"] is False
    assert rules["agent_h"]["overnight_holding_enabled"] is False
    assert rules["agent_h"]["overnight"]["overnight_requires_verified_gtc_stop"] is True
    assert rules["agent_h"]["overnight"]["expiration_day_absolute_deadline"] == "15:45"
    assert rules["agent_h"]["overnight"]["dte_1_to_3_liquidation_begin"] == "15:40"
    assert rules["agent_h"]["lease_valid_only_after_successful_push_to_origin_main"] is True
    assert rules["agent_h"]["recheck_remote_lease_before_every_place_option_order"] is True
    assert rules["agent_h"]["scheduler_must_enforce_max_concurrent_runs"] is False
    assert rules["agent_h"]["git_lease_is_the_concurrency_gate"] is True
    assert rules["agent_h"]["lease_acquire_before_account_or_scan"] is True
    assert rules["agent_h"]["lease_ttl_minutes"] == 12
    assert rules["agent_h"]["lease_renew_if_fewer_than_minutes_remaining"] == 3
    assert rules["agent_h"]["never_force_push_or_overwrite_conflicting_lease"] is True
    assert rules["agent_h"]["failed_lease_acquire_must_not_modify_or_clear_lease"] is True
    assert rules["agent_h"]["only_matching_run_id_may_renew_or_release_lease"] is True
    assert rules["agent_h"]["remote_lease_must_contain_exact_fields"] == [
        "automation_id",
        "run_id",
        "started_et",
        "expires_et",
    ]
    assert rules["agent_h"]["no_review_or_place_until_remote_lease_verified"] is True
    assert rules["agent_h"]["apply_both_fee_ceilings_on_every_trade"] is True
    assert rules["agent_h"]["bod_nlv_unavailable_means_no_new_entry"] is True
    assert rules["priority_does_not_authorize_agent_h_equity"] is True
    assert rules["agent_h"]["session_start_required_for_new_entry"] == [
        "et_trading_date",
        "first_valid_rth_timestamp_et",
        "account",
        "bod_nlv",
        "bod_nlv_field",
        "daily_loss_limit_usd",
    ]
    assert rules["agent_h"]["session_start_diagnostic_only_fields"] == ["first_fire_baseline_nlv"]
    assert (
        rules["agent_h"]["forced_liquidation"]["leftover_4_to_7_dte_while_overnight_disabled"]
        == "treat_as_dte_1_to_3_begin_1540"
    )
    assert rules["agent_h"]["protective_stop"]["time_in_force"] == "gtc"
    assert rules["agent_h"]["cancel_lifecycle"]["never_assume_cancel_means_zero_fill"] is True
    assert rules["agent_h"]["entry_order"]["cancel_confirm_before_replacement"] is True
    assert rules["agent_h"]["take_profit"]["cancel_existing_stop_and_confirm_before_tp"] is True
    assert rules["agent_h"]["take_profit"]["cancel_unfilled_replacement_seconds_after_initial_tp"] == 30
    assert rules["agent_h"]["forced_liquidation"]["dte_1_to_3_begin"] == "15:40"
    assert rules["agent_h"]["patterns"]["daily_neckline_governs_10m_breakout"] is True
    assert rules["agent_h"]["patterns"]["overlapping_rank"][0] == "hs_then_double_triple_then_triangle"
    assert rules["agent_h"]["patterns"]["earliest_practical_entry_after_retest_et"] == "13:10"
    assert rules["agent_h"]["expiration_selection"]["same_day_group_dte"] == [2, 3]
    assert rules["options"]["strike"]["put_delta_min"] == -0.5
    assert rules["options"]["strike"]["call_otm"] == "exactly_one_listed_strike_above_atm"
    assert "get_realized_pnl" in rules["agent_h"]["required_tools"]
    assert "get_earnings_calendar" in rules["agent_h"]["required_tools"]
    assert rules["agent_h"]["patterns"]["breakout_volume_multiple_of_median"] == 1.5
    assert rules["agent_h"]["patterns"]["retest_tolerance_pct"] == 0.002
    assert rules["agent_h"]["patterns"]["live_trigger_beyond_breakout_pct"] == 0.001
    assert rules["agent_h"]["patterns"]["volume_statistic"] == "median"
    assert rules["agent_h"]["estimated_round_trip_fees"] == "3 * entry_fee_from_review"
    assert rules["agent_h"]["entry_fee_source_hierarchy"][0] == "valid_positive_total_fee_only"
    assert rules["agent_h"]["entry_fee_source_hierarchy"][1] == "zero_total_plus_positive_component_is_fee_conflict"
    assert rules["agent_h"]["entry_fee_source_hierarchy"][2] == "zero_total_and_zero_or_absent_components_is_explicit_zero"
    assert rules["agent_h"]["journal_fee_conflict"] is True
    assert rules["agent_h"]["journal_entry_fee_source"] is True
    assert rules["agent_h"]["fee_status_values"] == [
        "quoted",
        "explicit_zero",
        "ambiguous",
        "unavailable",
    ]
    assert rules["agent_h"]["zero_total_plus_positive_component"]["fee_status"] == "ambiguous"
    assert rules["agent_h"]["zero_total_plus_positive_component"]["journal"] == "fee_conflict"
    assert rules["agent_h"]["zero_total_plus_positive_component"]["do_not_sum_or_select_estimate"] is True
    assert rules["agent_h"]["do_not_apply_049_ceiling_when_positive_fee_included"] is False
    assert rules["agent_h"]["universal_fee_gate"] == [
        "planned_loss <= 0.49% current NLV",
        "planned_loss + estimated_round_trip_fees <= 0.50% current NLV",
    ]
    assert rules["agent_h"]["closed_trade_uses_actual_net_pnl_not_estimated_fees"] is True
    assert rules["agent_h"]["allow_0dte"] is False
    assert rules["universe"]["include_index_options"] is False
    assert rules["options"]["min_dte"] == 2


def test_permissions_is_kill_switch_not_a_rules_copy():
    import json
    from pathlib import Path

    perms = json.loads((Path(__file__).resolve().parents[2] / "config" / "autonomous_permissions.json").read_text())
    assert perms["status"] == "ACTIVE"
    assert perms["rules_path"] == "config/rules.json"
    assert "universe" not in perms
    assert "risk" not in perms
    assert "patterns" not in perms


def test_agent_h_prompt_locks_schema_and_live_safety():
    from pathlib import Path

    prompt = (Path(__file__).resolve().parents[2] / "playbooks" / "agent_h_autonomous.PROMPT.md").read_text()
    assert "2026-09-05.3" in prompt
    assert "The lease is not acquired unless its commit successfully pushes to" in prompt
    assert "journal/h_lease.json` from `origin/main`, not merely the local checkout." in prompt
    assert "Never force-push or overwrite a conflicting lease." in prompt
    assert "A run that failed to acquire the lease must not clear or modify the lease." in prompt
    assert "Only the run whose `run_id` matches the remote lease may release it." in prompt
    assert "renew the lease before it has fewer than" in prompt
    assert "## Cursor/Grok concurrency rule" in prompt
    assert "**A. Clock.** Now in `America/New_York`. Clock only. **No RH calls.**" in prompt
    assert "Git on `origin/main` is the required concurrency" in prompt
    assert "acquire and remotely verify lease" in prompt
    assert "time_in_force=gtc" in prompt
    assert "09:30–09:44:59" in prompt
    assert "approximately **13:10–15:45 ET**" in prompt
    assert "Call delta: **+0.40 through +0.50 inclusive**" in prompt
    assert "Put delta: **−0.50 through −0.40 inclusive**" in prompt
    assert "planned_loss` ≤ **0.49% of current NLV**" in prompt
    assert "bod_nlv_unavailable" in prompt
    assert "maximum concurrent runs = 1" not in prompt


def test_inverse_etf_denylist_has_no_duplicate_twm():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "equity_day_trade.py"
    assert src.read_text(encoding="utf-8").count('"TWM"') == 1
    assert "TWM" in INVERSE_ETF_SYMBOLS

# ========================================================================
# pipeline/tests/test_fees.py
# Part: 11 · Tests
# Used by: CI / F
# Dual NLV fee ceilings
# ========================================================================

from pipeline.fees import classify_review_fees, fee_aware_planned_loss_ok


NLV = 1500.0
CEILING_049 = 0.0049 * NLV  # 7.35
CEILING_050 = 0.005 * NLV  # 7.50


def test_positive_total_fee_is_used_alone():
    out = classify_review_fees({"total_fee": "0.65", "commission": "0.65", "sec_fee": "0.02"})
    assert out["fee_status"] == "quoted"
    assert out["entry_fee"] == 0.65
    assert out["journal"] == "total_fee"
    assert out["estimated_round_trip_fees"] == out["entry_fee"] * 3
    assert out["apply_049_ceiling"] is True


def test_zero_total_plus_positive_component_is_fee_conflict():
    out = classify_review_fees({"total_fee": "$0.00", "commission": "0.65"})
    assert out["fee_status"] == "ambiguous"
    assert out["entry_fee"] is None
    assert out["journal"] == "fee_conflict"
    assert out["estimated_exit_fee"] is None
    assert out["estimated_round_trip_fees"] is None
    assert out["apply_049_ceiling"] is True
    assert fee_aware_planned_loss_ok(
        planned_loss=CEILING_049, current_nlv=NLV, classification=out
    )
    assert not fee_aware_planned_loss_ok(
        planned_loss=7.40, current_nlv=NLV, classification=out
    )


def test_zero_total_and_zero_or_absent_components_is_explicit_zero():
    accepted = classify_review_fees({"total_fee": 0, "commission": "0.00"})
    assert accepted["fee_status"] == "explicit_zero"
    assert accepted["entry_fee"] == 0.0
    assert accepted["journal"] == "fee_explicit_zero"
    assert accepted["apply_049_ceiling"] is True

    absent = classify_review_fees({"total_fee": "0.00"})
    assert absent["fee_status"] == "explicit_zero"
    assert absent["entry_fee"] == 0.0
    assert fee_aware_planned_loss_ok(
        planned_loss=CEILING_049, current_nlv=NLV, classification=absent
    )
    assert not fee_aware_planned_loss_ok(
        planned_loss=7.40, current_nlv=NLV, classification=absent
    )


def test_missing_total_sums_non_overlapping_components():
    out = classify_review_fees({"commission": "0.65", "sec_fee": "0.02", "taf_fee": "0.01"})
    assert out["fee_status"] == "quoted"
    assert out["entry_fee"] == 0.68
    assert out["journal"].startswith("components:")
    assert out["apply_049_ceiling"] is True


def test_both_fee_ceilings_apply_on_every_trade():
    out = classify_review_fees({"total_fee": 0.03})
    # 7.40 exceeds 0.49% of $1,500 even though 7.40 + 3*0.03 still fits 0.50%.
    assert out["fee_status"] == "quoted"
    assert out["apply_049_ceiling"] is True
    assert 7.40 > CEILING_049
    assert 7.40 + 0.09 <= CEILING_050
    assert not fee_aware_planned_loss_ok(
        planned_loss=7.40, current_nlv=NLV, classification=out
    )
    assert fee_aware_planned_loss_ok(
        planned_loss=CEILING_049, current_nlv=NLV, classification=out
    )
    expensive = classify_review_fees({"total_fee": 1.00})
    assert not fee_aware_planned_loss_ok(
        planned_loss=CEILING_049, current_nlv=NLV, classification=expensive
    )
    assert fee_aware_planned_loss_ok(
        planned_loss=4.50, current_nlv=NLV, classification=expensive
    )


def test_nested_zero_total_with_positive_component_is_conflict():
    out = classify_review_fees({"fees": {"total_fee": 0, "contract_fee": 0.12}})
    assert out["journal"] == "fee_conflict"
    assert out["entry_fee"] is None


def test_subtotal_plus_parts_is_unavailable():
    out = classify_review_fees({"estimated_fee": "0.70", "commission": "0.65"})
    assert out["fee_status"] == "unavailable"
    assert out["journal"] == "fee_unavailable"
    assert out["apply_049_ceiling"] is True

# ========================================================================
# pipeline/tests/test_session.py
# Part: 11 · Tests
# Used by: CI / F
# ET calendar date and flatten window
# ========================================================================

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pipeline.session import flatten_window, today_et


def test_today_et_before_utc_date_rollover():
    utc = datetime(2026, 9, 5, 0, 42, tzinfo=timezone.utc)
    assert today_et(utc).isoformat() == "2026-09-04"


def test_flatten_window_is_rth_only():
    et = ZoneInfo("America/New_York")
    assert flatten_window(datetime(2026, 8, 31, 15, 50, tzinfo=et))
    assert not flatten_window(datetime(2026, 8, 31, 16, 0, tzinfo=et))

# ========================================================================
# pipeline/tests/test_equity_day_trade.py
# Part: 11 · Tests
# Used by: CI / F
# Long-only equity selection and Phase 2 snapshots
# ========================================================================

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pipeline.equity_day_trade import (
    equity_quote_ok,
    is_inverse_etf,
    regular_hours_buy_ok,
    select_equity_day_trade_candidates,
    whole_share_size,
)
from pipeline.execution import build_equity_entry_proposal, can_place_live
from pipeline.risk import equity_risk_plan
from pipeline.session import (
    ET,
    entries_open,
    flatten_window,
    is_rth,
    option_entries_open,
    session_gate,
)


def test_session_rth_and_1545_cutoff():
    sunday_noon = datetime(2026, 8, 30, 12, 0, tzinfo=ET)
    monday_open = datetime(2026, 8, 31, 9, 30, tzinfo=ET)
    monday_morning = datetime(2026, 8, 31, 10, 0, tzinfo=ET)
    monday_1545 = datetime(2026, 8, 31, 15, 45, tzinfo=ET)
    monday_close = datetime(2026, 8, 31, 16, 0, tzinfo=ET)
    monday_pre = datetime(2026, 8, 31, 9, 29, tzinfo=ET)

    assert not is_rth(sunday_noon)
    assert is_rth(monday_open)
    assert is_rth(monday_morning)
    assert entries_open(monday_open)
    assert not option_entries_open(monday_open)
    assert entries_open(monday_morning)
    assert option_entries_open(monday_morning)
    assert is_rth(monday_1545)
    assert not entries_open(monday_1545)
    assert not option_entries_open(monday_1545)
    assert flatten_window(monday_1545)
    assert not is_rth(monday_close)
    assert not is_rth(monday_pre)
    gate = session_gate(monday_1545)
    assert gate["reason"] == "no_new_entries_after_1545"
    assert gate["option_reason"] == "no_new_entries_after_1545"
    open_gate = session_gate(monday_open)
    assert open_gate["entries_open"] is True
    assert open_gate["option_entries_open"] is False
    assert open_gate["option_reason"] == "no_new_option_entries_before_0945"


def test_whole_share_size_uses_floor_and_buying_power_cap():
    sized = whole_share_size(1500.0, 347.5)
    assert sized["ok"] is True
    assert sized["shares"] == 4
    assert sized["notional"] == 1390.0
    unaffordable = whole_share_size(1500.0, 1975.0)
    assert unaffordable["ok"] is False
    assert unaffordable["reason"] == "cannot_afford_one_share"
    assert whole_share_size(0, 10)["ok"] is False


def test_no_shorting_skips_bearish_and_inverse_etfs():
    assert is_inverse_etf("SQQQ") is True
    assert is_inverse_etf("SPY") is False
    assert is_inverse_etf("XYZ", {"description": "ProShares UltraShort Inverse"}) is True
    assert is_inverse_etf("QID", {"name": "ProShares UltraShort QQQ"}) is True
    assert is_inverse_etf("BIL", {"description": "SPDR Bloomberg 1-3 Month T-Bill Ultra Short Duration"}) is False

    cands, rejected = select_equity_day_trade_candidates(
        symbols=["SQQQ", "AMD", "AAPL"],
        technicals_by_symbol={
            "SQQQ": {"dominant_bias": "bullish"},
            "AMD": {"dominant_bias": "bearish"},
            "AAPL": {"dominant_bias": "bullish"},
        },
        option_candidate_symbols=set(),
        quotes_by_symbol={
            "AAPL": {"bid_price": "100", "ask_price": "100.10"},
            "AMD": {"bid_price": "50", "ask_price": "50.05"},
            "SQQQ": {"bid_price": "10", "ask_price": "10.02"},
        },
        tradability_by_symbol={
            "AAPL": {"regular_hours": {"buy": True}},
            "AMD": {"regular_hours": {"buy": True}},
            "SQQQ": {"regular_hours": {"buy": True}},
        },
        fundamentals_by_symbol={},
        buying_power=1500.0,
        playbook_status="RELEASED",
        take_profit_pct=0.25,
        stop_loss_pct=0.2,
    )
    reasons = {row["symbol"]: row["reason"] for row in rejected}
    assert reasons["SQQQ"] == "inverse_etf"
    assert reasons["AMD"] == "equity_long_only_requires_bullish"
    assert [c["symbol"] for c in cands] == ["AAPL"]
    assert cands[0]["side"] == "buy"
    assert cands[0]["quantity"] == 14  # floor(1500 / 100.10)


def test_options_priority_and_quote_gates():
    cands, rejected = select_equity_day_trade_candidates(
        symbols=["GOOGL", "META"],
        technicals_by_symbol={
            "GOOGL": {"dominant_bias": "bullish"},
            "META": {"dominant_bias": "bullish"},
        },
        option_candidate_symbols={"GOOGL"},
        quotes_by_symbol={"META": {"bid_price": "0", "ask_price": "350"}},
        tradability_by_symbol={
            "GOOGL": {"regular_hours": {"buy": True}},
            "META": {"regular_hours": {"buy": True}},
        },
        fundamentals_by_symbol={},
        buying_power=1500.0,
        playbook_status="RELEASED",
        take_profit_pct=0.25,
        stop_loss_pct=0.2,
    )
    reasons = {row["symbol"]: row["reason"] for row in rejected}
    assert reasons["GOOGL"] == "options_priority"
    assert reasons["META"] == "one_sided_or_missing_quote"
    assert cands == []


def test_equity_quote_and_tradability_parsers():
    ok, reason, metrics = equity_quote_ok({"bid_price": "10", "ask_price": "10.05"})
    assert ok and reason is None and metrics["ask"] == 10.05
    bad, bad_reason, _ = equity_quote_ok({"bid_price": "10", "ask_price": "0"})
    assert not bad and bad_reason == "one_sided_or_missing_quote"
    assert regular_hours_buy_ok({"regular_hours": {"buy": True}}) == (True, None)
    assert regular_hours_buy_ok(None)[0] is False
    assert regular_hours_buy_ok({"halted": True})[0] is False


def test_equity_risk_prices_from_limit():
    plan = equity_risk_plan(cost_basis=1000.0, shares=10, limit_price=100.0)
    assert plan["take_profit_value"] == 1250.0
    assert plan["stop_loss_value"] == 800.0
    assert plan["stop_price"] == 80.0
    assert plan["take_profit_price"] == 125.0
    assert plan["side"] == "long_only"


def test_equity_place_gate_and_proposal_is_buy_only():
    sunday = datetime(2026, 8, 30, 12, 0, tzinfo=ZoneInfo("America/New_York"))
    monday = datetime(2026, 8, 31, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    ok, reason = can_place_live(
        explicit_confirm=True,
        playbook_released=False,
        playbook_kind="equity",
        h_enabled=False,
        now=sunday,
    )
    assert not ok and reason == "equity_playbook_still_draft"
    ok2, reason2 = can_place_live(
        explicit_confirm=False,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=False,
        now=sunday,
    )
    assert not ok2 and reason2 == "missing_explicit_user_confirm"
    sunday_blocked, sunday_reason = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=False,
        now=sunday,
    )
    assert not sunday_blocked and sunday_reason == "outside_rth"
    ok3, reason3 = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=False,
        now=monday,
    )
    assert ok3 and reason3 is None
    blocked, blocked_reason = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=True,
        now=monday,
    )
    assert not blocked and blocked_reason == "h_owns_rth_while_enabled"

    proposal = build_equity_entry_proposal(
        {
            "symbol": "AAPL",
            "quantity": 4,
            "limit_price": 100.0,
            "playbook_status": "RELEASED",
            "risk": {"stop_loss_pct": 0.2, "take_profit_pct": 0.25},
        }
    )
    assert proposal["side"] == "buy"
    assert proposal["action"] == "buy_to_open"
    assert proposal["quantity"] == "4"
    assert proposal["places_order"] is False
    assert proposal["market_hours"] == "regular_hours"
    assert proposal["stop_price_after_fill"] == 80.0
    assert proposal["take_profit_price"] == 125.0


def test_pipeline_writes_equity_candidate_without_placing(tmp_path, monkeypatch):
    import json

    import pipeline.orchestrator as orch

    signals = tmp_path / "signals"
    journal = tmp_path / "journal"
    signals.mkdir()
    journal.mkdir()
    monkeypatch.setattr(orch, "SIGNALS", signals)
    monkeypatch.setattr(orch, "JOURNAL", journal)

    prices = [6, 6, 6, 5, 4, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6] + [6.2 + i * 0.05 for i in range(20)]
    bars = [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"day": bars}},
        "buying_power": 1500.0,
        "equity_quotes_by_symbol": {"AAPL": {"bid_price": "100.00", "ask_price": "100.10"}},
        "equity_tradability_by_symbol": {"AAPL": {"regular_hours": {"buy": True}}},
    }
    summary = orch.run_pipeline(raw)
    assert summary["places_orders"] is False
    assert summary["option_candidate_count"] == 0
    assert summary["equity_candidate_count"] == 1
    payload = json.loads((signals / "equity_candidates.json").read_text())
    assert payload["do_not_place"] is True
    assert payload["h_entry_ready"] is False
    assert payload["agent_h_may_use"] is False
    assert summary["h_entry_ready"] is False
    cand = payload["candidates"][0]
    assert cand["symbol"] == "AAPL"
    assert cand["side"] == "buy"
    assert cand["structure"] == "long_shares"
    assert cand["quantity"] == 14
    assert cand["playbook_status"] == "RELEASED"


def _double_bottom_bars():
    prices = [6, 6, 6, 5, 4, 3, 4, 5, 6, 5, 4, 3, 4, 5, 6] + [6.2 + i * 0.05 for i in range(20)]
    return [{"close": c, "high": c + 0.2, "low": c - 0.2} for c in prices]


def _pipeline_dirs(tmp_path, monkeypatch):
    import pipeline.orchestrator as orch

    signals = tmp_path / "signals"
    journal = tmp_path / "journal"
    signals.mkdir()
    journal.mkdir()
    monkeypatch.setattr(orch, "SIGNALS", signals)
    monkeypatch.setattr(orch, "JOURNAL", journal)
    return orch, signals, journal


def test_intraday_only_bars_do_not_create_equity_bias(tmp_path, monkeypatch):
    import json

    orch, signals, _journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"10minute": bars}},
        "buying_power": 1500.0,
        "equity_quotes_by_symbol": {"AAPL": {"bid_price": "100.00", "ask_price": "100.10"}},
        "equity_tradability_by_symbol": {"AAPL": {"regular_hours": {"buy": True}}},
    }
    summary = orch.run_pipeline(raw)
    assert summary["equity_candidate_count"] == 0
    payload = json.loads((signals / "equity_candidates.json").read_text())
    reasons = {row["symbol"]: row["reason"] for row in payload["rejected"]}
    assert reasons["AAPL"] == "equity_long_only_requires_bullish"


def test_option_candidate_uses_mid_and_falls_back_to_one_otm(tmp_path, monkeypatch):
    import json
    from datetime import timedelta

    from pipeline.session import today_et

    orch, signals, journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    exp = (today_et() + timedelta(days=3)).isoformat()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"day": bars}},
        "buying_power": 1500.0,
        "spots_by_symbol": {"AAPL": 100.0},
        "option_chains_by_symbol": {"AAPL": {"expiration_dates": [exp]}},
        "option_instruments_by_symbol_exp": {
            f"AAPL|{exp}": [
                {"id": "atm", "type": "call", "strike_price": "100"},
                {"id": "otm", "type": "call", "strike_price": "105"},
                {"id": "itm", "type": "call", "strike_price": "95"},
            ]
        },
        "option_quotes_by_id": {
            "atm": {
                "bid_price": "2.00",
                "ask_price": "2.10",
                "delta": "0.55",
                "mark_price": "9.99",
            },
            "otm": {
                "bid_price": "1.00",
                "ask_price": "1.05",
                "delta": "0.45",
                "mark_price": "9.99",
            },
        },
        "equity_quotes_by_symbol": {"AAPL": {"bid_price": "100.00", "ask_price": "100.10"}},
        "equity_tradability_by_symbol": {"AAPL": {"regular_hours": {"buy": True}}},
    }
    summary = orch.run_pipeline(raw)
    assert summary["option_candidate_count"] == 1
    assert summary["equity_candidate_count"] == 0
    payload = json.loads((signals / "option_candidates.json").read_text())
    cand = payload["candidates"][0]
    assert cand["option_id"] == "otm"
    assert cand["selection"] == "one_otm"
    assert cand["premium_mark"] == pytest.approx(1.025)
    assert cand["premium_source"] == "mid"
    assert cand["cash_debit"] == pytest.approx(102.5)
    assert payload["do_not_place"] is True
    assert payload["h_entry_ready"] is False
    assert "hour_confirm" in payload["h_still_requires"]
    assert (journal / f"{today_et().isoformat()}.md").exists()


def test_inverse_etf_never_becomes_option_candidate(tmp_path, monkeypatch):
    import json
    from datetime import timedelta

    from pipeline.session import today_et

    orch, signals, _journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    exp = (today_et() + timedelta(days=3)).isoformat()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "SQQQ"}]},
        "fundamentals_by_symbol": {
            "SQQQ": {"average_volume": 20_000_000, "name": "ProShares UltraPro Short QQQ"}
        },
        "historicals_by_symbol_timeframe": {"SQQQ": {"day": bars}},
        "buying_power": 1500.0,
        "spots_by_symbol": {"SQQQ": 10.0},
        "option_chains_by_symbol": {"SQQQ": {"expiration_dates": [exp]}},
        "option_instruments_by_symbol_exp": {
            f"SQQQ|{exp}": [
                {"id": "atm", "type": "call", "strike_price": "10"},
                {"id": "otm", "type": "call", "strike_price": "11"},
            ]
        },
        "option_quotes_by_id": {
            "atm": {"bid_price": "1.00", "ask_price": "1.05", "delta": "0.45"},
        },
        "portfolio": {"start_of_day_equity": "1500.00", "total_value": "1512"},
    }
    summary = orch.run_pipeline(raw)
    assert summary["option_candidate_count"] == 0
    assert summary["equity_candidate_count"] == 0
    assert "SQQQ" not in summary["eligible_equities"]
    assert summary["bod_nlv"] == 1500.0
    assert summary["bod_nlv_field"] == "start_of_day_equity"
    universe = json.loads((signals / "universe.json").read_text())
    reasons = {row["symbol"]: row["reason"] for row in universe["liquidity"]["rejected"]}
    assert reasons["SQQQ"] == "inverse_etf"


def test_option_candidate_rejects_debit_above_buying_power(tmp_path, monkeypatch):
    import json
    from datetime import timedelta

    from pipeline.session import today_et

    orch, signals, _journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    exp = (today_et() + timedelta(days=3)).isoformat()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"day": bars}},
        "buying_power": 1500.0,
        "spots_by_symbol": {"AAPL": 100.0},
        "option_chains_by_symbol": {"AAPL": {"expiration_dates": [exp]}},
        "option_instruments_by_symbol_exp": {
            f"AAPL|{exp}": [
                {"id": "atm", "type": "call", "strike_price": "100"},
            ]
        },
        "option_quotes_by_id": {
            "atm": {"bid_price": "19.50", "ask_price": "20.50", "delta": "0.45"},
        },
        "equity_quotes_by_symbol": {"AAPL": {"bid_price": "100.00", "ask_price": "100.10"}},
        "equity_tradability_by_symbol": {"AAPL": {"regular_hours": {"buy": True}}},
    }
    summary = orch.run_pipeline(raw)
    assert summary["option_candidate_count"] == 0
    payload = json.loads((signals / "option_candidates.json").read_text())
    reasons = {row["symbol"]: row["reason"] for row in payload["equity_fallbacks"]}
    assert reasons["AAPL"] == "exceeds_buying_power"


def test_incomplete_option_page_is_rejected(tmp_path, monkeypatch):
    import json
    from datetime import timedelta

    from pipeline.session import today_et

    orch, signals, _journal = _pipeline_dirs(tmp_path, monkeypatch)
    bars = _double_bottom_bars()
    exp = (today_et() + timedelta(days=3)).isoformat()
    raw = {
        "watchlists": [{"id": "1", "display_name": "T"}],
        "watchlist_items_by_id": {"1": [{"object_type": "instrument", "symbol": "AAPL"}]},
        "fundamentals_by_symbol": {"AAPL": {"average_volume": 3_000_000}},
        "historicals_by_symbol_timeframe": {"AAPL": {"day": bars}},
        "buying_power": 1500.0,
        "spots_by_symbol": {"AAPL": 200.0},
        "option_chains_by_symbol": {"AAPL": {"expiration_dates": [exp]}},
        "option_instruments_by_symbol_exp": {
            f"AAPL|{exp}": [{"id": "far", "type": "call", "strike_price": "100"}]
        },
        "option_quotes_by_id": {
            "far": {"bid_price": "1.00", "ask_price": "1.05", "delta": "0.45"},
        },
    }
    summary = orch.run_pipeline(raw)
    assert summary["option_candidate_count"] == 0
    payload = json.loads((signals / "option_candidates.json").read_text())
    reasons = {row["symbol"]: row["reason"] for row in payload["equity_fallbacks"]}
    assert reasons["AAPL"] == "option_chain_incomplete_atm_not_in_page"

# ========================================================================
# pipeline/tests/test_execution.py
# Part: 11 · Tests
# Used by: CI / F
# F place-gate including 09:45 option lock
# ========================================================================

from datetime import datetime
from zoneinfo import ZoneInfo

from pipeline.execution import (
    build_option_entry_proposal,
    can_place_live,
    load_latest_equity_candidates,
    load_latest_option_candidates,
)

ET = ZoneInfo("America/New_York")
SUNDAY = datetime(2026, 8, 30, 12, 0, tzinfo=ET)
MONDAY_RTH = datetime(2026, 8, 31, 10, 0, tzinfo=ET)


def test_place_blocked_when_playbook_draft():
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=False, h_enabled=False, now=SUNDAY
    )
    assert not ok
    assert reason == "options_playbook_still_draft"


def test_place_blocked_without_confirm():
    ok, reason = can_place_live(
        explicit_confirm=False, playbook_released=True, h_enabled=False, now=SUNDAY
    )
    assert not ok
    assert reason == "missing_explicit_user_confirm"


def test_place_blocked_outside_rth_even_with_confirm():
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=True, now=SUNDAY
    )
    assert not ok
    assert reason == "outside_rth"


def test_place_blocked_after_1545_even_if_h_disabled():
    monday_1545 = datetime(2026, 8, 31, 15, 45, tzinfo=ET)
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=monday_1545
    )
    assert not ok
    assert reason == "no_new_entries_after_1545"


def test_place_blocked_while_h_owns_rth():
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=True, now=MONDAY_RTH
    )
    assert not ok
    assert reason == "h_owns_rth_while_enabled"


def test_place_blocked_before_0945_for_options_even_if_h_disabled():
    monday_0930 = datetime(2026, 8, 31, 9, 30, tzinfo=ET)
    monday_0944 = datetime(2026, 8, 31, 9, 44, 59, tzinfo=ET)
    monday_0945 = datetime(2026, 8, 31, 9, 45, tzinfo=ET)
    blocked, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=monday_0930
    )
    assert not blocked and reason == "no_new_option_entries_before_0945"
    blocked2, reason2 = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=monday_0944
    )
    assert not blocked2 and reason2 == "no_new_option_entries_before_0945"
    ok, ok_reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=monday_0945
    )
    assert ok and ok_reason is None


def test_equity_place_allowed_at_open_if_h_disabled():
    monday_0930 = datetime(2026, 8, 31, 9, 30, tzinfo=ET)
    ok, reason = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        playbook_kind="equity",
        h_enabled=False,
        now=monday_0930,
    )
    assert ok and reason is None


def test_place_allowed_during_rth_if_h_disabled():
    ok, reason = can_place_live(
        explicit_confirm=True, playbook_released=True, h_enabled=False, now=MONDAY_RTH
    )
    assert ok and reason is None


def test_place_allowed_during_rth_with_override():
    ok, reason = can_place_live(
        explicit_confirm=True,
        playbook_released=True,
        h_enabled=True,
        now=MONDAY_RTH,
        h_rth_override=True,
    )
    assert ok and reason is None


def test_proposal_is_one_contract_buy_to_open():
    cand = {
        "symbol": "SOFI",
        "structure": "long_put",
        "expiration": "2026-09-04",
        "option_type": "put",
        "strike": "18.0",
        "option_id": "abc",
        "playbook_status": "DRAFT_NOT_RELEASED",
    }
    p = build_option_entry_proposal(cand, limit_price="0.43")
    assert p["quantity"] == "1"
    assert p["places_order"] is False
    assert p["legs"][0]["side"] == "buy"
    assert p["legs"][0]["position_effect"] == "open"


def test_load_latest_skips_historical_do_not_place(tmp_path, monkeypatch):
    import json

    import pipeline.execution as execution

    monkeypatch.setattr(execution, "SIGNALS", tmp_path)
    (tmp_path / "option_candidates.json").write_text(
        json.dumps(
            {
                "historical": True,
                "do_not_place": True,
                "candidates": [{"symbol": "SOFI"}],
            }
        )
    )
    (tmp_path / "equity_candidates.json").write_text(
        json.dumps({"do_not_place": True, "candidates": [{"symbol": "AAPL"}]})
    )
    assert load_latest_option_candidates() == []
    assert load_latest_equity_candidates() == []

    (tmp_path / "option_candidates.json").write_text(
        json.dumps({"candidates": [{"symbol": "NU"}]})
    )
    assert load_latest_option_candidates()[0]["symbol"] == "NU"

