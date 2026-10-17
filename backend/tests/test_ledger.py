"""Double-entry books and exactly-once payments."""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.sandbox.ledger import Ledger, UnbalancedEntry

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(audit_path=None, llm=None))


def pay_living(client: TestClient, amount: str = "1500", key: str | None = None) -> dict:
    d = client.post("/drafts", json={"kind": "tt_living", "amount_cny": amount, "payee_id": "student_own_cn"},
                    headers=H["student"]).json()
    client.post(f"/drafts/{d['id']}/approve", headers=H["parent"])
    headers = {**H["parent"], **({"Idempotency-Key": key} if key else {})}
    return {"draft": d, "response": client.post(f"/drafts/{d['id']}/execute", headers=headers)}


def test_an_unbalanced_entry_is_refused():
    books = Ledger()
    with pytest.raises(UnbalancedEntry):
        books.post("t", "oops", None, [("a", "CNY", Decimal("10")), ("b", "CNY", Decimal("-9.99"))])
    with pytest.raises(UnbalancedEntry):  # balanced in total but not per currency
        books.post("t", "oops", None, [("a", "CNY", Decimal("10")), ("b", "BDT", Decimal("-10"))])
    assert books.entries == []


def test_books_stay_balanced_and_reconciled_through_a_whole_term(client: TestClient):
    pay_living(client)
    client.post("/sandbox/advance", json={"days": 40}, headers=H["parent"])  # arrival, daily spending, autopilot
    view = client.get("/ledger", headers=H["student"]).json()
    books = view["books"]
    assert books["ok"] and books["balanced"] and books["reconciled"], books
    assert set(books["trial_balance"].values()) == {"0", "0.00"} or all(Decimal(v) == 0 for v in books["trial_balance"].values())
    assert view["payments_booked"] >= 1 and books["booked_twice"] == []
    assert all(a["books"] == a["shown"] for a in view["accounts"])
    sent = next(e for e in view["entries"] if e["event"] == "payment_sent")
    for cur in ("BDT", "CNY"):  # every leg of a cross-currency payment balances in its own currency
        assert sum(Decimal(p["amount"]) for p in sent["postings"] if p["currency"] == cur) == 0


def test_a_balance_changed_behind_the_books_is_caught(client: TestClient):
    s = client.app.state.svc
    s.bank.accounts["student_cn"].balance += Decimal("1000")  # money appears without an entry
    books = client.get("/ledger", headers=H["student"]).json()["books"]
    assert not books["ok"] and books["mismatches"][0]["account"] == "student_cn"


def test_a_retried_send_with_the_same_key_pays_once(client: TestClient):
    first = pay_living(client, key="tap-8f2c1d9e")
    assert first["response"].status_code == 200
    did = first["draft"]["id"]
    again = client.post(f"/drafts/{did}/execute", headers={**H["parent"], "Idempotency-Key": "tap-8f2c1d9e"})
    assert again.status_code == 200 and again.json() == first["response"].json()  # the first answer, nothing new
    view = client.get("/ledger", headers=H["parent"]).json()
    assert view["payments_booked"] == 1 and view["idempotent_replays"] == 1
    # without the key, a second execute is refused (the draft is already executed)
    assert client.post(f"/drafts/{did}/execute", headers=H["parent"]).status_code == 400


def test_the_same_key_for_a_different_request_is_refused(client: TestClient):
    body = {"kind": "tt_living", "amount_cny": "1500", "payee_id": "student_own_cn"}
    h = {**H["student"], "Idempotency-Key": "draft-key-001"}
    one = client.post("/drafts", json=body, headers=h)
    two = client.post("/drafts", json=body, headers=h)
    assert one.json()["id"] == two.json()["id"]  # a retried tap does not make a second draft
    other = client.post("/drafts", json={**body, "amount_cny": "9000"}, headers=h)
    assert other.status_code == 422


def test_the_bank_never_books_one_draft_twice(client: TestClient):
    s = client.app.state.svc
    paid = pay_living(client)
    did = paid["draft"]["id"]
    with pytest.raises(ValueError, match="never books one payment twice"):
        s.bank.execute_tt(did, "parent_bd", "student_own_cn", Decimal("1500"), Decimal("30000"), "parent", "EXECUTE", "living")


def test_the_parent_does_not_see_the_students_own_pay_in_the_books(client: TestClient):
    client.post("/save/income", json={"kind": "campus_job", "amount_cny": "800", "employer": "Campus library"},
                headers=H["student"])
    s = client.app.state.svc
    s.bank.credit_income("src-1", "campus_job", Decimal("800"), "student")
    parent = client.get("/ledger", headers=H["parent"]).json()
    student = client.get("/ledger", headers=H["student"]).json()
    assert not any(e["event"] == "income_received" for e in parent["entries"])
    assert any(e["event"] == "income_received" for e in student["entries"])
    assert "student_shield" not in {a["id"] for a in parent["accounts"]}
