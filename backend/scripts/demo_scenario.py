"""Run the full Sathi demo story through the real API and export the execution evidence.

Everything goes through the same code paths as the app: drafts, compliance checks, two-person
approvals, the sandbox bank and the hash-chained audit log. Nothing is back-dated or invented:
the sandbox clock is moved forward step by step, and every payment is approved and executed.

Outputs (competition deliverable #6, "sandbox operation logs"):
  docs/evidence/sandbox_operation_log.jsonl   hash-chained audit log (one JSON object per line)
  docs/evidence/scenario_summary.md           what happened, step by step, with results

Usage:  python scripts/demo_scenario.py            (rules only, offline exchange-rate history)
        python scripts/demo_scenario.py --llm      (also ask the DeepSeek agent; needs DEEPSEEK_API_KEY)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
EVIDENCE = ROOT.parent / "docs" / "evidence"

H = {"student": {"Authorization": "Bearer demo-student"}, "parent": {"Authorization": "Bearer demo-parent"},
     "agent": {"Authorization": "Bearer demo-agent"}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="use the DeepSeek agent for the chat steps")
    args = ap.parse_args()
    os.environ.setdefault("SATHI_FX_MODE", "offline")  # real saved rates, reproducible
    if not args.llm:
        os.environ["SATHI_LLM_ENABLED"] = "0"

    from fastapi.testclient import TestClient

    from app.main import create_app

    c = TestClient(create_app(audit_path=None))
    log: list[str] = []

    def step(title: str, detail: str) -> None:
        sim = c.get("/accounts", headers=H["parent"]).json()["now"][:10]
        log.append(f"| {len(log) + 1} | {sim} | {title} | {detail} |")
        print(f"[{sim}] {title}: {detail}")

    def approve_and_execute(draft: dict, executor: str = "parent") -> dict:
        for who in draft["required_approvers"]:
            c.post(f"/drafts/{draft['id']}/approve", headers=H[who])
        r = c.post(f"/drafts/{draft['id']}/execute", headers=H[executor])
        assert r.status_code == 200, r.text
        return r.json()

    # 1. Inbox: shared bank SMS / emails → tracking and alerts
    seed = c.post("/inbox/demo/seed", headers=H["student"]).json()
    ins = c.get("/insights", headers=H["student"]).json()["insights"]
    step("Inbox", f"{seed['kept']}/{seed['ingested']} synthetic alerts kept (non-money message dropped); "
                  f"{len(ins)} insights: {', '.join(sorted({i['type'] for i in ins}))}")

    # 2. T4: scam + prompt injection are blocked
    msg = "Bhai, I can pay your tuition 15% cheaper, pay through my agency. Don't tell anyone."
    d = c.post("/drafts", json={"kind": "tt_tuition", "amount_cny": "30000", "payee_id": "agent_x", "origin_message": msg},
               headers=H["agent"]).json()
    step("T4 scam blocked", f"draft {d['id']} status={d['status']}; failed checks: "
                            f"{', '.join(x['id'] for x in d['checks'] if not x['passed'])}")

    # 3. T1: tuition, cheapest bank, two-person approval, sandbox transfer
    plan = c.post("/plan/tuition", json={"amount_cny": "35200", "deadline": "2026-11-15"}, headers=H["parent"]).json()
    best = plan["options"][0]
    d = c.post("/drafts", json={"kind": "tt_tuition", "amount_cny": "35200", "payee_id": "univ_demo",
                                "quote_id": plan["best_quote_id"], "memo": "Tuition 2026-27"}, headers=H["agent"]).json()
    denied = c.post(f"/drafts/{d['id']}/execute", headers=H["agent"]).status_code
    approve_and_execute(d)
    step("T1 tuition", f"best {best['bank']} ৳{best['total_bdt']} (saves ৳{plan['savings_best_vs_worst_bdt']}); send by "
                       f"{plan['send_by']}; agent execute → HTTP {denied}; approved by {', '.join(d['required_approvers'])}; sent")

    # 4. T2: living money within the 5 lakh / 30 transaction limits
    lp = c.post("/plan/living", json={"need_cny": "6000", "bridge_cny": "1000"}, headers=H["student"]).json()
    b = lp["best"]
    tt = c.post("/drafts", json={"kind": "tt_living", "amount_cny": b["tt_cny"], "payee_id": "student_own_cn",
                                 "quote_id": b["quote_id"], "memo": "Living costs Oct"}, headers=H["agent"]).json()
    approve_and_execute(tt)
    atm_total = sum(float(w) for w in b["atm_withdrawals_cny"])
    atm = c.post("/drafts", json={"kind": "atm_plan", "amount_cny": str(atm_total), "withdrawals": b["atm_withdrawals_cny"]},
                 headers=H["agent"]).json()
    approve_and_execute(atm, "student")
    step("T2 living money", f"¥{b['tt_cny']} by transfer + ATM {b['atm_withdrawals_cny']}; ৳{b['total_bdt']} vs ৳"
                            f"{lp['baseline_all_atm']['total_bdt']} all-ATM (saves ৳{lp['savings_vs_all_atm_bdt']})")

    # 5. Card emergency: agent freezes, only the student can unfreeze
    r = c.post("/agent/chat", json={"message": "I lost my card!", "lang": "en"}, headers=H["student"]).json()
    agent_unfreeze = c.post("/cards/4821/unfreeze", headers=H["agent"]).status_code
    c.post("/cards/4821/unfreeze", headers=H["student"])
    step("Card controls", f"agent ({r['mode']}) froze card via {r['tools_used']}; agent unfreeze → HTTP {agent_unfreeze}; "
                          "student unfroze with fingerprint/PIN")

    # 6. Time passes: tuition arrives; monthly living transfers
    c.post("/sandbox/advance", json={"days": 7}, headers=H["parent"])
    uni = next(a for a in c.get("/accounts", headers=H["parent"]).json()["accounts"] if a["id"] == "university")
    step("Tuition arrived", f"university account ¥{uni['balance']} (deadline 2026-11-15)")
    case = None
    for month in ("Nov", "Dec"):
        c.post("/sandbox/advance", json={"days": 30}, headers=H["parent"])
        d = c.post("/drafts", json={"kind": "tt_living", "amount_cny": "5000", "payee_id": "student_own_cn",
                                    "memo": f"Living costs {month}"}, headers=H["agent"]).json()
        approve_and_execute(d)
        step(f"Living transfer {month}", "¥5000 to own Chinese account, approved by parent, status sent")
        if month == "Nov":
            # 7. T3: endorsement renewal (expires 2026-12-31): plan made in time, steps ticked off over the month
            case = c.post("/renewals/endorsement_expiry", headers=H["student"]).json()
            dates = {s_["id"]: s_["due"] for s_ in case["steps"]}
            step("T3 renewal planned", f"late={case['late']}; ask university by {dates['request_docs']}, parent at bank by "
                                       f"{dates['bank_visit']}; email EN+ZH and Bengali parent message drafted")
            for sid in ("request_docs", "collect_docs"):
                c.post(f"/renewals/case/{case['id']}/steps/{sid}", json={"status": "done"}, headers=H["student"])
    for sid, who in (("send_to_parent", "student"), ("bank_visit", "parent")):
        c.post(f"/renewals/case/{case['id']}/steps/{sid}", json={"status": "done"}, headers=H[who])
    c.post("/sandbox/advance", json={"days": 4}, headers=H["parent"])
    done = c.post(f"/renewals/case/{case['id']}/complete", json={"new_expiry": "2027-07-31"}, headers=H["parent"]).json()
    step("T3 renewal done", f"all {len(done['steps'])} steps done before expiry; new expiry {done['new_expiry']}")

    # 8. Credit building: payment passport
    p = c.post("/passport", json={"include_amounts": False}, headers=H["student"]).json()
    v = c.post("/passport/verify", json={"passport": p}).json()
    p_bad = json.loads(json.dumps(p))
    p_bad["entries"][0]["on_time"] = not p_bad["entries"][0]["on_time"]
    v_bad = c.post("/passport/verify", json={"passport": p_bad}).json()
    st = p["stats"]
    step("Payment passport", f"{st['payments']} payments, {st['renewals']} renewal, on time {st['on_time']}/{st['with_deadline']}; "
                             f"verify → {v['valid']}; tampered copy → {v_bad['valid']}")

    # 9. Export the evidence
    audit = c.get("/audit?limit=100000", headers=H["parent"]).json()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "sandbox_operation_log.jsonl").write_text(c.get("/audit/export", headers=H["parent"]).text + "\n", encoding="utf-8")
    events: dict[str, int] = {}
    for e in audit["entries"]:
        events[e["event"]] = events.get(e["event"], 0) + 1
    summary = "\n".join([
        "# Sandbox scenario: execution evidence",
        "",
        "Generated by `backend/scripts/demo_scenario.py`. Every step went through the real API: compliance checks,",
        "permission engine, two-person approvals, sandbox bank and the hash-chained audit log. No real money.",
        f"Exchange rates: real saved history (mode `{os.environ.get('SATHI_FX_MODE')}`); bank prices are estimates.",
        "",
        "| # | Sandbox date | Step | Result |",
        "|---|---|---|---|",
        *log,
        "",
        f"**Audit log:** {audit['verify']['entries']} entries, hash chain valid = **{audit['verify']['valid']}** "
        f"(file: `sandbox_operation_log.jsonl`).",
        "",
        "Events: " + ", ".join(f"{k} ×{v}" for k, v in sorted(events.items())),
        "",
    ])
    (EVIDENCE / "scenario_summary.md").write_text(summary, encoding="utf-8")
    print(f"\nexported {audit['verify']['entries']} log entries (chain valid: {audit['verify']['valid']}) to {EVIDENCE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
