from decimal import Decimal as D

import pytest

from app.corridors.loader import load_corridor
from app.engines.living_planner import LivingRequest, plan_living
from app.market import load_market

CORRIDOR = load_corridor()
MARKET = load_market()


@pytest.mark.parametrize("need", ["500", "2000", "6000", "12000", "25000"])
@pytest.mark.parametrize("bridge", ["0", "1000"])
@pytest.mark.parametrize("reserved", [0, 10, 25])
def test_best_plan_never_breaks_a_cap(need, bridge, reserved):
    plan = plan_living(LivingRequest(D(need), D(bridge), reserved_card_tx=reserved), CORRIDOR, MARKET)
    if plan.best is None:
        return  # infeasible is allowed; breaking a cap is not
    b = plan.best
    assert b.feasible
    u = b.cap_usage
    assert u["card_tx_after"] <= u["card_tx_cap"]
    assert D(u["card_bdt_after"]) <= D(u["card_bdt_cap"])
    assert D(u["living_remit_usd_after"]) <= D(u["living_remit_usd_cap"])
    assert b.tt_cny + sum(b.withdrawals, D(0)) >= D(need)  # the student gets at least what they need


def test_transfer_to_own_account_beats_many_atm_withdrawals():
    plan = plan_living(LivingRequest(D("6000")), CORRIDOR, MARKET)
    assert plan.best is not None
    assert plan.best.tt_cny > 0
    assert plan.savings_vs_baseline_bdt > 0


def test_bridge_money_must_come_from_atm():
    plan = plan_living(LivingRequest(D("6000"), bridge_cny=D("1500")), CORRIDOR, MARKET)
    assert sum(plan.best.withdrawals, D(0)) >= D("1500")


def test_withdrawals_are_whole_100_yuan_notes():
    plan = plan_living(LivingRequest(D("6050"), bridge_cny=D("1050")), CORRIDOR, MARKET)
    assert all(w % 100 == 0 for w in plan.best.withdrawals)


def test_no_chinese_account_means_atm_only():
    plan = plan_living(LivingRequest(D("4000"), has_cn_account=False), CORRIDOR, MARKET)
    assert plan.best.tt_cny == 0
    assert plan.best.withdrawals


def test_exhausted_transaction_cap_with_bridge_is_infeasible_and_explained():
    plan = plan_living(LivingRequest(D("3000"), bridge_cny=D("500"), card_tx_used=30), CORRIDOR, MARKET)
    assert plan.best is None
    assert any(v.startswith("tx_cap") for v in plan.baseline_all_atm.violations)


def test_too_much_for_all_caps_is_infeasible():
    # living-remittance cap (USD 2,000) + monthly ATM cap (USD 1,500) cannot cover 25,000 CNY
    plan = plan_living(LivingRequest(D("25000")), CORRIDOR, MARKET)
    assert plan.best is None
