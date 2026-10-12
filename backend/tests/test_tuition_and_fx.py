from datetime import date
from decimal import Decimal as D

import numpy as np

from app.corridors.loader import load_corridor
from app.engines.fx_range import RateRange, coverage_backtest, rate_range
from app.engines.tuition_planner import TuitionRequest, plan_tuition
from app.market import load_market

CORRIDOR = load_corridor()
MARKET = load_market()


def test_send_by_date_works_back_from_arrival_deadline():
    p = plan_tuition(TuitionRequest(D("35200"), date(2026, 11, 15), date(2026, 10, 12)), CORRIDOR, MARKET)
    # 7 transfer days + 3 buffer days
    assert p["send_by"] == "2026-11-05"
    assert p["status"] == "on_track"
    totals = [D(o["total_bdt"]) for o in p["options"]]
    assert totals == sorted(totals)
    assert p["best_quote_id"] == p["options"][0]["quote_id"]
    assert D(p["savings_best_vs_worst_bdt"]) >= 0


def test_too_late_to_arrive_is_flagged():
    p = plan_tuition(TuitionRequest(D("35200"), date(2026, 11, 15), date(2026, 11, 10)), CORRIDOR, MARKET)
    assert p["status"] == "at_risk_late"


def test_wait_risk_brackets_pay_now():
    fx = RateRange(horizon_days=24, spot=17.7, low=17.2, mid=17.7, high=18.3, level=0.8, n_samples=500)
    p = plan_tuition(TuitionRequest(D("35200"), date(2026, 11, 15), date(2026, 10, 12)), CORRIDOR, MARKET, fx)
    w = p["wait_risk"]
    assert D(w["if_wait_low_bdt"]) < D(w["pay_now_bdt"]) < D(w["if_wait_high_bdt"])


def synthetic_random_walk(n=2000, vol=0.003, seed=42):
    """Synthetic data for testing the method only (NOT market data)."""
    rng = np.random.default_rng(seed)
    return 17.7 * np.exp(np.cumsum(rng.normal(0, vol, n)))


def test_rate_range_is_ordered_around_spot():
    rates = synthetic_random_walk()
    rr = rate_range(rates, h=10, level=0.8)
    assert rr.low < rr.spot < rr.high
    assert rr.low < rr.mid < rr.high


def test_coverage_backtest_is_close_to_nominal_on_a_random_walk():
    rates = synthetic_random_walk()
    bt = coverage_backtest(rates, h=10, level=0.8, window=500, step=5)
    assert 0.70 <= bt["empirical_coverage"] <= 0.90
