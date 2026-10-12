"""Append-only, hash-chained audit log (the "sandbox operation logs" deliverable).

Each entry stores the SHA-256 of the previous entry, so editing or deleting any past entry breaks
the chain and `verify()` reports exactly where. Written as JSON Lines so judges can read it directly.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


class AuditLog:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.entries: list[dict] = []
        self._lock = threading.Lock()
        if path and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.entries.append(json.loads(line))

    @property
    def last_hash(self) -> str:
        return self.entries[-1]["hash"] if self.entries else GENESIS

    def append(self, event: str, actor: str, level: str, data: dict, sim_time: str | None = None) -> dict:
        with self._lock:
            body = {
                "seq": len(self.entries) + 1,
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "sim_time": sim_time,
                "event": event,
                "actor": actor,
                "permission_level": level,
                "data": data,
                "prev_hash": self.last_hash,
            }
            body["hash"] = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
            self.entries.append(body)
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(_canonical(body) + "\n")
            return body

    def verify(self) -> dict:
        prev = GENESIS
        for i, entry in enumerate(self.entries):
            body = {k: v for k, v in entry.items() if k != "hash"}
            expected = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
            if entry.get("prev_hash") != prev or entry.get("hash") != expected:
                return {"valid": False, "broken_at_seq": entry.get("seq", i + 1), "entries": len(self.entries)}
            prev = entry["hash"]
        return {"valid": True, "broken_at_seq": None, "entries": len(self.entries)}
