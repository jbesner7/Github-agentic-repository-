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
        "apply_049_ceiling": False,
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
    """True if the fee-aware planned-loss gate passes. Other risk checks are separate."""
    if current_nlv <= 0 or planned_loss < 0:
        return False
    status = classification.get("fee_status")
    entry_fee = classification.get("entry_fee")
    if status == "quoted" and isinstance(entry_fee, (int, float)) and entry_fee > 0:
        return (
            planned_loss + (3.0 * float(entry_fee))
            <= PLANNED_LOSS_CEILING_WITH_QUOTED_FEE * current_nlv
        )
    return planned_loss <= PLANNED_LOSS_CEILING_IF_FEE_UNAVAILABLE_OR_ZERO * current_nlv
