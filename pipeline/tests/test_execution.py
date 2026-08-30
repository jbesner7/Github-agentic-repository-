from pipeline.execution import build_option_entry_proposal, can_place_live


def test_place_blocked_when_playbook_draft():
    ok, reason = can_place_live(explicit_confirm=True, playbook_released=False)
    assert not ok
    assert reason == "options_playbook_still_draft"


def test_place_blocked_without_confirm():
    ok, reason = can_place_live(explicit_confirm=False, playbook_released=True)
    assert not ok
    assert reason == "missing_explicit_user_confirm"


def test_place_allowed_only_with_confirm_and_release():
    ok, reason = can_place_live(explicit_confirm=True, playbook_released=True)
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
