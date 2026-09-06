from decimal import Decimal

from pipeline.ticks import (
    EQUITY_TICK,
    as_price_str,
    entry_limit_from_mid,
    max_acceptable_debit_limit,
    one_tick_replacement,
    option_tick_size,
    parse_min_ticks,
    protective_stop_price,
    round_to_tick,
    stop_usable_versus_live_bid,
    take_profit_threshold,
)


RH_DOCUMENTED = {"cutoff_price": "3.00", "below_tick": "0.01", "above_tick": "0.05"}


def test_option_tick_size_requires_parsed_min_ticks():
    assert option_tick_size("2.99") is None
    assert option_tick_size("3.00") is None
    assert option_tick_size("4.13") is None
    assert option_tick_size("2.99", RH_DOCUMENTED) == Decimal("0.01")
    assert option_tick_size("3.00", RH_DOCUMENTED) == Decimal("0.05")
    assert option_tick_size("4.13", RH_DOCUMENTED) == Decimal("0.05")
    custom = {"cutoff_price": "1.00", "below_tick": "0.01", "above_tick": "0.05"}
    assert option_tick_size("0.90", custom) == Decimal("0.01")
    assert option_tick_size("1.00", custom) == Decimal("0.05")
    assert option_tick_size(None, RH_DOCUMENTED) is None
    # Missing cutoff is ambiguous — do not assume the typical $3.00 schedule.
    assert option_tick_size("1.10", {"below_tick": "0.01", "above_tick": "0.05"}) is None
    assert parse_min_ticks({"below_tick": "0.01", "above_tick": "0.05"}) is None


def test_option_tick_size_parses_schedule_without_inferring():
    schedule = [
        {"above_price": "0", "tick": "0.01"},
        {"above_price": "3.00", "tick": "0.05"},
    ]
    assert option_tick_size("2.99", schedule) == Decimal("0.01")
    assert option_tick_size("3.00", schedule) == Decimal("0.05")
    assert option_tick_size("1.00", {"increment": "0.01"}) == Decimal("0.01")
    assert option_tick_size("1.00", "0.05") == Decimal("0.05")
    # Conflicting extra fields make a scalar dict ambiguous.
    assert option_tick_size("1.00", {"tick": "0.01", "other": "x"}) is None


def test_one_tick_replacement_skips_when_plus_one_exceeds_cap_or_ask():
    assert one_tick_replacement("1.10", "1.15", "1.15", "0.01") == Decimal("1.11")
    assert one_tick_replacement("1.15", "1.20", "1.15", "0.01") is None
    assert one_tick_replacement("2.00", "2.00", "2.10", "0.01") is None
    assert one_tick_replacement("3.10", "3.20", "3.20", "0.05") == Decimal("3.15")
    assert one_tick_replacement("3.20", "3.20", "3.20", "0.05") is None


def test_max_acceptable_debit_is_independent_of_first_limit():
    assert max_acceptable_debit_limit("1.20", "1.50", "1.10", tick="0.01") == Decimal("1.10")
    assert max_acceptable_debit_limit(None, "1.10", tick="0.01") == Decimal("1.10")
    assert max_acceptable_debit_limit() is None
    assert max_acceptable_debit_limit("1.10") is None


def test_max_acceptable_debit_tick_floors_off_grid_nlv_or_fee_cap():
    assert max_acceptable_debit_limit("3.10", "3.02", min_ticks=RH_DOCUMENTED) == Decimal("3.00")
    assert max_acceptable_debit_limit("1.20", "1.114", min_ticks=RH_DOCUMENTED) == Decimal("1.11")
    assert max_acceptable_debit_limit("1.15", "1.20", min_ticks=RH_DOCUMENTED) == Decimal("1.15")
    custom = {"cutoff_price": "1.00", "below_tick": "0.01", "above_tick": "0.05"}
    assert max_acceptable_debit_limit("1.07", "1.20", min_ticks=custom) == Decimal("1.05")
    assert max_acceptable_debit_limit("0.004", min_ticks=RH_DOCUMENTED) is None


def test_entry_limit_half_tick_toward_bid_never_above_ask():
    assert entry_limit_from_mid("1.105", "1.20", "0.01") == Decimal("1.10")
    assert entry_limit_from_mid("1.104", "1.20", "0.01") == Decimal("1.10")
    assert entry_limit_from_mid("1.106", "1.20", "0.01") == Decimal("1.11")
    assert entry_limit_from_mid("1.19", "1.18", "0.01") == Decimal("1.18")


def test_protective_stop_rounds_toward_fill_never_widens():
    assert protective_stop_price("4.13", min_ticks=RH_DOCUMENTED) == Decimal("3.35")
    assert protective_stop_price("2.47", min_ticks=RH_DOCUMENTED) == Decimal("1.98")
    assert protective_stop_price("1.00", min_ticks=RH_DOCUMENTED) == Decimal("0.80")
    assert protective_stop_price("4.13") is None
    assert protective_stop_price("100", EQUITY_TICK, asset="equity") == Decimal("80.00")
    assert as_price_str(protective_stop_price("4.13", min_ticks=RH_DOCUMENTED)) == "3.35"


def test_stop_must_remain_below_live_option_bid():
    ok, reason = stop_usable_versus_live_bid("3.304", "3.35", "3.50")
    assert ok is True and reason is None
    stale_rounded, rounded_reason = stop_usable_versus_live_bid("3.304", "3.35", "3.35")
    assert stale_rounded is False and rounded_reason == "live_bid_at_or_below_rounded_stop"
    stale_raw, raw_reason = stop_usable_versus_live_bid("3.304", "3.35", "3.30")
    assert stale_raw is False and raw_reason == "live_bid_at_or_below_raw_stop"


def test_take_profit_threshold_rounds_up_to_next_tick():
    # $2.00 * 1.40 = $2.80, already on a penny tick.
    assert take_profit_threshold("2.00", min_ticks=RH_DOCUMENTED) == Decimal("2.80")
    # $2.47 * 1.40 = $3.458. Nickel at/above $3 → $3.50, not $3.45.
    assert take_profit_threshold("2.47", min_ticks=RH_DOCUMENTED) == Decimal("3.50")
    # Missing ticks: fail closed.
    assert take_profit_threshold("2.47") is None


def test_round_to_tick_modes():
    assert round_to_tick("3.304", "0.05", mode="nearest") == Decimal("3.30")
    assert round_to_tick("3.304", "0.05", mode="toward_fill") == Decimal("3.35")
    assert round_to_tick("3.304", "0.05", mode="toward_bid") == Decimal("3.30")
