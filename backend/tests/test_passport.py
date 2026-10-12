"""Payment passport (credit building): real on-time records, privacy option, and tamper resistance."""
import copy

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

H = {"student": {"Authorization": "Bearer demo-student"}, "parent": {"Authorization": "Bearer demo-parent"},
     "agent": {"Authorization": "Bearer demo-agent"}}


def pay_tuition(c, amount="35200"):
    d = c.post("/drafts", json={"kind": "tt_tuition", "amount_cny": amount, "payee_id": "univ_demo", "memo": "Tuition"},
               headers=H["parent"]).json()
    for who in ("parent", "student"):
        c.post(f"/drafts/{d['id']}/approve", headers=H[who])
    assert c.post(f"/drafts/{d['id']}/execute", headers=H["parent"]).status_code == 200
    return d


@pytest.fixture
def client():
    return TestClient(create_app(audit_path=None, llm=None))


def test_on_time_tuition_appears_with_proof(client):
    pay_tuition(client)
    client.post("/sandbox/advance", json={"days": 7}, headers=H["parent"])
    p = client.post("/passport", json={"include_amounts": True}, headers=H["student"]).json()
    e = p["entries"][0]
    assert e["kind"] == "tuition" and e["on_time"] is True and e["arrived"] <= e["due"] == "2026-11-15"
    assert e["amount_cny"] == "35200.00" and p["stats"]["on_time_pct"] == 100 and "Not an official credit score" in p["disclaimer"]
    assert client.post("/passport/verify", json={"passport": p}).json()["valid"]


def test_late_payment_is_shown_as_late_not_hidden(client):
    client.post("/sandbox/advance", json={"days": 31}, headers=H["parent"])  # 12 Nov: too late to arrive by 15 Nov
    pay_tuition(client)
    client.post("/sandbox/advance", json={"days": 7}, headers=H["parent"])
    p = client.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    assert p["entries"][0]["on_time"] is False and p["stats"]["on_time_pct"] == 0


def test_hiding_amounts(client):
    pay_tuition(client)
    p = client.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    assert p["entries"][0]["amount_cny"] is None and p["stats"]["total_cny"] is None


def test_tampered_or_fabricated_passports_fail(client):
    pay_tuition(client)
    client.post("/sandbox/advance", json={"days": 7}, headers=H["parent"])
    p = client.post("/passport", json={"include_amounts": True}, headers=H["student"]).json()
    changed = copy.deepcopy(p)
    changed["entries"][0]["amount_cny"] = "1.00"
    assert not client.post("/passport/verify", json={"passport": changed}).json()["valid"]
    fake = copy.deepcopy(p)
    fake["entries"].append({**p["entries"][0], "audit_seq": 9999, "date": "2026-09-01"})
    r = client.post("/passport/verify", json={"passport": fake}).json()
    assert not r["valid"] and any("signature" in x for x in r["reasons"])


def test_revoked_and_expired_passports_fail(client):
    pay_tuition(client)
    p = client.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    client.post(f"/passport/{p['id']}/revoke", headers=H["student"])
    assert "revoked by the holder" in client.post("/passport/verify", json={"passport": p}).json()["reasons"]
    p2 = client.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    client.post("/sandbox/advance", json={"days": 91}, headers=H["parent"])
    assert "expired" in client.post("/passport/verify", json={"passport": p2}).json()["reasons"]


def test_public_qr_page_needs_the_verification_code(client):
    pay_tuition(client)
    client.post("/sandbox/advance", json={"days": 7}, headers=H["parent"])
    p = client.post("/passport", json={"include_amounts": False}, headers=H["parent"]).json()
    good = client.get(f"/passport/{p['id']}/verify?sig={p['signature'][:24]}")
    assert good.status_code == 200 and ">VALID<" in good.text and "on time" in good.text and "¥" not in good.text
    bad = client.get(f"/passport/{p['id']}/verify?sig=wrong")
    assert "NOT VALID" in bad.text and "Demo Student" not in bad.text  # no personal data without the code


def test_only_users_can_issue_or_revoke(client):
    assert client.post("/passport", json={"include_amounts": True}, headers=H["agent"]).status_code == 403
    p = client.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    assert client.post(f"/passport/{p['id']}/revoke", headers=H["agent"]).status_code == 403


def test_renewal_done_before_expiry_counts_as_on_time(client):
    case = client.post("/renewals/endorsement_expiry", headers=H["student"]).json()
    client.post(f"/renewals/case/{case['id']}/complete", json={"new_expiry": "2027-07-31"}, headers=H["parent"])
    p = client.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    r = next(x for x in p["entries"] if x["kind"] == "renewal")
    assert r["on_time"] is True and p["stats"]["renewals"] == 1


def test_issued_passport_has_a_scannable_qr_and_still_verifies(client):
    pay_tuition(client)
    p = client.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    assert p["qr_svg"].startswith("<svg") and p["verify_url"].endswith(p["signature"][:24])
    assert client.post("/passport/verify", json={"passport": p}).json()["valid"]  # display keys are not signed


def test_passport_ignores_earlier_sessions_in_a_persistent_log(tmp_path):
    log = tmp_path / "audit.jsonl"
    first = TestClient(create_app(audit_path=log, llm=None))
    pay_tuition(first)  # session 1: one payment (its draft id is draft-0001)
    second = TestClient(create_app(audit_path=log, llm=None))  # restart: ids start again at draft-0001
    pay_tuition(second)
    p = second.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    assert p["stats"]["payments"] == 1  # only this session's payment
    assert second.post("/passport/verify", json={"passport": p}).json()["valid"]
