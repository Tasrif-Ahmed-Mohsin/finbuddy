# Build Plan: Sathi (mobile-first)

**Last updated:** 2026-10-12 · **Deadline:** 20 Oct 2026 23:59 Beijing (21:59 Dhaka) · **Target first full submission:** 18 Oct

## Status (end of Day 0, 12 Oct)
- ✅ Backend: rule pack, cost engine, living optimiser, tuition planner, FX range + coverage backtest, permissions (L0–L3, two-person, mandates, tamper/replay protection), compliance checks, scam/injection detection, sandbox bank, hash-chained audit log, REST API. **78 tests pass.**
- ✅ Mobile (Expo SDK 57): Home timeline + limit meters, Plan (tuition comparison, living optimiser), approval screen with biometrics/PIN, Activity (drafts + audit log), message scam check, Settings (role, language bn/en/zh, server, sandbox clock, rule pack with sources). Typecheck and lint clean. T1 verified end to end in the web build.
- ✅ (12 Oct, later) **AI agent + inbox:** DeepSeek tool-calling chat (read + draft only) with offline fallback; SMS/email ingestion (share/paste, webhook, IMAP), privacy redaction, rule + AI extraction with number grounding, insight engine (fees, limits, fraud, scams, phishing, OTP, renewals, FX markup), translated updates. **104 tests pass.** Design: [03_agent_and_inbox.md](03_agent_and_inbox.md).
- ✅ (12 Oct, later) **Real exchange rates:** live mid-market rate + 953 days of daily BDT/CNY history (fawazahmed0/exchange-api, CC0), offline fallback, honest ranges (80% ranges were right 82% of 689 past 7-day tests), "if you wait" cost range on tuition plans, real bank quotes can be entered (bank prices are labelled estimates until then).
- ✅ **Card controls** (like a banking app): freeze / unfreeze / report lost. Asymmetric permissions: the agent may freeze (protective, reversible) but never unfreeze; unfreeze and report-lost need fingerprint/PIN. "Was this you?" alerts offer one-tap freeze; charges on a frozen card raise a top alert. **120 tests pass.**
- ⏭ Next: T3 endorsement renewal assistant; photo document reader; credit-building payment passport; real anonymised SMS samples + friend's real BRAC quote; try on a real phone with Expo Go.

---

## 1. What the organisers actually expect (read from the rules, not guessed)

| They say | What it means for us |
|---|---|
| Theme: "AI as a Financial **Participant**", an agent that **completes real tasks** | Not a chatbot, not a dashboard. The agent must *do* things: plan, draft, and (with approval) execute transfers in a sandbox. |
| Brief: "intent understanding, task planning, safe execution, user control, measurable value" | Five capabilities. Every screen and module maps to at least one. |
| Scoring: task completion **40%** | 3–4 end-to-end tasks that **finish** in the sandbox, every time, live. |
| Security & compliance **30%** | Permission levels **implemented in code**, a rules engine, scam blocking, tamper-evident audit log. |
| Innovation & interaction **30%** | Parent ↔ student ↔ Chinese-document flow in 3 languages; honest FX ranges; constrained cost optimiser. |
| Deliverable: security self-assessment with "**permission-tier implementation** and known-risk list" | They will read *how* permissions are enforced. They must be enforced on the server, not just in UI text. |
| Deliverable: "**sandbox operation logs**" | Every action is logged as structured JSON, exportable as evidence. |
| Deliverable: source code with README, deployment steps, **test cases** | Automated tests from day 1 (`pytest`), plus scenario tests that produce the logs. |
| Judges: WeBank (a mobile-first digital bank) + econometrics professors | Mobile UX matters; any FX claim must survive "did you beat the random walk?" |

---

## 2. Product scope

### Users
- **Student** (in China; English/Bengali): living money, cards, limits, renewals.
- **Parent** (in Bangladesh; Bengali): pays tuition, approves big payments.

### MVP tasks: what "task completion" will be judged on

| # | Task (user says…) | Agent does | Problems solved |
|---|---|---|---|
| **T1** | "ছেলের টিউশন ৩৫,২০০ ইউয়ান, ১৫ তারিখের মধ্যে দিতে হবে" ("My son's tuition is 35,200 yuan, due by the 15th") | Parses intent → checks payee against allow-list → compares Bangladeshi banks' all-in cost → computes send-by date (deadline − transfer days − buffer) → shows FX-wait risk range → drafts transfer → **parent approves** → sandbox executes → tracks arrival | P-05, P-06, N-04, P-09 |
| **T2** | "I need ¥6,000 for this month" | Constrained optimiser: ATM withdrawals (~345 BDT each, caps) vs transfer to own Chinese account vs Alipay card → cheapest plan **that never breaks 5 lakh BDT / 30 transactions** → schedule → executes approved steps | N-01, N-02, N-06, P-11 |
| **T3** | (proactive) "Your endorsement expires in 21 days" | Builds renewal checklist → drafts enrolment-certificate request to university (EN/ZH) → sends parent a Bengali task list → tracks completion | N-05, P-07 |
| **T4** | "Someone says I can pay tuition 15% cheaper through his agency" / an uploaded message with hidden instructions | Detects scam / injection → **blocks** → explains in user's language → logs the event | P-09, P-24, P-25, N-08 |
| T5 (stretch) | Upload a Chinese document (e.g., the residence-permit checklist) | Extracts items → bilingual checklist with deadlines (24 h / 30 days) | P-10, P-18 |
| T6 (stretch) | "Australia mode": visa refused | Refund claim draft + convert-now vs hold scenario | P-29 |

### Explicitly out of scope (say so in the docs)
- Real money movement, real bank APIs (we use a **sandbox bank**). In a real product, execution would go through licensed partners.
- Crypto/on-chain (compliance reasons, see brief §2).
- Price *prediction*. We give calibrated **ranges** and risk, not buy/sell signals.

---

## 3. Architecture

```
┌──────────────── Phone (Expo / React Native, TypeScript) ────────────────┐
│ Home timeline · Sathi chat · Plans/Compare · Approvals · Activity log   │
│ Language: bn / en / zh · Lakh/crore formatting · Biometric/PIN approve   │
└───────────────▲─────────────────────────────────────────────────────────┘
                │ HTTPS (JSON)
┌───────────────┴──────────────── Backend (Python, FastAPI) ───────────────┐
│ Agent orchestrator ── LLM (tool calling; provider-swappable)             │
│   │  tools are READ / DRAFT only; the model has NO execute tool          │
│   │  deterministic fallback intent parser (offline / no-LLM demo mode)   │
│   ▼                                                                      │
│ Engines (pure code, unit-tested):                                        │
│   cost engine · living-money optimiser · tuition planner · FX ranges     │
│ Security layer:                                                          │
│   permission engine (L0–L3, approvals, 2-person rule) ·                  │
│   compliance rules (BD + CN rule packs with sources) · scam/injection    │
│ Sandbox bank (simulated accounts, clock, delays, fees)                   │
│ Audit log (append-only JSONL, hash-chained = tamper-evident)             │
│ Data: corridor rule pack (YAML, every value has source + confidence),    │
│       bank quotes, FX history                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Why a backend and not "all in the phone":** permission checks, compliance rules and the audit log must run where the user (or a tampered app) can't bypass them. That's the core of the 30% security score.

**Why Expo:** one TypeScript codebase for Android and iOS; test on a real phone with Expo Go (QR code); APK build for judges; **web version later almost for free** (react-native-web), which is exactly the "web page later if needed" plan.

### Key design rules (also go into the security self-assessment)
1. **The LLM never calculates money.** All amounts, fees, and rates come from the engines. The LLM only understands intent and explains.
2. **The LLM can't move money.** Execution requires a user approval token bound to the exact draft (amount, payee, rate quote, expiry). Change anything and the token is invalid.
3. **Documents and messages are data, never instructions.** Uploaded content is passed in tagged blocks; injection patterns are detected and logged.
4. **Every rule value carries its source, confidence (official / secondary / field / assumption) and review date.** The app shows an "estimate" badge on anything not official.
5. **Everything is logged.** Hash-chained JSONL; exportable as the execution evidence.

---

## 4. Permission model (implemented in `backend/app/security/permissions.py`)

| Level | Actions | Who/what can trigger |
|---|---|---|
| **L0 Read** | rates, comparisons, plans, explanations | agent freely |
| **L1 Draft** | create transfer drafts, reminders, checklists | agent freely; nothing moves |
| **L2 Execute** | execute a specific draft | **only with a user approval token**; above the 2-person threshold, both student and parent approve |
| **L3 Mandate** | repeat transfers within user-set caps (payee, max/period, expiry) | agent, only inside an active mandate; revocable |
| **Hard blocks** | unknown payee, rule violation, cap breach, scam/injection flag, stale quote, tampered draft, replayed token | nobody can override |

---

## 5. Core algorithms (for the "core algorithm description" deliverable)

1. **All-in cost engine:** cost = Σ legs (principal × rate markup vs mid-market + fixed fees + VAT + % fees). Reports "hidden cost vs mid-market" in ৳ and %.
2. **Living-money constrained optimiser (N-06):** minimise total cost over the mix of transfer-to-own-account / ATM withdrawals / card payments, subject to: monthly BDT cap, monthly transaction-count cap, per-withdrawal and daily caps, BD living-remittance cap, transfer arrival delay (bridge money). Exact search over a small grid, so it's transparent and provably never breaks a cap (unit-tested).
3. **Tuition planner:** send-by date = deadline − transfer days − buffer; bank ranking; "risk of waiting" range from the FX model; target-rate alert with deadline fallback.
4. **FX ranges:** empirical quantiles of h-day log returns of BDT/CNY (cross via USD) on a rolling window, with **coverage backtest** (do 80% ranges contain the outcome ~80% of the time?) and the random walk as the honest baseline.

---

## 6. Tech stack

| Part | Choice | Why |
|---|---|---|
| Mobile | Expo (React Native) + TypeScript + expo-router | Fast, cross-platform, Expo Go demo, web later |
| Approve | expo-local-authentication (biometric / device PIN) | Real "user control" moment on the phone |
| Backend | Python 3.12 + FastAPI + Pydantic | Fast to build; same language as data/FX code |
| Money math | `Decimal` (never floats for money) | Correct rounding; judges notice |
| Storage | JSON/JSONL files → SQLite if needed | Simple, inspectable, easy evidence export |
| LLM | Provider abstraction; Claude by default; deterministic fallback | Works even if the LLM is unreachable (e.g., network at the Shenzhen finals) |
| Tests | pytest (backend), scenario scripts that generate operation logs | Required deliverable |

**Finals risk:** at the on-site defence in Shenzhen, some foreign APIs may be unreachable from mainland China. Mitigation: host the backend outside the mainland, keep the deterministic fallback mode, and keep a recorded demo video.

---

## 7. Repository layout

```
chinahack/
├── README.md                 # what, why, how to run, how to test
├── docs/                     # brief, research, this plan, later: tech doc, security report
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI routes
│   │   ├── corridors/        # bd_cn.yaml rule pack (sources + confidence)
│   │   ├── engines/          # cost, living_planner, tuition_planner, fx_range
│   │   ├── security/         # permissions, compliance, scam
│   │   ├── sandbox/          # simulated bank + clock
│   │   ├── audit/            # hash-chained log
│   │   └── agent/            # orchestrator, tools, fallback intents (Day 4)
│   └── tests/
└── mobile/                   # Expo app
```

---

## 8. Schedule (8 days)

| Day | Date | Build | Done when |
|---|---|---|---|
| 0 | **12 Oct** | Plan; repo; rule pack; cost engine; living optimiser; permissions; compliance; sandbox; audit; API; tests | `pytest` green; API runs |
| 1 | 13 Oct | Mobile: navigation, Home timeline, Compare, Plan, Approval (biometric), Activity, wired to API | T1 + T2 work on the phone without chat |
| 2 | 14 Oct | FX data ingestion (real history) + range model + backtest; real Bangladeshi bank quotes (scrape or manual with date) | Range chart + coverage numbers |
| 3 | 15 Oct | Agent orchestrator (LLM tools) + chat screen + bn/en/zh + fallback mode | T1/T2 started by chat in Bengali |
| 4 | 16 Oct | T3 endorsement tracker + reminders; T4 scam/injection; document upload (T5) | All four tasks pass scenario tests |
| 5 | 17 Oct | Red-team tests; logs export; polish UI; deploy backend | Phone works against the deployed backend |
| 6 | **18 Oct** | **First full submission** (code + draft docs + logs) | Email sent |
| 7 | 19 Oct | Tech doc, security self-assessment, deck, demo video | Final versions |
| 8 | **20 Oct** | Fixes; final resubmission by midday Beijing | Done |

**Cut order if behind:** T6 → T5 → Chinese UI (keep Chinese document reading) → live LLM (fallback mode only).

---

## 9. Team split (adjust to your team size: 2–5)

| Role | Owns |
|---|---|
| Backend/engines | engines, security, sandbox, tests |
| Mobile | Expo app, approval flow, i18n |
| Data/FX | rates ingestion, bank quotes, FX ranges + backtest |
| Docs/pitch | tech doc, security report, deck, video, registration |

---

## 10. Definition of done (per deliverable)

| Deliverable | Done when |
|---|---|
| Technical documentation | Architecture, the 4 algorithms, security design, data sources + licences |
| Deck | ≤ 10 min; story (14 → 15 lakh, friend's problems) → demo → metrics → safety |
| Demo video | ≤ 5 min; T1–T4 on a real phone |
| Source code | GitHub; README; one-command run; tests pass |
| Security self-assessment | Permission levels with code references; known-risk list; red-team results |
| Execution evidence | Exported hash-chained sandbox logs for T1–T4 + video |
