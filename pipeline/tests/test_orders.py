from pipeline.equity_day_trade import INVERSE_ETF_SYMBOLS
from pipeline.orders import (
    EQUITY_WORKING_STATES,
    OPTION_WORKING_STATES,
    has_working_orders,
    working_orders,
)
from pipeline.io_util import load_rules


def test_working_option_and_equity_states():
    rows = working_orders(
        option_orders=[
            {"id": "o1", "state": "queued"},
            {"id": "o2", "state": "filled"},
            {"id": "o3", "status": "pending_cancelled"},
        ],
        equity_orders=[
            {"id": "e1", "state": "new"},
            {"id": "e2", "state": "cancelled"},
            {"id": "e3", "state": "unconfirmed"},
        ],
    )
    ids = {row["id"] for row in rows}
    assert ids == {"o1", "o3", "e1", "e3"}
    assert has_working_orders([{"state": "confirmed"}], [])
    assert not has_working_orders([{"state": "rejected"}], [{"state": "filled"}])


def test_rules_json_matches_working_states_and_10minute():
    rules = load_rules()
    assert set(rules["orders"]["option_working_states"]) == set(OPTION_WORKING_STATES)
    assert set(rules["orders"]["equity_working_states"]) == set(EQUITY_WORKING_STATES)
    assert rules["patterns"]["timeframes"] == ["10minute", "hour", "day"]
    assert rules["historicals"]["intraday_interval"] == "10minute"
    assert "15minute" not in rules["patterns"]["timeframes"]
    assert rules["options"]["may_hold_overnight_with_stop"] is False
    assert rules["options"]["flatten_at_close"] is True
    assert rules["options"]["overnight_lock_confirmed"] == "2026-09-05"
    assert rules["loop"]["flatten_equity_before_close"] is True
    assert rules["loop"]["options_may_hold_overnight_with_stop"] is False
    assert "flatten_before_close" not in rules["loop"]
    assert rules["git"]["work_on"] == "main"
    assert rules["git"]["open_pull_request"] is False
    assert rules["git"]["create_feature_branch"] is False
    assert rules["agent_h"]["equity_fallback"] is False
    assert rules["agent_h"]["min_dte"] == 2
    assert rules["agent_h"]["max_dte"] == 7
    assert rules["agent_h"]["allow_0dte"] is False
    assert rules["agent_h"]["allow_1dte"] is False
    assert rules["agent_h"]["no_new_entries_before"] == "09:45"
    assert rules["agent_h"]["same_day_expiry_target_flatten_by"] == "15:30"
    assert rules["agent_h"]["same_day_expiry_absolute_deadline"] == "15:45"
    assert rules["agent_h"]["max_new_entries_per_day"] == 2
    assert rules["agent_h"]["max_planned_loss_pct_of_current_nlv"] == 0.005
    assert rules["agent_h"]["max_debit_pct_of_current_nlv"] == 0.025
    assert rules["agent_h"]["max_daily_realized_loss_pct_of_session_start_nlv"] == 0.01
    assert rules["agent_h"]["option_quote"]["min_open_interest"] == 500
    assert rules["agent_h"]["option_quote"]["max_quote_age_seconds"] == 5
    assert rules["agent_h"]["intraday_timeframes"] == ["10minute", "hour", "day"]
    assert rules["agent_h"]["forbidden_timeframes"] == [
        "1minute",
        "3minute",
        "5minute",
        "15minute",
    ]
    assert rules["agent_h"]["chart_hierarchy"] == [
        "daily_setup",
        "hour_confirmation",
        "completed_10minute_trigger",
        "live_quote",
        "option_review",
    ]
    assert rules["agent_h"]["chart_roles"]["day"] == "major_trend_support_resistance_and_chart_pattern"
    assert rules["agent_h"]["chart_roles"]["hour"] == "confirm_direction_reject_conflict_with_broader_intraday_trend"
    assert rules["agent_h"]["chart_roles"]["10minute"] == "confirm_breakout_volume_retest_and_entry_trigger"
    assert rules["agent_h"]["chart_roles"]["live_quote"] == "validate_underlying_trigger_and_price_option_immediately_before_order"
    assert rules["agent_h"]["no_1m_3m_autonomous_noise"] is True
    assert rules["agent_h"]["no_5m_stateless_inconsistency"] is True
    assert rules["agent_h"]["include_index_options"] is False
    assert rules["agent_h"]["schema_version"] == "2026-09-05.2"
    assert rules["agent_h"]["overnight"]["evaluate"] == "current_dte_each_run"
    assert rules["agent_h"]["overnight"]["current_dte_lte_3_flatten_by"] == "15:45"
    assert rules["agent_h"]["overnight"]["current_dte_gte_4_overnight_with_stop"] is False
    assert rules["agent_h"]["overnight_holding_enabled"] is False
    assert rules["agent_h"]["overnight"]["overnight_requires_verified_gtc_stop"] is True
    assert rules["agent_h"]["overnight"]["expiration_day_absolute_deadline"] == "15:45"
    assert rules["agent_h"]["overnight"]["dte_1_to_3_liquidation_begin"] == "15:40"
    assert rules["agent_h"]["lease_valid_only_after_successful_push_to_origin_main"] is True
    assert rules["agent_h"]["recheck_remote_lease_before_every_place_option_order"] is True
    assert rules["agent_h"]["scheduler_must_enforce_max_concurrent_runs"] == 1
    assert rules["agent_h"]["apply_both_fee_ceilings_on_every_trade"] is True
    assert rules["agent_h"]["bod_nlv_unavailable_means_no_new_entry"] is True
    assert rules["agent_h"]["protective_stop"]["time_in_force"] == "gtc"
    assert rules["agent_h"]["cancel_lifecycle"]["never_assume_cancel_means_zero_fill"] is True
    assert rules["agent_h"]["entry_order"]["cancel_confirm_before_replacement"] is True
    assert rules["agent_h"]["take_profit"]["cancel_existing_stop_and_confirm_before_tp"] is True
    assert rules["agent_h"]["take_profit"]["cancel_unfilled_replacement_seconds_after_initial_tp"] == 30
    assert rules["agent_h"]["forced_liquidation"]["dte_1_to_3_begin"] == "15:40"
    assert rules["agent_h"]["patterns"]["daily_neckline_governs_10m_breakout"] is True
    assert rules["agent_h"]["patterns"]["earliest_practical_entry_after_retest_et"] == "13:10"
    assert rules["agent_h"]["expiration_selection"]["same_day_group_dte"] == [2, 3]
    assert rules["options"]["strike"]["put_delta_min"] == -0.5
    assert rules["options"]["strike"]["call_otm"] == "exactly_one_listed_strike_above_atm"
    assert "get_realized_pnl" in rules["agent_h"]["required_tools"]
    assert "get_earnings_calendar" in rules["agent_h"]["required_tools"]
    assert rules["agent_h"]["patterns"]["breakout_volume_multiple_of_median"] == 1.5
    assert rules["agent_h"]["patterns"]["retest_tolerance_pct"] == 0.002
    assert rules["agent_h"]["patterns"]["live_trigger_beyond_breakout_pct"] == 0.001
    assert rules["agent_h"]["patterns"]["volume_statistic"] == "median"
    assert rules["agent_h"]["estimated_round_trip_fees"] == "3 * entry_fee_from_review"
    assert rules["agent_h"]["entry_fee_source_hierarchy"][0] == "valid_positive_total_fee_only"
    assert rules["agent_h"]["entry_fee_source_hierarchy"][1] == "zero_total_plus_positive_component_is_fee_conflict"
    assert rules["agent_h"]["entry_fee_source_hierarchy"][2] == "zero_total_and_zero_or_absent_components_is_explicit_zero"
    assert rules["agent_h"]["journal_fee_conflict"] is True
    assert rules["agent_h"]["journal_entry_fee_source"] is True
    assert rules["agent_h"]["fee_status_values"] == [
        "quoted",
        "explicit_zero",
        "ambiguous",
        "unavailable",
    ]
    assert rules["agent_h"]["zero_total_plus_positive_component"]["fee_status"] == "ambiguous"
    assert rules["agent_h"]["zero_total_plus_positive_component"]["journal"] == "fee_conflict"
    assert rules["agent_h"]["zero_total_plus_positive_component"]["do_not_sum_or_select_estimate"] is True
    assert rules["agent_h"]["do_not_apply_049_ceiling_when_positive_fee_included"] is False
    assert rules["agent_h"]["universal_fee_gate"] == [
        "planned_loss <= 0.49% current NLV",
        "planned_loss + estimated_round_trip_fees <= 0.50% current NLV",
    ]
    assert rules["agent_h"]["closed_trade_uses_actual_net_pnl_not_estimated_fees"] is True
    assert rules["agent_h"]["allow_0dte"] is False
    assert rules["universe"]["include_index_options"] is False
    assert rules["options"]["min_dte"] == 2


def test_permissions_is_kill_switch_not_a_rules_copy():
    import json
    from pathlib import Path

    perms = json.loads((Path(__file__).resolve().parents[2] / "config" / "autonomous_permissions.json").read_text())
    assert perms["status"] == "ACTIVE"
    assert perms["rules_path"] == "config/rules.json"
    assert "universe" not in perms
    assert "risk" not in perms
    assert "patterns" not in perms


def test_agent_h_prompt_locks_schema_and_live_safety():
    from pathlib import Path

    prompt = (Path(__file__).resolve().parents[2] / "playbooks" / "agent_h_autonomous.PROMPT.md").read_text()
    assert "2026-09-05.2" in prompt
    assert "A lease is valid only after that commit successfully pushes to `origin/main`" in prompt
    assert "time_in_force=gtc" in prompt
    assert "09:30–09:44:59" in prompt
    assert "approximately **13:10–15:45 ET**" in prompt
    assert "Call delta: **+0.40 through +0.50 inclusive**" in prompt
    assert "Put delta: **−0.50 through −0.40 inclusive**" in prompt
    assert "planned_loss` ≤ **0.49% of current NLV**" in prompt
    assert "bod_nlv_unavailable" in prompt
    assert "maximum concurrent runs = 1" in prompt


def test_inverse_etf_denylist_has_no_duplicate_twm():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "equity_day_trade.py"
    assert src.read_text(encoding="utf-8").count('"TWM"') == 1
    assert "TWM" in INVERSE_ETF_SYMBOLS
