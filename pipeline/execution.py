from __future__ import annotations

from typing import Any

from pipeline.io_util import JOURNAL, SIGNALS, append_jsonl, load_rules, read_json, utc_now_iso, write_json


def load_latest_option_candidates() -> list[dict[str, Any]]:
    path = SIGNALS / "option_candidates.json"
    if not path.exists():
        return []
    payload = read_json(path)
    return list(payload.get("candidates") or [])


def can_place_live(*, explicit_confirm: bool, playbook_released: bool) -> tuple[bool, str | None]:
    """Agent F place-gate. Never invent a confirm."""
    if not playbook_released:
        return False, "options_playbook_still_draft"
    if not explicit_confirm:
        return False, "missing_explicit_user_confirm"
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


def record_review(proposal: dict[str, Any], review_response: dict[str, Any] | None, *, error: str | None = None) -> dict[str, Any]:
    rules = load_rules()
    released = rules["options"]["playbook_status"] == "RELEASED"
    allowed, reason = can_place_live(explicit_confirm=False, playbook_released=released)
    record = {
        "event": "phase3_dry_review",
        "as_of": utc_now_iso(),
        "proposal": proposal,
        "review": review_response,
        "error": error,
        "places_order": False,
        "playbook_status": rules["options"]["playbook_status"],
        "place_gate": {"allowed": allowed, "reason": reason},
    }
    write_json(SIGNALS / "execution_review.json", record)
    append_jsonl(JOURNAL / "reviews.jsonl", record)
    return record
