from __future__ import annotations

from datetime import datetime
from typing import Any

from pipeline.io_util import JOURNAL, SIGNALS, append_jsonl, load_rules, read_json, utc_now_iso, write_json
from pipeline.ticks import EQUITY_TICK, protective_stop_price
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
    stop_after_fill = protective_stop_price(price, EQUITY_TICK, stop_frac=(1.0 - stop_pct), asset="equity")
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
        "stop_price_after_fill": float(stop_after_fill) if stop_after_fill is not None else fill * (1.0 - stop_pct),
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
