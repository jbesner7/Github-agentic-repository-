"""Numeric schema invariants shared by the H prompt and rules.json.

Every threshold named in the Automation prompt must match
`config/rules.json` → `agent_h` exactly. Grok must not choose between two
different numbers. A mismatch is `rules_prompt_mismatch`: place nothing.
"""

from __future__ import annotations

from typing import Any


def _get(mapping: dict[str, Any], path: str) -> Any:
    cur: Any = mapping
    for part in path.split("."):
        cur = cur[part]
    return cur


# (rules path, exact rules value, strings that must appear in the H prompt)
NUMERIC_INVARIANTS: tuple[tuple[str, Any, tuple[str, ...]], ...] = (
    ("schema_version", "2026-09-06.3", ("2026-09-06.3",)),
    ("prompt_expected_schema_version", "2026-09-06.3", ("2026-09-06.3",)),
    ("no_new_entries_before", "09:45", ("09:45",)),
    ("no_new_entries_after", "15:45", ("15:45",)),
    ("overnight.dte_0_liquidation_begin", "15:30", ("15:30",)),
    ("overnight.dte_1_to_3_liquidation_begin", "15:40", ("15:40",)),
    ("lease_ttl_minutes", 12, ("12 minutes",)),
    ("lease_renew_if_fewer_than_minutes_remaining", 3, ("3 minutes",)),
    ("lease_renew_before_entry_unless_minutes_remaining", 6, ("6 minutes",)),
    ("min_dte", 2, ("2–7",)),
    ("max_dte", 7, ("2–7",)),
    ("max_new_entries_per_day", 2, ("two",)),
    ("stop_after_losing_trades", 2, ("two",)),
    ("cooldown_after_exit_minutes", 30, ("30 minutes",)),
    ("max_planned_loss_hard_ceiling_pct_of_current_nlv", 0.0049, ("0.49%",)),
    ("max_planned_loss_pct_of_current_nlv", 0.005, ("0.50%",)),
    ("max_debit_pct_of_current_nlv", 0.025, ("2.5%",)),
    ("max_daily_realized_loss_pct_of_session_start_nlv", 0.01, ("1.0%",)),
    ("option_quote.max_quote_age_seconds", 5, ("5 seconds",)),
    ("option_quote.min_volume", 100, ("100",)),
    ("option_quote.min_open_interest", 500, ("500",)),
    ("option_quote.max_spread_pct", 0.1, ("10%",)),
    ("option_quote.prefer_spread_pct", 0.05, ("5%",)),
    ("underlying_quote.max_quote_age_seconds", 5, ("five seconds",)),
    ("iv.reject_if_absolute_iv_gte", 1.5, ("150%",)),
    ("iv.one_otm_reject_if_gt_atm_iv_multiple", 1.25, ("1.25×",)),
    ("patterns.retest_tolerance_pct", 0.002, ("0.20%",)),
    ("patterns.breakout_close_beyond_level_pct", 0.001, ("0.10%",)),
    ("patterns.live_trigger_beyond_breakout_pct", 0.001, ("0.10%",)),
    ("patterns.breakout_volume_multiple_of_median", 1.5, ("1.5×",)),
    ("patterns.breakout_volume_lookback_completed_10m", 20, ("20",)),
    ("patterns.triangle_flat_slope_frac", 0.15, ("0.15",)),
    ("patterns.head_min_prominence_pct_beyond_both_shoulders", 0.015, ("1.5%",)),
    ("patterns.double_triple_variance_pct", 0.015, ("1.5%",)),
    ("patterns.head_shoulders_shoulder_variance_pct", 0.025, ("2.5%",)),
    ("patterns.max_pattern_bars_day", 60, ("60",)),
    ("patterns.max_pattern_bars_hour", 40, ("40",)),
    ("expiration_selection.same_day_dte_order", [4, 5, 6, 7, 3, 2], ("4, 5, 6, 7, 3, 2",)),
    ("take_profit.threshold_multiple_of_average_fill", 1.4, ("1.40",)),
)


def compare_rules_to_expected(agent_h: dict[str, Any]) -> list[str]:
    """Return mismatch reasons if rules.json drifted from the locked table."""
    mismatches: list[str] = []
    for path, expected, _needles in NUMERIC_INVARIANTS:
        try:
            actual = _get(agent_h, path)
        except (KeyError, TypeError):
            mismatches.append(f"missing:{path}")
            continue
        if actual != expected:
            mismatches.append(f"{path}: {actual!r} != {expected!r}")
    return mismatches


def compare_prompt_to_rules(prompt: str, agent_h: dict[str, Any]) -> list[str]:
    """Return mismatch reasons if the prompt does not mirror rules numbers."""
    mismatches = compare_rules_to_expected(agent_h)
    for _path, _expected, needles in NUMERIC_INVARIANTS:
        for needle in needles:
            if needle not in prompt:
                mismatches.append(f"prompt_missing:{needle}")
    forbidden = (
        "2026-09-06.2",
        "evaluate **2–3 DTE only**",
        "If last is inside the current bid/ask",
        "time_in_force=gtc",
    )
    for needle in forbidden:
        if needle in prompt:
            mismatches.append(f"prompt_has_retired:{needle}")
    return list(dict.fromkeys(mismatches))
