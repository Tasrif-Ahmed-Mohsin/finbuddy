"""Judge mode: every scripted task of the brief passes end to end, in fresh sandboxes, with evidence."""
from fastapi.testclient import TestClient

from app.fx import FxProvider
from app.judge import TASKS, run_all
from app.main import create_app

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}


def test_every_scripted_task_passes_with_evidence():
    res = run_all(fx=FxProvider(mode="fixture"))
    failed = {t["id"]: [c["what"] for c in t["checks"] if not c["ok"]] or t["error"] for t in res["tasks"] if not t["passed"]}
    assert not failed and res["passed"] == res["total"] == len(TASKS)
    assert {k: v["total"] for k, v in res["summary"].items()} == {"task": 9, "security": 7, "interaction": 4}
    for t in res["tasks"]:
        assert t["steps"] and t["value"] and t["evidence"], t["id"]


def test_the_compromised_ai_drill_moves_no_money():
    drill = next(t for t in run_all(fx=FxProvider(mode="fixture"))["tasks"] if t["id"] == "S5")
    assert drill["passed"] and len([s for s in drill["steps"] if s["who"] == "rogue AI"]) == 5
    assert "unknown tool" in drill["steps"][1]["got"] and "blocked" in drill["steps"][0]["got"]


def test_judge_endpoint_runs_without_touching_this_session():
    client = TestClient(create_app(audit_path=None, llm=None))
    before = len(client.app.state.svc.audit.entries)
    assert client.post("/judge/run", headers=H["agent"]).status_code == 403
    assert client.post("/judge/run").status_code == 401
    res = client.post("/judge/run", headers=H["parent"]).json()
    assert res["passed"] == res["total"]
    assert len(client.app.state.svc.audit.entries) == before and not client.get("/drafts", headers=H["parent"]).json()


def test_a_judge_run_never_messages_a_real_family(monkeypatch):
    # Even on a server set up to really send WhatsApp alerts, the judge's sandboxes keep them off.
    import app.judge as judge
    made = []
    real_init = judge.Sandbox.__init__

    def spy(self, fx=None, llm=None, bank_rates=None):
        real_init(self, fx, llm, bank_rates)
        made.append(self.svc)

    monkeypatch.setenv("WHATSAPP_MODE", "live")
    monkeypatch.setattr(judge.Sandbox, "__init__", spy)
    run_all(fx=FxProvider(mode="fixture"))
    assert made and all(not s.whatsapp.enabled and s.profile["parent_whatsapp"] is None for s in made)
