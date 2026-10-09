"""
test_classify_guards.py

Unit tests for TASK_040 — scorer guards for unknown year, implausible price and
listings with no detected fault.

Run from backend/ directory:
    python -m pytest ../tests/unit/test_classify_guards.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.models.enums import OpportunityClass
from app.services.opportunity_scorer import (
    calculate_true_profit,
    classify_opportunity,
    classify_opportunity_with_reason,
)


def _strong_case(**overrides):
    kwargs = dict(
        true_margin_pct=45.0,
        true_profit_pence=300000,
        market_value_confidence="high",
        has_unpriced_faults=False,
        write_off_category="clean",
        vagueness_signals=[],
        listing_price_pence=310000,
        market_value_pence=720000,
        comp_count=21,
        year=2015,
        fault_count=2,
    )
    kwargs.update(overrides)
    return kwargs


def test_normal_case_is_still_strong():
    assert classify_opportunity(**_strong_case()) == OpportunityClass.STRONG


def test_year_unknown_is_excluded():
    cls, reason = classify_opportunity_with_reason(**_strong_case(year=0))
    assert cls == OpportunityClass.EXCLUDE
    assert reason == "year_unknown"


def test_value_over_ten_times_price_is_excluded():
    cls, reason = classify_opportunity_with_reason(
        **_strong_case(listing_price_pence=60000, market_value_pence=660000)
    )
    assert cls == OpportunityClass.EXCLUDE
    assert reason == "price_implausible"


def test_golf_r_wing_from_prod_is_excluded():
    """Prod row 8ba365ca: £150 wing, £6,499 value, year 0, no faults, 97.7% margin."""
    cls, _ = classify_opportunity_with_reason(**_strong_case(
        true_margin_pct=97.69, true_profit_pence=634900,
        listing_price_pence=15000, market_value_pence=649900, year=0, fault_count=0,
    ))
    assert cls == OpportunityClass.EXCLUDE


def test_no_faults_with_strong_profit_is_worth_checking_not_strong():
    cls, reason = classify_opportunity_with_reason(**_strong_case(fault_count=0))
    assert cls == OpportunityClass.SPECULATIVE
    assert reason is None


def test_no_faults_with_weak_profit_is_excluded():
    cls, reason = classify_opportunity_with_reason(**_strong_case(fault_count=0, true_margin_pct=25.0))
    assert cls == OpportunityClass.EXCLUDE
    assert reason == "no_faults_detected"


def test_no_faults_with_low_confidence_is_excluded():
    cls, reason = classify_opportunity_with_reason(
        **_strong_case(fault_count=0, market_value_confidence="low")
    )
    assert cls == OpportunityClass.EXCLUDE
    assert reason == "no_faults_detected"


def test_writeoff_still_excluded_first():
    cls, reason = classify_opportunity_with_reason(**_strong_case(write_off_category="cat_s", year=0))
    assert cls == OpportunityClass.EXCLUDE
    assert reason == "writeoff:cat_s"


def test_fix_cost_makes_the_card_add_up():
    """market − price − (parts mid + effort) == true profit, for the API's fix_cost_pence."""
    cases = [
        (720000, 310000, 100000, 150000, 2.0, 15000),
        (290000, 65000, 30000, 54000, 1.0, 15000),
        (495000, 220000, 80000, 100001, 1.5, 15000),
    ]
    for market, price, pmin, pmax, days, rate in cases:
        r = calculate_true_profit(market, price, pmin, pmax, days, rate)
        fix = r["parts_cost_mid_pence"] + r["effort_cost_pence"]
        assert market - price - fix == r["true_profit_pence"]
