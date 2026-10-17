"""Passkey approvals: a person's device signs the exact payment, and the server checks that signature first.

Every device here is a SimulatedAuthenticator with a fresh random key: there is no fixed key anywhere.
"""
from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.passkey import SimulatedAuthenticator

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}


@pytest.fixture
def client() -> TestClient:
    app = create_app(audit_path=None, llm=None)
    s = app.state.svc
    s.settings = dataclasses.replace(s.settings, passkey_required=True)
    return TestClient(app)


def enrol(client: TestClient, who: str) -> SimulatedAuthenticator:
    dev = SimulatedAuthenticator(who)
    r = client.post("/auth/passkey/register", json=dev.registration(), headers=H[who])
    assert r.status_code == 200, r.text
    return dev


def living_draft(client: TestClient, amount: str = "1500") -> dict:
    r = client.post("/drafts", json={"kind": "tt_living", "amount_cny": amount, "payee_id": "student_own_cn"},
                    headers=H["student"])
    assert r.status_code == 200, r.text
    return r.json()


def test_no_fixed_demo_keys_and_registration_is_logged(client: TestClient):
    r = client.get("/auth/passkey/credentials", headers=H["parent"])
    assert r.json() == {"required": True, "credentials": []}  # nothing pre-registered: keys come from devices
    dev = enrol(client, "parent")
    creds = client.get("/auth/passkey/credentials", headers=H["parent"]).json()["credentials"]
    assert [c["credential_id"] for c in creds] == [dev.credential_id]
    assert creds[0]["thumbprint"].startswith("key_") and creds[0]["kind"] == "simulated"
    events = [e["event"] for e in client.get("/audit?limit=5", headers=H["parent"]).json()["entries"]]
    assert "passkey_registered" in events
    # the agent can neither register nor list passkeys
    assert client.post("/auth/passkey/register", json=SimulatedAuthenticator("parent").registration(),
                       headers=H["agent"]).status_code == 403


def test_plain_approve_is_refused_when_passkeys_are_required(client: TestClient):
    d = living_draft(client)
    r = client.post(f"/drafts/{d['id']}/approve", headers=H["parent"])
    assert r.status_code == 403 and "passkey" in r.json()["detail"]
    assert client.get(f"/drafts/{d['id']}", headers=H["parent"]).json()["approved_by"] == []


def test_signed_approval_then_execution(client: TestClient):
    dev = enrol(client, "parent")
    d = living_draft(client)
    r = client.post(f"/drafts/{d['id']}/passkey-approve", json=dev.sign(d["draft_hash"]), headers=H["parent"])
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["status"] == "approved" and view["approved_by"] == ["parent"]
    assert view["passkey_approvals"][0]["thumbprint"].startswith("key_")
    assert view["passkey_approvals"][0]["biometric_uv"] is True
    r = client.post(f"/drafts/{d['id']}/execute", headers=H["parent"])
    assert r.status_code == 200 and r.json()["draft"]["status"] == "executed"
    receipt = client.get("/receipts", headers=H["parent"]).json()[0]
    assert receipt["authority"]["passkey_signed"] is True


@pytest.mark.parametrize("attack, expect", [
    ("other_payment", "different payment"),
    ("no_uv", "fingerprint, face or PIN"),
    ("bad_origin", "does not trust"),
    ("forged", "does not verify"),
])
def test_bad_signatures_are_refused(client: TestClient, attack: str, expect: str):
    dev = enrol(client, "parent")
    d = living_draft(client)
    if attack == "other_payment":
        a = dev.sign(d["draft_hash"], challenge_hex="ab" * 32)
    elif attack == "no_uv":
        a = dev.sign(d["draft_hash"], user_verified=False)
    elif attack == "bad_origin":
        a = dev.sign(d["draft_hash"], origin="https://sathi-login.example")
    else:  # someone else's key, presented under the parent's credential id
        a = {**SimulatedAuthenticator("parent").sign(d["draft_hash"]), "credential_id": dev.credential_id}
    r = client.post(f"/drafts/{d['id']}/passkey-approve", json=a, headers=H["parent"])
    assert r.status_code == 403 and expect in r.json()["detail"]
    assert client.get(f"/drafts/{d['id']}", headers=H["parent"]).json()["approved_by"] == []
    events = [e["event"] for e in client.get("/audit?limit=3", headers=H["parent"]).json()["entries"]]
    assert "passkey_verification_failed" in events


def test_a_changed_draft_invalidates_the_signature(client: TestClient):
    """Sign ¥1,500, then the amount changes under the hood: the signature no longer matches the draft."""
    dev = enrol(client, "parent")
    d = living_draft(client)
    a = dev.sign(d["draft_hash"])
    client.app.state.svc.drafts[d["id"]].amount_cny += 1000
    r = client.post(f"/drafts/{d['id']}/passkey-approve", json=a, headers=H["parent"])
    assert r.status_code == 403 and "different payment" in r.json()["detail"]


def test_replayed_signature_and_wrong_person(client: TestClient):
    parent, student = enrol(client, "parent"), enrol(client, "student")
    d = living_draft(client)
    a = parent.sign(d["draft_hash"])
    assert client.post(f"/drafts/{d['id']}/passkey-approve", json=a, headers=H["parent"]).status_code == 200
    r = client.post(f"/drafts/{d['id']}/passkey-approve", json=a, headers=H["parent"])
    assert r.status_code == 403 and "already used" in r.json()["detail"]
    # the student presenting the parent's passkey: not registered to the student
    d2 = living_draft(client, "1200")
    r = client.post(f"/drafts/{d2['id']}/passkey-approve", json=parent.sign(d2["draft_hash"]), headers=H["student"])
    assert r.status_code == 403 and "registered for the student" in r.json()["detail"]
    assert student.credential_id != parent.credential_id


def test_two_person_rule_needs_both_passkeys(client: TestClient):
    parent, student = enrol(client, "parent"), enrol(client, "student")
    r = client.post("/drafts", json={"kind": "tt_tuition", "amount_cny": "35200", "payee_id": "univ_demo"},
                    headers=H["parent"])
    d = r.json()
    assert set(d["required_approvers"]) == {"parent", "student"}
    r = client.post(f"/drafts/{d['id']}/passkey-approve", json=parent.sign(d["draft_hash"]), headers=H["parent"])
    assert r.json()["status"] == "draft"  # one of two
    assert client.post(f"/drafts/{d['id']}/execute", headers=H["parent"]).status_code == 403
    r = client.post(f"/drafts/{d['id']}/passkey-approve", json=student.sign(d["draft_hash"]), headers=H["student"])
    assert r.json()["status"] == "approved"
    assert {p["actor"] for p in r.json()["passkey_approvals"]} == {"parent", "student"}


def test_agent_cannot_passkey_approve(client: TestClient):
    dev = enrol(client, "parent")
    d = living_draft(client)
    r = client.post(f"/drafts/{d['id']}/passkey-approve", json=dev.sign(d["draft_hash"]), headers=H["agent"])
    assert r.status_code == 403


def test_mandate_signature_needs_a_passkey_over_the_proposal(client: TestClient):
    parent = enrol(client, "parent")
    p = client.post("/mandates/proposals", json={"text": "প্রতি মাসে ৫০ হাজার টাকা", "lang": "bn"}, headers=H["parent"]).json()
    assert p["required_signers"] == ["parent"]
    r = client.post(f"/mandates/proposals/{p['id']}/sign", json={"proposal_hash": p["hash"]}, headers=H["parent"])
    assert r.status_code == 403 and "passkey" in r.json()["detail"]
    r = client.post(f"/mandates/proposals/{p['id']}/sign",
                    json={"proposal_hash": p["hash"], "assertion": parent.sign(p["hash"])}, headers=H["parent"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active"


def test_passkeys_survive_a_sandbox_reset(client: TestClient):
    dev = enrol(client, "parent")
    client.post("/sandbox/reset", headers=H["parent"])
    creds = client.get("/auth/passkey/credentials", headers=H["parent"]).json()["credentials"]
    assert [c["credential_id"] for c in creds] == [dev.credential_id]
