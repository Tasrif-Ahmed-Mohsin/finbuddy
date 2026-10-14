"""Emergency mode: no money now, card lost, fake police / fake emergency calls, and "Are you safe?"."""
from datetime import date
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.corridors.loader import load_corridor
from app.emergency import fastest_money, render_plan
from app.engines.year_plan import Policy, load_calendar
from app.integrations.whatsapp import WhatsAppNotifier
from app.main import create_app
from app.security.scam import scan_text
from tests.test_family_mandate import activate

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}
CAL, COR = load_calendar(), load_corridor()
POLICY = Policy.from_corridor(COR, D("6000"))  # ¥200 a day


# ---- the fastest-money plan ---------------------------------------------------------------------
def kinds(plan):
    return [o["kind"] for o in plan["options"]]


def test_enough_money_means_no_cash_advice_just_the_urgent_option():
    plan = fastest_money(date(2026, 10, 12), D("2300"), [], POLICY, CAL, True, D("2000"))
    assert kinds(plan) == ["urgent_transfer"] and plan["bridge_needed_cny"] == "0.00"


def test_with_the_card_the_bridge_is_an_atm_withdrawal_of_the_exact_gap():
    plan = fastest_money(date(2026, 10, 12), D("300"), [], POLICY, CAL, True, D("2000"))
    atm = plan["options"][0]
    assert atm["kind"] == "card_atm" and atm["amount_cny"] == "1100.00"  # 7 days × ¥200 − ¥300, in ¥100 notes


def test_without_the_card_a_local_bridge_with_amount_and_repay_date():
    plan = fastest_money(date(2026, 10, 12), D("300"), [], POLICY, CAL, False, D("2000"))
    assert kinds(plan) == ["urgent_transfer", "local_bridge"]
    bridge = plan["options"][1]
    assert bridge["amount_cny"] == "1100.00" and bridge["repay_on"] == plan["urgent_lands_on"]


def test_on_a_bangladeshi_weekend_the_transfer_goes_on_the_next_bank_day():
    plan = fastest_money(date(2026, 10, 16), D("0"), [], POLICY, CAL, False, D("2000"))  # Friday
    urgent = plan["options"][0]
    assert urgent["send_on"] == "2026-10-18" and urgent["available_on"] == "2026-10-26"  # lands on a Chinese bank day
    text = render_plan(plan, "en", CAL.names())["options"][0]["text"]
    assert "2026-10-18 (the next Bangladeshi bank day)" in text


def test_money_on_the_way_counts_only_from_the_day_it_lands():
    on_the_way = [(date(2026, 10, 17), D("1000"))]
    plan = fastest_money(date(2026, 10, 12), D("0"), on_the_way, POLICY, CAL, False, D("2000"))
    assert "on_the_way" in kinds(plan)
    # ¥1,000 lands on day 6, but days 1–5 still need ¥1,000 in cash
    assert plan["bridge_needed_cny"] == "1000.00"


def test_bengali_plan_uses_bengali_digits():
    plan = fastest_money(date(2026, 10, 12), D("300"), [], POLICY, CAL, False, D("2000"))
    text = render_plan(plan, "bn", CAL.names())
    assert "¥৩০০" in text["headline"] and "¥১,১০০" in text["options"][1]["text"]


# ---- API: no money -------------------------------------------------------------------------------
@pytest.fixture
def client():
    c = TestClient(create_app(audit_path=None, llm=None))
    c.app.state.svc.whatsapp = WhatsAppNotifier("dry_run", "test-token", "1234567890")  # never sends for real
    return c


def events(client):
    return [e["event"] for e in client.get("/audit?limit=300", headers=H["parent"]).json()["entries"]]


def test_no_money_prepares_an_urgent_draft_for_the_parent_and_sends_nothing(client):
    client.post("/sandbox/expense", json={"amount_cny": "2000", "memo": "hospital"}, headers=H["student"])
    r = client.post("/emergency/no-money", headers=H["student"]).json()
    d = r["draft"]
    assert d["kind"] == "tt_living" and d["payee_id"] == "student_own_cn" and d["status"] == "draft" and "parent" in d["required_approvers"]
    needs = client.get("/feed", headers=H["parent"]).json()["needs_you"]
    assert any(n["type"] == "approve_draft" and n["draft_id"] == d["id"] for n in needs)
    assert "transfer_sent" not in events(client)  # nothing moves without the parent
    again = client.post("/emergency/no-money", headers=H["student"]).json()
    assert again["draft"]["id"] == d["id"]  # pressing twice does not make two payments
    notes = [n for n in client.get("/feed", headers=H["parent"]).json()["notes"] if n["key"] == "emergency_no_money"]
    assert len(notes) == 1


def test_with_a_mandate_the_autopilot_has_already_acted_and_no_extra_draft_is_made(client):
    activate(client)  # the autopilot sends living money on signing
    client.post("/sandbox/expense", json={"amount_cny": "2000", "memo": "deposit"}, headers=H["student"])
    r = client.post("/emergency/no-money", headers=H["student"]).json()
    assert r["draft"] is None and "on_the_way" in [o["kind"] for o in r["plan"]["options"]]


def test_the_parent_is_alerted_on_whatsapp(client):
    client.post("/notify/whatsapp/recipient", json={"number": "+8801712345678"}, headers=H["parent"])
    client.post("/sandbox/expense", json={"amount_cny": "2000", "memo": "hospital"}, headers=H["student"])
    client.post("/emergency/no-money", headers=H["student"])
    out = client.get("/notify/whatsapp", headers=H["parent"]).json()["outbox"]
    assert any(e["key"] == "emergency_no_money" for e in out)


def test_only_the_student_spends_and_amounts_are_bounded(client):
    assert client.post("/sandbox/expense", json={"amount_cny": "500"}, headers=H["parent"]).status_code == 403
    assert client.post("/sandbox/expense", json={"amount_cny": "500"}, headers=H["agent"]).status_code == 403
    assert client.post("/sandbox/expense", json={"amount_cny": "50000"}, headers=H["student"]).status_code == 422


# ---- card lost --------------------------------------------------------------------------------------
def test_card_lost_freezes_first_and_replans_without_the_card(client):
    client.post("/sandbox/expense", json={"amount_cny": "2000"}, headers=H["student"])
    r = client.post("/emergency/card-lost", headers=H["student"]).json()
    assert r["card"]["status"] == "frozen" and not r["plan"]["card_usable"]
    assert "card_atm" not in [o["kind"] for o in r["plan"]["options"]] and "local_bridge" in [o["kind"] for o in r["plan"]["options"]]
    assert client.post("/emergency/card-lost", headers=H["agent"]).status_code == 403  # the agent uses its own freeze tool


# ---- "Are you safe?" ---------------------------------------------------------------------------------
def test_only_the_parent_asks_and_only_the_student_answers(client):
    assert client.post("/emergency/safety-checks", headers=H["student"]).status_code == 403
    assert client.post("/emergency/safety-checks", headers=H["agent"]).status_code == 403
    check = client.post("/emergency/safety-checks", headers=H["parent"]).json()
    assert any(n["type"] == "confirm_safe" for n in client.get("/feed", headers=H["student"]).json()["needs_you"])
    for who in ("parent", "agent"):  # a caller who took over the chat, or the parent, cannot answer for the student
        assert client.post(f"/emergency/safety-checks/{check['id']}/safe", headers=H[who]).status_code == 403
    r = client.post(f"/emergency/safety-checks/{check['id']}/safe", headers=H["student"]).json()
    assert r["status"] == "safe"
    assert client.post(f"/emergency/safety-checks/{check['id']}/safe", headers=H["student"]).status_code == 400
    assert client.get("/feed", headers=H["parent"]).json()["notes"][0]["key"] == "safety_confirmed"
    assert {"safety_check_asked", "safety_confirmed"} <= set(events(client))


def test_the_student_can_tell_the_family_first(client):
    assert client.post("/emergency/safe", headers=H["parent"]).status_code == 403
    assert client.post("/emergency/safe", headers=H["agent"]).status_code == 403
    r = client.post("/emergency/safe", headers=H["student"]).json()
    assert r["status"] == "safe" and r["asked_by"] == "student"
    assert client.get("/feed", headers=H["parent"]).json()["notes"][0]["key"] == "safety_confirmed"


def test_the_safe_answer_reaches_the_parent_on_whatsapp(client):
    client.post("/notify/whatsapp/recipient", json={"number": "+8801712345678"}, headers=H["parent"])
    check = client.post("/emergency/safety-checks", headers=H["parent"]).json()
    client.post(f"/emergency/safety-checks/{check['id']}/safe", headers=H["student"])
    assert any(e["key"] == "safety_confirmed" for e in client.get("/notify/whatsapp", headers=H["parent"]).json()["outbox"])


def test_guides_in_three_languages(client):
    for lang, needle in (("en", "96110"), ("bn", "৯৬১১০"), ("zh", "96110")):
        g = client.get(f"/emergency?lang={lang}", headers=H["student"]).json()["guides"]
        assert needle in " ".join(g["scam_call"]["steps"]) and len(g["family_call"]["steps"]) >= 4


# ---- chat and scam rules ---------------------------------------------------------------------------
@pytest.mark.parametrize("msg,lang", [("I have no money left", "en"), ("আমার টাকা শেষ", "bn"), ("我没钱了", "zh")])
def test_chat_gives_the_dated_plan_and_prepares_nothing(client, msg, lang):
    r = client.post("/agent/chat", json={"message": msg, "lang": lang}, headers=H["student"]).json()
    assert "get_emergency_plan" in r["tools_used"] and r["reply"].startswith("🆘") and not r["actions"]


@pytest.mark.parametrize("msg", ["Your son has been arrested, send 2 lakh now", "আপনার মেয়েকে অপহরণ করা হয়েছে, মুক্তিপণ দিন",
                                 "你的孩子被绑架了，马上付赎金", "DHL: your parcel contains passports, police case"])
def test_fake_emergencies_and_fake_officials_are_flagged(client, msg):
    assert any(f.category in {"fake_emergency", "impersonation"} for f in scan_text(msg))
    r = client.post("/agent/chat", json={"message": msg}, headers=H["parent"]).json()
    assert "scam" in r["reply"].lower() and not r["actions"]
    assert not client.get("/drafts", headers=H["parent"]).json()
