"""Open-banking connections with consent (read-only), and the privacy page's rights (PIPL)."""
from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.passkey import SimulatedAuthenticator
from tests.fake_llm import FakeLLM, completion

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(audit_path=None, llm=None))


def connect(client: TestClient, who: str, connector: str, perms=("ReadAccountsBasic", "ReadBalances"), days=90) -> dict:
    c = client.post("/banks/consents", json={"connector": connector, "permissions": list(perms), "days": days},
                    headers=H[who])
    assert c.status_code == 200, c.text
    a = client.post(f"/banks/consents/{c.json()['id']}/authorise", json={}, headers=H[who])
    assert a.status_code == 200, a.text
    return a.json()


def test_no_reading_without_consent_and_only_the_holder_can_allow(client: TestClient):
    assert client.get("/banks/brac_bd/accounts", headers=H["agent"]).status_code == 403
    # the student cannot connect the parent's bank, the agent cannot connect any
    assert client.post("/banks/consents", json={"connector": "brac_bd"}, headers=H["student"]).status_code == 403
    assert client.post("/banks/consents", json={"connector": "brac_bd"}, headers=H["agent"]).status_code == 403
    assert client.post("/banks/consents", json={"connector": "brac_bd", "days": 365}, headers=H["parent"]).status_code == 422


def test_consent_allows_reading_balances_then_revoke_stops_it(client: TestClient):
    c = connect(client, "parent", "brac_bd")
    assert c["status"] == "Authorised" and c["days_left"] == 90 and c["can_move_money"] is False
    data = client.get("/banks/brac_bd/accounts", headers=H["agent"]).json()  # Sathi reads through the consent
    acct = data["Data"]["Account"][0]
    assert data["consent_id"] == c["id"] and acct["Balance"]["Amount"]["Currency"] == "BDT"
    assert "Transactions" not in acct  # not allowed by this consent
    assert client.get("/banks/brac_bd/accounts", headers=H["student"]).status_code == 403  # not the student's bank
    r = client.delete(f"/banks/consents/{c['id']}", headers=H["parent"])
    assert r.json()["status"] == "Revoked"
    assert client.get("/banks/brac_bd/accounts", headers=H["agent"]).status_code == 403
    events = [e["event"] for e in client.get("/audit?limit=10", headers=H["parent"]).json()["entries"]]
    assert {"bank_consent_authorised", "bank_data_read", "bank_consent_revoked", "bank_read_denied"} <= set(events)


def test_a_consent_expires_after_its_days(client: TestClient):
    connect(client, "student", "boc_cn", ("ReadAccountsBasic", "ReadBalances", "ReadTransactionsBasic"), days=10)
    assert "Transactions" in client.get("/banks/boc_cn/accounts", headers=H["agent"]).json()["Data"]["Account"][0]
    client.post("/sandbox/advance", json={"days": 11}, headers=H["parent"])
    assert client.get("/banks/boc_cn/accounts", headers=H["agent"]).status_code == 403
    assert client.get("/banks", headers=H["student"]).json()["consents"][0]["status"] == "Expired"


def test_with_passkeys_required_the_holder_signs_the_consent():
    app = create_app(audit_path=None, llm=None)
    s = app.state.svc
    s.settings = dataclasses.replace(s.settings, passkey_required=True)
    client = TestClient(app)
    dev = SimulatedAuthenticator("parent")
    client.post("/auth/passkey/register", json=dev.registration(), headers=H["parent"])
    c = client.post("/banks/consents", json={"connector": "brac_bd"}, headers=H["parent"]).json()
    assert client.post(f"/banks/consents/{c['id']}/authorise", json={}, headers=H["parent"]).status_code == 403
    r = client.post(f"/banks/consents/{c['id']}/authorise", json={"assertion": dev.sign(c["hash"])}, headers=H["parent"])
    assert r.status_code == 200 and r.json()["status"] == "Authorised"


def test_privacy_page_names_deepseek_in_china_and_hides_nothing(client: TestClient):
    p = client.get("/privacy", headers=H["parent"]).json()
    assert any("China" in r["name"] and r["law"].startswith("PIPL") for r in p["recipients"])
    ids = {h["id"] for h in p["held"]}
    assert {"messages", "passkeys", "bank_connections", "audit_log"} <= ids and "earnings" not in ids  # the parent
    assert "earnings" in {h["id"] for h in client.get("/privacy", headers=H["student"]).json()["held"]}
    assert client.get("/privacy", headers=H["agent"]).status_code == 403


def test_export_and_delete_my_messages(client: TestClient):
    client.post("/inbox/demo/seed", headers=H["parent"])
    export = client.get("/privacy/export", headers=H["parent"]).json()
    assert export["messages"] and export["person"] == "parent"
    r = client.post("/privacy/delete", json={"categories": ["messages"]}, headers=H["parent"]).json()
    assert r["deleted"]["messages"] > 0
    assert client.get("/privacy/export", headers=H["parent"]).json()["messages"] == []
    # the safety check keeps the amounts but no text
    status = client.get("/security/taint/status", headers=H["parent"]).json()
    assert status["untrusted_entities"] > 0
    assert client.post("/privacy/delete", json={"categories": ["earnings"]}, headers=H["parent"]).status_code == 403
    assert client.post("/privacy/delete", json={"categories": ["audit_log"]}, headers=H["parent"]).status_code == 400


def test_switching_the_ai_off_means_nothing_goes_to_deepseek():
    llm = FakeLLM([completion("hello from the model")] * 3)
    client = TestClient(create_app(audit_path=None, llm=llm.client()))
    r = client.post("/agent/chat", json={"message": "how much money is left?", "lang": "en"}, headers=H["parent"]).json()
    assert r["mode"] == "llm"
    calls = len(llm.requests)
    assert client.post("/privacy/ai", json={"allowed": False}, headers=H["parent"]).json() == {"ai": False}
    r = client.post("/agent/chat", json={"message": "how much money is left?", "lang": "en"}, headers=H["parent"]).json()
    assert r["mode"] == "fallback" and len(llm.requests) == calls  # the rules answered; the model was not called
    assert client.get("/privacy", headers=H["parent"]).json()["switches"]["ai"] is False
