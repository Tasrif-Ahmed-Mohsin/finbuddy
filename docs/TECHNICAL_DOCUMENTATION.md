# Sathi: Technical Documentation

**FinTechathon 2026 · International Track · Topic C: Cross-border & Student Finance Assistant**
Repository: https://github.com/Tasrif-Ahmed-Mohsin/finbuddy · Version: 13 Oct 2026 · Companion: [SECURITY_SELF_ASSESSMENT.md](SECURITY_SELF_ASSESSMENT.md)

> **Sandbox:** no real money moves. All payments run in a simulated bank. The **exchange rate is real** (live, plus 953 days of saved daily history). **Bank prices are estimates**, calibrated with one real payment (BRAC Bank, ৳18.35/¥), until real quotes are entered.

---

## 1. Summary

Sathi (সাথী, "companion") is an AI agent that **plans, checks and, with the user's approval, carries out** the cross-border money tasks of an international student and their family. The hero corridor is **Bangladesh → China**: a Bengali-speaking parent pays from Dhaka, the student lives in China, and university and bank documents are in Chinese.

The agent works in **Bengali, English and Chinese**. It keeps every payment **inside the real limits** students face (Student File caps, card caps of 5 lakh BDT and 30 transactions per month, ATM caps), finds the **lowest all-in cost**, and **blocks scams**. It never moves money without a human: the AI can only read, plan and draft.

| Organiser capability | How Sathi shows it |
|---|---|
| **Intent understanding** | Chat in BN/EN/ZH with DeepSeek tool calling; shared SMS/email parsed into transactions; photographed documents read and explained |
| **Task planning** | Deadline-aware tuition planner, limit-constrained living-money optimiser, backward-scheduled renewal plan |
| **Safe execution** | Deterministic compliance checks, permission levels L0–L3, approval tokens bound to the exact draft, sandbox bank, hash-chained log |
| **User control** | Fingerprint/PIN approval, two-person rule above ৳1 lakh, revocable mandates, the user confirms anything read by AI |
| **Measurable value** | ৳ saved vs alternatives, honest FX ranges with backtest, limits never breached (tested), on-time payment passport |

## 2. Problem and evidence (short)

Full research: [01_problem_research.md](01_problem_research.md) (34 problems with sources) plus a field interview with a Bangladeshi student who arrived in China in Sept 2026. Key facts:

- **Fees, not the rate, are the big leak.** The interviewee's real BRAC payment of ¥35,200 at ৳18.35 was only about **+0.2%** over the mid-market rate. The **~৳8,000 Student File charge** pushed total overhead to **~1.5%**. Every ATM withdrawal abroad costs **~৳345**.
- **Limits break the money pipeline:** a monthly card cap of 5 lakh BDT and 30 transactions; endorsements granted only Sep → Dec for students; a yearly Student File renewal.
- **Language and scams:** Chinese-only forms; hundi offers (the interviewee was offered hundi); "discount tuition agents"; fake-police calls.

## 3. Architecture

```mermaid
flowchart TB
  subgraph Phone["Mobile app (Expo SDK 57, React Native, TypeScript)"]
    UI["Home · Plan · Sathi (updates, chat, SMS, photo) · Activity · Settings<br/>Payment draft · Renewal · Passport"]
    BIO["Biometric / PIN approval (expo-local-authentication)"]
  end
  subgraph API["Backend (Python 3.12, FastAPI)"]
    SVC["Service layer (AppState): the ONLY path to drafts, approvals, execution"]
    AG["Agent: DeepSeek tool calling (read + draft only) + offline rule-based fallback"]
    ENG["Engines: cost · living optimiser · tuition planner · FX ranges · renewal planner"]
    SEC["Security: permission engine · approval tokens · compliance checks · scam/injection scan"]
    INB["Inbox: filter → redact → scan → rules/AI extraction (grounded) → tracking → insights"]
    DOC["Document reader (DeepSeek vision, grounded, not stored)"]
    PASS["Payment passport (HMAC-signed, audit-referenced)"]
    BANK["Sandbox bank: accounts, cards, clock, transfer delays, fees"]
    AUD["Audit log: append-only JSONL, SHA-256 hash chain"]
  end
  subgraph Data["Data"]
    RULES["Rule pack bd_cn.yaml (value + source + confidence)"]
    FX["fx_history.csv (953 days, CC0) + live rate"]
    Q["bank_quotes.yaml (estimates + 1 real calibration)"]
  end
  UI -- HTTPS JSON --> SVC
  BIO -. proves presence .-> UI
  AG --> SVC
  SVC --> ENG & SEC & INB & DOC & PASS & BANK
  BANK --> AUD
  SVC --> AUD
  ENG --> RULES & FX & Q
  AG -. redacted text only .-> DS[(DeepSeek API)]
  DOC -. image in memory .-> DS
```

**Why a backend, not "all in the phone":** the permission checks, compliance rules and audit log must run where neither a tampered app nor the AI can skip them. Every route goes through one service class (`backend/app/service.py`), and every action is logged.

### 3.1 Request lifecycle: tuition payment (task T1)

```mermaid
sequenceDiagram
  participant P as Parent (app)
  participant A as Agent / app
  participant S as Service + security
  participant B as Sandbox bank
  participant L as Audit log
  A->>S: plan/tuition (¥35,200, due 15 Nov)
  S-->>A: banks ranked by all-in cost, send-by 5 Nov, wait-risk range
  A->>S: create draft (agent allowed: L1 DRAFT)
  S->>S: compliance checks (payee allow-list, fee notice, quote fresh, memo, endorsement…)
  S->>L: draft_created
  A->>S: execute → 403 (agent can never execute)
  P->>S: approve (after fingerprint/PIN) → token bound to draft hash
  Note over S: ≥ ৳1 lakh → student must approve too
  P->>S: execute
  S->>S: re-run checks + verify tokens (hash, nonce, expiry, approvers)
  S->>B: transfer (arrives after 7 days)
  B->>L: transfer_sent … transfer_arrived
```

### 3.2 Repository map

| Path | Content |
|---|---|
| `backend/app/service.py` | Service layer: plans, drafts, approvals, execution, mandates, cards, renewals, passport, documents |
| `backend/app/engines/` | `cost.py`, `living_planner.py`, `tuition_planner.py`, `fx_range.py` |
| `backend/app/security/` | `permissions.py` (levels, tokens, mandates), `compliance.py` (checks), `scam.py` (scam/injection patterns) |
| `backend/app/agent/` | `llm.py` (DeepSeek client), `chat.py` (tool-calling agent + fallback), `explain.py` (grounded translation) |
| `backend/app/inbox/` | `filters.py`, `redact.py`, `parsers.py`, `extract_llm.py`, `insights.py`, `service.py`, `email_imap.py` |
| `backend/app/` | `fx.py` (real rates), `market.py`, `renewal.py`, `passport.py`, `documents.py`, `sandbox/bank.py`, `audit/log.py` |
| `backend/app/corridors/bd_cn.yaml` | Rule pack: every number with value, confidence (official / secondary / field / assumption) and source |
| `backend/scripts/` | `fetch_fx_history.py` (data pipeline), `demo_scenario.py` (end-to-end run + evidence export) |
| `backend/tests/` | 144 automated tests (11 files) |
| `mobile/src/` | Expo Router screens (`app/`), components, API client, i18n (bn/en/zh), formatting (lakh, Bengali digits) |
| `docs/` | Research, plans, this document, security self-assessment, `evidence/` (sandbox operation logs) |

## 4. Core algorithms

### 4.1 All-in cost engine (`engines/cost.py`)
For each way of delivering `X` CNY, all money uses `Decimal`, never float:

- **Bank transfer (TT):** `total = (X + intermediary) × bank_rate + fixed_fee`
- **ATM withdrawal i** with a Bangladeshi card: `(wᵢ + CN_ATM_fee) × mid × (1+card_markup) × (1+non_USD_factor) + BD_fee`
- **Alipay with a foreign card:** 3% service fee on payments above ¥200, at the card rate

`overhead = total − X × mid_market`. The engine returns every line item ("where the money goes").

### 4.2 Living-money constrained optimiser (`engines/living_planner.py`)
**Decision:** how much to send by bank transfer `t` to the student's own Chinese account, and how to split the rest `X − t` into ATM withdrawals.

**Minimise** total cost, subject to:
- card transactions: used + reserved + n ≤ 30 (field data)
- card BDT charged: spent + ATM cost ≤ 5,00,000 (field data)
- ATM: per withdrawal ≤ min(ATM cap, daily cap), in whole ¥100 notes; monthly ATM ≤ USD 1,500 equivalent; enough days at the daily cap
- living remittance this month + `t` ≤ USD 2,000 (FE Circular 37, secondary)
- money needed before a transfer can arrive (bridge) comes from the ATM

**Method:** exact grid search over `t` in ¥100 steps, so it's transparent and auditable. ATM amounts use maximum-size withdrawals to minimise fixed fees. Every rejected option records *which* limit it breaks. A property-style test checks 30 input combinations: **the chosen plan never breaks a limit**, and infeasible cases explain why.

**Result on real rates:** ¥6,000/month costs ৳1,14,128 vs ৳1,17,416 using only the ATM (**saves ৳3,288/month**, overhead nearly halved). ¥10,000 saves ৳7,256.

### 4.3 Tuition planner (`engines/tuition_planner.py`)
- **Send-by date** = deadline − transfer days (field: ~7) − safety buffer (3). Chinese universities count a fee as paid when it *arrives*.
- Status: `on_track` / `urgent` / `urgent_no_buffer` / `at_risk_late`.
- Banks are ranked by all-in cost for the exact amount (fixed fee vs rate trade-off).
- **Wait-risk:** the cost range if the family waits until the send-by date, from §4.4. It is labelled honestly: under a random walk, waiting has no expected gain and only adds risk.

### 4.4 FX ranges with an honesty check (`engines/fx_range.py`, `fx.py`)
We do **not** predict direction: Meese & Rogoff (1983) found that a random walk beats most models. For a horizon of `h` days we take the empirical 10th/50th/90th percentiles of past `h`-day log returns of BDT/CNY (rolling 250-day window), centred on today's rate.

**Coverage backtest on 953 days of real data** (an 80% range should contain the real rate ~80% of the time):

| Horizon | Tests | 80% range contained the outcome |
|---|---|---|
| 7 days | 689 | **81.9%** |
| 14 days | 675 | 85.8% |
| 30 days | 643 | 86.8% |

Ranges are slightly conservative at longer horizons. The **data pipeline** is `scripts/fetch_fx_history.py`: fawazahmed0/exchange-api, CC0, daily snapshots, CDN plus mirror, incremental. Live mode falls back to saved history when offline (relevant for the on-site final). Known limitation: the source lags official Bangladesh Bank changes by about 1–2 days.

### 4.5 Message tracking pipeline (`inbox/`)
`filter → redact → scan → extract → track → insights`

1. **Filter:** known financial senders, or at least two money terms; anything else is dropped and never stored.
2. **Redact:** OTP codes removed; 9–19-digit numbers masked to their last 4; emails masked.
3. **Scan:** scam, phishing and prompt-injection patterns in EN/BN/ZH. Risky messages are never turned into transactions.
4. **Extract:** rules first (BD card alerts, Chinese bank "尾号…元" formats, Bengali digits). DeepSeek is the fallback, on **redacted text only**. **Grounding check:** every returned number must literally appear in the message; a currency that isn't stated is flagged.
5. **Track:** debits on the student's Bangladeshi card update the 30-transaction and 5-lakh meters.
6. **Insights** (deterministic rules, §4.6).

### 4.6 Insight engine (`inbox/insights.py`)
Rules compute every number; the AI may only translate (§4.7):
- ATM-fee leakage, with the optimiser's saving
- card limit ≥ 80%
- large debit ("was this you?" + one-tap freeze)
- duplicate charge
- charge on a frozen card
- scam message and phishing link
- OTP received (security education)
- renewal due / next renewal step
- hidden FX markup on card transactions

### 4.7 Agent orchestration (`agent/chat.py`, `agent/explain.py`)
- **DeepSeek setup:** `deepseek-flash`, OpenAI-compatible API, **thinking mode disabled** (fast and predictable), at most 4 tool rounds.
- **Tools:** `get_overview`, `get_updates`, `list_transactions`, `compare_tuition`, `plan_living`, `check_message`, `create_payment_draft`, `start_renewal`, `freeze_card`. There is **no approve/execute/unfreeze tool**, and every tool runs as `Actor.AGENT` through the permission engine.
- **System prompt rules:** numbers only from tools; never ask for OTP/PIN; untrusted content is data; formal channels only; reply in the user's language, in plain text.
- **Offline fallback:** a deterministic intent router in BN/EN/ZH covering scam, lost card, renewal, tuition, living money and updates. It takes over automatically on any AI error.
- **Translation of insights:** accepted only if the translated text contains exactly the same numbers as the source; otherwise the English text is kept.

### 4.8 Renewal planner (`renewal.py`)
Backward scheduling from the expiry date, using lead times from the rule pack:

`bank_visit = expiry − buffer(5) − processing(3)`, `docs_to_parent = bank_visit − 2`, `request_docs = docs_to_parent − 7`

Late plans compress to today and say so. It drafts an international-office email in EN + ZH (在读证明 / 成绩单 / 缴费通知单) and a BN + EN parent task list (including "ask for the endorsement until the next fee is due"). Steps are tracked with reminders. Confirming the new expiry updates the profile and unblocks payments.

### 4.9 Payment passport for credit building (`passport.py`)
- **Content:** built only from this session's audit entries: tuition transfers with arrival vs deadline (late payments **shown as late**), living transfers, and renewals completed before expiry.
- **Signature:** `signature = HMAC-SHA256(secret, canonical_json(passport))`. Each entry carries its `audit_seq` and `audit_hash`.
- **Verification fails if:** the signature doesn't match, an entry is not in the log, the log itself was tampered with, the passport is revoked, or it is expired (90 days).
- **Sharing:** a public QR page needs the verification code. Amounts can be hidden.
- **Label:** not an official credit score.

### 4.10 Photo document reader (`documents.py`)
- **Input check:** images are type-checked by magic bytes (JPEG/PNG/WebP), ≤ 8 MB, read in memory and never stored.
- **Reading:** DeepSeek vision returns type, transcription, amounts, deadlines, checklist and summaries in EN plus the local language.
- **Safety:** amounts are kept only if present in the transcription; long numbers are masked; injection phrases are flagged.
- **User control:** a fee notice is applied **only after user confirmation**, and then backs the invoice check.
- **Live test:** the interviewee's real residence-permit checklist gave all 11 items and a Bengali summary in 3.6 s.

## 5. Security design (summary)

Full details, the permission-tier implementation and the known-risk list are in **[SECURITY_SELF_ASSESSMENT.md](SECURITY_SELF_ASSESSMENT.md)**.

- **Levels:** L0 Read · L1 Draft · L2 Execute (user approval token) · L3 Mandate (capped, revocable) · hard blocks nobody can override.
- **Approval tokens:** HMAC over the draft hash (amount, payee, rate quote, expiry, memo). They expire after 15 minutes, are single-use, and require two people above ৳1 lakh.
- **Asymmetric friction:** protective actions are easy (the agent may freeze a card); risky actions need a human (unfreeze, report lost, approve, issue a passport).
- **Logging:** a hash-chained audit log for every action; tamper detection is tested.
- **AI containment:** the AI has no execute tool; numbers are grounded; inputs are treated as untrusted; it degrades to rules when unavailable.

## 6. Data, sources and licences

| Data | Source | Confidence / licence |
|---|---|---|
| Mid-market BDT/CNY (live + 953 days) | fawazahmed0/exchange-api | CC0-1.0 (public domain) |
| Bank prices | `bank_quotes.yaml`: estimates + **1 real BRAC payment** (৳18.35/¥, ~৳8,000 charge) | `sample` = estimate; labelled in the app |
| Rules and limits | `corridors/bd_cn.yaml`, 30+ parameters, each with source | official / secondary / field / assumption |
| Demo messages | `data/demo_messages.yaml` | **synthetic**, written by us, generic senders |
| Research | `docs/01_problem_research.md` | sources cited per item |

**Software licences** (all permissive): FastAPI, Pydantic, PyYAML, pytest (MIT); Uvicorn, NumPy, httpx, qrcode (BSD); Expo, React Native, react-native-svg and Expo modules (MIT). No proprietary code or data is included.

## 7. Measurable value

| Metric | Value | How measured |
|---|---|---|
| Living money ¥6,000/month | **৳3,288 saved per month** (~৳39,000/yr) vs ATM-only | optimiser on real rates |
| Living money ¥10,000/month | ৳7,256 saved per month | optimiser on real rates |
| Tuition ¥35,200 | ৳6,854 between the cheapest and the dearest bank option; real BRAC overhead 1.45% shown honestly | tuition planner |
| Card limits | 0 breaches in 30 tested combinations | `test_best_plan_never_breaks_a_cap` |
| FX honesty | 7-day 80% ranges right **81.9%** of 689 tests | coverage backtest |
| Safety | every red-team case blocked (see security report §9) | automated tests |
| Languages | BN/EN/ZH UI; agent and offline fallback tested in all three | tests |

## 8. API overview (FastAPI; interactive docs at `/docs`)

| Area | Endpoints |
|---|---|
| Rates and plans | `GET /market`, `POST /market/quotes`, `GET /fx`, `GET /fx/history`, `POST /plan/tuition`, `POST /plan/living` |
| Drafts and execution | `POST /drafts`, `GET /drafts[/{id}]`, `POST /drafts/{id}/approve`, `POST /drafts/{id}/execute`, `POST /drafts/{id}/execute-under-mandate/{m}`, `POST/DELETE /mandates` |
| Agent | `POST /agent/chat`, `GET /agent/status`, `POST /check/message` |
| Inbox | `POST /inbox/messages`, `POST /inbox/webhook` (`X-Ingest-Token`), `POST /inbox/email/sync`, `POST /inbox/demo/seed`, `GET /inbox/messages`, `GET /inbox/transactions`, `GET /inbox/summary`, `GET /inbox/sources`, `GET /insights?lang=` |
| Cards | `GET /cards`, `POST /cards/{last4}/freeze`, `POST /cards/{last4}/unfreeze`, `POST /cards/{last4}/report-lost` |
| Renewals | `POST/GET /renewals/{item}`, `POST /renewals/case/{id}/steps/{step}`, `POST /renewals/case/{id}/complete` |
| Documents | `POST /documents/read`, `POST /documents/apply` |
| Passport | `POST /passport`, `POST /passport/verify`, `POST /passport/{id}/revoke`, `GET /passport/{id}/verify?sig=` (public HTML) |
| Overview | `GET /timeline`, `GET /profile`, `GET /accounts`, `GET /corridor`, `POST /sandbox/advance`, `GET /audit`, `GET /audit/export`, `GET /health` |

Authentication in the sandbox: `Authorization: Bearer demo-student | demo-parent | demo-agent` (a known risk; see the security report).

## 9. Deployment and running

```bash
# Backend (Python 3.12)
cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Mobile (Node 22): scan the QR code with Expo Go, or use --web
cd mobile && npm install && npx expo start
```

| Variable (`backend/.env`, git-ignored) | Purpose |
|---|---|
| `DEEPSEEK_API_KEY` | AI agent, extraction fallback, translation, document reader (optional: rules work without it) |
| `DEEPSEEK_MODEL` | default `deepseek-flash` |
| `SATHI_FX_MODE` | `live` (default) · `offline` (saved history) · `fixture` (tests) |
| `SATHI_INGEST_TOKEN` | webhook secret for SMS forwarders |
| `SATHI_PASSPORT_SECRET` | passport signing key (random per process if unset) |
| `SATHI_IMAP_HOST / _USER / _PASSWORD` | optional read-only bank-alert mailbox (app password) |
| `EXPO_PUBLIC_API_URL` (mobile) | backend address for a deployed server |

**Final-day network plan (Shenzhen):** DeepSeek is reachable from mainland China. If the network fails anyway, FX switches to the saved history and the agent to its rule-based fallback, so every task still completes.

## 10. Testing and execution evidence

- `cd backend && .venv/Scripts/python -m pytest -q` runs **144 test cases** (107 test functions, some parameterised over many inputs), all passing:

  | Area | Test functions |
  |---|---|
  | Inbox and privacy | 17 |
  | FX and card controls | 16 |
  | Security and permissions | 15 |
  | End-to-end API scenarios | 13 |
  | Payment passport | 10 |
  | Renewals | 9 |
  | Living optimiser (incl. 30-combination limit check) | 7 |
  | Agent | 6 |
  | Documents | 5 |
  | Tuition and FX method | 5 |
  | Cost engine | 4 |

  Tests never call the real AI (a fake DeepSeek server is used) or the network.
- `cd mobile && npx tsc --noEmit && npx expo lint`: clean.
- **Execution evidence:** `python scripts/demo_scenario.py` runs the full story through the real API over about 2 sandbox months: scam blocked, tuition with two approvals, living money, card freeze/unfreeze, monthly transfers, renewal, passport. It exports `docs/evidence/sandbox_operation_log.jsonl` (52 entries, hash chain valid) and `docs/evidence/scenario_summary.md`.

## 11. Limitations and next steps

- Sandbox only; real execution would go through licensed partners (banks / remittance operators).
- Bank prices: one real data point so far; more real quotes are needed (the app accepts them).
- Message parsers are tuned on synthetic samples; we need real anonymised alerts.
- Automatic SMS reading is not used: Google Play allows it only for default SMS apps, and iOS has no API. Share, forward and email are used instead.
- Production hardening (real authentication, device-bound approval keys, KMS, TLS, rate limits): see the security report's known-risk list.
