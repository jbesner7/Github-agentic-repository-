from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pipeline.session import flatten_window, today_et


def test_today_et_before_utc_date_rollover():
    utc = datetime(2026, 9, 5, 0, 42, tzinfo=timezone.utc)
    assert today_et(utc).isoformat() == "2026-09-04"


def test_flatten_window_is_rth_only():
    et = ZoneInfo("America/New_York")
    assert flatten_window(datetime(2026, 8, 31, 15, 50, tzinfo=et))
    assert not flatten_window(datetime(2026, 8, 31, 16, 0, tzinfo=et))
