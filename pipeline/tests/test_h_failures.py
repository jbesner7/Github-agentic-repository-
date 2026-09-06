from datetime import datetime, timezone

from pipeline.h_closer import MONITOR
from pipeline.h_failures import (
    FakeBroker,
    inject_canceled_but_filled,
    inject_git_outage_then_protect,
    inject_lease_loss_while_git_up,
    inject_stale_underlying_quote,
    inject_tool_timeout,
    inject_two_stateless_emergency_closes,
)
from pipeline.h_gates import RemoteLease


OWNED = RemoteLease(owned_by_this_run=True, expired=False, other_unexpired_holder=False)
OTHER = RemoteLease(owned_by_this_run=False, expired=False, other_unexpired_holder=True)
EXPIRED = RemoteLease(owned_by_this_run=True, expired=True, other_unexpired_holder=False)
UNREADABLE = RemoteLease(owned_by_this_run=False, expired=True, other_unexpired_holder=False, readable=False)


def test_entry_fill_then_protect_while_git_up():
    broker = FakeBroker()
    placed = broker.place(kind="entry", quantity=1, lease=OWNED, git_status="ok")
    assert placed["ok"] is True
    broker.fill(placed["order_id"], 1)
    assert broker.positions == 1
    protect = broker.place(kind="protect", quantity=1, lease=OWNED, git_status="ok")
    assert protect["ok"] is True


def test_fill_then_git_outage_still_protects():
    broker = FakeBroker(positions=1)
    result = inject_git_outage_then_protect(broker, lease=UNREADABLE)
    assert result["handoff"] == "emergency_protect_from_broker_state"
    assert result["placed"]["ok"] is True
    assert result["placed"]["reason"] == "emergency_protection_without_git"


def test_lease_loss_to_other_holder_blocks_when_git_is_up():
    broker = FakeBroker(positions=1)
    result = inject_lease_loss_while_git_up(broker, lease=OTHER)
    assert result["placed"]["ok"] is False
    assert result["placed"]["reason"] == "lease_held_after_fill"


def test_canceled_but_filled_must_protect():
    broker = FakeBroker()
    placed = broker.place(kind="entry", quantity=1, lease=OWNED, git_status="ok")
    rec = inject_canceled_but_filled(broker, placed["order_id"], filled=1)
    assert rec["state"] == "cancelled"
    assert rec["filled_quantity"] == 1
    assert rec["must_protect"] is True
    protect = broker.place(kind="protect", quantity=1, lease=OWNED, git_status="ok")
    assert protect["ok"] is True


def test_stale_quote_blocks_entry():
    now = datetime(2026, 9, 8, 17, 30, 0, tzinfo=timezone.utc)
    px, reason = inject_stale_underlying_quote(
        {
            "bid_price": "10.00",
            "ask_price": "10.10",
            "updated_at": "2026-09-08T17:29:50Z",
        },
        now=now,
    )
    assert px is None
    assert reason == "underlying_quote_stale"


def test_tool_timeout_fail_closed_on_entry_not_on_emergency_if_tool_recovers():
    broker = FakeBroker()
    timed_out = inject_tool_timeout(broker, lease=OWNED, kind="entry")
    assert timed_out["ok"] is False
    assert timed_out["reason"] == "tool_timeout"
    broker.tool_timeouts.clear()
    emergency = broker.place(kind="protect", quantity=1, lease=EXPIRED, git_status="timeout")
    assert emergency["ok"] is True
    assert emergency["reason"] == "emergency_protection_without_git"


def test_two_stateless_git_down_fires_submit_one_close():
    broker = FakeBroker(positions=1)
    result = inject_two_stateless_emergency_closes(broker, lease=UNREADABLE)
    assert result["first_plan"]["ref_id"] == result["second_plan"]["ref_id"]
    assert result["first"]["ok"] is True
    assert result["second"]["ok"] is True
    assert result["second"]["reused"] is True
    assert result["first"]["order_id"] == result["second"]["order_id"]
    assert result["tickets"] == 1


def test_second_fire_monitors_existing_working_close():
    broker = FakeBroker(positions=1)
    first = broker.place(kind="protect", quantity=1, lease=UNREADABLE, git_status="outage")
    assert first["ok"] is True
    second = broker.place(kind="flatten", quantity=1, lease=UNREADABLE, git_status="outage")
    assert second["ok"] is False
    assert second["reason"] == MONITOR
    assert broker.submitted_tickets == 1
