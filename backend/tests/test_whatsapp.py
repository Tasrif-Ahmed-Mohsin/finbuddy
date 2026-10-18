"""WhatsApp alerts: notifications only, family's own number, dry run vs live, never the token or message text in logs."""
import json
from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from app.integrations.whatsapp import WhatsAppNotifier, mask, normalise_number
from app.main import create_app

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}
NOW = datetime(2026, 10, 12, 9)
TOKEN = "EAA-test-token-never-logged"


class FakeMeta:
    def __init__(self, responses=None):
        self.requests: list[dict] = []
        self.responses = list(responses or [])

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append({"url": str(request.url), "auth": request.headers.get("authorization"),
                              "body": json.loads(request.content)})
        if self.responses:
            status, body = self.responses.pop(0)
            return httpx.Response(status, json=body)
        return httpx.Response(200, json={"messages": [{"id": "wamid.TEST"}]})


def live(fake: FakeMeta) -> WhatsAppNotifier:
    return WhatsAppNotifier("live", TOKEN, "1234567890", "v21.0", httpx.MockTransport(fake.handler))


def test_numbers_must_be_international():
    assert normalise_number("+880 1712-345678") == "+8801712345678"
    assert normalise_number("008801712345678") == "+8801712345678"
    with pytest.raises(ValueError):
        normalise_number("01712345678")  # no country code
    assert mask("+8801712345678") == "••••5678"


def test_dry_run_sends_nothing():
    n = WhatsAppNotifier("dry_run", TOKEN, "1234567890", transport=httpx.MockTransport(lambda r: pytest.fail("no network")))
    e = n.send("+8801712345678", "ব্লুফিন · টেস্ট", "test", "test", NOW)
    assert e.status == "logged" and e.to == "••••5678" and "ব্লুফিন" in e.detail


def test_live_posts_a_text_message_to_the_cloud_api():
    fake = FakeMeta()
    e = live(fake).send("+8801712345678", "ব্লুফিন · ¥৬,০০০ পাঠানো হয়েছে", "note", "autopilot_sent", NOW)
    r = fake.requests[0]
    assert e.status == "sent" and e.message_id == "wamid.TEST"
    assert r["url"] == "https://graph.facebook.com/v21.0/1234567890/messages" and r["auth"] == f"Bearer {TOKEN}"
    assert r["body"]["to"] == "8801712345678" and r["body"]["type"] == "text" and "ব্লুফিন" in r["body"]["text"]["body"]
    assert TOKEN not in json.dumps(e.to_dict())


def test_outside_the_24h_window_the_approved_template_is_sent():
    fake = FakeMeta([(400, {"error": {"code": 131047, "message": "Re-engagement message"}})])
    e = live(fake).send("+8801712345678", "text", "note", "k", NOW)
    assert e.status == "sent_template" and fake.requests[1]["body"]["template"]["name"] == "hello_world"


def test_a_number_not_on_the_test_list_fails_with_a_clear_reason():
    fake = FakeMeta([(400, {"error": {"code": 131030, "message": "Recipient phone number not in allowed list"}})])
    e = live(fake).send("+8801712345678", "text", "note", "k", NOW)
    assert e.status == "failed" and "allowed list" in e.detail and len(fake.requests) == 1  # no template spam


def test_network_failure_never_breaks_sathi():
    def boom(request):
        raise httpx.ConnectError("offline")
    n = WhatsAppNotifier("live", TOKEN, "1", transport=httpx.MockTransport(boom))
    assert n.send("+8801712345678", "x", "note", "k", NOW).status == "failed"


# ---- through the app --------------------------------------------------------------------------
@pytest.fixture
def client():
    c = TestClient(create_app(audit_path=None, llm=None))
    c.app.state.svc.whatsapp = WhatsAppNotifier("dry_run", TOKEN, "1234567890")  # tests never send for real
    return c


def test_only_users_set_the_number_and_the_agent_cannot_message_anyone(client):
    assert client.post("/notify/whatsapp/recipient", json={"number": "+8801712345678"}, headers=H["agent"]).status_code == 403
    assert client.post("/notify/whatsapp/test", headers=H["agent"]).status_code == 403
    assert client.get("/notify/whatsapp", headers=H["agent"]).status_code == 403
    r = client.post("/notify/whatsapp/recipient", json={"number": "01712"}, headers=H["parent"])
    assert r.status_code == 400
    r = client.post("/notify/whatsapp/recipient", json={"number": "+8801712345678", "lang": "bn"}, headers=H["parent"]).json()
    assert r["recipient"] == "••••5678" and r["mode"] == "dry_run"


def test_family_alerts_go_out_in_bengali_with_a_safety_footer_and_logs_hold_no_text(client):
    client.post("/notify/whatsapp/recipient", json={"number": "+8801712345678"}, headers=H["parent"])
    p = client.post("/mandates/proposals", json={"text": "প্রতি মাসে ১ লাখ ২০ হাজার টাকা পর্যন্ত", "lang": "bn"}, headers=H["parent"]).json()
    client.post(f"/mandates/proposals/{p['id']}/sign", json={"proposal_hash": p["hash"]}, headers=H["parent"])
    client.post(f"/mandates/proposals/{p['id']}/sign", json={"proposal_hash": p["hash"]}, headers=H["student"])
    out = client.get("/notify/whatsapp", headers=H["parent"]).json()["outbox"]
    sent = next(e for e in out if e["key"] == "autopilot_sent")
    assert sent["status"] == "logged" and sent["detail"].startswith("ব্লুফিন · ব্লুফিন শিক্ষার্থীর")
    assert "আঙুলের ছাপ" in client.app.state.svc.whatsapp.outbox[-1].detail or any("আঙুলের ছাপ" in e["detail"] for e in out)
    entries = client.get("/audit?limit=200", headers=H["parent"]).json()["entries"]
    wa = [e for e in entries if e["event"] == "whatsapp_notified"]
    assert wa and all(set(e["data"]) == {"kind", "key", "mode", "status", "to"} for e in wa)
    assert TOKEN not in json.dumps(entries)


def test_fast_forward_sends_one_summary_not_one_message_per_note(client):
    client.post("/notify/whatsapp/recipient", json={"number": "+8801712345678"}, headers=H["parent"])
    client.post("/sandbox/advance", json={"days": 30}, headers=H["parent"])
    out = client.get("/notify/whatsapp", headers=H["parent"]).json()["outbox"]
    assert [e["kind"] for e in out] == ["digest"] and "সারসংক্ষেপ" in out[0]["detail"]


def test_no_number_means_no_messages(client):
    client.post("/sandbox/advance", json={"days": 30}, headers=H["parent"])
    assert client.get("/notify/whatsapp", headers=H["parent"]).json()["outbox"] == []
