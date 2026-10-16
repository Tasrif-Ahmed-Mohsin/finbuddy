"""Stress test and "what if": the year plan must hold up when reality differs from the plan."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.corridors.loader import load_corridor
from app.engines.stress import shift_estimated_holidays, stress_test, what_if
from app.engines.year_plan import Policy, load_calendar, simulate, spending_pace, topup_decision
from app.fx import FIXTURE
from app.main import create_app
from app.market import build_market, load_quote_config
from tests.test_year_plan import demo_situation

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}
CAL, COR, CFG = load_calendar(), load_corridor(), load_quote_config()
MARKET = build_market(FIXTURE, CFG)
POLICY = Policy.from_corridor(COR, D("6000"))  # ¥200 a day


# ---- the spending pace (shared by the year plan and the live autopilot) ---------------------------
def test_pace_is_the_plan_until_there_is_a_week_of_history():
    assert spending_pace(D("200"), [D("400")] * 6) == D("200")


def test_pace_follows_faster_spending_but_ignores_one_big_bill():
    assert spending_pace(D("200"), [D("260")] * 14) == D("260")
    assert spending_pace(D("200"), [D("200")] * 13 + [D("1500")]) == D("200")  # one deposit is not a new pace


def test_pace_never_drops_below_the_plan():
    assert spending_pace(D("200"), [D("120")] * 14) == D("200")


# ---- simulation hooks -----------------------------------------------------------------------
def test_hooks_that_match_the_plan_change_nothing():
    sit = demo_situation()
    plain = simulate("sathi", sit, POLICY, CAL, COR, MARKET)
    hooked = simulate("sathi", sit, POLICY, CAL, COR, MARKET, spend=lambda d: POLICY.daily_spend_cny,
                      delay=lambda: 0, reality=CAL)
    assert hooked.stuck == plain.stuck and hooked.transfers == plain.transfers


def test_moved_holidays_move_only_the_estimated_dates():
    later = shift_estimated_holidays(CAL, 2)
    pairs = list(zip(CAL.closures, later.closures))
    assert any(a.confidence == "assumption" for a, _ in pairs)
    for a, b in pairs:
        assert (b.start - a.start) == (timedelta(days=2) if a.confidence == "assumption" else timedelta(0))


def test_late_money_lands_late_but_the_planner_does_not_panic():
    sit = demo_situation()
    late = simulate("sathi", sit, POLICY, CAL, COR, MARKET, delay=lambda: 3)
    on_time = simulate("sathi", sit, POLICY, CAL, COR, MARKET)
    assert late.stuck == [] and len(late.transfers) <= len(on_time.transfers) + 1  # no double sending
    assert all(date.fromisoformat(t["lands"]) - date.fromisoformat(t["send_on"]) >= timedelta(days=10) for t in late.transfers)


# ---- stress test --------------------------------------------------------------------------------
def test_stress_test_is_reproducible_and_sathi_holds_up():
    a = stress_test(demo_situation(), POLICY, CAL, COR, MARKET, runs=40, seed=7)
    b = stress_test(demo_situation(), POLICY, CAL, COR, MARKET, runs=40, seed=7)
    assert a["stuck_days"] == b["stuck_days"]
    sathi, today = a["stuck_days"]["sathi"], a["stuck_days"]["today"]
    assert sathi["median"] <= 1 and sathi["mean"] * 5 < today["mean"] and sathi["worst"] < today["median"]
    assert today["zero_share_pct"] == 0  # today's way gets stuck in every messy year


def test_what_if_scenarios():
    rows = {r["key"]: r for r in what_if(demo_situation(), POLICY, CAL, COR, MARKET, lambda mid: build_market(mid, CFG))}
    assert set(rows) == {"taka_weakens_10", "spending_plus_30", "transfers_3_days_late", "holidays_2_days_later", "all_at_once"}
    assert all(r["stuck_days_sathi"] <= r["stuck_days_today"] for r in rows.values())
    assert rows["spending_plus_30"]["stuck_days_sathi"] == 0 and rows["spending_plus_30"]["stuck_days_today"] > 0
    base = D(rows["transfers_3_days_late"]["family_pays_bdt"])  # same money, only later: costs the same
    assert D(rows["transfers_3_days_late"]["change_bdt"]) == 0
    assert D("0.08") < D(rows["taka_weakens_10"]["change_bdt"]) / base < D("0.11")  # ≈ 10% more taka for the same yuan


# ---- API and the live autopilot ---------------------------------------------------------------
@pytest.fixture
def client():
    return TestClient(create_app(audit_path=None, llm=None))


def test_stress_endpoint(client):
    r = client.get("/plan/stress?runs=30", headers=H["parent"])
    assert r.status_code == 200
    body = r.json()
    assert body["runs"] == 30 and {"today", "sathi"} <= set(body["stuck_days"]) and len(body["what_if"]) == 6
    crisis = next(w for w in body["what_if"] if w["key"] == "dollar_crisis")  # Earn & Save: a 4-week dollar shortage
    assert crisis["weeks"] == 4 and crisis["stuck_days_today"] >= crisis["stuck_days_sathi"] and body["crisis"]["starts_tested"] > 20
    assert client.get("/plan/stress").status_code == 401
    events = [e for e in client.get("/audit", headers=H["parent"]).json()["entries"] if e["event"] == "stress_tested"]
    assert events and events[-1]["actor"] == "parent"


def test_live_runway_uses_the_real_spending_pace(client):
    plan_daily = D(client.get("/runway", headers=H["student"]).json()["daily_spend_cny"])
    client.app.state.svc.bank.spend_log = [plan_daily * D("1.3")] * 14  # two weeks of spending 30% faster
    assert D(client.get("/runway", headers=H["student"]).json()["daily_spend_cny"]) == (plan_daily * D("1.3")).quantize(D("0.01"))


def test_late_margin_only_adds_caution_and_only_near_chinese_closures():
    plain = Policy(POLICY.daily_spend_cny, POLICY.transfer_days, POLICY.safety_days, POLICY.target_days,
                   POLICY.min_transfer_cny, 0)
    extra = []
    for k in range(240):
        today = date(2026, 10, 12) + timedelta(days=k)
        for bal in (D("1800"), D("2400"), D("3000")):
            a, b = (topup_decision(today, bal, [], p, CAL) for p in (plain, POLICY))
            assert not (a and not b)  # the margin never makes Sathi wait where it would have sent
            if b and not a:
                extra.append(b)
    assert extra  # it does change some decisions…
    for dec in extra:  # …and only where a few days' delay would run into a Chinese closure
        late = dec.wait_would_land + timedelta(days=POLICY.late_margin_days)
        assert CAL.closures_in(dec.wait_would_land, late) or not CAL.is_open("CN", late)
