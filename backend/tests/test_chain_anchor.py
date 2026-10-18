"""The evidence log's on-chain anchor: the shipped log must be the anchored one, and the chain must say so."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.integrations import chain_anchor
from app.main import create_app

H = {r: {"Authorization": f"Bearer demo-{r}"} for r in ("student", "parent", "agent")}
RECORD = chain_anchor.DEFAULT_RECORD
LOG = chain_anchor.DEFAULT_LOG


def fake_chain(head: str, entries: int, *, status: str = "0x1", topic_head: str | None = None):
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    contract = rec["contract"]["address"]
    answers = {
        "eth_blockNumber": "0x2",
        "eth_getCode": "0x6080604052",
        "eth_getTransactionReceipt": {"status": status, "to": contract, "logs": [{"topics": [
            chain_anchor.ANCHORED_TOPIC, "0x" + "0" * 64, "0x" + (topic_head or head)]}]},
        "eth_getTransactionByHash": {"input": chain_anchor._expected_input_prefix(head, entries) + "00" * 32},
    }
    return lambda url, method, params, timeout: answers[method]


def test_offline_the_shipped_log_is_the_anchored_one():
    out = chain_anchor.check(rpc="")
    assert out["enabled"] and not out["live"]
    assert out["log_head"] == out["anchored_head"] and out["entries"] == 255
    assert out["ok"] and {c["id"] for c in out["checks"]} == {"log_chain_valid", "log_head_matches_record"}


def test_live_checks_pass_against_the_chain(monkeypatch):
    out0 = chain_anchor.check(rpc="")
    monkeypatch.setattr(chain_anchor, "_rpc", fake_chain(out0["log_head"], out0["entries"]))
    out = chain_anchor.check(rpc="http://chain")
    assert out["live"] and out["ok"] and len(out["checks"]) == 6 and out["network"]["latest_block"] == 2


def test_a_failed_or_foreign_transaction_fails_the_check(monkeypatch):
    out0 = chain_anchor.check(rpc="")
    monkeypatch.setattr(chain_anchor, "_rpc", fake_chain(out0["log_head"], out0["entries"], status="0x0", topic_head="ab" * 32))
    out = chain_anchor.check(rpc="http://chain")
    failed = {c["id"] for c in out["checks"] if not c["ok"]}
    assert not out["ok"] and failed == {"transaction_succeeded", "event_carries_this_head"}


def test_an_edited_log_no_longer_matches_the_anchor(tmp_path: Path):
    lines = LOG.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[149])
    entry["event"] = entry["event"] + "_edited"
    lines[149] = json.dumps(entry, ensure_ascii=False)
    edited = tmp_path / "log.jsonl"
    edited.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = chain_anchor.check(log_path=edited, rpc="")
    assert not out["ok"] and [c["id"] for c in out["checks"] if not c["ok"]] == ["log_chain_valid"]


def test_an_unreachable_chain_is_said_plainly(monkeypatch):
    def down(url, method, params, timeout):
        raise chain_anchor.httpx.ConnectError("down")
    monkeypatch.setattr(chain_anchor, "_rpc", down)
    out = chain_anchor.check(rpc="http://chain")
    assert out["enabled"] and not out["live"] and out["network"]["reachable"] is False and out["ok"]


def test_no_record_means_no_anchor_card(tmp_path: Path):
    assert chain_anchor.check(record_path=tmp_path / "none.json", rpc="") == {"enabled": False}


@pytest.mark.parametrize("who", ["parent", "student"])
def test_the_trust_center_endpoint(who):
    chain_anchor._cache["value"] = None
    body = TestClient(create_app(audit_path=None, llm=None)).get("/security/anchor", headers=H[who]).json()
    assert body["enabled"] and body["anchored_head"] == body["log_head"]
