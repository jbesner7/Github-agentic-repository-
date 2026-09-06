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
    assert rules["agent_h"]["schema_version"] == "2026-09-06.6"
    assert rules["agent_h"]["prompt_expected_schema_version"] == "2026-09-06.6"
    assert rules["agent_h"]["emergency_protection_path_does_not_require_git"] is True
    assert rules["agent_h"]["git_unavailable_allows_emergency_protection_without_lease"] is True
    assert rules["agent_h"]["emergency_close_serialized_by_broker_not_git"] is True
    assert rules["agent_h"]["one_working_sell_to_close_per_option_position"] is True
    assert rules["agent_h"]["emergency_close_uses_deterministic_ref_id"] is True
    assert rules["agent_h"]["duplicate_emergency_ref_id_is_retry_not_new_order"] is True
    assert rules["agent_h"]["overlapping_stateless_runs_must_not_submit_duplicate_closes"] is True
    assert rules["agent_h"]["known_other_lease_holder_blocks_emergency_even_if_git_unavailable"] is True
    assert rules["agent_h"]["entry_order"]["skip_if_required_cash_exceeds_buying_power"] is True
    assert rules["agent_h"]["continuity_store"] == "broker_positions_and_working_orders"
    assert rules["agent_h"]["patterns"]["hour_trend_lookback_completed"] == 20
    assert rules["agent_h"]["read_rules_permissions_playbook_before_any_place"] is True
    assert rules["agent_h"]["schema_or_rules_prompt_mismatch_blocks_all_orders_including_exits"] is True
    assert rules["agent_h"]["numeric_thresholds_are_schema_invariants"] is True
    assert rules["agent_h"]["rules_prompt_mismatch_means_place_nothing"] is True
    assert rules["agent_h"]["lease_renew_before_entry_unless_minutes_remaining"] == 6
    assert rules["agent_h"]["account_selection_before_exposure_reconciliation"] is True
    assert rules["agent_h"]["core_recovery_capability_before_full_required_tools"] is True
    assert rules["agent_h"]["take_profit"]["round_threshold_up_to_next_valid_tick"] is True
    assert rules["agent_h"]["overnight"]["evaluate"] == "current_dte_each_run"
    assert rules["agent_h"]["overnight"]["current_dte_lte_3_flatten_by"] == "15:45"
    assert rules["agent_h"]["overnight"]["current_dte_gte_4_overnight_with_stop"] is False
    assert rules["agent_h"]["overnight_holding_enabled"] is False
    assert rules["agent_h"]["overnight"]["overnight_requires_verified_gtc_stop"] is True
    assert rules["agent_h"]["overnight"]["expiration_day_absolute_deadline"] == "15:45"
    assert rules["agent_h"]["overnight"]["dte_1_to_3_liquidation_begin"] == "15:40"
    assert rules["agent_h"]["lease_valid_only_after_successful_push_to_origin_main"] is True
    assert rules["agent_h"]["recheck_remote_lease_before_every_place_option_order"] is False
    assert rules["agent_h"]["recheck_remote_lease_before_every_new_entry_place_option_order"] is True
    assert rules["agent_h"]["reacquire_lease_before_any_place_if_expired_and_unowned"] is True
    assert rules["agent_h"]["never_place_from_momentary_absent_other_lease"] is True
    assert rules["agent_h"]["renew_lease_immediately_before_entry_placement"] is True
    assert rules["agent_h"]["new_lease_owner_exposure_has_priority_over_scan"] is True
    assert rules["agent_h"]["inactive_permissions_block_new_entries_only"] is True
    assert rules["agent_h"]["inactive_permissions_allow_cancel_protect_reduce_close"] is True
    assert rules["agent_h"]["owner_stop_all_including_exits_revokes_recovery"] is True
    assert rules["agent_h"]["failed_lease_push_means_place_nothing_and_exit"] is False
    assert rules["agent_h"]["failed_lease_acquire_push_means_place_nothing_and_exit"] is True
    assert rules["agent_h"]["rejected_lease_push_means_place_nothing_and_exit"] is False
    assert rules["agent_h"]["rejected_lease_acquire_push_means_place_nothing_and_exit"] is True
    assert rules["agent_h"]["no_review_or_place_until_remote_lease_verified"] is False
    assert rules["agent_h"]["no_new_entry_review_or_place_until_remote_lease_verified"] is True
    assert rules["agent_h"]["failed_lease_renewal_blocks_new_entry_only"] is False
    assert rules["agent_h"]["failed_lease_renewal_must_still_protect_or_flatten_this_run_fill"] is False
    assert rules["agent_h"]["protection_or_flatten_of_this_run_fill_allowed_after_failed_renewal"] is False
    assert rules["agent_h"]["this_run_fill_must_protect_or_flatten_even_if_remote_lease_mismatched_or_expired"] is False
    assert rules["agent_h"]["this_run_fill_must_protect_or_flatten_if_lease_expired_or_unreadable_and_no_other_run_holds_it"] is False
    assert rules["agent_h"]["no_review_or_place_until_remote_lease_verified"] is False
    assert rules["agent_h"]["this_run_fill_must_not_place_if_another_run_id_holds_remote_lease"] is True
    assert rules["agent_h"]["other_run_lease_owner_handles_leftover_exposure"] is True
    assert rules["agent_h"]["entry_order"]["max_acceptable_debit_is_not_first_limit"] is True
    assert rules["agent_h"]["entry_order"]["max_acceptable_debit_is_tick_floored"] is True
    assert rules["agent_h"]["entry_order"]["max_acceptable_debit"].startswith("tick_floor(")
    assert rules["agent_h"]["entry_order"]["skip_replacement_if_plus_one_tick_exceeds_max_or_live_ask"] is True
    assert rules["agent_h"]["protective_stop"]["round_trigger_to_min_ticks"] is True
    assert rules["agent_h"]["protective_stop"]["never_round_stop_away_from_fill"] is True
    assert rules["agent_h"]["forced_liquidation"]["do_not_restore_stop_during_forced_liquidation"] is True
    assert rules["agent_h"]["forced_liquidation"]["restore_protective_stop_if_unfilled"] is False
    assert rules["agent_h"]["after_pull_or_rebase_reread_remote_lease_before_writing_h_lease"] is True
    assert rules["agent_h"]["acquire_retry_uses_remote_lease_only_not_this_run_working_tree_write"] is True
    assert rules["agent_h"]["this_run_working_tree_lease_write_does_not_block_acquire_retry"] is True
    assert rules["agent_h"]["never_overwrite_unexpired_remote_lease_held_by_other_run_id"] is True
    assert rules["agent_h"]["fast_forward_pull_of_other_run_lease_is_held_not_free"] is True
    assert rules["agent_h"]["pull_ff_only_or_rebase_onto_origin_main_before_every_main_journal_push"] is True
    assert rules["agent_h"]["non_fast_forward_lease_or_journal_push_retry_once_after_rebase"] is True
    assert rules["agent_h"]["never_force_push_on_non_fast_forward"] is True
    assert rules["agent_h"]["scheduler_must_enforce_max_concurrent_runs"] is False
    assert rules["agent_h"]["git_lease_is_the_concurrency_gate"] is True
    assert rules["agent_h"]["lease_acquire_before_account_or_scan"] is True
    assert rules["agent_h"]["lease_ttl_minutes"] == 12
    assert rules["agent_h"]["lease_renew_if_fewer_than_minutes_remaining"] == 3
    assert rules["agent_h"]["never_force_push_or_overwrite_conflicting_lease"] is True
    assert rules["agent_h"]["failed_lease_acquire_must_not_modify_or_clear_lease"] is True
    assert rules["agent_h"]["only_matching_run_id_may_renew_or_release_lease"] is True
    assert rules["agent_h"]["remote_lease_must_contain_exact_fields"] == [
        "automation_id",
        "run_id",
        "started_et",
        "expires_et",
    ]
    assert rules["agent_h"]["apply_both_fee_ceilings_on_every_trade"] is True
    assert rules["agent_h"]["bod_nlv_unavailable_means_no_new_entry"] is True
    assert rules["priority_does_not_authorize_agent_h_equity"] is True
    assert rules["agent_h"]["session_start_required_for_new_entry"] == [
        "et_trading_date",
        "first_valid_rth_timestamp_et",
        "account",
        "bod_nlv",
        "bod_nlv_field",
        "daily_loss_limit_usd",
    ]
    assert rules["agent_h"]["session_start_diagnostic_only_fields"] == ["first_fire_baseline_nlv"]
    assert (
        rules["agent_h"]["forced_liquidation"]["leftover_4_to_7_dte_while_overnight_disabled"]
        == "treat_as_dte_1_to_3_begin_1540"
    )
    assert rules["agent_h"]["protective_stop"]["time_in_force"] == "gfd"
    assert rules["agent_h"]["protective_stop"]["do_not_attempt_gtc"] is True
    assert rules["agent_h"]["protective_stop"]["rounded_stop_must_remain_below_live_option_bid"] is True
    assert rules["agent_h"]["entry_order"]["never_infer_tick_from_premium"] is True
    assert rules["agent_h"]["underlying_quote"]["never_describe_last_or_midpoint_as_executable"] is True
    assert rules["agent_h"]["underlying_quote"]["bullish_call_uses_live_underlying_ask"] is True
    assert rules["agent_h"]["underlying_quote"]["bearish_put_uses_live_underlying_bid"] is True
    assert rules["agent_h"]["underlying_quote"]["prefer_last_if_inside_bid_ask"] is False
    assert rules["agent_h"]["underlying_quote"]["else_use_midpoint_as_executable_price"] is False
    assert rules["agent_h"]["forced_liquidation"]["one_replacement_limit_does_not_apply_to_mandatory_or_protection_failed_liquidation"] is True
    assert rules["agent_h"]["forced_liquidation"]["mandatory_liquidation_repeat_every_seconds"] == 15
    assert rules["agent_h"]["atm_fallback"]["do_not_try_another_contract_if_review_order_checks_block_atm"] is True
    assert rules["agent_h"]["patterns"]["retest_bullish_low_must_enter_zone"] is True
    assert rules["agent_h"]["patterns"]["retest_bearish_high_must_enter_zone"] is True
    assert rules["agent_h"]["overnight"]["do_not_attempt_gtc_unless_schema_confirms_support"] is True
    assert rules["agent_h"]["grok_decides"] == ["pattern", "direction", "candidate"]
    assert rules["agent_h"]["cancel_lifecycle"]["never_assume_cancel_means_zero_fill"] is True
    assert rules["agent_h"]["entry_order"]["cancel_confirm_before_replacement"] is True
    assert rules["agent_h"]["take_profit"]["cancel_existing_stop_and_confirm_before_tp"] is True
    assert rules["agent_h"]["take_profit"]["cancel_unfilled_replacement_seconds_after_initial_tp"] == 30
    assert rules["agent_h"]["forced_liquidation"]["dte_1_to_3_begin"] == "15:40"
    assert rules["agent_h"]["patterns"]["daily_neckline_governs_10m_breakout"] is True
    assert rules["agent_h"]["patterns"]["overlapping_rank"][0] == "hs_then_double_triple_then_triangle"
    assert rules["agent_h"]["patterns"]["earliest_practical_entry_after_retest_et"] == "13:10"
    assert rules["agent_h"]["expiration_selection"]["same_day_group_dte"] == [4, 5, 6, 7, 3, 2]
    assert rules["agent_h"]["expiration_selection"]["same_day_dte_order"] == [4, 5, 6, 7, 3, 2]
    assert rules["agent_h"]["expiration_selection"]["evaluate_ascending_dte_inside_permitted_group"] is False
    assert rules["agent_h"]["expiration_selection"]["evaluate_same_day_dte_in_locked_order"] is True
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
    assert "2026-09-06.6" in prompt
    assert "2026-09-06.5" not in prompt
    assert "2026-09-06.4" not in prompt
    assert "2026-09-06.3" not in prompt
    assert "## Invariant registry" in prompt
    assert "git_unavailable_emergency_only" in prompt
    assert "## Continuity" in prompt
    assert "already_covered_monitor_only" in prompt
    assert "emergency_close_ref_id" in prompt
    assert "place nothing** even if Git later looks down" in prompt
    assert "If `required_cash` > buying power or the 2.5% debit cap fails: skip." in prompt
    assert "2026-09-06.2" not in prompt
    assert "2026-09-06.1" not in prompt
    assert "2026-09-05.6" not in prompt
    assert "2026-09-05.5" not in prompt
    assert "2026-09-05.4" not in prompt
    assert "2026-09-05.3" not in prompt
    assert "The lease is not acquired unless its commit successfully pushes to" in prompt
    assert "journal/h_lease.json` from `origin/main`, not merely the local checkout." in prompt
    assert "Never force-push or overwrite a conflicting lease." in prompt
    assert "A run that failed to acquire the lease must not clear or modify the lease." in prompt
    assert "Only the run whose `run_id` matches the remote lease may renew or release it." in prompt
    assert "renew the lease before it has fewer than" in prompt
    assert "git pull --ff-only origin main" in prompt
    assert "rebase that commit onto `origin/main`" in prompt
    assert "reacquire" in prompt
    assert "Never place based only on observing that no other" in prompt
    assert "A fast-forward pull that brought in another run’s lease is a **held** lease" in prompt or "if **another** unexpired `run_id` is there, that is a **held** lease" in prompt
    assert "**does not** block the retry" in prompt
    assert "re-read **only** `origin/main:journal/h_lease.json`" in prompt
    assert "without modifying `journal/h_lease.json`" in prompt
    assert "journal `lease_held_after_fill`" in prompt
    assert "must own a currently valid remotely verified lease" in prompt
    assert "A4.5 Account, recovery tools, files, then exposure" in prompt
    assert "It does **not** outrank the file gates above." in prompt
    assert "including leftover protection" in prompt
    assert "rules_prompt_mismatch" in prompt
    assert "unless at least **6 minutes** remain" in prompt
    assert "rounded **up** to the next valid broker tick" in prompt
    assert "core recovery tools" in prompt
    assert "Existing exposure may only be cancelled, protected, reduced, or closed" in prompt
    assert "stop all order activity, including exits" in prompt
    assert "Bullish call trigger: use the live underlying **ask**" in prompt
    assert "Bearish put trigger: use the live underlying **bid**" in prompt
    assert "Do **not** describe last or midpoint as executable" in prompt
    assert "**4 DTE, 5 DTE, 6 DTE, 7 DTE, 3 DTE, 2 DTE**" in prompt
    assert "evaluate **2–3 DTE only**" not in prompt
    assert "If last is inside the current bid/ask" not in prompt
    assert "time_in_force=gfd" in prompt
    assert "replacement_skipped_tick_cap" in prompt
    assert "the tick-floored minimum" in prompt
    assert "Round that trigger to a valid `min_ticks` increment toward the fill" in prompt
    assert "**Do not restore the protective stop** during forced liquidation." in prompt
    assert "**Take-profit only:**" in prompt
    assert "## Cursor/Grok concurrency rule" in prompt
    assert "**A. Clock.** Now in `America/New_York`. Clock only. **No RH calls.**" in prompt
    assert "Git on `origin/main` is the required concurrency" in prompt
    assert "acquire and remotely verify lease" in prompt
    assert "time_in_force=gtc" not in prompt
    assert "Do not attempt GTC unless an owner-approved schema change" in prompt
    assert "09:30–09:44:59" in prompt
    assert "approximately **13:10–15:45 ET**" in prompt
    assert "Call delta: **+0.40 through +0.50 inclusive**" in prompt
    assert "Put delta: **−0.50 through −0.40 inclusive**" in prompt
    assert "planned_loss` ≤ **0.49% of current NLV**" in prompt
    assert "bod_nlv_unavailable" in prompt
    assert "maximum concurrent runs = 1" not in prompt


def test_inverse_etf_denylist_has_no_duplicate_twm():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "equity_day_trade.py"
    assert src.read_text(encoding="utf-8").count('"TWM"') == 1
    assert "TWM" in INVERSE_ETF_SYMBOLS
