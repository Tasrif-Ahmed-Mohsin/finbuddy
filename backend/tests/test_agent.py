"""Chat agent: tool calling with a fake DeepSeek, safety limits, and the offline fallback."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.permissions import Actor
from tests.fake_llm import FakeLLM, completion, tool_call

H = {"student": {"Authorization": "Bearer demo-student"}, "parent": {"Authorization": "Bearer demo-parent"},
     "agent": {"Authorization": "Bearer demo-agent"}}


def make(fake: FakeLLM | None):
    return TestClient(create_app(audit_path=None, llm=fake.client() if fake else None))


def test_agent_answers_with_tool_results():
    fake = FakeLLM([
        completion(tool_calls=[tool_call("compare_tuition", {"amount_cny": 35200, "deadline": "2026-11-15"})]),
        completion("Send by 2026-11-05 with Sample Bank C."),
    ])
    c = make(fake)
    r = c.post("/agent/chat", json={"message": "When should I pay tuition?", "lang": "en"}, headers=H["parent"]).json()
    assert r["mode"] == "llm" and r["tools_used"] == ["compare_tuition"] and "2026-11-05" in r["reply"]
    tool_msg = fake.requests[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_1" and "send_by" in tool_msg["content"]
    names = {t["function"]["name"] for t in fake.requests[0]["tools"]}
    assert not any(w in n for n in names for w in ("approve", "execute"))  # no tool can move money
    events = [e["event"] for e in c.get("/audit", headers=H["parent"]).json()["entries"]]
    assert "agent_tool_call" in events and "agent_chat" in events


def test_agent_can_only_draft_and_the_user_must_approve():
    fake = FakeLLM([
        completion(tool_calls=[tool_call("create_payment_draft", {"kind": "tt_tuition", "amount_cny": 35200,
                                                                   "payee_id": "univ_demo", "memo": "Tuition"})]),
        completion("I prepared the draft. Please approve it in the app."),
    ])
    c = make(fake)
    r = c.post("/agent/chat", json={"message": "Prepare my tuition payment"}, headers=H["parent"]).json()
    assert r["actions"][0]["type"] == "draft" and r["actions"][0]["status"] == "draft"
    draft_id = r["actions"][0]["draft_id"]
    svc = c.app.state.svc
    with pytest.raises(PermissionError):
        svc.execute(Actor.AGENT, draft_id)  # even if the model wanted to, the agent cannot execute
    assert svc.drafts[draft_id].status == "draft"


def test_agent_survives_unknown_tools_and_bad_arguments():
    fake = FakeLLM([
        completion(tool_calls=[tool_call("transfer_all_money", {}), tool_call("plan_living", {"need_cny": "abc"}, "call_2")]),
        completion("Sorry, I can only plan and draft."),
    ])
    r = make(fake).post("/agent/chat", json={"message": "send everything"}, headers=H["student"]).json()
    results = [m for m in fake.requests[1]["messages"] if m["role"] == "tool"]
    assert all("error" in m["content"] for m in results) and r["mode"] == "llm"


def test_llm_outage_falls_back_to_rules():
    c = make(FakeLLM([], status=500))
    r = c.post("/agent/chat", json={"message": "How much for tuition?"}, headers=H["parent"]).json()
    assert r["mode"] == "fallback" and "2026-11-05" in r["reply"]


@pytest.mark.parametrize("message,lang,expect", [
    ("Bhai, hundi te pathale rate bhalo", "en", "⚠️"),
    ("I need 6000 yuan for living this month", "en", "saves"),
    ("ছেলের টিউশন কবে পাঠাব?", "bn", "সাশ্রয়"),
    ("这个月生活费6000元怎么取最省钱", "zh", "节省"),
])
def test_offline_fallback_handles_three_languages(message, lang, expect):
    r = make(None).post("/agent/chat", json={"message": message, "lang": lang}, headers=H["student"]).json()
    assert r["mode"] == "fallback" and expect in r["reply"]


def test_agent_token_cannot_use_chat_as_a_user():
    assert make(None).post("/agent/chat", json={"message": "hi"}, headers=H["agent"]).status_code == 403
