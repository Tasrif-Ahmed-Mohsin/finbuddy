"""Year plan ("never stuck"): bank calendar, the look-ahead top-up rule, the year simulation, cost truth."""
from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.corridors.loader import load_corridor
from app.engines.cost_truth import field_payment_truth
from app.engines.year_plan import Policy, Situation, load_calendar, plan_year, project, topup_decision
from app.fx import load_history
from app.main import create_app
from app.market import build_market, load_quote_config
from app.fx import FIXTURE

H = {"student": {"Authorization": "Bearer demo-student"}, "parent": {"Authorization": "Bearer demo-parent"},
     "agent": {"Authorization": "Bearer demo-agent"}}
CAL = load_calendar()
COR = load_corridor()
MARKET = build_market(FIXTURE, load_quote_config())
POLICY = Policy.from_corridor(COR, D("6000"))  # ¥200 a day


def test_bank_calendar_knows_both_weekends_and_festivals():
    assert not CAL.is_open("BD", date(2026, 10, 16)) and CAL.is_open("CN", date(2026, 10, 16))  # Friday
    assert CAL.is_open("BD", date(2026, 10, 18)) and not CAL.is_open("CN", date(2026, 10, 18))  # Sunday
    assert CAL.closed_because("BD", date(2027, 3, 10)) == "Eid-ul-Fitr"
    assert CAL.closed_because("CN", date(2027, 2, 8)) == "Spring Festival (Chinese New Year)"
    # sent 1 Feb: +7 days falls in Spring Festival, so it lands on the first Chinese bank day after it
    assert CAL.arrival(date(2027, 2, 1), 7) == date(2027, 2, 15)
    assert all(c.confidence in {"official", "secondary", "assumption"} for c in CAL.closures)


def test_no_transfer_when_waiting_is_safe():
    assert topup_decision(date(2026, 10, 12), D("6000"), [], POLICY, CAL) is None  # 30 days of money


def test_nothing_is_sent_on_a_bangladeshi_bank_holiday():
    assert topup_decision(date(2027, 3, 9), D("0"), [], POLICY, CAL) is None  # Eid: branches closed


def test_sends_before_eid_and_says_why():
    # 5 Mar 2027 is a Friday; Sun 7 Mar is the last bank day before the Eid closure (8–13 Mar).
    bal = D("2600")  # 13 days of money
    dec = topup_decision(date(2027, 3, 7), bal, [], POLICY, CAL)
    assert dec is not None and dec.closures == ["Eid-ul-Fitr"] and dec.wait_would_land == date(2027, 3, 22)
    assert dec.lands == date(2027, 3, 15)
    # sized so that after landing the student has target + safety days of money
    at_landing = project(bal, [], date(2027, 3, 7), date(2027, 3, 14), POLICY.daily_spend_cny)
    assert at_landing + dec.amount_cny >= POLICY.daily_spend_cny * (POLICY.target_days + POLICY.safety_days)
    assert dec.amount_cny % 100 == 0 and dec.bridge_cny == 0


def test_bridge_cash_when_money_runs_out_before_any_transfer_can_land():
    dec = topup_decision(date(2026, 10, 12), D("500"), [], POLICY, CAL)  # runs out on day 3, transfer lands day 7
    assert dec is not None and dec.bridge_cny == D("900")


def demo_situation(**kw):
    base = dict(start=date(2026, 10, 12), end=date(2027, 6, 29), balance_cny=D("2300"), in_transit=[],
                card_valid_until=date(2026, 12, 31), card_active=True, student_file_valid_until=date(2027, 9, 15))
    return Situation(**{**base, **kw})


def test_year_today_gets_stuck_after_the_card_stops_sathi_never_does():
    plan = plan_year(demo_situation(), POLICY, CAL, COR, MARKET)
    today, sathi = plan["strategies"]["today"], plan["strategies"]["sathi"]
    assert sathi["stuck_days"] == 0 and today["stuck_days"] > 0
    first = today["stuck_periods"][0]
    assert first["from"] > "2026-12-31" and "endorsement" in first["reasons"][0]  # the friend's #1 pain
    assert any("Eid" in " ".join(p["reasons"]) for p in today["stuck_periods"])
    assert all(t["send_on"] <= t["lands"] for t in sathi["transfers"])
    assert len(sathi["atm"]) == 0  # no ATM needed: transfers land in time
    # fees, not the exchange rate, are most of what families lose today
    assert D(plan["headline"]["fees_share_today_pct"]) > 50
    assert D(plan["headline"]["saved_bdt"]) > 0 and D(plan["headline"]["overhead_sathi_pct"]) < D(plan["headline"]["overhead_today_pct"])


def test_year_plan_respects_bangladeshs_monthly_living_limit():
    plan = plan_year(demo_situation(balance_cny=D("0")), POLICY, CAL, COR, MARKET)
    cap_cny = COR.v("bd_living_remit_cap_usd_per_month") * MARKET.mid.cny_per_usd
    per_month: dict[str, D] = {}
    for t in plan["strategies"]["sathi"]["transfers"]:
        per_month[t["send_on"][:7]] = per_month.get(t["send_on"][:7], D(0)) + D(t["amount_cny"])
    assert all(v <= cap_cny for v in per_month.values())


def test_a_renewed_endorsement_removes_the_stuck_days_it_caused():
    plan = plan_year(demo_situation(card_valid_until=date(2027, 7, 31)), POLICY, CAL, COR, MARKET)
    assert plan["strategies"]["today"]["stuck_days"] == 0


def test_cost_truth_from_the_real_payment():
    fp = load_quote_config()["field_payments"][0]
    t = field_payment_truth(fp, load_history())
    assert t["paid_bdt"] == "653920.00"  # 35,200 x 18.35 + 8,000
    assert D("0") < D(t["rate_markup_pct"]) < D("1")  # the bank's rate was close to the market
    assert D(t["fee_vs_rate"]) > 5  # the fixed charge cost over five times the rate markup


@pytest.fixture
def client():
    return TestClient(create_app(audit_path=None, llm=None))


def test_year_plan_api(client):
    yp = client.get("/plan/year", headers=H["agent"]).json()  # READ level: the agent may look
    assert yp["headline"]["stuck_days_sathi"] == 0 and yp["headline"]["stuck_days_today"] > 0
    assert yp["cost_truth"][0]["fee_bdt"] == "8000.00"
    assert {a["confidence"] for a in yp["assumptions"]} <= {"official", "secondary", "field", "assumption"}
    assert any(e["type"] == "card_stops" for e in yp["events"]) and any(e["type"] == "bank_closure" for e in yp["events"])
    assert "year_planned" in {e["event"] for e in client.get("/audit", headers=H["parent"]).json()["entries"]}


def test_sandbox_transfers_follow_both_bank_calendars(client):
    client.post("/sandbox/advance", json={"days": 4}, headers=H["parent"])  # Fri 16 Oct: Bangladeshi branches closed
    d = client.post("/drafts", json={"kind": "tt_living", "amount_cny": "3000", "payee_id": "student_own_cn"},
                    headers=H["agent"]).json()
    client.post(f"/drafts/{d['id']}/approve", headers=H["parent"])
    sent = client.post(f"/drafts/{d['id']}/execute", headers=H["parent"]).json()["bank_event"]["data"]
    assert sent["leaves_on"] == "2026-10-18" and sent["arrives_at"].startswith("2026-10-26")  # Sun → +7 = Sun → Mon


def test_sandbox_student_spends_and_gets_stuck_without_a_plan(client):
    r = client.post("/sandbox/advance", json={"days": 20}, headers=H["parent"]).json()
    assert r["stuck_days"] > 0  # ¥2,300 lasts ~11 days at ¥200/day
    notes = client.get("/feed", headers=H["parent"]).json()["notes"]
    assert any(n["key"] == "stuck" for n in notes) and any(n["key"] == "runway_low" for n in notes)
