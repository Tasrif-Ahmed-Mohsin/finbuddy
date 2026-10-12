"""Real exchange rates (provider, ranges, quotes) and card controls (freeze / unfreeze / report lost)."""
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.fx import FxPoint, FxProvider, load_history
from app.main import create_app
from app.market import build_market, load_quote_config
from app.security.permissions import Actor
from tests.fake_llm import FakeLLM, completion, tool_call

H = {"student": {"Authorization": "Bearer demo-student"}, "parent": {"Authorization": "Bearer demo-parent"},
     "agent": {"Authorization": "Bearer demo-agent"}}
ATM_SMS = "Dear Customer, your Card ending 4821 was used for ATM withdrawal of CNY 2,000.00 at ICBC SHANGHAI. Fee BDT 345.00."


@pytest.fixture
def client():
    return TestClient(create_app(audit_path=None, llm=None))


# ---- exchange rates ---------------------------------------------------------------
def test_saved_history_is_real_and_long_enough():
    hist = load_history()
    assert len(hist) > 900 and hist[0].date == "2024-03-02"
    assert all(100 < p.bdt_per_usd < 140 and 6 < p.cny_per_usd < 8 for p in hist)


def test_offline_mode_uses_the_last_saved_day():
    fx = FxProvider(mode="offline")
    mid = fx.latest()
    assert mid.as_of == fx.history[-1].date and not mid.sample and "offline" in mid.source


def test_live_mode_falls_back_when_the_network_fails(monkeypatch):
    import urllib.request

    def boom(*a, **k):
        raise OSError("no network")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    fx = FxProvider(mode="live", history=[FxPoint("2026-10-01", 123.0, 6.7)])
    mid = fx.latest()
    assert mid.as_of == "2026-10-01" and fx.last_error == "OSError"


def test_bank_quotes_are_markups_on_the_real_mid_rate():
    fx = FxProvider(mode="offline")
    m = build_market(fx.latest(), load_quote_config())
    for q in m.quotes:
        assert q.sample and q.bdt_per_cny > m.mid.bdt_per_cny  # every estimate costs more than mid-market


def test_ranges_on_real_history_and_backtest_honesty():
    fx = FxProvider(mode="offline")
    rr = fx.range(14)
    assert rr.low < rr.spot < rr.high
    bt = fx.backtest(7)
    assert bt["tests"] > 500 and 0.7 <= bt["empirical_coverage"] <= 0.95  # an 80% range should be right ~80% of the time


def test_tuition_plan_now_includes_wait_risk(client):
    p = client.post("/plan/tuition", json={"amount_cny": "35200", "deadline": "2026-11-15"}, headers=H["parent"]).json()
    w = p["wait_risk"]
    assert w is not None and D(w["if_wait_low_bdt"]) < D(w["pay_now_bdt"]) < D(w["if_wait_high_bdt"])
    assert w["backtest"]["empirical_coverage"] > 0 and p["data_quality"]["bank_quotes"] == "estimated"


def test_fx_overview_and_history(client):
    o = client.get("/fx").json()
    assert o["history_days"] > 900 and o["horizons"]["7"]["backtest"]["tests"] > 500
    h = client.get("/fx/history?days=365").json()
    assert 2 < len(h) <= 181 and h[-1]["date"] == load_history()[-1].date


def test_real_quote_can_be_entered_and_wins_if_cheaper(client):
    mid = D(client.get("/market").json()["mid"]["bdt_per_cny"])
    r = client.post("/market/quotes", json={"bank": "My Bank (real)", "bdt_per_cny": str(round(mid * D("1.004"), 4)),
                                            "fixed_fee_bdt": "500"}, headers=H["parent"])
    assert r.status_code == 200
    plan = client.post("/plan/tuition", json={"amount_cny": "35200", "deadline": "2026-11-15"}, headers=H["parent"]).json()
    assert plan["best_quote_id"] == r.json()["quote_id"] and plan["data_quality"]["bank_quotes"] == "mixed"
    bad = client.post("/market/quotes", json={"bank": "Typo", "bdt_per_cny": "1.84", "fixed_fee_bdt": "0"}, headers=H["parent"])
    assert bad.status_code == 400  # an obviously wrong rate is rejected
    assert client.post("/market/quotes", json={"bank": "Agent Bank", "bdt_per_cny": str(mid), "fixed_fee_bdt": "0"},
                       headers=H["agent"]).status_code == 403


# ---- card controls --------------------------------------------------------------------
def test_agent_can_freeze_but_never_unfreeze(client):
    assert client.post("/cards/4821/freeze", json={"reason": "suspicious"}, headers=H["agent"]).json()["status"] == "frozen"
    assert client.post("/cards/4821/unfreeze", headers=H["agent"]).status_code == 403
    assert client.post("/cards/4821/unfreeze", headers=H["student"]).json()["status"] == "active"
    events = [e["event"] for e in client.get("/audit", headers=H["student"]).json()["entries"]]
    assert {"card_frozen", "card_active", "permission_denied"} <= set(events)


def test_frozen_card_blocks_atm_withdrawals(client):
    client.post("/cards/4821/freeze", headers=H["student"])
    r = client.post("/drafts", json={"kind": "atm_plan", "amount_cny": "1000", "withdrawals": ["1000"]}, headers=H["student"]).json()
    assert r["status"] == "blocked" and "card_active" in {c["id"] for c in r["checks"] if not c["passed"]}


def test_frozen_card_also_blocks_execution_if_frozen_after_approval(client):
    d = client.post("/drafts", json={"kind": "atm_plan", "amount_cny": "1000", "withdrawals": ["1000"]}, headers=H["student"]).json()
    client.post(f"/drafts/{d['id']}/approve", headers=H["student"])
    client.post("/cards/4821/freeze", headers=H["parent"])
    r = client.post(f"/drafts/{d['id']}/execute", headers=H["student"])
    assert r.status_code == 403 and "card_active" in r.json()["detail"]


def test_charge_on_a_frozen_card_raises_top_alert(client):
    client.post("/cards/4821/freeze", headers=H["student"])
    client.post("/inbox/messages", json={"sender": "BD Bank Alert", "text": ATM_SMS}, headers=H["student"])
    ins = client.get("/insights", headers=H["student"]).json()["insights"]
    assert ins[0]["type"] == "card_used_while_blocked" and ins[0]["action"]["op"] == "report_lost"


def test_large_debit_alert_offers_one_tap_freeze(client):
    client.post("/inbox/demo/seed", headers=H["student"])
    large = next(i for i in client.get("/insights", headers=H["student"]).json()["insights"] if i["type"] == "large_debit")
    assert large["action"] == {"screen": "card", "op": "freeze", "last4": "4821"}


def test_report_lost_is_final(client):
    r = client.post("/cards/4821/report-lost", headers=H["parent"]).json()
    assert r["status"] == "lost" and r["replacement_last4"]
    assert client.post("/cards/4821/unfreeze", headers=H["parent"]).status_code == 400
    assert client.post("/cards/4821/report-lost", headers=H["agent"]).status_code == 403


def test_offline_agent_freezes_on_lost_card_in_bengali():
    c = TestClient(create_app(audit_path=None, llm=None))
    r = c.post("/agent/chat", json={"message": "আমার কার্ড হারিয়ে গেছে!", "lang": "bn"}, headers=H["student"]).json()
    assert "freeze_card" in r["tools_used"] and r["actions"][0]["status"] == "frozen" and "🔒" in r["reply"]
    # "how do I unfreeze?" must NOT freeze again or do anything else risky
    r2 = c.post("/agent/chat", json={"message": "how do I unfreeze my card?"}, headers=H["student"]).json()
    assert "freeze_card" not in r2["tools_used"]


def test_llm_agent_freeze_tool_exists_but_no_unfreeze_tool():
    fake = FakeLLM([completion(tool_calls=[tool_call("freeze_card", {"reason": "user says card stolen"})]),
                    completion("Frozen. Call your bank.")])
    c = TestClient(create_app(audit_path=None, llm=fake.client()))
    r = c.post("/agent/chat", json={"message": "my card was stolen"}, headers=H["student"]).json()
    assert r["actions"] == [{"type": "card", "last4": "4821", "status": "frozen"}]
    names = {t["function"]["name"] for t in fake.requests[0]["tools"]}
    assert "freeze_card" in names and not ({"unfreeze_card", "report_card_lost"} & names)
    svc = c.app.state.svc
    with pytest.raises(PermissionError):
        svc.unfreeze_card(Actor.AGENT, "4821")
