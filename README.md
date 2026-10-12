# Sathi: cross-border student finance agent

**FinTechathon 2026 · International Track · Topic C (Cross-border & Student Finance Assistant)**

Sathi (সাথী, "companion") helps international students and their families move money across borders at
the **lowest true cost**, **inside every limit**, and **safely**, in Bengali, English and Chinese.
Hero corridor: **Bangladesh → China**.

> ⚠️ Sandbox only. No real money moves. The **mid-market exchange rate is real** (live, with 953 days of saved
> history from [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api), CC0). **Bank prices are
> estimates** (`backend/app/data/bank_quotes.yaml`) until real quotes are entered; the app always says which.

## What works today

| Task | What happens |
|---|---|
| **T1 Tuition** | Compare banks by all-in cost → send-by date worked back from the arrival deadline → draft → **parent + student approve** (two-person rule above ৳1 lakh) → sandbox transfer → arrives after the transfer delay |
| **T2 Living money** | Constrained optimiser: transfer-to-own-account vs ATM withdrawals (~৳345 each) → cheapest plan that **never breaks** the 5 lakh BDT / 30 transactions / ATM / living-remittance caps |
| **T4 Scams** | Hundi, "discount tuition agents", fake police, card rental, crypto and prompt injection detected (EN/BN/ZH) → drafts **blocked** with an explanation |
| **AI agent + inbox** | Share/forward bank SMS and emails → privacy redaction (OTP removed, numbers masked) → transactions tracked → alerts and savings insights. DeepSeek chat agent explains, plans and drafts (it can never approve or send). See [docs/03_agent_and_inbox.md](docs/03_agent_and_inbox.md) |
| **Real rates** | Live BDT/CNY rate, 1-year chart, honest 80% ranges with a backtest (right 82% of 689 tests), "if you wait" cost range; refresh history with `python scripts/fetch_fx_history.py` |
| **T3 Renewal assistant** | Endorsement / Student File renewal planned backwards from the expiry date; university email in English + Chinese; Bengali task list for the parent; reminders until the new expiry is confirmed |
| **Photo document reader** | Photograph a fee notice or Chinese form → explained in Bengali/English/Chinese; amounts grounded, injection flagged, photo not stored; fee notice used only after you confirm |
| **Credit-building passport** | Signed on-time payment record with QR verification for landlords/banks (not an official credit score) |
| **Execution evidence** | `python scripts/demo_scenario.py` runs the full story and exports the hash-chained sandbox log to `docs/evidence/` |
| **Card controls** | Freeze / unfreeze / report lost. The agent may freeze (protective) but never unfreeze; unfreeze needs fingerprint/PIN |
| Security | Permission levels L0–L3, approval tokens bound to the exact draft (tamper and replay blocked), mandates with caps, hash-chained audit log |

## Run it

**Backend** (Python 3.12):
```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
API docs: http://localhost:8000/docs

**AI (optional):** put `DEEPSEEK_API_KEY=...` in `backend/.env`. This file is git-ignored; never put the key in the mobile app. Without a key, Sathi uses rule-based answers. Optional email: `SATHI_IMAP_HOST`, `SATHI_IMAP_USER`, `SATHI_IMAP_PASSWORD` (an app password).

**Mobile app** (Node 22, Expo SDK 57):
```bash
cd mobile
npm install
npx expo start          # scan the QR code with Expo Go on your phone
npx expo start --web    # or open in a browser
```
On a phone, the app looks for the backend on the same computer at port 8000 (the phone and computer must be on the same Wi-Fi, and the firewall must allow port 8000). Change the address in **Settings** if needed, or set `EXPO_PUBLIC_API_URL`.

## Test it
```bash
cd backend && .venv/Scripts/python -m pytest -q        # 144 tests: engines, security, agent, inbox, FX, cards, renewals, passport, documents
cd mobile && npx tsc --noEmit && npx expo lint
```

## Submission documents
- [Technical documentation](docs/TECHNICAL_DOCUMENTATION.md): architecture, core algorithms, security design, data, API, deployment, tests
- [Security self-assessment](docs/SECURITY_SELF_ASSESSMENT.md): permission-tier implementation, threat model, red-team results, known-risk list
- [Execution evidence](docs/evidence/scenario_summary.md): hash-chained sandbox operation log from a full end-to-end run

## Repository map
```
docs/00_project_brief.md     competition rules, decisions, concept, plan
docs/01_problem_research.md  34 problems + field interview, with sources and confidence labels
docs/02_build_plan.md        organiser expectations → scope → architecture → schedule
backend/app/corridors/       rule pack (every number has a source + confidence)
backend/app/engines/         cost engine, living optimiser, tuition planner, FX ranges
backend/app/security/        permissions, compliance checks, scam/injection detection
backend/app/sandbox/         simulated bank with clock, delays and fees
backend/app/audit/           hash-chained operation log (execution evidence)
mobile/src/app/              Expo Router screens (Home, Plan, Sathi, Activity, Settings, Draft)
```
