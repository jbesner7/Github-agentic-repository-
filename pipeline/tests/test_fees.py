from pipeline.fees import classify_review_fees, fee_aware_planned_loss_ok


NLV = 1500.0
CEILING_049 = 0.0049 * NLV  # 7.35
CEILING_050 = 0.005 * NLV  # 7.50


def test_positive_total_fee_is_used_alone():
    out = classify_review_fees({"total_fee": "0.65", "commission": "0.65", "sec_fee": "0.02"})
    assert out["fee_status"] == "quoted"
    assert out["entry_fee"] == 0.65
    assert out["journal"] == "total_fee"
    assert out["estimated_round_trip_fees"] == out["entry_fee"] * 3
    assert out["apply_049_ceiling"] is True


def test_zero_total_plus_positive_component_is_fee_conflict():
    out = classify_review_fees({"total_fee": "$0.00", "commission": "0.65"})
    assert out["fee_status"] == "ambiguous"
    assert out["entry_fee"] is None
    assert out["journal"] == "fee_conflict"
    assert out["estimated_exit_fee"] is None
    assert out["estimated_round_trip_fees"] is None
    assert out["apply_049_ceiling"] is True
    assert fee_aware_planned_loss_ok(
        planned_loss=CEILING_049, current_nlv=NLV, classification=out
    )
    assert not fee_aware_planned_loss_ok(
        planned_loss=7.40, current_nlv=NLV, classification=out
    )


def test_zero_total_and_zero_or_absent_components_is_explicit_zero():
    accepted = classify_review_fees({"total_fee": 0, "commission": "0.00"})
    assert accepted["fee_status"] == "explicit_zero"
    assert accepted["entry_fee"] == 0.0
    assert accepted["journal"] == "fee_explicit_zero"
    assert accepted["apply_049_ceiling"] is True

    absent = classify_review_fees({"total_fee": "0.00"})
    assert absent["fee_status"] == "explicit_zero"
    assert absent["entry_fee"] == 0.0
    assert fee_aware_planned_loss_ok(
        planned_loss=CEILING_049, current_nlv=NLV, classification=absent
    )
    assert not fee_aware_planned_loss_ok(
        planned_loss=7.40, current_nlv=NLV, classification=absent
    )


def test_missing_total_sums_non_overlapping_components():
    out = classify_review_fees({"commission": "0.65", "sec_fee": "0.02", "taf_fee": "0.01"})
    assert out["fee_status"] == "quoted"
    assert out["entry_fee"] == 0.68
    assert out["journal"].startswith("components:")
    assert out["apply_049_ceiling"] is True


def test_both_fee_ceilings_apply_on_every_trade():
    out = classify_review_fees({"total_fee": 0.03})
    # 7.40 exceeds 0.49% of $1,500 even though 7.40 + 3*0.03 still fits 0.50%.
    assert out["fee_status"] == "quoted"
    assert out["apply_049_ceiling"] is True
    assert 7.40 > CEILING_049
    assert 7.40 + 0.09 <= CEILING_050
    assert not fee_aware_planned_loss_ok(
        planned_loss=7.40, current_nlv=NLV, classification=out
    )
    assert fee_aware_planned_loss_ok(
        planned_loss=CEILING_049, current_nlv=NLV, classification=out
    )
    expensive = classify_review_fees({"total_fee": 1.00})
    assert not fee_aware_planned_loss_ok(
        planned_loss=CEILING_049, current_nlv=NLV, classification=expensive
    )
    assert fee_aware_planned_loss_ok(
        planned_loss=4.50, current_nlv=NLV, classification=expensive
    )


def test_nested_zero_total_with_positive_component_is_conflict():
    out = classify_review_fees({"fees": {"total_fee": 0, "contract_fee": 0.12}})
    assert out["journal"] == "fee_conflict"
    assert out["entry_fee"] is None


def test_subtotal_plus_parts_is_unavailable():
    out = classify_review_fees({"estimated_fee": "0.70", "commission": "0.65"})
    assert out["fee_status"] == "unavailable"
    assert out["journal"] == "fee_unavailable"
    assert out["apply_049_ceiling"] is True
