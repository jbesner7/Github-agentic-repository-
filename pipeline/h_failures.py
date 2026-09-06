"""Failure-injection helpers for Agent H order, lease, Git, and quote faults.

These models are test-only. They do not place live orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.h_continuity import handoff_after_lease_loss, reconstruct_run_mode
from pipeline.h_gates import RemoteLease, may_place_option_order
from pipeline.quotes import executable_underlying_price


@dataclass
class FakeOrder:
    order_id: str
    kind: str
    state: str = "confirmed"
    filled_quantity: int = 0
    requested_quantity: int = 1
    cancel_reported: bool = False


@dataclass
class FakeBroker:
    orders: dict[str, FakeOrder] = field(default_factory=dict)
    positions: int = 0
    tool_timeouts: set[str] = field(default_factory=set)
    place_calls: list[dict[str, Any]] = field(default_factory=list)

    def place(self, *, kind: str, quantity: int, lease: RemoteLease, git_status: str) -> dict[str, Any]:
        if "place_option_order" in self.tool_timeouts:
            return {"ok": False, "reason": "tool_timeout"}
        allowed, reason = may_place_option_order(lease, kind=kind, git_status=git_status)
        if not allowed:
            return {"ok": False, "reason": reason}
        order_id = f"{kind}-{len(self.place_calls) + 1}"
        order = FakeOrder(order_id=order_id, kind=kind, requested_quantity=quantity)
        self.orders[order_id] = order
        self.place_calls.append({"kind": kind, "quantity": quantity, "git_status": git_status})
        return {"ok": True, "reason": reason, "order_id": order_id}

    def fill(self, order_id: str, quantity: int) -> None:
        order = self.orders[order_id]
        order.filled_quantity += quantity
        order.state = "filled" if order.filled_quantity >= order.requested_quantity else "partially_filled"
        self.positions += quantity

    def request_cancel(self, order_id: str, *, filled_despite_cancel: int = 0) -> FakeOrder:
        order = self.orders[order_id]
        order.cancel_reported = True
        order.state = "cancelled"
        if filled_despite_cancel:
            order.filled_quantity += filled_despite_cancel
            self.positions += filled_despite_cancel
        return order

    def reconcile_after_cancel(self, order_id: str) -> dict[str, Any]:
        order = self.orders[order_id]
        must_protect = order.filled_quantity > 0
        return {
            "state": order.state,
            "filled_quantity": order.filled_quantity,
            "must_protect": must_protect,
            "never_assume_zero_fill": True,
        }


def inject_git_outage_then_protect(
    broker: FakeBroker,
    *,
    lease: RemoteLease,
    quantity: int = 1,
) -> dict[str, Any]:
    """Git fetch/push timed out. Emergency protection still places."""
    mode = reconstruct_run_mode(has_option_position=broker.positions > 0, has_working_order=False)
    handoff = handoff_after_lease_loss(lease, git_status="outage", this_run_filled=True, kind="protect")
    placed = broker.place(kind="protect", quantity=quantity, lease=lease, git_status="outage")
    return {"mode": mode, "handoff": handoff, "placed": placed}


def inject_lease_loss_while_git_up(
    broker: FakeBroker,
    *,
    lease: RemoteLease,
    quantity: int = 1,
) -> dict[str, Any]:
    """Git is reachable. Another holder owns the lease: do not place."""
    placed = broker.place(kind="protect", quantity=quantity, lease=lease, git_status="ok")
    return {"placed": placed}


def inject_canceled_but_filled(broker: FakeBroker, order_id: str, filled: int = 1) -> dict[str, Any]:
    broker.request_cancel(order_id, filled_despite_cancel=filled)
    return broker.reconcile_after_cancel(order_id)


def inject_stale_underlying_quote(quote: dict[str, Any], *, now) -> tuple[float | None, str | None]:
    return executable_underlying_price(quote, direction="call", now=now)


def inject_tool_timeout(broker: FakeBroker, *, lease: RemoteLease, kind: str) -> dict[str, Any]:
    broker.tool_timeouts.add("place_option_order")
    return broker.place(kind=kind, quantity=1, lease=lease, git_status="ok")
