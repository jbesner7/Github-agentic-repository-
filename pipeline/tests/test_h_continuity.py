from pipeline.h_closer import MONITOR, PLACE
from pipeline.h_continuity import (
    CONTINUITY_STORE,
    EMERGENCY_CLOSER,
    MANAGE_EXISTING,
    SCAN_IF_FLAT,
    exposure_fields,
    handoff_after_lease_loss,
    leftover_close_plan,
    reconstruct_run_mode,
)
from pipeline.h_gates import RemoteLease


OWNED = RemoteLease(owned_by_this_run=True, expired=False, other_unexpired_holder=False)
OTHER = RemoteLease(owned_by_this_run=False, expired=False, other_unexpired_holder=True)
EXPIRED = RemoteLease(owned_by_this_run=True, expired=True, other_unexpired_holder=False)


def test_stateless_run_reconstructs_from_broker_not_chat():
    assert CONTINUITY_STORE == "broker_positions_and_working_orders"
    assert EMERGENCY_CLOSER == "broker_occupancy_and_deterministic_ref_id"
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
        handoff_after_lease_loss(EXPIRED, git_status="outage", kind="protect")
        == "emergency_protect_from_broker_state"
    )
    assert (
        handoff_after_lease_loss(OTHER, git_status="ok", kind="protect")
        == "place_nothing_new_owner_manages"
    )
    assert (
        handoff_after_lease_loss(OTHER, git_status="outage", kind="protect")
        == "place_nothing_new_owner_manages"
    )
    assert (
        handoff_after_lease_loss(EXPIRED, git_status="ok", kind="protect")
        == "emergency_protect_from_broker_state"
    )
    assert (
        handoff_after_lease_loss(OWNED, git_status="timeout", kind="entry")
        == "place_nothing_git_unavailable"
    )


def test_two_stateless_runs_share_one_closer_plan():
    empty: list = []
    first = leftover_close_plan(
        option_id="opt-nvda",
        position_quantity=1,
        option_orders=empty,
        session_date_et="2026-09-08",
    )
    second = leftover_close_plan(
        option_id="opt-nvda",
        position_quantity=1,
        option_orders=empty,
        session_date_et="2026-09-08",
    )
    assert first["action"] == "place" and first["reason"] == PLACE
    assert first["ref_id"] == second["ref_id"]
    covered = leftover_close_plan(
        option_id="opt-nvda",
        position_quantity=1,
        option_orders=[
            {
                "option_id": "opt-nvda",
                "state": "confirmed",
                "side": "sell",
                "position_effect": "close",
                "quantity": 1,
                "filled_quantity": 0,
            }
        ],
        session_date_et="2026-09-08",
    )
    assert covered["action"] == "monitor" and covered["reason"] == MONITOR
