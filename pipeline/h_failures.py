"""Failure-injection helpers for Agent H order, lease, Git, and quote faults.

These models are test-only. They do not place live orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.h_closer import REUSE, decide_emergency_close
from pipeline.h_continuity import handoff_after_lease_loss, reconstruct_run_mode
from pipeline.h_gates import RemoteLease, is_emergency_kind, may_place_option_order
from pipeline.quotes import executable_underlying_price


@dataclass
class FakeOrder:
    order_id: str
    kind: str
    state: str = "confirmed"
    filled_quantity: int = 0
    requested_quantity: int = 1
    cancel_reported: bool = False
    option_id: str = "opt-1"
    ref_id: str | None = None

    def as_rh_order(self) -> dict[str, Any]:
        side = "sell" if is_emergency_kind(self.kind) else "buy"
        effect = "close" if is_emergency_kind(self.kind) else "open"
        return {
            "id": self.order_id,
            "kind": self.kind,
            "state": self.state,
            "quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "option_id": self.option_id,
            "side": side,
            "position_effect": effect,
            "ref_id": self.ref_id,
        }


@dataclass
class FakeBroker:
    orders: dict[str, FakeOrder] = field(default_factory=dict)
    positions: int = 0
    tool_timeouts: set[str] = field(default_factory=set)
    place_calls: list[dict[str, Any]] = field(default_factory=list)
    ref_index: dict[str, str] = field(default_factory=dict)
    submitted_tickets: int = 0

    def book(self) -> list[dict[str, Any]]:
        return [order.as_rh_order() for order in self.orders.values()]

    def accept_place(
        self,
        *,
        kind: str,
        quantity: int,
        option_id: str,
        ref_id: str | None,
        reason: str,
    ) -> dict[str, Any]:
        """Broker idempotency: the same ref_id is a retry, not a second ticket."""
        if ref_id and ref_id in self.ref_index:
            return {
                "ok": True,
                "reason": REUSE,
                "order_id": self.ref_index[ref_id],
                "reused": True,
                "ref_id": ref_id,
            }
        order_id = f"{kind}-{self.submitted_tickets + 1}"
        order = FakeOrder(
            order_id=order_id,
            kind=kind,
            requested_quantity=quantity,
            option_id=option_id,
            ref_id=ref_id,
        )
        self.orders[order_id] = order
        self.submitted_tickets += 1
        if ref_id:
            self.ref_index[ref_id] = order_id
        return {"ok": True, "reason": reason, "order_id": order_id, "ref_id": ref_id}

    def place(
        self,
        *,
        kind: str,
        quantity: int,
        lease: RemoteLease,
        git_status: str,
        option_id: str = "opt-1",
        session_date_et: str = "2026-09-08",
        ref_id: str | None = None,
    ) -> dict[str, Any]:
        if "place_option_order" in self.tool_timeouts:
            return {"ok": False, "reason": "tool_timeout"}
        allowed, reason = may_place_option_order(lease, kind=kind, git_status=git_status)
        if not allowed:
            return {"ok": False, "reason": reason}
        if is_emergency_kind(kind):
            decision = decide_emergency_close(
                option_id=option_id,
                position_quantity=quantity,
                option_orders=self.book(),
                session_date_et=session_date_et,
            )
            if decision["action"] in {"monitor", "skip"}:
                return {"ok": False, "reason": decision["reason"], "skipped": True, "ref_id": decision["ref_id"]}
            ref_id = ref_id or decision["ref_id"]
            if decision["action"] == "reuse":
                reason = REUSE
        placed = self.accept_place(
            kind=kind,
            quantity=quantity,
            option_id=option_id,
            ref_id=ref_id,
            reason=reason,
        )
        self.place_calls.append({"kind": kind, "quantity": quantity, "git_status": git_status, "ref_id": ref_id})
        return placed

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
    option_id: str = "opt-1",
    session_date_et: str = "2026-09-08",
) -> dict[str, Any]:
    """Git fetch/push timed out. Emergency protection still places once."""
    mode = reconstruct_run_mode(has_option_position=broker.positions > 0, has_working_order=False)
    handoff = handoff_after_lease_loss(lease, git_status="outage", kind="protect")
    placed = broker.place(
        kind="protect",
        quantity=quantity,
        lease=lease,
        git_status="outage",
        option_id=option_id,
        session_date_et=session_date_et,
    )
    return {"mode": mode, "handoff": handoff, "placed": placed}


def inject_two_stateless_emergency_closes(
    broker: FakeBroker,
    *,
    lease: RemoteLease,
    quantity: int = 1,
    option_id: str = "opt-1",
    session_date_et: str = "2026-09-08",
) -> dict[str, Any]:
    """Two overlapping Git-down fires decide against the same empty book, then submit."""
    snapshot = broker.book()
    first_plan = decide_emergency_close(
        option_id=option_id,
        position_quantity=quantity,
        option_orders=snapshot,
        session_date_et=session_date_et,
    )
    second_plan = decide_emergency_close(
        option_id=option_id,
        position_quantity=quantity,
        option_orders=snapshot,
        session_date_et=session_date_et,
    )
    first = broker.accept_place(
        kind="protect",
        quantity=quantity,
        option_id=option_id,
        ref_id=first_plan["ref_id"],
        reason=first_plan["reason"],
    )
    second = broker.accept_place(
        kind="flatten",
        quantity=quantity,
        option_id=option_id,
        ref_id=second_plan["ref_id"],
        reason=second_plan["reason"],
    )
    return {
        "first_plan": first_plan,
        "second_plan": second_plan,
        "first": first,
        "second": second,
        "tickets": broker.submitted_tickets,
    }


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
