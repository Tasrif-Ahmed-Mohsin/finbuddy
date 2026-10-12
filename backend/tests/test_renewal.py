"""Renewal assistant (T3): backward planning, drafted messages, step tracking, permissions, agent."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.corridors.loader import load_corridor
from app.main import create_app
from app.renewal import plan_renewal
from tests.fake_llm import FakeLLM, completion, tool_call

H = {"student": {"Authorization": "Bearer demo-student"}, "parent": {"Authorization": "Bearer demo-parent"},
     "agent": {"Authorization": "Bearer demo-agent"}}
PROFILE = {"student_name": "Demo Student", "university": "Demo University", "home_bank": "your bank"}


def test_plan_works_backwards_from_expiry():
    c = plan_renewal("r-1", "endorsement_expiry", date(2026, 12, 31), date(2026, 10, 12), load_corridor(), PROFILE)
    due = {s.id: s.due for s in c.steps}
    # buffer 5 + bank processing 3 → bank visit 23 Dec; scans 2 days before; university 7 days before that
    assert due["bank_visit"] == date(2026, 12, 23)
    assert due["send_to_parent"] == date(2026, 12, 21)
    assert due["request_docs"] == date(2026, 12, 14)
    assert due["confirm_new_expiry"] == date(2026, 12, 26)
    assert not c.late and [s.owner for s in c.steps] == ["student", "student", "student", "parent", "parent"]
    assert sorted(due.values()) == [due[k] for k in ("request_docs", "collect_docs", "send_to_parent", "bank_visit", "confirm_new_expiry")]


def test_late_plan_compresses_to_today_and_says_so():
    c = plan_renewal("r-2", "endorsement_expiry", date(2026, 12, 31), date(2026, 12, 20), load_corridor(), PROFILE)
    assert c.late and all(s.due >= date(2026, 12, 20) for s in c.steps)
    assert "express" in c.steps[0].detail


def test_messages_are_bilingual_and_contain_the_deadlines():
    c = plan_renewal("r-3", "endorsement_expiry", date(2026, 12, 31), date(2026, 10, 12), load_corridor(), PROFILE)
    email, parent = c.messages["university_email"], c.messages["parent_message"]
    assert "在读证明" in email["zh"] and "成绩单" in email["zh"] and "缴费通知单" in email["zh"]
    assert "Enrolment certificate" in email["en"] and "2026-12-20" in email["en"]  # collect-docs deadline
    assert "2026-12-23" in parent["bn"] and "এনরোলমেন্ট" in parent["bn"]  # bank visit deadline, documents in Bengali
    assert "your bank" not in parent["bn"] and "আপনার ব্যাংক" in parent["bn"]  # no English words in the Bengali text
    assert "not only a few months" in parent["en"]  # ask for a longer endorsement (the friend's #1 pain)


@pytest.fixture
def client():
    return TestClient(create_app(audit_path=None, llm=None))


def test_full_renewal_flow_through_the_api(client):
    c = client.post("/renewals/endorsement_expiry", headers=H["student"]).json()
    assert c["status"] == "open" and c["next_step"] == "request_docs"
    assert client.post("/renewals/endorsement_expiry", headers=H["parent"]).json()["id"] == c["id"]  # idempotent
    r = client.post(f"/renewals/case/{c['id']}/steps/request_docs", json={"status": "done"}, headers=H["student"]).json()
    assert r["next_step"] == "collect_docs"
    done = client.post(f"/renewals/case/{c['id']}/complete", json={"new_expiry": "2027-07-31"}, headers=H["parent"]).json()
    assert done["status"] == "completed"
    assert client.get("/profile", headers=H["parent"]).json()["endorsement_expiry"] == "2027-07-31"
    events = [e["event"] for e in client.get("/audit", headers=H["parent"]).json()["entries"]]
    assert {"renewal_planned", "renewal_step", "renewal_completed"} <= set(events)


def test_agent_may_plan_but_not_tick_steps_or_confirm(client):
    c = client.post("/renewals/endorsement_expiry", headers=H["agent"]).json()
    assert client.post(f"/renewals/case/{c['id']}/steps/request_docs", json={"status": "done"}, headers=H["agent"]).status_code == 403
    assert client.post(f"/renewals/case/{c['id']}/complete", json={"new_expiry": "2027-07-31"}, headers=H["agent"]).status_code == 403


def test_bad_new_expiry_is_rejected(client):
    c = client.post("/renewals/endorsement_expiry", headers=H["parent"]).json()
    assert client.post(f"/renewals/case/{c['id']}/complete", json={"new_expiry": "2026-11-01"}, headers=H["parent"]).status_code == 400


def test_next_step_reminder_replaces_generic_warning_and_turns_red_when_overdue(client):
    client.post("/sandbox/advance", json={"days": 60}, headers=H["parent"])  # 11 Dec: 20 days left → generic warning
    types = {i["type"] for i in client.get("/insights", headers=H["parent"]).json()["insights"]}
    assert "renewal_due" in types
    client.post("/renewals/endorsement_expiry", headers=H["parent"])
    client.post("/sandbox/advance", json={"days": 5}, headers=H["parent"])  # 16 Dec: request_docs (14 Dec) overdue
    ins = client.get("/insights", headers=H["parent"]).json()["insights"]
    step = next(i for i in ins if i["type"] == "renewal_step")
    assert step["severity"] == "alert" and "overdue" in step["body"].lower() and "renewal_due" not in {i["type"] for i in ins}


def test_offline_agent_starts_a_renewal_in_bengali():
    c = TestClient(create_app(audit_path=None, llm=None))
    r = c.post("/agent/chat", json={"message": "আমার কার্ডের এনডোর্সমেন্ট নবায়ন করতে চাই", "lang": "bn"}, headers=H["student"]).json()
    assert "start_renewal" in r["tools_used"] and r["actions"][0]["type"] == "renewal" and "📋" in r["reply"]


def test_llm_agent_uses_the_renewal_tool():
    fake = FakeLLM([completion(tool_calls=[tool_call("start_renewal", {"item": "student_file_expiry"})]),
                    completion("Plan ready.")])
    c = TestClient(create_app(audit_path=None, llm=fake.client()))
    r = c.post("/agent/chat", json={"message": "help me renew my student file"}, headers=H["student"]).json()
    assert r["actions"][0] == {"type": "renewal", "item": "student_file_expiry", "case_id": r["actions"][0]["case_id"]}
    assert '"steps"' in fake.requests[1]["messages"][-1]["content"]
