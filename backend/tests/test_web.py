"""Public deployment: one address for the web app and the API, rate limits, AI budget, demo reset."""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.llm import DeepSeekClient, LLMUnavailable
from app.main import create_app
from app.web import create_site

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}


@pytest.fixture
def web_dir(tmp_path):
    d = tmp_path / "dist"
    d.mkdir()
    (d / "index.html").write_text("<html>sathi app</html>", encoding="utf-8")
    (d / "favicon.ico").write_bytes(b"icon")
    (tmp_path / "secret.env").write_text("DEEPSEEK_API_KEY=sk-not-for-you", encoding="utf-8")
    return d


@pytest.fixture
def site(web_dir):
    return TestClient(create_site(create_app(audit_path=None, llm=None), web_dir, {"ai": (3, 600.0), "write": (5, 600.0)}))


def test_api_lives_under_api_and_app_routes_get_the_web_app(site):
    assert site.get("/api/health").json()["sandbox"] is True
    assert site.get("/api/emergency", headers=H["parent"]).json()["plan"]["today"] == "2026-10-12"
    for path in ("/", "/emergency", "/plan", "/draft/draft-0001"):  # app links, even ones that look like API paths
        assert site.get(path).text == "<html>sathi app</html>"
    assert site.get("/favicon.ico").content == b"icon"


@pytest.mark.parametrize("path", ["/../secret.env", "/%2e%2e/secret.env", "/..%2fsecret.env", "/dist/../secret.env"])
def test_files_outside_the_build_are_never_served(site, path):
    assert "sk-not-for-you" not in site.get(path).text


def test_ai_endpoints_are_rate_limited_per_address(site):
    codes = [site.post("/api/agent/chat", json={"message": "hello"}, headers=H["student"]).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    other = {"x-forwarded-for": "203.0.113.9"}  # a different visitor is not affected
    assert site.post("/api/agent/chat", json={"message": "hello"}, headers={**H["student"], **other}).status_code == 200
    assert site.get("/api/health").status_code == 200  # reading is never limited


def test_the_cpu_heavy_stress_test_is_rate_limited_per_address(web_dir):
    site = TestClient(create_site(create_app(audit_path=None, llm=None), web_dir, {"heavy": (2, 600.0)}))
    codes = [site.get("/api/plan/stress?runs=20", headers=H["parent"]).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    other = {"x-forwarded-for": "203.0.113.9"}
    assert site.get("/api/plan/stress?runs=20", headers={**H["parent"], **other}).status_code == 200
    assert site.get("/api/plan/year", headers=H["parent"]).status_code == 200  # other reads are not limited


def test_ai_budget_runs_out_into_the_rule_based_fallback():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]})

    llm = DeepSeekClient("test-key", transport=httpx.MockTransport(handler), daily_calls=2)
    llm.chat([{"role": "user", "content": "a"}])
    llm.chat([{"role": "user", "content": "b"}])
    with pytest.raises(LLMUnavailable, match="budget"):
        llm.chat([{"role": "user", "content": "c"}])
    assert len(calls) == 2
    c = TestClient(create_app(audit_path=None, llm=llm))
    r = c.post("/agent/chat", json={"message": "send money"}, headers=H["parent"]).json()
    assert r["mode"] != "llm" and "How much" in r["reply"]  # still answers, with the rules


def test_users_can_reset_the_demo_but_the_agent_cannot():
    c = TestClient(create_app(audit_path=None, llm=None))
    c.post("/sandbox/advance", json={"days": 5}, headers=H["parent"])
    assert c.get("/emergency", headers=H["parent"]).json()["plan"]["today"] == "2026-10-17"
    assert c.post("/sandbox/reset", headers=H["agent"]).status_code == 403
    assert c.post("/sandbox/reset", headers=H["parent"]).json()["now"].startswith("2026-10-12")
    assert c.get("/emergency", headers=H["parent"]).json()["plan"]["today"] == "2026-10-12"
