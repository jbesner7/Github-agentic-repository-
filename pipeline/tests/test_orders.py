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
    assert rules["options"]["may_hold_overnight_with_stop"] is True
    assert rules["options"]["flatten_at_close"] is False
    assert rules["options"]["overnight_lock_confirmed"] == "2026-08-31"
    assert rules["loop"]["flatten_equity_before_close"] is True
    assert rules["loop"]["options_may_hold_overnight_with_stop"] is True
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
    assert rules["agent_h"]["same_day_expiry_flatten_by"] == "15:30"
    assert rules["agent_h"]["max_new_entries_per_day"] == 2
    assert rules["agent_h"]["max_planned_loss_pct_of_current_nlv"] == 0.005
    assert rules["agent_h"]["max_debit_pct_of_current_nlv"] == 0.025
    assert rules["agent_h"]["max_daily_realized_loss_pct_of_session_start_nlv"] == 0.01
    assert rules["agent_h"]["option_quote"]["min_open_interest"] == 500
    assert rules["agent_h"]["option_quote"]["max_quote_age_seconds"] == 5
    assert rules["agent_h"]["intraday_timeframes"] == ["10minute", "hour", "day"]
    assert rules["agent_h"]["include_index_options"] is False
    assert rules["agent_h"]["overnight"]["dte_2_3_flatten_by"] == "15:45"
    assert rules["agent_h"]["overnight"]["dte_4_7_overnight_with_stop"] is True
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


def test_inverse_etf_denylist_has_no_duplicate_twm():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "equity_day_trade.py"
    assert src.read_text(encoding="utf-8").count('"TWM"') == 1
    assert "TWM" in INVERSE_ETF_SYMBOLS
