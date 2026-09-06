from decimal import Decimal

from pipeline.ticks import (
    EQUITY_TICK,
    as_price_str,
    entry_limit_from_mid,
    max_acceptable_debit_limit,
    one_tick_replacement,
    option_tick_size,
    protective_stop_price,
    round_to_tick,
)


def test_option_tick_size_typical_and_min_ticks():
    assert option_tick_size("2.99") == Decimal("0.01")
    assert option_tick_size("3.00") == Decimal("0.05")
    assert option_tick_size("4.13") == Decimal("0.05")
    custom = {"cutoff_price": "1.00", "below_tick": "0.01", "above_tick": "0.05"}
    assert option_tick_size("0.90", custom) == Decimal("0.01")
    assert option_tick_size("1.00", custom) == Decimal("0.05")
    assert option_tick_size(None) is None


def test_one_tick_replacement_skips_when_plus_one_exceeds_cap_or_ask():
    # Mid entry at 1.10, max/ask 1.15: +1 penny is legal.
    assert one_tick_replacement("1.10", "1.15", "1.15", "0.01") == Decimal("1.11")
    # First ticket already at max: +1 tick is impossible.
    assert one_tick_replacement("1.15", "1.20", "1.15", "0.01") is None
    # First ticket already at live ask: +1 tick exceeds ask.
    assert one_tick_replacement("2.00", "2.00", "2.10", "0.01") is None
    # Nickel option above $3.
    assert one_tick_replacement("3.10", "3.20", "3.20", "0.05") == Decimal("3.15")
    assert one_tick_replacement("3.20", "3.20", "3.20", "0.05") is None


def test_max_acceptable_debit_is_independent_of_first_limit():
    assert max_acceptable_debit_limit("1.20", "1.50", "1.10") == Decimal("1.10")
    assert max_acceptable_debit_limit(None, "1.10") == Decimal("1.10")
    assert max_acceptable_debit_limit() is None


def test_entry_limit_half_tick_toward_bid_never_above_ask():
    assert entry_limit_from_mid("1.105", "1.20", "0.01") == Decimal("1.10")
    assert entry_limit_from_mid("1.104", "1.20", "0.01") == Decimal("1.10")
    assert entry_limit_from_mid("1.106", "1.20", "0.01") == Decimal("1.11")
    assert entry_limit_from_mid("1.19", "1.18", "0.01") == Decimal("1.18")


def test_protective_stop_rounds_toward_fill_never_widens():
    # $4.13 fill * 0.80 = $3.304. Nickel tick. Toward fill = $3.35, not $3.30.
    assert protective_stop_price("4.13") == Decimal("3.35")
    # $2.47 fill * 0.80 = $1.976. Penny tick. Toward fill = $1.98.
    assert protective_stop_price("2.47") == Decimal("1.98")
    # Already on a tick: keep it.
    assert protective_stop_price("1.00") == Decimal("0.80")
    # Equity $0.01.
    assert protective_stop_price("100", EQUITY_TICK, asset="equity") == Decimal("80.00")
    assert as_price_str(protective_stop_price("4.13")) == "3.35"


def test_round_to_tick_modes():
    assert round_to_tick("3.304", "0.05", mode="nearest") == Decimal("3.30")
    assert round_to_tick("3.304", "0.05", mode="toward_fill") == Decimal("3.35")
    assert round_to_tick("3.304", "0.05", mode="toward_bid") == Decimal("3.30")
