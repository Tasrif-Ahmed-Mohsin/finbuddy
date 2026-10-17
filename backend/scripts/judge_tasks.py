"""Run Judge mode: every scripted task of the brief, end to end, and write the report the judges can read.

Each task runs in its own fresh sandbox through the real API (the same code paths as the app): compliance checks,
the permission engine, approvals and signatures, the autopilot, the sandbox bank and the hash-chained log.
The chat is answered by the offline rules, so the run is free, fast and gives the same result every time.

Output:  docs/evidence/judge_tasks.md

Usage:  python scripts/judge_tasks.py
"""
from __future__ import annotations

import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SATHI_LLM_ENABLED", "0")
os.environ.setdefault("WHATSAPP_MODE", "off")
os.environ.setdefault("SATHI_FX_MODE", "saved")  # the saved real history: no network needed
os.environ.setdefault("SATHI_AUDIT_PATH", str(ROOT / "var" / "judge-audit.jsonl"))

from app.fx import FxProvider  # noqa: E402
from app.judge import run_all  # noqa: E402

OUT = ROOT.parent / "docs" / "evidence" / "judge_tasks.md"
NAMES = {"task": "Task completion (40%)", "security": "Security & compliance (30%)", "interaction": "Innovation & interaction (30%)"}


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    res = run_all(fx=FxProvider())
    lines = [
        "# Judge mode: scripted tasks, run end to end",
        "",
        f"Run on {date.today().isoformat()} with `python scripts/judge_tasks.py` (also in the app: Settings → Judge mode). "
        "Every task runs in its own fresh sandbox through the real API; the chat is answered by the offline rules, so the "
        "result is the same every time. The AI model cannot change what is allowed: the permission engine sits below it, "
        "and task S5 gives the agent a malicious model to prove it.",
        "",
        f"**{res['passed']} of {res['total']} tasks passed.**",
        "",
        "| Judging dimension | Passed |",
        "|---|---|",
    ]
    for key, name in NAMES.items():
        s = res["summary"][key]
        lines.append(f"| {name} | {s['passed']} / {s['total']} |")
    for key, name in NAMES.items():
        lines += ["", f"## {name}"]
        for t in (t for t in res["tasks"] if t["criterion"] == key):
            mark = "✅" if t["passed"] else "❌"
            lines += ["", f"### {mark} {t['id']} · {t['title']}", "", f"*{t['goal']}*", "", "| Who | Did | Result |", "|---|---|---|"]
            lines += [f"| {cell(s['who'])} | {cell(s['did'])} | {cell(s['got'])} |" for s in t["steps"]]
            lines += [""] + [f"- {'✓' if c['ok'] else '✗'} {c['what']}" for c in t["checks"]]
            if t["error"]:
                lines.append(f"- ✗ error: {t['error']}")
            if t["value"]:
                lines.append(f"- **Value:** {t['value']}")
            ev = t["evidence"]
            if ev and ev.get("seq"):
                lines.append(f"- **Evidence:** log entry #{ev['seq']} `{ev['event']}` hash `{ev['hash']}…` (chain valid: {ev['chain_valid']})")
            lines.append(f"- Ran in {t['ms']} ms")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{res['passed']}/{res['total']} passed → {OUT}")
    for key in NAMES:
        print(f"  {key}: {res['summary'][key]['passed']}/{res['summary'][key]['total']}")
    sys.exit(0 if res["passed"] == res["total"] else 1)


if __name__ == "__main__":
    main()
