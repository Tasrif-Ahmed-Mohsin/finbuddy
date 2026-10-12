from decimal import Decimal as D

from app.corridors.loader import load_corridor
from app.engines.cost import alipay_card_cost, atm_cost, tt_cost
from app.market import BankQuote
from app.money import q2


def quote(rate: str, fee: str) -> BankQuote:
    return BankQuote("t", "Test Bank", D(rate), D(fee), "2026-10-12", "test", True)


def test_tt_cost_lines_sum_to_total_and_overhead_is_markup_plus_fee():
    c = tt_cost(D("35200"), quote("18.00", "1000"), D("17.70"))
    assert sum(line.bdt for line in c.lines) == c.total_bdt
    assert c.total_bdt == D("35200") * D("18.00") + D("1000")
    assert c.overhead_bdt == q2(D("35200") * D("0.30") + D("1000"))


def test_intermediary_fee_means_sending_more():
    c = tt_cost(D("1000"), quote("18", "0"), D("17.7"), intermediary_fee_cny=D("100"))
    assert c.total_bdt == D("1100") * D("18")
    assert c.mid_value_bdt == D("1000") * D("17.7")
    assert sum(line.bdt for line in c.lines) == c.total_bdt


def test_atm_cost_counts_fixed_fees_per_withdrawal():
    corridor = load_corridor()
    c = atm_cost([D("2000"), D("2000")], corridor, D("17.70"))
    assert c.card_transactions == 2
    assert sum(line.bdt for line in c.lines) == c.total_bdt
    bd_fee_line = next(l for l in c.lines if l.label.startswith("Bangladeshi bank ATM fees"))
    assert bd_fee_line.bdt == 2 * corridor.v("bd_card_atm_fixed_fee_bdt")
    assert c.overhead_bdt > 0


def test_alipay_fee_only_on_payments_above_threshold():
    corridor = load_corridor()
    c = alipay_card_cost([D("150"), D("300")], corridor, D("17.70"))
    fee_line = next(l for l in c.lines if l.label.startswith("Alipay foreign-card fee"))
    # only the 300 CNY payment is above 200 -> 3% of 300 = 9 CNY, charged at the card rate
    assert fee_line.bdt > 0
    assert fee_line.bdt < D("9") * D("20")
    assert c.card_transactions == 2
