# Build Plan: Bluefin (mobile-first)

**Last updated:** 2026-10-12 · **Deadline:** 20 Oct 2026 23:59 Beijing (21:59 Dhaka) · **Target first full submission:** 18 Oct

## Status (end of Day 0, 12 Oct)
- ✅ Backend: rule pack, cost engine, living optimiser, tuition planner, FX range + coverage backtest, permissions (L0–L3, two-person, mandates, tamper/replay protection), compliance checks, scam/injection detection, sandbox bank, hash-chained audit log, REST API. **78 tests pass.**
- ✅ Mobile (Expo SDK 57): Home timeline + limit meters, Plan (tuition comparison, living optimiser), approval screen with biometrics/PIN, Activity (drafts + audit log), message scam check, Settings (role, language bn/en/zh, server, sandbox clock, rule pack with sources). Typecheck and lint clean. T1 verified end to end in the web build.
- ✅ (12 Oct, later) **AI agent + inbox:** DeepSeek tool-calling chat (read + draft only) with offline fallback; SMS/email ingestion (share/paste, webhook, IMAP), privacy redaction, rule + AI extraction with number grounding, insight engine (fees, limits, fraud, scams, phishing, OTP, renewals, FX markup), translated updates. **104 tests pass.** Design: [03_agent_and_inbox.md](03_agent_and_inbox.md).
- ✅ (12 Oct, later) **Real exchange rates:** live mid-market rate + 953 days of daily BDT/CNY history (fawazahmed0/exchange-api, CC0), offline fallback, honest ranges (80% ranges were right 82% of 689 past 7-day tests), "if you wait" cost range on tuition plans, real bank quotes can be entered (bank prices are labelled estimates until then).
- ✅ **Card controls** (like a banking app): freeze / unfreeze / report lost. Asymmetric permissions: the agent may freeze (protective, reversible) but never unfreeze; unfreeze and report-lost need fingerprint/PIN. "Was this you?" alerts offer one-tap freeze; charges on a frozen card raise a top alert. **120 tests pass.**
- ✅ **T3 Renewal assistant** (the friend's #1 problem): plan worked backwards from the expiry date (ask university → collect → send to parent → bank visit → confirm), email to the international office in English + Chinese (在读证明 / 成绩单 / 缴费通知单), Bengali + English task list for the parent including "ask for an endorsement until the next fee is due", document checklist with confidence labels, step tracking with reminders (red when overdue), new expiry updates the profile. The agent may create the plan; only users tick steps or confirm. Bluefin never sends messages: the user copies or shares them. **129 tests pass.**
- ✅ **Credit building: payment passport.** Signed, verifiable record of on-time payments built only from this session's hash-chained log (tuition, living transfers, renewals done before expiry); hide-amounts option; QR code to a public verify page (needs the code); tampered, fabricated, revoked or expired passports fail; late payments shown as late. Users only.
- ✅ **Execution evidence:** `backend/scripts/demo_scenario.py` runs the whole story through the real API over ~2 sandbox months and exports `docs/evidence/sandbox_operation_log.jsonl` (hash chain valid) + `scenario_summary.md`. **139 tests pass.**
- ✅ **Photo document reader** (DeepSeek vision): fee notices, Chinese bank forms, university checklists → type, summary in the user's language, amounts (must appear in the transcription), deadlines, bilingual checklist; injection phrases flagged; long numbers masked; photo never stored; a fee notice is applied only after the user confirms (then it backs the invoice check). Live test on the friend's real residence-permit checklist: all 11 items read in 3.6 s. **144 tests pass.**
- ✅ **Real BRAC data point** (friend: ৳18.35/¥, ~৳8,000 file charge): BRAC's rate was only ~+0.2% over mid-market; the file charge was the bigger cost. Added a calibrated BRAC quote; generic estimates lowered to 0.6–1.8%.
- ✅ **Technical documentation** ([TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)) and **security self-assessment** ([SECURITY_SELF_ASSESSMENT.md](SECURITY_SELF_ASSESSMENT.md)) written: deliverables #1 and #5.
- 🔁 **13 Oct: re-architecture around one loop (Sense → Plan → Act → Prove).** Honest audit: the project read as 11 separate features; our own data showed the exchange rate was not the main problem (BRAC +0.22% vs a ৳8,000 charge, 5.5×); the one part where the AI acts (mandates) had no screen. Interview follow-up: **both** parent and student handle money; **renewing the endorsement needs the student in person** (passport), so a student in China loses the card abroad on 31 Dec. Built:
  - **Year plan** ("never stuck"): day-by-day simulation with both countries' bank calendars (`data/bank_holidays.yaml`, confidence per date), the endorsement end and card caps. Today's habits: 20 stuck days; Bluefin: 0. Cost truth: rate markup vs fees.
  - **Family mandate** from the parent's own words (bn/en/zh): rules parser + grounded DeepSeek + policy validator; template read-back; signatures bound to the proposal hash; both sign from ৳1 lakh; living money to the student's own account only; calendar-month caps.
  - **Autopilot**: the same look-ahead rule; acts only inside the mandate; asks the family when a cap is too small; explains why in the family feed.
  - **App**: Today · Plan (Year) · Family · Bluefin · Proof; spoken read-back before approving or signing; receipts showing who or what authorised each payment.
  - **Fixes**: the endorsement no longer blocks transfers (only card use); raw mandates are for the paying parent only; the Student File renewal link.
  - **Renewal plan** for a student abroad.
  - **Evidence**: 4 sandbox months, 0 stuck days, 187-entry log. **183 tests pass.**
- ✅ **13 Oct: real bank prices.**
  - Eastern Bank's daily CNY rate sheets (139 sheets, Mar–Oct 2026) via `scripts/fetch_bank_rates.py`, plus live refresh. Its CNY selling rate averaged +0.96% above the market.
  - Per-transfer fees from published 2026 schedules (EBL Retail + SME; Southeast; Prime): commission by amount + correspondent ৳2,500 + SWIFT ৳500 + 15% VAT, i.e. ৳3,680 on ৳1.13 lakh.
  - A Student File fee table: EBL ৳8,625 / ৳7,475; Southeast ৳8,050 / ৳4,025; Prime ৳6,900 / ৳6,900.
  - The unnamed estimates are gone. Every price says where it comes from: published, real payment, your quote, or estimate. BRAC's fees are labelled as an assumption.
  - The friend's ৳8,000 matches a one-time Student File opening fee.
  - **203 tests pass.**
- ✅ **16 Oct: Earn & Save (Interview #2).** A second student: in a dollar shortage money comes by hundi ("1–2 taka lost per dollar"), while students' own pay abroad leaks into luxury instead of savings. Built:
  - **Income in China** with the corridor's work rules (Exit and Entry Law Art. 43/80: university approval + work-study annotation; hour cap from conflicting sources, warned at 8 h): unauthorised work is flagged and never planned on.
  - **Savings rule the student signs** (words in bn/en/zh or a form; template read-back; hash covers share, target, cooling-off, family lock, sharing, fixed destination) → the autopilot fills the **Shield** on pay days (L3 inside the rule) and covers real shortfalls from it; planned withdrawals wait the cooling-off (and the parent, only if the student chose it); emergencies are instant.
  - **Taka lens**: wants in what they cost the family to send (cheapest legal bank, fees included) and in days of living money; bank-alert insights for pay and wants.
  - **Honest hundi check**: one bank transfer can cost more on paper ($500 at ৳124.5: ৳3,701 vs ৳623); Bluefin says so and shows the legal ways that beat both (Shield, planned transfers, the 10 Aug 2026 education-card circular).
  - **Dollar-crisis test**: 4 weeks without student transfers at every start week: 0% → 39% → **94%** of starts without a stuck day (today → Bluefin → Bluefin + Shield), typical 20 → 4 → **0** days.
  - App: **Save** tab, Shield card on Today, emergency option, crisis row in the stress test, chat tools + offline router (bn/en/zh, Banglish), family feed notes. Evidence: 237 entries; a top-up refused by the living cap was covered by the Shield; 0 stuck days. **327 tests pass.**
- ⏭ Next: deck (≤10 min) + demo video (≤5 min); try on a real phone with Expo Go (fingerprint, speech in Bengali); deploy the backend; first full submission on 18 Oct; ask organisers whether the on-chain bonus expects FISCO BCOS (anchor the log's chain head); exact date of the friend's payment and real SMS samples.

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
│ Home timeline · Bluefin chat · Plans/Compare · Approvals · Activity log   │
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
