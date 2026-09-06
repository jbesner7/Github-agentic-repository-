from pipeline.h_continuity import (
    CONTINUITY_STORE,
    MANAGE_EXISTING,
    SCAN_IF_FLAT,
    chat_is_not_continuity_store,
    exposure_fields,
    handoff_after_lease_loss,
    next_fire_must_reconstruct_from_broker,
    reconstruct_run_mode,
)
from pipeline.h_gates import RemoteLease


OWNED = RemoteLease(owned_by_this_run=True, expired=False, other_unexpired_holder=False)
OTHER = RemoteLease(owned_by_this_run=False, expired=False, other_unexpired_holder=True)
EXPIRED = RemoteLease(owned_by_this_run=True, expired=True, other_unexpired_holder=False)


def test_stateless_run_reconstructs_from_broker_not_chat():
    assert CONTINUITY_STORE == "broker_positions_and_working_orders"
    assert chat_is_not_continuity_store() is True
    assert next_fire_must_reconstruct_from_broker() is True
    assert reconstruct_run_mode(has_option_position=True, has_working_order=False) == MANAGE_EXISTING
    assert reconstruct_run_mode(has_option_position=False, has_working_order=True) == MANAGE_EXISTING
    assert reconstruct_run_mode(has_option_position=False, has_working_order=False) == SCAN_IF_FLAT
    identity = exposure_fields(
        {"option_id": "abc", "quantity": "1", "average_price": "2.10", "chain_symbol": "NVDA"}
    )
    assert identity["option_id"] == "abc"
    assert identity["chain_symbol"] == "NVDA"


def test_handoff_git_outage_vs_other_holder():
    assert (
        handoff_after_lease_loss(EXPIRED, git_status="outage", this_run_filled=True, kind="protect")
        == "emergency_protect_from_broker_state"
    )
    assert (
        handoff_after_lease_loss(OTHER, git_status="ok", this_run_filled=True, kind="protect")
        == "place_nothing_new_owner_manages"
    )
    assert (
        handoff_after_lease_loss(EXPIRED, git_status="ok", this_run_filled=True, kind="protect")
        == "reacquire_then_recover"
    )
    assert (
        handoff_after_lease_loss(OWNED, git_status="timeout", this_run_filled=False, kind="entry")
        == "place_nothing_git_unavailable"
    )
