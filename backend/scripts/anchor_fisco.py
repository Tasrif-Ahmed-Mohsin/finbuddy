"""Anchor the head hash of the sandbox operation log on a FISCO BCOS 3.x chain, and check it later.

The log is tamper-evident on its own: each entry stores the SHA-256 of the entry before. Writing the newest hash (the
head) into a blockchain transaction adds a witness outside our server. After that, the history up to the head cannot be
rewritten without the rewrite showing, not even by whoever runs Bluefin.

The script talks to the chain through FISCO BCOS's Ethereum-compatible JSON-RPC. This is `[web3_rpc]` in each node's
config.ini, port 8545, available since v3.9. The script compiles the EvidenceAnchor contract below with solc 0.8.11 and
signs with a fresh key that exists only in memory for that run. The key is never printed or saved; the chain is a local
test chain.

Setup:   pip install eth-account py-solc-x requests

Usage:
    python backend/scripts/anchor_fisco.py anchor docs/evidence/sandbox_operation_log.jsonl --rpc http://127.0.0.1:8545
        (checks the log's chain, deploys EvidenceAnchor, anchors the head hash and entry count, reads it back)
    python backend/scripts/anchor_fisco.py verify docs/evidence/sandbox_operation_log.jsonl --rpc http://127.0.0.1:8545
        --contract 0x... [--tx 0x...]
        (recomputes the head hash from the file and checks it against the contract, the transaction and the deployed code)
    python backend/scripts/anchor_fisco.py calldata docs/evidence/sandbox_operation_log.jsonl
        (offline: prints the exact transaction input the anchor call carries, to compare with a recorded transaction)
    python backend/scripts/anchor_fisco.py source
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from verify_audit_log import verify as verify_chain  # same folder: the standalone log verifier

CONTRACT_NAME = "EvidenceAnchor"
SOLC_VERSION = "0.8.11"  # the newest Solidity version FISCO BCOS 3.x documents for its EVM
CONTRACT_SOURCE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;

/// Witnesses the head hash of Bluefin's hash-chained sandbox operation log.
/// The log links every entry to the one before, so recording the newest link here fixes the whole history up to it.
contract EvidenceAnchor {
    struct Record {
        bytes32 headHash;
        uint256 entries;
        string label;
        uint256 blockNumber;
        uint256 timestamp;  // FISCO BCOS block time, in milliseconds
    }

    address public owner;
    Record[] private records;
    mapping(bytes32 => uint256) private position;  // head hash => index + 1; 0 means never anchored

    event Anchored(uint256 indexed id, bytes32 indexed headHash, uint256 entries, string label, address submitter);

    constructor() {
        owner = msg.sender;
    }

    function anchor(bytes32 headHash, uint256 entries, string calldata label) external returns (uint256 id) {
        require(msg.sender == owner, "only the owner anchors");
        require(headHash != bytes32(0) && entries > 0, "empty record");
        require(position[headHash] == 0, "already anchored");
        records.push(Record(headHash, entries, label, block.number, block.timestamp));
        id = records.length - 1;
        position[headHash] = records.length;
        emit Anchored(id, headHash, entries, label, msg.sender);
    }

    function count() external view returns (uint256) {
        return records.length;
    }

    function get(uint256 id) external view returns (bytes32, uint256, string memory, uint256, uint256) {
        Record storage r = records[id];
        return (r.headHash, r.entries, r.label, r.blockNumber, r.timestamp);
    }

    function lookup(bytes32 headHash) external view returns (bool found, uint256 id, uint256 entries, uint256 blockNumber) {
        uint256 p = position[headHash];
        if (p == 0) return (false, 0, 0, 0);
        Record storage r = records[p - 1];
        return (true, p - 1, r.entries, r.blockNumber);
    }
}
"""
ANCHORED_EVENT = "Anchored(uint256,bytes32,uint256,string,address)"
DEFAULT_LABEL = "Bluefin docs/evidence/sandbox_operation_log.jsonl"


# --- the log ---------------------------------------------------------------------------------------------------------

def read_log(path: str) -> tuple[str, int]:
    """Check the log's hash chain and return (head hash, entry count). Refuses a broken chain."""
    with open(path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    result = verify_chain(entries)
    if not result["valid"]:
        raise SystemExit(f"The log's chain is BROKEN at entry {result['broken_at_seq']}: {result['why']}. Nothing anchored.")
    return entries[-1]["hash"], len(entries)


# --- contract and encoding -------------------------------------------------------------------------------------------

def compile_contract() -> dict:
    import solcx

    if SOLC_VERSION not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(SOLC_VERSION)
    out = solcx.compile_standard({
        "language": "Solidity",
        "sources": {f"{CONTRACT_NAME}.sol": {"content": CONTRACT_SOURCE}},
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "evmVersion": "london",
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"]}},
        },
    }, solc_version=SOLC_VERSION)
    c = out["contracts"][f"{CONTRACT_NAME}.sol"][CONTRACT_NAME]
    return {"abi": c["abi"], "bytecode": "0x" + c["evm"]["bytecode"]["object"],
            "runtime": "0x" + c["evm"]["deployedBytecode"]["object"]}


def call_data(signature: str, types: list[str], values: list) -> str:
    from eth_abi import encode
    from eth_utils import function_signature_to_4byte_selector

    return "0x" + (function_signature_to_4byte_selector(signature) + encode(types, values)).hex()


def anchor_calldata(head: str, entries: int, label: str) -> str:
    return call_data("anchor(bytes32,uint256,string)", ["bytes32", "uint256", "string"], [bytes.fromhex(head), entries, label])


# --- JSON-RPC --------------------------------------------------------------------------------------------------------

class Chain:
    def __init__(self, url: str):
        import requests

        self.url, self.http, self.next_id = url, requests.Session(), 0

    def rpc(self, method: str, *params):
        self.next_id += 1
        reply = self.http.post(self.url, json={"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": list(params)},
                               timeout=30).json()
        if reply.get("error"):
            raise RuntimeError(f"{method}: {reply['error']}")
        return reply["result"]

    def call(self, to: str, data: str) -> bytes:
        return bytes.fromhex(self.rpc("eth_call", {"to": to, "data": data}, "latest")[2:])

    def lookup(self, contract: str, head: str) -> tuple[bool, int, int, int]:
        from eth_abi import decode

        raw = self.call(contract, call_data("lookup(bytes32)", ["bytes32"], [bytes.fromhex(head)]))
        return tuple(decode(["bool", "uint256", "uint256", "uint256"], raw))

    def wait_receipt(self, tx_hash: str, timeout: float = 90) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            receipt = self.rpc("eth_getTransactionReceipt", tx_hash)
            if receipt:
                return receipt
            time.sleep(1)
        raise TimeoutError(f"no receipt for {tx_hash} after {timeout:.0f}s")

    def send(self, account, data: str, to: str | None, gas: int) -> dict:
        """Sign a legacy (EIP-155) transaction with the in-memory key, send it, wait for the receipt."""
        tx = {"nonce": int(self.rpc("eth_getTransactionCount", account.address, "pending"), 16),
              "gasPrice": int(self.rpc("eth_gasPrice"), 16), "gas": gas, "value": 0, "data": data}
        chain_id = int(self.rpc("eth_chainId"), 16)
        if chain_id:
            tx["chainId"] = chain_id
        if to:
            tx["to"] = to
        signed = account.sign_transaction(tx)
        tx_hash = self.rpc("eth_sendRawTransaction", "0x" + bytes(signed.raw_transaction).hex())
        receipt = self.wait_receipt(tx_hash)
        if int(receipt["status"], 16) != 1:
            raise RuntimeError(f"transaction {tx_hash} failed: {json.dumps(receipt)}")
        return receipt


def decode_anchored(receipt: dict) -> dict:
    from eth_abi import decode
    from eth_utils import keccak

    topic0 = "0x" + keccak(text=ANCHORED_EVENT).hex()
    for log in receipt.get("logs") or []:
        if log["topics"] and log["topics"][0].lower() == topic0:
            entries, label, submitter = decode(["uint256", "string", "address"], bytes.fromhex(log["data"][2:]))
            return {"id": int(log["topics"][1], 16), "headHash": log["topics"][2][2:].lower(),
                    "entries": entries, "label": label, "submitter": submitter}
    raise RuntimeError("the receipt has no Anchored event")


def chain_info(chain: Chain) -> dict:
    info = {"rpc": chain.url, "eth_chainId": int(chain.rpc("eth_chainId"), 16), "blockNumber": int(chain.rpc("eth_blockNumber"), 16)}
    try:
        info["clientVersion"] = chain.rpc("web3_clientVersion")
    except Exception:  # optional on FISCO BCOS
        pass
    return info


# --- commands --------------------------------------------------------------------------------------------------------

def cmd_anchor(args) -> int:
    from eth_account import Account

    head, entries = read_log(args.log)
    print(f"Log:           {args.log}: {entries} entries, chain VALID")
    print(f"Head hash:     {head}")
    chain = Chain(args.rpc)
    info = chain_info(chain)
    print(f"Chain:         {info}")

    compiled = compile_contract()
    account = Account.create()  # throwaway key, held only in this process
    print(f"Signer:        {account.address} (fresh key, kept in memory only)")

    deploy = chain.send(account, compiled["bytecode"], None, gas=3_000_000)
    contract = deploy["contractAddress"]
    print(f"Deployed:      {CONTRACT_NAME} at {contract}, tx {deploy['transactionHash']}, block {int(deploy['blockNumber'], 16)}")

    receipt = chain.send(account, anchor_calldata(head, entries, args.label), contract, gas=1_000_000)
    event = decode_anchored(receipt)
    print(f"Anchored:      tx {receipt['transactionHash']}, block {int(receipt['blockNumber'], 16)}, event {event}")

    found, record_id, on_chain_entries, block = chain.lookup(contract, head)
    ok = found and on_chain_entries == entries and event["headHash"] == head and event["entries"] == entries
    print(f"Read back:     lookup(head) = found {found}, id {record_id}, entries {on_chain_entries}, block {block}"
          f" -> {'MATCH' if ok else 'MISMATCH'}")

    if args.json:
        tx = chain.rpc("eth_getTransactionByHash", receipt["transactionHash"])
        record = {"log": args.log, "headHash": head, "entries": entries, "label": args.label, "chain": info,
                  "contract": {"name": CONTRACT_NAME, "address": contract, "solc": SOLC_VERSION, "owner": account.address,
                               "deployTx": deploy["transactionHash"], "deployBlock": int(deploy["blockNumber"], 16),
                               "runtimeMatchesSource": chain.rpc("eth_getCode", contract, "latest").lower() == compiled["runtime"].lower()},
                  "anchorTx": {"hash": receipt["transactionHash"], "block": int(receipt["blockNumber"], 16), "event": event,
                               "input": tx.get("input"), "receipt": receipt},
                  "readBack": {"found": found, "id": record_id, "entries": on_chain_entries, "block": block}}
        Path(args.json).write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"Record:        {args.json}")
    return 0 if ok else 1


def cmd_verify(args) -> int:
    head, entries = read_log(args.log)
    chain = Chain(args.rpc)
    checks: list[tuple[str, bool]] = []
    print(f"Log head:      {head} ({entries} entries, chain VALID)")

    found, record_id, on_chain_entries, block = chain.lookup(args.contract, head)
    print(f"On chain:      lookup(head) = found {found}, id {record_id}, entries {on_chain_entries}, block {block}")
    checks.append(("head hash anchored with the same entry count", found and on_chain_entries == entries))

    runtime = chain.rpc("eth_getCode", args.contract, "latest").lower()
    checks.append(("deployed code is exactly the EvidenceAnchor source compiled with solc " + SOLC_VERSION,
                   runtime == compile_contract()["runtime"].lower()))

    if args.tx:
        tx = chain.rpc("eth_getTransactionByHash", args.tx)
        receipt = chain.rpc("eth_getTransactionReceipt", args.tx)
        event = decode_anchored(receipt)
        print(f"Transaction:   {args.tx}, block {int(receipt['blockNumber'], 16)}, event {event}")
        checks.append(("transaction succeeded and was sent to this contract",
                       int(receipt["status"], 16) == 1 and (tx.get("to") or "").lower() == args.contract.lower()))
        checks.append(("transaction input is anchor(head hash, entries, label)",
                       (tx.get("input") or "").lower() == anchor_calldata(head, entries, event["label"]).lower()))
        checks.append(("Anchored event carries the same head hash and count", event["headHash"] == head and event["entries"] == entries))

    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    a = sub.add_parser("anchor", help="deploy EvidenceAnchor and anchor the log's head hash")
    a.add_argument("log")
    a.add_argument("--rpc", default="http://127.0.0.1:8545")
    a.add_argument("--label", default=DEFAULT_LABEL)
    a.add_argument("--json", metavar="PATH", help="also write the full record (no keys) to PATH")
    a.set_defaults(run=cmd_anchor)

    v = sub.add_parser("verify", help="check the log's head hash against an anchored record")
    v.add_argument("log")
    v.add_argument("--rpc", default="http://127.0.0.1:8545")
    v.add_argument("--contract", required=True)
    v.add_argument("--tx", help="the anchoring transaction hash, to check its input and event too")
    v.set_defaults(run=cmd_verify)

    c = sub.add_parser("calldata", help="offline: the exact input of the anchor transaction for this log")
    c.add_argument("log")
    c.add_argument("--label", default=DEFAULT_LABEL)
    c.set_defaults(run=lambda args: print(anchor_calldata(*read_log(args.log), args.label)) or 0)

    s = sub.add_parser("source", help="print the contract source")
    s.set_defaults(run=lambda args: print(CONTRACT_SOURCE) or 0)

    args = ap.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
