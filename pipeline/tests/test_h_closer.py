from pipeline.h_closer import (
    MONITOR,
    PLACE,
    REUSE,
    decide_emergency_close,
    emergency_close_generation,
    emergency_close_ref_id,
    working_close_quantity,
)


def test_ref_id_is_stable_across_fires_and_changes_with_identity():
    first = emergency_close_ref_id(option_id="opt-a", session_date_et="2026-09-08")
    second = emergency_close_ref_id(option_id="opt-a", session_date_et="2026-09-08")
    other = emergency_close_ref_id(option_id="opt-b", session_date_et="2026-09-08")
    next_day = emergency_close_ref_id(option_id="opt-a", session_date_et="2026-09-09")
    after_cancel = emergency_close_ref_id(option_id="opt-a", session_date_et="2026-09-08", generation=1)
    assert first == second
    assert first != other
    assert first != next_day
    assert first != after_cancel
    assert first.count("-") == 4


def test_working_close_covers_leftover_quantity():
    orders = [
        {
            "option_id": "opt-a",
            "state": "confirmed",
            "side": "sell",
            "position_effect": "close",
            "quantity": 1,
            "filled_quantity": 0,
        },
        {
            "option_id": "opt-b",
            "state": "confirmed",
            "side": "sell",
            "position_effect": "close",
            "quantity": 1,
            "filled_quantity": 0,
        },
    ]
    assert working_close_quantity(orders, option_id="opt-a") == 1
    assert working_close_quantity(orders, option_id="opt-c") == 0


def test_generation_increments_only_after_terminal_close():
    working = {
        "option_id": "opt-a",
        "state": "confirmed",
        "kind": "protect",
        "quantity": 1,
        "filled_quantity": 0,
    }
    cancelled = {**working, "state": "cancelled"}
    filled = {**working, "state": "filled", "filled_quantity": 1}
    assert emergency_close_generation([working], option_id="opt-a") == 0
    assert emergency_close_generation([cancelled], option_id="opt-a") == 1
    assert emergency_close_generation([filled], option_id="opt-a") == 0


def test_decide_place_monitor_and_reuse():
    session = "2026-09-08"
    empty = decide_emergency_close(
        option_id="opt-a",
        position_quantity=1,
        option_orders=[],
        session_date_et=session,
    )
    assert empty["action"] == "place" and empty["reason"] == PLACE
    covered = decide_emergency_close(
        option_id="opt-a",
        position_quantity=1,
        option_orders=[
            {
                "option_id": "opt-a",
                "state": "queued",
                "side": "sell",
                "position_effect": "close",
                "quantity": 1,
                "filled_quantity": 0,
            }
        ],
        session_date_et=session,
    )
    assert covered["action"] == "monitor" and covered["reason"] == MONITOR
    reuse = decide_emergency_close(
        option_id="opt-a",
        position_quantity=1,
        option_orders=[
            {
                "option_id": "opt-a",
                "state": "unknown",
                "side": "sell",
                "position_effect": "close",
                "quantity": 1,
                "filled_quantity": 0,
                "ref_id": empty["ref_id"],
            }
        ],
        session_date_et=session,
    )
    assert reuse["action"] == "reuse" and reuse["reason"] == REUSE
    assert reuse["ref_id"] == empty["ref_id"]
    after_cancel = decide_emergency_close(
        option_id="opt-a",
        position_quantity=1,
        option_orders=[
            {
                "option_id": "opt-a",
                "state": "cancelled",
                "kind": "protect",
                "quantity": 1,
                "filled_quantity": 0,
            }
        ],
        session_date_et=session,
    )
    assert after_cancel["action"] == "place"
    assert after_cancel["ref_id"] != empty["ref_id"]


def test_filled_close_covers_stale_position_and_nested_option_id():
    session = "2026-09-08"
    filled = decide_emergency_close(
        option_id="opt-nested",
        position_quantity=1,
        option_orders=[
            {
                "option": {"id": "opt-nested"},
                "state": "filled",
                "side": "sell",
                "position_effect": "close",
                "quantity": 1,
                "filled_quantity": 1,
            }
        ],
        session_date_et=session,
    )
    assert filled["action"] == "monitor"
    assert filled["uncovered"] == 0
    working_nested = decide_emergency_close(
        option_id="opt-nested",
        position_quantity=1,
        option_orders=[
            {
                "legs": [{"option": {"id": "opt-nested"}, "side": "sell", "position_effect": "close"}],
                "state": "confirmed",
                "quantity": 1,
                "filled_quantity": 0,
            }
        ],
        session_date_et=session,
    )
    assert working_nested["action"] == "monitor"


def test_prior_same_day_fill_does_not_cover_later_sequential_open():
    session = "2026-09-08"
    orders = [
        {
            "option_id": "opt-a",
            "state": "filled",
            "side": "buy",
            "position_effect": "open",
            "quantity": 1,
            "filled_quantity": 1,
        },
        {
            "option_id": "opt-a",
            "state": "filled",
            "side": "sell",
            "position_effect": "close",
            "quantity": 1,
            "filled_quantity": 1,
        },
        {
            "option_id": "opt-a",
            "state": "filled",
            "side": "buy",
            "position_effect": "open",
            "quantity": 1,
            "filled_quantity": 1,
        },
    ]
    second = decide_emergency_close(
        option_id="opt-a",
        position_quantity=1,
        option_orders=orders,
        session_date_et=session,
    )
    assert second["action"] == "place"
    assert second["uncovered"] == 1
    stale_after_flat = decide_emergency_close(
        option_id="opt-a",
        position_quantity=1,
        option_orders=orders[:2],
        session_date_et=session,
    )
    assert stale_after_flat["action"] == "monitor"
