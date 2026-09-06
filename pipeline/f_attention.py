"""Agent F (this chat) attention lock.

F does not run H’s waterfall, lease machine, or scan budget. F places only
after an explicit confirm of a specific order, and never during RTH while
H is enabled.
"""

from __future__ import annotations

from pipeline.h_budget import is_rth


F_LOCKS = (
    "pipeline.execution",
    "pipeline.f_attention",
    "config/rules.json",
)
F_DOES_NOT_RUN = (
    "h_watchlist_waterfall",
    "h_historicals_budget",
    "h_option_chain_scan",
    "h_lease_acquire",
)


def f_may_place(
    *,
    confirmed_specific_order: bool,
    h_enabled: bool,
    weekday: int,
    et_time: object,
    owner_stop_all: bool = False,
) -> tuple[bool, str]:
    if owner_stop_all:
        return False, "owner_revoked_all_order_activity"
    if not confirmed_specific_order:
        return False, "no_explicit_confirm_of_specific_order"
    if h_enabled and is_rth(weekday=weekday, et_time=et_time):
        return False, "h_owns_rth"
    return True, "ok"


def f_may_run_h_scan() -> bool:
    return False
