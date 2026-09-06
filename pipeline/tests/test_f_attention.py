from pathlib import Path

from pipeline.f_attention import F_DOES_NOT_RUN, f_may_place, f_may_run_h_scan


ROOT = Path(__file__).resolve().parents[2]


def test_f_chat_does_not_run_h_scan_or_place_without_confirm():
    assert f_may_run_h_scan() is False
    assert f_may_place(
        confirmed_specific_order=False,
        h_enabled=True,
        weekday=0,
        et_time="14:00",
    ) == (False, "no_explicit_confirm_of_specific_order")
    assert f_may_place(
        confirmed_specific_order=True,
        h_enabled=True,
        weekday=0,
        et_time="14:00",
    ) == (False, "h_owns_rth")
    assert f_may_place(
        confirmed_specific_order=True,
        h_enabled=True,
        weekday=6,
        et_time="14:00",
    ) == (True, "ok")
    assert "h_lease_acquire" in F_DOES_NOT_RUN
    assert "h_watchlist_waterfall" in F_DOES_NOT_RUN


def test_agents_md_stays_f_chat_only():
    text = (ROOT / "AGENTS.md").read_text()
    assert "BEGIN AGENT H PROMPT" not in text
    assert "print_card" not in text
    assert "9af478e7-a454-11f1-a7d1-d6b4613131ce" not in text
    assert "specific" in text.lower()
    assert "place nothing" in text.lower()
    assert "Do not keep or paste the H Automation prompt in this chat." in text
    assert "disable the H Automation" in text
    agents = (ROOT / "agents" / "README.md").read_text()
    assert "BEGIN AGENT H PROMPT" not in agents
    assert "Do not paste H into this chat." in agents
    assert "If H is enabled during RTH: **place nothing**." in agents
