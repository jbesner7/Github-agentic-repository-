"""Explicit invariant-key registry shared by the H prompt and rules.json.

Each locked threshold has a stable key. The prompt must contain the
rendered line `INV[key]=value` exactly once in the registry block.
Grok must not choose between two different numbers. A mismatch is
`rules_prompt_mismatch`: place nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InvariantSpec:
    key: str
    path: str
    value: Any


def _get(mapping: dict[str, Any], path: str) -> Any:
    cur: Any = mapping
    for part in path.split("."):
        cur = cur[part]
    return cur


def render_inv_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, float):
        return format(value, ".10g")
    return str(value)


def registry_line(spec: InvariantSpec) -> str:
    return f"INV[{spec.key}]={render_inv_value(spec.value)}"


INVARIANT_REGISTRY: tuple[InvariantSpec, ...] = (
    InvariantSpec("schema_version", "schema_version", "2026-09-06.7"),
    InvariantSpec("prompt_expected_schema_version", "prompt_expected_schema_version", "2026-09-06.7"),
    InvariantSpec("no_new_entries_before", "no_new_entries_before", "09:45"),
    InvariantSpec("no_new_entries_after", "no_new_entries_after", "15:45"),
    InvariantSpec("dte_0_liquidation_begin", "overnight.dte_0_liquidation_begin", "15:30"),
    InvariantSpec("dte_1_to_3_liquidation_begin", "overnight.dte_1_to_3_liquidation_begin", "15:40"),
    InvariantSpec("lease_ttl_minutes", "lease_ttl_minutes", 12),
    InvariantSpec("lease_renew_midrun_minutes", "lease_renew_if_fewer_than_minutes_remaining", 3),
    InvariantSpec("lease_renew_before_entry_minutes", "lease_renew_before_entry_unless_minutes_remaining", 6),
    InvariantSpec("min_dte", "min_dte", 2),
    InvariantSpec("max_dte", "max_dte", 7),
    InvariantSpec("max_new_entries_per_day", "max_new_entries_per_day", 2),
    InvariantSpec("stop_after_losing_trades", "stop_after_losing_trades", 2),
    InvariantSpec("cooldown_after_exit_minutes", "cooldown_after_exit_minutes", 30),
    InvariantSpec("planned_loss_hard_ceiling_pct", "max_planned_loss_hard_ceiling_pct_of_current_nlv", 0.0049),
    InvariantSpec("planned_loss_plus_fees_pct", "max_planned_loss_pct_of_current_nlv", 0.005),
    InvariantSpec("max_debit_pct", "max_debit_pct_of_current_nlv", 0.025),
    InvariantSpec("max_daily_realized_loss_pct", "max_daily_realized_loss_pct_of_session_start_nlv", 0.01),
    InvariantSpec("option_quote_max_age_seconds", "option_quote.max_quote_age_seconds", 5),
    InvariantSpec("option_min_volume", "option_quote.min_volume", 100),
    InvariantSpec("option_min_open_interest", "option_quote.min_open_interest", 500),
    InvariantSpec("option_max_spread_pct", "option_quote.max_spread_pct", 0.1),
    InvariantSpec("option_prefer_spread_pct", "option_quote.prefer_spread_pct", 0.05),
    InvariantSpec("underlying_quote_max_age_seconds", "underlying_quote.max_quote_age_seconds", 5),
    InvariantSpec("iv_reject_absolute", "iv.reject_if_absolute_iv_gte", 1.5),
    InvariantSpec("iv_otm_vs_atm_multiple", "iv.one_otm_reject_if_gt_atm_iv_multiple", 1.25),
    InvariantSpec("retest_tolerance_pct", "patterns.retest_tolerance_pct", 0.002),
    InvariantSpec("breakout_close_beyond_pct", "patterns.breakout_close_beyond_level_pct", 0.001),
    InvariantSpec("live_trigger_beyond_pct", "patterns.live_trigger_beyond_breakout_pct", 0.001),
    InvariantSpec("breakout_volume_multiple", "patterns.breakout_volume_multiple_of_median", 1.5),
    InvariantSpec("breakout_volume_lookback", "patterns.breakout_volume_lookback_completed_10m", 20),
    InvariantSpec("triangle_flat_slope_frac", "patterns.triangle_flat_slope_frac", 0.15),
    InvariantSpec("head_prominence_pct", "patterns.head_min_prominence_pct_beyond_both_shoulders", 0.015),
    InvariantSpec("double_triple_variance_pct", "patterns.double_triple_variance_pct", 0.015),
    InvariantSpec("hs_shoulder_variance_pct", "patterns.head_shoulders_shoulder_variance_pct", 0.025),
    InvariantSpec("max_pattern_bars_day", "patterns.max_pattern_bars_day", 60),
    InvariantSpec("max_pattern_bars_hour", "patterns.max_pattern_bars_hour", 40),
    InvariantSpec("hour_trend_lookback", "patterns.hour_trend_lookback_completed", 20),
    InvariantSpec("scan_window_begin", "patterns.earliest_practical_entry_after_retest_et", "13:10"),
    InvariantSpec("max_daily_historicals_per_fire", "fire_budget.max_daily_historicals_per_fire", 8),
    InvariantSpec("max_hour_historicals_per_fire", "fire_budget.max_hour_historicals_per_fire", 3),
    InvariantSpec("max_ten_minute_historicals_per_fire", "fire_budget.max_ten_minute_historicals_per_fire", 2),
    InvariantSpec("same_day_dte_order", "expiration_selection.same_day_dte_order", [4, 5, 6, 7, 3, 2]),
    InvariantSpec("take_profit_multiple", "take_profit.threshold_multiple_of_average_fill", 1.4),
)

REGISTRY_HEADER = "## Invariant registry"
FORBIDDEN_PROMPT = (
    "2026-09-06.6",
    "2026-09-06.5",
    "2026-09-06.4",
    "2026-09-06.3",
    "2026-09-06.2",
    "2026-09-06.1",
    "evaluate **2–3 DTE only**",
    "If last is inside the current bid/ask",
    "time_in_force=gtc",
    "A4.5 Account, recovery tools, then exposure (after a valid remote lease).",
    "including protection and liquidation — is permitted until this run has successfully pushed its lease",
)


def registry_block() -> str:
    lines = [REGISTRY_HEADER, "Each locked number appears once as `INV[key]=value`. Do not restate these values in prose."]
    lines.extend(registry_line(spec) for spec in INVARIANT_REGISTRY)
    return "\n".join(lines)


def compare_rules_to_expected(agent_h: dict[str, Any]) -> list[str]:
    """Return mismatch reasons if rules.json drifted from the locked registry."""
    mismatches: list[str] = []
    for spec in INVARIANT_REGISTRY:
        try:
            actual = _get(agent_h, spec.path)
        except (KeyError, TypeError):
            mismatches.append(f"missing:{spec.path}")
            continue
        if actual != spec.value:
            mismatches.append(f"{spec.path}: {actual!r} != {spec.value!r}")
    return mismatches


def compare_prompt_to_rules(prompt: str, agent_h: dict[str, Any]) -> list[str]:
    """Return mismatch reasons if the prompt registry block does not match rules."""
    mismatches = compare_rules_to_expected(agent_h)
    if REGISTRY_HEADER not in prompt:
        mismatches.append("prompt_missing:invariant_registry_header")
    for spec in INVARIANT_REGISTRY:
        line = registry_line(spec)
        if line not in prompt:
            mismatches.append(f"prompt_missing:{line}")
        elif prompt.count(line) != 1:
            mismatches.append(f"prompt_duplicate:{line}")
    for needle in FORBIDDEN_PROMPT:
        if needle in prompt:
            mismatches.append(f"prompt_has_retired:{needle}")
    return list(dict.fromkeys(mismatches))
