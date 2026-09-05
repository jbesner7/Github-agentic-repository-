from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from typing import Any

ET = ZoneInfo("America/New_York")
RTH_START = time(9, 30)
RTH_END = time(16, 0)
NO_NEW_ENTRIES_AFTER = time(15, 45)


def now_et(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(ET)
    if now.tzinfo is None:
        return now.replace(tzinfo=ET)
    return now.astimezone(ET)


def today_et(now: datetime | None = None) -> date:
    """Calendar date in America/New_York. Do not use UTC date.today() for DTE or journals."""
    return now_et(now).date()


def is_weekday(now: datetime | None = None) -> bool:
    return now_et(now).weekday() < 5


def is_rth(now: datetime | None = None) -> bool:
    """Mon–Fri 09:30 inclusive through 16:00 exclusive America/New_York."""
    dt = now_et(now)
    if not is_weekday(dt):
        return False
    t = dt.time()
    return RTH_START <= t < RTH_END


def entries_open(now: datetime | None = None) -> bool:
    """New entries only in RTH before 15:45 ET."""
    dt = now_et(now)
    if not is_rth(dt):
        return False
    return dt.time() < NO_NEW_ENTRIES_AFTER


def flatten_window(now: datetime | None = None) -> bool:
    """Still RTH, but new entries are closed (15:45–16:00 ET)."""
    dt = now_et(now)
    if not is_rth(dt):
        return False
    return dt.time() >= NO_NEW_ENTRIES_AFTER


def session_gate(now: datetime | None = None) -> dict[str, Any]:
    dt = now_et(now)
    rth = is_rth(dt)
    open_for_entry = entries_open(dt)
    reason = None
    if not rth:
        reason = "outside_rth"
    elif not open_for_entry:
        reason = "no_new_entries_after_1545"
    return {
        "timezone": "America/New_York",
        "now_et": dt.isoformat(),
        "is_rth": rth,
        "entries_open": open_for_entry,
        "flatten_window": flatten_window(dt),
        "reason": reason,
    }
