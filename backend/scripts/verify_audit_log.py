"""Verify an exported sandbox operation log on its own: no server, no project code, only the Python standard library.

Each entry stores the SHA-256 of the previous entry and its own SHA-256 over its canonical JSON, so editing, deleting,
inserting or reordering any entry breaks the chain at that exact place.

Usage:
    python backend/scripts/verify_audit_log.py docs/evidence/sandbox_operation_log.jsonl
    python backend/scripts/verify_audit_log.py docs/evidence/sandbox_operation_log.jsonl --tamper 120
        (changes one value of entry 120 in memory, to show the check catching it; the file is not touched)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter

GENESIS = "0" * 64


def canonical(obj: dict) -> str:
    """The exact serialisation the log hashes (same as backend/app/audit/log.py)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def verify(entries: list[dict]) -> dict:
    prev = GENESIS
    for i, entry in enumerate(entries):
        body = {k: v for k, v in entry.items() if k != "hash"}
        expected = hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()
        if entry.get("prev_hash") != prev:
            return {"valid": False, "broken_at_seq": entry.get("seq", i + 1), "why": "prev_hash does not match the entry before"}
        if entry.get("hash") != expected:
            return {"valid": False, "broken_at_seq": entry.get("seq", i + 1), "why": "the entry's content does not match its hash"}
        prev = entry["hash"]
    return {"valid": True, "broken_at_seq": None, "why": None}


def tamper(entries: list[dict], seq: int) -> str:
    """Change one value inside entry `seq` (in memory), the way someone editing the file would."""
    target = next(e for e in entries if e.get("seq") == seq)
    data = target.get("data") or {}
    for key, value in data.items():
        if isinstance(value, str) and any(ch.isdigit() for ch in value):
            data[key] = value.replace(next(ch for ch in value if ch.isdigit()), "9", 1)
            return f"entry {seq}: data.{key} {value!r} → {data[key]!r}"
    target["event"] = target["event"] + "_edited"
    return f"entry {seq}: event renamed to {target['event']!r}"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--tamper", type=int, metavar="SEQ", help="edit entry SEQ in memory and show that the check catches it")
    args = ap.parse_args()

    with open(args.path, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    if args.tamper:
        print("Tamper test:", tamper(entries, args.tamper))

    result = verify(entries)
    levels = Counter(e.get("permission_level") for e in entries)
    actors = Counter(e.get("actor") for e in entries)
    events = Counter(e.get("event") for e in entries)
    print(f"Entries:       {len(entries)} (seq {entries[0]['seq']} → {entries[-1]['seq']})")
    print(f"Sandbox time:  {entries[0].get('sim_time')} → {entries[-1].get('sim_time')}")
    print(f"Chain:         {'VALID' if result['valid'] else 'BROKEN at entry ' + str(result['broken_at_seq']) + ': ' + result['why']}")
    print(f"Head hash:     {entries[-1]['hash']}")
    print("By level:      " + ", ".join(f"{k} {v}" for k, v in levels.most_common()))
    print("By actor:      " + ", ".join(f"{k} {v}" for k, v in actors.most_common()))
    print("Money:         "
          f"{events['transfer_sent']} transfers sent, {events['transfer_arrived']} arrived, "
          f"{events['iso20022_generated']} ISO 20022 messages, "
          f"{sum(1 for e in entries if e['event'] == 'transfer_sent' and e.get('permission_level') == 'MANDATE')} "
          "sent by the autopilot under the signed mandate")
    print("Refusals:      "
          f"{events['permission_denied']} permission denied, {events['mandate_sign_denied']} mandate signatures refused, "
          f"{events['passkey_verification_failed']} passkey signature refused, {events['bank_read_denied']} bank read refused")
    print("Other:         " + ", ".join(f"{k} {events[k]}" for k in (
        "passkey_registered", "mandate_signed", "draft_approved", "idempotent_replay", "shield_saved", "shield_cover",
        "bank_consent_authorised", "bank_consent_revoked") if events[k]))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
