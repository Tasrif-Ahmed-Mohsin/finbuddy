# Submission map: FinTechathon 2026, International Track, Topic C

Team **inki_ponki** · Project **Bluefin**: a cross-border student finance agent, Bangladesh → China.
Repository: https://github.com/Tasrif-Ahmed-Mohsin/finbuddy

## Evaluate it in 5 minutes

1. **Watch the story**: the demo video (≤ 5 min, link below) follows the app's Story mode: Sense → Plan → Act → Prove.
2. **Run it yourself**: start the backend and the app ([README → Run it](README.md#run-it)). On first launch, four
   short cards; then tap **See the whole story**: eleven steps, each doing the real thing on the sandbox (bank messages,
   the year plan, a Bangla mandate, two passkey signatures, an attack refused, the student's own Shield, four months passing, receipts, proof).
3. **Run the judges' tasks**: Settings → Judge mode (or `python scripts/judge_tasks.py`): **20/20** scripted tasks pass
   in fresh sandboxes, each with steps, checks, value and the log entry that proves it.
4. **Run the tests**: `cd backend && .venv/Scripts/python -m pytest -q`: **409 tests** pass, including the red-team cases.

## The six deliverables

| # | Deliverable | Where |
|---|---|---|
| 1 | **Technical documentation** (architecture, core algorithms, security design) | PDF: [submission/Bluefin_Technical_Documentation.pdf](submission/Bluefin_Technical_Documentation.pdf) · source: [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md); bank standards in [docs/FINTECH_STANDARDS_ISO20022.md](docs/FINTECH_STANDARDS_ISO20022.md) |
| 2 | **Presentation deck** (≤ 10 min) | *to be added* |
| 3 | **Demo video** (≤ 5 min) | *to be added* |
| 4 | **Source code** with README, deployment and tests | this repository: [README.md](README.md) (run it, deploy it), `backend/tests/` (409 tests), `Dockerfile` + `render.yaml` |
| 5 | **Security self-assessment** (permission tiers, known-risk list) | PDF: [submission/Bluefin_Security_Self_Assessment.pdf](submission/Bluefin_Security_Self_Assessment.pdf) · source: [docs/SECURITY_SELF_ASSESSMENT.md](docs/SECURITY_SELF_ASSESSMENT.md): levels L0–L3 with the action map, red-team results, 40 known risks |
| 6 | **Execution evidence** (sandbox operation logs + demo video) | PDF: [submission/Bluefin_Execution_Evidence.pdf](submission/Bluefin_Execution_Evidence.pdf) · source: [docs/EXECUTION_EVIDENCE.md](docs/EXECUTION_EVIDENCE.md) (the report) and [docs/evidence/](docs/evidence/): see below |

## Execution evidence (topic C is not on-chain: sandbox logs)

| Evidence | What it shows | File |
|---|---|---|
| **Sandbox operation log** | Four sandbox months (12 Oct 2026 → 21 Feb 2027) through the real API, one day at a time: 0 days without money; every approval, mandate signature and bank consent a passkey signature; a retried Send paid once; the books balanced. 255 entries, hash chain valid | [sandbox_operation_log.jsonl](docs/evidence/sandbox_operation_log.jsonl), [scenario_summary.md](docs/evidence/scenario_summary.md) (`scripts/demo_scenario.py`); check the chain with `python backend/scripts/verify_audit_log.py docs/evidence/sandbox_operation_log.jsonl` |
| **Judge mode** | The brief's scripted tasks, 20/20: task completion 9/9, security 7/7 (incl. a compromised-AI drill), interaction 4/4 | [judge_tasks.md](docs/evidence/judge_tasks.md) (`scripts/judge_tasks.py`) |
| **Safety fuzzing** | 50,000 random honest and hostile steps, 9 safety rules checked after every step: 0 broken, 492 payments still went through, 3 of 3 deliberate bugs caught | [safety_fuzzing_evidence.md](docs/evidence/safety_fuzzing_evidence.md), [fuzzing_report.json](docs/evidence/fuzzing_report.json) |
| **AI-specific defences** | Taint tracking, the output firewall, Confirmation of Payee | [taint_tracking_evidence.md](docs/evidence/taint_tracking_evidence.md), [ai_output_firewall_evidence.md](docs/evidence/ai_output_firewall_evidence.md), [confirmation_of_payee_evidence.md](docs/evidence/confirmation_of_payee_evidence.md) |

## How it maps to the scoring

| Dimension | Where to look |
|---|---|
| **Task completion (40%)** | Story mode; Judge tasks T1–T9; the year plan (20 → 0 days without money); the four-month sandbox log |
| **Security & compliance (30%)** | Judge tasks S1–S7; passkey-signed approvals; two-person rule; taint tracking; output firewall; Confirmation of Payee; double-entry books and exactly-once payments; safety fuzzing; the security self-assessment |
| **Innovation & interaction (30%)** | A family mandate spoken in Bangla; read-backs in three languages; one question instead of a guess; corrections; offline fallback; the animated companion; the trust center; privacy and AI consent (PIPL) |

All money is simulated (sandbox). The mid-market exchange rate and the banks' published rate sheets and fees are real.
