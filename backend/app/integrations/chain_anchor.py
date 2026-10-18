"""The evidence log's on-chain anchor (FISCO BCOS), checked live and read-only.

`scripts/anchor_fisco.py` wrote the head hash of the committed sandbox operation log into a transaction on a FISCO BCOS
chain and saved what it did (contract, transaction, no keys) to `docs/evidence/anchor_record.json`. This module answers
one question for the trust center: is the log we ship still the log that was anchored? It recomputes the log's hash
chain, compares its head with the record and, when the chain's JSON-RPC is reachable (`SATHI_ANCHOR_RPC`, on the server
only), asks the chain itself: the contract has code, the transaction succeeded, its input is `anchor(head, entries, …)`
and its event carries the same head. Nothing here can write to the chain.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.audit.log import AuditLog

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RECORD = ROOT / "docs" / "evidence" / "anchor_record.json"
DEFAULT_LOG = ROOT / "docs" / "evidence" / "sandbox_operation_log.jsonl"
ANCHOR_SELECTOR = "0x5e1374e4"  # first 4 bytes of keccak256("anchor(bytes32,uint256,string)")
ANCHORED_TOPIC = "0xb1eee06fcafba001c6b5e3f301fa8992048d66b89b7d9ea5525ff1638f233134"  # Anchored(uint256,bytes32,uint256,string,address)
CACHE_SECONDS = 60

_cache: dict = {"at": 0.0, "value": None}


def _rpc(url: str, method: str, params: list, timeout: float):
    r = httpx.post(url, json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1}, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    if body.get("error"):
        raise RuntimeError(body["error"])
    return body.get("result")


def _expected_input_prefix(head: str, entries: int) -> str:
    return ANCHOR_SELECTOR + head.lower() + format(entries, "064x")


def check(record_path: Path | None = None, log_path: Path | None = None, rpc: str | None = None, timeout: float = 4.0) -> dict:
    record_path = Path(record_path or os.environ.get("SATHI_ANCHOR_RECORD") or DEFAULT_RECORD)
    log_path = Path(log_path or os.environ.get("SATHI_EVIDENCE_LOG") or DEFAULT_LOG)
    rpc = rpc if rpc is not None else (os.environ.get("SATHI_ANCHOR_RPC") or None)
    if not record_path.exists() or not log_path.exists():
        return {"enabled": False}
    rec = json.loads(record_path.read_text(encoding="utf-8"))
    contract, tx = rec["contract"]["address"], rec["anchorTx"]["hash"]
    log = AuditLog(log_path)
    verify = log.verify()
    head = log.last_hash
    checks = [
        {"id": "log_chain_valid", "ok": verify["valid"]},
        {"id": "log_head_matches_record", "ok": head == rec["headHash"] and verify["entries"] == rec["entries"]},
    ]
    network = {"name": "FISCO BCOS", "version": rec["chain"]["clientVersion"].split("/")[1] if "/" in rec["chain"]["clientVersion"] else "",
               "chain_id": rec["chain"]["eth_chainId"], "reachable": False, "latest_block": None}
    if rpc:
        try:
            network["latest_block"] = int(_rpc(rpc, "eth_blockNumber", [], timeout), 16)
            code = _rpc(rpc, "eth_getCode", [contract, "latest"], timeout) or "0x"
            receipt = _rpc(rpc, "eth_getTransactionReceipt", [tx], timeout) or {}
            txn = _rpc(rpc, "eth_getTransactionByHash", [tx], timeout) or {}
            network["reachable"] = True
            checks += [
                {"id": "contract_on_chain", "ok": len(code) > 2},
                {"id": "transaction_succeeded", "ok": receipt.get("status") == "0x1"
                    and (receipt.get("to") or "").lower() == contract.lower()},
                {"id": "transaction_anchors_this_head", "ok": (txn.get("input") or "").lower().startswith(
                    _expected_input_prefix(head, verify["entries"]))},
                {"id": "event_carries_this_head", "ok": any(
                    (lg.get("topics") or [None])[0] == ANCHORED_TOPIC and len(lg.get("topics") or []) > 2
                    and lg["topics"][2].lower() == "0x" + head.lower() for lg in receipt.get("logs") or [])},
            ]
        except (httpx.HTTPError, RuntimeError, ValueError, KeyError):
            network["reachable"] = False
    return {
        "enabled": True,
        "network": network,
        "contract": contract,
        "transaction": tx,
        "block": rec["anchorTx"]["block"],
        "anchored_head": rec["headHash"],
        "log_head": head,
        "entries": verify["entries"],
        "checks": checks,
        "ok": all(c["ok"] for c in checks),
        "live": network["reachable"],
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def cached_check() -> dict:
    """The trust center polls this; one chain round-trip a minute is plenty."""
    now = time.monotonic()
    if _cache["value"] is None or now - _cache["at"] > CACHE_SECONDS:
        _cache["value"], _cache["at"] = check(), now
    return _cache["value"]
